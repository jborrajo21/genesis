from greetly.core import greet


def test_greet():
    assert greet("Javier") == "Hello, Javier!"
