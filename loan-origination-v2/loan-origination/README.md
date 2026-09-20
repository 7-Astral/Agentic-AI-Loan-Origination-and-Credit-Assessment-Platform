# Loan Origination Platform — v5 (chat agent: conversational intake, document OCR, Five C's assessment)

Full-stack build: Next.js frontend, FastAPI backend, PostgreSQL database, JWT
auth, a polished responsive UI, and three working portals — Admin, Bank
staff, and Customer — all backed by real data. As of v5 the customer portal
also offers a real conversational intake flow (`/customer/chat`), backed by
a separate LangGraph chat-agent service that does genuine document OCR and
Five C's credit assessment, converging on the same deterministic
auto-approval/escalation routing as the plain form. See "What's new in v5"
below.

## What's new in v4

- **Bank position ladder**: each bank now has its own configurable approval
  hierarchy (`bank_positions` — e.g. Loan Officer → Credit Manager → CFO →
  CEO → Board), seeded per bank with a title, rank, an approval limit
  (`max_approval_amount`, nullable = unlimited), and two permission flags:
  `can_manage_staff` and `can_manage_products`. Nothing about the hierarchy
  is hardcoded — an admin (or any staff member with `can_manage_staff`) can
  shape it differently per bank.
- **Bank self-service portal** (`/staff`): staff log in and land in a
  dedicated portal scoped to their own bank. What they can do depends on
  their position:
  - **Team** (gated on `can_manage_staff`) — register new staff for the bank,
    assign them a position at creation time, and **deactivate/reactivate**
    staff accounts (soft-delete, not a hard row delete — see below).
  - **Products** and **Policies** (gated on `can_manage_products`) — add
    loan products and auto-approval policies for the bank.
  - **Applications** — every application submitted to the bank, with status
    and (if escalated) which position needs to approve it next.
  - **Notifications** — a bell with an unread badge; alerts land here when
    an application needs that staff member's position to approve it.
  A staff member without a position, or whose position lacks a permission,
  sees a "Restricted" message instead of the management UI — enforced both
  in the UI (nav links are hidden) and on the API (403 if bypassed).
- **Deterministic decision routing** (`app/core/lending_logic.py`): every
  submitted application is checked against the bank's lending policy first.
  Under the auto-approval threshold → approved immediately. Over it → routed
  to the lowest position on the bank's ladder whose approval limit actually
  covers the amount, and every staff member holding that position gets a
  notification. This is deliberately a plain deterministic function, not an
  LLM call — it's the seed of the Decision Agent (FR8) for a later phase.
- **Customer loan application flow** (`/customer`): browse products across
  banks, apply with an amount/tenure/purpose, and see the outcome
  immediately — auto-approved, or under review with the position it's
  pending on. A running list of "My applications" shows status for every
  past submission.
- **Admin → staff creation now includes position assignment**: the existing
  Admin "Add staff" modal gained a Position dropdown (scoped to the chosen
  bank), so admins can create fully-configured staff accounts too, not just
  bank self-service.
- **Removing staff = deactivate, not delete**: accounts are never hard-deleted
  (they're referenced by past applications, decisions, and audit log entries,
  which need to stay intact for compliance). Instead, both the Admin Users
  page and the bank Team page have a Deactivate/Reactivate action per row:
  - Deactivating flips `users.is_active` to `false`. That account can no
    longer log in, immediately invalidates any JWT it's currently holding
    (checked on every authenticated request, not just at login), and is
    automatically skipped when the routing logic decides who to notify for
    an escalation.
  - Every deactivate/reactivate writes an `audit_logs` row.
  - A staff member can never deactivate their own account (the button is
    hidden on their own row) — otherwise the last `can_manage_staff` holder
    at a bank could lock themselves out with no way back in.
  - On the Team page this is gated the same way as everything else
    (`can_manage_staff`); on the Admin Users page it works platform-wide,
    across any bank or role.
- Two new tables: `bank_positions` and `notifications`, plus new columns
  (`users.position_id`, `escalations.escalated_to_position_id`) — see
  `migrations/versions/e80fc8b39b2c_bank_hierarchy_and_notifications.py`.

## What's new in v5 — the chat agent

The plain "Apply for a loan" form is now joined by a real conversational
intake flow at **`/customer/chat`** ("Chat with the assistant" on the
customer portal), backed by a separate service, `services/agent-backend` —
a LangGraph-based agent doing genuine discovery chat, structured interview,
Gemini-vision document OCR, and a real Five C's credit assessment (capacity,
capital, character, collateral, conditions), not a toy stub. It runs on its
own port (8001) and its own Postgres schemas inside the same database, and
hands every completed interview into the *same* `route_loan_decision` the
plain form uses — so a chat-submitted application shows up for staff exactly
like any other, correctly auto-approved or escalated and notified.

