# Running the API test suite

54 tests covering auth, admin (bank/staff onboarding, deactivate/reactivate),
bank-staff management (staff/products/policies — create, partial update,
soft deactivate/reactivate, permission gating), end-to-end lending decision
routing (auto-approval + manager notification, escalation routing +
notification), audit logging (bank_id, human-readable entity_label,
manager-only gating), and the core-banking catalog contract used by the
chat agent.

They run against a **real Postgres database** (a second, disposable
database on the same `db` container docker-compose already runs) — not
sqlite — because the models use Postgres-only types. The suite creates and
drops its own tables in that database every run; it never touches the real
`loan_origination` database.

## One-time setup

1. Rebuild the `api` image so `pytest`/`pytest-asyncio` (added to
   `requirements.txt`) are installed:

   ```
   docker compose up -d --build api
   ```

2. Create the throwaway test database (safe to re-run — ignore the "already
   exists" error if you run it twice):

   ```
   docker compose exec db psql -U postgres -c "CREATE DATABASE loan_origination_test;"
   ```

## Running the tests

Every time you want to check a change:

```
docker compose exec -e TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/loan_origination_test api pytest
```

That's the one command — copy/paste it after any backend change. Add
`-v` for per-test output, or point it at one file/test while you're working
on something specific, e.g.:

```
docker compose exec -e TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/loan_origination_test api pytest tests/test_lending_logic.py -v
```

A clean run ends with something like `54 passed`. Since the `api` service
already has a live volume mount, editing a test file takes effect
immediately — no rebuild needed unless `requirements.txt` changes again.
