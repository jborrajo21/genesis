from pathlib import Path

import pytest

from genesis.errors import GenesisError
from genesis.planner import _parse_plan
from genesis.template_registry import PYTHON_CLI, select_template, template_dir

CLI = {"language": "python", "kind": "cli"}


@pytest.mark.parametrize(
    "label,expected",
    [
        (CLI, "python-cli"),
        ({"language": "Python", "kind": " CLI "}, "python-cli"),  # case and spacing
        ({"language": "python", "kind": "web app"}, None),  # known language, no template
        ({"language": "rust", "kind": "cli"}, None),
        ({"language": "python"}, None),  # half a label is not a label
        (None, None),  # a plan file written before labels existed
        ({}, None),
    ],
)
def test_select_template(label, expected):
    template = select_template(label)
    assert (template.name if template else None) == expected


@pytest.mark.parametrize(
    "stack",
    [
        ["Python 3.10+", "Jinja2", "watchdog", "Flask or http.server for dev server"],
        ["Python 3.11", "requests", "beautifulsoup4 for web scraping"],
        ["Python 3.11", "click", "a GUI is out of scope"],
        ["Python 3.11", "argparse", "no web framework needed"],
        ["Python 3.11", "pandas", "mobile export not supported"],
    ],
)
def test_stack_text_no_longer_vetoes_a_labelled_plan(stack):
    """The regression this change exists for.

    The old matcher joined the stack into one string and refused the template if
    any excluded word appeared anywhere in it, so a plan was refused for saying it
    was *not* a web app. Every stack here was measured being refused on Sept 21,
    2026; each is a Python CLI that happens to mention a word (D-094).
    """
    plan = _parse_plan(
        {
            "project_name": "demo",
            "summary": "s",
            "stack": stack,
            "phases": [{"name": "Core", "steps": ["do a thing"]}],
            "label": CLI,
        }
    )
    assert plan.supported is True


def test_the_label_is_trusted_over_the_stack():
    """Selection reads the label alone, deliberately.

    A cross-check against the stack would reinstate the matching this replaces,
    and would merge two numbers the eval keeps apart: whether the model picked a
    stack we cover, and whether we read it correctly. A mislabelled plan is a
    planner defect, measured from the corpus rather than guarded here (D-094).
    """
    fastapi_labelled_cli = {
        "project_name": "api",
        "summary": "s",
        "stack": ["Python 3.11", "FastAPI", "Postgres"],
        "phases": [{"name": "Core", "steps": ["do a thing"]}],
        "label": CLI,
    }
    assert _parse_plan(fastapi_labelled_cli).supported is True


def test_supported_is_recomputed_not_read_from_input():
    """D-093: a plan file cannot talk its way past the registry."""
    plan = _parse_plan(
        {
            "project_name": "demo",
            "summary": "s",
            "stack": ["Rust"],
            "phases": [{"name": "Core", "steps": ["do a thing"]}],
            "label": {"language": "rust", "kind": "cli"},
            "supported": True,
        }
    )
    assert plan.supported is False


def test_template_dir_reports_a_missing_template(monkeypatch):
    monkeypatch.setattr("genesis.template_registry._TEMPLATES_ROOT", Path("/nonexistent"))
    with pytest.raises(GenesisError, match="force-reinstall"):
        template_dir(PYTHON_CLI)
