// 遊戲的紙娃娃外觀（DollSpec）→ Q 版小人（QK-1）。只換畫法：欄位與值照舊，名稱不同的部件在這裡對過去。
// - 成對武器（主手、副手同一把匕首）→ Q 版的 paired（一手一把）。
// - 規則武器 fist ＝空手（QK-5，美術 PM 對 QK-8 的決定）：主手、副手的 fist 不傳下去，畫成空手拳頭（赤膊武僧不戴拳套）；拳套只給 gauntlet。
// - 赤膊（bare）照原樣傳下去（QK-8 起 Q 版有赤膊畫法，qNpc.npcPrep 換成膚色）。其他不認得的 kind 照原樣傳下去（Q 版不認得就不畫）。
import type { DollSpec } from "./appearance";
import { elementTint } from "./appearance";
import type { InkPose } from "./inkPose";
import { itemColors } from "./itemColors";
import type { QHooks, QItem, QLook, QPose, QUnit } from "./qCore";
import { qWeapon } from "./qWeapons";

/** 遊戲畫面用的顏色：裝備色照 itemColors（材質色表 material.ts）、元素色照 palette。 */
export const GAME_HOOKS: QHooks = { colors: (it: QItem) => itemColors({ ...it }), tint: elementTint };

export function qUnitOf(spec: DollSpec): QUnit {
  const look: QLook = { ...spec.look };
  const gear: QUnit["gear"] = { ...spec.gear };
  if (gear.main_hand?.kind === "fist") delete gear.main_hand;
  if (gear.off_hand?.kind === "fist") delete gear.off_hand;
  const main = gear.main_hand;
  const off = gear.off_hand;
  if (main?.kind === "dagger" && off?.kind === "dagger") {
    gear.main_hand = { ...main, kind: "paired" };
    delete gear.off_hand;
  }
  return { look, gear };
}

/**
 * QK-5：Q 版腿短（大腿 4、小腿 5，C 是 15），C 的片段（跳躍收腿、蹲低、跪地、滑倒、倒下前的膝軟）照搬會讓腿折進身體、腳浮到腰上。
 * Q 版只在這裡收斂（片段資料不改，C 畫法照舊）：膝 ≤ 0.9、髖 −0.7～0.75（qGear.leg 再 ×1.6）；往下沉的 bob 照腿長比例 ×0.6、最多 3.2。
 */
export const Q_LEG = { knee: 0.9, hipMin: -0.7, hipMax: 0.75, bobK: 0.6, bobMax: 3.2 } as const;
export function qLegFit(p: InkPose): InkPose {
  const out: InkPose = { ...p };
  const cl = (v: number, a: number, b: number): number => Math.max(a, Math.min(b, v));
  for (const k of ["kneeN", "kneeF"] as const) if (typeof out[k] === "number") out[k] = cl(out[k], -Q_LEG.knee, Q_LEG.knee);
  for (const k of ["hipN", "hipF"] as const) if (typeof out[k] === "number") out[k] = cl(out[k], Q_LEG.hipMin, Q_LEG.hipMax);
  if (typeof out.bob === "number" && out.bob > 0) out.bob = Math.min(Q_LEG.bobMax, out.bob * Q_LEG.bobK);
  return out;
}

/** inkPose 的姿勢欄位 Q 版照用（elbow、armF、reach 等 C 專用的欄位 Q 版不吃；腿照 qLegFit 收斂）。 */
export const qPoseOf = (p: InkPose | null): QPose | null => (p === null ? null : (qLegFit(p) as QPose));

/** Q 版武器握把到作用端的長度（特效起點用；不在武器表＝0，用手掌）。 */
export const qWeaponLen = (it: QItem | undefined): number => qWeapon(it)?.W.len ?? 0;
