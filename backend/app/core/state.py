from pydantic import BaseModel, Field
from typing import List, Dict, Any

class ToolCallRecord(BaseModel):
    """Record of an executed tool (like search or scraping)."""
    tool_name: str
    arguments: Dict[str, Any]
    output: str
    timestamp: float
    duration: float

class LLMIOLog(BaseModel):
    """Log of a model completion call."""
    agent_name: str
    prompt_name: str
    llm_input: str  # Full query text sent
    llm_output: str # Raw model response
    timestamp: float
    prompt_tokens: int = 0
    completion_tokens: int = 0

class FactNode(BaseModel):
    """Extracted atomic fact with its source and evidence."""
    fact: str
    evidence: str
    source_url: str
    source_title: str
    sub_topic: str

class ResearchState(BaseModel):
    """Global state of the deep research process."""
    task_id: str = ""
    topic: str
    max_depth: int
    max_breadth: int
    current_depth: int = 0
    
    # Results
    sources: List[Dict[str, Any]] = Field(default_factory=list)      # [{title, url, content}]
    extracted_facts: List[FactNode] = Field(default_factory=list)     # List of FactNode
    search_history: List[str] = Field(default_factory=list)           # List of searched queries
    
    # Trace & Logs
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    llm_logs: List[LLMIOLog] = Field(default_factory=list)
    logs: List[str] = Field(default_factory=list)                     # Execution step logs

    # Phase 4 Cost & Budget tracking
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_search_calls: int = 0
    current_estimated_cost: float = 0.0
    max_cost_budget: float = 1.0
    circuit_breaker_triggered: bool = False
