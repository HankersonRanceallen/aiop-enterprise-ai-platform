import time
import httpx

from app.core.config import settings
from app.services.llm.base import BaseLLMService, EmbeddingResponse, LLMResponse


class OllamaService(BaseLLMService):
    """
    Local Ollama provider (Llama 3.1, Qwen, Mistral, etc.)
    Zero API cost — ideal for private data and offline usage.
    """

    def __init__(self):
        self._base_url = settings.ollama_base_url
        self._model = settings.ollama_model

    @property
    def provider_name(self) -> str:
        return "ollama"

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
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
        latency_ms = (time.monotonic() - start) * 1000

        data = response.json()
        content = data.get("message", {}).get("content", "")
        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)

        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model=self._model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=round(latency_ms, 2),
        )

    async def embed(self, text: str) -> EmbeddingResponse:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._base_url}/api/embeddings",
                json={"model": self._model, "prompt": text},
            )
            response.raise_for_status()

        data = response.json()
        embedding = data.get("embedding", [])

        return EmbeddingResponse(
            embedding=embedding,
            provider=self.provider_name,
            model=self._model,
        )
