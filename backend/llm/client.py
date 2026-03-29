from backend.config import (
    LLM_PROVIDER,
    GROQ_API_KEY,
    GEMINI_API_KEY,
    OPENROUTER_API_KEY
)

from backend.llm.groq_client import GroqClient
from backend.llm.gemini_client import GeminiClient
from backend.llm.openrouter_client import OpenRouterClient


def get_llm():

    provider = LLM_PROVIDER.lower().strip()

    if provider == "groq":
        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY missing in .env")
        return GroqClient()

    elif provider == "gemini":
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY missing in .env")
        return GeminiClient()

    elif provider == "openrouter":
        if not OPENROUTER_API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY missing in .env")
        return OpenRouterClient()

    raise RuntimeError(
        f"Invalid LLM_PROVIDER '{LLM_PROVIDER}'. Valid options: groq, gemini, openrouter"
    )