# Deep Research Agent - Developer Agent Guidelines

This document provides essential repository facts, behavioral guidelines, constraints, and operational instructions for autonomous AI agents (like Cursor, Claude Code, or Antigravity) working in this repository.

---

## 1. Project Overview & Technology Stack

This project is an automated **Deep Research Agent** featuring a multi-agent backend architecture and a responsive glassmorphic frontend UI.

### Technology Stack
- **Language**: Python 3.11+ (Backend), JavaScript/TypeScript (Frontend)
- **Backend Web Framework**: FastAPI + Uvicorn
- **AI Agent Orchestration**: Custom lightweight asynchronous event loop (`AsyncResearchLoop`) with full observability (tool call tracing and LLM I/O logging).
- **Core LLM**: OpenAI API specification compatible models (e.g., GPT-4o-mini, or Zhipu AI GLM models via compatibility fallback)
- **Search Capabilities**: Tavily Web Search API & Academic API (arXiv & Semantic Scholar)
- **Scraping & Cleaning**: Jina Reader API with custom BeautifulSoup fallback
- **Frontend**: Vue 3 + Vite + TypeScript (with custom dark glassmorphic styling)

---

## 2. Directory Structure

```
.
├── backend/                  # Python backend application
│   ├── app/
│   │   ├── config.py         # Configuration settings (API Keys, Defaults)
│   │   ├── agents/           # Specialized AI Agent classes
│   │   │   ├── base.py
│   │   │   ├── planner.py
│   │   │   ├── scraper.py
│   │   │   ├── extractor.py
│   │   │   └── synthesizer.py
│   │   ├── core/             # Orchestration and state management
│   │   │   ├── loop.py       # Asynchronous research recursive loop
│   │   │   └── state.py      # Pydantic data state models
│   │   ├── prompts/          # Centralized prompts storage
│   │   │   ├── manager.py    # Prompts loading and interpolation
│   │   │   └── prompts.yaml  # System/User prompt definitions
│   │   ├── search/           # Search clients & routers
│   │   │   ├── tavily_client.py
│   │   │   ├── academic_client.py
│   │   │   └── router.py
│   │   └── utils/
│   ├── requirements.txt      # Project Python dependencies
│   ├── test_cli.py           # Command Line sandbox runner
│   └── tests/                # Unit & Integration tests
├── docs/                     # Design and specifications
│   ├── design-docs/
│   ├── exec-plans/
│   └── product-specs/
└── agents.md                 # This guide
```

---

## 3. Reference Specifications & Documentation

Refer to these documents for deep design context before modifying codebase areas:
- **General Plan**: [plan.md](docs/plan.md)
- **Backend Design**: [phase1_backend.md](docs/design-docs/phase1_backend.md)
- **Execution Plan**: [phase1_backend_exec.md](docs/exec-plans/phase1_backend_exec.md)
- **Specifications Index**: [README.md](docs/product-specs/README.md)
- **State Models Spec**: [state_models.md](docs/product-specs/state_models.md)
- **Multi-Agent Spec**: [multi_agents.md](docs/product-specs/multi_agents.md)
- **Async Event Loop Spec**: [async_loop.md](docs/product-specs/async_loop.md)
- **Observability Spec**: [logging_tracing.md](docs/product-specs/logging_tracing.md)

---

## 4. Key Constraints & Rules for AI Agents

When editing code, AI agents MUST respect the following boundaries:

### A. Centralized Prompt Management
- **Rule**: Never hardcode prompt strings inside Python Agent classes. All prompts must reside in [prompts.yaml](backend/app/prompts/prompts.yaml) and be accessed via `PromptManager`.
- **Brace Escaping**: YAML system/user prompt definitions containing curly braces `{}` (e.g., JSON schemas) **must write double curly braces `{{` and `}}`**. Otherwise, Python's `.format()` call will throw a `KeyError`.

### B. State Observability and Tracking
- **Rule**: Every tool execution must be recorded to the global `ResearchState` logs.
- Use the `@track_tool_call(tool_name)` decorator for all tool-like functions.
- Explicitly pass `state=self.state` during `GLMClient.chat_completion(...)` to ensure LLM token counts and inputs/outputs are tracked correctly inside `state.llm_logs`.

### C. Concurrency and Deduplication
- **Concurrency**: Use `asyncio.gather` for parallelizing sub-topic processing and parallel web-scraping to prevent execution latency.
- **Deduplication**: Ensure search queries and scraped URLs are checked against `state.search_history` and `self.scraped_urls` before invoking external APIs.

---

## 5. Setup & Operational Commands

AI agents should run these commands to set up the environment, run the sandbox, or execute tests.

### Local Development Environment Setup
```bash
# From repository root
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running the CLI Sandbox Runner
```bash
# Run deep research on a specific topic
python test_cli.py --topic "Your Research Topic" --depth 2 --breadth 2 --mode all
```
*Note: Make sure `OPENAI_API_KEY` and `TAVILY_API_KEY` are defined in `backend/.env` or as environment variables.*

### Running Automated Test Suite
Ensure the virtual environment is active, then run:
```bash
# Run all tests
PYTHONPATH=. pytest tests/

# Run individual test files
PYTHONPATH=. pytest tests/test_prompts.py
PYTHONPATH=. pytest tests/test_search.py
PYTHONPATH=. pytest tests/test_scraper_extractor.py
PYTHONPATH=. pytest tests/test_tracker.py
PYTHONPATH=. pytest tests/test_planner_synthesizer.py
PYTHONPATH=. pytest tests/test_loop.py
```

---

## 6. Commit and Code Integrity

- Ensure Pydantic types match precisely between backend schemas and frontend definitions.
- Before committing, run `pytest` to make sure there are no regressions.
- Keep commit messages concise, descriptive, and prefix them with appropriate scopes (e.g., `feat(backend): ...`, `fix(prompts): ...`).
