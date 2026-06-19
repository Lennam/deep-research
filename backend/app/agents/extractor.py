from app.prompts.manager import prompt_manager
from app.core.llm import glm_client, GLMClient
from app.utils.json_helper import parse_json_robustly
from app.core.tracker import track_tool_call
from typing import Any

class ExtractorAgent:
    def __init__(self, client: GLMClient = None, state: Any = None):
        self.client = client or glm_client
        self.state = state

    @track_tool_call("extractor_extract")
    async def extract(self, sub_topic: str, query: str, raw_content: str) -> list:
        """
        Extracts key facts and evidence from raw content for a specific research sub-topic.
        """
        if not raw_content or not raw_content.strip():
            return []

        system_prompt = prompt_manager.get_prompt("extractor", "system")
        user_prompt = prompt_manager.get_prompt(
            "extractor", "user",
            sub_topic=sub_topic,
            query=query,
            raw_content=raw_content
        )

        try:
            response_text = await self.client.chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format="json",
                state=self.state,
                agent_name="extractor",
                prompt_name="extract_facts"
            )
            
            data = parse_json_robustly(response_text)
            if isinstance(data, dict):
                return data.get("facts", [])
            elif isinstance(data, list):
                return data
            return []
        except Exception as e:
            print(f"Error in ExtractorAgent: {e}")
            return []
