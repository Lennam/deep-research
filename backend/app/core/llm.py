import asyncio
import time
from typing import Any
from zhipuai import ZhipuAI
from app.config import settings

class GLMClient:
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.ZHIPUAI_API_KEY
        self.model = model or settings.GLM_MODEL
        self.client = None
        if self.api_key and self.api_key != "your_zhipu_api_key_here":
            self.client = ZhipuAI(api_key=self.api_key)

    async def chat_completion(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        response_format: str = None,
        state: Any = None,
        agent_name: str = "agent",
        prompt_name: str = "prompt"
    ) -> str:
        """
        Calls Zhipu AI GLM model asynchronously and logs the inputs/outputs to the provided state.
        """
        if not self.client:
            raise ValueError("Zhipu AI API Key is not configured. Please set ZHIPUAI_API_KEY in .env.")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        start_time = time.time()

        def _call():
            params = {
                "model": self.model,
                "messages": messages,
            }
            if response_format == "json":
                params["response_format"] = {"type": "json_object"}
            
            response = self.client.chat.completions.create(**params)
            content = response.choices[0].message.content
            
            prompt_tokens = 0
            completion_tokens = 0
            if hasattr(response, "usage") and response.usage:
                prompt_tokens = getattr(response.usage, "prompt_tokens", 0)
                completion_tokens = getattr(response.usage, "completion_tokens", 0)
                
            return content, prompt_tokens, completion_tokens

        content, p_tokens, c_tokens = await asyncio.to_thread(_call)

        # Log results if state is provided
        if state is not None:
            from app.core.state import LLMIOLog
            state.llm_logs.append(LLMIOLog(
                agent_name=agent_name,
                prompt_name=prompt_name,
                llm_input=f"System:\n{system_prompt}\n\nUser:\n{user_prompt}",
                llm_output=content,
                timestamp=start_time,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens
            ))

        return content

# Singleton instance
glm_client = GLMClient()
