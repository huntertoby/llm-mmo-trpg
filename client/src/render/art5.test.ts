// Phase 5A-ART5（docs/art/5A-ART檢查.md）：戰場最小大小、矮異形的狀態列、道童的杖頭綠光與大小。
import { describe, expect, it } from "vitest";
import type { UnitDraw } from "../battle/drawModel";
import { TILE_SIZE } from "../battle/geometry";
import { UNIT_HEADROOM } from "../battle/elevation";
import { ELITE_SCALE, FIELD_SIZES, SIZES, resolveCreature } from "./inkCreature";
import { DOLL_SCALE, drawFigure } from "./paperdoll";
import { resolveDollT, UNIT_DOLLS } from "./testDolls";
import {
  ROW_ICON_FEET,
  ROW_Y_FEET,
  ROW_Y_HEADROOM_CAP,
  ROW_Y_UPPER_HP_CAP,
  creatureFieldScale,
  creatureOf,
  humanoidLookScale,
  statusRowY,
} from "./unitSprite";

const T = TILE_SIZE;
const unit = (over: Partial<UnitDraw>): UnitDraw => ({
  id: "u1", x: 0, y: 0, marker: "A", template: "t", name: "n", team: "enemy", fill: 0, hpRatio: 1, shieldRatio: 0,
  active: false, hero: false, downed: false, summon: false, totem: false, remaining: null, revivable: false, bomb: null,
  facing: "west", weaponId: "fangs", weaponClass: "melee", ...over,
});
const dollLook = (over: Record<string, unknown>): UnitDraw["dollLook"] => ({ skin: "#f1c9a5", skull: false, gear: {}, beard: false, affixes: [], traits: [], ...over }) as UnitDraw["dollLook"];
const creatureUnit = (creature: Record<string, unknown>, over: Partial<UnitDraw> = {}): UnitDraw => unit({ dollLook: dollLook({ creature: { traits: [], ...creature } }), ...over });

describe("戰場上的最小大小", () => {
  it("tiny 0.8、small 0.9，medium 以上不變；樣張用的 SIZES 不變", () => {
    expect(FIELD_SIZES).toEqual({ tiny: 0.8, small: 0.9, medium: 1, large: 1.25, huge: 1.6 });
    expect(SIZES["tiny"]).toBe(0.62);
    expect(SIZES["small"]).toBe(0.8);
    expect(resolveCreature({ look: { body: "lizard", size: "tiny" } }).size).toBeCloseTo(0.62);
    expect(resolveCreature({ look: { body: "lizard", size: "tiny" }, field: true }).size).toBeCloseTo(0.8);
  });
  it("戰場單位：幼蜥仍比餘燼蜥小，精英 ×1.15 照乘，頭目不乘", () => {
    const whelp = creatureOf(creatureUnit({ body: "lizard", material: "magma", size: "tiny" }))!;
    const lizard = creatureOf(creatureUnit({ body: "lizard", material: "magma", size: "small" }))!;
    expect(whelp.size).toBeCloseTo(0.8);
    expect(lizard.size).toBeCloseTo(0.9);
    expect(whelp.size).toBeLessThan(lizard.size);
    expect(creatureOf(creatureUnit({ body: "lizard", size: "small" }, { elite: true }))!.size).toBeCloseTo(0.9 * ELITE_SCALE);
    expect(creatureOf(creatureUnit({ body: "hound", size: "large" }, { elite: true }))!.size).toBeCloseTo(1.25 * ELITE_SCALE);
    expect(creatureOf(creatureUnit({ body: "golem", size: "huge" }, { elite: true, dollLook: dollLook({ rarity: "legendary", creature: { body: "golem", size: "huge", traits: [] } }) }))!.size).toBeCloseTo(1.6);
  });
});

