from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    # App
    app_name: str = "AIOP - Enterprise AI Platform"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://aiop:aiop_secret@postgres:5432/aiop_db"

    # Auth
    secret_key: str = "change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # LLM
    llm_provider: Literal["openai", "anthropic", "ollama"] = "openai"
    llm_model: str = "gpt-4o"

    # OpenAI
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"

    # Anthropic
    anthropic_api_key: str = ""

    # Ollama
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1"

    # RAG
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k_retrieval: int = 5

    # Uploads
    upload_dir: str = "/app/uploads"
    max_file_size_mb: int = 50

    # MLflow (V3)
    mlflow_tracking_uri: str = "http://mlflow:5000"
    mlflow_experiment_name: str = "aiop-rag-platform"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
