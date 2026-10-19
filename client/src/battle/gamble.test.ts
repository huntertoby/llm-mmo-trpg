import { describe, expect, it } from "vitest";
import type { PreviewOut } from "../api/types";
import { branchResult, gambleLines, gambleSummary } from "./gamble";
import { previewLines } from "./previewText";
import { smallView } from "./testFixtures";
import { unitNames } from "./units";

const view = smallView();
const names = unitNames(view);

const target = (min: number, max: number) => ({
  unit_id: "unit_0003",
  hit_permille: 800,
  crit_permille: 50,
  damage: { minimum: min, maximum: max, expected_milli: 0, expected_if_hit_milli: 0 },
  ally: false,
  knock_permille: null,
  status_chances: [],
});

const branch = (over: Record<string, unknown>) => ({
  kind: "win",
  permille: 600,
  multiplier_permille: 1000,
  targets: [],
  self_damage_min: 0,
  self_damage_max: 0,
  self_statuses: [],
  self_healed_min: 0,
  self_healed_max: 0,
  ...over,
});

const base = {
  action: { type: "end_turn", unit_id: "unit_0001" },
  hit_permille: 875,
  crit_permille: 50,
  damage: null,
  affected_tiles: [],
  affected_units: [],
  certain: [],
  possible: [],
  cover: null,
  notes: [],
  targets: [],
  healed: [],
  min_events: [],
  max_events: [],
  gamble: {
    chance_permille: 600,
    branches: [
      branch({ kind: "win", permille: 600, multiplier_permille: 2000, targets: [target(16, 32)] }),
      branch({ kind: "lose", permille: 400, targets: [target(8, 16)], self_damage_min: 4, self_damage_max: 8 }),
    ],
  },
} as unknown as PreviewOut;

describe("gamble preview", () => {
  it("summarises both branches with their chances and results", () => {
    expect(gambleSummary(base)).toBe("60%：傷害 ×2（目標 16–32）｜40%：你受 4–8 傷害");
  });

  it("returns nothing for a skill without a gamble", () => {
    const plain = { ...base, gamble: null } as unknown as PreviewOut;
    expect(gambleSummary(plain)).toBeNull();
    expect(gambleLines(plain, names)).toEqual([]);
  });

  it("describes statuses, heals and a fixed self damage; no change is 'as usual'", () => {
    const [win] = base.gamble!.branches;
    expect(branchResult(win)).toBe("傷害 ×2（目標 16–32）");
    expect(branchResult(branch({ self_damage_min: 5, self_damage_max: 5 }) as never)).toBe("你受 5 傷害");
    expect(branchResult(branch({ self_statuses: ["prone"] }) as never)).toBe("你獲得「倒地」");
    expect(branchResult(branch({ self_healed_min: 2, self_healed_max: 6 }) as never)).toBe("你回復 2–6");
    expect(branchResult(branch({}) as never)).toBe("照常");
  });

  it("lists the damage range of each target under each branch", () => {
    const lines = gambleLines(base, names);
    expect(lines[0]).toBe("賭注（命中後擲 d1000）：60%：傷害 ×2（目標 16–32）｜40%：你受 4–8 傷害");
    expect(lines).toContain(`　成功（60%）：${names.label("unit_0003")} 傷害 16–32`);
    expect(lines).toContain(`　失敗（40%）：${names.label("unit_0003")} 傷害 8–16`);
  });

  it("is part of the preview lines, followed by the miss backlash notes", () => {
    const p = { ...base, miss_notes: ["失手時：你獲得「倒地」"] } as unknown as PreviewOut;
    const lines = previewLines(p, names, view);
    expect(lines.some((l) => l.startsWith("賭注（命中後擲 d1000）：60%："))).toBe(true);
    expect(lines).toContain("失手時：你獲得「倒地」");
  });
});
