import os
from dotenv import load_dotenv

load_dotenv()


def require_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


LLM_PROVIDER = os.getenv("LLM_PROVIDER")
DATA_PROVIDER = os.getenv("DATA_PROVIDER", "semantic")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")