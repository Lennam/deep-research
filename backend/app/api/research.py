import asyncio
import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from app.config import settings
from app.core.state import ResearchState
from app.core.loop import AsyncResearchLoop
from app.core.manager import task_manager
from app.utils.db import save_report, get_report_by_id

router = APIRouter(prefix="/research", tags=["research"])

class ResearchRequest(BaseModel):
    topic: str
    max_depth: Optional[int] = None
    max_breadth: Optional[int] = None
    search_mode: str = "auto" # "auto", "web", "academic", "all"
    max_cost_budget: Optional[float] = None

class ResearchStartResponse(BaseModel):
    task_id: str
    status: str
    message: str

async def run_research_background(task_id: str, loop_instance: AsyncResearchLoop):
    try:
        # Run the core research loop
        report = await loop_instance.run()
        
        # Save the completed report to the SQLite database
        state_dict = loop_instance.state.model_dump()
        await save_report(
            report_id=task_id,
            topic=loop_instance.state.topic,
            max_depth=loop_instance.state.max_depth,
            max_breadth=loop_instance.state.max_breadth,
            report_content=report,
            state_dict=state_dict,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        # Notify clients that the task is complete
        task_manager.publish_event(task_id, "complete", {"report_id": task_id, "report": report})
    except asyncio.CancelledError:
        # Task was aborted by user
        loop_instance.state.logs.append("研究任务已被用户中止。")
        task_manager.publish_event(task_id, "error", {"message": "研究任务已被用户中止。"})
        # Save the partial state to database if cancelled
        try:
            await save_report(
                report_id=task_id,
                topic=loop_instance.state.topic,
                max_depth=loop_instance.state.max_depth,
                max_breadth=loop_instance.state.max_breadth,
                report_content="# Research Cancelled\n\nThe research task was cancelled by user before completion.",
                state_dict=loop_instance.state.model_dump(),
                created_at=datetime.now(timezone.utc).isoformat()
            )
        except Exception as db_err:
            print(f"[Research Background] Failed to save cancelled state: {db_err}")
    except Exception as e:
        # Log generic errors
        import traceback
        traceback.print_exc()
        loop_instance.state.logs.append(f"任务执行出错: {str(e)}")
        task_manager.publish_event(task_id, "error", {"message": f"任务执行出错: {str(e)}"})
        try:
            await save_report(
                report_id=task_id,
                topic=loop_instance.state.topic,
                max_depth=loop_instance.state.max_depth,
                max_breadth=loop_instance.state.max_breadth,
                report_content=f"# Research Failed\n\nAn error occurred: {str(e)}",
                state_dict=loop_instance.state.model_dump(),
                created_at=datetime.now(timezone.utc).isoformat()
            )
        except Exception as db_err:
            print(f"[Research Background] Failed to save error state: {db_err}")
    finally:
        # Clean up task
        task_manager.remove_task(task_id)

@router.post("/start", response_model=ResearchStartResponse)
async def start_research(request: ResearchRequest):
    topic = request.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic cannot be empty")
        
    depth = request.max_depth if request.max_depth is not None else settings.DEFAULT_MAX_DEPTH
    breadth = request.max_breadth if request.max_breadth is not None else settings.DEFAULT_MAX_BREADTH
    budget = request.max_cost_budget if request.max_cost_budget is not None else settings.DEFAULT_MAX_COST_BUDGET
    
    # Initialize Research State
    state = ResearchState(
        topic=topic,
        max_depth=depth,
        max_breadth=breadth,
        max_cost_budget=budget
    )
    
    # Generate a task ID
    task_id = task_manager.create_task(state)
    state.task_id = task_id
    
    # Set up event callback for loop log publishing
    def on_event_callback(event_type: str, data: dict):
        task_manager.publish_event(task_id, event_type, data)
        
    # Initialize Loop with callback
    loop_instance = AsyncResearchLoop(
        state=state,
        search_mode=request.search_mode,
        on_event=on_event_callback
    )
    
    # Launch research loop in the background
    background_task = asyncio.create_task(run_research_background(task_id, loop_instance))
    task_manager.associate_async_task(task_id, background_task)
    
    return ResearchStartResponse(
        task_id=task_id,
        status="running",
        message="研究任务已成功在后台启动"
    )

from fastapi import Request

@router.get("/stream/{task_id}")
async def stream_research_events(task_id: str, request: Request):
    async def event_generator():
        import time
        try:
            queue = task_manager.register_queue(task_id)
        except KeyError:
            # If the task is already finished and removed from active memory, check SQLite
            report_data = await get_report_by_id(task_id)
            if report_data:
                # Replay all logs from historical database to help clients catch up
                state_json = report_data.get("state_json", {})
                history_logs = state_json.get("logs", [])
                for log_msg in history_logs:
                    yield f"event: log\ndata: {json.dumps({'message': log_msg, 'timestamp': time.time()}, ensure_ascii=False)}\n\n"
                
                # Check if it was cancelled or failed
                if "已被用户中止" in "".join(history_logs):
                    yield f"event: error\ndata: {json.dumps({'message': '研究任务已被用户中止。'}, ensure_ascii=False)}\n\n"
                elif "任务执行出错" in "".join(history_logs):
                    yield f"event: error\ndata: {json.dumps({'message': '任务执行出错。'}, ensure_ascii=False)}\n\n"
                else:
                    yield f"event: complete\ndata: {json.dumps({'report_id': task_id, 'report': report_data['report_content']}, ensure_ascii=False)}\n\n"
            else:
                yield f"event: error\ndata: {json.dumps({'message': 'Task not found or already finished'}, ensure_ascii=False)}\n\n"
            return

        try:
            # Stream logs and state updates to SSE client
            while True:
                if await request.is_disconnected():
                    print(f"[SSE Connection] Client disconnected for task {task_id}")
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
                    
                    if event["event"] in ("complete", "error"):
                        break
                except asyncio.TimeoutError:
                    # Connection keep-alive heartbeat
                    yield ": heartbeat\n\n"
        finally:
            task_manager.unregister_queue(task_id, queue)
            # Phase 4: Auto-cancel background task if orphaned
            await task_manager.cancel_task_if_orphaned(task_id)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/stop/{task_id}")
async def stop_research(task_id: str):
    cancelled = await task_manager.cancel_task(task_id)
    if cancelled:
        return {
            "task_id": task_id,
            "status": "stopped",
            "message": "研究任务已成功被中止"
        }
    else:
        # Check if task id is simply a past task
        report_data = await get_report_by_id(task_id)
        if report_data:
            return {
                "task_id": task_id,
                "status": "completed",
                "message": "研究任务已在之前正常完成"
            }
        else:
            raise HTTPException(status_code=404, detail="Active research task not found")
