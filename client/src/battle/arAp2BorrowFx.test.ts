// AR-AP2：預支的施放演出 `borrow_pull`（`borrowFx.ts` 的位置與時間軸、`skillClips.ts` 的片段、接到播放計畫）。
// 事件是真引擎跑的（`dev/fixtures/ap2Events.json`：U1 施放預支 +1，自身）。美術：docs/art/AP-2-美術.md 第 4 節、5.3。
import { describe, expect, it } from "vitest";
import type { BattleResponse, BattleView, SkillCard, StepOut, UnitView } from "../api/types";
import fixture from "../dev/fixtures/ap2Events.json";
import { clipDef, PRIMITIVE_PLAYS } from "../render/skillClips";
import { BORROW_MS, borrowFrame, borrowMK, CHEST_DY, chestAt, GEM_R, MIN_GEM_PX, SLOT_R, slotAt } from "./borrowFx";
import { frameOps, playbackPlan } from "./playback";
import { UPPER_HP_BOTTOM } from "./rerollFx";
import { tile, unit } from "./testFixtures";
import { TILE_SIZE } from "./geometry";

const HERO = "unit_0001";
const SKILL = "skill_t_prim";
const EVENTS = (fixture as unknown as { borrow: { events: Record<string, unknown>[] } }).borrow.events;

export function borrowView(units: UnitView[]): BattleView {
  const tiles = [];
  for (let y = 0; y < 7; y++) for (let x = 0; x < 9; x++) tiles.push(tile(x, y));
  return { team: "ally", map_id: "t", width: 9, height: 7, tiles, objects: [], units, traps: [], turn_order: [HERO], active_unit: HERO, round: 1, max_rounds: 30, pending: null, source_wells: [], zones: [], runes: [] } as unknown as BattleView;
}
export const BORROW_CARD = { id: SKILL, shape: "自身", skeleton: "aura", effect_ids: ["borrow_ap"], icon: { segments: [{ skeleton: "aura", shape_id: "self", range: 0, effects: [{ type: "borrow_ap" }] }] } } as unknown as SkillCard;
const resOf = (): BattleResponse => {
  const before = borrowView([unit(HERO, "ally", 1, 3, { ap: 3 }), unit("unit_0002", "enemy", 6, 6)]);
  const after = borrowView([unit(HERO, "ally", 1, 3, { ap: 4, ap_borrowed: 1, ap_next_loss: 1, ap_next_loss_borrowed: 1 }), unit("unit_0002", "enemy", 6, 6)]);
  return { steps: [{ actor_id: HERO, events: EVENTS, view: after, step: { type: "use_skill", unit_id: HERO, skill_id: SKILL } } as unknown as StepOut], initial_view: before, view: after } as unknown as BattleResponse;
};
const plan = () => playbackPlan(resOf(), HERO, "normal", { [SKILL]: BORROW_CARD }, new Set(), () => "staff", () => null, () => null, false);

describe("片段 borrow_pull（5.3 第 1、2 點）", () => {
  it("預支換成專屬的拉回片段：320 ms（不超過拍肩），另一隻手前伸、拉回、回站姿；特效 borrowSlot 整段", () => {
    expect(PRIMITIVE_PLAYS.borrow_ap).toEqual({ role: "post", clip: "borrow_pull" });
    const d = clipDef("borrow_pull");
    expect(d.ms).toBe(320);
    expect(d.ms).toBeLessThanOrEqual(clipDef("shoulder_tap").ms);
    expect(d.anchor).toBe("offhand");
    expect(d.keys.map(([t]) => t)).toEqual([0, 0.34, 0.75, 1]);
    expect(d.keys[1]![1]).toEqual({ armF: -1.7, elbowF: -0.1, lean: 0.1 });
    expect(d.keys[2]![1]).toEqual({ armF: -0.5, elbowF: -1.7, lean: -0.18 });
    expect(d.fx).toEqual([{ kind: "borrowSlot", where: "feet", from: 0, to: 1 }]);
    expect(d.hitAt).toBeUndefined();
  });
  it("真引擎事件 → 播放計畫：施放者那一列有 borrow_pull（不再是拍肩）", () => {
    const rows = plan().frames.flatMap((f) => frameOps(f)).flatMap((op) => (op.op === "vfx" ? (op.skill ?? []) : []));
    expect(rows.some((r) => r.unitId === HERO && r.clip === "borrow_pull" && !r.recover)).toBe(true);
    expect(rows.some((r) => r.clip === "shoulder_tap")).toBe(false);
  });
});

