import subprocess
import sys
from pathlib import Path

SCRIPT = Path(sys.executable).parent / ("greetly.exe" if sys.platform == "win32" else "greetly")


def run_cli(*args):
    return subprocess.run([str(SCRIPT), *args], capture_output=True, text=True)


def test_help_exits_zero():
    res = run_cli("--help")
    assert res.returncode == 0
    assert "usage:" in res.stdout


def test_run_prints_to_stdout():
    res = run_cli("run", "data.csv")
    assert res.returncode == 0
    assert "data.csv" in res.stdout


def test_missing_subcommand_exits_two():
    assert run_cli().returncode == 2


def test_expected_failure_exits_one_and_writes_to_stderr():
    res = run_cli("run", "   ")
    assert res.returncode == 1
    assert res.stdout == ""
    assert "error:" in res.stderr
