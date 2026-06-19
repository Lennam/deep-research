import pytest
from unittest.mock import AsyncMock
from app.agents.planner import PlannerAgent
from app.agents.synthesizer import SynthesizerAgent
from app.core.state import ResearchState, FactNode

@pytest.mark.asyncio
async def test_planner_initial_plan():
    mock_client = AsyncMock()
    mock_client.chat_completion.return_value = """
    {
      "sub_topics": [
        {
          "title": "Quantum Error Correction",
          "reason": "Important for fault tolerance",
          "search_queries": ["QEC codes", "surface codes"]
        }
      ]
    }
    """
    state = ResearchState(topic="Quantum computing", max_depth=1, max_breadth=1)
    planner = PlannerAgent(client=mock_client, state=state)
    
    plan = await planner.generate_initial_plan("Quantum computing", breadth=1)
    
    assert "sub_topics" in plan
    assert len(plan["sub_topics"]) == 1
    assert plan["sub_topics"][0]["title"] == "Quantum Error Correction"
    assert plan["sub_topics"][0]["search_queries"] == ["QEC codes", "surface codes"]
    
    assert len(state.tool_calls) == 1
    assert state.tool_calls[0].tool_name == "planner_generate_initial_plan"


@pytest.mark.asyncio
async def test_planner_refine_and_expand():
    mock_client = AsyncMock()
    mock_client.chat_completion.return_value = """
    {
      "search_queries": ["topological codes", "color codes"]
    }
    """
    state = ResearchState(topic="Quantum computing", max_depth=1, max_breadth=1)
    planner = PlannerAgent(client=mock_client, state=state)
    
    queries = await planner.refine_and_expand("Quantum Error Correction", ["Surface codes are 2D"])
    
    assert len(queries) == 2
    assert "topological codes" in queries
    assert len(state.tool_calls) == 1
    assert state.tool_calls[0].tool_name == "planner_refine_and_expand"


@pytest.mark.asyncio
async def test_synthesizer_generate_report():
    mock_client = AsyncMock()
    mock_client.chat_completion.return_value = "# Final Research Report\n\n- Quantum computing is scaling."
    
    state = ResearchState(topic="Quantum scaling", max_depth=1, max_breadth=1)
    state.sources = [
        {"title": "Paper A", "url": "https://arxiv.org/1", "content": "Abstract of paper 1"}
    ]
    state.extracted_facts = [
        FactNode(
            fact="Sycamore has 53 qubits",
            evidence="Page 3",
            source_url="https://arxiv.org/1",
            source_title="Paper A",
            sub_topic="Hardware scaling"
        )
    ]
    
    synthesizer = SynthesizerAgent(client=mock_client, state=state)
    report = await synthesizer.generate_report(state)
    
    assert "Final Research Report" in report
    mock_client.chat_completion.assert_called_once()
    assert len(state.tool_calls) == 1
    assert state.tool_calls[0].tool_name == "synthesizer_generate_report"
