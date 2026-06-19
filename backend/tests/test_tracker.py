import pytest
import time
from unittest.mock import AsyncMock, MagicMock
from app.core.state import ResearchState
from app.core.tracker import track_tool_call
from app.core.llm import GLMClient

class DummyAgent:
    def __init__(self, state):
        self.state = state

    @track_tool_call("dummy_tool")
    async def run_tool(self, input_val: str) -> str:
        # Simulate some asynchronous work
        return f"Processed: {input_val}"


@pytest.mark.asyncio
async def test_tool_call_tracking():
    state = ResearchState(topic="Test Topic", max_depth=1, max_breadth=1)
    agent = DummyAgent(state)
    
    result = await agent.run_tool("hello tracker")
    
    assert result == "Processed: hello tracker"
    assert len(state.tool_calls) == 1
    
    record = state.tool_calls[0]
    assert record.tool_name == "dummy_tool"
    assert record.arguments["args"] == ["hello tracker"]
    assert record.output == "Processed: hello tracker"
    assert record.duration > 0


@pytest.mark.asyncio
async def test_llm_logging():
    state = ResearchState(topic="Test Topic", max_depth=1, max_breadth=1)
    
    # Mock zhipu SDK
    mock_sdk_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="LLM Answer Content"))]
    
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 10
    mock_usage.completion_tokens = 20
    mock_response.usage = mock_usage
    
    mock_sdk_client.chat.completions.create.return_value = mock_response
    
    # Instantiate client with mock sdk client
    client = GLMClient(api_key="dummy_key", model="glm-mock")
    client.client = mock_sdk_client
    
    response = await client.chat_completion(
        system_prompt="You are a helper",
        user_prompt="Explain tracking",
        state=state,
        agent_name="tester",
        prompt_name="test_prompt"
    )
    
    assert response == "LLM Answer Content"
    assert len(state.llm_logs) == 1
    
    log = state.llm_logs[0]
    assert log.agent_name == "tester"
    assert log.prompt_name == "test_prompt"
    assert "Explain tracking" in log.llm_input
    assert log.llm_output == "LLM Answer Content"
    assert log.prompt_tokens == 10
    assert log.completion_tokens == 20
