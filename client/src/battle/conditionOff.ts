// 本場條件不成立的技能標灰（LW-2，06 6.37「提示與標灰」）：伺服器 `BattleResponse.skills_off` 列出主角帶
// 「整場固定」條件（目前只有獨狼 `lone_wolf`）而本場不成立的技能。技能列與說明卡把它標灰並寫原因。
// - 只管「看起來」：招能不能按照舊看 `legal_actions`／`disabledReason`（帶條件的效果不發動，其餘照常能用）。
// - 之後別的整場固定條件（BS-2「要拿匕首類」）由後端 `trpg.api.condition_off.STICKY_CONDITIONS` 加一筆即可，
//   這裡不認條件種類，只照 `whole` 分兩種字。
import type { SkillOff } from "../api/types";
import type { SkillButton } from "./targeting";

/** 一招的標灰：原因（伺服器給）＋是不是整招不會生效。 */
export interface ConditionOffMark {
  reason: string;
  /** 技能層級的條件：整招（被動整個）不會生效；`false`＝只有帶條件的那部分效果不會發動。 */
  whole: boolean;
}

export type ConditionOffMap = Readonly<Record<string, ConditionOffMark>>;

/** 伺服器的清單 → 技能 ID 對照（沒有欄位＝沒有要標灰的）。 */
export function conditionOffMap(list: readonly SkillOff[] | null | undefined): ConditionOffMap {
  const map: Record<string, ConditionOffMark> = {};
  for (const s of list ?? []) map[s.skill_id] = { reason: s.reason_zh, whole: s.whole };
  return map;
}

/** 把標灰套到技能按鈕（其他欄位不動；沒有標灰的按鈕原樣）。 */
export function withConditionOff(buttons: readonly SkillButton[], map: ConditionOffMap): SkillButton[] {
  return buttons.map((b) => {
    const mark = map[b.skillId];
    return mark === undefined ? b : { ...b, conditionOff: mark };
  });
}

/** 按鈕、小圖示加的 class（前面帶空白，直接接在既有 class 後面）。 */
export function conditionOffClass(mark: ConditionOffMark | null | undefined): string {
  return mark == null ? "" : " cond-off";
}

/** 說明卡第一行的後半句：整招不生效或只有那部分不發動。 */
export const OFF_WHOLE_ZH = "這一招本場不會生效";
export const OFF_PART_ZH = "帶條件的效果本場不會發動，其餘照常";

/** 說明卡第一行（「本場不成立：開戰時身邊有隊友，獨狼本場不成立（帶條件的效果本場不會發動，其餘照常）」）。 */
export function conditionOffLine(mark: ConditionOffMark): string {
  return `本場不成立：${mark.reason}（${mark.whole ? OFF_WHOLE_ZH : OFF_PART_ZH}）`;
}

/** 按鈕與小圖示的無障礙說明（螢幕閱讀器念出「本場不成立」）。 */
export function conditionOffLabel(name: string, mark: ConditionOffMark | null | undefined): string {
  return mark == null ? name : `${name}（本場不成立：${mark.reason}）`;
}
