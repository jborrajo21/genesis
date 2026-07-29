from genesis.adapter import Completion, ToolCall
from genesis.agent import Agent
from genesis.fakes import FakeAdapter
from genesis.tools import ToolRegistry, add_tool


def test_agent_runs_a_tool_then_answers():
    fake = FakeAdapter(
        [
            Completion(
                text="", tool_calls=[ToolCall(id="c1", name="add", arguments={"a": 2, "b": 3})]
            ),
            Completion(text="The answer is 5"),
        ]
    )
    agent = Agent(fake, ToolRegistry([add_tool]))
    result = agent.run("what is 2+3?")
    assert result.text == "The answer is 5"
    assert result.stop_reason == "done"
    assert any(m.role == "tool" and m.content == "5" for m in fake.calls[1])


def test_agent_stops_at_max_turns():
    tool_req = Completion(
        text="", tool_calls=[ToolCall(id="c", name="add", arguments={"a": 1, "b": 1})]
    )
    fake = FakeAdapter([tool_req, tool_req])
    agent = Agent(fake, ToolRegistry([add_tool]), max_turns=2)
    assert agent.run("loop forever").stop_reason == "max_turns"


def test_agent_stops_at_budget():
    fake = FakeAdapter(
        [
            Completion(
                text="",
                tool_calls=[ToolCall(id="c", name="add", arguments={"a": 1, "b": 1})],
                usage=1000,
            )
        ]
    )
    agent = Agent(fake, ToolRegistry([add_tool]), token_budget=100)
    assert agent.run("expensive").stop_reason == "budget"
