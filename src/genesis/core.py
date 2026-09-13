import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

from genesis.adapter import ModelAdapter
from genesis.anthropic_adapter import AnthropicAdapter
from genesis.interface import (
    _confirm_overwrite,
    _get_idea,
    _get_json_path,
    _get_output_dir,
    _get_save_path,
    _select_adapter,
    _select_model,
    answer_fn,
    print_error,
    print_next_steps,
    print_progress,
    print_success,
)
from genesis.ollama_adapter import OllamaAdapter
from genesis.planner import Plan, Planner, PlannerError, _parse_plan
from genesis.scaffolder import build_and_test, scaffold


def _build_adapter(adapter_str: str, model: str, max_tokens: int) -> ModelAdapter:
    """Map an adapter name to a live adapter. Raises ValueError on unknown name or missing SDK."""
    if adapter_str == "anthropic":
        try:
            return AnthropicAdapter(model=model, max_tokens=max_tokens)
        except ImportError:
            raise ValueError(
                "Anthropic SDK not installed. Install with: pip install 'genesis[anthropic]'"
            )
    if adapter_str == "ollama":
        return OllamaAdapter(model=model, max_tokens=max_tokens)
    else:
        raise ValueError(f"Unknown adapter: {adapter_str}")


def _create_plan(
    idea: str | None,
    adapter_str: str,
    model: str,
    max_rounds: int = 6,
    max_tokens: int = 10000,
) -> Plan:
    """Create a plan from an idea. Raises PlannerError on failure."""
    if adapter_str is None:
        adapter_str = _select_adapter()
    if model is None:
        model = _select_model(adapter_str)

    adapter = _build_adapter(adapter_str, model, max_tokens)

    planner = Planner(adapter)
    return planner.plan(idea=idea, max_rounds=max_rounds, answer_fn=answer_fn)


def cmd_plan(
    idea: str | None,
    adapter_str: str,
    model: str,
    output_path: str,
    max_rounds: int = 6,
    max_tokens: int = 10000,
) -> int:
    """Plan an idea and return exit code."""
    try:
        if idea is None:
            idea = _get_idea()
        print_progress("Planning")
        plan = _create_plan(idea, adapter_str, model, max_rounds, max_tokens)
        print_success("Plan created")

        plan_dict = asdict(plan)
        plan_json = json.dumps(plan_dict, indent=2)

        if output_path:
            with open(output_path, "w") as f:
                f.write(plan_json)
            print_success(f"Plan saved to {output_path}")
        elif sys.stdin.isatty():
            save = _get_save_path()
            if save:
                with open(save, "w") as f:
                    f.write(plan_json)
                print_success(f"Plan saved to {save}")
            else:
                print(plan_json)
        else:
            print(plan_json)

        return 0

    except ValueError as e:
        print_error(str(e))
        return 1
    except PlannerError as e:
        print_error(f"Planning failed: {e}")
        return 1
    except ConnectionError as e:
        print_error(str(e))
        return 1
    except OSError as e:
        print_error(f"Could not write output: {e}")
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return 1


def cmd_scaffold(plan_json: str, output_dir: str | None, force: bool) -> int:
    """Scaffold a plan and return exit code."""
    try:
        if output_dir is None:
            output_dir = _get_output_dir()
        print_progress("Scaffolding")
        plan_data = json.loads(plan_json)
        plan = _parse_plan(plan_data)
        target_path = Path(output_dir)

        if target_path.exists():
            if not force:
                print_error(f"{output_dir} already exists. Use --force to overwrite.")
                return 1
            if any(target_path.iterdir()) and not (target_path / "PLAN.md").exists():
                print_error(
                    f"{output_dir} is not empty and was not created by Genesis. "
                    "Refusing to delete it — remove it yourself or choose another directory."
                )
                return 1
            shutil.rmtree(target_path)

        repo_dir = scaffold(plan, target_path)

        if not plan.supported:
            print_success(f"Scaffolded plan to {repo_dir} (unsupported stack — see PLAN.md)")
            return 0

        res = build_and_test(repo_dir)

        print_success(f"Scaffolded to {repo_dir}")
        if res.ok:
            print_success("Build and tests passed")
            print_next_steps(repo_dir)
            return 0
        else:
            print_error("Build or tests failed")
            print(res.output, file=sys.stderr)
            return 1

    except json.JSONDecodeError as e:
        print_error(f"Invalid plan JSON: {e}")
        return 1
    except KeyError as e:
        print_error(f"Plan JSON is missing a required key: {e}")
        return 1
    except TypeError:
        print_error("Plan JSON is not a plan object — expected an object with plan fields.")
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return 1


def cmd_scaffold_file(plan_path: str | None, output_dir: str | None, force: bool) -> int:
    """Read a plan from a path (prompting if absent), then scaffold it."""
    try:
        if plan_path is None:
            plan_path = _get_json_path()
        plan_json = Path(plan_path).read_text()
    except OSError as e:
        print_error(f"Could not read plan file: {e}")
        return 1
    return cmd_scaffold(plan_json, output_dir, force)


def cmd_create(
    idea: str | None,
    output_dir: str | None,
    adapter_str: str,
    model: str,
    output_path: str | None,
    force: bool,
    max_rounds: int = 6,
    max_tokens: int = 10000,
) -> int:
    """Plan and scaffold end-to-end."""
    try:
        if idea is None:
            idea = _get_idea()
        if output_dir is None:
            output_dir = _get_output_dir()
        print_progress("Planning")
        plan = _create_plan(idea, adapter_str, model, max_rounds, max_tokens)
        print_success("Plan created")
        plan_json = json.dumps(asdict(plan), indent=2)

        if output_path:
            with open(output_path, "w") as f:
                f.write(plan_json)
            print_success(f"Plan saved to {output_path}")

        target = Path(output_dir)
        if target.exists() and not force:
            if not sys.stdin.isatty():
                print_error(f"{output_dir} already exists. Use --force to overwrite.")
                return 1
            if not _confirm_overwrite(output_dir):
                print_error("Cancelled.")
                return 1
            force = True

        return cmd_scaffold(plan_json, output_dir, force)
    except ValueError as e:
        print_error(str(e))
        return 1
    except PlannerError as e:
        print_error(f"Planning failed: {e}")
        return 1
    except ConnectionError as e:
        print_error(str(e))
        return 1
    except OSError as e:
        print_error(f"Could not write output: {e}")
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return 1
