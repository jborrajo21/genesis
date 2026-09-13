import io
import json

import pytest

from genesis.adapter import Completion
from genesis.anthropic_adapter import SUPPORTED_MODELS
from genesis.core import _create_plan, cmd_create, cmd_plan, cmd_scaffold, cmd_scaffold_file
from genesis.fakes import FakeAdapter
from genesis.interface import _select_adapter, _select_model
from genesis.ollama_adapter import SUPPORTED_MODELS as OLLAMA_MODELS

PY = ["Python 3.11"]
RUST = ["Rust", "clap"]


def _plan(stack):
    """A plan dict, as it appears inside a planner response and in a plan file."""
    return {
        "project_name": "todo",
        "summary": "a cli todo app",
        "stack": stack,
        "phases": [{"name": "setup", "steps": ["init"]}],
        "manual_checklist": [],
    }


def _ready(stack):
    """A planner 'ready' response wrapping that plan."""
    return json.dumps({"status": "ready", "plan": _plan(stack)})


@pytest.fixture
def fake_adapter(monkeypatch):
    """Make _build_adapter hand back a scripted FakeAdapter. Call it with the responses."""

    def install(*responses):
        fake = FakeAdapter([Completion(text=r) for r in responses])
        monkeypatch.setattr("genesis.core._build_adapter", lambda *a, **k: fake)
        return fake

    return install


def test_create_plan_returns_plan(fake_adapter):
    fake_adapter(_ready(PY))
    plan = _create_plan("a todo app", "anthropic", "claude-haiku-4-5")
    assert plan.project_name == "todo"
    assert plan.supported is True


def test_create_plan_marks_unsupported_stack(fake_adapter):
    fake_adapter(_ready(RUST))
    assert _create_plan("a todo app", "anthropic", "m").supported is False


def test_cmd_plan_writes_output_file(fake_adapter, tmp_path):
    fake_adapter(_ready(PY))
    out = tmp_path / "plan.json"
    assert cmd_plan("idea", "anthropic", "m", str(out), 6, 10000) == 0
    assert json.loads(out.read_text())["project_name"] == "todo"


def test_cmd_plan_prints_json_to_stdout(fake_adapter, monkeypatch, capsys):
    fake_adapter(_ready(PY))
    monkeypatch.setattr("genesis.core._get_save_path", lambda: "")
    assert cmd_plan("idea", "anthropic", "m", None, 6, 10000) == 0
    out = capsys.readouterr().out
    assert json.loads(out[out.index("{") :])["project_name"] == "todo"


def test_cmd_plan_unknown_adapter_exits_one(capsys):
    assert cmd_plan("idea", "nope", "m", None, 6, 10000) == 1
    assert "Unknown adapter" in capsys.readouterr().err


def test_cmd_scaffold_unsupported_skips_build(tmp_path):
    out = tmp_path / "gen"
    assert cmd_scaffold(json.dumps(_plan(RUST)), str(out), False) == 0
    assert (out / "PLAN.md").exists()
    assert not (out / "pyproject.toml").exists()


def test_cmd_scaffold_bad_json_exits_one(tmp_path, capsys):
    assert cmd_scaffold("{not json", str(tmp_path / "gen"), False) == 1
    assert "Invalid plan JSON" in capsys.readouterr().err


def test_cmd_scaffold_existing_dir_without_force_exits_one(tmp_path, capsys):
    out = tmp_path / "gen"
    out.mkdir()
    assert cmd_scaffold(json.dumps(_plan(RUST)), str(out), False) == 1
    assert "already exists" in capsys.readouterr().err


def test_cmd_scaffold_file_reads_path(tmp_path):
    plan_file = tmp_path / "plan.json"
    plan_file.write_text(json.dumps(_plan(RUST)))
    out = tmp_path / "gen"
    assert cmd_scaffold_file(str(plan_file), str(out), False) == 0
    assert (out / "PLAN.md").exists()


def test_cmd_scaffold_file_missing_path_exits_one(tmp_path, capsys):
    assert cmd_scaffold_file(str(tmp_path / "nope.json"), str(tmp_path / "gen"), False) == 1
    assert "Could not read plan file" in capsys.readouterr().err


def test_cmd_create_hands_plan_content_to_scaffold(fake_adapter, tmp_path):
    fake_adapter(_ready(RUST))
    out = tmp_path / "gen"
    assert cmd_create("a todo app", str(out), "anthropic", "m", None, False, 6, 10000) == 0


def test_cmd_create_saves_plan_when_output_given(fake_adapter, tmp_path):
    fake_adapter(_ready(RUST))
    saved = tmp_path / "plan.json"
    args = ("idea", str(tmp_path / "gen"), "anthropic", "m", str(saved), False, 6, 10000)
    assert cmd_create(*args) == 0
    assert json.loads(saved.read_text())["project_name"] == "todo"


def test_select_adapter_reads_choice(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *a: "1")
    assert _select_adapter() == "anthropic"


