// 「隊伍與影子」面板的純函式（PNL-1a；docs/art/資訊面板-移植需求.md 3.3、4.1 #29～#33、#41、#42）：分頁記號、成員卡的種類。
import type { WorldMyShadow, WorldPartyView } from "../api/types";
import type { TabBadgeSpec } from "../ui/panelTabRules";

/** 面板標題（#41 新字）。 */
export const PARTY_PANEL_TITLE_ZH = "隊伍與影子";
/** 分頁名與短名（#29、#41）。 */
export const PARTY_TAB_ZH = { party: "隊伍", shadow: "我的影子", shadowShort: "影子" } as const;
/** 影子還沒存（#32；字不變，原本是「還沒存（在城鎮休息、換技能等整備時自動存）」一串）。 */
export const SHADOW_UNSAVED_ZH = "還沒存";
export const SHADOW_UNSAVED_NOTE_ZH = "在城鎮休息、換技能等整備時自動存";
/** 獨行（字不變）。 */
export const SOLO_ZH = "只帶主角（可以在城鎮雇傭兵或借影子）";
/** 劇情夥伴標籤（#31 新字）。 */
export const COMPANION_TAG_ZH = "劇情夥伴";

/** 隊伍分頁的細框數字（#29、#42）：「3／3」＝成員數／（隊友上限＋主角）。 */
export function partyCountBadge(party: Pick<WorldPartyView, "members" | "max_hired">): TabBadgeSpec {
  const text = `${party.members.length}／${party.max_hired + 1}`;
  return { kind: "p", value: text, hint: `${PARTY_TAB_ZH.party} ${text}（含主角）` };
}

/** 我的影子分頁：還沒存時掛琥珀三角（#42「還沒存」）；存了不掛（純資訊）。 */
export function shadowBadge(shadow: Pick<WorldMyShadow, "saved">): TabBadgeSpec | null {
  return shadow.saved ? null : { kind: "warn", hint: SHADOW_UNSAVED_ZH };
}

export type MemberKind = "hero" | "companion" | "mercenary" | "shadow" | "other";

/** 成員卡的種類：主角金框、劇情夥伴綠框（描框只表示狀態，3.1 第 3 條）。主角＝第一位、不是傭兵／影子／夥伴（同 `hud.ts` 的 `mateCards`）。 */
export function memberKind(m: WorldPartyView["members"][number], index: number): MemberKind {
  if (m.companion != null) return "companion";
  if (m.mercenary != null) return "mercenary";
  if (m.shadow != null) return "shadow";
  return index === 0 ? "hero" : "other";
}

/** 卡上的「打法 …」行（#30）：主角沒有（`ai_zh` 為 null）。 */
export const memberAiText = (m: WorldPartyView["members"][number]): string | null => m.ai_zh ?? null;

/** 劇情夥伴的 `note_zh`（「劇情夥伴：任務結束後離隊」）由綠底標籤＋`companion_zh` 帶到（#31），卡上不再寫；其他成員照舊寫。 */
export const memberNote = (m: WorldPartyView["members"][number]): string | null => (m.companion != null ? null : (m.note_zh ?? null));
