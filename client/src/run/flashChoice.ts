// 靈感閃現「選變體」畫面改版（FL-1b，docs/art/靈感閃現選擇-移植需求.md）的純函式與定稿字。
// 欄位名、單位、大標、一句話、說明卡全部由伺服器給（`FlashOptionOut.changes`、`headline_zh`、`say_zh`、`PendingFlashOut.terms`；
// 開發 PM 第 12 節決定 1：對照表在後端 `flash_changes.py`）；這裡只決定樣式與排法、解析術語標記。
import type { FlashOption, PendingFlash, SkillCard, StatChange } from "../api/types";
import { LLM_SOURCE_LABEL } from "./llmFlow";

// ---- 定稿字（9.1） ------------------------------------------------------------------------

/** 9.1 #19。 */
export const FLASH_PICK_TITLE_ZH = "靈感閃現";
export const FLASH_PICK_SUBTITLE_ZH = "選一個變化";
/** 9.1 #34（寬版上固定區；窄版收進 (i)）。 */
export const FLASH_MUST_PICK_ZH = "一定要選一個。選哪個這招整體都會強一點，標 ▼ 的是拿來換的";
/** 有轉型選項的面板用這句（FL-1h，06 6.34.5「轉型不套強度下限」，玩法 PM 選 (b)）：轉型照新種類重算強度，不跟原本比。 */
export const FLASH_MUST_PICK_TRANSFORM_ZH = "一定要選一個。選哪個這招整體都會強一點（轉型除外），標 ▼ 的是拿來換的";
/** 選中轉型卡時，下固定區一句話的句末接這句（FL-1h，06 6.34.5）。 */
export const FLASH_TRANSFORM_FOOT_ZH = "轉型後照新種類重算強度，不跟原本比。";
/** 重閃選項整招和現在一樣、前 → 後一列都沒有時，卡裡放的那一行（FL-1h，玩法 PM 交接 4.1.2 第 4 條；美術 RR-2 可修 2）。 */
export const FLASH_SAME_AS_NOW_ZH = "和現在一樣，選了這招不會變";
/** 9.1 #21（都沒選時的下固定區）。 */
export const FLASH_PICK_NONE_ZH = "先點一個變化。點數已經扣了，一定要選一個。";
/** 9.1 #22。 */
export const FLASH_BASE_WIDE_ZH = "原本的樣子";
export const FLASH_BASE_NARROW_ZH = "原本";
export const FLASH_MORE_WIDE_ZH = "完整說明";
export const FLASH_MORE_NARROW_ZH = "說明";
/** 大世界這個面板鎖住時的提示（2.1；字不變）。 */
export const FLASH_LOCK_NOTE_ZH = "先選完閃現的變化：選之前不能移動、開戰或使用其他服務。";
/** 「後」是 null（拿掉的效果）時寫的字（開發 PM 第 12 節決定 5）。 */
export const FLASH_NONE_ZH = "沒有";

// ---- 標頭 --------------------------------------------------------------------------------

/** 第幾次（9.1 #20）：「第 1 次閃現」；重閃照現行「重閃調整欄」「重閃第 N 次」；大變化加「（大變化）」。 */
export function pendingWhat(p: PendingFlash, narrow = false): string {
  if (p.slot !== null) return p.slot === 0 ? "重閃調整欄" : `重閃第 ${p.slot} 次`;
  return `第 ${p.nth} 次${narrow ? "" : "閃現"}${p.major ? "（大變化）" : ""}`;
}

/** 金底標籤「已扣 1 點」。 */
export function paidTag(p: PendingFlash): string {
  return `已扣 ${p.cost} 點`;
}

// ---- 選項卡 ------------------------------------------------------------------------------

/** 這一題有沒有轉型選項（上固定區那句帶「轉型除外」）。 */
export function hasTransform(options: readonly FlashOption[]): boolean {
  return options.some((o) => o.transform);
}

/** 下固定區的一句話：伺服器的 `say_zh`（沒有退回 `summary_zh`）；轉型卡句末接 `FLASH_TRANSFORM_FOOT_ZH`（前句沒有句號時補一個）。 */
export function sayText(o: FlashOption): string {
  const say = o.say_zh || o.summary_zh;
  if (!o.transform) return say;
  const lead = say === "" || /[。！？]$/u.test(say) ? say : `${say}。`;
  return `${lead}${FLASH_TRANSFORM_FOOT_ZH}`;
}

