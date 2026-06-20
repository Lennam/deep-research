export interface ToolCallRecord {
  tool_name: string;
  arguments: Record<string, any>;
  output: string;
  timestamp: number;
  duration: number;
}

export interface LLMIOLog {
  agent_name: string;
  prompt_name: string;
  llm_input: string;
  llm_output: string;
  prompt_tokens: number;
  completion_tokens: number;
  timestamp: number;
}

export interface FactNode {
  fact: string;
  evidence: string;
  source_url: string;
  source_title: string;
  sub_topic: string;
}

export interface ResearchState {
  topic: string;
  max_depth: number;
  max_breadth: number;
  current_depth: number;
  sources: Array<{ url: string; title: string; snippet?: string }>;
  extracted_facts: FactNode[];
  search_history: string[];
  tool_calls: ToolCallRecord[];
  llm_logs: LLMIOLog[];
  logs: string[];
}

export interface LogEvent {
  message: string;
  timestamp: number;
}

export interface StateUpdateEvent {
  current_depth: number;
  sources_count: number;
  facts_count: number;
}
