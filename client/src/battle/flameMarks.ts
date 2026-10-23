// 可燃標記的淡化／明顯判斷（Phase 3-38）：純函式，不寫死技能 ID。
// 明顯的條件：(1) 選取中的技能會點火（製造 `ignite` 關鍵字，或元素為火）；(2) 場上已有火
// （任何格子有 `fire` 表面、有燃燒中的單位或物件）。其餘時候淡化。
import type { DrawModel } from "./drawModel";

/** 技能卡裡判斷用到的欄位。 */
export interface IgniteCard {
  keywords?: { makes: ReadonlyArray<{ id: string }> };
  icon?: { elements: readonly string[] };
}

export function skillIgnites(card: IgniteCard | null | undefined): boolean {
  if (card == null) return false;
  if (card.keywords?.makes.some((k) => k.id === "ignite") === true) return true;
  return card.icon?.elements.includes("fire") === true;
}

export function fireOnField(model: Pick<DrawModel, "tiles" | "units" | "objects">): boolean {
  return (
    model.tiles.some((t) => t.surface === "fire") ||
    model.objects.some((o) => o.burning) ||
    model.units.some((u) => u.statusIds?.includes("burning") === true)
  );
}

export function flameEmphasis(
  model: Pick<DrawModel, "tiles" | "units" | "objects">,
  selected: IgniteCard | null | undefined,
): boolean {
  return skillIgnites(selected) || fireOnField(model);
}
