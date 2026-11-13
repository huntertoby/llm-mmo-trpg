// 「任務與線頭」面板的純函式（PNL-3；docs/art/資訊面板-移植需求.md 3.3「任務與線頭」、4.1 #24～#28、#40、#42）：分頁記號、步驟兩欄、新字。
import type { WorldQuestLog, WorldView } from "../api/types";
import type { TabBadgeSpec } from "../ui/panelTabRules";

/** 面板標題（字不變）。 */
export const QUEST_PANEL_TITLE_ZH = "任務與線頭";
/** 分頁名與短名（#40 新字「任務」）。 */
export const QUEST_TAB_ZH = { quests: "任務日誌", questsShort: "任務", threads: "線頭", threadsShort: "線頭" } as const;
/** 兩個空狀態（字不變）。 */
export const NO_QUEST_ZH = "還沒有接任務。到小鎮找人說話，看看「可以接的任務」。";
export const NO_THREAD_ZH = "還沒有線頭。事件的結果會留下線頭（每人約 5 條，約 3 天到期）。";
/** 線頭規則句（#28：有線頭時放分頁第一行右邊的 (i)，字不變）；第一行的 L2 短句照樣張。 */
export const THREAD_RULE_ZH = "事件的結果會留下線頭（每人約 5 條，約 3 天到期）。";
export const THREAD_LINE_ZH = "事件的結果會留下線頭";
/** 完成的任務：PNL-4 起收進任務日誌最後的摺疊「已完成（N）」（PNL-3 美術驗收可修 2），卡上不再掛標籤。 */
export const QUEST_DONE_ZH = "已完成";
export const QUEST_DONE_FOLD = "done";
export const questDoneFoldText = (n: number): string => `${QUEST_DONE_ZH}（${n}）`;

/** 進行中的任務數。 */
export const activeQuestCount = (quests: readonly WorldQuestLog[]): number => quests.filter((q) => !q.done).length;

/** 任務日誌分頁：細框「進行中條數」（#27、滑過「進行中 N」）；0 條不掛（純資訊）。 */
export function questsBadge(view: Pick<WorldView, "quests">): TabBadgeSpec | null {
  const n = activeQuestCount(view.quests ?? []);
  return n > 0 ? { kind: "p", value: n, hint: `進行中 ${n}` } : null;
}

/** 線頭分頁：細框「條數」（#42「線頭 2 條」）；0 條不掛。快到期的琥珀三角先不掛（第 5 節第 9 點）。 */
export function threadsBadge(view: Pick<WorldView, "threads">): TabBadgeSpec | null {
  const n = (view.threads ?? []).length;
  return n > 0 ? { kind: "p", value: n, hint: `${QUEST_TAB_ZH.threads} ${n} 條` } : null;
}

export type StepState = "done" | "current" | "todo";

/** 步驟的狀態：綠勾＝完成、金圈＝目前、空圈數字＝未到。 */
export const stepState = (s: WorldQuestLog["steps"][number]): StepState => (s.done ? "done" : s.current ? "current" : "todo");

/**
 * 步驟兩欄（#24）：後端分好的「地點｜要做的事」（`place_zh`、`task_zh`）；舊資料沒有時整句放右欄。
 */
export function stepParts(s: WorldQuestLog["steps"][number]): { place: string | null; task: string } {
  const task = s.task_zh ?? null;
  if (task === null || task === "") return { place: null, task: s.text_zh };
  return { place: s.place_zh ?? null, task };
}

/** 線頭的到期字（#26）：「剩 2 天 23 小時」；舊伺服器沒有 `left_zh` 時用原字。 */
export const threadLeftText = (t: { left_zh?: string | null; expires_zh: string }): string => t.left_zh ?? t.expires_zh;

/** 線頭指向的地點標籤（字照舊「指向○○」）。 */
export const threadPlaceText = (location: string): string => `指向${location}`;
