// 技能點與技能等級（Phase 3-26a）的純函式：分配草稿、費用、營火換裝。數值（每級花幾點、最高幾級）
// 都來自伺服器（`hero.skill_growth`、每張卡的 `growth`），前端不寫死。
import type { RunChoice, RunHero, SkillCard } from "../api/types";
import { SLOT_LIMITS, slotOf, slotUsage, type SlotKind } from "./flow";

/** 分配草稿：技能 ID → 想升到的等級（只放比目前高的）。 */
export type LevelDraft = Readonly<Record<string, number>>;

/** 技能目前的等級（沒有成長資料的技能——被動、反應、姿態——視為 1，不能升級）。 */
export function levelOf(card: Pick<SkillCard, "growth">): number {
  return card.growth?.level ?? 1;
}

/** 技能卡上的等級標籤，例如「Lv.3」。 */
export function levelBadge(level: number): string {
  return `Lv.${level}`;
}

/** 草稿裡這張卡的等級（沒動過為目前等級）。 */
export function draftLevel(card: SkillCard, draft: LevelDraft): number {
  return draft[card.id] ?? levelOf(card);
}

/** 草稿要花的技能點。 */
export function draftCost(hero: RunHero, draft: LevelDraft): number {
  const per = hero.skill_growth?.upgrade_cost ?? 1;
  let total = 0;
  for (const card of hero.skills) total += (draftLevel(card, draft) - levelOf(card)) * per;
  return total;
}

export function pointsLeft(hero: RunHero, draft: LevelDraft): number {
  return (hero.skill_points ?? 0) - draftCost(hero, draft);
}

export function canRaise(hero: RunHero, card: SkillCard, draft: LevelDraft): boolean {
  const growth = hero.skill_growth;
  if (card.growth == null || growth == null) return false;
  return draftLevel(card, draft) < growth.max_level && pointsLeft(hero, draft) >= growth.upgrade_cost;
}

export function canLower(card: SkillCard, draft: LevelDraft): boolean {
  return card.growth != null && draftLevel(card, draft) > levelOf(card);
}

/** 草稿加減一級（不能低於目前等級、不能超過最高等級或剩下的點數）。 */
export function adjustLevel(hero: RunHero, card: SkillCard, draft: LevelDraft, delta: 1 | -1): LevelDraft {
  if (delta > 0 ? !canRaise(hero, card, draft) : !canLower(card, draft)) return draft;
  const next = draftLevel(card, draft) + delta;
  const out = { ...draft };
  if (next <= levelOf(card)) delete out[card.id];
  else out[card.id] = next;
  return out;
}

export function hasDraft(draft: LevelDraft): boolean {
  return Object.keys(draft).length > 0;
}

/** 送出的 `levels`（技能 ID 排序，穩定）。 */
export function draftLevels(draft: LevelDraft): Record<string, number> {
  const out: Record<string, number> = {};
  for (const id of Object.keys(draft).sort()) out[id] = draft[id] as number;
  return out;
}

export function spendChoice(draft: LevelDraft): RunChoice {
  return { kind: "spend", levels: draftLevels(draft) };
}

/** 技能卡上顯示的等級說明：目前等級、下一級、小特性（沒有成長資料的技能為空）。 */
export function growthLines(card: Pick<SkillCard, "growth">): string[] {
  const g = card.growth;
  if (g == null) return [];
  const lines = [g.current_text];
  if (g.next_text != null) lines.push(`下一級　${g.next_text}`);
  lines.push(g.trait_text);
  return lines;
}

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
