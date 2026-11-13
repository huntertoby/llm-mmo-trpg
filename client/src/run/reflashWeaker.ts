// RR-2（#160，06 6.34.3「強度下限」例外）：被強度下限卡住的重閃格改出較弱的候選，扣點前先提醒。
// RR-2b：兩層確認合成一層（入口提醒＋選類別面板最上面再寫一次，不另跳確認框）；「比原本弱」小標撤掉。
// 字全由伺服器送（`ReflashSlotOut.weaker_zh`／`weaker_pick_zh`、`PendingFlashOut.weaker_foot_zh`）；這裡只取欄位，不自己推規則。
import type { PendingFlash, SkillFlash } from "../api/types";
import { FLASH_MUST_PICK_ZH } from "./flashChoice";

export interface WeakerSlot {
  /** 入口與選類別面板的提醒字「這一格原本的變化特別強，重閃後這部分會變弱」。 */
  warn: string;
  /** 選類別面板提醒字後面那句「整招不會比現在弱；扣點後一定要選一個。」。 */
  pick: string;
}

/** 這一格重閃會不會讓被換掉的部分變弱（伺服器 `weaker`）；不會時 `null`。 */
export function weakerSlot(f: SkillFlash | undefined, slot: number): WeakerSlot | null {
  const s = f?.reflash_slots?.find((x) => x.slot === slot);
  if (s === undefined || s.weaker !== true || s.available === false) return null;
  return { warn: s.weaker_zh ?? "", pick: s.weaker_pick_zh ?? "" };
}

/** 選類別面板最上面那一行：提醒字＋「整招不會比現在弱；扣點後一定要選一個。」（提醒字沒有句號時補一個）。 */
export function weakerLeadText(w: WeakerSlot): string {
  const warn = w.warn === "" || /[。！？]$/.test(w.warn) ? w.warn : `${w.warn}。`;
  return `${warn}${w.pick}`;
}

/** 上固定區那句（不含句尾句號，同 `FLASH_MUST_PICK_ZH`）：較弱的重閃把「選哪個這招整體都會強一點…」換成伺服器的
 * `weaker_foot_zh`，「一定要選一個。」照留。 */
export function mustPickText(p: PendingFlash): string {
  const foot = p.weaker_foot_zh;
  if (foot === null || foot === undefined || foot === "") return FLASH_MUST_PICK_ZH;
  const lead = FLASH_MUST_PICK_ZH.slice(0, FLASH_MUST_PICK_ZH.indexOf("。") + 1);
  return `${lead}${foot.replace(/。$/, "")}`;
}
