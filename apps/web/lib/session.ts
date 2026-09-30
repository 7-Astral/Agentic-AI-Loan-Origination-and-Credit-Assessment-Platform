// Shared by lib/api.ts and lib/agent-api.ts (services/api and agent-backend
// verify the same JWT and both raise 401 "Invalid or expired token" for it —
// see app/core/deps.get_current_user and agent-backend's
// app/core/identity.get_customer_id_from_token). Without this, an expired
// token surfaced as a raw error on whatever the person happened to be doing
// (submitting a form, sending a chat message) with no way forward except
// guessing to log out — this clears the stale token and sends them to
// /login instead, the moment an authenticated call comes back 401.
export function handleExpiredSession() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem("lo_token");
  if (!window.location.pathname.startsWith("/login")) {
    window.location.href = "/login?expired=1";
  }
}
