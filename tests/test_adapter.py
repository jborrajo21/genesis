from genesis.fakes import FakeAdapter
from genesis.adapter import Completion

def test_fake_asapter_returns_reply():
    assert FakeAdapter().complete([]) == Completion(text="ok")