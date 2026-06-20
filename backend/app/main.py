import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.research import router as research_router
from app.api.reports import router as reports_router
from app.utils.db import init_db

# Configure simple logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize the SQLite database on startup
    logger.info("Initializing database...")
    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    yield
    # Cleanup actions on shutdown (if any) can be added here
    logger.info("Shutting down API service...")

app = FastAPI(
    title="Deep Research Agent API",
    description="API backend for controlling deep research agents, streaming real-time logs, and managing historical reports.",
    version="1.0.0",
    lifespan=lifespan
)

# Set up CORS middleware to allow the Vue 3 frontend to communicate with it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for development and deployment simplicity
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(research_router, prefix="/api")
app.include_router(reports_router, prefix="/api")

@app.get("/")
async def root():
    return {
        "app": "Deep Research Agent API",
        "version": "1.0.0",
        "status": "healthy"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
