// RR-2（#160，06 6.34.3「強度下限」例外）：被強度下限卡住的重閃格改出較弱的候選，扣點前先提醒。
// 字全由伺服器送（`ReflashSlotOut.weaker_zh`／`weaker_confirm_zh`、`PendingFlashOut.weaker_foot_zh`、
// `FlashOptionOut.weaker_tag_zh`）；這裡只取欄位，不自己推規則。
import type { PendingFlash, SkillFlash } from "../api/types";
import { FLASH_MUST_PICK_ZH } from "./flashChoice";

/** 確認框的兩個按鈕（06 6.34.3：「重閃」「先不要」）。 */
export const REFLASH_WEAKER_GO_ZH = "重閃";
export const REFLASH_WEAKER_BACK_ZH = "先不要";

export interface WeakerSlot {
  /** 入口的提醒字「這一格重閃可能比原本弱」。 */
  warn: string;
  /** 按下去、扣點前的確認句。 */
  confirm: string;
}

/** 這一格重閃會不會比原本弱（伺服器 `weaker`）；不會時 `null`。 */
export function weakerSlot(f: SkillFlash | undefined, slot: number): WeakerSlot | null {
  const s = f?.reflash_slots?.find((x) => x.slot === slot);
  if (s === undefined || s.weaker !== true || s.available === false) return null;
  return { warn: s.weaker_zh ?? "", confirm: s.weaker_confirm_zh ?? "" };
}

/** 上固定區那句（不含句尾句號，同 `FLASH_MUST_PICK_ZH`）：較弱的重閃把「選哪個這招整體都會強一點…」換成伺服器的
 * `weaker_foot_zh`，「一定要選一個。」照留。 */
export function mustPickText(p: PendingFlash): string {
  const foot = p.weaker_foot_zh;
  if (foot === null || foot === undefined || foot === "") return FLASH_MUST_PICK_ZH;
  const lead = FLASH_MUST_PICK_ZH.slice(0, FLASH_MUST_PICK_ZH.indexOf("。") + 1);
  return `${lead}${foot.replace(/。$/, "")}`;
}
