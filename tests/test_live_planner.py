import os

import pytest

from genesis.adapter import Message
from genesis.anthropic_adapter import AnthropicAdapter
from genesis.planner import Planner


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="no ANTHROPIC_API_KEY set; live multi-tool agent test skipped",
)
def test_live_planner_round_returns_well_formed_result():
    planner = Planner(AnthropicAdapter(model="claude-haiku-4-5", max_tokens=1500))
    result = planner._round([Message(role="user", content="a todo CLI")])
    assert result.status in ("need_info", "ready")
    if result.status == "need_info":
        assert len(result.questions) > 0
        assert all(isinstance(q, str) for q in result.questions)
    else:
        assert result.plan is not None and result.plan.project_name
