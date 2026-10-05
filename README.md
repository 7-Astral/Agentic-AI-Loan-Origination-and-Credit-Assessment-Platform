# Agentic AI Loan Origination and Credit Assessment Platform

A loan origination system with three portals (customer, bank staff, admin).
Customers apply by chatting with an assistant, upload their documents, and the
application goes to bank staff with a Five C's credit assessment report.

The AI handles the conversation and reads documents. The assessment is
rule based. Every decision is made by a staff member.

## What you need

Docker Desktop is required. Nothing else has to be installed (no Node, no
Python, no database).

- Download it from https://www.docker.com/products/docker-desktop
- Works on Windows, Mac (Intel and Apple Silicon) and Linux
- Open Docker Desktop and wait until it says it is running before you start

The settings file `agent-backend/.env` is already included, so there is
nothing to configure.

## Setup

1. Install Docker Desktop and make sure it is running.

2. Open a terminal in the project folder and start everything. The first run
   takes a few minutes.

   ```bash
   docker compose up --build
   ```

3. In a second terminal, create the tables and load the demo data. This is
   only needed the first time.

   ```bash
   docker compose exec api alembic upgrade head
   docker compose exec api python -m scripts.seed
   docker compose exec mock-core-banking alembic -c mock_core_banking/alembic.ini upgrade head
   docker compose exec mock-core-banking python -m mock_core_banking.seed
   docker compose exec mock-core-banking python -m mock_core_banking.seed_rules
   docker compose exec agent-backend alembic -c app/alembic.ini upgrade head
   docker compose exec agent-backend python -m scripts.ingest_policies
   ```

   The last command loads the bank policy file into the policy search. It
   takes a minute or two the first time.

4. Open http://localhost:3000/login

## Demo logins

| Role | Email | Password |
|---|---|---|
| Admin | admin@bank.com | Admin@123 |
| Credit Manager | manager@bank.com | Manager@123 |
| Loan Officer | officer@bank.com | Officer@123 |
| Customer | customer@bank.com | Customer@123 |

These are for the demo only.

## Pages

All pages are served from http://localhost:3000

### General

| URL | What it is for |
|---|---|
| `/` | Landing page |
| `/login` | Sign in. Sends each role to its own portal |
| `/register` | Create a new customer account |

### Customer

| URL | What it is for |
|---|---|
| `/customer` | Customer home. Start or continue an application, see past applications, notifications and requests from the bank |
| `/customer/chat` | Chat with the loan assistant: pick a product, answer the questions, upload documents, submit |
| `/customer/chat?session=<id>` | Reopen a submitted application to answer a request from the bank |

### Bank staff

| URL | What it is for |
|---|---|
| `/staff` | Staff overview for their own bank |
| `/staff/applications` | All applications submitted to the bank |
| `/staff/applications/<id>/report` | Assessment report: scores, risks, conditions, documents, chat transcript. Staff record the decision here and can ask the applicant for more information or a document |
| `/staff/team` | Add, edit and deactivate staff (managers only) |
| `/staff/products` | Loan products for the bank (managers only) |
| `/staff/policies` | Lending policies for the bank (managers only) |
| `/staff/notifications` | Notifications for the signed in staff member |
| `/staff/audit` | Audit log for the bank |

### Admin

| URL | What it is for |
|---|---|
| `/admin` | Platform overview |
| `/admin/banks` | Banks on the platform |
| `/admin/users` | All users. Create staff, deactivate or reactivate accounts |
| `/admin/products` | Loan products across banks |
| `/admin/policies` | Lending policies across banks |
| `/admin/audit` | Platform audit log |

### Playground (no login needed)

| URL | What it is for |
|---|---|
| `/playground` | Try the credit assessment with sample applicants or your own numbers |
| `/playground/documents` | Try document reading and see how it is checked against the applicant's answers |
| `/playground/scan` | Watch a document being scanned and its values pulled out |

## Services

| Service | URL | What it does |
|---|---|---|
| Web app | http://localhost:3000 | Next.js frontend |
| Platform API | http://localhost:8000/docs | Logins, banks, products, policies, staff, applications, decisions |
| Agent backend | http://localhost:8001/docs | Chat interview, document reading, Five C's assessment |
| Mock core banking | http://localhost:9100/docs | Interview questions, document checklists, assessment rules and policy |
| Mock credit bureau | http://localhost:9200/docs | Stand in credit bureau |
| Postgres | localhost:5433 | Database (user `postgres`, password `postgres`) |

## Project layout

```
apps/web          Next.js frontend
services/api      Platform API (FastAPI)
agent-backend     Chat agent, document agent, assessment engine (FastAPI + LangGraph)
  mock_core_banking   Assessment configuration service
  mock_bureau         Credit bureau stand in
docker-compose.yml
```

## A typical run through

1. Sign in as the customer and open the chat.
2. Tell the assistant what you need, pick a product and answer the questions.
3. Upload the documents it asks for and submit.
4. Sign in as the Credit Manager and open the application's report.
5. Ask the customer for something if needed, then record the decision.
6. Sign back in as the customer to see the request or the outcome.

## Common problems

- **Chat says it cannot reach the assistant.** Check `GEMINI_API_KEY` in
  `agent-backend/.env`, then run `docker compose restart agent-backend`.
- **AI quota reached.** The free Gemini tiercan has a daily limit. Wait or use
  another key.
- **Document upload fails because of a rate limit.** Skip the upload and
  submit the application anyway. The credit assessment still runs, so you can
  review that part.
- **Changed code in `agent-backend/app` but nothing happened.** That service
  does not auto reload. Run `docker compose restart agent-backend`.
- **Login fails for the demo accounts.** The seed step has not been run. Run
  the commands in step 3.
- **Port already in use.** Stop whatever is using 3000, 8000, 8001, 9100,
  9200 or 5433, or change the port in `docker-compose.yml`.

## Stopping

```bash
docker compose down
```

Add `-v` to also delete the database.


