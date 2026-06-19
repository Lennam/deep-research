from app.prompts.manager import prompt_manager
from app.core.llm import glm_client, GLMClient
from app.core.tracker import track_tool_call
from typing import Any

class SynthesizerAgent:
    def __init__(self, client: GLMClient = None, state: Any = None):
        self.client = client or glm_client
        self.state = state

    @track_tool_call("synthesizer_generate_report")
    async def generate_report(self, state: Any) -> str:
        """
        Compiles all collected sources and extracted facts, synthesizing the final Markdown research report.
        """
        # Format sources list
        sources_list = []
        for idx, s in enumerate(state.sources):
            title = s.get('title') or s.get('source_title') or 'Unknown'
            url = s.get('url') or s.get('source_url') or ''
            content = s.get('content') or ''
            sources_list.append(
                f"[{idx+1}] Title: {title}\n    URL: {url}\n    Summary: {content[:200]}"
            )
        sources_str = "\n".join(sources_list) if sources_list else "No sources found."

        # Format facts list
        facts_list = []
        for f in state.extracted_facts:
            facts_list.append(
                f"- [Source: {f.source_url}] Fact: {f.fact}\n  Evidence: {f.evidence}"
            )
        facts_str = "\n".join(facts_list) if facts_list else "No facts extracted."

        system_prompt = prompt_manager.get_prompt("synthesizer", "system")
        user_prompt = prompt_manager.get_prompt(
            "synthesizer", "user",
            topic=state.topic,
            sources=sources_str,
            facts=facts_str
        )

        try:
            report_markdown = await self.client.chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                state=self.state,
                agent_name="synthesizer",
                prompt_name="write_report"
            )
            return report_markdown
        except Exception as e:
            print(f"Error in SynthesizerAgent: {e}")
            return f"# Research Report: {state.topic}\n\nAn error occurred during report synthesis: {e}"
