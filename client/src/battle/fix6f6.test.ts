// 6F-6 戰鬥介面小修：浮動字錯開、閃避／失手照打的那一刻、只在我方倒地者畫復活愛心。
import { describe, expect, it } from "vitest";
import type { BattleView } from "../api/types";
import { FloatStack, FLOAT_STACK_GAP, groupRise, stackedY, stackOffsets } from "../render/floatStack";
import { FLOAT_RISE_MAX } from "../render/uiAnim";
import { downedLook } from "../render/unitLook";
import { buildDrawModel, showsRevivable } from "./drawModel";
import { feedbackFor, immobilityOf, WORD_DODGE, WORD_MISS, type FloatItem } from "./feedback";
import { smallView, unit } from "./testFixtures";
import { vfxFor, type VfxCast } from "./vfx";
import { clipHighlights, mapClipRect } from "../render/mapClip";
import { castEffects } from "../render/vfxEffects";
import { tileLift } from "./elevation";

/** 兩個字（中心 y、高度）的外框不重疊。 */
const apart = (a: { y: number; h: number }, b: { y: number; h: number }) => Math.abs(a.y - b.y) >= (a.h + b.h) / 2;

describe("6F-6 floating text stacks instead of overlapping", () => {
  it("offsets follow the real heights (a crit line is taller than a plain one)", () => {
    const off = stackOffsets([28, 34, 28]);
    expect(off[0]).toBe(0);
    expect(off[1]).toBe((28 + 34) / 2 + FLOAT_STACK_GAP);
    expect(off[2]).toBe((off[1] ?? 0) + (34 + 28) / 2 + FLOAT_STACK_GAP);
  });

  it("the trap-clamp case: 擊倒、暴擊 −9、＋倒地 at rest never overlap", () => {
    const heights = [28, 35, 28];
    const off = new FloatStack().place("4,3", 0, 900, heights);
    const ys = off.map((o) => stackedY(200, o, 0));
    for (let i = 1; i < heights.length; i++) expect(apart({ y: ys[i - 1]!, h: heights[i - 1]! }, { y: ys[i]!, h: heights[i]! })).toBe(true);
  });

  it("a later beat on the same cell starts above the words that are still playing, with room for their rise", () => {
    const st = new FloatStack();
    const first = st.place("2,2", 0, 900, [28]);
    const second = st.place("2,2", 300, 1200, [28]);
    expect(first).toEqual([0]);
    // 舊字還在往上飄（最多 FLOAT_RISE_MAX），新字從它的上緣再往上留一段
    expect(second[0]).toBe(14 + FLOAT_RISE_MAX + FLOAT_STACK_GAP + 14);
    // 舊字飄到最高時，新字（剛出現、還沒飄）仍在它上面
    expect(apart({ y: 200 - first[0]! - FLOAT_RISE_MAX, h: 28 }, { y: 200 - second[0]!, h: 28 })).toBe(true);
    // 另一格不受影響；舊字播完後同一格從頭算
    expect(st.place("3,2", 300, 1200, [28])).toEqual([0]);
    expect(st.place("2,2", 1300, 2000, [28])).toEqual([0]);
  });

  it("words of one group rise together, so a later word is never caught by an earlier one", () => {
    const delay = 0.15;
    for (const p of [0, 0.1, 0.3, 0.6, 1]) {
      // 第 0 個的進度 g；第 1 個晚 delay 才開始，自己的進度 (g - delay)/(1 - delay)
      const g = delay + p * (1 - delay);
      expect(groupRise(p, delay, 16)).toBeCloseTo(groupRise(g, 0, 16), 9);
    }
    expect(groupRise(1, 0.3, 22)).toBe(22);
  });

  it("no room above the head (first rows): the whole group is pushed down together, order and spacing kept", () => {
    const limit = 40;
    const heights = [28, 28, 28];
    const off = new FloatStack().place("0,0", 0, 900, heights);
    const top = Math.max(...off);
    for (const natural of [30, 70]) {
      // 30：一個都放不下；70：只放得下前兩個（舊做法第三個會掉到身體上、和別的字分開）
      const ys = off.map((o) => stackedY(natural, o, limit, top));
      expect(ys[2]).toBe(limit); // 最上面那個剛好在上限
      for (let i = 1; i < 3; i++) {
        expect(ys[i]!).toBeLessThan(ys[i - 1]!); // 順序不變：後來的在上面
        expect(apart({ y: ys[i - 1]!, h: 28 }, { y: ys[i]!, h: 28 })).toBe(true);
      }
      for (const y of ys) expect(y).toBeGreaterThanOrEqual(limit);
    }
    // 有空間時照舊往上，不推
    expect(off.map((o) => stackedY(300, o, limit, top))).toEqual(off.map((o) => 300 - o));
  });
});