`services/api` gained a small `/api/v1/...` router
(`app/api/routes/core_banking.py`) that the agent reads the product catalog
from and submits completed applications to, authenticated with a shared
`SERVICE_API_KEY` rather than a user JWT (server-to-server). `loan_products`
gained a few columns (`product_code`, `secured`, `rate_type`,
`comparison_rate`, `establishment_fee`, `max_lvr`, `features`) so this
platform's own table can fully satisfy that catalog contract on its own —
see migration `0f8bc6a836fe`.

Full details — why it's a separate service, how identity and the product
catalog are bridged, and what's still split across the two systems — are in
the project's `db-schema-design.md` (§8, "v5 — the chat agent integration").
Quick facts worth knowing before you run it:

- **Four services now**, not two: `services/api` (8000), `services/agent-backend`
  (8001), `services/agent-backend`'s bundled `mock_core_banking` (9000, still
  serves document-requirement checklists / HEM policy / Five C's rules —
  assessment configuration, kept separate from the staff-managed catalog),
  and `apps/web` (3000). See "Running the chat agent" below.
- **Needs a Gemini API key.** The chat, document OCR and assessment agents
  call Google's Gemini API (`GEMINI_API_KEY` in `services/agent-backend/.env`)
  — without a working key (and network access to
  `generativelanguage.googleapis.com`), the plain form still works fine, but
  `/customer/chat` will show connection errors past the opening greeting.
- **One bank per chat deployment (for now).** `PLATFORM_BANK_ID` in
  `services/agent-backend/.env` picks which bank's catalog the assistant
  offers — like a bank's own branded assistant, not a cross-bank
  marketplace. Multi-bank chat is a natural next step, not a redesign.
- Signing in with a customer account and using the chat ties the resulting
  application to that real account; you can also use the chat signed out to
  explore discovery/interview, but submitting a real application requires
  being signed in as a customer.

## Quickest path — Docker only

No Node/Python needed locally.

```bash
docker compose up --build
```

Once the containers are up, run migrations and seed (one-time — or again if
you're upgrading from v3, see "Upgrading from v3" below):
```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m scripts.seed
```

Then open **http://localhost:3000/login** and sign in with any of:

| Role                          | Email               | Password       |
|--------------------------------|---------------------|----------------|
| Admin (platform-wide)          | admin@bank.com      | Admin@123      |
| Staff — Credit Manager         | manager@bank.com    | Manager@123    |
| Staff — Loan Officer           | officer@bank.com    | Officer@123    |
| Customer                       | customer@bank.com   | Customer@123   |

Admin lands on `/admin`. The Credit Manager lands on `/staff` with full bank
self-service (Team, Products, Policies, Applications, Notifications). The
Loan Officer lands on the same portal but only sees Overview, Applications
and Notifications — Team/Products/Policies are hidden and blocked, since
that position's `can_manage_staff`/`can_manage_products` are both `false`.
The customer lands on `/customer` and can apply for a loan right away.

**Change these passwords / regenerate the encryption key before this goes anywhere near a real deployment** — see "Security notes" below.

### Upgrading from v3

If you already have a v3 database running, you only need to run the new
migration — your data is preserved:
```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m scripts.seed
```
The seed script is idempotent and safe to re-run. Note: the old
`staff@bank.com` account from v3 no longer exists in the seed — it's been
replaced with `manager@bank.com` (Credit Manager) and `officer@bank.com`
(Loan Officer) so the position hierarchy has something to demonstrate. If
you created other staff accounts under v3, they'll have `position_id = null`
until you (or a manager) assign them one from the Team page.

## Native setup (no Docker for the apps)

### 1. Frontend
```bash
cd apps/web
npm install
```

### 2. Backend
```bash
cd services/api
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
cp .env.example .env
```

### 3. Start Postgres
```bash
docker compose up -d db
```

### 4. Migrate + seed
```bash
cd services/api
alembic upgrade head
python -m scripts.seed
```

### 5. Run both apps (two terminals)
```bash
cd services/api && uvicorn app.main:app --reload
cd apps/web && npm run dev
```

## Running the chat agent (`services/agent-backend`)

Optional but needed for `/customer/chat` — the plain form works without it.

```bash
cd services/agent-backend
python -m venv venv && source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env   # fill in GEMINI_API_KEY, and PLATFORM_BANK_ID with a real bank's id
                        # from `select id, name from banks;` — CATALOG_API_KEY must match
                        # services/api's SERVICE_API_KEY (same dev default if you haven't changed it)
```

Run each service's migrations (they share the one Postgres database, in
their own schemas, so this only needs doing once each):
```bash
alembic -c mock_core_banking/alembic.ini upgrade head
alembic -c app/alembic.ini upgrade head
python -m mock_core_banking.seed          # document requirements, HEM/shading policy
python -m mock_core_banking.seed_rules    # Five C's rules
```

