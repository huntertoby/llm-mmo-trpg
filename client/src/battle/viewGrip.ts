// 普攻、技能起手用的武器類別與普攻變體表列（6R-F；前端審查第 5 點）：從這一步開始前的畫面（`before`）的裝備算，
// 不讀繪製器的狀態。純函式：同一份畫面一定得到同一個答案，重播、觀戰、重新整理都挑到同一個變體。
import type { BattleView } from "../api/types";
import { attackFamilyOf, type AttackFamily } from "../render/attackVariants";
import { weaponClassOf, type WeaponClass } from "../render/skillClips";
import { gripOf } from "../render/unitSprite";
import { unitDrawOf, type UnitDraw } from "./drawModel";
import { onField } from "./units";

const cache = new WeakMap<BattleView, ReadonlyMap<string, UnitDraw>>();

/** 畫面裡每個人的畫法資料（只用來看裝備與有沒有骨架；同一份畫面只算一次）。 */
function unitsOf(view: BattleView): ReadonlyMap<string, UnitDraw> {
  const hit = cache.get(view);
  if (hit !== undefined) return hit;
  const units = new Map(view.units.filter(onField).map((u) => [u.id, unitDrawOf(view, u, "", null, "")]));
  cache.set(view, units);
  return units;
}

/** 這個人在 `view` 裡的武器類別（起手對照表的列）；沒有骨架（異形、形態、召喚物、倒下）或不在場上當空手。 */
export function weaponClassInView(unitId: string, view: BattleView): WeaponClass {
  const u = unitsOf(view).get(unitId);
  const g = u === undefined ? null : gripOf(u);
  return g === null ? "bare" : weaponClassOf(g.main, g.off);
}

/** 這個人在 `view` 裡的普攻變體表列；沒有骨架或不是近戰武器為 `null`。 */
export function attackFamilyInView(unitId: string, view: BattleView): AttackFamily | null {
  const u = unitsOf(view).get(unitId);
  const g = u === undefined ? null : gripOf(u);
  return g === null ? null : attackFamilyOf(g.main, g.off);
}
