from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api import auth, documents, chat, dashboard, agents, mlops


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="3.0.0",
    description="""
## Enterprise AI Knowledge & Agent Platform

- 📄 **V1** — RAG pipeline, multi-provider LLM, document Q&A
- 🤖 **V2** — LangGraph multi-agent system with SSE streaming
- 🔬 **V3** — MLflow tracking, LLM-as-judge evaluation, monitoring dashboard
""",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,      prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(chat.router,      prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(agents.router,    prefix="/api/v1")
app.include_router(mlops.router,     prefix="/api/v1")


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "3.0.0",
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "mlflow_uri": settings.mlflow_tracking_uri,
    }
