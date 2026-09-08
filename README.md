# Agentic AI Loan Origination and Credit Assessment Platform

An agentic AI-assisted loan origination platform: a Next.js frontend, a FastAPI backend, a
Postgres + pgvector database, and a mock credit bureau sandbox, wired together for local
development. See [CLAUDE.md](./CLAUDE.md) for what's built so far.

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

   The 5 C's risk assessment's ABN lookup calls the ABR web service, which requires a free
   GUID — register for one at https://abr.business.gov.au/Tools/WebServices and set it as
   `ABR_GUID` in `.env`. Left unset, the ABN collector degrades gracefully rather than
   failing (business applicants just won't get ABR-verified details). The credit bureau
   collector needs no such registration — it talks to `services/mock-bureau`, a local
   sandbox started by `docker compose` alongside `api` and `web`.

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
- Mock credit bureau sandbox: [http://localhost:8001](http://localhost:8001) (dev/local only — see CLAUDE.md)

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

### Mock credit bureau (`services/mock-bureau`)

```sh
cd services/mock-bureau
python -m venv .venv
.venv/Scripts/activate       # on Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -e ".[dev]"

pytest                       # tests
uvicorn main:app --reload --port 8001   # dev server
```

### Frontend (`apps/web`)

Next.js only loads `.env` files from inside `apps/web` itself — the repo-root `.env` is not
read when running `next dev` locally (it's only picked up via `docker compose`'s `env_file`).
Create `apps/web/.env.local` with at least:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

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
/services/mock-bureau   → mock credit bureau sandbox (dev/local only)
/packages/shared-types  → shared type definitions (placeholder)
/infra                  → infrastructure-as-code (placeholder)
/docs                   → project documentation (placeholder)
```

See [CLAUDE.md](./CLAUDE.md) for stack details, conventions, and where new code should go.
