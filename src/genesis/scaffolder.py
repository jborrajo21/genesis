import re
import shutil
import subprocess
import venv
from dataclasses import dataclass
from pathlib import Path

from genesis.planner import Plan
from genesis.template_registry import select_template, template_dir

_DEFAULT_NAME = "project"


@dataclass
class BuildResult:
    installed: bool
    tested: bool
    output: str

    @property
    def ok(self) -> bool:
        return self.installed and self.tested


def normalize(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    if not slug:
        return _DEFAULT_NAME
    if slug[0].isdigit():
        slug = "p_" + slug
    return slug


def scaffold(plan: Plan, target_dir: Path) -> Path:
    template = select_template(plan.stack)
    if template is None:
        return _scaffold_generic(plan, target_dir)

    name = normalize(plan.project_name)

    shutil.copytree(
        template_dir(template),
        target_dir,
        ignore=shutil.ignore_patterns(".pytest_cache", ".ruff_cache", "__pycache__"),
    )

    for path in target_dir.rglob("*"):
        if path.is_file():
            text = path.read_text()
            if template.package in text:
                path.write_text(text.replace(template.package, name))

    (target_dir / "src" / template.package).rename(target_dir / "src" / name)

    pyproject = target_dir / "pyproject.toml"
    pyproject.write_text(pyproject.read_text().replace(template.description, plan.summary))
    (target_dir / "PLAN.md").write_text(_render_plan_md(plan))

    return target_dir


def _render_plan_md(plan: Plan) -> str:
    lines = [f"# {plan.project_name}", "", plan.summary, "", "## Stack", ""]
    lines += [f"- {item}" for item in plan.stack]
    lines += ["", "## Phases", ""]
    for phase in plan.phases:
        lines.append(f"### {phase.name}")
        lines += [f"- {step}" for step in phase.steps]
        lines.append("")
    if plan.manual_checklist:
        lines += ["## Manual checklist", ""]
        lines += [f"- [ ] {item}" for item in plan.manual_checklist]
    return "\n".join(lines) + "\n"


def build_and_test(repo_dir: Path) -> BuildResult:
    repo_dir = repo_dir.resolve()
    venv_dir = repo_dir / ".venv"
    venv.create(venv_dir, with_pip=True)
    py = venv_dir / "bin" / "python"

    install = subprocess.run(
        [str(py), "-m", "pip", "install", "-e", ".[dev]"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if install.returncode != 0:
        return BuildResult(installed=False, tested=False, output=install.stdout + install.stderr)
    test = subprocess.run(
        [str(py), "-m", "pytest"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    return BuildResult(
        installed=True,
        tested=test.returncode == 0,
        output=install.stdout + install.stderr + test.stdout + test.stderr,
    )


def _scaffold_generic(plan: Plan, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "PLAN.md").write_text(_render_plan_md(plan))
    (target_dir / "README.md").write_text(_render_generic_readme(plan))
    return target_dir


def _render_generic_readme(plan: Plan) -> str:
    stack = ", ".join(plan.stack)
    return (
        f"# {plan.project_name}\n\n"
        f"{plan.summary}\n\n"
        f"Genesis doesn't have an automated scaffold for this stack ({stack}), "
        "so no code was generated. Follow PLAN.md phase by phase to build it "
        "by hand.\n"
    )
