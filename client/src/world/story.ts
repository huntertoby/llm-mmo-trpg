// 大世界事件與任務畫面的純函式（Phase 5B-5；docs/phases/Phase5計畫.md 18.6）。規則與可用狀態都由後端
// `WorldView` 下發（事件卡、可引用的事實、好感度級距、任務步驟），這裡只決定畫面顯示什麼、表單驗證、對話紀錄怎麼累積。
import type { WorldDialogLine, WorldEventSolution, WorldLlmView, WorldQuestLog, WorldView } from "../api/types";

/** 情境判定回答與聊天的長度上限（同後端 PLAYER_TEXT_LIMIT）。 */
export const PLAYER_TEXT_MAX = 500;
/** 一次最多引用幾筆事實（同後端 CARE_CITE_MAX）。 */
export const CITE_MAX = 4;

/** 點一下引用、再點取消；超過上限時不加。 */
export function toggleCite(cited: readonly string[], fact: string): string[] {
  if (cited.includes(fact)) return cited.filter((f) => f !== fact);
  if (cited.length >= CITE_MAX) return [...cited];
  return [...cited, fact];
}

/**
 * 點選引用時把事實的關鍵詞插進回答（5C-3d：引擎要在原文找到關鍵詞才算這筆）。
 * 已經含有、沒有可插的文字、或插了會超過字數上限時不動。
 */
export function insertCite(text: string, insert: string | null | undefined): string {
  if (insert == null || insert === "" || text.includes(insert)) return text;
  const trimmed = text.replace(/\s+$/u, "");
  const next = trimmed === "" ? insert : `${trimmed}，${insert}`;
  return [...next].length > PLAYER_TEXT_MAX ? text : next;
}

/**
 * 畫面角落的「說書人休息中」小標示（5E-3b）：開關開著、但健康檢查說本機模型不可用時顯示
 * （說書人、情境、聊天都改用固定文字；不擋操作）。開關關著是刻意不用，不顯示。
 */
export function narratorResting(llm: Pick<WorldLlmView, "enabled" | "model_available"> | null): boolean {
  return llm !== null && llm.enabled && llm.model_available === false;
}

/** 輸入框下方的字數（例：「12／500」）；超過時加「（太長）」。 */
export function lengthLabel(text: string): string {
  const n = [...text].length;
  return `${n}／${PLAYER_TEXT_MAX}${n > PLAYER_TEXT_MAX ? "（太長）" : ""}`;
}

/** 回答能不能送出：不超過上限（空白也可以送，照降級提議判定）。 */
export function canSubmitAnswer(text: string, busy: boolean): boolean {
  return !busy && [...text].length <= PLAYER_TEXT_MAX;
}

/** 聊天能不能送出：有字、不超過上限。 */
export function canSendChat(text: string, busy: boolean): boolean {
  const n = [...text.trim()].length;
  return !busy && n > 0 && n <= PLAYER_TEXT_MAX;
}

/** 解法按鈕的文字：「情境判定：找安全路（感知、力量）」；交涉多顯示付出的補給。 */
export function solutionLabel(s: WorldEventSolution): string {
  const note = s.note_zh !== "" ? `：${s.note_zh}` : "";
  const attrs = s.attributes_zh !== "" ? `（${s.attributes_zh}）` : "";
  const cost = s.kind === "parley" && s.cost_supplies > 0 ? `（付出 ${s.cost_supplies} 補給）` : "";
  return `${s.kind_zh}${note}${attrs}${cost}`;
}

/** 解法按鈕的說明卡：可以用時的說明（內容的補充說明 `hint_zh` 在前一行，TXT-1）、不能用時的原因。 */
export function solutionHint(s: WorldEventSolution): string {
  if (!s.available) return s.unavailable_zh ?? "現在不能用";
  const extra = s.hint_zh ?? "";
  const base = solutionKindHint(s);
  return extra !== "" ? `${extra}\n${base}` : base;
}

function solutionKindHint(s: WorldEventSolution): string {
  switch (s.kind) {
    case "abandon":
      return "不管這件事，不留懲罰，事件就此結束";
    case "parley":
      return s.cost_supplies > 0 ? `不擲骰、一定成功；付出 ${s.cost_supplies} 補給` : "不擲骰、一定成功";
    case "combat":
      return "在這裡開一場一般戰鬥；打贏才算解決，輸了或撤退事件就作罷";
    case "opportunity":
      return "得到一次機遇技能三選一（完整技能）；同一個機遇只能拿一次";
    default:
      return "看看處境，再寫你打算怎麼做（送出前可以換別的解法）";
  }
}

