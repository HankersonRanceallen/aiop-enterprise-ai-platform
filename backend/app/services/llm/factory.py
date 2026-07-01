"""
LLM Factory
============
Returns the correct LLM service based on LLM_PROVIDER env var.
This single function is what swaps providers platform-wide.

Usage:
    llm = get_llm_service()       # reads from config
    llm = get_llm_service("anthropic")  # explicit override
"""
from app.core.config import settings
from app.services.llm.base import BaseLLMService


def get_llm_service(provider: str | None = None) -> BaseLLMService:
    target = provider or settings.llm_provider

    if target == "openai":
        from app.services.llm.openai_service import OpenAIService
        return OpenAIService()

    elif target == "anthropic":
        from app.services.llm.anthropic_service import AnthropicService
        return AnthropicService()

    elif target == "ollama":
        from app.services.llm.ollama_service import OllamaService
        return OllamaService()

    else:
        raise ValueError(
            f"Unknown LLM provider: '{target}'. "
            f"Valid options: openai, anthropic, ollama"
        )
