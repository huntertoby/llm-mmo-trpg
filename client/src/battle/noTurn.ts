// 「目標不會轉身」的字（BS-2，06 6.21.1 B、C6；資料由 BS-1 給：預覽 `no_turn`／`no_turn_reason`、事件 `attack_rolled.no_turn`）。
// 純函式：攻擊預覽、戰鬥紀錄行與它們的說明卡共用同一套字。
// - 隱蔽出手（`concealed`）：帶隱蔽時的近戰攻擊，任何武器、敵我都適用。
// - 無聲（`silent`，修正效果 `silent_strike`）：手持匕首類時，自己的近戰攻擊都不讓目標轉身。
// 和背刺一起時前面加「背刺・」（例「背刺・無聲（不會轉身）」）。
import type { PreviewOut } from "../api/types";
import type { UnitNames } from "./units";

export type NoTurnKind = "concealed" | "silent";

/** 原因 → 名稱（兩種各自的字；和戰鬥紀錄的「［隱蔽出手（不會轉身）］」同一套）。 */
export const NO_TURN_ZH: Readonly<Record<NoTurnKind, string>> = {
  concealed: "隱蔽出手",
  silent: "無聲",
};

/** 說明卡（滑過標籤時）：為什麼不會轉身、之後會怎樣。 */
export const NO_TURN_HINT_ZH: Readonly<Record<NoTurnKind, string>> = {
  concealed: "隱蔽出手：帶隱蔽時的近戰攻擊，目標不會轉身。出手後脫離隱蔽，要再來一次得重新隱匿。",
  silent: "無聲：手持匕首或雙匕首時，你的近戰攻擊（普攻、武器技、反應攻擊）不會讓目標轉身，可以留在背後連續背刺。目標在自己的回合行動時照常轉身。",
};

export function isNoTurnKind(v: unknown): v is NoTurnKind {
  return v === "concealed" || v === "silent";
}

/** 標籤字：「背刺・無聲（不會轉身）」「隱蔽出手（不會轉身）」。 */
export function noTurnLabel(kind: NoTurnKind, backstab: boolean): string {
  return `${backstab ? "背刺・" : ""}${NO_TURN_ZH[kind]}（不會轉身）`;
}

/** 預覽裡的一列：字、種類（說明卡用）。 */
export interface NoTurnRow {
  text: string;
  kind: NoTurnKind;
}

/** 預覽的「不會轉身」：每個目標一列「背刺・無聲（不會轉身）：盜賊」（依伺服器給的目標順序）。沒有時空陣列。 */
export function noTurnRows(p: PreviewOut, names: UnitNames): NoTurnRow[] {
  const kind = p.no_turn_reason;
  if (!isNoTurnKind(kind)) return [];
  const behind = new Set(p.backstab);
  return (p.no_turn ?? []).map((uid) => ({ text: `${noTurnLabel(kind, behind.has(uid))}：${names.label(uid)}`, kind }));
}

/** 伺服器 `notes` 裡 BS-1 的「…（不會轉身）：目標」句：前端改用 `noTurnRows` 畫（同一件事不寫兩次）。 */
export function isNoTurnNote(note: string): boolean {
  return /（不會轉身）：/.test(note);
}

/** 戰鬥紀錄命中判定行尾的「［背刺・無聲（不會轉身）］」：精簡文字拿掉它，改畫成標籤。 */
const NO_TURN_BRACKET = /［[^］]*（不會轉身）］/g;

export function stripNoTurnBracket(text: string): string {
  return text.replace(NO_TURN_BRACKET, "");
}
