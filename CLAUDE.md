# CLAUDE.md

## What this is

An agentic AI-assisted loan origination and credit assessment platform. A single backend
service handles loan applications, credit assessment, and (eventually) audit trails, with
LLM agents assisting loan officers and applicants throughout the process. Two agent flows
exist so far: a conversational loan-enquiry agent (`agents/orchestrator.py`) and a 5 C's
credit risk assessment agent (`agents/risk_assessment/`, see below).

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
/services/mock-bureau   → mock credit bureau sandbox (dev/local only, see below)
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
- Authentication (provider abstraction, password hashing, JWT, route dependencies) → `/auth`

The single backend service is expected to grow `/admin` and `/audit` modules in later
sprints as business functionality is added.

## Authentication, roles, and portals

### Auth provider abstraction — local auth is a deliberate, documented substitute

The Project Charter and architecture documents specify **Microsoft Entra ID** for staff and
**Azure AD B2C** for customers. This has **not** been implemented — wiring up a real Azure
tenant is out of scope for this stage of development, and local email/password auth stands
in for it so the two portals below can be built and demoed without that dependency.

Every route handler and the frontend depend only on the resolved user and role — never on
anything local-auth-specific — via `auth/providers.py`'s `AuthProvider` protocol:

```python
class AuthProvider(Protocol):
    async def authenticate(self, credentials: Credentials) -> AuthenticatedUser | None: ...
    async def get_user_claims(self, token: str) -> UserClaims | None: ...
```

`auth/local_provider.py`'s `LocalAuthProvider` is the only implementation today (argon2
password hashing via `passlib[argon2]` — not bcrypt, which has a known version
incompatibility with current passlib releases; JWTs via PyJWT, `HS256`, signed with the
required `JWT_SECRET` setting, ~30 minute access-token lifetime, no refresh tokens).
`auth/factory.py::get_auth_provider()` selects the implementation via the `AUTH_PROVIDER`
setting (default `local`). **Swapping to Entra ID/Azure AD B2C later should only ever touch
a new provider implementation and the factory** — no route handler, dependency, or frontend
code should need to change.

### Role model and access control

Four roles (`models/enums.py::UserRole`): `customer`, `loan_officer`, `credit_manager`,
`admin`. `auth/dependencies.py` provides `get_current_user` (401 if the token is missing or
invalid) and `require_role(*roles)` (403 for the wrong role).

**Role checks and ownership checks are separate concerns, and every protected endpoint
needs both.** A role check alone would let any authenticated customer read any other
customer's application by changing the id in the URL — `routers/applications.py` scopes
every query and every fetched row by the authenticated user's own id (`customer_id`) or
bank (`bank_id`), never by a role check in isolation. The one deliberate exception to
"never re-check the DB, trust the JWT claims": `POST /applications/{id}/actions` re-fetches
the acting officer's `User` row and checks `is_active`, since it's the one endpoint whose
effect (an `officer_actions` row plus a status change) outlives the token — every other
endpoint trusts the claims for the full ~30 minute token lifetime.

### Customer/officer view split

A customer and an officer looking at the same `applications` row see genuinely different
response shapes (`routers/applications.py`'s `_build_customer_view` vs
`_build_officer_view`), not the same payload with fields hidden client-side. An officer's
`reject`/`override` reason, the full `officer_actions` history, the customer's financial
profile, and the live 5 C's risk report are **never serialized** into a customer's
response — a customer sees only a derived `outcome` (once `status == decided`) and, while
still pending, the latest `request_info` message. Rejecting or overriding an application
without checking this split is the fastest way to leak internal assessment reasoning to
the applicant it's about.

### Seeded dev accounts

`scripts/seed.py` seeds six local-auth accounts (three customers, a loan officer, a credit
manager, a platform admin) all with the password `Demo1234!`, plus a spread of sample
applications across every status. **These credentials must never exist in a deployed
environment** — they exist purely so the portals below have something to log into locally.

### Frontend: token storage and route guards

The access token is kept in `localStorage` (`apps/web/lib/auth.ts`), not an httpOnly
cookie — a deliberate dev-stage trade-off. This accepts XSS-based token theft as a known
risk in exchange for avoiding a `Set-Cookie`/CSRF story and `credentials: "include"` on
every request. **Consequence**: Next.js edge `middleware.ts` cannot read `localStorage`, so
route protection is a client-side guard (`components/auth-guard.tsx`) instead, rendered
inside each protected page rather than at the edge — it redirects an unauthenticated
visitor to `/${bankSlug}/login`, and an authenticated visitor on the wrong portal to the
home path their own role owns.

### Routes and modules added

- Backend: `auth/` (provider abstraction, security, dependencies), `routers/auth.py`
  (`/auth/login`, `/auth/logout`, `/auth/me`, `/auth/register` — customer self-registration
  only, any client-supplied `role` is ignored), `routers/applications.py`
  (`GET /applications`, `GET /applications/{id}`, `POST /applications/{id}/actions`),
  `routers/users.py` (`GET`/`PATCH /users/me/profile`), plus the `users`,
  `customer_profiles`, `applications`, and `officer_actions` tables.