describe("位置與畫面下限（5.3 第 3、4、5 點）", () => {
  it("菱形半對角 ≥ 4.5 畫面 px：1600 寬（1.31）MK 1、800 寬（0.53）約 1.70", () => {
    expect(borrowMK(1.31)).toBe(1);
    expect(borrowMK(0.53)).toBeCloseTo(4.5 / (5 * 0.53), 6);
    for (const s of [0.4, 0.53, 0.8, 1, 1.31, 2]) expect(GEM_R * borrowMK(s) * s).toBeGreaterThanOrEqual(MIN_GEM_PX - 1e-9);
  });
  it("那格：前推 17＋(MK−1)×8、上緣不高於上一排血條下緣＋1（1600、800 都沒碰到上一排）；西向對稱", () => {
    for (const s of [0.53, 1.31]) {
      const mk = borrowMK(s), p = slotAt(1, mk);
      expect(p.x).toBeCloseTo(17 + (mk - 1) * 8, 6);
      expect(p.y - (SLOT_R + 1.9) * mk).toBeGreaterThanOrEqual(UPPER_HP_BOTTOM + 1 - 1e-9);
      expect(slotAt(-1, mk)).toEqual({ x: -p.x, y: p.y });
    }
    expect(slotAt(1, 1).y).toBe(-9); /* 1600 寬：格子中心往上 9 */
  });
  it("胸口＝遊戲端 chest()（腳底往上 T×0.35＝16.8）、往面向 3", () => {
    expect(CHEST_DY).toBeCloseTo(TILE_SIZE * 0.23 - 16.8, 6);
    expect(chestAt(1)).toEqual({ x: 3, y: CHEST_DY });
    expect(chestAt(-1)).toEqual({ x: -3, y: CHEST_DY });
  });
});

describe("時間軸（第 4 節的表）", () => {
  const f = (t: number) => borrowFrame(t, 1, 1)!;
  it("0–90 那格浮出（0.6 → 1、淡入），菱形在那格裡 0.72", () => {
    expect(f(0).slot.a).toBe(0);
    expect(f(0).slot.k).toBeCloseTo(0.6, 6);
    expect(f(90).slot).toMatchObject({ k: 1, a: 1, slash: 0 });
    expect(f(95).gem.k).toBeCloseTo(0.72, 6);
    expect(f(95).gem).toMatchObject({ x: slotAt(1, 1).x, y: slotAt(1, 1).y });
  });
  it("100–230 菱形沿往上拱的弧線飛到胸口，170 長到 1；150–220 紅斜線畫出來", () => {
    expect(f(170).gem.k).toBeCloseTo(1, 6);
    expect(f(150).slot.slash).toBe(0);
    expect(f(220).slot.slash).toBe(1);
    const mid = f(165).gem, ch = chestAt(1), s = slotAt(1, 1);
    expect(mid.y).toBeLessThan(Math.min(s.y, ch.y)); /* 往上拱 */
    expect(f(230).gem.x).toBeCloseTo(ch.x, 6);
    expect(f(230).gem.y).toBeCloseTo(ch.y, 6);
  });
  it("215–320 光圈；菱形縮到 0.65；230–320 那格淡出、260–320 菱形淡出；超出 320 不畫", () => {
    expect(f(214).arrive.p).toBe(0);
    expect(f(270).arrive.p).toBeGreaterThan(0);
    expect(f(320).gem.k).toBeCloseTo(0.65, 6);
    expect(f(320).slot.a).toBe(0);
    expect(f(320).gem.a).toBe(0);
    expect(f(250).gem.a).toBe(1);
    expect(borrowFrame(321, 1, 1)).toBeNull();
    expect(borrowFrame(-1, 1, 1)).toBeNull();
    expect(BORROW_MS).toBe(320);
  });
});
