import time
import anthropic

from app.core.config import settings
from app.services.llm.base import BaseLLMService, EmbeddingResponse, LLMResponse


class AnthropicService(BaseLLMService):
    """
    Anthropic Claude provider.
    Note: Anthropic does not currently offer an embeddings API.
    When using this provider, embeddings fall back to OpenAI.
    """

    def __init__(self):
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.llm_model  # e.g. claude-3-5-sonnet-20241022

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self,
        messages: list[dict],
        system_prompt: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        kwargs: dict = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        start = time.monotonic()
        response = await self._client.messages.create(**kwargs)
        latency_ms = (time.monotonic() - start) * 1000

        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text

        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model=self._model,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            latency_ms=round(latency_ms, 2),
        )

    async def embed(self, text: str) -> EmbeddingResponse:
        # Anthropic doesn't have an embeddings API — fall back to OpenAI embeddings.
        # In Phase 3, we'll track which embedding model is used separately from the LLM.
        from app.services.llm.openai_service import OpenAIService
        openai = OpenAIService()
        return await openai.embed(text)
