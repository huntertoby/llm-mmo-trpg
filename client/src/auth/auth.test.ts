import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { AuthStatus } from "../api/types";
import {
  accountLine,
  AUTH_TOKEN_KEY,
  authHeaders,
  loginProblem,
  needsLogin,
  readToken,
  worldGate,
  writeToken,
} from "./auth";

const account = { account_id: "a1", username: "alice", characters: 1, max_characters: 3, can_create: true, admin: false };

describe("token storage", () => {
  const store = new Map<string, string>();
  beforeEach(() => {
    store.clear();
    vi.stubGlobal("window", {
      localStorage: {
        getItem: (k: string) => store.get(k) ?? null,
        setItem: (k: string, v: string) => void store.set(k, v),
        removeItem: (k: string) => void store.delete(k),
      },
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("round-trips and clears", () => {
    expect(readToken()).toBeNull();
    writeToken("t0");
    expect(store.get(AUTH_TOKEN_KEY)).toBe("t0");
    expect(readToken()).toBe("t0");
    writeToken(null);
    expect(readToken()).toBeNull();
  });

  it("does not throw when storage is blocked", () => {
    vi.stubGlobal("window", {
      get localStorage(): never {
        throw new Error("blocked");
      },
    });
    expect(readToken()).toBeNull();
    expect(() => writeToken("x")).not.toThrow();
  });
});

describe("auth helpers", () => {
  it("builds the bearer header", () => {
    expect(authHeaders(null)).toEqual({});
    expect(authHeaders("")).toEqual({});
    expect(authHeaders("abc")).toEqual({ Authorization: "Bearer abc" });
  });

  it("validates the login form", () => {
    expect(loginProblem("", "x")).toBe("請輸入帳號");
    expect(loginProblem("alice", "")).toBe("請輸入密碼");
    expect(loginProblem("a".repeat(21), "x")).toContain("20");
    expect(loginProblem("alice", "x")).toBeNull();
  });

  it("picks the gate", () => {
    const off: AuthStatus = { dev_mode: false, account: null };
    expect(worldGate(off)).toBe("login");
    expect(worldGate({ ...off, dev_mode: true })).toBe("world");
    expect(worldGate({ ...off, account })).toBe("world");
  });

  it("describes the account", () => {
    expect(accountLine({ dev_mode: true, account: null })).toBe("開發模式（不用登入）");
    expect(accountLine({ dev_mode: false, account })).toBe("帳號 alice・角色 1／3");
  });

  it("redirects to login on 401 except for the login endpoint itself (5D-R2)", () => {
    expect(needsLogin(401, "/runs/start-options")).toBe(true);
    expect(needsLogin(401, "/world/characters")).toBe(true);
    expect(needsLogin(401, "/auth/login")).toBe(false);
    expect(needsLogin(403, "/runs")).toBe(false);
    expect(needsLogin(404, "/runs/saves")).toBe(false);
  });
});
