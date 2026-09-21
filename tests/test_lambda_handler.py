import base64
import io
import json
import logging
import tempfile
import zipfile
from pathlib import Path

import pytest

from genesis import lambda_handler as lh
from genesis.adapter import Completion, StopReason
from genesis.errors import AdapterAuthError, AdapterError

FIXTURES = Path(__file__).parent / "fixtures"


def load_event(name):
    return json.loads((FIXTURES / name).read_text())


def make_event(method="POST", path="/scaffold", body=None, b64=False, headers=None):
    event = {
        "version": "2.0",
        "rawPath": path,
        "headers": headers if headers is not None else {},
        "requestContext": {"http": {"method": method}},
        "isBase64Encoded": b64,
    }
    if body is not None:
        event["body"] = body
    return event


def plan_body(name="Todo CLI", stack=None):
    return json.dumps(
        {
            "project_name": name,
            "summary": "A command-line todo list manager.",
            "stack": stack or ["Python 3.11", "argparse"],
            "phases": [{"name": "Core", "steps": ["add a task"]}],
            "manual_checklist": [],
        }
    )


def unzip(response):
    return zipfile.ZipFile(io.BytesIO(base64.b64decode(response["body"])))


def test_both_fixtures_normalise_identically():
    """The base64 branch must produce exactly what the plain branch does."""
    plain = lh._normalise(load_event("scaffold_event.json"))
    encoded = lh._normalise(load_event("scaffold_event_b64.json"))
    assert plain == encoded
    assert json.loads(plain.body)["project_name"] == "Todo CLI"


def test_headers_are_lowercased():
    req = lh._normalise(make_event(headers={"Anthropic-Api-Key": "k", "Content-Type": "json"}))
    assert req.headers == {"anthropic-api-key": "k", "content-type": "json"}


@pytest.mark.parametrize("event", [make_event(), make_event(body=None)])
def test_absent_body_becomes_empty_string(event):
    """A GET carries no body; `.get(k, default)` would still yield None if present-and-null."""
    assert lh._normalise(event).body == ""


def test_null_body_becomes_empty_string():
    event = make_event()
    event["body"] = None
    assert lh._normalise(event).body == ""


def test_wrong_method_is_405_with_allow():
    res = lh.handler(make_event(method="GET"), None)
    assert res["statusCode"] == 405
    assert res["headers"]["Allow"] == "POST"


def test_unknown_path_is_404():
    assert lh.handler(make_event(path="/nope"), None)["statusCode"] == 404


def test_root_describes_the_api():
    """A link that 404s is worse than no link. The root is the API root, not the
    front door — that is the Pages site — so it lists endpoints rather than HTML."""
    res = lh.handler(make_event(method="GET", path="/"), None)
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert set(body["endpoints"]) == {"POST /scaffold", "POST /plan", "POST /create"}
    assert lh._API_KEY_HEADER in body["authentication"]
    assert "never stored" in body["authentication"]


def test_scaffold_returns_a_buildable_repo_as_a_zip():
    res = lh.handler(make_event(body=plan_body()), None)
    assert res["statusCode"] == 200
    assert res["isBase64Encoded"] is True
    assert res["headers"]["Content-Type"] == "application/zip"

    names = unzip(res).namelist()
    assert {n.split("/")[0] for n in names} == {"todo_cli"}
    assert "todo_cli/pyproject.toml" in names
    assert "todo_cli/PLAN.md" in names


def test_scaffold_from_the_base64_fixture():
    """The path a real Function URL takes when it decides the body is not text."""
    res = lh.handler(load_event("scaffold_event_b64.json"), None)
    assert res["statusCode"] == 200
    assert "todo_cli/pyproject.toml" in unzip(res).namelist()


def test_content_disposition_filename_is_normalised():
    res = lh.handler(make_event(body=plan_body()), None)
    assert res["headers"]["Content-Disposition"] == 'attachment; filename="todo_cli.zip"'


def test_content_disposition_filename_cannot_inject():
    """project_name is model output; normalize() leaves only [a-z0-9_], so CRLF and
    quotes cannot break out of the header value."""
    res = lh.handler(make_event(body=plan_body(name='Todo "CLI"!\r\nX-Evil: 1')), None)
    value = res["headers"]["Content-Disposition"]
    assert value.startswith('attachment; filename="') and value.endswith('.zip"')
    assert not set(value[22:-5]) - set("abcdefghijklmnopqrstuvwxyz0123456789_")


def test_unsupported_stack_still_scaffolds_and_says_so():
    res = lh.handler(make_event(body=plan_body(stack=["TypeScript", "React"])), None)
    assert res["statusCode"] == 200
    assert res["headers"]["Genesis-Supported"] == "false"


