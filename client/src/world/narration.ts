// 說書人文字的擺法（Phase 6C-7；21.7、docs/archive/art/HUD版面.md 5.7）的純函式：
// - 字幕：畫面上方一行，幾秒後淡出；點「多講一點」看完整旁白；
// - 對話框：一次一段（1～2 句），按一下播下一段；
// - 選項圖示、屬性圖示、骰子動畫的每一格與結束狀態。
// 只決定畫面怎麼擺，規則與數值都照後端 `WorldView`。
import type { WorldEventSolution, WorldStory } from "../api/types";

// ---- 句子與分段 ----

/** 以。！？切句（保留標點）；空字串回傳空陣列。 */
export function sentences(text: string): string[] {
  const t = text.trim();
  if (t === "") return [];
  return (t.match(/[^。！？!?]+[。！？!?」』]*/g) ?? [t]).map((s) => s.trim()).filter((s) => s !== "");
}

/** 對話框一段最多幾個字（超過就換下一段；單句太長時整句一段）。 */
export const PAGE_MAX = 48;

/** 一段文字 → 對話框的段落（每段 1～2 句、不超過 `PAGE_MAX` 字）。 */
export function storyPages(text: string): string[] {
  const out: string[] = [];
  let cur = "";
  let count = 0;
  for (const s of sentences(text)) {
    if (cur !== "" && (count >= 2 || [...cur].length + [...s].length > PAGE_MAX)) {
      out.push(cur);
      cur = "";
      count = 0;
    }
    cur += s;
    count += 1;
  }
  if (cur !== "") out.push(cur);
  return out;
}

/** 對話框的狀態：目前第幾段、要不要顯示「下一段」與「多講一點」。 */
export interface DialogState {
  pages: string[];
  index: number;
  /** 已經把「多講一點」的段落接上。 */
  expanded: boolean;
}

export function dialogStart(story: WorldStory): DialogState {
  return { pages: storyPages(story.text_zh), index: 0, expanded: false };
}

export const hasNext = (s: DialogState): boolean => s.index < s.pages.length - 1;

/** 還有「多講一點」可以接（播到最後一段、還沒接、後端有給）。 */
export function canMore(s: DialogState, story: WorldStory): boolean {
  return !s.expanded && !hasNext(s) && (story.more_zh ?? "") !== "";
}

/** 按一下：還有下一段就播下一段；沒有時不動。 */
export function dialogNext(s: DialogState): DialogState {
  return hasNext(s) ? { ...s, index: s.index + 1 } : s;
}

/** 「多講一點」：把補充的段落接在後面，跳到第一段補充。 */
export function dialogMore(s: DialogState, story: WorldStory): DialogState {
  if (!canMore(s, story)) return s;
  const more = storyPages(story.more_zh ?? "");
  return { pages: [...s.pages, ...more], index: s.pages.length, expanded: true };
}

// ---- 字幕 ----

/** 字幕顯示多久開始淡出（毫秒）。 */
export const SUBTITLE_MS = 6000;
/** 淡出的時間（毫秒）。 */
export const SUBTITLE_FADE_MS = 800;
/** 字幕一行最多幾個字。 */
export const SUBTITLE_MAX = 40;

/** 字幕那一行：第一句，太長截斷加「……」。 */
export function subtitleLine(text: string): string {
  const first = sentences(text)[0] ?? "";
  return [...first].length > SUBTITLE_MAX ? `${[...first].slice(0, SUBTITLE_MAX).join("")}……` : first;
}

/** 字幕有沒有比一行更多的內容（要不要給「多講一點」）。 */
export function subtitleHasMore(story: WorldStory): boolean {
  return subtitleLine(story.text_zh) !== story.text_zh.trim() || (story.more_zh ?? "") !== "";
}

export type SubtitlePhase = "show" | "fade" | "gone";

/** 過了 `elapsed` 毫秒時字幕的樣子；展開（看完整旁白）時一直顯示。 */
export function subtitlePhase(elapsed: number, expanded: boolean, ms = SUBTITLE_MS, fade = SUBTITLE_FADE_MS): SubtitlePhase {
  if (expanded || elapsed < ms) return "show";
  return elapsed < ms + fade ? "fade" : "gone";
}

// ---- 選項圖示 ----

export type SolutionIcon = "combat" | "persuade" | "sneak" | "investigate" | "force" | "chance" | "leave" | "trade";

export const SOLUTION_ICON_ZH: Readonly<Record<SolutionIcon, string>> = {
  combat: "戰鬥",
  persuade: "說服",
  sneak: "潛行",
  investigate: "調查",
  force: "硬闖",
  chance: "機遇",
  leave: "放棄",
  trade: "交涉",
};

