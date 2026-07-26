from genesis.tools import ToolRegistry, add_tool


def test_direct_run():
    add_tool.func(2, 3) == "5"


def test_dispatched_run():
    assert ToolRegistry([add_tool]).run("add", {"a": 2, "b": 3}) == "5"
