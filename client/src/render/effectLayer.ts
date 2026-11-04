// 6F-7（美術 PM 驗收 6F-6 小修 7）：特效放在哪一層（純函式）。
// 地格的紫色狀態光環原本和浮動字放在同一層，後播的光環會蓋在前一步的「暴擊 −9」上面。
// 現在光環標 `layer: "under"`，放進浮動字下面的 `floatRings` 層；地上的特效（`clip: "map"`）照舊在最下面的 `groundFx`。
import type { Effect } from "./vfxEffects";

export type EffectLayer = "groundFx" | "floatRings" | "effects";

/** 戰場 `world` 容器裡特效層由下到上的順序（BattleRenderer 照這個順序 addChild）。 */
export const EFFECT_LAYER_ORDER: readonly EffectLayer[] = ["groundFx", "floatRings", "effects"];

export function effectLayerOf(e: Pick<Effect, "clip" | "layer">): EffectLayer {
  if (e.clip === "map") return "groundFx";
  return e.layer === "under" ? "floatRings" : "effects";
}