describe("異形的狀態列", () => {
  const rowOf = (u: UnitDraw): number => statusRowY(creatureOf(u), creatureFieldScale(u));
  const feet = T * 0.23;
  const k = (T / 52) * DOLL_SCALE;

  it("人形與沒有異形外觀的單位維持原位", () => {
    expect(statusRowY(null)).toBe(ROW_Y_FEET);
    expect(rowOf(unit({ dollLook: dollLook({}) }))).toBe(ROW_Y_FEET);
  });

  it("矮異形（餘燼幼蜥、熔爐母獸的蜥蜴身形）：圖示中心 ＝ 身體最高點 − 圖示/2 − 1，比原位高", () => {
    for (const size of ["tiny", "small", "medium"]) {
      const u = creatureUnit({ body: "lizard", material: "magma", size });
      const top = feet + -19 * FIELD_SIZES[size]! * k;
      expect(rowOf(u)).toBeCloseTo(top - ROW_ICON_FEET / 2 - 1);
      expect(rowOf(u)).toBeLessThan(ROW_Y_FEET);
    }
    // 熔核（腹部 (2,-7.4)）在圖示下方，不會被蓋住
    const mother = creatureUnit({ body: "lizard", material: "magma", size: "medium" });
    const coreY = feet + -7.4 * k;
    expect(rowOf(mother) + ROW_ICON_FEET / 2).toBeLessThan(coreY);
  });

  it("浮空的晶靈、和人一樣高的傀儡、頭目維持原位", () => {
    expect(rowOf(creatureUnit({ body: "wisp" }))).toBe(ROW_Y_FEET);
    expect(rowOf(creatureUnit({ body: "wraith" }))).toBe(ROW_Y_FEET);
    expect(rowOf(creatureUnit({ body: "flyer", variant: "bird" }))).toBe(ROW_Y_FEET);
    expect(rowOf(creatureUnit({ body: "golem" }))).toBe(ROW_Y_FEET);
    expect(rowOf(creatureUnit({ body: "golem", size: "huge" }))).toBe(ROW_Y_FEET);
  });

  it("高一點的異形會碰到上限：不超出頭頂預留，也不蓋到上一排單位的 HP 條", () => {
    for (const body of ["hound", "bear", "pylon", "serpent"]) {
      const y = rowOf(creatureUnit({ body }));
      expect(y).toBeLessThan(ROW_Y_FEET);
      expect(y - ROW_ICON_FEET / 2).toBeGreaterThanOrEqual(-T / 2 - UNIT_HEADROOM);
      expect(y - ROW_ICON_FEET / 2).toBeGreaterThan(T * 0.36 + 5 - T); // 上一排的 HP 條下緣
      expect(y).toBeCloseTo(Math.max(ROW_Y_HEADROOM_CAP, ROW_Y_UPPER_HP_CAP));
    }
  });

  it("不比原位低：腳邊就已經在身體上方的扁平異形也不往下掉", () => {
    for (const body of ["ooze", "lizard", "crawler", "shell", "feline", "boar"]) {
      for (const size of ["tiny", "small", "medium", "large"]) expect(rowOf(creatureUnit({ body, size }))).toBeLessThanOrEqual(ROW_Y_FEET);
    }
  });
});

describe("青霧道童", () => {
  const look = UNIT_DOLLS["sect_acolyte"]!;
  it("資料：杖頭綠光 #b6f0a0、戰場大小 0.9", () => {
    expect(look.main_glow).toBe("#b6f0a0");
    expect(look.scale).toBe(0.9);
    expect(humanoidLookScale({ dollLook: look })).toBe(0.9);
    expect(humanoidLookScale({ dollLook: dollLook({}) })).toBe(1);
    expect(humanoidLookScale({ dollLook: dollLook({ scale: 9 }) })).toBe(1);
  });
  it("主手（圖騰杖）帶綠光，畫出來有綠色光暈；沒有光色的圖騰杖照舊", () => {
    const spec = resolveDollT({ template: "sect_acolyte", team: "enemy", summon: false, weaponId: "totem_staff" });
    expect(spec.gear.main_hand?.glow).toBe("#b6f0a0");
    const fills: string[] = [];
    const ctx = new Proxy({} as Record<string, unknown>, {
      get: (t, p: string) => (p in t ? t[p] : () => undefined),
      set: (t, p: string, v) => {
        t[p] = v;
        if (p === "fillStyle") fills.push(String(v));
        return true;
      },
    }) as unknown as CanvasRenderingContext2D;
    drawFigure(ctx, spec, "east");
    expect(fills).toContain("#b6f0a0");
    const plain = resolveDollT({ template: "sect_acolyte", team: "enemy", summon: false, weaponId: "totem_staff", dollLook: { ...look, main_glow: null } });
    const fills2: string[] = [];
    const ctx2 = new Proxy({} as Record<string, unknown>, {
      get: (t, p: string) => (p in t ? t[p] : () => undefined),
      set: (t, p: string, v) => {
        t[p] = v;
        if (p === "fillStyle") fills2.push(String(v));
        return true;
      },
    }) as unknown as CanvasRenderingContext2D;
    drawFigure(ctx2, plain, "east");
    expect(fills2).not.toContain("#b6f0a0");
  });
});
