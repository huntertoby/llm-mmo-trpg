// RG-3（#162）戰場標記的純函式：誰瞄準誰、準星合併、瞄準線幾何與虛線、照排切段、盾兵連結、看一眼時間軸、
// 「蓄」不再畫在目標格、三個浮字與看一眼的回饋項目、可疑痕跡進 DrawModel。規格 `docs/art/RG樣張.md` 第 2、8 節。
import { describe, expect, it } from "vitest";
import type { PreviewOut, TelegraphOut } from "../api/types";
import { buildDrawModel } from "./drawModel";
import { feedbackFor, WORD_LOCK_BLOCKED, WORD_LOCK_INTERRUPTED, WORD_LOCK_MISS } from "./feedback";
import { TILE_SIZE } from "./geometry";
import {
  aimDraws,
  blinkPhase,
  chipCenter,
  chipY,
  dashes,
  flowOffset,
  glanceDir,
  glanceFrame,
  glanceY,
  guardDraw,
  lineGeom,
  linkDots,
  NORTH_CHIP_DX,
  reticleDraws,
  reticleY,
  RG_MIN,
  splitRows,
} from "./rgMarks";
import { minMarkScale } from "../render/minMark";
import { telegraphMarks } from "./telegraph";
import { smallView, unit } from "./testFixtures";

const T = TILE_SIZE;

function charge(unitId: string, target: string | null, over: Record<string, unknown> = {}) {
  return { unit_id: unitId, skill_id: "skill_crane_piercing_shot", name_zh: "鶴唳穿雲", release: "next_turn", remaining: 1, pos: { x: 0, y: 0 }, tiles: [{ x: 0, y: 0 }], lock_target_id: target, text: "瞄準", ...over };
}

function telegraph(charges: ReturnType<typeof charge>[]): TelegraphOut {
  return { round: 1, changes: [], burning: [], upcoming: [], bombs: [], charges } as TelegraphOut;
}

const view = smallView();

describe("aim draws (lock_target_id)", () => {
  it("draws the caster to its target and reads the server's blocker", () => {
    const t = telegraph([charge("unit_0003", "unit_0001", { lock_blocker_id: "unit_0004" })]);
    expect(aimDraws(t, view)).toEqual([
      { casterId: "unit_0003", targetId: "unit_0001", caster: { x: 2, y: 1 }, target: { x: 0, y: 0 }, blockerId: "unit_0004", blocker: { x: 2, y: 0 } },
    ]);
  });

  it("skips plain charges and anyone not on the field (downed, escaped, hidden)", () => {
    const t = telegraph([charge("unit_0003", null), charge("unit_0004", "unit_0002"), charge("unit_0005", "unit_0001"), charge("unit_0003", "unit_9999")]);
    expect(aimDraws(t, view)).toEqual([]);
    expect(aimDraws(null, view)).toEqual([]);
  });

  it("merges two aims at one target into one reticle; grey only if every line is blocked", () => {
    const a = aimDraws(telegraph([charge("unit_0003", "unit_0001", { lock_blocker_id: "unit_0004" }), charge("unit_0004", "unit_0001")]), view);
    expect(reticleDraws(a)).toEqual([{ targetId: "unit_0001", pos: { x: 0, y: 0 }, blocked: false }]);
    const b = aimDraws(telegraph([charge("unit_0003", "unit_0001", { lock_blocker_id: "unit_0004" })]), view);
    expect(reticleDraws(b)[0]?.blocked).toBe(true);
  });
});

describe("telegraph: the aimed tile has no charge area", () => {
  it("keeps only the caster's 蓄 badge (at the caster, not the target)", () => {
    const marks = telegraphMarks(telegraph([charge("unit_0003", "unit_0001", { pos: { x: 0, y: 0 }, tiles: [{ x: 0, y: 0 }] })]), view);
    expect(marks.map((m) => [m.pos.x, m.pos.y, m.kind, m.glyph])).toEqual([[2, 1, "charge", "蓄1"]]);
  });

  it("plain charges still mark their area", () => {
    const marks = telegraphMarks(telegraph([charge("unit_0003", null, { pos: { x: 2, y: 1 }, tiles: [{ x: 1, y: 1 }] })]), view);
    expect(marks.map((m) => m.kind).sort()).toEqual(["charge", "charge_area"]);
  });
});

