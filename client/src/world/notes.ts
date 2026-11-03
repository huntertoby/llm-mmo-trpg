// 地點留言與足跡的純函式（Phase 5E-3；09 9.6.10 #105）：留言上限 50 字、不能換行；後端再檢查一次。
export const NOTE_MAX = 50;

/** 送出前的檢查：沒問題回 `null`，否則回顯示給玩家的原因。 */
export function noteProblem(text: string, max: number = NOTE_MAX): string | null {
  const trimmed = text.trim();
  if (trimmed === "") return "留言不能是空的";
  if ([...trimmed].length > max) return `最多 ${max} 字`;
  if (/[\n\r\t]/.test(trimmed)) return "留言不能換行";
  return null;
}

/** 剩餘字數（以字元算，和後端的 `len` 一致）。 */
export function remainingLabel(text: string, max: number = NOTE_MAX): string {
  const left = max - [...text.trim()].length;
  return left >= 0 ? `還可以打 ${left} 字` : `超過 ${-left} 字`;
}

/** 刪除鍵的說明：自己的留言，或管理者刪別人的（5E-3b）。 */
export function noteDeleteLabel(mine: boolean): string {
  return mine ? "刪除我的留言" : "刪除這則留言（管理者）";
}

/** UTC 秒 → 台北時間「11/03 06:05」。 */
export function noteTime(at: number): string {
  const d = new Date((at + 8 * 3600) * 1000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(d.getUTCMonth() + 1)}/${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`;
}
