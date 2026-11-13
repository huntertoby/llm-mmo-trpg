// PB-1e：頭目部位的頭頂小格、外觀旗標、南邊有人時 HUD 改掛最上層（純函式）；PB-1f：「{部位} 破！」浮字拿掉，回饋照舊在重畫之後。
import { describe, expect, it } from "vitest";
import type { BattleView, PartView, UnitView } from "../api/types";
import { buildDrawModel } from "./drawModel";
import { frameOps, type Frame } from "./playback";
import type { FeedbackItem } from "./feedback";
import { debrisOf, dollPartsOf, HP_H, HP_W, HP_Y, partDraws, partHudUp, partOrder, STRIP, stripBars, stripLayout } from "./partStrip";
import { tile, unit } from "./testFixtures";
import { readFile, SRC_DIR } from "../test/sourceScan";

const part = (id: string, o: Partial<PartView> = {}): PartView => ({ id, name_zh: id, hp: 24, max_hp: 24, broken: false, exposed: true, reach: "any", break_lines_zh: [], ...o });

describe("頭頂部位小格的排法（移植需求 2.3）", () => {
  it("1600 寬：HP 條正下方隔 0.8、三條各寬 11.2、間隔 1.6、高 2.6、底邊 0.8；寬度不超出 HP 條", () => {
    const L = stripLayout(3, 1.31);
    expect(L.top).toBeCloseTo(HP_Y + HP_H + 0.8);
    expect(L.w).toBeCloseTo(11.2);
    expect(L.h).toBeCloseTo(2.6);
    expect(L.bottom).toBeCloseTo(L.top + 2.6 + 0.8);
    expect(L.x0 + 3 * L.w + 2 * STRIP.gap).toBeCloseTo(HP_W / 2 - STRIP.pad);
    expect(L.xs).toBeCloseTo(5.6);
  });
  it("800 寬（地圖 0.53）只放大高度：條高畫面 ≥ 2 px、「×」≥ 4 px；寬度不變", () => {
    const L = stripLayout(3, 0.53);
    expect(L.h * 0.53).toBeCloseTo(2);
    expect(L.xs * 0.53).toBeCloseTo(4);
    expect(L.w).toBeCloseTo(11.2);
    expect(L.k).toBeGreaterThan(1);
  });
  it("順序照 18.2.3：拂塵｜氣海｜長劍（伺服器照 ID 排）", () => {
    expect(partOrder([part("dantian"), part("sword"), part("whisk")]).map((p) => p.id)).toEqual(["whisk", "dantian", "sword"]);
  });
  it("看不到資訊：全部未露出；演出中斷掉的那一條先是空槽、落地才打叉", () => {
    const ps = partDraws([part("whisk", { broken: true, hp: 0 }), part("dantian")]);
    expect(stripBars(ps, true).map((b) => b.kind)).toEqual(["hidden", "hidden"]);
    expect(stripBars(ps, false, { part: "whisk", k: "fly" })[0]).toEqual({ kind: "ok", hp: 0, max: 1 });
    expect(stripBars(ps, false)[0]).toEqual({ kind: "broken" });
  });
});

describe("人物外觀旗標（移植需求 3.6）", () => {
  it("沒有部位＝null（貼圖鍵不變）；拂塵、長劍破了＝剪短、劍斷；氣海露出＝氣旋、破了＝裂痕", () => {
    expect(dollPartsOf(undefined)).toBeNull();
    expect(dollPartsOf(partDraws([part("dantian", { exposed: false }), part("whisk")]))).toBeNull();
    expect(dollPartsOf(partDraws([part("whisk", { broken: true }), part("sword", { broken: true }), part("dantian")]))).toEqual({ whisk: true, sword: true, dantian: "qi" });
    expect(dollPartsOf(partDraws([part("dantian", { broken: true })]))).toEqual({ dantian: "crack" });
  });
  it("演出前兩格部位還在（白閃、裂紋）；第 3 格斷了但地上還沒有掉落物", () => {
    const ps = partDraws([part("whisk", { broken: true }), part("dantian", { exposed: false })]);
    expect(dollPartsOf(ps, { part: "whisk", k: "flash" })).toEqual({ fx: { part: "whisk", k: "flash" } });
    expect(dollPartsOf(ps, { part: "whisk", k: "fly" })).toEqual({ whisk: true });
    expect(debrisOf(ps, { part: "whisk", k: "fly" })).toEqual({ whisk: false, sword: false });
    expect(debrisOf(ps)).toEqual({ whisk: true, sword: false });
  });
});

