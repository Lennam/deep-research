import json
import re
from typing import Any

def parse_json_robustly(text: str) -> Any:
    """
    Robustly parses JSON from LLM output.
    Supports stripping markdown code fences (```json ... ```) and extracting JSON structures.
    """
    text = text.strip()
    
    # Strip markdown code block fences if present
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        text = match.group(1).strip()
        
    # Find the outer JSON boundaries (either curly braces or square brackets)
    first_brace = text.find('{')
    first_bracket = text.find('[')
    
    start_idx = -1
    if first_brace != -1 and first_bracket != -1:
        start_idx = min(first_brace, first_bracket)
    elif first_brace != -1:
        start_idx = first_brace
    elif first_bracket != -1:
        start_idx = first_bracket
        
    last_brace = text.rfind('}')
    last_bracket = text.rfind(']')
    
    end_idx = -1
    if last_brace != -1 and last_bracket != -1:
        end_idx = max(last_brace, last_bracket)
    elif last_brace != -1:
        end_idx = last_brace
    elif last_bracket != -1:
        end_idx = last_bracket
        
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        text = text[start_idx:end_idx+1]
        
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        # Fallback raw parsing or raise
        raise json.JSONDecodeError(f"Failed to parse robustified JSON. Text: {text[:200]}...", e.doc, e.pos)
