import { describe, expect, it } from "vitest";
import type { StatusView } from "../api/types";
import { COST_STATUS_NOTE } from "../battle/glossary";
import { statusLine } from "./Hud";

const status = (over: Partial<StatusView> = {}): StatusView => ({
  status_id: "stun",
  remaining: 2,
  source_id: "unit_0001",
  amount: null,
  charge_tiles: [],
  cost_status: false,
  ...over,
});

describe("cost status mark (3-50c)", () => {
  it("marks a cost status as not cleansable in the status line", () => {
    expect(statusLine(status({ cost_status: true }))).toContain(COST_STATUS_NOTE);
    expect(COST_STATUS_NOTE).toBe("（代價狀態，無法淨化）");
  });

  it("leaves an ordinary status unmarked", () => {
    expect(statusLine(status())).not.toContain("無法淨化");
  });
});
