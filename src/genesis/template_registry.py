import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Template:
    name: str
    path: str
    package: str  # placeholder package inside the template, e.g. "greetly"
    description: str  # placeholder description in its pyproject.toml
    requires: tuple[str, ...]
    excludes: tuple[str, ...]


PYTHON_CLI = Template(
    name="python-cli",
    path="python-cli",
    package="greetly",
    description="A tiny greeting CLI",
    requires=("python",),
    excludes=(
        "react",
        "vue",
        "flask",
        "django",
        "fastapi",
        "node",
        "ios",
        "android",
        "swift",
        "kotlin",
        "web",
        "mobile",
        "gui",
        "electron",
    ),
)

TEMPLATES: tuple[Template, ...] = (PYTHON_CLI,)


def _mentions(text: str, marker: str) -> bool:
    return re.search(rf"\b{re.escape(marker)}\b", text) is not None


def select_template(stack: list[str]) -> Template | None:
    """First template whose markers match the stack, or None. Order is precedence."""
    text = " ".join(stack).lower()
    for template in TEMPLATES:
        if all(_mentions(text, r) for r in template.requires) and not any(
            _mentions(text, x) for x in template.excludes
        ):
            return template
    return None
