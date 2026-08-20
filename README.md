# Agentic AI Loan Origination and Credit Assessment Platform

A scaffold for an agentic AI-assisted loan origination platform: a Next.js frontend, a FastAPI
backend, and a Postgres + pgvector database, wired together for local development. This stage
sets up structure and tooling only — no business logic, data models, or agent behavior yet.

## Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose
- [Node.js](https://nodejs.org/) 20+ and [pnpm](https://pnpm.io/) 9+ (for running the frontend outside Docker)
- [Python](https://www.python.org/) 3.11+ (for running the backend outside Docker)

## Setup

1. Clone the repository.
2. Copy the environment template and adjust values if needed:

   ```sh
   cp .env.example .env
   ```

3. Start the stack:

   ```sh
   docker compose up
   ```

4. In a separate terminal, run the database migrations:

   ```sh
   docker compose exec api alembic upgrade head
   ```

## URLs

- Frontend: [http://localhost:3000](http://localhost:3000)
- API: [http://localhost:8000](http://localhost:8000)
- Interactive API docs (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)

## Running outside Docker

### Backend (`services/api`)

```sh
cd services/api
python -m venv .venv
.venv/Scripts/activate       # on Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -e ".[dev]"

pytest                       # tests
ruff check .                 # lint
black --check .              # format check
mypy core                    # type check (strict on core/ for now)
alembic upgrade head         # apply migrations
```

### Frontend (`apps/web`)

```sh
cd apps/web
pnpm install

pnpm test                    # tests
pnpm lint                    # lint
pnpm format                  # format check
pnpm typecheck                # type check
pnpm dev                     # dev server
```

## Repo layout

```
/apps/web              → Next.js 14 (App Router) + TypeScript frontend
/services/api           → Python FastAPI backend
/packages/shared-types  → shared type definitions (placeholder)
/infra                  → infrastructure-as-code (placeholder)
/docs                   → project documentation (placeholder)
```

See [CLAUDE.md](./CLAUDE.md) for stack details, conventions, and where new code should go.
