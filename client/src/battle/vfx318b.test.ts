// Phase 3-18b 特效補強：生成水表面用水花配色、無傷害技能依施加的狀態上色、傳送的消散與出現、傳說技能較華麗的蓄力。
import { describe, expect, it } from "vitest";
import type { BattleView, Pos, SkillCard } from "../api/types";
import { isEmptyVfx, scaleVfx, vfxFor, VFX_TIMING, warpPlan } from "./vfx";
import { colorVfx, elementVfx, statusOfVfxKey, statusVfxKey, WATER_VFX_KEY } from "./vfxPalette";
import { paletteOf } from "../render/statusVfx";
import { statusColor } from "../render/skillParts";

const CASTER = "u_hero";
const FOE = "u_foe";
const at = (x: number, y: number): Pos => ({ x, y });
const view = (units: Record<string, Pos>): BattleView => ({ units: Object.entries(units).map(([id, pos]) => ({ id, pos })) }) as unknown as BattleView;
const units = view({ [CASTER]: at(2, 2), [FOE]: at(4, 2) });
const card = (extra: Record<string, unknown> = {}): Record<string, SkillCard> => ({ skill_x: { id: "skill_x", shape: "指定格（射程 4）", skeleton: "strike", ...extra } as unknown as SkillCard });
const used = (tiles: Pos[]) => ({ seq: 1, round: 1, type: "skill_used", unit_id: CASTER, skill_id: "skill_x", tiles });
const surface = (after: string, cause = "effect") => ({ seq: 2, round: 1, type: "surface_changed", pos: at(4, 2), before: "none", after, remaining: 3, cause });
const status = (id: string, source: string | null = CASTER) => ({ seq: 3, round: 1, type: "status_applied", target_id: FOE, status_id: id, duration: 2, refreshed: false, source_id: source });
const damage = (element: string) => ({ seq: 4, round: 1, type: "damage_dealt", target_id: FOE, source_id: CASTER, element, crit: false, amount: 4 });

describe("生成水表面的技能用水花配色", () => {
  it("沒有傷害元素：element ＝ water，配色是水花粒子", () => {
    const v = vfxFor([used([at(4, 2)]), surface("water")], units, card());
    expect(v.casts[0]!.element).toBe(WATER_VFX_KEY);
    expect(elementVfx(v.casts[0]!.element).particle).toBe("splash");
  });
  it("有傷害元素時以傷害元素為準；表面不是水、或不是技能效果造成的不算", () => {
    expect(vfxFor([used([at(4, 2)]), surface("water"), damage("fire")], units, card()).casts[0]!.element).toBe("fire");
    expect(vfxFor([used([at(4, 2)]), surface("ice")], units, card()).casts[0]!.element).not.toBe(WATER_VFX_KEY);
    expect(vfxFor([used([at(4, 2)]), surface("water", "interaction:fire_ice")], units, card()).casts[0]!.element).not.toBe(WATER_VFX_KEY);
  });
});

describe("無傷害技能依施加的狀態上色", () => {
  it("配色鍵是 status:<id>，顏色取自部件庫的狀態色（與技能圖示同一份）", () => {
    const v = vfxFor([used([at(4, 2)]), status("stunned")], units, card());
    const key = v.casts[0]!.element;
    expect(key).toBe(statusVfxKey("stunned"));
    expect(statusOfVfxKey(key)).toBe("stunned");
    const pal = paletteOf(key);
    expect(pal.primary).toBe(colorVfx(statusColor("stunned")).primary);
    expect(pal.primary).toBe(parseInt(statusColor("stunned").slice(1), 16));
  });
  it("不同狀態的顏色不同；別人施加的狀態、有傷害元素、治療都不套用", () => {
    const a = vfxFor([used([at(4, 2)]), status("hasted")], units, card()).casts[0]!.element;
    const b = vfxFor([used([at(4, 2)]), status("silenced")], units, card()).casts[0]!.element;
    expect(paletteOf(a).primary).not.toBe(paletteOf(b).primary);
    expect(vfxFor([used([at(4, 2)]), status("stunned", FOE)], units, card()).casts[0]!.element).toBe("default");
    expect(vfxFor([used([at(4, 2)]), status("stunned"), damage("ice")], units, card()).casts[0]!.element).toBe("ice");
    expect(vfxFor([used([at(4, 2)]), { seq: 5, round: 1, type: "healed", target_id: CASTER }, status("regenerating")], units, card()).casts[0]!.element).toBe("support");
  });
  it("不認得的狀態仍有顏色（部件庫的預設色），元素鍵不受影響", () => {
    expect(paletteOf(statusVfxKey("brand_new_status")).primary).toBeGreaterThan(0);
    expect(paletteOf("fire")).toBe(elementVfx("fire"));
  });
});

