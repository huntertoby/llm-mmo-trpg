// 灰掉的技能按鈕的原因（Phase 3-5c-2）：本地端能判斷的（冷卻、源力、已啟動）照舊；本地端只能說
// 「目前沒有合法目標」時，改用伺服器（引擎）給的拒絕理由，例如「視線被阻擋」「法力不足」。
import { GENERIC_REASON, type SkillButton } from "./targeting";

export type ReasonMap = Readonly<Record<string, string>>;

/** 把伺服器的原因套到技能按鈕；可用的按鈕與本地端已有具體原因的按鈕不動。 */
export function withReasons(buttons: readonly SkillButton[], reasons: ReasonMap | null): SkillButton[] {
  if (reasons === null) return [...buttons];
  return buttons.map((b) => {
    if (b.disabledReason !== GENERIC_REASON) return b;
    const reason = reasons[b.skillId];
    return reason === undefined ? b : { ...b, disabledReason: reason };
  });
}

/** 點到灰掉的技能時在訊息列顯示的一句話。 */
export function blockedMessage(button: SkillButton): string | null {
  return button.disabledReason === null ? null : `${button.name}不能用：${button.disabledReason}`;
}
