// 靈感閃現「選變體」畫面改版（FL-1b，docs/art/靈感閃現選擇-移植需求.md）的純函式與定稿字。
// 欄位名、單位、大標、一句話、說明卡全部由伺服器給（`FlashOptionOut.changes`、`headline_zh`、`say_zh`、`PendingFlashOut.terms`；
// 開發 PM 第 12 節決定 1：對照表在後端 `flash_changes.py`）；這裡只決定樣式與排法、解析術語標記。
import type { FlashOption, PendingFlash, StatChange } from "../api/types";
import { LLM_SOURCE_LABEL } from "./llmFlow";

// ---- 定稿字（9.1） ------------------------------------------------------------------------

/** 9.1 #19。 */
export const FLASH_PICK_TITLE_ZH = "靈感閃現";
export const FLASH_PICK_SUBTITLE_ZH = "選一個變化";
/** 9.1 #34（寬版上固定區；窄版收進 (i)）。 */
export const FLASH_MUST_PICK_ZH = "一定要選一個。選哪個這招整體都會強一點，標 ▼ 的是拿來換的";
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
