"""Core logic for greetly.

Everything in this module is a placeholder. Replace `run` with the project's
real behaviour and delete this note when you do.
"""


class AppError(Exception):
    """An expected failure. `cli.main` turns this into exit code 1."""


def run(target: str | None = None) -> str:
    """Placeholder behaviour: report what was asked for, and do nothing else."""
    if target is None:
        return "greetly: nothing to do (pass a target to see it echoed back)"
    if not target.strip():
        raise AppError("target must not be blank")
    return f"greetly: would run against {target!r}"
