import asyncio
import time
from typing import Any
from openai import OpenAI
from app.config import settings

class LLMClient:
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        # Determine API key, base URL, and model, resolving fallbacks
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = base_url or settings.OPENAI_BASE_URL
        self.model = model or settings.OPENAI_MODEL

        self.client = None
        if self.api_key and self.api_key != "your_openai_api_key_here":
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

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
        Calls the LLM using OpenAI specification asynchronously and logs the inputs/outputs to the provided state.
        """
        if not self.client:
            raise ValueError("OpenAI/Zhipu API Key is not configured. Please set OPENAI_API_KEY in .env.")

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
            content = response.choices[0].message.content or ""
            
            prompt_tokens = 0
            completion_tokens = 0
            if hasattr(response, "usage") and response.usage:
                prompt_tokens = getattr(response.usage, "prompt_tokens", 0)
                completion_tokens = getattr(response.usage, "completion_tokens", 0)
                
            return content, prompt_tokens, completion_tokens

        try:
            content, p_tokens, c_tokens = await asyncio.to_thread(_call)
        except Exception as e:
            from openai import APIConnectionError
            if isinstance(e, APIConnectionError):
                print(
                    "\n" + "!"*60 + "\n"
                    "LLM Connection Error detected!\n"
                    "If you are using Modelscope/Dashscope and have a proxy client running,\n"
                    "the request might be geoblocked (Modelscope blocks non-Chinese proxy IPs).\n"
                    "Please:\n"
                    " 1. Switch your proxy client to 'Rule (规则)' mode.\n"
                    " 2. Add 'modelscope.cn' and 'aliyuncs.com' to your DIRECT rules.\n"
                    " 3. Alternatively, configure standard OpenAI settings in backend/.env.\n"
                    + "!"*60 + "\n"
                )
            raise e

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
            
            # Phase 4: cost metrics update
            state.total_prompt_tokens += p_tokens
            state.total_completion_tokens += c_tokens
            
            # Cost calculation
            call_input_cost = p_tokens * settings.LLM_INPUT_COST_PER_TOKEN
            call_output_cost = c_tokens * settings.LLM_OUTPUT_COST_PER_TOKEN
            state.current_estimated_cost += (call_input_cost + call_output_cost)

        return content

# Backwards compatibility aliases
GLMClient = LLMClient
glm_client = LLMClient()