describe("marks sit on the measured head top", () => {
  it("reticle, chip and glance offsets follow the spec (k = 1 and the 800 k)", () => {
    expect(reticleY(-26.1, 1)).toBeCloseTo(-26.1 - 4 - 13.6);
    expect(chipY(-26.1, 1)).toBeCloseTo(-26.1 - 2 - 7.85);
    expect(glanceY(-26.1, 1)).toBeCloseTo(-26.1 - 2 - 8);
    // 800 寬地圖縮放 0.53：準星 1.51、小盾 1.48、看一眼 1.62、「？」1.41、線 1.88（樣張第 2 節）
    const k = (s: { base: number; min: number }) => minMarkScale(s.base, s.min, 0.53);
    expect(k(RG_MIN.reticle)).toBeCloseTo(1.51, 2);
    expect(k(RG_MIN.chip)).toBeCloseTo(1.48, 2);
    expect(k(RG_MIN.glance)).toBeCloseTo(1.62, 2);
    expect(k(RG_MIN.question)).toBeCloseTo(1.415, 2);
    expect(k(RG_MIN.line)).toBeCloseTo(1.89, 2);
    expect(k(RG_MIN.reticle) * 0.53 * 20).toBeCloseTo(16);
  });

  it("blinks 520 on / 380 dim; reduced motion stays on", () => {
    expect([0, 519, 520, 899, 900].map((ms) => blinkPhase(ms))).toEqual([0, 0, 1, 1, 0]);
    expect(blinkPhase(700, true)).toBe(0);
  });
});

describe("aim line geometry", () => {
  const a = { x: 0, y: 0 };
  const b = { x: 200, y: 0 };

  it("starts 0.4 tile out, stops 11×k before the reticle", () => {
    const g = lineGeom(a, b, 1, null, null);
    expect(g?.start).toBeCloseTo(0.4 * T);
    expect(g?.end).toBeCloseTo(200 - 11);
    expect(g?.cut).toBeNull();
  });

  it("pushes the start out of the caster's charge badge", () => {
    const g = lineGeom(a, b, 1, { x: 0.4 * T, y: 0 }, null);
    expect(g?.start).toBeGreaterThanOrEqual(0.4 * T + 12 - 0.5);
  });

  it("breaks 0.22 tile before the blocker", () => {
    const g = lineGeom(a, b, 1, null, { x: 100, y: 0 });
    expect(g?.cut).toBeCloseTo(100 - 0.22 * T);
  });

  it("dashes are 4 on / 7 off, and a negative offset flows toward the target", () => {
    expect(dashes(0, 30, 4, 7, 0)).toEqual([[0, 4], [11, 15], [22, 26]]);
    const later = dashes(0, 30, 4, 7, flowOffset(250, 1));
    expect(later[0]?.[0]).toBeGreaterThan(0); // 往終點走了 6 px
    expect(flowOffset(1000, 1)).toBe(-24);
    expect(flowOffset(1000, 1, true)).toBe(0);
  });

  it("splits a line by the row it crosses", () => {
    // 從第 0 排中心往下走到第 2 排中心：切成三塊、排號 0、1、2
    const parts = splitRows(0, 96, 96, 24, 120, 3);
    expect(parts.map((p) => p.row)).toEqual([0, 1, 2]);
    expect(parts[0]?.s1).toBeCloseTo(24);
    expect(parts[1]?.s1).toBeCloseTo(72);
    expect(splitRows(10, 40, 100, 30, 30, 3)).toEqual([{ s0: 10, s1: 40, row: 0 }]);
  });
});

describe("shield guard", () => {
  const preview = (cover: PreviewOut["cover"], targetId = "unit_0003") => ({ action: { type: "attack", unit_id: "unit_0001", target_id: targetId }, cover }) as unknown as PreviewOut;

  it("only draws for a shield_guard cover with a unit", () => {
    const g = guardDraw(preview({ penalty: 2, kind: "shield_guard", name_zh: "持盾弟子", pos: [2, 0], unit_id: "unit_0004" }), view);
    expect(g).toEqual({ wardId: "unit_0003", ward: { x: 2, y: 1 }, guardId: "unit_0004", guard: { x: 2, y: 0 } });
    expect(guardDraw(preview({ penalty: 2, kind: "crate", name_zh: "木箱", pos: [2, 0], object_id: "obj_0002" }), view)).toBeNull();
    expect(guardDraw(preview(null), view)).toBeNull();
    expect(guardDraw(null, view)).toBeNull();
  });

  it("moves the chip to the upper right when the guard is due north", () => {
    expect(chipCenter({ x: 2, y: 0 }, { x: 2, y: 1 }, 100, -30, 1)).toEqual({ x: 100 + NORTH_CHIP_DX, y: -26 });
    expect(chipCenter({ x: 2, y: 2 }, { x: 2, y: 1 }, 100, -30, 1)).toEqual({ x: 100, y: chipY(-30, 1) });
  });

  it("the dotted link ends beside the chip and never runs through the ward's body", () => {
    const ward = { x: 120, y: 120 };
    for (const guard of [{ x: 120, y: 168 }, { x: 168, y: 120 }, { x: 72, y: 120 }, { x: 168, y: 168 }]) {
      const chip = { x: ward.x, y: chipY(ward.y - 26, 1) };
      const dots = linkDots(guard, ward, chip, 1);
      const last = dots[dots.length - 1];
      expect(Math.abs((last?.x ?? 0) - chip.x)).toBeCloseTo(8.1, 0);
      // 身體範圍：格子中心左右 9、頭頂到腳底
      const inside = dots.filter((d) => Math.abs(d.x - ward.x) < 9 && d.y > ward.y - 26 && d.y < ward.y + 11);
      expect(inside).toEqual([]);
    }
  });
});

