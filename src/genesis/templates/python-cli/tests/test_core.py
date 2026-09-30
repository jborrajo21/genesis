import pytest

from greetly.core import AppError, run


def test_run_without_a_target():
    assert "nothing to do" in run()


def test_run_with_a_target():
    assert "data.csv" in run("data.csv")


def test_blank_target_is_an_expected_failure():
    with pytest.raises(AppError):
        run("   ")
