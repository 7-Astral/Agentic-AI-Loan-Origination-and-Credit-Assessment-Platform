import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { handleExpiredSession } from "@/lib/session";

function setLocation(pathname: string) {
  Object.defineProperty(window, "location", {
    value: { pathname, href: `http://localhost${pathname}` },
    writable: true,
  });
}

describe("handleExpiredSession", () => {
  beforeEach(() => {
    window.localStorage.setItem("lo_token", "abc123");
  });

  afterEach(() => {
    window.localStorage.clear();
  });

  it("clears the stored token", () => {
    setLocation("/customer");
    handleExpiredSession();
    expect(window.localStorage.getItem("lo_token")).toBeNull();
  });

  it("redirects to /login?expired=1 when not already on a login page", () => {
    setLocation("/customer");
    handleExpiredSession();
    expect(window.location.href).toBe("/login?expired=1");
  });

  it("does not redirect again when already on a login page", () => {
    setLocation("/login");
    handleExpiredSession();
    // href should be left as whatever it was — never overwritten a second time.
    expect(window.location.href).toBe("http://localhost/login");
  });
});
