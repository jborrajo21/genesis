import pytest

from genesis.adapter import Completion, Message
from genesis.fakes import FakeAdapter
from genesis.planner import Phase, Plan, Planner, PlannerError, RoundResult, _parse_plan


def test_round_asks_when_info_missing():
    fake = FakeAdapter(
        [
            Completion(
                text='{"status": "need_info", \
                    "questions": ["What CLI framework?", "Which Python version?"]}'
            )
        ]
    )
    result = Planner(fake)._round([Message(role="user", content="a todo app")])
    assert result == RoundResult(
        status="need_info", questions=["What CLI framework?", "Which Python version?"]
    )


def test_round_raises_on_missing_questions():
    fake = FakeAdapter([Completion(text='{"status": "need_info"}')])
    with pytest.raises(PlannerError):
        Planner(fake)._round([Message(role="user", content="x")])


def test_round_raises_on_missing_plan_key():
    fake = FakeAdapter([Completion(text='{"status": "ready", "plan": {"project_name": "x"}}')])
    with pytest.raises(PlannerError):
        Planner(fake)._round([Message(role="user", content="x")])


def test_round_parses_ready_plan():
    plan_json = '{"status": "ready", \
        "plan": \
            {"project_name": "todo", \
                "summary": "a cli todo app", \
                "stack": ["Python 3.11"], \
                "phases": [{"name": "setup", "steps": ["init repo"]\
            }], "manual_checklist": []}}'
    result = Planner(FakeAdapter([Completion(text=plan_json)]))._round(
        [Message(role="user", content="x")]
    )
    assert result.status == "ready"
    assert result.plan.project_name == "todo"
    assert result.plan.phases[0].name == "setup"


def test_plan_loops_clarify_then_ready():
    need = Completion(text='{"status": "need_info", "questions": ["Which storage?"]}')
    ready = Completion(
        text='{"status": "ready", \
            "plan": \
                {"project_name": "todo", \
                    "summary": "s", \
                    "stack": ["Python 3.11"], \
                    "phases": [\
                        {"name": "setup", \
                        "steps": ["init"]}\
                            ], \
                    "manual_checklist": []}}'
    )
    fake = FakeAdapter([need, ready])
    result = Planner(fake).plan("a todo app", answer_fn=lambda qs: ["SQLite"])
    assert result.project_name == "todo"
    assert any("SQLite" in m.content for m in fake.calls[1])


def test_plan_raises_when_never_ready():
    need = Completion(text='{"status": "need_info", "questions": ["q?"]}')
    fake = FakeAdapter([need, need, need])
    with pytest.raises(PlannerError):
        Planner(fake).plan("vague", answer_fn=lambda qs: ["a"], max_rounds=2)


def test_parse_plan_flags_python_cli_supported():
    data = {
        "project_name": "todo",
        "summary": "s",
        "stack": ["Python 3.11", "argparse"],
        "phases": [{"name": "setup", "steps": ["init"]}],
        "manual_checklist": [],
    }
    assert _parse_plan(data).supported is True


def test_parse_plan_flags_web_unsupported():
    data = {
        "project_name": "app",
        "summary": "s",
        "stack": ["React", "Node"],
        "phases": [{"name": "ui", "steps": ["build"]}],
        "manual_checklist": ["install Node"],
    }
    plan = _parse_plan(data)
    assert plan.supported is False
    assert plan.manual_checklist


def test_revise_returns_updated_plan():
    original = Plan(
        project_name="todo",
        summary="s1",
        stack=["Python 3.11"],
        supported=True,
        phases=[Phase("setup", ["init"])],
    )
    revised = '{"status": "ready", \
        "plan": {\
            "project_name": "todo", \
            "summary": "s2", \
            "stack": ["Python 3.11"], \
                "phases": [{\
                    "name": "setup", \
                    "steps": ["init", "add config"]\
                }], \
            "manual_checklist": []}}'
    fake = FakeAdapter([Completion(text=revised)])
    result = Planner(fake).revise(original, "add a config step")
    assert result.summary == "s2"
    assert any("add a config step" in m.content for m in fake.calls[0])


@pytest.mark.parametrize(
    "payload",
    [
        '{"status": "ready", "plan": null}',
        '{"status": "ready", "plan": "a string"}',
        '{"status": "ready", "plan": []}',
        '{"status": "need_info", "questions": null}',
        '{"status": "need_info", "questions": "one question"}',
        '{"status": "ready", '
        '"plan": {"project_name": "x", "summary": "s", "stack": '
        '["python"], "phases": ["juststring"]}}',
        '{"status": "ready", '
        '"plan": {"project_name": "x", "summary": "s", "stack": '
        '["python"], "phases": [null]}}',
    ],
)
def test_round_rejects_wrong_typed_payloads(payload):
    with pytest.raises(PlannerError):
        Planner(FakeAdapter([Completion(text=payload)])).plan(idea="x", answer_fn=lambda q: [])
