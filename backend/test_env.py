import sys
from pathlib import Path

# Add app to path
sys.path.append(str(Path(__file__).resolve().parent))

try:
    from app.config import settings
    print("SUCCESS: Configuration loaded successfully!")
    print(f"OPENAI_API_KEY: {settings.OPENAI_API_KEY[:4] + '***' if settings.OPENAI_API_KEY else 'Missing'}")
    print(f"OPENAI_BASE_URL: {settings.OPENAI_BASE_URL}")
    print(f"OPENAI_MODEL: {settings.OPENAI_MODEL}")
    print(f"TAVILY_API_KEY: {settings.TAVILY_API_KEY[:4] + '***' if settings.TAVILY_API_KEY else 'Missing'}")
except Exception as e:
    print(f"FAILURE: Error loading configuration: {e}")
    sys.exit(1)