/** 卡的內容（不看 `id`：每個選項的技能 id 都不同）一樣嗎。欄位照鍵名排序比，不依賴鍵的順序。 */
function sameCard(a: SkillCard, b: SkillCard): boolean {
  const norm = (c: SkillCard) => {
    const { id: _id, ...rest } = c;
    return JSON.stringify(rest, (_k, v: unknown) => (v !== null && typeof v === "object" && !Array.isArray(v) ? Object.fromEntries(Object.entries(v).sort(([x], [y]) => (x < y ? -1 : x > y ? 1 : 0))) : v));
  };
  return norm(a) === norm(b);
}

/** 重閃的這個選項整招和現在一樣（前 → 後一列都沒有、名稱不變、卡的內容也和現在的卡相同）：卡裡放「和現在一樣」那一行。
 * 只在重閃（`slot` 不為空；基準是現在的卡）；新的閃現照舊（玩法 PM 4.1.2 第 4 條只寫重閃）。`now` 是畫面上現在的卡。
 * 本機模型寫了一句話描述（`note_zh`）的卡不算：卡裡已經有字，不再加這行。 */
export function sameAsNow(p: PendingFlash, o: FlashOption, now: SkillCard | undefined): boolean {
  if (p.slot === null || (o.changes ?? []).length > 0 || noteOf(o) !== null) return false;
  // 找不到現在的卡就不下「一樣」的結論（寧可不寫，也不寫錯）
  return now !== undefined && renamedTo(o, now.name_zh) === null && sameCard(o.card, now);
}

/** 白話大標；還沒填的模板退回 `summary_zh`（8.2）。 */
export function headlineOf(o: FlashOption): string {
  const h = o.headline_zh ?? null;
  return h === null || h === "" ? o.summary_zh : h;
}

// ---- LLM 的名稱與描述（LF-3） ------------------------------------------------------------

/** 改名那一列的欄位名（「名稱 點燃斬 → 竹影焚心」）。 */
export const FLASH_NAME_ZH = "名稱";
/** 名稱來自本機模型時，新名稱後面的小標記（沿用候選卡的 LLM 標記字 `LLM_SOURCE_LABEL`，玩法 PM 2026-10-29 定案）。 */
export const FLASH_LLM_NAME_ZH = LLM_SOURCE_LABEL;
/** 小標記的說明卡（玩法 PM 2026-11-13 定案，FL-1g 換字）。 */
export const FLASH_LLM_NAME_HINT = "源晶推演：這個名字是源晶照你這一路的戰鬥推演出來的，只是名字；效果和數值都照規則定，不會因為名字改變。";

/** 選了這個會改名時的新名稱（大變化、轉型）；名稱不變（小變化）為 `null`。`current` 是畫面上的原名。 */
export function renamedTo(o: FlashOption, current: string): string | null {
  const name = o.card.name_zh;
  return name === "" || name === current ? null : name;
}

/** 新名稱是本機模型取的（伺服器 `name_source`）。 */
export function llmNamed(o: FlashOption): boolean {
  return o.name_source === "llm";
}

/** 本機模型寫的一句話描述；沒有為 `null`（不佔位）。 */
export function noteOf(o: FlashOption): string | null {
  const note = o.note_zh ?? null;
  return note === null || note === "" ? null : note;
}

/** 「後」的四種樣式（第 3 節）；拿掉的效果（`after` 是 null）照「變弱」（第 12 節決定 5）。
 * 代價欄位：伺服器只在變貴時給 `cost`，變便宜給 `better`（FL-1g，FL-1b 驗收必修 1），這裡照方向畫。 */
export type NowStyle = "up" | "cost" | "down" | "new";

export function nowStyle(c: StatChange): NowStyle {
  if (c.after === null) return c.direction === "cost" ? "up" : "down";
  switch (c.direction) {
    case "cost":
      return "cost";
    case "worse":
      return "down";
    case "new":
      return c.before === null ? "new" : "up";
    default:
      return "up";
  }
}

