import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/session", () => ({
  handleExpiredSession: vi.fn(),
}));

import { handleExpiredSession } from "@/lib/session";
import { api, ApiError } from "@/lib/api";

// lib/api.ts's request() only calls handleExpiredSession on a 401 when a
// token was passed in — a failed login attempt also returns 401 but never
// carries a token, and must not bounce the user through the expired-session
// redirect (see the comment in lib/api.ts above that check).

describe("api request() 401 handling", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("triggers handleExpiredSession on a 401 for an authenticated call", async () => {
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      json: async () => ({ detail: "Invalid or expired token" }),
    });

    await expect(api.me("stale-token")).rejects.toBeInstanceOf(ApiError);
    expect(handleExpiredSession).toHaveBeenCalledTimes(1);
  });

  it("does not trigger handleExpiredSession on a failed login (no token yet)", async () => {
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 401,
      statusText: "Unauthorized",
      json: async () => ({ detail: "Incorrect email or password" }),
    });

    await expect(api.login("a@b.com", "wrong")).rejects.toBeInstanceOf(ApiError);
    expect(handleExpiredSession).not.toHaveBeenCalled();
  });

  it("resolves normally on a successful response", async () => {
    (fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: "u1", email: "a@b.com", full_name: "A", role: "customer", bank_id: null, position_id: null, is_active: true }),
    });

    const user = await api.me("good-token");
    expect(user.email).toBe("a@b.com");
    expect(handleExpiredSession).not.toHaveBeenCalled();
  });
});
