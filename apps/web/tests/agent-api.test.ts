import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/session", () => ({
  handleExpiredSession: vi.fn(),
}));

import { handleExpiredSession } from "@/lib/session";
import { agentApi, AgentApiError } from "@/lib/agent-api";

// Same 401-vs-token guard as lib/api.ts, but agent-backend also serves fully
// anonymous sessions (start() is often called with token=null before the
// applicant ever logs in) — those must never trigger the redirect either.

describe("agentApi request() 401 handling", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("triggers handleExpiredSession when an authenticated turn comes back 401", async () => {
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      json: async () => ({ detail: "Invalid or expired token" }),
    });

    await expect(agentApi.sendMessage("stale-token", "session-1", "hi")).rejects.toBeInstanceOf(AgentApiError);
    expect(handleExpiredSession).toHaveBeenCalledTimes(1);
  });

  it("does not trigger handleExpiredSession for an anonymous (no-token) call", async () => {
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      json: async () => ({ detail: "Some other reason" }),
    });

    await expect(agentApi.start(null)).rejects.toBeInstanceOf(AgentApiError);
    expect(handleExpiredSession).not.toHaveBeenCalled();
  });
});
