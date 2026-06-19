import pytest
from pathlib import Path
from app.prompts.manager import PromptManager

def test_prompt_manager_load():
    manager = PromptManager()
    assert "planner" in manager.prompts
    assert "extractor" in manager.prompts
    assert "synthesizer" in manager.prompts

def test_prompt_manager_get_prompt():
    manager = PromptManager()
    
    # Test planner system prompt (no arguments needed)
    sys_prompt = manager.get_prompt("planner", "system")
    assert "JSON" in sys_prompt
    
    # Test planner user prompt (requires topic and breadth)
    user_prompt = manager.get_prompt("planner", "user", topic="Quantum Computing", breadth=4)
    assert "Quantum Computing" in user_prompt
    assert "4" in user_prompt

def test_prompt_manager_missing_args():
    manager = PromptManager()
    with pytest.raises(KeyError):
        # Missing 'breadth' argument
        manager.get_prompt("planner", "user", topic="Quantum Computing")
