# AIOP — Enterprise AI Cloud Platform

A production-grade, cloud-native Enterprise AI Knowledge & Agent Platform. Built to demonstrate the full lifecycle of an AI engineering system — from RAG fundamentals to multi-agent orchestration to MLOps observability — backed by a tested, CI/CD-ready, AWS-deployable architecture.

> Think of it as a self-contained version of the internal AI platforms enterprises build for employees, customers, and knowledge workers — upload documents, ask questions, get verified answers with citations, run multi-agent workflows, and monitor model quality and cost in production.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Features by Version](#features-by-version)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Testing](#testing)
- [CICD](#cicd)
- [AWS Deployment](#aws-deployment)
- [Switching LLM Providers](#switching-llm-providers)
- [Skills Demonstrated](#skills-demonstrated)

---

## Overview

Most RAG portfolio projects stop at "upload a PDF, ask a question." This platform goes three layers deeper:

| Version | Focus |
|---------|-------|
| **V1 — RAG Foundation** | Upload → Embed → Retrieve → Generate → Cite sources |
| **V2 — Agent Platform** | Multi-agent LangGraph workflows with live SSE streaming |
| **V3 — MLOps Layer** | MLflow tracking, LLM-as-judge evaluation, cost monitoring |

Built as a real multi-tenant SaaS platform — organizations, role-based access, swappable LLM providers, and full observability — not a single-file notebook demo.

---

## Architecture

### System Layers

| Layer | Technology | Role |
|-------|-----------|------|
| **Frontend** | Next.js 15, TypeScript, Tailwind | UI — chat, agents, documents, MLOps dashboard |
| **Backend** | FastAPI, Python 3.11 | API, auth, business logic |
| **Auth** | JWT (access + refresh), bcrypt | User sessions, organization scoping |
| **LLM Layer** | BaseLLMService abstraction | Swappable OpenAI / Anthropic / Ollama |
| **Agents** | LangGraph StateGraph | Planner → Retriever → Analysis → Report |
| **Vector DB** | PostgreSQL + pgvector | Semantic similarity search |
| **MLOps** | MLflow | Experiment tracking, evaluation, monitoring |
| **Cloud** | AWS ECS, RDS, ALB, ECR | Production infrastructure via Terraform |

### Request Flow — RAG Chat

```
User Question
     │
     ▼
Next.js Frontend  ──►  FastAPI Backend
                              │
                         ┌────┴────┐
                         ▼         ▼
                      Embed      Auth
                      Query      (JWT)
                         │
                         ▼
                  pgvector Search
                  (cosine similarity)
                         │
                         ▼
                  Top-K Chunks
                         │
                         ▼
                  LLM Generation
                  (OpenAI / Anthropic / Ollama)
                         │
                         ▼
                  Answer + Sources
                         │
                         ▼
                  MLflow Logging
```

### Agent Workflow — V2

```
User Task
     │
     ▼
Planner Agent      ── breaks task into steps
     │
     ▼
Retriever Agent    ── targeted pgvector search
     │
     ▼
Analysis Agent     ── synthesises findings
     │
     ▼
Report Agent       ── polished executive report
     │
     ▼
SSE Stream to Frontend (live, agent by agent)
```

### LLM Provider Layer

The architectural core — every provider implements the same interface:

```python
class BaseLLMService(ABC):
    async def generate(self, messages, ...) -> LLMResponse: ...
    async def embed(self, text) -> EmbeddingResponse: ...
```

Swap providers with one line in `.env`:

```env
LLM_PROVIDER=openai       # or anthropic, or ollama
LLM_MODEL=gpt-4o
```

---

## Tech Stack

| Category | Technology |
|----------|-----------|
| **Backend** | Python 3.11, FastAPI, SQLAlchemy (async), Pydantic |
| **Frontend** | TypeScript, Next.js 15, Tailwind CSS |
| **Database** | PostgreSQL 16, pgvector |
| **AI / Agents** | LangGraph, OpenAI SDK, Anthropic SDK, Ollama |
| **MLOps** | MLflow, LLM-as-judge evaluation |
| **Auth** | JWT, bcrypt, python-jose |
| **Infrastructure** | Docker, Docker Compose, Terraform |
| **Cloud** | AWS ECS Fargate, RDS, ALB, ECR, Secrets Manager |
| **CI/CD** | GitHub Actions |
| **Testing** | pytest, pytest-asyncio, httpx |

---

## Features by Version

### V1 — RAG Foundation

- Multi-tenant auth — organizations, roles (admin/member/viewer), JWT
- Document upload — PDF, DOCX, TXT — async chunking + embedding pipeline
- Semantic search via pgvector cosine similarity
- RAG chat with multi-turn conversation history and source citations
- Usage dashboard — documents, queries, token usage
- Swappable LLM provider architecture

### V2 — Agent Platform

- LangGraph multi-agent workflow — Planner, Retriever, Analysis, Report agents
- Real-time SSE streaming — frontend shows each agent activating live
- Each agent has a specialised prompt, role, and output in the shared AgentState
- Agent run history persisted to database with full step trace

### V3 — MLOps Layer

- MLflow experiment tracking — every RAG query and agent run logged automatically
- LLM-as-judge evaluation — faithfulness, relevance, completeness scored 0 to 1
- Model comparison table — quality vs latency vs cost across all providers
- Real-time monitoring — request volume, error rate, token usage, estimated cost
- Per-model cost calculation using live token pricing

### Engineering

- Unit tests with mocked LLM — zero external dependencies, instant
- Integration tests against real Postgres
- GitHub Actions CI — lint, unit tests, integration tests, Docker build
- GitHub Actions CD — build, push to ECR, rolling deploy to ECS with rollback
- Terraform — VPC, ECS Fargate, RDS Multi-AZ, ALB, ECR, IAM, Secrets Manager

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- OpenAI API key (or Anthropic/Ollama)

### Run locally

```bash
git clone https://github.com/<your-username>/aiop.git
cd aiop

cp .env.example .env
# Edit .env — set SECRET_KEY, OPENAI_API_KEY, POSTGRES_PASSWORD

docker compose up --build
```

### URLs

| Service | URL |
|---------|-----|
| App | http://localhost:3000 |
| API docs (Swagger) | http://localhost:8000/docs |
| MLflow UI | http://localhost:5001 |

### First run walkthrough

1. Register at `/register` — create an account and organization
2. Upload a PDF on the **Documents** page — wait for status to show `Ready`
3. Ask a question on the **Chat** page — get an answer with cited sources
4. Run a task on the **Agents** page — watch all four agents stream live
5. Run an evaluation on the **MLOps** page — see faithfulness, relevance, completeness scores
6. Open MLflow at `localhost:5001` — view logged experiments

---

## Project Structure

```
aiop/
├── backend/
│   ├── app/
│   │   ├── core/                  config, database, security
│   │   ├── models/                SQLAlchemy ORM models
│   │   ├── schemas/               Pydantic request/response schemas
│   │   ├── api/                   FastAPI route handlers
│   │   └── services/
│   │       ├── llm/               BaseLLMService + OpenAI/Anthropic/Ollama + factory
│   │       ├── rag/               retriever (pgvector) + pipeline (RAG orchestration)
│   │       ├── agents/            LangGraph state, 4 agent nodes, graph
│   │       ├── document_processor.py
│   │       ├── evaluation.py      LLM-as-judge scoring
│   │       └── mlflow_service.py  experiment logging + cost calculation
│   ├── tests/
│   │   ├── unit/                  mocked LLM, no external deps
│   │   └── integration/           real Postgres required
│   └── requirements.txt
│
├── frontend/
│   └── src/app/
│       ├── login/ register/       auth pages
│       ├── chat/                  RAG chat UI
│       ├── agents/                live multi-agent workflow
│       ├── documents/             upload and manage documents
│       ├── dashboard/             usage analytics
│       └── mlops/                 model comparison, evaluation, monitoring
│
├── infra/
│   ├── terraform/                 VPC, ECS, RDS, ALB, ECR, IAM
│   └── ecs/                       ECS task definition templates
│
├── .github/workflows/
│   ├── ci.yml                     lint, test, build
│   └── cd.yml                     push ECR, deploy ECS
│
└── docker-compose.yml
```

---

## API Reference

Full interactive docs at **http://localhost:8000/docs**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Register and create organization |
| `POST` | `/api/v1/auth/login` | Login, receive JWT tokens |
| `GET` | `/api/v1/auth/me` | Current user profile |
| `POST` | `/api/v1/documents/upload` | Upload and auto-index a document |
| `GET` | `/api/v1/documents` | List documents |
| `DELETE` | `/api/v1/documents/{id}` | Delete document |
| `POST` | `/api/v1/chat` | Send a RAG question |
| `GET` | `/api/v1/chat/conversations` | List conversations |
| `GET` | `/api/v1/chat/conversations/{id}` | Get conversation with messages |
| `POST` | `/api/v1/agents/run/stream` | Run multi-agent workflow (SSE) |
| `GET` | `/api/v1/agents/runs` | List past agent runs |
| `GET` | `/api/v1/agents/runs/{id}` | Get agent run with step log |
| `POST` | `/api/v1/mlops/evaluate` | Run LLM-as-judge evaluation |
| `GET` | `/api/v1/mlops/model-comparison` | Model quality/cost/latency table |
| `GET` | `/api/v1/mlops/monitoring` | Real-time platform health |
| `GET` | `/api/v1/dashboard/stats` | Usage analytics |

---

## Testing

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt

# Unit tests — fast, zero external dependencies
pytest tests/unit/ -m "not integration" -v

# Integration tests — requires Postgres
export TEST_DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/aiop_test
pytest tests/integration/ -m integration -v

# With coverage
pytest tests/unit/ -m "not integration" --cov=app --cov-report=term-missing
```

### What is tested

| Area | Tests |
|------|-------|
| Security | JWT creation, expiry, tampering, password hashing |
| Document processing | Chunking, edge cases, TXT extraction |
| RAG pipeline | Full flow with mocked LLM, empty results, MLflow logging |
| Evaluation | Scoring, clamping, fallbacks, composite calculation |
| Agent nodes | Planner, analysis, report — all individually unit tested |
| MLflow service | Cost calculation, silent failure on connection error |
| Auth API | Register, login, duplicate email, bad token (integration) |
| Chat API | Send message, conversations, auth guards (integration) |

---

## CICD

### CI — runs on every push and pull request

```
Lint (ruff)
     │
     ▼
Unit Tests (no external deps)
     │
     ▼
Integration Tests (Postgres service container)
     │
     ▼
Docker Build (backend + frontend)
```

### CD — runs on merge to main

```
Build Images
     │
     ▼
Push to ECR
     │
     ▼
Deploy Backend to ECS (rolling, auto-rollback on failure)
     │
     ▼
Deploy Frontend to ECS
```

Required GitHub secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

---

## AWS Deployment

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# Fill in: db_password, openai_api_key, anthropic_api_key, app_secret_key

terraform init
terraform apply
```

### What Terraform provisions

| Resource | Details |
|----------|---------|
| VPC | Public + private subnets across 2 AZs, NAT gateway |
| ECS Fargate | Backend + frontend services with auto-scaling |
| RDS PostgreSQL 16 | pgvector support, Multi-AZ in production |
| ALB | Path-based routing — `/api/*` to backend, `/*` to frontend |
| ECR | Two repositories with image scanning and lifecycle policies |
| IAM | Scoped roles for ECS execution and task |
| Secrets Manager | DATABASE_URL, OPENAI_API_KEY, SECRET_KEY |

---

## Switching LLM Providers

Change one line in `.env`:

```env
# Phase 1 — OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o

# Phase 2 — Anthropic
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022

# Phase 3 — Local / free
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1
```

Nothing else changes. The RAG pipeline, agents, and evaluation service all use `BaseLLMService` and are provider-agnostic. The V3 model comparison table shows the quality, latency, and cost difference between providers using real data from your own queries.

---

## Skills Demonstrated

| Category | Skills |
|----------|--------|
| **AI / ML** | RAG pipelines, vector embeddings, semantic search, LangGraph agents, prompt engineering, LLM-as-judge evaluation |
| **Backend** | FastAPI, async SQLAlchemy, JWT auth, background tasks, SSE streaming |
| **Databases** | PostgreSQL, pgvector, cosine similarity, multi-tenant schema design |
| **MLOps** | MLflow experiment tracking, evaluation pipelines, cost and latency monitoring |
| **Cloud** | Docker, Terraform, AWS ECS Fargate, RDS, ALB, ECR, Secrets Manager |
| **CI/CD** | GitHub Actions, automated testing, ECR push, ECS rolling deploy |
| **Engineering** | Provider abstraction pattern, type safety, pytest unit and integration testing |

---

## License

MIT
