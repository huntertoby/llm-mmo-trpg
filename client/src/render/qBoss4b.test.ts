// QK-4b：頭目照 huge ×1.6、HUD 在剪影上方、外光沿輪廓、待機首尾接上、攻擊命中對齊出手格。
import { describe, expect, it } from "vitest";
import type { BattleView } from "../api/types";
import type { UnitDraw } from "../battle/drawModel";
import { TILE_SIZE } from "../battle/geometry";
import { bossHeadroom } from "../battle/elevation";
import { creatureStrikeInView } from "../battle/viewGrip";
import { creatureTop, HUGE_FIELD_SCALE } from "./inkCreature";
import { DOLL_SCALE } from "./paperdoll";
import { BOSS_CLIPS, BOSS_FIELD_SCALE, BOSS_GLOW_W, BOSS_MS, bossAct, bossAttackClip, bossAttackHitU, bossPlan } from "./qBoss";
import { BOSS_HUD_GAP, FEET, ROW_Y_FEET, bossHudDy, creatureFieldScale, creatureOf, hpBoxOf, statusRowY } from "./unitSprite";

const T = TILE_SIZE;
function stream(draw: (c: CanvasRenderingContext2D) => void, digits = 3): string {
  const out: string[] = [];
  const ctx = new Proxy({} as Record<string, unknown>, {
    get: (t, p: string) => (p in t ? t[p] : (...a0: unknown[]) => { const a = p === "rotate" ? a0.map((x) => (((x as number) % (2 * Math.PI)) + 2 * Math.PI) % (2 * Math.PI)) : a0; out.push(`${p}(${a.map((x) => (typeof x === "number" ? (Math.abs(x) < 10 ** -digits ? 0 : x).toFixed(digits) : String(x))).join(",")})`); }),
    set: (t, p: string, v) => ((t[p] = v), out.push(`${p}=${typeof v === "number" ? v.toFixed(digits) : String(v)}`), true),
  }) as unknown as CanvasRenderingContext2D;
  draw(ctx);
  return out.join(";");
}
const HEART = { body: "wisp", material: "crystal", element: "fire", size: "huge", traits: ["core"] };
const LORD = { body: "golem", material: "crystal", size: "huge", traits: ["core"] };
const unit = (template: string, creature: Record<string, unknown>, over: Partial<UnitDraw> = {}): UnitDraw =>
  ({
    id: "b", x: 4, y: 5, marker: "", template, name: "n", team: "enemy", fill: 0, hpRatio: 1, shieldRatio: 0, active: false, hero: false, downed: false, summon: false, totem: false,
    remaining: null, revivable: false, bomb: null, facing: "south", weaponId: "fangs", weaponClass: "melee",
    dollLook: { skin: "#fff", skull: false, gear: {}, beard: false, affixes: [], traits: [], rarity: "legendary", creature },
    ...over,
  }) as unknown as UnitDraw;

describe("QK-4b：頭目戰場大小與 HUD", () => {
  it("頭目 ×1.6（取代 ×0.9）；一般異形 ×1", () => {
    expect(HUGE_FIELD_SCALE).toBe(1.6);
    expect(BOSS_FIELD_SCALE).toBe(1.6);
    expect(creatureFieldScale(unit("ashen_heart", HEART))).toBe(1.6);
    expect(creatureFieldScale(unit("rift_shard_lord", LORD))).toBe(1.6);
    expect(creatureFieldScale(unit("hound_alpha", { body: "hound", size: "large" }))).toBe(1);
  });
  it("HUD 整組在剪影上方：HP 條（含朝南三角形）下緣離頭頂 2px；一般單位不搬", () => {
    for (const [tpl, look] of [["ashen_heart", HEART], ["rift_shard_lord", LORD]] as const)
      for (const facing of ["south", "east", "north", "west"] as const) {
        const u = unit(tpl, look, { facing });
        const top = FEET + creatureTop(creatureOf(u)!) * (T / 52) * DOLL_SCALE * 1.6;
        const dy = bossHudDy(u);
        expect(dy).toBeLessThan(0);
        expect(hpBoxOf(u)!.b + dy).toBeLessThanOrEqual(top - BOSS_HUD_GAP + 1e-9);
        expect(statusRowY(creatureOf(u), creatureFieldScale(u))).toBe(ROW_Y_FEET);
      }
    expect(bossHudDy(unit("hound_alpha", { body: "hound" }))).toBe(0);
  });
  it("最上排：HUD 不超出頭頂預留（QK-9：頭目自己的預留 `BOSS_HEADROOM`）", () => {
    const u = unit("rift_shard_lord", LORD, { y: 0 });
    const dy = bossHudDy(u);
    expect(ROW_Y_FEET - 6 + dy).toBeGreaterThanOrEqual(-T / 2 - bossHeadroom("rift_shard_lord") - 6.01);
  });
});