const HERO = "u_hero";
const FOE = "u_foe";
function duel(foe: string[] = []): BattleView {
  return {
    map_id: "bamboo_grove",
    units: [unit(HERO, "ally", 1, 1), unit(FOE, "enemy", 2, 1, { statuses: foe.map((status_id) => ({ status_id, remaining: 1 })) as never })],
    tiles: [],
  } as unknown as BattleView;
}
const words = (events: Record<string, unknown>[], after: BattleView, before: BattleView) =>
  feedbackFor(events, after, immobilityOf(events, before))
    .filter((i): i is FloatItem => i.kind === "float")
    .map((f) => f.text);
const missAt = (seq: number) => ({ seq, round: 1, type: "attack_rolled", attacker_id: HERO, target_id: FOE, hit: false });

describe("6F-6 dodge or miss is judged at the moment of the swing", () => {
  it("free before, frozen later in the same step: the miss is still a dodge (float and dodge clip)", () => {
    const events = [missAt(1), { seq: 2, round: 1, type: "status_applied", target_id: FOE, status_id: "frozen", duration: 1, refreshed: false, source_id: HERO }];
    expect(words(events, duel(["frozen"]), duel())).toEqual([WORD_DODGE]);
    expect(vfxFor(events, duel(["frozen"]), {}, immobilityOf(events, duel())).reactions?.map((r) => r.kind)).toEqual(["dodge"]);
  });

  it("stunned before the swing: 失手, no dodge clip", () => {
    const events = [missAt(1)];
    expect(words(events, duel(["stun"]), duel(["stun"]))).toEqual([WORD_MISS]);
    expect(vfxFor(events, duel(["stun"]), {}, immobilityOf(events, duel(["stun"]))).reactions ?? []).toEqual([]);
  });

  it("stood up earlier in the same step, then missed: 閃避", () => {
    const events = [{ seq: 1, round: 1, type: "status_removed", target_id: FOE, status_id: "prone", reason: "stood_up" }, missAt(2)];
    expect(words(events, duel(), duel(["prone"]))).toEqual([WORD_DODGE]);
  });

  it("rooted earlier in the same step, then missed: 失手; events the pause already showed are skipped but still counted", () => {
    const events = [{ seq: 1, round: 1, type: "status_applied", target_id: FOE, status_id: "root", duration: 1, refreshed: false, source_id: HERO }, missAt(2)];
    const still = immobilityOf(events, duel());
    const shown = feedbackFor([events[1]!], duel(["root"]), still).filter((i): i is FloatItem => i.kind === "float");
    expect(shown.map((f) => f.text)).toEqual([WORD_MISS]);
  });

  it("without a before view the old rule (after view) still applies", () => {
    expect(feedbackFor([missAt(1)], duel(["frozen"])).filter((i): i is FloatItem => i.kind === "float").map((f) => f.text)).toEqual([WORD_MISS]);
  });
});

