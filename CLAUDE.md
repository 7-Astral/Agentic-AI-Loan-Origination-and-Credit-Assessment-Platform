# CLAUDE.md

## What this is

An agentic AI-assisted loan origination and credit assessment platform. A single backend
service will grow to handle loan applications, credit assessment, and audit trails, with
LLM agents assisting loan officers and applicants throughout the process. This is currently
a structural scaffold — no business logic, data models, or agent behavior have been built yet.

## Stack

- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2.x (async), Alembic, Pydantic v2, uvicorn
- **Database**: PostgreSQL 16 with the pgvector extension
- **Agent tooling**: LangGraph, Anthropic SDK (installed and pinned; not yet wired to any agent code)
- **Python packaging**: `pyproject.toml`
- **Frontend package manager**: pnpm

## Repo layout

```
/apps/web              → Next.js frontend
/services/api           → FastAPI backend (single service)
/packages/shared-types  → shared TypeScript type definitions
/infra                  → infrastructure-as-code
/docs                   → project documentation
```

## Where things go (backend, `services/api`)

- API routers → `/routers`
- SQLAlchemy models → `/models`
- Pydantic schemas → `/schemas`
- Agent code (graphs, nodes, tools, prompts, LLM clients, checkpoints) → `/agents`
- External service adapters (credit bureaus, document stores, etc.) → `/integration`
- App configuration and DB session setup → `/core`

The single backend service is expected to grow `/admin`, `/applications`, `/officer`,
`/assessment`, and `/audit` modules in later sprints as business functionality is added.

## Conventions

- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (no
  enforcement tooling wired up yet — this is a convention to follow by hand).
- Python: Ruff + Black for linting/formatting; mypy is configured strict on `/core` only for now.
- TypeScript: ESLint + Prettier.
- Database schema changes go through Alembic migrations — no manual schema edits.
- Secrets (API keys, credentials) are never hardcoded or committed; they are read from the
  environment only. `.env.example` documents every required variable.
