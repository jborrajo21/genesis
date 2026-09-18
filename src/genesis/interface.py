import sys
from pathlib import Path

from genesis.anthropic_adapter import SUPPORTED_MODELS as ANTHROPIC_MODELS
from genesis.errors import InputUnavailableError
from genesis.ollama_adapter import SUPPORTED_MODELS as OLLAMA_MODELS


def _prompt(message: str) -> str:
    """Read one line of interactive input. Raises InputUnavailableError at EOF."""
    try:
        return input(message).strip()
    except EOFError:
        raise InputUnavailableError(
            "Genesis needs interactive input here, but stdin is empty. "
            "Pass the values as arguments instead — see `genesis <command> --help`."
        ) from None


def answer_fn(questions: list[str]) -> list[str]:
    """Prompt user for answers to clarifying questions."""
    answers = []
    for i, q in enumerate(questions, 1):
        print(f"\n[Q{i}/{len(questions)}] {q}")
        answer = _prompt("→ ")
        answers.append(answer)
    return answers


def print_progress(msg: str) -> None:
    """Print a progress message."""
    print(f"\n→ {msg}...", end=" ", flush=True)


def print_success(msg: str) -> None:
    """Print a success message."""
    print(f"✓ {msg}")


def print_error(msg: str) -> None:
    """Print an error message to stderr."""
    print(f"✗ {msg}", file=sys.stderr)


def _confirm_overwrite(path: str) -> bool:
    """Prompt user for overwrite confirmation."""
    print(f"\n{path} already exists.")
    return _prompt("Overwrite? (y/n) → ").lower() == "y"


def _get_idea() -> str:
    """Prompt for idea if not provided."""
    print("\nWhat's your project idea?")
    return _prompt("→ ")


def _get_output_dir() -> str:
    """Prompt for output directory if not provided."""
    print("\nWhere should we scaffold it?")
    return _prompt("→ ")


def _get_json_path() -> str:
    """Prompt for plan json file path if not provided."""
    print("\nEnter your json plan's path?")
    return _prompt("→ ")


def _get_save_path() -> str:
    """Prompt for save path."""
    print("\nSave this plan to a file?")
    return _prompt("Path (leave blank to print instead) → ")


def _select_adapter() -> str:
    """Prompt user to select adapter if not provided."""
    print("\nChoose adapter:")
    print("1) Anthropic")
    print("2) Ollama")
    choice = _prompt("→ ")
    if choice == "1":
        return "anthropic"
    elif choice == "2":
        return "ollama"
    else:
        raise ValueError("Invalid choice")


def _select_model(adapter: str) -> str:
    """Prompt user to select model if not provided."""
    if adapter == "anthropic":
        models = ANTHROPIC_MODELS
    elif adapter == "ollama":
        models = OLLAMA_MODELS
    else:
        raise ValueError(f"Unknown adapter: {adapter}")

    print(f"\nChoose {adapter} model:")
    for i, model in enumerate(models, 1):
        print(f"{i}) {model}")
    print(f"{len(models) + 1}) Enter custom model name")

    choice = _prompt("→ ")
    try:
        idx = int(choice) - 1
        if idx == len(models):
            return _prompt("Model name: ")
        return models[idx]
    except (ValueError, IndexError):
        raise ValueError("Invalid choice")


def print_next_steps(repo_dir: Path) -> None:
    """Commands a user needs to start working in a freshly scaffolded repo."""
    print("\nRun:")
    print(f"  cd {repo_dir}")
    print("  python -m venv .venv && source .venv/bin/activate")
    print('  pip install -e ".[dev]"')