/** 持有線頭、可以抵掉交涉付出時的按鈕文字：「用〔商人欠你人情〕抵」。 */
export function waiveLabel(s: WorldEventSolution): string | null {
  if (s.kind !== "parley" || s.waive_thread == null) return null;
  return `用〔${s.waive_zh ?? s.waive_thread}〕抵`;
}

/** 這個解法按下去要送什麼：情境判定開情境（`open`），其他（含機遇，5B-4c）送 `event_solve`（`solve`）。 */
export function solutionClick(
  s: WorldEventSolution,
): { kind: "open"; template: string } | { kind: "solve"; solution: number } | null {
  if (s.kind === "situation") return s.template != null ? { kind: "open", template: s.template } : null;
  if (s.kind === "abandon" || s.kind === "parley" || s.kind === "combat" || s.kind === "opportunity")
    return { kind: "solve", solution: s.index };
  return null;
}

/** 任務步驟前的記號：已完成 ✔、目前 ▶、還沒到 ・。 */
export function stepMark(step: WorldQuestLog["steps"][number]): string {
  if (step.done) return "✔";
  return step.current ? "▶" : "・";
}

/** 任務日誌的排序：進行中在前、完成的在後（各自照後端順序）。 */
export function sortQuests(quests: readonly WorldQuestLog[]): WorldQuestLog[] {
  return [...quests.filter((q) => !q.done), ...quests.filter((q) => q.done)];
}

/** 好感度一行：「中立（−9～19）・目前 0」。 */
export function affinityLine(npc: { range_zh: string; affinity: number }): string {
  const value = npc.affinity < 0 ? `−${-npc.affinity}` : String(npc.affinity);
  return `${npc.range_zh}・目前 ${value}`;
}

/** 一則對話紀錄（前端保留，代決 5B5-8）。 */
export interface ChatEntry {
  speaker: string;
  text: string;
  more?: string;
  mine: boolean;
}

const KIND_TAG: Record<WorldDialogLine["kind"], string> = {
  rumor: "傳聞",
  quest_entry: "任務入口",
  secret: "祕密",
  chat: "",
  nothing: "",
  tavern: "傳聞",
};

/** 後端的對話行 → 紀錄（傳聞、入口、祕密加標籤）。 */
export function dialogEntries(lines: readonly WorldDialogLine[]): ChatEntry[] {
  return lines.map((line) => {
    const tag = KIND_TAG[line.kind];
    return { speaker: line.speaker_zh, text: tag !== "" ? `〔${tag}〕${line.text_zh}` : line.text_zh, more: line.more_zh || undefined, mine: false };
  });
}

/** 把這次的對話接到該 NPC 的紀錄後面（最多留 `max` 則）。 */
export function appendChat(log: Readonly<Record<string, ChatEntry[]>>, npc: string, entries: readonly ChatEntry[], max = 30): Record<string, ChatEntry[]> {
  if (entries.length === 0) return { ...log };
  const next = [...(log[npc] ?? []), ...entries].slice(-max);
  return { ...log, [npc]: next };
}

/** 依 NPC 分組這次回應的對話行。 */
export function dialogByNpc(lines: readonly WorldDialogLine[]): Record<string, WorldDialogLine[]> {
  const out: Record<string, WorldDialogLine[]> = {};
  for (const line of lines) {
    if (line.npc === null || line.npc === undefined) continue;
    (out[line.npc] ??= []).push(line);
  }
  return out;
}

/** 右側「任務與線頭」按鈕上的小字：進行中任務數・線頭數。 */
export function questBadge(view: WorldView): string {
  const active = (view.quests ?? []).filter((q) => !q.done).length;
  const threads = (view.threads ?? []).length;
  const parts: string[] = [];
  if (active > 0) parts.push(`任務 ${active}`);
  if (threads > 0) parts.push(`線頭 ${threads}`);
  return parts.join("・");
}

/** 判定明細的算式：「d20 12（一般）＋屬性 1＋用心 1＋種族 0 ＝ 14 vs DC 12（基準 13，−1）」。 */
export function checkFormula(r: {
  roll: number;
  mode_zh: string;
  attribute_mod: number;
  care_bonus: number;
  race_bonus: number;
  total: number;
  dc: number;
  base_dc: number;
  dc_shift: number;
}): string {
  const sign = (n: number) => (n < 0 ? `−${-n}` : `＋${n}`);
  const shift = r.dc_shift === 0 ? "" : `，${r.dc_shift < 0 ? "−" : "＋"}${Math.abs(r.dc_shift)}`;
  return `d20 ${r.roll}（${r.mode_zh}）${sign(r.attribute_mod)}屬性${sign(r.care_bonus)}用心${sign(r.race_bonus)}種族 ＝ ${r.total} vs DC ${r.dc}（基準 ${r.base_dc}${shift}）`;
}
