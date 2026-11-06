// 郵寄面板（Phase 6T-1b；docs/art/郵寄外觀.md 第 3 節、樣張 sample/mail.html）的純函式。
// 規則全在伺服器（6T-1a `/mail`、`/mail/quote`）：能不能寄、稅與實收、綁定原因、背包放不下都照伺服器給的；
// 這裡只整理附件草稿、分頁標籤與按鈕狀態。
import type { MailLetter, MailQuote, MailSend, MailView, WorldBagItem } from "../api/types";

export type MailTab = "send" | "inbox" | "returned";

/** 分頁標籤：「寄東西／收件匣 N／退件・過期 N」（0 封時不寫數字）。 */
export function mailTabs(mail: Pick<MailView, "inbox" | "returned">): { id: MailTab; label: string }[] {
  const n = (k: number) => (k > 0 ? ` ${k}` : "");
  return [
    { id: "send", label: "寄東西" },
    { id: "inbox", label: `收件匣${n(mail.inbox.length)}` },
    { id: "returned", label: `退件・過期${n(mail.returned.length)}` },
  ];
}

/** 打開面板時的分頁：有信先看收件匣、再來退件；都沒有就寄東西。 */
export function firstTab(mail: Pick<MailView, "inbox" | "returned">): MailTab {
  if (mail.inbox.length > 0) return "inbox";
  if (mail.returned.length > 0) return "returned";
  return "send";
}

/** 寄東西的草稿：物品 ID → 個數（材料、消耗品）＋裝備 ID（依點選順序）。 */
export interface MailDraft {
  to: string | null;
  items: Readonly<Record<string, number>>;
  gear: readonly string[];
  gold: number;
  note: string;
}

export const EMPTY_DRAFT: MailDraft = { to: null, items: {}, gear: [], gold: 0, note: "" };

/** 已經佔了幾格附件（一種物品或一件裝備算一格）。 */
export function slotsUsed(d: Pick<MailDraft, "items" | "gear">): number {
  return Object.keys(d.items).length + d.gear.length;
}

/** 背包縮圖列的一格能不能點進附件，與灰掉的原因（伺服器的 `tradable`／`bound_zh`）。 */
export function sendableState(row: WorldBagItem): { ok: boolean; reason: string | null } {
  if (row.tradable === true) return { ok: true, reason: null };
  return { ok: false, reason: row.bound_zh ?? "不能寄" };
}

/**
 * 點背包縮圖列的一格：物品加 1 個（不超過持有數）、裝備加一次；附件格滿了（`max`）且是新的一格時不加。
 * 不能寄的（`tradable` 假）原樣不動。
 */
export function addToDraft(d: MailDraft, row: WorldBagItem, max: number): MailDraft {
  if (!sendableState(row).ok) return d;
  if (row.gear === true) {
    if (d.gear.includes(row.item) || slotsUsed(d) >= max) return d;
    return { ...d, gear: [...d.gear, row.item] };
  }
  const have = d.items[row.item] ?? 0;
  if (have === 0 && slotsUsed(d) >= max) return d;
  if (have >= row.count) return d;
  return { ...d, items: { ...d.items, [row.item]: have + 1 } };
}

/**
 * 附件格裡可堆疊物品的個數（6T-1c，玩法 PM 3.5 acfc999f：材料、消耗品寄件時可以填數量；裝備維持一次 1 件）：
 * 夾在 1～背包裡的數量（`row.count`）之間；不是數字的字照 1。不在附件裡、裝備、不能寄的原樣不動。
 */
export function setDraftCount(d: MailDraft, row: WorldBagItem, n: number): MailDraft {
  if (row.gear === true || !sendableState(row).ok || d.items[row.item] === undefined) return d;
  const want = Number.isFinite(n) ? Math.floor(n) : 1;
  const count = Math.min(Math.max(1, want), Math.max(1, row.count));
  return { ...d, items: { ...d.items, [row.item]: count } };
}

/** 數量框的字 → 數字（空的或不是數字＝`NaN`，交給 `setDraftCount` 照 1）。 */
export function countValue(text: string): number {
  const digits = text.replace(/[^\d]/g, "");
  return digits === "" ? Number.NaN : Number.parseInt(digits, 10);
}

/**
 * 郵差在這個分頁說的話（6T-1c）：剛寄出／領了退件時的那句（`action`）優先；等級不到照伺服器的 `line_zh`；
 * 其他照 `tab_lines`（伺服器已把沒填的換成打開面板那句）；收件匣沒有信時用 `inbox_empty`。
 */
export function tabSay(mail: Pick<MailView, "line_zh" | "level_ok" | "tab_lines" | "inbox">, tab: MailTab, action: string | null): string | null {
  if (action !== null) return action;
  const lines = mail.tab_lines;
  if (!mail.level_ok || lines == null) return mail.line_zh ?? null;
  if (tab === "send") return lines.send;
  if (tab === "inbox") return mail.inbox.length > 0 ? lines.inbox : lines.inbox_empty;
  return lines.returned;
}

/** 從附件拿掉一格（整格拿掉）。 */
export function removeFromDraft(d: MailDraft, id: string): MailDraft {
  if (d.gear.includes(id)) return { ...d, gear: d.gear.filter((g) => g !== id) };
  const items = { ...d.items };
  delete items[id];
  return { ...d, items };
}

/** 草稿 → 寄件請求（沒選收件人為 `null`；個數 0 的不送）。 */
export function sendBody(d: MailDraft): MailSend | null {
  if (d.to === null) return null;
  const items = Object.fromEntries(Object.entries(d.items).filter(([, n]) => n > 0));
  return { kind: "mail_send", to: d.to, items, gear: [...d.gear], gold: Math.max(0, Math.floor(d.gold)), note: d.note };
}

/** 金幣輸入框的字 → 數字（不是數字、負數＝0）。 */
export function goldValue(text: string): number {
  const n = Number.parseInt(text.replace(/[^\d]/g, ""), 10);
  return Number.isFinite(n) && n > 0 ? n : 0;
}

/** 「寄出」能不能按，與不能按的原因（第一條；伺服器的檢查全部列在下面）。 */
export function sendState(d: MailDraft, quote: MailQuote | null, here: boolean, hereProblem: string | null): { ok: boolean; reason: string | null } {
  if (!here) return { ok: false, reason: hereProblem ?? "要在城鎮的郵差這裡" };
  if (d.to === null) return { ok: false, reason: "先選收件人" };
  if (quote === null) return { ok: false, reason: "檢查中…" };
  if (!quote.ok) return { ok: false, reason: quote.problems[0]?.text_zh ?? "還不能寄" };
  return { ok: true, reason: null };
}

/** 信上的附件一行（「焦鐵 ×3、熔岩核 ×1、紫電長弓（4 級）」）。 */
export function letterThings(letter: Pick<MailLetter, "items" | "gear">): string {
  return [...letter.items.map((i) => `${i.name_zh} ×${i.count}`), ...letter.gear.map((g) => g.name_zh)].join("、");
}

/** 一封信的第二行：「寄自 灰燼荒原・餘燼集・剩 2 天」（退件不寫天數）。 */
export function letterSub(letter: Pick<MailLetter, "from_zh" | "days_left" | "status_zh">, returned: boolean): string {
  if (returned) return `${letter.status_zh}・寄自 ${letter.from_zh}`;
  return `寄自 ${letter.from_zh}・剩 ${letter.days_left} 天`;
}
