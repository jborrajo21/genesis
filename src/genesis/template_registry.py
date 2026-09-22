from dataclasses import dataclass
from pathlib import Path

from genesis.errors import GenesisError


@dataclass(frozen=True)
class Template:
    name: str
    path: str
    package: str  # placeholder package inside the template, e.g. "greetly"
    description: str  # placeholder description in its pyproject.toml
    language: str  # matched against the planner's label, exactly and lowercased
    kind: str


PYTHON_CLI = Template(
    name="python-cli",
    path="python-cli",
    package="greetly",
    description="A tiny greeting CLI",
    language="python",
    kind="cli",
)

TEMPLATES: tuple[Template, ...] = (PYTHON_CLI,)
_TEMPLATES_ROOT = Path(__file__).resolve().parent / "templates"


def template_dir(template: Template) -> Path:
    """Filesystem location of a template's files inside the installed package."""
    path = _TEMPLATES_ROOT / template.path
    if not path.is_dir():
        raise GenesisError(
            f"Template '{template.name}' is missing from the installed package. "
            "Reinstall with: pip install --force-reinstall genesis-agent"
        )
    return path


def select_template(label: dict | None) -> Template | None:
    """The template matching a planner-emitted label, or None."""
    if not label:
        return None
    language = str(label.get("language", "")).strip().lower()
    kind = str(label.get("kind", "")).strip().lower()
    for template in TEMPLATES:
        if template.language == language and template.kind == kind:
            return template
    return None
