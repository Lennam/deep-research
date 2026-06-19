import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.state import ResearchState
from app.core.loop import AsyncResearchLoop

@pytest.mark.asyncio
async def test_research_loop_end_to_end():
    # Setup mock state
    state = ResearchState(topic="Artificial General Intelligence", max_depth=2, max_breadth=2)
    
    # Call 1: initial plan (returns JSON plan with 1 sub-topic, 2 queries)
    initial_plan_json = """
    {
      "sub_topics": [
        {
          "title": "AGI Definition",
          "reason": "Clarifying concepts",
          "search_queries": ["what is AGI", "AGI criteria"]
        }
      ]
    }
    """
    
    # Call 2: extract facts for query 1 "what is AGI"
    extracted_facts_json_1 = """
    {
      "facts": [
        {"fact": "AGI stands for Artificial General Intelligence", "evidence": "Intro section"}
      ]
    }
    """
    # Call 3: extract facts for query 2 "AGI criteria"
    extracted_facts_json_2 = """
    {
      "facts": [
        {"fact": "AGI requires reasoning ability", "evidence": "Section 2"}
      ]
    }
    """
    
    # Call 4: refine plan (depth 1 -> depth 2 refinement)
    refined_plan_json = """
    {
      "search_queries": ["AGI vs narrow AI"]
    }
    """
    
    # Call 5: extract facts for query 3 "AGI vs narrow AI" (depth 2)
    extracted_facts_json_3 = """
    {
      "facts": [
        {"fact": "Narrow AI is task specific", "evidence": "Summary"}
      ]
    }
    """
    
    # Call 6: report synthesis
    report_markdown = "# AGI Research Report\n\nGenerated AGI details."
    
    contents = [
        initial_plan_json,         # 1. generate plan
        extracted_facts_json_1,    # 2. extract fact for query 1
        extracted_facts_json_2,    # 3. extract fact for query 2
        refined_plan_json,         # 4. refine plan (depth 1)
        extracted_facts_json_3,    # 5. extract fact for query 3
        report_markdown            # 6. write final report
    ]
    
    # Create synchronous MagicMock for the Zhipu completions API
    mock_responses = []
    for content in contents:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=content))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=20)
        mock_responses.append(mock_response)
        
    mock_create = MagicMock()
    mock_create.side_effect = mock_responses
    
    # Mock search client returning different URLs per query
    async def mock_search(query, max_results, mode=None):
        if "what is AGI" in query:
            return [{"title": "AGI Paper 1", "url": "https://agi.com/1", "content": "Intro C1"}]
        elif "AGI criteria" in query:
            return [{"title": "AGI Paper 2", "url": "https://agi.com/2", "content": "Intro C2"}]
        elif "AGI vs narrow AI" in query:
            return [{"title": "AGI Paper 3", "url": "https://agi.com/3", "content": "Intro C3"}]
        return []
    
    # Mock scraper returning content
    mock_scraped_text = "Detailed text description of AGI details."
    
    # Construct research loop
    loop = AsyncResearchLoop(
        state=state, 
        glm_key="dummy_key", 
        tavily_key="dummy_key",
        search_mode="auto"
    )
    
    # Inject mock completions create method to loop's shared client
    loop.planner.client.client.chat.completions.create = mock_create
    
    # Patch searcher and scraper
    with patch.object(loop.search_router, "search", AsyncMock(side_effect=mock_search)) as patch_search, \
         patch.object(loop.scraper, "scrape", AsyncMock(return_value=mock_scraped_text)) as patch_scrape:
         
         report = await loop.run()
         
         # Assert final report matches
         assert report == report_markdown
         
         # Assert searches occurred
         assert patch_search.call_count == 3
         
         # Assert facts extracted
         assert len(state.extracted_facts) == 3
         assert state.extracted_facts[0].fact == "AGI stands for Artificial General Intelligence"
         assert state.extracted_facts[0].source_url == "https://agi.com/1"
         assert state.extracted_facts[1].fact == "AGI requires reasoning ability"
         assert state.extracted_facts[2].fact == "Narrow AI is task specific"
         
         # Assert sources listed (3 unique sources)
         assert len(state.sources) == 3
         assert state.sources[0]["url"] == "https://agi.com/1"
         assert state.sources[1]["url"] == "https://agi.com/2"
         assert state.sources[2]["url"] == "https://agi.com/3"
         
         # Assert search history recorded
         assert "what is AGI" in state.search_history
         assert "AGI criteria" in state.search_history
         assert "AGI vs narrow AI" in state.search_history
         
         # Assert depth tracking
         assert state.current_depth == 2
         
         # Check tool calls logging
         tool_names = [tc.tool_name for tc in state.tool_calls]
         assert "planner_generate_initial_plan" in tool_names
         assert "extractor_extract" in tool_names
         assert "planner_refine_and_expand" in tool_names
         assert "synthesizer_generate_report" in tool_names
         
         # Check LLM I/O logs
         assert len(state.llm_logs) == 6
         assert state.llm_logs[0].agent_name == "planner"
         assert state.llm_logs[0].prompt_name == "generate_plan"
         assert state.llm_logs[-1].agent_name == "synthesizer"
         assert state.llm_logs[-1].prompt_name == "write_report"
         assert state.llm_logs[0].prompt_tokens == 10
         assert state.llm_logs[0].completion_tokens == 20