describe("QK-4b：外光與待機", () => {
  it("兩位頭目都畫剪影外光（沒有 DOM 時以 glow 參數驗）：灰燼之心不再畫核心光暈當外光，火焰箭蓄力時才亮", () => {
    expect(BOSS_GLOW_W).toBe(2.2);
    const still = stream((c) => bossAct(c, "ah", "idle", 0, { phase: 2 }));
    const flare = stream((c) => bossAct(c, "ah", "firebolt", 0.3, { phase: 2 }));
    // 核心光暈＝3 圈 arc 半徑 32×… 的平塗；待機沒有、蓄力有
    expect(still).not.toMatch(/arc\(0\.000,-2\d\.\d{3},3\d\.\d{3}/);
    expect(flare).toMatch(/arc\(0\.000,-2\d\.\d{3},3\d\.\d{3}/);
  });
  it("待機一圈首尾接上：u＝1 那一格和 u＝0 相同（兩位、每個階段）", () => {
    for (const [id, phases] of [["ah", [1, 2, 3]], ["sl", [1, 2, 3, 4]]] as const)
      for (const phase of phases) expect(stream((c) => bossAct(c, id, "idle", 1, { phase }), 1), `${id}${phase}`).toBe(stream((c) => bossAct(c, id, "idle", 0, { phase }), 1));
  });
});

describe("QK-4b：頭目攻擊命中對齊出手格", () => {
  it("每個攻擊片段的出手格在 (0,1)，那一格有出手特效、前一格沒有", () => {
    for (const [id, phase] of [["ah", 1], ["ah", 2], ["sl", 2]] as const)
      // BAL-21c：瞬步殘影 blink 是位移片段（由傳送播、沒有出手特效），同受擊、倒下不在這裡驗
      for (const clip of BOSS_CLIPS[id].filter((c) => c !== "hit" && c !== "death" && c !== "blink")) {
        const u = bossAttackHitU(id, clip, phase);
        expect(u, `${id} ${clip}`).toBeGreaterThan(0);
        expect(u).toBeLessThan(1);
        const has = (v: number) => bossPlan(id, clip, v, { phase }).fx.some((f) => f.ranged === true || ["burst", "ring", "bolt", "slash"].includes(f.k));
        expect(has(u), `${id} ${clip}`).toBe(true);
        expect(has(u - 1 / 11)).toBe(false);
      }
  });
  it("viewGrip：頭目的出招長度＝片段長度、出手格同 bossAttackHitU（依階段、動作類型）", () => {
    const view = {
      units: [
        { id: "b", pos: { x: 2, y: 2 }, team: "enemy", template_id: "ashen_heart", hp: 10, max_hp: 10, statuses: [], doll_look: { creature: HEART, rarity: "legendary" }, boss_phase: { index: 2 } },
        { id: "h", pos: { x: 3, y: 2 }, team: "ally", template_id: "hero", hp: 10, max_hp: 10, statuses: [] },
      ],
      tiles: [],
    } as unknown as BattleView;
    const got = creatureStrikeInView("b", view, "cast");
    expect(got).not.toBeNull();
    if (got === null) return;
    const clip = bossAttackClip("ah", "cast", 2);
    expect(got.ms).toBe(BOSS_MS[clip]);
    expect(got.hitAt).toBeCloseTo(bossAttackHitU("ah", clip, 2), 9);
  });
});
