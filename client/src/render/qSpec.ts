// 遊戲的紙娃娃外觀（DollSpec）→ Q 版小人（QK-1）。只換畫法：欄位與值照舊，名稱不同的部件在這裡對過去。
// - 成對武器（主手、副手同一把匕首）→ Q 版的 paired（一手一把）。
// - 赤膊（bare）照原樣傳下去（QK-8 起 Q 版有赤膊畫法，qNpc.npcPrep 換成膚色）。其他不認得的 kind 照原樣傳下去（Q 版不認得就不畫）。
import type { DollSpec } from "./appearance";
import { elementTint } from "./appearance";
import type { InkPose } from "./inkPose";
import { itemColors } from "./paperdoll";
import type { QHooks, QItem, QLook, QPose, QUnit } from "./qCore";
import { qWeapon } from "./qWeapons";

/** 遊戲畫面用的顏色：裝備色照 itemColors（材質色表 material.ts）、元素色照 palette。 */
export const GAME_HOOKS: QHooks = { colors: (it: QItem) => itemColors({ ...it }), tint: elementTint };

export function qUnitOf(spec: DollSpec): QUnit {
  const look: QLook = { ...spec.look };
  const gear: QUnit["gear"] = { ...spec.gear };
  const main = gear.main_hand;
  const off = gear.off_hand;
  if (main?.kind === "dagger" && off?.kind === "dagger") {
    gear.main_hand = { ...main, kind: "paired" };
    delete gear.off_hand;
  }
  return { look, gear };
}

/** inkPose 的姿勢欄位 Q 版照用（elbow、armF、reach 等 C 專用的欄位 Q 版不吃）。 */
export const qPoseOf = (p: InkPose | null): QPose | null => (p === null ? null : (p as QPose));

/** Q 版武器握把到作用端的長度（特效起點用；不在武器表＝0，用手掌）。 */
export const qWeaponLen = (it: QItem | undefined): number => qWeapon(it)?.W.len ?? 0;
