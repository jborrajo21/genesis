import os

import pytest

from genesis.agent import Agent
from genesis.anthropic_adapter import AnthropicAdapter
from genesis.tools import ToolRegistry, add_tool, multiply_tool


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="no ANTHROPIC_API_KEY set; live multi-tool agent test skipped",
)
def test_agent_uses_multiple_tools_live():
    agent = Agent(
        AnthropicAdapter(model="claude-haiku-4-5", max_tokens=300),
        ToolRegistry([add_tool, multiply_tool]),
        max_turns=5,
    )
    result = agent.run(
        "What is 2 plus 3, and what is 4 times 5? "
        "Use the add and multiply tools for the calculations."
    )
    assert result.stop_reason == "done"
    assert {"add", "multiply"} <= {c.name for c in result.tool_calls}
