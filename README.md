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
- unit and integration tests for contracts and the complete graph.

No real API key belongs in this repository. Copy `.env.example` to `.env` and provide secrets locally.

## Quick start

### Backend development

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --project backend
uv run --project backend uvicorn app.main:app --reload --app-dir backend
uv run --project backend pytest backend/tests
```

### Docker infrastructure

```bash
docker compose up -d postgres redis etcd minio milvus
docker compose --profile app up --build backend
```

The API is available at `http://localhost:8000`; health endpoints are `/health/live` and `/health/ready`.

## Research flow

```text
Memory Recall -> Intent Router -> Planner
  -> Web Scout + Local Scout
  -> Evidence Judge -> Analyst -> Reflect
  -> Writer -> Citation Validator -> Memory Commit
```

The current workflow uses deterministic mock adapters so it can be demonstrated and tested
without paid credentials. Bocha, DashScope, Milvus persistence, background jobs, SSE, and the
Vue workbench are introduced in subsequent milestones behind the same contracts.

## Repository layout

```text
backend/       FastAPI application, domain contracts, graph, services, and tests
frontend/      Vue 3 research workbench (introduced in a later milestone)
docker-compose.yml
```

## License

MIT

