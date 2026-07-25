from genesis.adapter import Completion
from genesis.fakes import FakeAdapter


def test_fake_asapter_returns_reply():
    assert FakeAdapter([Completion(text="ok")]).complete([]) == Completion(text="ok")