describe("glance", () => {
  it("pops, turns the eyes 60–150 ms, sends sight lines 150–240 ms, fades 480–600 ms", () => {
    expect(glanceFrame(0)).toMatchObject({ scale: 0.6, look: 0, sight: 0, alpha: 1 });
    expect(glanceFrame(90).scale).toBeCloseTo(1.1);
    expect(glanceFrame(150)).toMatchObject({ scale: 1, look: 1, sight: 0 });
    expect(glanceFrame(240)).toMatchObject({ sight: 1, alpha: 1 });
    expect(glanceFrame(540).alpha).toBeCloseTo(0.5);
    expect(glanceFrame(600).alpha).toBe(0);
    expect(glanceFrame(30, true)).toEqual({ scale: 1, alpha: 1, look: 1, sight: 1 });
    expect(glanceDir({ x: 2, y: 2 }, { x: 1, y: 2 })).toEqual({ x: -1, y: 0 });
  });
});

describe("feedback words and the glance item", () => {
  const ev = (type: string, more: Record<string, unknown>) => ({ seq: 1, round: 1, type, ...more });

  it("落空 on the archer, 被擋下 on the blocker, 被打斷 on the archer — all good-yellow, never on the target", () => {
    const items = feedbackFor(
      [
        ev("effect_fizzled", { effect_kind: "followup", pos: { x: 0, y: 0 }, reason: "lock_on_concealed", lock_caster_id: "unit_0003" }),
        ev("effect_fizzled", { effect_kind: "followup", pos: { x: 0, y: 0 }, reason: "lock_on_blocked", lock_caster_id: "unit_0003", lock_blocker_id: "unit_0004" }),
        ev("followup_cancelled", { unit_id: "unit_0003", skill_id: "s", name_zh: "鶴唳穿雲", reason: "interrupted" }),
        ev("followup_cancelled", { unit_id: "unit_0003", skill_id: "s", name_zh: "x", reason: "downed" }),
        ev("effect_fizzled", { effect_kind: "followup", pos: { x: 0, y: 0 }, reason: "followup_no_target" }),
      ],
      view,
    );
    expect(items.map((i) => (i.kind === "float" ? [i.text, i.pos.x, i.pos.y, i.tone] : i.kind))).toEqual([
      [WORD_LOCK_MISS, 2, 1, "good"],
      [WORD_LOCK_BLOCKED, 2, 0, "good"],
      [WORD_LOCK_INTERRUPTED, 2, 1, "good"],
    ]);
  });

  it("a blocked miss without a known blocker falls back to the archer; an unknown archer shows nothing", () => {
    const items = feedbackFor([ev("effect_fizzled", { pos: { x: 0, y: 0 }, reason: "lock_on_blocked", lock_caster_id: "unit_0003" }), ev("effect_fizzled", { pos: { x: 0, y: 0 }, reason: "lock_on_lost" })], view);
    expect(items.map((i) => (i.kind === "float" ? [i.text, i.pos.x, i.pos.y] : i.kind))).toEqual([[WORD_LOCK_BLOCKED, 2, 1]]);
  });

  it("trap_glance becomes a glance item at the owner, pointing at the trap", () => {
    const items = feedbackFor([ev("trap_glance", { owner_id: "unit_0003", pos: { x: 3, y: 2 } })], view);
    expect(items).toEqual([{ kind: "glance", pos: { x: 2, y: 1 }, unitId: "unit_0003", to: { x: 3, y: 2 } }]);
    expect(feedbackFor([ev("trap_glance", { owner_id: "unit_9999", pos: { x: 3, y: 2 } })], view)).toEqual([]);
  });
});

describe("trap traces reach the draw model", () => {
  it("copies trap_traces; absent or empty → no key", () => {
    const m = buildDrawModel(smallView({ trap_traces: [{ x: 3, y: 2 }] }), "unit_0001");
    expect(m.traces).toEqual([{ x: 3, y: 2 }]);
    expect(buildDrawModel(smallView({ trap_traces: null }), "unit_0001").traces).toBeUndefined();
    expect("traces" in buildDrawModel(smallView(), "unit_0001")).toBe(false);
  });
});

void unit;
