import hashlib
import tomllib
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
        label={"language": "python", "kind": "cli"},
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
    assert (out / ".gitignore").exists()


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
    assert result.entrypoint
    assert not (out / ".venv").exists()
    assert not (out / ".pytest_cache").exists()
    assert not list(out.rglob("__pycache__"))


def _tree(root):
    """Map each file's path (relative to root) to a hash of its bytes."""
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_scaffold_is_byte_identical_across_runs(tmp_path):
    first = scaffold(sample_plan(), tmp_path / "first")
    second = scaffold(sample_plan(), tmp_path / "second")
    assert _tree(first) == _tree(second)


def test_scaffold_excludes_caches(tmp_path):
    out = scaffold(sample_plan(), tmp_path / "gen")
    junk = {".pytest_cache", ".ruff_cache", "__pycache__"}
    assert not [p for p in out.rglob("*") if junk & set(p.parts)]


@pytest.mark.parametrize("raw,expected", [("Class", "p_class"), ("import", "p_import")])
def test_normalize_avoids_python_keywords(raw, expected):
    assert normalize(raw) == expected


def test_summary_with_quotes_keeps_pyproject_valid(tmp_path):
    plan = sample_plan()
    plan.summary = 'A "quoted" tool.\nWith a newline.'
    out = scaffold(plan, tmp_path / "gen")
    tomllib.loads((out / "pyproject.toml").read_text())