def test_supported_stack_is_flagged_supported():
    res = lh.handler(make_event(body=plan_body()), None)
    assert res["headers"]["Genesis-Supported"] == "true"


def test_no_temp_directory_survives_success_or_failure():
    """/tmp persists between Lambda invocations, so a leak reaches the next caller."""
    tmp = Path(tempfile.gettempdir())
    before = set(tmp.iterdir())
    lh.handler(make_event(body=plan_body()), None)
    lh.handler(make_event(body="not json"), None)
    assert set(tmp.iterdir()) == before


@pytest.mark.parametrize(
    "body,fragment",
    [
        ("not json", "Could not read the request body"),
        ("", "Could not read the request body"),
        ('{"project_name": "x"}', "Missing required key"),
        ("[1, 2]", "expected a plan object"),
    ],
)
def test_bad_bodies_are_400_with_a_useful_message(body, fragment):
    res = lh.handler(make_event(body=body), None)
    assert res["statusCode"] == 400
    assert fragment in json.loads(res["body"])["message"]


def test_a_non_function_url_event_is_400_not_a_traceback():
    res = lh.handler({"rawPath": "/"}, None)
    assert res["statusCode"] == 400
    assert "requestContext" in json.loads(res["body"])["message"]


def test_server_side_failures_are_500_and_leak_nothing(monkeypatch):
    """OSError means /tmp, which is ours — the caller is not at fault and sees no paths."""

    def boom(plan, target):
        raise OSError(28, "No space left on device", "/tmp/tmpsecret/todo_cli")

    monkeypatch.setattr(lh, "scaffold", boom)
    res = lh.handler(make_event(body=plan_body()), None)
    assert res["statusCode"] == 500
    assert "/tmp" not in res["body"]
    assert "No space left" not in res["body"]


def test_nothing_escapes_as_an_unhandled_exception(monkeypatch):
    def boom(plan, target):
        raise RuntimeError("internal detail nobody should see")

    monkeypatch.setattr(lh, "scaffold", boom)
    res = lh.handler(make_event(body=plan_body()), None)
    assert res["statusCode"] == 500
    assert "internal detail" not in res["body"]


# --- /plan -----------------------------------------------------------------

KEY = "sk-ant-secret"


def plan_event(body, key=KEY):
    headers = {"Anthropic-Api-Key": key} if key else {}
    return make_event(path="/plan", body=json.dumps(body), headers=headers)


def fake_adapter(monkeypatch, payload=None, error=None, captured=None):
    """Replace AnthropicAdapter so /plan runs with no key, no network, no SDK."""

    class Fake:
        def __init__(self, **kwargs):
            if captured is not None:
                captured.update(kwargs)

        def complete(self, messages, tools=None, response_schema=None):
            if error is not None:
                raise error
            return Completion(
                text=json.dumps(payload), tool_calls=[], usage=1, stop_reason=StopReason.DONE
            )

    monkeypatch.setattr(lh, "AnthropicAdapter", Fake)


def test_plan_without_a_key_is_401_naming_the_header():
    res = lh.handler(plan_event({"idea": "a todo cli"}, key=None), None)
    assert res["statusCode"] == 401
    assert "anthropic-api-key" in json.loads(res["body"])["message"]


def test_plan_returns_questions_and_passes_the_key_and_model(monkeypatch):
    captured = {}
    questions = {"status": "need_info", "questions": ["Which storage?"]}
    fake_adapter(monkeypatch, questions, captured=captured)
    res = lh.handler(plan_event({"idea": "a todo cli", "model": "claude-sonnet-5"}), None)

    assert json.loads(res["body"]) == {"status": "need_info", "questions": ["Which storage?"]}
    assert captured["api_key"] == KEY
    assert captured["model"] == "claude-sonnet-5"
    assert captured["max_tokens"] > 20  # the adapter default truncates every plan


def test_plan_ready_output_posts_straight_into_scaffold(monkeypatch):
    """The two endpoints compose: no server state reconstructs the pipeline."""
    fake_adapter(
        monkeypatch,
        {
            "status": "ready",
            "plan": {
                "project_name": "Todo CLI",
                "summary": "s",
                "stack": ["Python 3.11"],
                "phases": [{"name": "Core", "steps": ["add a task"]}],
            },
        },
    )
    planned = json.loads(
        lh.handler(
            plan_event({"idea": "a todo cli", "rounds": [{"questions": ["q"], "answers": ["a"]}]}),
            None,
        )["body"]
    )
    assert planned["status"] == "ready"

    scaffolded = lh.handler(make_event(body=json.dumps(planned["plan"])), None)
    assert scaffolded["statusCode"] == 200
    assert "todo_cli/pyproject.toml" in unzip(scaffolded).namelist()