- Frontend: `/[bankSlug]/login`, `/[bankSlug]/portal` (+ `/[applicationId]`, customer),
  `/[bankSlug]/officer` (+ `/[applicationId]`, loan_officer/credit_manager), `/[bankSlug]/admin`
  (placeholder). The existing chat flow moved from `/` to `/[bankSlug]`, with `/` now a
  redirect to the single seeded bank (`/demo-mutual`). The pre-existing `/applications`,
  `/applications/[id]`, and `/risk-assessment` pages are unrelated and untouched.

## 5 C's credit risk assessment

`POST /risk-assessment` (`routers/risk_assessment.py`) accepts a raw or normalised
application as JSON and returns a report assessing it against Character, Capacity, Capital,
Collateral and Conditions. **It never blocks on missing data** — every stage degrades
gracefully and the endpoint always returns 200 with a partial report rather than failing.
It produces no approval, rejection, eligibility verdict or overall risk grade — that's an
assessment, not a decision, and stays a human/downstream-stage responsibility.

Modules:

- `schemas/application.py` — the canonical normalised application shape (every field
  optional at every level).
- `agents/risk_assessment/normalise.py` — coerces raw JSON into that shape; tolerant of
  missing fields, mixed date formats, and currency strings.
- `models/required_field_template.py` + `agents/risk_assessment/checklist_loader.py` — the
  per-product-type required-fields checklist, DB-driven and versioned like
  `QuestionTemplate`/`agents/questions/loader.py`. Seeded in `scripts/seed.py`.
- `agents/risk_assessment/completeness.py` — diffs a normalised application against the
  checklist to produce `missing_fields` and a completeness score.
- `agents/risk_assessment/capacity.py` — Capacity's arithmetic (disposable income, loan
  servicing) — plain code, never a model output. Benchmark figures substituted for missing
  declared data (expenses, revolving-credit repayments, interest rate) are always called
  out in `notes`.
- `agents/risk_assessment/five_cs.py` — Character, Capital, Collateral and Conditions.
- `agents/risk_assessment/orchestrator.py` — coordinates collection and assembles the
  report. Collection is conditional and independent: the credit bureau is only called when
  name/dob/address are all present, the ABR only when an ABN is present; one collector
  failing or being skipped never prevents the others or the report itself.
- `integration/credit_bureau.py`, `integration/abr.py` — the external adapters (below).

### Source / confidence taxonomy

Every one of the five C's carries `{ value, source, confidence, notes }`. Applied
consistently across all five:

| `source`             | meaning                                              | `confidence` |
|-----------------------|-------------------------------------------------------|--------------|
| `bureau-verified`     | from a matched credit bureau report                    | high         |
| `abn-verified`        | from a matched ABR lookup                               | high         |
| `calculated`          | arithmetic in code from declared inputs (Capacity)      | medium       |
| `applicant-declared`  | taken as given from the applicant, unverified           | medium/low   |
| `unavailable`         | the data/lookup needed wasn't available; `value` is null | low          |

**Character is never synthesised.** If the bureau call didn't happen, failed, or returned
`matched: false`, Character is `unavailable` with a null value — no score is ever estimated
from other fields or produced by a language model. A fabricated credit score is treated as
the single worst failure mode this system could have.

### Mock credit bureau (`services/mock-bureau`)

A separate FastAPI service (own `docker-compose` entry, port 8001 published) modelling how
a real credit bureau sandbox behaves: OAuth2 client-credentials + Bearer auth, JSON
request/response.

- `POST /oauth2/v1/token` — `{ client_id, client_secret, grant_type: "client_credentials" }`
  → `{ access_token, token_type: "Bearer", expires_in }`.
- `POST /credit-report/v1` — Bearer-authenticated, `{ name, dob, address }` → a report on
  match, or `{ "matched": false }` (200, not an error — no match is a legitimate outcome).
- Seeded with six synthetic test identities in `data/identities.py` spanning the score
  bands (excellent/good/fair/poor/adverse/thin-file). None are real people.

**To swap for a live bureau**: point `MOCK_BUREAU_BASE_URL` and the
`MOCK_BUREAU_CLIENT_ID`/`MOCK_BUREAU_CLIENT_SECRET` settings at the real provider — the
call shape in `integration/credit_bureau.py` is modelled on how a real bureau sandbox
behaves, so no calling code changes.

### ABN Lookup (ABR)

`integration/abr.py` calls the public ABR web service and requires a free GUID registered
with the ABR (https://abr.business.gov.au/Tools/WebServices), read from settings as
`ABR_GUID`. Unset in dev by default — the collector degrades to `found: None` /
`unavailable` rather than raising when it's absent, consistent with the never-block rule.
The endpoint wraps its response in JSONP and returns 200 with an `Exception`/no-`Abn`
payload for an invalid or unknown ABN (not an HTTP error) — both are handled explicitly
rather than trusting the status code.

## Conventions

- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (no
  enforcement tooling wired up yet — this is a convention to follow by hand).
- Python: Ruff + Black for linting/formatting; mypy is configured strict on `/core` only for now.
- TypeScript: ESLint + Prettier.
- Database schema changes go through Alembic migrations — no manual schema edits.
- Secrets (API keys, credentials) are never hardcoded or committed; they are read from the
  environment only. `.env.example` documents every required variable.
