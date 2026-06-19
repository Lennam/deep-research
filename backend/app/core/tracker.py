import time
import functools
from typing import Callable, Any
from app.core.state import ToolCallRecord

def track_tool_call(tool_name: str):
    """
    Decorator to wrap asynchronous methods that act as tools (e.g. search, scrape).
    Expects the target instance to have a `self.state` property containing a ResearchState.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs) -> Any:
            start_time = time.time()
            
            # Serialize arguments for logging
            serialized_args = {
                "args": [str(arg) for arg in args],
                "kwargs": {k: str(v) for k, v in kwargs.items()}
            }
            
            try:
                result = await func(self, *args, **kwargs)
                output_str = str(result)[:3000] # Truncate large outputs to save memory
                return result
            except Exception as e:
                output_str = f"Error: {e}"
                raise e
            finally:
                duration = time.time() - start_time
                if hasattr(self, "state") and self.state is not None:
                    self.state.tool_calls.append(ToolCallRecord(
                        tool_name=tool_name,
                        arguments=serialized_args,
                        output=output_str,
                        timestamp=start_time,
                        duration=duration
                    ))
        return wrapper
    return decorator
