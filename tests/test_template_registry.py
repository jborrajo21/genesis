import json
from pathlib import Path

import pytest

from genesis.errors import GenesisError
from genesis.template_registry import PYTHON_CLI, select_template, template_dir

RESULTS = Path(__file__).resolve().parent.parent / "evals" / "results"


def _recorded_plans():
    for path in sorted(RESULTS.glob("*.jsonl")):
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            stack = (record.get("plan") or {}).get("stack")
            if stack:
                yield record, stack


def test_corpus_is_populated():
    """Guards the test below from passing vacuously if the glob finds nothing."""
    assert sum(1 for _ in _recorded_plans()) >= 100


def test_classifier_agrees_with_every_recorded_eval_plan():
    """Persisted eval plans are a regression corpus for stack classification (D-063).

    A change that alters any recorded outcome fails here, forcing the question of
    whether that change was intended rather than letting it move silently.
    """
    disagreements = [
        (record["model"], record["idea"], stack, record["supported"])
        for record, stack in _recorded_plans()
        if (select_template(stack) is not None) != record["supported"]
    ]
    assert not disagreements, disagreements


@pytest.mark.parametrize(
    "stack,expected",
    [
        (["Python 3.11", "argparse"], "python-cli"),
        (["Python 3.11", "a guide to usage"], "python-cli"),
        (["Python 3.11", "Axios-like client"], "python-cli"),
        (["Python 3.11", "Django 5.0"], None),
        (["Node.js 20", "commander"], None),
        (["Rust", "tokio"], None),
    ],
)
def test_select_template(stack, expected):
    template = select_template(stack)
    assert (template.name if template else None) == expected


def test_template_dir_reports_a_missing_template(monkeypatch):
    monkeypatch.setattr("genesis.template_registry._TEMPLATES_ROOT", Path("/nonexistent"))
    with pytest.raises(GenesisError, match="force-reinstall"):
        template_dir(PYTHON_CLI)
