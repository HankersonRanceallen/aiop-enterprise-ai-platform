"""
LLM Service Layer — Abstract Base
===================================
All LLM providers implement this interface. The rest of the system
calls llm_service.generate() and llm_service.embed() without knowing
which provider is behind it — OpenAI, Anthropic, or Ollama.

This abstraction is the key to:
  - Multi-provider support
  - MLflow model comparison (Phase 3)
  - Cost/latency benchmarking
  - Automatic provider fallback
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0


@dataclass
class EmbeddingResponse:
    embedding: list[float]
    provider: str
    model: str
    tokens_used: int = 0
    dimensions: int = field(init=False)

    def __post_init__(self):
        self.dimensions = len(self.embedding)


class BaseLLMService(ABC):
    """Every LLM provider must implement these two methods."""

    @abstractmethod
    async def generate(
        self,
        messages: list[dict],
        system_prompt: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        ...

    @abstractmethod
    async def embed(self, text: str) -> EmbeddingResponse:
        """Embed a string into a vector."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """e.g. 'openai', 'anthropic', 'ollama'"""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """e.g. 'gpt-4o', 'claude-3-5-sonnet-20241022'"""
        ...
