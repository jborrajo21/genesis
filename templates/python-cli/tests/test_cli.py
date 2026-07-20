import subprocess
import sys


def test_cli_greet():
    res = subprocess.run(
        [sys.executable, "-m", "greetly", "greet", "Javier"], capture_output=True, text=True
    )
    assert res.returncode == 0
    assert res.stdout == "Hello, Javier!\n"
