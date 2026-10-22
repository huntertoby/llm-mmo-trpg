// 裝備授予的常駐技能（Phase 3G-G3b，第 9 類詞條）：技能列的「來自裝備」標記（純函式）。
// 技能本身在 `UnitView.skills` 裡；`gear_skills` 說明它來自哪個欄位的哪件物品。卸下裝備後伺服器就不再列出。
import type { GearSkillView, UnitView } from "../api/types";

/** 單位身上由裝備授予的技能（沒有時為空陣列）。 */
export function gearSkillsOf(u: UnitView): readonly GearSkillView[] {
  return u.gear_skills ?? [];
}

/** 這個技能若是裝備授予的，來源的說明（「欄位：物品名」）；不是裝備來的時 `null`。 */
export function gearSkillSource(u: UnitView, skillId: string): string | null {
  const g = gearSkillsOf(u).find((s) => s.skill_id === skillId);
  return g === undefined ? null : `${g.slot_zh}：${g.item_name_zh}`;
}

/** 技能列上的標記文字：「來自裝備・副手：壁壘塔盾」。 */
export function gearSkillBadge(source: string): string {
  return `來自裝備・${source}`;
}
