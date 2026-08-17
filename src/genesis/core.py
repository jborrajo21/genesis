import json
import sys
from dataclasses import asdict
from pathlib import Path

from genesis.anthropic_adapter import AnthropicAdapter
from genesis.planner import Plan, Planner, PlannerError, _parse_plan
from genesis.scaffolder import build_and_test, scaffold


def _create_plan(
    idea: str,
    adapter_str: str,
    model: str,
    max_rounds: int = 4,
    max_tokens: int = 1000,
) -> Plan:
    """Create a plan from an idea. Raises PlannerError on failure."""
    if adapter_str == "anthropic":
        adapter = AnthropicAdapter(model=model, max_tokens=max_tokens)
    # Need to create OllamaAdapter
    # elif adapter_str == "ollama"
    # adapter = OllamaAdapter(model=model)
    else:
        raise ValueError(f"Unknown adapter: {adapter_str}")

    planner = Planner(adapter)
    return planner.plan(idea=idea, max_rounds=max_rounds, answer_fn=answer_fn)


def cmd_plan(
    idea: str,
    adapter_str: str,
    model: str,
    output_path: str | None,
    max_rounds: int = 4,
    max_tokens: int = 1000,
) -> int:
    """Plan an idea and return exit code."""
    try:
        plan = _create_plan(idea, adapter_str, model, max_rounds, max_tokens)

        plan_dict = asdict(plan)
        plan_json = json.dumps(plan_dict, indent=2)

        if output_path:
            with open(output_path, "w") as f:
                f.write(plan_json)
        else:
            print(plan_json)

        return 0

    except PlannerError as e:
        print(f"Error: planning failed: {e}", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"Error: could not write output: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: unexpected error: {e}", file=sys.stderr)
        return 1


def cmd_scaffold(plan_json: str, output_dir: str, force: bool) -> int:
    """Scaffold a plan and return exit code."""
    try:
        plan_data = json.loads(plan_json)
        plan = _parse_plan(plan_data)
        target_path = Path(output_dir)

        if target_path.exists() and not force:
            print(f"Error: {output_dir} already exists. Use --force to overwrite.", file=sys.stderr)
            return 1

        repo_dir = scaffold(plan, target_path)
        res = build_and_test(repo_dir)

        print(f"Scaffolded to {repo_dir}")
        if res.installed and res.tested:
            print("✓ Build and tests passed")
            return 0
        else:
            print("✗ Build or tests failed:", file=sys.stderr)
            print(res.output, file=sys.stderr)
            return 1

    except json.JSONDecodeError as e:
        print(f"Error: invalid plan JSON: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: unexpected error: {e}", file=sys.stderr)
        return 1


def cmd_create(
    idea: str,
    output_dir: str,
    adapter_str: str,
    model: str,
    output_path: str | None,
    force: bool,
    max_rounds: int = 4,
    max_tokens: int = 1000,
) -> int:
    """Plan and scaffold end-to-end."""
    try:
        plan = _create_plan(idea, adapter_str, model, max_rounds, max_tokens)
        plan_json = json.dumps(asdict(plan), indent=2)

        if output_path:
            with open(output_path, "w") as f:
                f.write(plan_json)
        else:
            print(plan_json)

        return cmd_scaffold(plan_json, output_dir, force)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except PlannerError as e:
        print(f"Error: planning failed: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: unexpected error: {e}", file=sys.stderr)
        return 1


def answer_fn(questions: list[str]) -> list[str]:
    answers = []
    for q in questions:
        print(f"\n{q}")
        answer = input("> ").strip()
        answers.append(answer)
    return answers
