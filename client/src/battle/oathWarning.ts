// 誓約警告（Phase 5C-3b；06 6.26「會違反誓約的動作按下前先警告」）。
// 判定全部在引擎（`POST /battles/{id}/preview` 的 `oath_warning`），前端不猜：只有「戰鬥有誓約、還沒違反」
// （`oath_active`）時，送出動作之前才多問一次預覽；有警告就先跳確認。純函式，測試在 oathWarning.test.ts。
import type { Action, BattleResponse, PreviewOut } from "../api/types";

/** 送出這個動作之前要不要問誓約警告：戰鬥有誓約且還沒違反，而且是主角自己的動作。 */
export function needsOathCheck(response: Pick<BattleResponse, "oath_active" | "hero_id">, action: Action): boolean {
  if (response.oath_active !== true) return false;
  return "unit_id" in action && action.unit_id === response.hero_id;
}

/** 預覽帶回的警告文字；沒有警告為 `null`。 */
export function oathWarningOf(preview: Pick<PreviewOut, "oath_warning"> | null): string | null {
  const text = preview?.oath_warning ?? null;
  return text === null || text === "" ? null : text;
}

export const OATH_CONFIRM_LABEL = "仍要執行（違反誓約）";
export const OATH_CANCEL_LABEL = "取消，不執行";