def test_unknown_model_is_400_listing_the_allowed_ones(monkeypatch):
    fake_adapter(monkeypatch, {"status": "need_info", "questions": []})
    res = lh.handler(plan_event({"idea": "x", "model": "gpt-4"}), None)
    assert res["statusCode"] == 400
    assert "claude-haiku-4-5" in json.loads(res["body"])["message"]


def test_a_rejected_key_is_401_not_400(monkeypatch):
    """AdapterAuthError subclasses GenesisError, so a clause placed one line too
    low would return a plausible-looking 400 instead."""
    fake_adapter(monkeypatch, error=AdapterAuthError("the API key was rejected by Anthropic"))
    res = lh.handler(plan_event({"idea": "x"}), None)
    assert res["statusCode"] == 401

    fake_adapter(monkeypatch, error=AdapterError("upstream 529"))
    assert lh.handler(plan_event({"idea": "x"}), None)["statusCode"] == 502


def test_the_key_never_reaches_a_log_line_or_a_response(monkeypatch, caplog):
    fake_adapter(monkeypatch, error=RuntimeError("boom"))
    with caplog.at_level(logging.DEBUG):
        res = lh.handler(plan_event({"idea": "x"}), None)
    assert res["statusCode"] == 500
    assert KEY not in caplog.text
    assert KEY not in json.dumps(res)


# --- /create ---------------------------------------------------------------

READY_PLAN = {
    "status": "ready",
    "plan": {
        "project_name": "Todo CLI",
        "summary": "s",
        "stack": ["Python 3.11"],
        "phases": [{"name": "Core", "steps": ["add a task"]}],
    },
}


def create_event(body, key=KEY):
    headers = {"Anthropic-Api-Key": key} if key else {}
    return make_event(path="/create", body=json.dumps(body), headers=headers)


def test_create_without_a_key_is_401():
    res = lh.handler(create_event({"idea": "a todo cli"}, key=None), None)
    assert res["statusCode"] == 401


def test_create_asks_questions_before_it_builds(monkeypatch):
    """Same request and need_info shape as /plan — create is a planning round
    that happens to end in an artefact."""
    fake_adapter(monkeypatch, {"status": "need_info", "questions": ["Which storage?"]})
    res = lh.handler(create_event({"idea": "a todo cli"}), None)
    assert res["headers"]["Content-Type"] == "application/json"
    assert json.loads(res["body"]) == {"status": "need_info", "questions": ["Which storage?"]}


def test_create_returns_a_zip_once_ready(monkeypatch):
    """The endpoint returns two media types: JSON while asking, zip when done."""
    fake_adapter(monkeypatch, READY_PLAN)
    res = lh.handler(
        create_event({"idea": "a todo cli", "rounds": [{"questions": ["q"], "answers": ["a"]}]}),
        None,
    )
    assert res["statusCode"] == 200
    assert res["headers"]["Content-Type"] == "application/zip"
    assert res["headers"]["Content-Disposition"] == 'attachment; filename="todo_cli.zip"'
    assert res["isBase64Encoded"] is True
    assert "todo_cli/pyproject.toml" in unzip(res).namelist()


def test_create_carries_rounds_into_the_conversation(monkeypatch):
    """The client holds the conversation; a dropped round would plan on the wrong input."""
    captured = {}

    class Fake:
        def __init__(self, **kwargs):
            pass

        def complete(self, messages, tools=None, response_schema=None):
            captured["messages"] = [m.content for m in messages]
            return Completion(
                text=json.dumps(READY_PLAN), tool_calls=[], usage=1, stop_reason=StopReason.DONE
            )

    monkeypatch.setattr(lh, "AnthropicAdapter", Fake)
    lh.handler(
        create_event(
            {
                "idea": "a todo cli",
                "rounds": [{"questions": ["Which storage?"], "answers": ["JSON file"]}],
            }
        ),
        None,
    )
    assert any("JSON file" in m for m in captured["messages"])


def test_create_rejects_an_unknown_model(monkeypatch):
    fake_adapter(monkeypatch, READY_PLAN)
    res = lh.handler(create_event({"idea": "x", "model": "gpt-4"}), None)
    assert res["statusCode"] == 400


def test_create_leaves_no_temp_directory(monkeypatch):
    fake_adapter(monkeypatch, READY_PLAN)
    tmp = Path(tempfile.gettempdir())
    before = set(tmp.iterdir())
    lh.handler(create_event({"idea": "a todo cli"}), None)
    assert set(tmp.iterdir()) == before


def test_wrong_method_on_create_is_405():
    res = lh.handler(make_event(method="GET", path="/create"), None)
    assert res["statusCode"] == 405
    assert res["headers"]["Allow"] == "POST"
