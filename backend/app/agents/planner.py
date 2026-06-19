from app.prompts.manager import prompt_manager
from app.core.llm import glm_client, GLMClient
from app.utils.json_helper import parse_json_robustly
from app.core.tracker import track_tool_call
from typing import Any, List, Dict

class PlannerAgent:
    def __init__(self, client: GLMClient = None, state: Any = None):
        self.client = client or glm_client
        self.state = state

    @track_tool_call("planner_generate_initial_plan")
    async def generate_initial_plan(self, topic: str, breadth: int) -> Dict[str, Any]:
        """
        Analyzes the research topic and returns sub-topics with their search queries.
        """
        system_prompt = prompt_manager.get_prompt("planner", "system")
        user_prompt = prompt_manager.get_prompt(
            "planner", "user",
            topic=topic,
            breadth=breadth
        )

        try:
            response_text = await self.client.chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format="json",
                state=self.state,
                agent_name="planner",
                prompt_name="generate_plan"
            )
            data = parse_json_robustly(response_text)
            if not isinstance(data, dict) or "sub_topics" not in data:
                return {"sub_topics": []}
            return data
        except Exception as e:
            print(f"Error in PlannerAgent generate_initial_plan: {e}")
            return {"sub_topics": []}

    @track_tool_call("planner_refine_and_expand")
    async def refine_and_expand(self, topic: str, existing_facts: List[str]) -> List[str]:
        """
        Analyzes current facts gathered for a sub-topic, deciding if deeper queries are required.
        """
        if not existing_facts:
            return []

        system_prompt = prompt_manager.get_prompt("planner", "refine_system")
        user_prompt = prompt_manager.get_prompt(
            "planner", "refine_user",
            topic=topic,
            existing_facts="\n".join(f"- {fact}" for fact in existing_facts)
        )

        try:
            response_text = await self.client.chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format="json",
                state=self.state,
                agent_name="planner",
                prompt_name="refine_plan"
            )
            data = parse_json_robustly(response_text)
            if isinstance(data, dict):
                return data.get("search_queries", [])
            return []
        except Exception as e:
            print(f"Error in PlannerAgent refine_and_expand: {e}")
            return []
