// 技能點與技能等級（Phase 3-26a）的純函式：分配草稿、費用、營火換裝。數值（每級花幾點、最高幾級）
// 都來自伺服器（`hero.skill_growth`、每張卡的 `growth`），前端不寫死。
import type { EvolutionChoice, EvolutionOption, RunChoice, RunHero, SkillCard } from "../api/types";
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
  const next = draftLevel(card, draft) + 1;
  return next <= growth.max_level && pointsLeft(hero, draft) >= growth.upgrade_cost && !evolveBlocked(hero, card, next);
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

export function spendChoice(draft: LevelDraft, evolve: Record<string, number> = {}): RunChoice {
  const base = { kind: "spend" as const, levels: draftLevels(draft) };
  return Object.keys(evolve).length > 0 ? { ...base, evolve: { ...evolve } } : base;
}

// ---- 分歧進化（Phase 3-26b）------------------------------------------------------------

/** 進化草稿：技能 ID → 選的分支索引（`hero.evolutions[].options[].index`）。 */
export type EvolveDraft = Readonly<Record<string, number>>;

/** 升到 `target` 會經過分歧進化（還沒進化過的技能才會）。 */
export function crossesEvolution(hero: RunHero, card: SkillCard, target: number): boolean {
  const growth = hero.skill_growth;
  if (growth == null || card.growth == null) return false;
  return levelOf(card) < growth.evolve_level && target >= growth.evolve_level && card.growth.evolved_from_zh == null;
}

/** 升到 `target` 被分歧進化的門檻擋住（這一輪用過的次數不夠）。 */
export function evolveBlocked(hero: RunHero, card: SkillCard, target: number): boolean {
  const need = hero.skill_growth?.evolve_uses ?? 0;
  return crossesEvolution(hero, card, target) && (card.growth?.uses ?? 0) < need;
}

/** 下一級升不了的原因（門檻沒到時）；可以升為 `null`。 */
export function raiseBlockedText(hero: RunHero, card: SkillCard, draft: LevelDraft): string | null {
  const growth = hero.skill_growth;
  const next = draftLevel(card, draft) + 1;
  if (growth == null || next > growth.max_level || !evolveBlocked(hero, card, next)) return null;
  return (
    card.growth?.blocked_text ??
    `要在這一輪用過 ${growth.evolve_uses} 次才能升到 Lv.${growth.evolve_level}（目前 ${card.growth?.uses ?? 0} 次）`
  );
}

export function evolutionOf(hero: RunHero, skillId: string): EvolutionChoice | undefined {
  return (hero.evolutions ?? []).find((e) => e.skill_id === skillId);
}

/** 草稿經過分歧進化時可選的兩支（沒有經過、或沒有任何合格的進化時為空）。 */
export function evolutionOptions(hero: RunHero, card: SkillCard, draft: LevelDraft): EvolutionOption[] {
  if (!crossesEvolution(hero, card, draftLevel(card, draft))) return [];
  return [...(evolutionOf(hero, card.id)?.options ?? [])];
}

/** 草稿要送出的 `evolve`（只放這次會經過進化、而且選了的技能；依 ID 排序）。 */
export function draftEvolve(hero: RunHero, draft: LevelDraft, evolve: EvolveDraft): Record<string, number> {
  const out: Record<string, number> = {};
  for (const card of [...hero.skills].sort((a, b) => (a.id < b.id ? -1 : 1))) {
    const pick = evolve[card.id];
    if (pick !== undefined && evolutionOptions(hero, card, draft).some((o) => o.index === pick)) out[card.id] = pick;
  }
  return out;
}

/** 經過分歧進化、但還沒選分支的技能（有任何一個時不能送出）。 */
export function missingEvolutions(hero: RunHero, draft: LevelDraft, evolve: EvolveDraft): string[] {
  const picked = draftEvolve(hero, draft, evolve);
  return hero.skills
    .filter((card) => evolutionOptions(hero, card, draft).length > 0 && picked[card.id] === undefined)
    .map((card) => card.name_zh);
}

/** 技能卡上顯示的等級說明：目前等級、下一級、小特性（沒有成長資料的技能為空）。 */
export function growthLines(card: Pick<SkillCard, "growth">): string[] {
  const g = card.growth;
  if (g == null) return [];
  const lines = [g.current_text];
  if (g.evolved_from_zh != null) lines.push(`進化自　${g.evolved_from_zh}`);
  if (g.next_text != null) lines.push(`下一級　${g.next_text}`);
  if (g.blocked_text != null) lines.push(`還不能升級　${g.blocked_text}`);
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
