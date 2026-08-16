def cmd_plan(idea: str, adapter: str, model: str, interactive: bool, output: str | None) -> int:
    """Plan an idea and return exit code."""
    ...


def cmd_scaffold(plan_json: str, output_dir: str, force: bool) -> int:
    """Scaffold a plan and return exit code."""
    ...


def cmd_create(
    idea: str,
    output_dir: str,
    adapter: str,
    model: str,
    interactive: bool,
    output: str | None,
    force: bool,
) -> int:
    """Plan and scaffold end-to-end."""
    ...