Then run the two extra services (two more terminals):
```bash
cd services/agent-backend && python -m uvicorn mock_core_banking.main:app --port 9000
cd services/agent-backend && python run.py   # the agent itself, port 8001
```

Set `NEXT_PUBLIC_AGENT_API_URL=http://localhost:8001` in `apps/web/.env.local`
(see `.env.local.example`) so the frontend knows where to find it.

## Project structure

```
apps/web/                 Next.js 14 frontend
  app/login/, app/register/  Split-panel auth pages (AuthShell component)
  app/admin/                  Admin portal (layout + Overview/Users/Products/Policies/Audit)
  app/staff/                   Bank self-service portal:
    layout.tsx                   Sidebar shell, permission-gated nav, notification bell
    page.tsx                     Overview (position, approval limit, pending counts)
    team/, products/, policies/  Permission-gated management pages (Add-* modals)
    applications/                 All applications submitted to the bank
    notifications/                 Position-targeted alerts, mark-as-read
  app/customer/               Apply-for-a-loan form + "My applications" list
  app/customer/chat/          Chat UI for the conversational intake flow (talks to agent-backend)
  lib/agent-api.ts            Typed fetch client for services/agent-backend (separate from lib/api.ts)
  components/ui/               Shared UI kit — Button, Input/Field/Select, Card, Badge, Modal, Toast, Skeleton
  components/icons.tsx          Small dependency-free inline SVG icon set
  lib/api.ts                    Typed fetch client for the FastAPI backend
  lib/auth-context.tsx           Auth state (token + user), login/register/logout
  lib/staff-context.tsx           Bank positions + notifications for the staff portal

services/api/              FastAPI backend
  app/models/                SQLAlchemy models — 16 tables + bank_positions, notifications
  app/schemas/                 Pydantic request/response schemas (schemas/bank.py is new)
  app/api/routes/                auth.py, admin.py, bank.py (staff self-service), loans.py (customer)
  app/core/                       config, JWT + password hashing, deps.py (role/permission checks),
                                    lending_logic.py (auto-approve/escalate routing)
  app/db/                          session, declarative base, EncryptedString custom type
  migrations/                     Alembic — init + bank-hierarchy-and-notifications + v5 catalog-contract fields
  scripts/seed.py                 Default data, demo logins, and the position ladder

services/agent-backend/    LangGraph chat agent — discovery/interview, document OCR, Five C's assessment
  app/agents/                 interaction/ (discovery + interview graphs), document/ (OCR + reconcile),
                                assessment/ (Five C's metrics + rules engine)
  app/api/                     interview.py (chat turns + /submit bridge), documents.py, assessment.py
  app/services/core_banking.py  CatalogClient (→ services/api) + AssessmentConfigClient (→ mock_core_banking)
  app/core/identity.py          Validates services/api's JWT to tie a session to a real customer
  mock_core_banking/            Bundled service — document-requirement checklists, HEM/shading policy, rules
  app/alembic/, mock_core_banking/alembic/   Separate migration chains for the two schemas this service owns
```

## Security notes (read before this leaves your laptop)

- `JWT_SECRET` and `FERNET_KEY` (in `app/core/config.py`, overridable via `.env`)
  are dev placeholders committed for convenience. Generate real ones before any
  shared or deployed use:
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- Sensitive fields (`users.phone`, `applicant_profiles.national_id`,
  `applicant_profiles.monthly_income`) are encrypted at rest via the
  `EncryptedString` column type — but only as strong as `FERNET_KEY`.
- The seeded passwords are placeholders. Change them (or delete the seeded
  users) before this is anything but a local demo.
- Position/permission checks are enforced server-side
  (`require_bank_permission` in `app/core/deps.py`) on every mutating bank
  endpoint — the UI hiding a nav link is a convenience, not the security
  boundary.

## Roadmap

Phases 1–3 (scaffold, real schema + migration, auth) and Phase 5 (Admin
portal UI) are done. Phase 4/7 (loan application flow, deterministic
auto-approval/escalation routing, position-based notifications) has two
front doors now — the plain form and the chat agent — both converging on
the same routing. Phase 6 (the LangGraph multi-agent layer: conversational
intake, document OCR/verification, a Five C's credit assessment, a rules
engine) is built and running as `services/agent-backend` (v5) — see "What's
new in v5" above and `db-schema-design.md` §8 for the integration details
and what's still split across the two systems. Still ahead: Phase 8 (AI
configuration and integrations actually being written to by the app), a
real external credit bureau (the Five C's assessment today uses declared +
OCR'd document data, not a bureau pull — the adapter is built to be
swappable, per the standing decision to keep that interface clean), and
mirroring the chat agent's Five C's results into this platform's own
`credit_assessments` table so staff can see the full assessment breakdown
next to an escalated application, not just the routing outcome.
