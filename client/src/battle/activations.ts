// 常駐類傳說（Phase 3D-6）：生效中的啟動、剩餘輪數與 HUD 文字（純函式）。
import type { ActivationView, BattleView, UnitView } from "../api/types";

/**
 * 限時傳說還剩幾輪（含本輪）：在持有者第 `expires_round` 輪的回合開始時結束，
 * 所以是 `expires_round − 目前輪數`。整場型為 `null`。
 */
export function activationRemaining(view: BattleView, a: ActivationView): number | null {
  if (a.expires_round === null) return null;
  return Math.max(0, a.expires_round - view.round);
}

/** HUD 的一行：「戰神降臨：剩 3 輪（第 4 輪你的回合開始時結束）」「慈焰誓約（規則改變「慈焰」）：整場」。 */
export function activationLine(view: BattleView, a: ActivationView): string {
  const rule = a.rule_name_zh === null ? "" : `（規則改變「${a.rule_name_zh}」）`;
  const left = activationRemaining(view, a);
  const when = left === null ? "整場" : `剩 ${left} 輪（第 ${a.expires_round} 輪你的回合開始時結束）`;
  return `${a.name_zh}${rule}：${when}`;
}

/** 技能按鈕的停用原因：這個常駐類傳說已經啟動（`null` 表示沒有啟動）。 */
export function activeReason(hero: UnitView, skillId: string): string | null {
  const found = (hero.activations ?? []).find((a) => a.skill_id === skillId);
  if (found === undefined) return null;
  return found.expires_round === null ? "已啟動（整場有效）" : `已啟動（到第 ${found.expires_round} 輪你的回合開始）`;
}
