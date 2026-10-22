// 召喚物的灌注關鍵字（Phase 3-33b，docs/design/06-技能.md 6.29.1）：
// 召喚技能的目標選好後多一步「選關鍵字」；召喚物普攻命中後附加該關鍵字對應的效果。
// 可選的關鍵字由伺服器依施放者持有的關鍵字與對照表算出（UnitView.infusion_options，第一個是預設）。
import type { Action, SkillCard, UnitView } from "../api/types";

export type InfusionOption = NonNullable<UnitView["infusion_options"]>[number];

/** 技能是不是召喚技能：製造「召喚」關鍵字（伺服器依 summon 原語推導）。 */
export function isSummonCard(card: SkillCard | undefined): boolean {
  return card?.keywords.makes.some((k) => k.id === "summon") ?? false;
}

/**
 * 送出 `action` 之前要不要問灌注哪個關鍵字：召喚技能、還沒指定、施放者有 2 個以上可選時才問
 * （只有 1 個時直接用預設）。回傳要列出的選項；不用問時回傳空陣列。
 */
export function infusionChoices(
  caster: UnitView | null,
  action: Action,
  cards: Readonly<Record<string, SkillCard | undefined>>,
): readonly InfusionOption[] {
  if (caster === null || action.type !== "use_skill" || action.infusion != null) return [];
  const options = caster.infusion_options ?? [];
  if (options.length < 2 || !isSummonCard(cards[action.skill_id])) return [];
  return options;
}

/** 帶上選好的關鍵字。 */
export function withInfusion(action: Action, keywordId: string): Action {
  return action.type === "use_skill" ? { ...action, infusion: keywordId } : action;
}

/** 召喚物灌注的關鍵字名稱（「點燃」）；沒有灌注時 `null`。`owner` 是召喚者（查名稱用）。 */
export function infusionName(unit: UnitView, owner: UnitView | null): string | null {
  if (unit.infusion == null) return null;
  return owner?.infusion_options?.find((o) => o.id === unit.infusion)?.name_zh ?? unit.infusion;
}

/** 視窗的提示文字。 */
export function infusionPromptText(skillName: string, count: number): string {
  return `${skillName}：選一個關鍵字灌注給召喚物（共 ${count} 個可選）。召喚物的普攻命中後會附加它的效果。`;
}
