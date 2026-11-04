// 6N-6 追加（美術 PM 6N-5 驗收）：目標不能動時沒打中不播閃避、字樣寫「失手」；「暴擊 −N」縮小。
import { describe, expect, it } from "vitest";
import type { BattleView } from "../api/types";
import { BIG_MAX_CELLS, BIG_RATIO, BIG_REST, floatFit, floatFontSize, floatFrame, FLOAT_FONT } from "../render/uiAnim";
import { feedbackFor, immobileIn, isImmobileStatus, WORD_DODGE, WORD_MISS, type FloatItem } from "./feedback";
import { logLines } from "./log";
import { unitNames } from "./units";
import { withSpecials } from "./specials";
import { vfxFor } from "./vfx";
import glossaryAll from "./fixtures/glossary.json";

const HERO = "u_hero";
const FOE = "u_foe";

function view(foeStatuses: string[] = []): BattleView {
  return {
    map_id: "bamboo_grove",
    units: [
      { id: HERO, name_zh: "主角", pos: { x: 1, y: 1 }, team: "ally", max_hp: 20, statuses: [] },
      { id: FOE, name_zh: "盜賊", pos: { x: 2, y: 1 }, team: "enemy", max_hp: 20, statuses: foeStatuses.map((status_id) => ({ status_id, remaining: 1 })) },
    ],
    tiles: [],
  } as unknown as BattleView;
}
const miss = [{ seq: 4, round: 1, type: "attack_rolled", attacker_id: HERO, target_id: FOE, hit: false }];
const words = (v: BattleView) => feedbackFor(miss, v).filter((i): i is FloatItem => i.kind === "float").map((f) => f.text);

describe("a miss on a target that cannot move", () => {
  it("the immobile statuses come from the status data (skip_turn / prevents_move) plus the prone posture (6R-F)", () => {
    const ids = (glossaryAll.statuses as { id: string }[]).map((s) => s.id).filter(isImmobileStatus).sort();
    expect(ids).toEqual(["frozen", "prone", "root", "stun"]);
    expect(isImmobileStatus("slow")).toBe(false);
    expect(isImmobileStatus("no_such_status")).toBe(false);
    expect(immobileIn(view(["stun"]))(FOE)).toBe(true);
    expect(immobileIn(view(["slow", "burning"]))(FOE)).toBe(false);
    expect(immobileIn(view(["stun"]))(HERO)).toBe(false);
  });

  it("a free target dodges: 閃避 and a dodge clip", () => {
    expect(words(view())).toEqual([WORD_DODGE]);
    expect(vfxFor(miss, view(), {}).reactions?.map((r) => r.kind)).toEqual(["dodge"]);
  });

  for (const s of ["frozen", "stun", "prone", "root"]) {
    it(`${s}: no dodge clip, no dodge highlight, the float says 失手`, () => {
      const v = view([s]);
      expect(words(v)).toEqual([WORD_MISS]);
      const vfx = vfxFor(miss, v, {});
      expect(vfx.reactions ?? []).toEqual([]);
      const special = withSpecials(vfx, miss, v, v);
      expect((special.specials ?? []).filter((x) => x.kind === "dodge")).toEqual([]);
    });
  }

  it("the battle log keeps the server's wording (失手)", () => {
    const ev = [{ ...miss[0]!, text: "主角 攻擊 盜賊：失手" }];
    const text = logLines([{ events: ev }], unitNames(view(["frozen"]))).map((l) => l.text).join(" ");
    expect(text).toContain("失手");
    expect(text).not.toContain(WORD_DODGE);
  });
});

describe("crit float size", () => {
  it("rests at 1.3× the normal damage number", () => {
    expect(floatFontSize(false)).toBe(FLOAT_FONT);
    const restBig = floatFontSize(true) * floatFrame(0.6, true).scale;
    const restNormal = floatFontSize(false) * floatFrame(0.6, false).scale;
    expect(restBig / restNormal).toBeCloseTo(BIG_RATIO, 9);
    expect(floatFrame(0.6, true).scale).toBe(BIG_REST);
  });

  it("the whole string is at most 1.8 cells wide at rest; shorter strings are not shrunk", () => {
    const cell = 48;
    // 量到的寬度約 ＝ 字數 × 字級（中文全形）；「暴擊 −9」短、「暴擊 −1234」長
    for (const chars of [4, 5, 6, 7, 9]) {
      const width = chars * floatFontSize(true) * 0.75;
      const fit = floatFit(width, cell, true);
      expect(fit).toBeLessThanOrEqual(1);
      expect(width * BIG_REST * fit).toBeLessThanOrEqual(BIG_MAX_CELLS * cell + 1e-9);
      if (width * BIG_REST <= BIG_MAX_CELLS * cell) expect(fit).toBe(1);
    }
    expect(floatFit(500, cell, false)).toBe(1);
  });
});