function viewWith(units: UnitView[]): BattleView {
  const tiles = [];
  for (let y = 0; y < 4; y++) for (let x = 0; x < 4; x++) tiles.push(tile(x, y));
  return { team: "ally", map_id: "t", width: 4, height: 4, tiles, objects: [], units, traps: [], turn_order: [], active_unit: null, round: 1, max_rounds: 30, objective: { kind: "eliminate", tiles: [], rounds: null, leader_retreat: false }, ended: false, winner: null, end_reason: null, pending: null, source_wells: [], zones: [], runes: [] } as unknown as BattleView;
}

describe("南邊那格有人：頭目 HUD 改掛最上層（移植需求 3.4）", () => {
  const boss = unit("b", "enemy", 1, 1, { parts: [part("whisk")] } as Partial<UnitView>);
  it("有部位、南邊站著人才算；倒下的不算；沒有部位的單位不算", () => {
    expect(partHudUp({ x: 1, y: 1, parts: partDraws([part("whisk")]) }, [{ x: 1, y: 2, downed: false }])).toBe(true);
    expect(partHudUp({ x: 1, y: 1, parts: partDraws([part("whisk")]) }, [{ x: 1, y: 2, downed: true }])).toBe(false);
    expect(partHudUp({ x: 1, y: 1 }, [{ x: 1, y: 2, downed: false }])).toBe(false);
  });
  it("buildDrawModel：頭目帶 parts 與 partHudUp；沒有部位的單位沒有這兩個欄位", () => {
    const m = buildDrawModel(viewWith([boss, unit("h", "ally", 1, 2)]), "h");
    const b = m.units.find((u) => u.id === "b")!;
    expect(b.parts?.map((p) => p.id)).toEqual(["whisk"]);
    expect(b.partHudUp).toBe(true);
    const h = m.units.find((u) => u.id === "h")!;
    expect("parts" in h || "partHudUp" in h).toBe(false);
    const m2 = buildDrawModel(viewWith([boss, unit("h", "ally", 2, 2)]), "h");
    expect(m2.units.find((u) => u.id === "b")!.partHudUp).toBeUndefined();
  });
});

describe("PB-1f：「{部位} 破！」浮字拿掉，回饋不再提前（PB-1e 驗收裁定待決 1）", () => {
  const dmg: FeedbackItem = { kind: "float", pos: { x: 1, y: 1 }, text: "−9", tone: "damage", big: false, slot: 0 };
  const frame = (vfx: boolean): Frame => ({ actorId: "a", motions: [], vfx: vfx ? ({ leadMs: 100 } as unknown as Frame["vfx"]) : null, vfxImpactMs: 0, view: {} as BattleView, lifts: [], liftMs: 0, feedback: [dmg], feedbackMs: 900, lines: [], pauseMs: 0 }) as unknown as Frame;
  it("有特效：回饋只有一段、在重畫之後", () => {
    const ops = frameOps(frame(true)).map((o) => (o.op === "feedback" ? `feedback:${o.items.map((i) => (i.kind === "float" ? i.text : i.kind)).join(",")}` : o.op));
    expect(ops).toEqual(["mark", "vfx", "view", "feedback:−9"]);
  });
  it("回饋項目不再有 early 欄位（原始碼）", () => {
    expect(readFile(SRC_DIR, "battle/feedback.ts")).not.toMatch(/\bearly\b/u);
    expect(readFile(SRC_DIR, "battle/playback.ts")).not.toMatch(/\bearly\b/u);
  });
});
