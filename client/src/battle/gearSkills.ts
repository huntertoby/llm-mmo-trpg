// 裝備授予的常駐技能（Phase 3G-G3b，第 9 類詞條）：技能列的「來自裝備」標記（純函式）。
// 技能本身在 `UnitView.skills` 裡；`gear_skills` 說明它來自哪個欄位的哪件物品。卸下裝備後伺服器就不再列出。
// E1（08 8.28）：主動、反應、修正、被動都可能來自裝備；同一招第二份的 `skill_id` 是複本鍵 `<技能 ID>~2`
// （`copy_of` 是原技能），技能列各自一顆按鈕、各自的冷卻。
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

/**
 * 技能列按鈕上的副標題（E1 美術小修 1，玩法 PM 定 A）：只寫裝備名（金框、金字已經表示「來自裝備」）；
 * 放不下時由 CSS 截掉尾巴（不加「…」），完整的「來自裝備・欄位：物品名」在說明卡上方與 aria-label。
 */
export function gearSkillItem(u: UnitView, skillId: string): string | null {
  return gearSkillsOf(u).find((s) => s.skill_id === skillId)?.item_name_zh ?? null;
}

/** 這個裝備授予的技能在主角身上沒有效果的原因（E5：例「這把武器不能套用」）；有效或不是裝備來的時 `null`。 */
export function gearSkillOff(u: UnitView, skillId: string): string | null {
  return gearSkillsOf(u).find((s) => s.skill_id === skillId)?.off_zh ?? null;
}

/** 只有一部分沒有效果時的說明（E5：「這招不能套用：火球」）；沒有時 `null`。 */
export function gearSkillNote(u: UnitView, skillId: string): string | null {
  return gearSkillsOf(u).find((s) => s.skill_id === skillId)?.note_zh ?? null;
}

/** 技能列上的標記文字：「來自裝備・副手：壁壘塔盾」。 */
export function gearSkillBadge(source: string): string {
  return `來自裝備・${source}`;
}
