// 營火換裝的純函式（Phase 3-26a；3W-5 起技能點、技能等級與分歧進化取消，只留換裝）。
import type { RunChoice, RunHero, SkillCard } from "../api/types";
import { SLOT_LIMITS, slotOf, slotUsage, type SlotKind } from "./flow";

// ---- 營火換裝 ----------------------------------------------------------------------------

/** 目前的技能（裝備＋備用）依 ID 查卡片。 */
export function ownedCards(hero: RunHero): Map<string, SkillCard> {
  return new Map([...hero.skills, ...(hero.bench ?? [])].map((c) => [c.id, c]));
}

/** 換裝草稿（裝備清單的 ID，順序即技能列順序）用到的欄位數。 */
export function loadoutUsage(hero: RunHero, ids: readonly string[]): Record<SlotKind, number> {
  const cards = ownedCards(hero);
  return slotUsage(ids.map((id) => cards.get(id)).filter((c): c is SkillCard => c !== undefined));
}

/** 備用技能 `id` 能不能裝上（對應欄位還沒滿；規則改變型傳說的限制由後端 422 補上）。 */
export function canEquip(hero: RunHero, ids: readonly string[], id: string): boolean {
  const card = ownedCards(hero).get(id);
  if (card === undefined || ids.includes(id)) return false;
  const kind = slotOf(card);
  return loadoutUsage(hero, ids)[kind] < SLOT_LIMITS[kind];
}

export function loadoutChanged(hero: RunHero, ids: readonly string[]): boolean {
  return ids.length !== hero.skills.length || ids.some((id, i) => hero.skills[i]?.id !== id);
}

export function loadoutChoice(ids: readonly string[]): RunChoice {
  return { kind: "loadout", skills: [...ids] };
}
