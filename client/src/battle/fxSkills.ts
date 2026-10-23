// 戰場效果（陷阱、持續區域，Phase 3-36b）需要的技能資料：觸發方式、元素、表面。
// 來源是技能卡的 `icon`（前端的技能表）；查不到技能時回傳 `undefined`，畫法退回「踩到觸發＋灰色」。
import type { SkillCard } from "../api/types";

export interface FxSkill {
  /** 技能效果上的第一個元素（陷阱的元素色）；沒有為 `null`。 */
  element: string | null;
  /** 區域效果（子效果）上的第一個元素；沒有為 `null`。 */
  zoneElement: string | null;
  /** 技能效果產生的表面（區域元素色的備案）；沒有為 `null`。 */
  surface: string | null;
  /** 陷阱觸發方式（`enter`／`delay`）；不是陷阱為 `null`。 */
  trapTrigger: string | null;
}

export type FxSkills = (skillId: string) => FxSkill | undefined;

export function fxSkillOf(card: SkillCard): FxSkill {
  const icon = card.icon;
  let surface: string | null = null;
  for (const seg of icon.segments) {
    for (const e of seg.effects) {
      if (surface === null && e.surface != null && e.surface !== "") surface = e.surface;
    }
  }
  return {
    element: icon.elements[0] ?? null,
    zoneElement: icon.zone_element ?? null,
    surface,
    trapTrigger: icon.trap_trigger ?? null,
  };
}

/** 技能卡快取 → 查表函式。 */
export function fxSkillsOf(cards: Readonly<Record<string, SkillCard | undefined>>): FxSkills {
  return (skillId) => {
    const card = cards[skillId];
    return card === undefined ? undefined : fxSkillOf(card);
  };
}
