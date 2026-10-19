// 暫時獲得的技能（Phase 3D-8c，`grant_skill`）：技能列的標記、剩餘輪數與預覽文字（純函式）。
import type { GrantedSkillView, PreviewOut, UnitView } from "../api/types";
import type { UnitNames } from "./units";

/** 單位暫時獲得的技能（沒有時為空陣列）。 */
export function grantedOf(u: UnitView): readonly GrantedSkillView[] {
  return u.granted_skills ?? [];
}

/** 這個技能若是暫時獲得的，還剩幾輪；不是暫時技能時 `null`。 */
export function grantedRemaining(u: UnitView, skillId: string): number | null {
  return grantedOf(u).find((g) => g.skill_id === skillId)?.remaining ?? null;
}

/** 技能列上的標記文字：「暫時・剩 3 輪」。 */
export function grantedBadge(remaining: number): string {
  return `暫時・剩 ${remaining} 輪`;
}

/** HUD 的一行：「飛行 剩 3 輪」。 */
export function grantedLine(g: GrantedSkillView): string {
  return `${g.name_zh} 剩 ${g.remaining} 輪`;
}

/** 預覽：誰會暫時獲得哪個技能、幾輪（已經暫時擁有時只是刷新輪數）。 */
export function grantLines(p: PreviewOut, names: UnitNames): string[] {
  return (p.grants ?? []).map((g) =>
    g.refreshed
      ? `${names.label(g.unit_id)} 的暫時技能「${g.name_zh}」刷新為 ${g.duration} 輪`
      : `${names.label(g.unit_id)} 暫時獲得技能「${g.name_zh}」${g.duration} 輪（在他的回合結束時倒數，不佔技能欄位）`,
  );
}