describe("6F-6 the revive heart only on our own downed units", () => {
  const v = smallView({
    units: [
      unit("unit_0001", "ally", 0, 0),
      unit("unit_0002", "ally", 0, 1, { hp: 0, downed: true, revivable: true }),
      unit("unit_0003", "enemy", 2, 1, { hp: 0, downed: true, revivable: true }),
      unit("unit_0004", "third", 2, 0, { hp: 0, downed: true, revivable: true }),
      unit("unit_0005", "ally", 1, 1, { hp: 0, downed: true, revivable: false }),
    ],
  });
  const byId = (id: string) => v.units.find((u) => u.id === id)!;

  it("ally downed and revivable: heart; enemy or third side: no heart (grave, as lost)", () => {
    expect(showsRevivable(v, byId("unit_0002"), "unit_0001")).toBe(true);
    expect(showsRevivable(v, byId("unit_0003"), "unit_0001")).toBe(false);
    expect(showsRevivable(v, byId("unit_0004"), "unit_0001")).toBe(false);
    expect(showsRevivable(v, byId("unit_0005"), "unit_0001")).toBe(false);
    const model = buildDrawModel(v, "unit_0001");
    const look = (id: string) => {
      const u = model.units.find((x) => x.id === id)!;
      return downedLook(u.downed, u.revivable).badge?.kind;
    };
    expect(look("unit_0002")).toBe("heart");
    expect(look("unit_0003")).toBe("grave");
    expect(look("unit_0004")).toBe("grave");
  });

  it("follows the hero's side (a hero on the enemy team sees hearts on that team)", () => {
    const flipped = smallView({ units: [unit("h", "enemy", 0, 0), unit("a", "enemy", 1, 0, { downed: true, revivable: true }), unit("b", "ally", 2, 0, { downed: true, revivable: true })] });
    expect(showsRevivable(flipped, flipped.units[1]!, "h")).toBe(true);
    expect(showsRevivable(flipped, flipped.units[2]!, "h")).toBe(false);
  });
});

describe("6F-6 area previews and ground effects stay inside the map", () => {
  const grid = { width: 4, height: 3 };
  const P = (x: number, y: number) => ({ x, y });

  it("tiles outside the map are not highlighted (moves, targets, area, range, directions, telegraph)", () => {
    const h = clipHighlights(grid, {
      moves: [P(0, 0), P(-1, 0)],
      attacks: [P(3, 2), P(4, 2)],
      preview: [P(0, -1), P(1, 0), P(2, 3)],
      picked: [P(9, 9)],
      directions: [{ pos: P(0, -1), arrow: "↑" }],
      telegraph: [{ pos: P(1, 1) }, { pos: P(1, 5) }],
      range: [P(-1, -1), P(2, 2)],
      focus: null,
    });
    expect(h.moves).toEqual([P(0, 0)]);
    expect(h.attacks).toEqual([P(3, 2)]);
    expect(h.preview).toEqual([P(1, 0)]);
    expect(h.picked).toEqual([]);
    expect(h.directions).toEqual([]);
    expect(h.telegraph).toEqual([{ pos: P(1, 1) }]);
    expect(h.range).toEqual([P(2, 2)]);
    expect(h.focus).toBeNull();
  });

  it("the clip rect is the map: flat from y 0; a raised tile in the first row lifts the top edge", () => {
    expect(mapClipRect({ width: 4, height: 3, tiles: [] })).toEqual({ x: 0, y: 0, width: 4 * 48, height: 3 * 48 });
    const tiles = Array.from({ length: 12 }, (_, i) => ({ height: i === 2 ? 2 : i === 5 ? 9 : 0 }));
    const r = mapClipRect({ width: 4, height: 3, tiles });
    expect(r.y).toBe(-tileLift(2)); // 只看第一排；第二排更高的格子不把上緣往上推
    expect(r.y + r.height).toBe(3 * 48);
  });

  const cast = (kind: VfxCast["kind"], element = "holy"): VfxCast => ({
    kind,
    element,
    from: P(0, 3),
    to: P(0, 0),
    tiles: [P(0, 0), P(1, 0), P(0, 1)],
    path: [P(0, 3), P(0, 0)],
    ranged: true,
    intensity: 1,
    crit: false,
    charge: true,
    legendary: false,
    chargeMs: 100,
    startMs: 0,
    impactMs: 200,
  });

  it("area bursts (with the holy column) and cones are ground effects; charge, projectile and slash are not", () => {
    const area = castEffects(cast("area"), 0, 100);
    expect(area.filter((e) => e.clip === "map").length).toBe(3); // 每格一個爆發
    expect(area.filter((e) => e.clip !== "map").length).toBe(3 + 1); // 每格的格子閃光（在格內）＋蓄力
    expect(castEffects(cast("cone"), 0, 100).filter((e) => e.clip === "map").length).toBe(1 + 3);
    const proj = castEffects(cast("projectile"), 0, 100);
    expect(proj.map((e) => e.clip ?? "none")).toEqual(["none", "none", "map"]); // 蓄力、飛行物不裁；落點的爆發裁
    expect(castEffects({ ...cast("slash"), tiles: [P(0, 0)] }, 0, 100)[1]?.clip).toBeUndefined();
  });
});
