import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

from genesis.anthropic_adapter import SUPPORTED_MODELS as ANTHROPIC_MODELS
from genesis.anthropic_adapter import AnthropicAdapter
from genesis.interface import (
    _get_idea,
    _get_json_path,
    _get_output_dir,
    _select_adapter,
    _select_model,
    print_error,
    print_progress,
    print_success,
)
from genesis.planner import Plan, Planner, PlannerError, _parse_plan
from genesis.scaffolder import build_and_test, scaffold

# from genesis.ollama_adapter import SUPPORTED_MODELS as OLLAMA_MODELS


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

    valid_models = {
        "anthropic": ANTHROPIC_MODELS,
        # "ollama": OLLAMA_MODELS,
    }
    if model not in valid_models.get(adapter_str, []):
        raise ValueError(f"Unknown model '{model}' for adapter '{adapter_str}'")

    if adapter_str == "anthropic":
        try:
            adapter = AnthropicAdapter(model=model, max_tokens=max_tokens)
        except ImportError:
            raise ValueError(
                "Anthropic SDK not installed. Install with: pip install 'genesis[anthropic]'"
            )
    # Need to create OllamaAdapter
    # elif adapter_str == "ollama"
    #     try:
    #         adapter = OllamaAdapter(model=model)
    #     except ConnectionError:
    #         raise ValueError("Ollama not found at localhost:11434. Run: ollama serve")
    else:
        raise ValueError(f"Unknown adapter: {adapter_str}")

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
            print("\nSave this plan to a file?")
            save = input("Path (leave blank to print instead) → ").strip()
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
    except OSError as e:
        print_error(f"Could not write output: {e}")
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return 1


def cmd_scaffold(plan_json: str | None, output_dir: str | None, force: bool) -> int:
    """Scaffold a plan and return exit code."""
    try:
        if output_dir is None:
            output_dir = _get_output_dir()
        if plan_json is None:
            plan_json = _get_json_path()
        else:
            plan_json = Path(plan_json).read_text()
        print_progress("Scaffolding")
        plan_data = json.loads(plan_json)
        plan = _parse_plan(plan_data)
        target_path = Path(output_dir)

        if target_path.exists():
            if not force:
                print_error(f"{output_dir} already exists. Use --force to overwrite.")
                return 1
            shutil.rmtree(target_path)

        repo_dir = scaffold(plan, target_path)

        if not plan.supported:
            print_success(f"Scaffolded plan to {repo_dir} (unsupported stack — see PLAN.md)")
            return 0

        res = build_and_test(repo_dir)

        print_success(f"Scaffolded to {repo_dir}")
        if res.installed and res.tested:
            print_success("Build and tests passed")
            return 0
        else:
            print_error("Build or tests failed")
            print(res.output, file=sys.stderr)
            return 1

    except json.JSONDecodeError as e:
        print_error(f"Invalid plan JSON: {e}")
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return 1


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
        if target.exists():
            print(f"\n{output_dir} already exists.")
            overwrite = input("Overwrite? (y/n) → ").strip().lower()
            if overwrite != "y":
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
    except OSError as e:
        print_error(f"Could not write output: {e}")
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return 1


def answer_fn(questions: list[str]) -> list[str]:
    """Prompt user for answers to clarifying questions."""
    answers = []
    for i, q in enumerate(questions, 1):
        print(f"\n[Q{i}/{len(questions)}] {q}")
        answer = input("→ ").strip()
        answers.append(answer)
    return answers
