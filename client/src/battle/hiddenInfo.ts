// HID-1：隱蔽中的敵人只藏資訊（05 5.1.2，玩法決定 #144；使用者：「B 只藏資訊」）。
// 伺服器依陣營過濾：看不到資訊的單位 `hidden_info: true`，`hp`、`shield` 為 `null`，`statuses`、`stacks` 為空。
// 前端只負責把「？」畫出來（HUD、滑過資訊卡、單位卡、行動順序列）；位置、外觀、名稱照畫。
import type { UnitView } from "../api/types";

/** 看不到的數值寫成這個字。 */
export const UNKNOWN_MARK = "？";

/** 說明卡的一句（為什麼是「？」）。 */
export const HIDDEN_INFO_HINT = "隱蔽中：看不到 HP、護盾與狀態；被揭露、隱蔽解除或我方有人站在上下左右相鄰時才看得到。";

/** 伺服器沒給這個單位的 HP、護盾、狀態。 */
export function isHiddenInfo(u: Pick<UnitView, "hidden_info">): boolean {
  return u.hidden_info === true;
}

/** 還站著（沒倒下、HP 大於 0；看不到 HP 的隱蔽敵人算站著）。 */
export function standing(u: Pick<UnitView, "hp" | "downed">): boolean {
  return u.downed !== true && (u.hp === null || u.hp > 0);
}

/** HP 的字：看不到時「？」。 */
export function hpValueText(u: Pick<UnitView, "hp">): string {
  return u.hp === null ? UNKNOWN_MARK : String(u.hp);
}
