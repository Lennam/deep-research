from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.llm import glm_client
from app.utils.vector_store import vector_store
from app.utils.db import get_report_by_id

router = APIRouter(prefix="/research", tags=["chat"])

class ChatRequest(BaseModel):
    task_id: str
    question: str

class ChatResponse(BaseModel):
    answer: str
    sources: list

@router.post("/chat", response_model=ChatResponse)
async def chat_with_research(request: ChatRequest):
    task_id = request.task_id.strip()
    question = request.question.strip()

    if not task_id or not question:
        raise HTTPException(status_code=400, detail="task_id and question are required")

    report_data = await get_report_by_id(task_id)
    if not report_data:
        raise HTTPException(status_code=404, detail=f"Research task with ID {task_id} not found")

    try:
        query_emb = await glm_client.get_embedding(question)
        hits = await vector_store.similarity_search(task_id, query_emb, k=5)
    except Exception as e:
        print(f"Chat embedding or similarity search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to query vector database: {str(e)}")

    if not hits:
        context = f"Report Content:\n{report_data.get('report_content', '')}"
        sources = []
    else:
        context_items = []
        sources = []
        for idx, hit in enumerate(hits):
            text = hit["text"]
            meta = hit.get("metadata") or {}
            url = meta.get("url") or ""
            title = meta.get("title") or "Unknown Source"
            hit_type = meta.get("type") or "chunk"
            
            context_items.append(f"[{idx+1}] [Type: {hit_type}] [Source: {title} ({url})]\nContent: {text}")
            if url and not any(s["url"] == url for s in sources):
                sources.append({"title": title, "url": url})
                
        context = "\n\n---\n\n".join(context_items)

    system_prompt = (
        "你是一个专业且严谨的科技与学术助手。请根据提供的研究上下文（包括爬取的文献分块或提取的事实要点），回答用户的提问。\n"
        "要求：\n"
        "1. 回答内容必须完全基于提供的研究上下文，不要捏造任何事实或外推没有的数据。\n"
        "2. 在阐述关键结论或数字时，请使用类似 [1]、[2] 的格式在行内（inline）引用支撑当前说法的上下文序号。\n"
        "3. 保持专业、中立、学术的语气。\n"
        "4. 回答语言使用中文。\n"
    )

    user_prompt = (
        f"用户提问: {question}\n\n"
        f"搜集到的研究上下文数据:\n"
        f"---\n"
        f"{context}\n"
        f"---\n\n"
        f"请根据上述上下文提供回答。"
    )

    try:
        answer = await glm_client.chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            agent_name="chat_assistant",
            prompt_name="chat_with_report"
        )
        return ChatResponse(answer=answer, sources=sources)
    except Exception as e:
        print(f"Error calling LLM for chat completion: {e}")
        raise HTTPException(status_code=500, detail=f"LLM completion failed: {str(e)}")
