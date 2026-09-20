import base64
import io
import json
import tempfile
import zipfile
from pathlib import Path

import pytest

from genesis import lambda_handler as lh

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


def test_root_is_not_a_404():
    """A link that 404s is worse than no link; the placeholder must still answer."""
    assert lh.handler(make_event(method="GET", path="/"), None)["statusCode"] == 501


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
