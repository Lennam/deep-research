from app.prompts.manager import prompt_manager
from app.core.llm import glm_client, GLMClient
from app.core.tracker import track_tool_call
from app.utils.json_helper import parse_json_robustly
from app.utils.vector_store import vector_store
from typing import Any

class SynthesizerAgent:
    def __init__(self, client: GLMClient = None, state: Any = None):
        self.client = client or glm_client
        self.state = state

    @track_tool_call("synthesizer_generate_report")
    async def generate_report(self, state: Any) -> str:
        """
        Compiles all collected sources and extracted facts, synthesizing the final Markdown research report.
        Uses chapter-by-chapter incremental RAG synthesis.
        """
        # Step 1: Format global sources list for indexing stable references
        sources_list = []
        for idx, s in enumerate(state.sources):
            title = s.get('title') or s.get('source_title') or 'Unknown'
            url = s.get('url') or s.get('source_url') or ''
            content = s.get('content') or ''
            sources_list.append(
                f"[{idx+1}] Title: {title}\n    URL: {url}\n    Summary: {content[:200]}"
            )
        sources_str = "\n".join(sources_list) if sources_list else "No sources found."

        # Step 2: Extract all sub-topics titles to feed the planner
        sub_topics_list = list(set([f.sub_topic for f in state.extracted_facts if f.sub_topic]))
        sub_topics_str = ", ".join(sub_topics_list) if sub_topics_list else state.topic

        # Step 3: Generate the outline / chapters
        print("[Synthesizer] Generating report outline...")
        outline_system = prompt_manager.get_prompt("synthesizer", "outline_system")
        outline_user = prompt_manager.get_prompt(
            "synthesizer", "outline_user",
            topic=state.topic,
            sub_topics=sub_topics_str
        )

        try:
            response_text = await self.client.chat_completion(
                system_prompt=outline_system,
                user_prompt=outline_user,
                response_format="json",
                state=self.state,
                agent_name="synthesizer",
                prompt_name="generate_outline"
            )
            outline_data = parse_json_robustly(response_text)
            chapters = outline_data.get("chapters", [])
        except Exception as e:
            print(f"Error generating outline: {e}")
            chapters = []

        # If outline generation failed, fallback to a single-pass generation
        if not chapters:
            print("[Synthesizer] Outline generation failed. Falling back to single-pass report generation.")
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
            return await self.client.chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                state=self.state,
                agent_name="synthesizer",
                prompt_name="write_report_single_pass"
            )

        # Step 4: Generate each chapter incrementally using RAG
        report_sections = []
        report_sections.append(f"# {state.topic}\n")
        report_sections.append("## 前言\n本报告基于自动化深度研究智能体抓取的海量学术文献与互联网实时资讯，进行多源数据交叉验证和事实融合后整理合成。\n")

        print(f"[Synthesizer] Outline generated. Starting synthesis of {len(chapters)} chapters...")
        for idx, ch in enumerate(chapters):
            ch_title = ch.get("title", f"第 {idx+1} 章节")
            ch_desc = ch.get("description", "")
            print(f"[Synthesizer] Writing chapter {idx+1}/{len(chapters)}: {ch_title}...")

            # Semantic retrieval for the chapter context
            chapter_query = f"{ch_title}: {ch_desc}"
            try:
                query_emb = await self.client.get_embedding(chapter_query)
                hits = await vector_store.similarity_search(state.task_id, query_emb, k=20)
            except Exception as e:
                print(f"Retrieval embedding failed for chapter: {e}")
                hits = []

            # Format chapter facts
            relevant_facts = []
            for hit in hits:
                meta = hit.get("metadata") or {}
                if meta.get("type") == "fact":
                    fact_text = hit["text"]
                    url = meta.get("url") or ""
                    relevant_facts.append(f"- [Source: {url}] Fact: {fact_text}")

            # Fallback to local facts if similarity hits are too few
            if len(relevant_facts) < 3:
                for f in state.extracted_facts:
                    relevant_facts.append(f"- [Source: {f.source_url}] Fact: {f.fact}")

            facts_str = "\n".join(relevant_facts) if relevant_facts else "No relevant facts found."

            # Generate the chapter content
            chapter_system = prompt_manager.get_prompt("synthesizer", "chapter_system")
            chapter_user = prompt_manager.get_prompt(
                "synthesizer", "chapter_user",
                topic=state.topic,
                chapter_title=ch_title,
                chapter_description=ch_desc,
                sources=sources_str,
                facts=facts_str
            )

            try:
                chapter_content = await self.client.chat_completion(
                    system_prompt=chapter_system,
                    user_prompt=chapter_user,
                    state=self.state,
                    agent_name="synthesizer",
                    prompt_name=f"write_chapter_{idx+1}"
                )
                report_sections.append(chapter_content + "\n")
            except Exception as e:
                print(f"Error synthesizing chapter {ch_title}: {e}")
                report_sections.append(f"## {ch_title}\n\n*由于系统异常，该章节生成失败: {e}*\n")

        # Step 5: Append global bibliography / references section
        report_sections.append("## 参考文献与数据源\n")
        for idx, s in enumerate(state.sources):
            title = s.get('title') or s.get('source_title') or 'Unknown'
            url = s.get('url') or s.get('source_url') or ''
            report_sections.append(f"- [{idx+1}] **{title}**: [访问链接]({url})\n")

        return "\n".join(report_sections)