/** 代價整項不用付了（轉型後不花 AP、耐力…）：「後」寫「不用花」、照變好（樣張轉型那張「AP 2 → 不用花」）。 */
export const FLASH_NO_COST_ZH = "不用花";

/** 「後」的字：伺服器的 `after_zh`；拿掉的效果「沒有」、拿掉的代價「不用花」。 */
export function nowText(c: StatChange): string {
  if (c.after !== null) return c.after_zh ?? c.after;
  return c.direction === "cost" ? FLASH_NO_COST_ZH : FLASH_NONE_ZH;
}

// ---- 卸下選單（8.3、9.1 #28） ------------------------------------------------------------

/** 轉型後佔的欄位 → 選單上的欄位名：被動、反應填「被動欄」，召喚、陷阱（主動）填「主動欄」。姿態欄不出選單。 */
export function unequipSlotZh(slot: string | null | undefined): string {
  return slot === "active" ? "主動欄" : "被動欄";
}

export function unequipPrompt(o: FlashOption): string {
  return `${unequipSlotZh(o.unequip_slot)}滿了，選一招卸下`;
}

/** 姿態欄只有 1 格：自動換下原姿態，不出選單（8.3）。 */
export function autoUnequip(o: FlashOption): string | null {
  return o.unequip_slot === "stance" && o.unequip_candidates.length > 0 ? (o.unequip_candidates[0] ?? null) : null;
}

/** 要不要畫卸下選單。 */
export function showsUnequipMenu(o: FlashOption | undefined): boolean {
  return o !== undefined && o.unequip_candidates.length > 0 && autoUnequip(o) === null;
}

// ---- 術語標記 ----------------------------------------------------------------------------

/** 伺服器字串裡的一段：純文字、術語（`[[id|字]]`，點線底線＋說明卡）、圖示（`{{kw:<id>}}` 關鍵字小圓章）。 */
export type TermPiece = { kind: "text"; text: string } | { kind: "term"; id: string; label: string } | { kind: "icon"; cat: string; id: string };

const MARK_RE = /\[\[([^|\]]+)(?:\|([^\]]*))?\]\]|\{\{([a-z]+):([^}]+)\}\}/gu;

export function parseTerms(text: string): TermPiece[] {
  const out: TermPiece[] = [];
  let last = 0;
  for (const m of text.matchAll(MARK_RE)) {
    const at = m.index ?? 0;
    if (at > last) out.push({ kind: "text", text: text.slice(last, at) });
    if (m[1] !== undefined) out.push({ kind: "term", id: m[1], label: m[2] ?? m[1] });
    else out.push({ kind: "icon", cat: m[3] ?? "", id: m[4] ?? "" });
    last = at + m[0].length;
  }
  if (last < text.length) out.push({ kind: "text", text: text.slice(last) });
  return out;
}

/** 去掉標記只留字（測試、無障礙標籤用）。 */
export function plainTerms(text: string): string {
  return parseTerms(text)
    .map((p) => (p.kind === "text" ? p.text : p.kind === "term" ? p.label : ""))
    .join("");
}

/** 不可拆的詞（FL-1h，美術 11-13）：條件括號（`.fc-when`）與下固定區的一句話（`.fc-say-line`，FL-1i）可以在字間換行，
 * 但這些詞整個換到下一行，不會斷成「手持雙手／槍時才有」「重算強／度」（FL-1i，美術 RR-2 驗收 F-1）、
 * 「火焰傷／害」「轉／型」（FL-1j，美術 FL-1i 複驗可修 1、2）、「回／合」「點／燃」（FL-1j 待決 2 裁定；「本／回合」可以）。
 * 數字和單位另由 `numberUnitRuns`、「」括起來的名字另由 `quotedSpans` 通用處理，不列在這裡。 */
export const FLASH_NO_BREAK_WORDS: readonly string[] = ["雙手槍", "強度", "傷害", "轉型", "回合", "點燃"];