def test_select_adapter_rejects_invalid_choice(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *a: "9")
    with pytest.raises(ValueError):
        _select_adapter()


def test_select_model_reads_choice(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *a: "1")
    assert _select_model("anthropic") == SUPPORTED_MODELS[0]


def test_select_model_accepts_custom_name(monkeypatch):
    answers = iter([str(len(SUPPORTED_MODELS) + 1), "some-future-model"])
    monkeypatch.setattr("builtins.input", lambda *a: next(answers))
    assert _select_model("anthropic") == "some-future-model"


def test_select_model_rejects_unknown_adapter():
    with pytest.raises(ValueError):
        _select_model("openai")


def test_select_model_offers_ollama_models(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *a: "1")
    assert _select_model("ollama") == OLLAMA_MODELS[0]


@pytest.mark.slow
def test_cmd_scaffold_supported_plan_builds(tmp_path):
    out = tmp_path / "gen"
    assert cmd_scaffold(json.dumps(_plan(PY)), str(out), False) == 0
    assert (out / "pyproject.toml").exists()


def test_cmd_plan_reports_unreachable_server(monkeypatch, capsys):
    def boom(*a, **k):
        raise ConnectionError("Could not reach Ollama at http://x. Run: ollama serve")

    monkeypatch.setattr(
        "genesis.core._build_adapter", lambda *a, **k: type("A", (), {"complete": boom})()
    )
    assert cmd_plan("idea", "ollama", "m", None, 6, 10000) == 1
    err = capsys.readouterr().err
    assert "ollama serve" in err
    assert "Could not write output" not in err


def test_cmd_create_reports_unreachable_server(monkeypatch, capsys, tmp_path):
    def boom(*a, **k):
        raise ConnectionError("Could not reach Ollama at http://x. Run: ollama serve")

    monkeypatch.setattr(
        "genesis.core._build_adapter", lambda *a, **k: type("A", (), {"complete": boom})()
    )
    assert cmd_create("idea", str(tmp_path / "gen"), "ollama", "m", None, False, 6, 10000) == 1
    err = capsys.readouterr().err
    assert "ollama serve" in err
    assert "Could not write output" not in err


@pytest.mark.parametrize(
    "payload",
    [
        '{"project_name": "x"}',
        '{"project_name": "x", "summary": "s", "stack": ["Python"], "phases": "not a list"}',
        "[]",
        '"just a string"',
        "null",
    ],
)
def test_cmd_scaffold_rejects_malformed_plans(payload, tmp_path, capsys):
    assert cmd_scaffold(payload, str(tmp_path / "gen"), False) == 1
    err = capsys.readouterr().err
    assert "Unexpected error" not in err
    assert not (tmp_path / "gen").exists()


def test_cmd_scaffold_accepts_plan_with_no_phases(tmp_path):
    plan = _plan(PY)
    plan["phases"] = []
    assert cmd_scaffold(json.dumps(plan), str(tmp_path / "gen"), False) == 0
    assert (tmp_path / "PLAN.md").exists() is False
    assert (tmp_path / "gen" / "PLAN.md").exists()


def test_cmd_create_force_overwrites_a_previous_scaffold(fake_adapter, tmp_path, monkeypatch):
    fake_adapter(_ready(RUST))
    out = tmp_path / "gen"
    out.mkdir()
    (out / "PLAN.md").write_text("an earlier scaffold")
    (out / "OLD.txt").write_text("stale")
    monkeypatch.setattr("builtins.input", lambda *a: pytest.fail("--force must not prompt"))
    assert cmd_create("idea", str(out), "anthropic", "m", None, True, 6, 10000) == 0
    assert not (out / "OLD.txt").exists()
    assert (out / "PLAN.md").exists()


def test_cmd_create_force_refuses_directory_genesis_did_not_create(fake_adapter, tmp_path, capsys):
    fake_adapter(_ready(RUST))
    out = tmp_path / "precious"
    out.mkdir()
    (out / "thesis.txt").write_text("irreplaceable")
    assert cmd_create("idea", str(out), "anthropic", "m", None, True, 6, 10000) == 1
    assert (out / "thesis.txt").read_text() == "irreplaceable"
    assert "Refusing to delete" in capsys.readouterr().err


def test_cmd_create_without_force_refuses_when_not_a_tty(
    fake_adapter, tmp_path, monkeypatch, capsys
):
    fake_adapter(_ready(RUST))
    out = tmp_path / "gen"
    out.mkdir()
    monkeypatch.setattr("genesis.core.sys.stdin", io.StringIO())
    assert cmd_create("idea", str(out), "anthropic", "m", None, False, 6, 10000) == 1
    assert "Use --force" in capsys.readouterr().err


def test_cmd_scaffold_unsupported_prints_no_setup_steps(tmp_path, capsys):
    assert cmd_scaffold(json.dumps(_plan(RUST)), str(tmp_path / "gen"), False) == 0
    assert "Run:" not in capsys.readouterr().out
