from pathlib import Path

import pytest

from genesis.planner import Phase, Plan
from genesis.scaffolder import normalize, scaffold


def sample_plan():
    return Plan(
        project_name="Todo App",
        summary="A command-line todo list manager.",
        stack=["Python 3.11", "argparse"],
        supported=True,
        phases=[Phase("Core", ["add task", "list tasks"])],
        manual_checklist=["create a data dir"],
    )


@pytest.mark.parametrize(
    "raw,expected",
    [("Todo App", "todo_app"), ("my-cli", "my_cli"), ("7guis", "p_7guis"), ("!!!", "project")],
)
def test_normalize(raw, expected):
    assert normalize(raw) == expected


def test_scaffold_structure(tmp_path):
    out = scaffold(sample_plan(), tmp_path / "gen")
    assert (out / "pyproject.toml").exists()
    assert (out / "src" / "todo_app").is_dir()
    assert not (out / "src" / "greetly").exists()
    text = (out / "pyproject.toml").read_text()
    assert 'name = "todo_app"' in text
    assert "A command-line todo list manager." in text


def test_no_stray_greetly(tmp_path):
    out = scaffold(sample_plan(), tmp_path / "gen")
    for path in out.rglob("*"):
        if path.is_file():
            assert "greetly" not in path.read_text()


def test_plan_travels(tmp_path):
    out = scaffold(sample_plan(), tmp_path / "gen")
    plan_md = (out / "PLAN.md").read_text()
    assert "A command-line todo list manager." in plan_md
    assert "Core" in plan_md


@pytest.mark.slow
def test_generated_repo_builds(tmp_path, monkeypatch):
    from genesis.scaffolder import build_and_test

    monkeypatch.chdir(tmp_path)
    out = scaffold(sample_plan(), Path("gen"))
    result = build_and_test(out)
    assert result.ok, result.output
    assert (out / ".venv" / "bin" / "todo_app").exists()