/** 數字（含小數、骰子「1d4」、正負號、百分比）。 */
const NUM_UNIT_RE = /[+\-−]?\d+(?:\.\d+)?(?:d\d+)?[%‰]?/gu;
/** 數字後面的單位：中文字或英文字母（「回合」「格」「成」「AP」）。 */
const UNIT_HEAD_RE = /^[\p{Script=Han}A-Za-z]+/u;
/** 單位最多黏幾個字（太長的不黏，免得整段不能斷行）。 */
const UNIT_MAX = 2;

/**
 * 數字後面的單位：英文字母整串（「AP」）；中文取前 `UNIT_MAX` 個字（「回合」「格」「倍」）。
 * 不用 `Intl.Segmenter`：實測 ICU 把「回合，」切成「回／合」，各瀏覽器的詞典也不同；多黏一個字（「5 格外」）只少一個斷點，無害。
 */
export function unitAfterNumber(after: string): string {
  const run = UNIT_HEAD_RE.exec(after)?.[0] ?? "";
  if (run === "") return "";
  if (/^[A-Za-z]/u.test(run)) return /^[A-Za-z]+/u.exec(run)?.[0] ?? "";
  return [...(/^\p{Script=Han}+/u.exec(run)?.[0] ?? "")].slice(0, UNIT_MAX).join("");
}

/**
 * 「」括起來的名字最多幾個字（不含括號）時整段連同括號不斷行（FL-1j 待決 2 裁定，美術 `docs/art/FL-1b驗收.md` 末節：
 * 「雷電」「被標記」這類讀起來會誤會的通用規則，不逐字列舉）。超過照常可斷。
 */
export const QUOTED_NAME_MAX = 6;
const QUOTED_RE = /「([^「」\n]*)」/gu;

/** 一段不斷行的範圍 `[from, to)`（字串索引）。 */
type Span = readonly [number, number];
type Run = { text: string; keep: boolean };

/** 「」括起來、內容 1～`QUOTED_NAME_MAX` 字的名字（含括號）。 */
function quotedSpans(text: string): Span[] {
  const out: Span[] = [];
  for (const m of text.matchAll(QUOTED_RE)) {
    const n = [...(m[1] ?? "")].length;
    if (n === 0 || n > QUOTED_NAME_MAX) continue;
    const from = m.index ?? 0;
    out.push([from, from + m[0].length]);
  }
  return out;
}

/** `i` 落在某個不可拆詞的中間（不含頭尾）。 */
const insideWord = (words: readonly Span[], i: number): Span | undefined => words.find(([a, b]) => a < i && i < b);

/**
 * 數字＋單位（`numberUnitRuns` 的範圍）。`words`（不可拆詞的範圍）：前面黏的那個字、後面的單位不切進詞的中間——
 * 「第 3 格轉型」的單位只到「格」（不黏成「格轉」）、「強度 +1」不從「度」黏起，和 FL-1j 先切詞的結果一樣。
 */
function numberUnitSpans(text: string, words: readonly Span[] = []): Span[] {
  const out: Span[] = [];
  let at = 0;
  for (const m of text.matchAll(NUM_UNIT_RE)) {
    const start = m.index ?? 0;
    if (start < at) continue;
    // 英文字或數字中間的數字（「2d6」的「6」已含在前一個比對裡；「AP2」這類）不拆
    if (start > 0 && /[A-Za-z0-9.]/u.test(text[start - 1] ?? "")) continue;
    const end = start + m[0].length;
    const gap = /^ ?/u.exec(text.slice(end))?.[0] ?? "";
    const unit = unitAfterNumber(text.slice(end + gap.length));
    const lead = /[\p{Script=Han}] ?$/u.exec(text.slice(at, start))?.[0] ?? "";
    let from = start - lead.length;
    let to = unit === "" ? end : end + gap.length + unit.length;
    if (insideWord(words, from) !== undefined) from = start;
    const cut = insideWord(words, to);
    if (cut !== undefined) to = cut[0] > end + gap.length ? cut[0] : end;
    if (from === start && to === end) continue;
    out.push([from, to]);
    at = to;
  }
  return out;
}