describe("傳送的消散與出現", () => {
  it("淡出淡入的位移：前半起點消散、後半終點出現", () => {
    const plan = warpPlan({ style: "fade", from: at(1, 1), to: at(5, 5), durationMs: 260 });
    expect(plan).toEqual([
      { kind: "vanish", pos: at(1, 1), startMs: 0, endMs: 130 },
      { kind: "appear", pos: at(5, 5), startMs: 130, endMs: 260 },
    ]);
  });
  it("滑動的位移或略過（時間 0）沒有特效", () => {
    expect(warpPlan({ style: "slide", from: at(1, 1), to: at(2, 1), durationMs: 140 })).toEqual([]);
    expect(warpPlan({ style: "fade", from: at(1, 1), to: at(5, 5), durationMs: 0 })).toEqual([]);
  });
});

describe("傳說技能較華麗的蓄力", () => {
  const cast = (extra: Record<string, unknown>) => vfxFor([used([at(4, 2)]), damage("fire")], units, card(extra)).casts[0]!;
  it("稀有度傳說：蓄力時間較長、標記 legendary，命中時間跟著延後", () => {
    const common = cast({ rarity_id: "common" });
    const legend = cast({ rarity_id: "legendary" });
    expect(common).toMatchObject({ legendary: false, chargeMs: VFX_TIMING.charge });
    expect(legend).toMatchObject({ legendary: true, chargeMs: VFX_TIMING.chargeLegendary });
    expect(VFX_TIMING.chargeLegendary).toBeGreaterThan(VFX_TIMING.charge);
    expect(legend.impactMs - common.impactMs).toBe(VFX_TIMING.chargeLegendary - VFX_TIMING.charge);
  });
  it("也讀圖示資料的稀有度；一般攻擊沒有蓄力；播放速度會縮放蓄力時間", () => {
    expect(cast({ icon: { rarity: "legendary", segments: [] } }).legendary).toBe(true);
    const basic = vfxFor([{ type: "attack_rolled", attacker_id: CASTER, target_id: FOE, hit: true }], units, {}).casts[0]!;
    expect(basic).toMatchObject({ legendary: false, chargeMs: 0 });
    const fast = scaleVfx({ casts: [cast({ rarity_id: "legendary" })], hits: [], blasts: [], shake: 0, leadMs: 0 }, 0.5);
    expect(fast.casts[0]!.chargeMs).toBe(Math.round(VFX_TIMING.chargeLegendary * 0.5));
  });
});

describe("rune detonation burst (3-28)", () => {
  const view = { units: [{ id: "u1", pos: { x: 1, y: 1 } }] } as unknown as Parameters<typeof vfxFor>[1];

  it("turns a detonated rune into a burst at the rune tile in the element colour", () => {
    const vfx = vfxFor([{ type: "rune_removed", reason: "detonated", pos: { x: 3, y: 2 }, element: "fire", rune_id: 1, owner_id: "u1" }], view, {});
    expect(vfx.blasts).toEqual([{ pos: { x: 3, y: 2 }, element: "fire", atMs: 0 }]);
    expect(isEmptyVfx(vfx)).toBe(false);
  });

  it("ignores runes that merely expired and scales with playback speed", () => {
    expect(vfxFor([{ type: "rune_removed", reason: "expired", pos: { x: 3, y: 2 }, element: "fire" }], view, {}).blasts).toEqual([]);
    const tag = vfxFor([{ type: "rune_removed", reason: "detonated", pos: { x: 0, y: 0 }, element: null }], view, {});
    expect(tag.blasts[0]?.element).toBe("default");
    expect(scaleVfx({ ...tag, blasts: [{ pos: { x: 0, y: 0 }, element: "x", atMs: 100 }] }, 0.5).blasts[0]?.atMs).toBe(50);
  });
});
