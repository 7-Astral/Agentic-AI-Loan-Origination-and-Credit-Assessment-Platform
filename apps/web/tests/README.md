# Running the frontend test suite

20 tests covering the pieces of the UI that have actually caused bugs or are
easy to silently break: the chat markdown renderer, the loan product cards
(including a direct regression test for the "Select button stayed disabled"
bug from earlier this session), the expired-session redirect logic, and the
401-handling in both API clients (`lib/api.ts` for the main platform,
`lib/agent-api.ts` for the chat agent).

## How it's built

- **Vitest** + **jsdom** + **React Testing Library**. No real browser, no
  dev server, no backend services — everything DOM-related runs in a
  simulated browser inside the test process, and `fetch` is mocked directly
  in the API-client tests (`vi.stubGlobal("fetch", ...)`), so nothing here
  talks to services/api or services/agent-backend.
- Kept deliberately separate from the two Python suites — this is a
  different language/runtime with its own tool (`npm test`), not something
  that plugs into `pytest`.

## One-time setup

Rebuild the `web` image so the new devDependencies (vitest and friends,
added to `package.json`) are actually installed — the container keeps its
own `node_modules` (see `docker-compose.yml`'s `/app/node_modules` volume),
so a plain restart won't pick them up:

```
docker compose up -d --build web
```

## Running the tests

```
docker compose exec web npm test
```

Or, if you'd rather run it directly on your machine instead of through
Docker (equivalent, just needs `npm install` run locally first):

```
cd apps/web
npm install
npm test
```

Add `--watch` (via `npm run test:watch`) while working on something
specific, or point Vitest at one file:

```
docker compose exec web npx vitest run tests/ProductOptionCards.test.tsx
```

A clean run ends with `Tests  20 passed (20)`.

## What's covered

- `components/chat/ChatMarkdown.tsx` — bold/italic/code inline formatting,
  bullet and numbered list detection, paragraph vs. line-break handling.
- `components/chat/ProductOptionCards.tsx` — one card per product, the
  Select button's `disabled` state tracking the `interactive` prop
  (regression test for the "only the most recent turn should be clickable"
  bug), and `onSelect` firing with the right product on click.
- `lib/session.ts`'s `handleExpiredSession()` — clears the stored token and
  redirects to `/login?expired=1`, but only when not already on a login
  page (so it can't redirect-loop).
- `lib/api.ts` and `lib/agent-api.ts`'s shared `request()` 401 handling —
  an authenticated call that comes back 401 (a stale/expired token) should
  trigger `handleExpiredSession()`; a 401 with no token attached (a failed
  login, or an anonymous chat session that hasn't started yet) must not,
  since that's not an expired session at all.

## What's not covered

Nothing here renders a full page or drives real navigation (no Next.js
router, no `next/navigation` mocking) — these are unit/component tests for
the pieces with actual logic in them, not end-to-end page tests. The bigger
page components (chat page, admin dashboards, etc.) are mostly composition
and data-fetching wiring around the pieces tested here.
