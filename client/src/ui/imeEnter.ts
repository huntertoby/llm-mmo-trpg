// 文字輸入框按 Enter 送出的共用判斷（TXT-2，`docs/phases/現代網頁指南試用.md` 第 A 項）。
// 注音、倉頡、拼音、日文輸入法用 Enter「確定選字」；選字中的那一下不能當成送出，否則會把半截字送出去。
// 同時看 `isComposing` 與 `keyCode === 229`：Safari 不支援 `isComposing`（舊版還會先送 `compositionend`
// 再送 `keydown`），組字中按 Enter 的 `keyCode` 是 229。所有文字輸入框的 Enter 處理都要經過這裡
// （`imeEnterRule.test.ts` 掃原始碼檢查）。

/** 鍵盤事件需要的欄位（React 的 `KeyboardEvent` 與原生 `KeyboardEvent` 都符合）。 */
export interface EnterKeyEvent {
  key: string;
  keyCode: number;
  nativeEvent?: { isComposing?: boolean };
  isComposing?: boolean;
}

/** 輸入法正在組字（這一下 Enter 是選字，不是送出）。 */
export function isImeComposing(e: EnterKeyEvent): boolean {
  return e.nativeEvent?.isComposing === true || e.isComposing === true || e.keyCode === 229;
}

/** 文字輸入框裡「要送出」的 Enter：是 Enter，而且不是輸入法選字。 */
export function isSubmitEnter(e: EnterKeyEvent): boolean {
  return e.key === "Enter" && !isImeComposing(e);
}
