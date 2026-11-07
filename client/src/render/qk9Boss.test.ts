// QK-9：頭目的環 ×1.6、浮動字與眼睛從 HUD 上方冒、最上排畫布照頭目加高（HUD 不疊剪影、頭不出畫布）。
import { describe, expect, it } from "vitest";
import type { UnitDraw } from "../battle/drawModel";
import { TILE_SIZE } from "../battle/geometry";
import { bossHeadroom, topReserve, UNIT_HEADROOM } from "../battle/elevation";
import { creatureTop } from "./inkCreature";
import { DOLL_SCALE } from "./paperdoll";
import { BOSS_HUD_GAP, FEET, bossHudDy, creatureOf, hpBoxOf, ringScale, unitMarkTopY, unitTopY } from "./unitSprite";

const T = TILE_SIZE;
const HEART = { body: "wisp", material: "crystal", element: "fire", size: "huge", traits: ["core"] };
const LORD = { body: "golem", material: "crystal", size: "huge", traits: ["core"] };
const unit = (template: string, creature: Record<string, unknown>, over: Partial<UnitDraw> = {}): UnitDraw =>
  ({
    id: "b", x: 4, y: 5, marker: "", template, name: "n", team: "enemy", fill: 0, hpRatio: 1, shieldRatio: 0, active: false, hero: false, downed: false, summon: false, totem: false,
    remaining: null, revivable: false, bomb: null, facing: "south", weaponId: "fangs", weaponClass: "melee",
    dollLook: { skin: "#fff", skull: false, gear: {}, beard: false, affixes: [], traits: [], rarity: "legendary", creature },
    ...over,
  }) as unknown as UnitDraw;
const BOSSES = [["ashen_heart", HEART], ["rift_shard_lord", LORD]] as const;
const FACINGS = ["south", "east", "north", "west"] as const;

describe("QK-9：頭目收尾", () => {
  it("陣營環、精英金環照樣張頭目的環（灰燼之心 40、碎晶之主 26 單位）× 1.6；一般單位不變", () => {
    const px = (T / 52) * DOLL_SCALE;
    expect(ringScale(unit("ashen_heart", HEART)) * T * 0.36).toBeCloseTo(40 * 1.6 * px, 6);
    expect(ringScale(unit("rift_shard_lord", LORD)) * T * 0.36).toBeCloseTo(26 * 1.6 * px, 6);
    expect(ringScale(unit("hound_alpha", { body: "hound", size: "large" }))).toBe(1);
  });
  it("浮動字、眼睛的起點在 HUD 上緣（比剪影頭頂高）；一般單位＝頭頂", () => {
    for (const [tpl, look] of BOSSES)
      for (const facing of FACINGS) {
        const u = unit(tpl, look, { facing });
        expect(unitMarkTopY(u)).toBeLessThan(unitTopY(u));
        expect(unitMarkTopY(u)).toBeLessThanOrEqual(hpBoxOf(u)!.t + bossHudDy(u));
      }
    const h = unit("hound_alpha", { body: "hound" });
    expect(unitMarkTopY(h)).toBe(unitTopY(h));
  });
  it("最上排：頭頂預留夠放剪影＋HUD（四個朝向、含護盾條），HUD 不被卡住", () => {
    for (const [tpl, look] of BOSSES) {
      let need = 0;
      for (const facing of FACINGS)
        for (const shieldRatio of [0, 0.5]) {
          const u = unit(tpl, look, { facing, shieldRatio, y: 0 });
          const free = unit(tpl, look, { facing, shieldRatio, y: 50 });
          const head = FEET + creatureTop(creatureOf(u)!) * (T / 52) * DOLL_SCALE * 1.6;
          expect(bossHudDy(u)).toBe(bossHudDy(free)); // 沒被卡住
          expect(hpBoxOf(u)!.b + bossHudDy(u)).toBeLessThanOrEqual(head - BOSS_HUD_GAP + 1e-9);
          need = Math.max(need, -(unitMarkTopY(u) + T / 2), -(head + T / 2));
        }
      expect(bossHeadroom(tpl)).toBeGreaterThanOrEqual(need);
      expect(bossHeadroom(tpl)).toBeLessThanOrEqual(need + 8);
    }
  });
  it("畫布：有頭目時照頭目加高，沒有頭目不變", () => {
    const tiles = Array.from({ length: 36 }, () => ({ height: 0 }));
    expect(topReserve({ width: 6, height: 6, tiles, units: [{ template: "hero_fighter" }] })).toBe(UNIT_HEADROOM);
    expect(topReserve({ width: 6, height: 6, tiles, units: [{ template: "rift_shard_lord" }] })).toBe(bossHeadroom("rift_shard_lord"));
  });
});
