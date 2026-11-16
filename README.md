# EvidenceFlow

EvidenceFlow is an evidence-grounded multi-agent deep research system built with LangGraph, Milvus, FastAPI, and Vue 3.

The project turns a research topic into a traceable report through planning, parallel web and local retrieval, evidence judging, analysis, reflection, citation-constrained writing, and citation validation.

## Implemented

- strict environment-based configuration;
- shared research, evidence, finding, and event contracts;
- FastAPI liveness and readiness endpoints;
- local PostgreSQL, Redis, MinIO, etcd, and Milvus infrastructure;
- an offline LangGraph research workflow with planning and parallel scouts;
- deterministic evidence deduplication, judging, analysis, and reflection;
- bounded supplemental search with a two-iteration default;
- citation-constrained Markdown reports and citation validation;
- PostgreSQL persistence for tasks, evidence, findings, reports, and replayable events;
- Redis/ARQ background execution with cancellation at graph node boundaries;
- research task, report, evidence, cancellation, and SSE event APIs;
- Argon2id password hashing and expiring JWT bearer authentication;
- ownership checks across tasks, reports, evidence, cancellation, and event streams;
- selectable Bocha web search and DashScope/Qwen planning, analysis, and report writing;
- bounded provider retries, structured LLM output validation, and strict evidence ID mapping;
- user-scoped document ingestion, chunking, Milvus retrieval, and semantic research memory;
- Vue 3 research workbench with authenticated SSE progress, reports, evidence, and knowledge management;
- unit and integration tests for contracts and the complete graph.

No real API key belongs in this repository. Copy `.env.example` to `.env` and provide secrets locally.

## Quick start

### Backend development

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --project backend
uv run --project backend alembic upgrade head
uv run --project backend uvicorn app.main:app --reload --app-dir backend
uv run --project backend arq app.jobs.WorkerSettings
uv run --project backend pytest backend/tests
```

### Docker infrastructure

```bash
docker compose up -d postgres redis etcd minio milvus
docker compose --profile app up --build backend worker frontend
```

The workbench is available at `http://localhost:5173` and the API at `http://localhost:8000`;
health endpoints are `/health/live` and `/health/ready`.
Register through `POST /api/auth/register`, then send the returned token as
`Authorization: Bearer <token>` to the research endpoints. Interactive API documentation is
available at `/docs`.

The default `mock` providers run without paid credentials. To enable the real research path,
set `LLM_PROVIDER=dashscope`, `WEB_SEARCH_PROVIDER=bocha`, `DASHSCOPE_API_KEY`, and
`BOCHA_API_KEY` in the local `.env` file. Secrets must never be committed.

`POST /api/documents` accepts a title, text content, and optional source URI. Docker deployments
use Milvus as the shared vector store; deterministic embeddings keep this path usable without an
embedding API. Set `EMBEDDING_PROVIDER=dashscope` to use `text-embedding-v3`. The in-memory vector
store is intended only for tests or a single-process development session.

## Research flow

```text
Memory Recall -> Intent Router -> Planner
  -> Web Scout + Local Scout
  -> Evidence Judge -> Analyst -> Reflect
  -> Writer -> Citation Validator -> Memory Commit
```

The workflow retains deterministic mock adapters so it can be demonstrated and tested without
paid credentials.

## Repository layout

```text
backend/       FastAPI application, domain contracts, graph, services, and tests
frontend/      Vue 3 research workbench and Nginx runtime
docker-compose.yml
```

## License

MIT

