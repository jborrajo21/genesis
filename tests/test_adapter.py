from genesis.adapter import Completion
from genesis.fakes import FakeAdapter


def test_fake_asapter_returns_reply():
    assert FakeAdapter().complete([]) == Completion(text="ok")