/** 不可拆詞（由左往右、同一處取最長的，不重疊）。 */
function wordSpans(text: string, words: readonly string[]): Span[] {
  const out: Span[] = [];
  let from = 0;
  for (;;) {
    let at = -1;
    let word = "";
    for (const w of words) {
      const i = w === "" ? -1 : text.indexOf(w, from);
      if (i >= 0 && (at < 0 || i < at || (i === at && w.length > word.length))) {
        at = i;
        word = w;
      }
    }
    if (at < 0) return out;
    out.push([at, at + word.length]);
    from = at + word.length;
  }
}

/** 範圍照起點排序，**重疊**的併成一段（只是相鄰的照樣分開，兩段之間仍可斷行）；切成段。 */
function runsOf(text: string, spans: readonly Span[]): Run[] {
  const sorted = [...spans].sort((a, b) => a[0] - b[0] || b[1] - a[1]);
  const merged: [number, number][] = [];
  for (const [a, b] of sorted) {
    const last = merged[merged.length - 1];
    if (last !== undefined && a < last[1]) last[1] = Math.max(last[1], b);
    else merged.push([a, b]);
  }
  const out: Run[] = [];
  let at = 0;
  for (const [a, b] of merged) {
    if (a > at) out.push({ text: text.slice(at, a), keep: false });
    out.push({ text: text.slice(a, b), keep: true });
    at = b;
  }
  if (at < text.length) out.push({ text: text.slice(at), keep: false });
  return out;
}

/**
 * 數字和單位黏成一段（FL-1j，美術 FL-1i 複驗可修 1：「燃燒少 1 回合」不斷成「少 1 ／回合」）：通用規則，不逐字列舉——
 * 數字前面緊貼的一個中文字（「少」「第」「等」，可隔一個空白）＋數字＋（空白）＋後面的單位（`unitAfterNumber`）包成 `keep`。
 * 數字後面沒有單位、前面也沒有中文字時不包。
 */
export function numberUnitRuns(text: string): Run[] {
  return runsOf(text, numberUnitSpans(text));
}

/**
 * 純文字切段：`keep` 為 true 的那段畫成不斷行。三種規則的範圍取聯集（重疊的併成一段）：
 * 「」括起來 ≤ 6 字的名字（FL-1j 待決 2）、不可拆詞（`FLASH_NO_BREAK_WORDS`）、數字＋單位（`numberUnitSpans`）。
 * 聯集而不是先切詞再找數字：「少 1 回合」的「回合」也是不可拆詞，先切詞會把「少 1」和「回合」切成相鄰兩段、中間又能斷。
 * 沒有時整段一個 `keep: false`。
 */
export function noBreakRuns(text: string, words: readonly string[] = FLASH_NO_BREAK_WORDS): Run[] {
  const ws = wordSpans(text, words);
  return runsOf(text, [...quotedSpans(text), ...ws, ...numberUnitSpans(text, ws)]);
}

/** 「後」結尾的條件括號（「（目標這回合被撞過才有）」）拆出來，畫成次要字（樣張 `.fc-when`）。 */
export function splitWhen(text: string): { main: string; when: string | null } {
  if (!text.endsWith("）")) return { main: text, when: null };
  const at = text.indexOf("（");
  if (at <= 0) return { main: text, when: null };
  return { main: text.slice(0, at), when: text.slice(at) };
}

// ---- 鍵盤：方向鍵在選項間移動（4：鍵盤可聚焦，方向鍵切換由開發定） ----------------------

export function stepPick(order: readonly number[], current: number | null, key: string): number | null {
  if (order.length === 0) return null;
  const at = current === null ? -1 : order.indexOf(current);
  if (key === "ArrowDown" || key === "ArrowRight") return order[(at + 1 + order.length) % order.length] ?? null;
  if (key === "ArrowUp" || key === "ArrowLeft") return order[at <= 0 ? order.length - 1 : at - 1] ?? null;
  if (key === "Home") return order[0] ?? null;
  if (key === "End") return order[order.length - 1] ?? null;
  return current;
}

// ---- 下固定區的最小高度（5 第 1 條：點哪個都不跳框） ------------------------------------

/** 有沒有任何一個選項選了會出卸下選單（下固定區要預留那一列的高度）。 */
export function anyUnequipMenu(options: readonly FlashOption[]): boolean {
  return options.some((o) => showsUnequipMenu(o));
}
