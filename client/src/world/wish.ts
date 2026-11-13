// 許願池面板（WP-3；docs/phases/PhaseWP計畫.md 第 5 節）的純函式與前端自寫的字。
// 資料全讀 `WorldView.wish`（WP-2）：費用、退款、任務幣、本週剩幾次、能不能許與原因、LLM 開不開、選單、字數上限、守池人。
// 規則一律由伺服器裁決（能不能許看 `available`／`blocked_zh`），前端只決定「送出鈕現在按不按得下去」（有沒有寫願望、挑了幾個關鍵字）。
// 這裡的字都是暫定字（玩法 PM 定稿後只換字），完整清單在 `docs/phases/PhaseWP-3報告.md`。
import type { StatChange, WorldAction, WorldPendingOffer, WorldView } from "../api/types";

export type WishData = NonNullable<WorldView["wish"]>;

/** 兩種許法＝兩個分頁：說出願望（LLM 開著才有）、從選單挑關鍵字。 */
export type WishMode = "text" | "menu";

export const WISH_ZH = {
  tabText: "說出願望",
  tabTextShort: "願望",
  tabMenu: "從選單挑",
  tabMenuShort: "選單",
  coins: "任務幣",
  left: "本週還能許",
  textLead: "用一句話說出想要的力量；池子會從裡面聽出 1～2 個關鍵字，給你三招挑一招。",
  textPlaceholder: "例：想把敵人凍住，再一錘敲碎",
  menuLead: "挑 1～2 個關鍵字：三招都會帶第 1 個，第 2 個會盡量出現在其中一招。",
  submit: "許願",
  needText: "先寫下你的願望",
  needKeyword: "先挑 1 個關鍵字",
  rowCoins: "任務幣",
  rowLeft: "本週次數",
  rowGain: "得到",
  gain: "技能三選一",
  notEnough: "不夠",
  noneLeft: "用完了",
  timeout: "池子這次沒來得及回應（等了 10 秒），改從選單挑關鍵字吧（沒有扣任務幣）。",
  waitText: "池水泛起漣漪，正在聽你的願望……",
  waitNote: "最多等 10 秒；來不及就改從選單挑關鍵字（不扣任務幣）。",
  pickNth: (n: number) => `第 ${n} 個`,
  /** 下固定區「名字：說明」中間的冒號（WP-3b）。 */
  pickedSep: "：",
  leftTimes: (n: number) => `剩 ${n} 次`,
  refundNote: (refund: number) => `三招都不拿也算一次，退回 ${refund} 任務幣。`,
  skip: "都不拿",
  skipRefund: (refund: number) => `都不拿（退回 ${refund} 任務幣）`,
} as const;

/** 有哪些分頁：LLM 關著（`llm` false）只有選單（規格第 5 節第 1 點）。 */
export function wishModes(w: Pick<WishData, "llm">): WishMode[] {
  return w.llm ? ["text", "menu"] : ["menu"];
}

/** 願望文字整理：去頭尾空白（伺服器組鍵前也 `strip`）。 */
export function wishText(raw: string): string {
  return raw.trim();
}

/** 選單點一個關鍵字：已選＝拿掉（後面的往前補）；沒選而且還沒滿＝加在最後；滿了＝不變。順序有意義（第 1 個三招都帶）。 */
export function toggleKeyword(picked: readonly string[], id: string, max: number): string[] {
  if (picked.includes(id)) return picked.filter((k) => k !== id);
  if (picked.length >= max) return [...picked];
  return [...picked, id];
}

/** 下固定區要寫說明的那一個（WP-3b 乙案）：最後挑中的那一個（拿掉後退回前一個）；沒挑＝null。 */
export function pickedFocus<K extends { id: string }>(menu: readonly K[], picked: readonly string[]): K | null {
  for (let i = picked.length - 1; i >= 0; i--) {
    const k = menu.find((m) => m.id === picked[i]);
    if (k !== undefined) return k;
  }
  return null;
}

/** 送出鈕現在為什麼按不下去（`null`＝可以按）。伺服器說不能許時回它的原因（畫面第一行另有「現在不能用」）。 */
export function wishSubmitBlock(w: Pick<WishData, "available" | "blocked_zh">, mode: WishMode, text: string, picked: readonly string[]): string | null {
  if (!w.available) return w.blocked_zh ?? "";
  // 文字超過上限輸入框（maxLength）就打不進去；真的超過讓伺服器回原因
  if (mode === "text") return wishText(text) === "" ? WISH_ZH.needText : null;
  return picked.length === 0 ? WISH_ZH.needKeyword : null;
}

/** 要送的世界動作（TS 型別的 `keywords` 必填：文字許願帶 `[]`，WP-2 待決 5）。 */
export function wishAction(mode: WishMode, text: string, picked: readonly string[]): WorldAction {
  return mode === "text" ? { kind: "wish", text: wishText(text), keywords: [] } : { kind: "wish", keywords: [...picked] };
}

function row(field: string, name: string, before: string | null, after: string, direction: StatChange["direction"]): StatChange {
  return { field, label_zh: name, name_zh: name, before, before_zh: before, after, after_zh: after, direction };
}

/**
 * 下固定區的「前 → 後」（照 FL-1b 的四種記號，`run/FlashChoiceParts.DiffRows`）：任務幣與本週次數是代價、得到的三選一是新。
 * 付不起、沒次數時「後」寫「不夠」「沒有了」（照代價畫，原因在第一行）。
 */
export function wishDiffs(w: Pick<WishData, "coins" | "cost" | "left">): StatChange[] {
  const coinsAfter = w.coins >= w.cost ? String(w.coins - w.cost) : WISH_ZH.notEnough;
  const leftAfter = w.left > 0 ? WISH_ZH.leftTimes(w.left - 1) : WISH_ZH.noneLeft;
  return [
    row("quest_coins", WISH_ZH.rowCoins, String(w.coins), coinsAfter, "cost"),
    row("wish_left", WISH_ZH.rowLeft, WISH_ZH.leftTimes(w.left), leftAfter, "cost"),
    row("offer", WISH_ZH.rowGain, null, WISH_ZH.gain, "new"),
  ];
}

// ---------------- 三選一畫面（`QuestLog.WorldOfferPending`）----------------

/** 三選一的標題：許願池＝伺服器的名稱（「許願池」）；其他照舊。 */
export function offerTitle(p: Pick<WorldPendingOffer, "source" | "quest_name_zh">): string {
  return p.source === "wish" ? p.quest_name_zh : "任務給的技能三選一";
}

/** 標題下那一行：許願池只寫伺服器的那一句（不再接「許願池：」）；其他照舊「任務：步驟」。 */
export function offerSubtitle(p: Pick<WorldPendingOffer, "source" | "quest_name_zh" | "step_zh">): string {
  return p.source === "wish" ? p.step_zh : `${p.quest_name_zh}：${p.step_zh}`;
}

/** 不拿鈕（TXT-2 用詞統一成「都不拿」，07 7.6「可以都不拿」）：有退款＝「都不拿（退回 N 任務幣）」，其他「都不拿」。 */
export function offerSkipLabel(p: Pick<WorldPendingOffer, "source" | "refund">): string {
  return p.source === "wish" && p.refund > 0 ? WISH_ZH.skipRefund(p.refund) : WISH_ZH.skip;
}
