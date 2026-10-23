# Running the agent-backend test suite

48 tests covering the chat agent's own logic: slot validation/batching
(pure functions, no DB or LLM), the discovery graph end-to-end (loan-type
classification, category narrowing, product cards — including a direct
regression test for the "two products under one type only showed one"
bug), the full interview graph (ask → extract → validate → next slot,
repeated to completion, then submit into the main platform's real loan
pipeline), and the staff-facing decision/report endpoints.

## How it's built

- **Real Postgres** for the operational read-model (applications, messages,
  slots, decisions — everything in `app.models.application`) — a second,
  disposable database on the same `db` container docker-compose already
  runs, same reasoning as `services/api`'s suite: the models use
  Postgres-specific types, and this is what actually runs in production.
- **The Gemini LLM is never called.** `app.core.llm.get_llm` is replaced
  with a small in-process fake (`FakeLLM` in `tests/conftest.py`) that
  returns canned responses instead of hitting Google's API — tests are
  fast, free, and deterministic.
- **services/api and mock_core_banking are never called either.** The
  `app.services.core_banking.core_banking` client (which normally makes
  HTTP calls to both of those) is replaced with an in-process fake catalog
  with a small fixed set of loan types/products.
- The LangGraph checkpointer is the graphs' own default in-memory one
  (`MemorySaver`), not the real `AsyncPostgresSaver` the app uses in
  production — that just needs a second Postgres-backed table set the
  tests don't need, since a test's graph object only has to live for that
  one test.

None of this touches your real `loan_origination` database, your Gemini
API key/quota, or services/api.

## One-time setup

1. Rebuild the `agent-backend` image so `pytest`/`pytest-asyncio` (added to
   `requirements.txt`) are installed:

   ```
   docker compose up -d --build agent-backend
   ```

2. Create the throwaway test database (safe to re-run — ignore the "already
   exists" error if you run it twice):

   ```
   docker compose exec db psql -U postgres -c "CREATE DATABASE agent_backend_test;"
   ```

## Running the tests

```
docker compose exec -e TEST_APP_DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/agent_backend_test agent-backend pytest
```

Add `-v` for per-test output, or point it at one file while working on
something specific:

```
docker compose exec -e TEST_APP_DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/agent_backend_test agent-backend pytest tests/test_discovery_api.py -v
```

A clean run ends with `48 passed`.

## A real finding from building this suite (now fixed)

While wiring up the interview graph tests, the fake LLM's call log showed
`ask_node` (in `app/agents/interaction/graph.py`) calling the LLM **twice**
per slot instead of once: it used to build the question text, *then* call
`interrupt()`. Because a LangGraph node that calls `interrupt()` re-runs
from the top of the function on every resume (the same behavior
`present_node` in `discovery.py` already works around — see its comment),
resuming `ask_node` re-generated the question a second time before moving
on, and that second copy is what actually got written into the transcript
— not the one the applicant was shown. In production this meant every
interview turn burned two Gemini calls instead of one, and the stored
transcript could end up with slightly different wording than what the
applicant actually saw.

**Fixed** by splitting `ask_node` into two nodes, the same shape
`discovery.py` already uses between `classify_type_node` (does the LLM
work) and `clarify_type_node` (does the interrupting): a new
`compose_question_node` computes the question and nothing else — no
`interrupt()`, so it runs to completion exactly once and its result is
committed to checkpointed state before the graph ever pauses — and
`ask_node` now just reads that already-computed question and calls
`interrupt()`. (There's a defensive fallback in `ask_node` for any
interview thread whose checkpoint was already paused mid-turn under the
old code when this shipped — it recomputes the question inline just for
that one turn, then behaves normally from then on.)

`test_ask_llm_called_exactly_once_per_slot_not_twice` in
`test_interview_api.py` pins this down: it asserts exactly one questioner
call per slot (3, for the default 3-slot fixture) across a full interview,
not 6.
