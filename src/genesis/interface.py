import sys

from genesis.anthropic_adapter import SUPPORTED_MODELS as ANTHROPIC_MODELS

# from genesis.ollama_adapter import SUPPORTED_MODELS as OLLAMA_MODELS


def answer_fn(questions: list[str]) -> list[str]:
    """Prompt user for answers to clarifying questions."""
    answers = []
    for i, q in enumerate(questions, 1):
        print(f"\n[Q{i}/{len(questions)}] {q}")
        answer = input("→ ").strip()
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
    return input("Overwrite? (y/n) → ").strip().lower() == "y"


def _get_idea() -> str:
    """Prompt for idea if not provided."""
    print("\nWhat's your project idea?")
    return input("→ ").strip()


def _get_output_dir() -> str:
    """Prompt for output directory if not provided."""
    print("\nWhere should we scaffold it?")
    return input("→ ").strip()


def _get_json_path() -> str:
    """Prompt for plan json file path if not provided."""
    print("\nEnter your json plan's path?")
    return input("→ ").strip()


def _get_save_path() -> str:
    """Prompt for save path."""
    print("\nSave this plan to a file?")
    return input("Path (leave blank to print instead) → ").strip()


def _select_adapter() -> str:
    """Prompt user to select adapter if not provided."""
    print("\nChoose adapter:")
    print("1) Anthropic")
    print("2) Ollama")
    choice = input("→ ").strip()
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
    # elif adapter == "ollama":
    # models = OLLAMA_MODELS
    else:
        raise ValueError(f"Unknown adapter: {adapter}")

    print(f"\nChoose {adapter} model:")
    for i, model in enumerate(models, 1):
        print(f"{i}) {model}")
    print(f"{len(models) + 1}) Enter custom model name")

    choice = input("→ ").strip()
    try:
        idx = int(choice) - 1
        if idx == len(models):
            return input("Model name: ").strip()
        return models[idx]
    except (ValueError, IndexError):
        raise ValueError("Invalid choice")
