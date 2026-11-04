// 探索時的腳步聲（AU-3）：走到哪一格就依那一格的地表踏一步（純函式挑音效，`playFieldStep` 交給引擎）。
// 室內地板照 6B-ART1 的房間配色（木板＝木、石板＝石）；室外照地形與表面（荒原的土＝沙）。
import type { FieldView, Pos } from "../api/types";
import { play } from "../audio";
import { stepKey, stepSoundFor, type StepSound } from "../audio/footsteps";
import { roomKindOf, roomPalette } from "../render/interiorArt";

/** 這張實地地圖走到 `to` 的腳步聲。 */
export function fieldStepSound(field: Pick<FieldView, "tiles" | "region" | "interior" | "facilities">, to: Pos): StepSound {
  const tile = field.tiles.find((t) => t.x === to.x && t.y === to.y) ?? null;
  const floor = field.interior ? roomPalette(roomKindOf(field.facilities.map((f) => f.kind)), field.region === "ashen_waste" ? "ashen" : "town").style : null;
  return stepSoundFor(tile, { region: field.region, floor: floor === "plank" || floor === "slab" ? floor : null });
}

/** 踏一步（第 `n` 步；變體鍵＝地圖:格:步數）。 */
export function playFieldStep(field: FieldView, to: Pos, n: number): void {
  play(fieldStepSound(field, to), { variantKey: stepKey(field.map_id, to.x, to.y, n) });
}
