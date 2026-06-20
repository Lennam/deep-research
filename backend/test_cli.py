import asyncio
import argparse
import json
import os
from pathlib import Path
from app.config import settings
from app.core.state import ResearchState
from app.core.loop import AsyncResearchLoop

async def main():
    parser = argparse.ArgumentParser(description="Deep Research Agent CLI Runner")
    parser.add_argument("--topic", type=str, required=True, help="Research topic")
    parser.add_argument("--depth", type=int, default=settings.DEFAULT_MAX_DEPTH, help="Research recursion depth")
    parser.add_argument("--breadth", type=int, default=settings.DEFAULT_MAX_BREADTH, help="Search breadth")
    parser.add_argument("--mode", type=str, default="auto", choices=["auto", "web", "academic", "all"], help="Search mode")
    
    args = parser.parse_args()

    print("\n" + "="*50)
    print("   DEEP RESEARCH AGENT CLI RUNNER   ")
    print("="*50)
    print(f"Topic:   {args.topic}")
    print(f"Depth:   {args.depth}")
    print(f"Breadth: {args.breadth}")
    print(f"Mode:    {args.mode}")
    print("="*50 + "\n")

    # Verify environment keys are present
    has_openai = settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your_openai_api_key_here"
    if not settings.TAVILY_API_KEY or settings.TAVILY_API_KEY == "your_tavily_api_key_here":
        print("[Warning] TAVILY_API_KEY is not set. Real Web searches will fail.")

    # Initialize State
    state = ResearchState(
        topic=args.topic,
        max_depth=args.depth,
        max_breadth=args.breadth
    )

    # Initialize Loop
    loop = AsyncResearchLoop(
        state=state,
        search_mode=args.mode
    )

    # Start loop
    try:
        report = await loop.run()
        
        # Ensure output folder exists
        output_dir = Path(__file__).resolve().parent / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save Report
        report_path = output_dir / "report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n[Success] Markdown report saved to: {report_path}")
        
        # Save State JSON (containing all tool calls and LLM logs)
        state_path = output_dir / "state.json"
        
        # Custom dict extraction since sets and other structures are cleaned by pydantic
        state_dict = state.model_dump()
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, ensure_ascii=False, indent=2)
        print(f"[Success] Execution state logs saved to: {state_path}")
        
        print("\n" + "="*50)
        print("   RESEARCH COMPLETED SUCCESSFULLY   ")
        print("="*50 + "\n")

    except Exception as e:
        print(f"\n[Failure] Error occurred during research: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
