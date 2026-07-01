import time
from openai import AsyncOpenAI

from app.core.config import settings
from app.services.llm.base import BaseLLMService, EmbeddingResponse, LLMResponse


class OpenAIService(BaseLLMService):
    def __init__(self):
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.llm_model
        self._embedding_model = settings.openai_embedding_model

    @property
    def provider_name(self) -> str:
        return "openai"

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
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)

        start = time.monotonic()
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=all_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        latency_ms = (time.monotonic() - start) * 1000

        choice = response.choices[0]
        usage = response.usage

        return LLMResponse(
            content=choice.message.content or "",
            provider=self.provider_name,
            model=self._model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            total_tokens=usage.total_tokens if usage else 0,
            latency_ms=round(latency_ms, 2),
        )

    async def embed(self, text: str) -> EmbeddingResponse:
        response = await self._client.embeddings.create(
            model=self._embedding_model,
            input=text,
        )
        data = response.data[0]
        return EmbeddingResponse(
            embedding=data.embedding,
            provider=self.provider_name,
            model=self._embedding_model,
            tokens_used=response.usage.total_tokens if response.usage else 0,
        )
