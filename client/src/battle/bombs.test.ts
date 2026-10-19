import { describe, expect, it } from "vitest";
import type { PreviewOut, StatusView } from "../api/types";
import { bombCountdown, bombLines, bombStatus, bombStatusText, reviveLines } from "./bombs";
import { smallView, unit } from "./testFixtures";
import { unitNames } from "./units";

const bomb = (over: Partial<StatusView> = {}): StatusView => ({
  status_id: "time_bomb",
  remaining: 2,
  source_id: "unit_0001",
  amount: null,
  blast_radius: 1,
  ...over,
});

describe("time bomb status", () => {
  it("reads the countdown from the unit's statuses", () => {
    const carrier = unit("unit_0003", "enemy", 2, 1, { statuses: [bomb({ remaining: 2 })] });
    expect(bombStatus(carrier)?.blast_radius).toBe(1);
    expect(bombCountdown(carrier)).toBe(2);
    expect(bombCountdown(unit("unit_0004", "enemy", 0, 0))).toBeNull();
  });

  it("describes the countdown and flags the one that goes off next", () => {
    expect(bombStatusText(bomb())).toBe("定時炸彈（還要 2 次環境回合爆炸，半徑 1 格）");
    expect(bombStatusText(bomb({ remaining: 1 }))).toContain("下一次環境回合就會爆炸");
  });
});

describe("preview lines", () => {
  const view = smallView();
  const names = unitNames(view);
  const preview = (over: Partial<PreviewOut>) => ({ bombs: [], revives: [], ...over }) as PreviewOut;

  it("lists the bomb with its countdown and blast size", () => {
    const [line] = bombLines(
      preview({ bombs: [{ unit_id: "unit_0003", rounds: 2, radius: 1, tiles: [[2, 1], [1, 1], [3, 1], [2, 0], [2, 2]] }] }),
      names,
    );
    expect(line).toContain("2 次環境回合後");
    expect(line).toContain("半徑 1 格");
    expect(line).toContain("5 格");
    expect(bombLines(preview({}), names)).toEqual([]);
  });

  it("lists the revive and notes a moved landing tile", () => {
    const same = reviveLines(preview({ revives: [{ unit_id: "unit_0002", hp: 6, pos: [0, 1], from_pos: [0, 1] }] }), names);
    expect(same[0]).toContain("以 6 HP 站在 (0, 1)");
    expect(same[0]).not.toContain("被占用");
    const moved = reviveLines(preview({ revives: [{ unit_id: "unit_0002", hp: 6, pos: [0, 2], from_pos: [0, 1] }] }), names);
    expect(moved[0]).toContain("原位置 (0, 1) 被占用");
  });
});
