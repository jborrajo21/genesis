import pytest

from genesis.cli import main


@pytest.fixture
def spy(monkeypatch):
    """Replace the three commands with recorders. Returns a dict of what was called."""
    calls = {}

    def make(name):
        def recorder(*args):
            calls["name"], calls["args"] = name, args
            return 0

        return recorder

    for name in ("cmd_plan", "cmd_scaffold_file", "cmd_create"):
        monkeypatch.setattr(f"genesis.cli.{name}", make(name))
    return calls


@pytest.mark.parametrize("command", ["plan", "scaffold", "create"])
def test_help_exits_zero(command):
    with pytest.raises(SystemExit) as exc:
        main([command, "--help"])
    assert exc.value.code == 0


def test_plan_dispatches_with_defaults(spy):
    assert main(["plan", "a todo app"]) == 0
    assert spy["name"] == "cmd_plan"
    idea, adapter, model, output, max_rounds, max_tokens = spy["args"]
    assert idea == "a todo app"
    assert (adapter, model, output) == (None, None, None)
    assert (max_rounds, max_tokens) == (6, 10000)


def test_plan_dispatches_flags(spy):
    argv = [
        "plan",
        "a todo app",
        "--adapter",
        "ollama",
        "--model",
        "mistral",
        "--output",
        "p.json",
    ]
    assert main(argv) == 0
    idea, adapter, model, output, max_rounds, max_tokens = spy["args"]
    assert idea == "a todo app"
    assert (adapter, model, output) == ("ollama", "mistral", "p.json")
    assert (max_rounds, max_tokens) == (6, 10000)


def test_plan_tuning_flags_are_ints(spy):
    assert main(["plan", "x", "--max-rounds", "2", "--max-tokens", "500"]) == 0
    *_, max_rounds, max_tokens = spy["args"]
    assert (max_rounds, max_tokens) == (2, 500)


def test_scaffold_dispatches(spy):
    assert main(["scaffold", "plan.json", "out"]) == 0
    assert spy["name"] == "cmd_scaffold_file"
    assert spy["args"] == ("plan.json", "out", False)


def test_scaffold_force(spy):
    assert main(["scaffold", "plan.json", "out", "--force"]) == 0
    assert spy["args"] == ("plan.json", "out", True)


def test_scaffold_without_args_passes_none(spy):
    assert main(["scaffold"]) == 0
    assert spy["args"] == (None, None, False)


def test_create_dispatches(spy):
    argv = [
        "create",
        "a todo app",
        "out",
        "--adapter",
        "anthropic",
        "--model",
        "claude-haiku-4-5",
        "--output",
        "p.json",
        "--force",
        "--max-rounds",
        "3",
        "--max-tokens",
        "42",
    ]
    assert main(argv) == 0
    assert spy["name"] == "cmd_create"
    assert spy["args"] == (
        "a todo app",
        "out",
        "anthropic",
        "claude-haiku-4-5",
        "p.json",
        True,
        3,
        42,
    )


def test_create_defaults(spy):
    assert main(["create", "idea", "out"]) == 0
    assert spy["args"] == ("idea", "out", None, None, None, False, 6, 10000)


@pytest.mark.parametrize("argv", [[], ["nope"], ["plan", "--bogus"]])
def test_parse_errors_exit_two(argv):
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2