/** 情境判定的方法關鍵字 → 圖示（照順序找第一個）。 */
const METHOD_WORDS: readonly (readonly [SolutionIcon, RegExp])[] = [
  ["sneak", /潛|躲|繞|偷|溜|藏|摸黑/u],
  ["persuade", /說服|勸|談|騙|哄|交談|安撫|嚇|威|唬|講/u],
  ["investigate", /查|找|看|辨|察|聽|嗅|搜|讀|認/u],
  ["force", /撞|推|搬|爬|闖|扛|拉|劈|砸|硬|游|跳/u],
];

/** 屬性 → 沒有關鍵字時的退回圖示。 */
const ATTR_ICON: Readonly<Record<AttrKey, SolutionIcon>> = { str: "force", con: "force", dex: "sneak", int: "investigate", wis: "investigate", wil: "persuade" };

/** 選項前面的圖示：戰鬥、交涉、機遇、放棄照種類；情境判定看方法的關鍵字，沒有時看第一個屬性。 */
export function solutionIcon(s: Pick<WorldEventSolution, "kind" | "note_zh" | "attributes_zh">): SolutionIcon {
  switch (s.kind) {
    case "combat":
      return "combat";
    case "parley":
      return "trade";
    case "opportunity":
      return "chance";
    case "abandon":
      return "leave";
    default:
      break;
  }
  for (const [icon, re] of METHOD_WORDS) if (re.test(s.note_zh)) return icon;
  const first = attrKeys(s.attributes_zh)[0];
  return first !== undefined ? ATTR_ICON[first] : "investigate";
}

/** 選項按鈕上的一行字：情境判定與交涉用說明（`note_zh`），其他用種類名。 */
export function solutionLine(s: Pick<WorldEventSolution, "kind" | "kind_zh" | "note_zh">): string {
  return s.note_zh !== "" && s.kind !== "abandon" && s.kind !== "combat" ? s.note_zh : s.kind_zh;
}

// ---- 屬性 ----

export type AttrKey = "str" | "dex" | "con" | "int" | "wis" | "wil";

export const ATTR_ZH: Readonly<Record<AttrKey, string>> = { str: "力量", dex: "敏捷", con: "體質", int: "智力", wis: "感知", wil: "意志" };
const ZH_ATTR: Readonly<Record<string, AttrKey>> = Object.fromEntries(Object.entries(ATTR_ZH).map(([k, v]) => [v, k as AttrKey]));

/** 中文屬性名 → 屬性；不認得為 `null`。 */
export const attrKey = (zh: string): AttrKey | null => ZH_ATTR[zh.trim()] ?? null;

/** 「感知、力量」→ ["wis", "str"]（不認得的略過）。 */
export function attrKeys(text: string): AttrKey[] {
  return text
    .split(/[、,，／/]/u)
    .map(attrKey)
    .filter((k): k is AttrKey => k !== null);
}

// ---- 擲骰 ----

/** 骰子動畫的時間（毫秒）。 */
export const DICE_MS = 900;
/** 動畫中每格換一次面的間隔（毫秒）。 */
export const DICE_TICK_MS = 70;

export type Outcome = "success" | "partial" | "failure";

/** 結果的顏色（成功綠、勉強黃、失敗紅）。 */
export const OUTCOME_COLOR: Readonly<Record<Outcome, string>> = { success: "#5ad06a", partial: "#e8bb48", failure: "#e04a3a" };

/** 擲骰用的是哪一顆：一般取第一顆；優勢、劣勢取和 `roll` 相同的那一顆。 */
export function usedDie(dice: readonly [number, number] | readonly number[], roll: number): 0 | 1 {
  return dice[0] === roll ? 0 : 1;
}

export interface DiceFrame {
  faces: [number, number];
  done: boolean;
  /** 結束後用的那一顆（動畫中為 `null`）。 */
  used: 0 | 1 | null;
}

/**
 * 過了 `elapsed` 毫秒時兩顆骰的樣子。動畫中照固定的序列換面（確定性、不用亂數），
 * 結束時是真正的點數並標出用的那一顆。
 */
export function diceFrame(dice: readonly number[], roll: number, elapsed: number, ms = DICE_MS): DiceFrame {
  const a = dice[0] ?? 1;
  const b = dice[1] ?? 1;
  if (elapsed >= ms) return { faces: [a, b], done: true, used: usedDie([a, b], roll) };
  const t = Math.floor(elapsed / DICE_TICK_MS);
  return { faces: [((a + t * 7) % 20) + 1, ((b + t * 13 + 5) % 20) + 1], done: false, used: null };
}
