import asyncio
import uuid
from typing import Dict, Tuple, Set, Optional
from app.core.state import ResearchState

class TaskManager:
    def __init__(self):
        # Structure: { task_id: (asyncio.Task, ResearchState, Set[asyncio.Queue]) }
        self.active_tasks: Dict[str, Tuple[Optional[asyncio.Task], ResearchState, Set[asyncio.Queue]]] = {}

    def create_task(self, state: ResearchState) -> str:
        task_id = str(uuid.uuid4())
        # Initialize an empty set of queues for this task
        self.active_tasks[task_id] = (None, state, set())
        return task_id

    def register_queue(self, task_id: str) -> asyncio.Queue:
        """Registers a queue for SSE streaming when a client connects."""
        if task_id not in self.active_tasks:
            raise KeyError("Task not found")
        
        task, state, queues = self.active_tasks[task_id]
        queue = asyncio.Queue()
        
        # Replay historical logs to the new client connection to solve race condition
        import time
        for log_msg in state.logs:
            queue.put_nowait({
                "event": "log",
                "data": {"message": log_msg, "timestamp": time.time()}
            })
            
        # Replay current status
        queue.put_nowait({
            "event": "state_update",
            "data": {
                "current_depth": state.current_depth,
                "sources_count": len(state.sources),
                "facts_count": len(state.extracted_facts)
            }
        })
        
        queues.add(queue)
        return queue

    def unregister_queue(self, task_id: str, queue: asyncio.Queue):
        """Unregisters and removes a queue when client disconnects to prevent memory leak."""
        if task_id in self.active_tasks:
            self.active_tasks[task_id][2].discard(queue)

    def publish_event(self, task_id: str, event_type: str, data: dict):
        """Publishes an event to all registered queues for a task."""
        if task_id not in self.active_tasks:
            return
        _, _, queues = self.active_tasks[task_id]
        payload = {"event": event_type, "data": data}
        for queue in queues:
            queue.put_nowait(payload)

    def associate_async_task(self, task_id: str, task: asyncio.Task):
        """Associates the running asyncio.Task object with the task_id."""
        if task_id in self.active_tasks:
            _, state, queues = self.active_tasks[task_id]
            self.active_tasks[task_id] = (task, state, queues)

    def get_state(self, task_id: str) -> Optional[ResearchState]:
        """Gets the ResearchState for a task_id."""
        if task_id in self.active_tasks:
            return self.active_tasks[task_id][1]
        return None

    async def cancel_task(self, task_id: str) -> bool:
        """Cancels the active asyncio.Task for the given task_id."""
        if task_id not in self.active_tasks:
            return False
        task, _, _ = self.active_tasks[task_id]
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            return True
        return False

    async def cancel_task_if_orphaned(self, task_id: str) -> bool:
        """Cancels the task if there are no active SSE listener queues remaining."""
        if task_id not in self.active_tasks:
            return False
        task, state, queues = self.active_tasks[task_id]
        if len(queues) == 0:
            print(f"[TaskManager] Task {task_id} is orphaned (0 queues). Cancelling background task.")
            return await self.cancel_task(task_id)
        return False

    def remove_task(self, task_id: str):
        """Removes the task from the manager after completion or error."""
        self.active_tasks.pop(task_id, None)

# Singleton instance
task_manager = TaskManager()
