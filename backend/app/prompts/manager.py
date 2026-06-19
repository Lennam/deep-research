import yaml
from pathlib import Path
from typing import Dict, Any

class PromptManager:
    def __init__(self, filepath: Path = None):
        if filepath is None:
            filepath = Path(__file__).resolve().parent / "prompts.yaml"
        self.filepath = filepath
        self.prompts: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Loads prompt configurations from YAML file."""
        if not self.filepath.exists():
            raise FileNotFoundError(f"Prompts file not found at {self.filepath}")
        
        with open(self.filepath, "r", encoding="utf-8") as f:
            self.prompts = yaml.safe_load(f) or {}

    def get_prompt(self, agent_name: str, prompt_type: str, **kwargs) -> str:
        """
        Retrieves and formats a prompt template.
        
        Args:
            agent_name: Name of the agent (e.g. 'planner', 'extractor', 'synthesizer')
            prompt_type: Type of the prompt (e.g. 'system', 'user', 'refine_system')
            kwargs: Variables to format the template with
        
        Returns:
            The formatted prompt string
        """
        agent_prompts = self.prompts.get(agent_name)
        if not agent_prompts:
            raise KeyError(f"Agent '{agent_name}' not found in prompts config.")
            
        template = agent_prompts.get(prompt_type)
        if template is None:
            raise KeyError(f"Prompt type '{prompt_type}' not found for agent '{agent_name}'.")

        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise KeyError(f"Missing required parameter {e} for prompt {agent_name}.{prompt_type}. Available keys: {list(kwargs.keys())}")

# Singleton instance
prompt_manager = PromptManager()
