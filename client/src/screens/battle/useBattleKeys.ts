// 戰鬥畫面的鍵盤快捷鍵（由 BattleScreen 抽出，Phase 3T-7）。
// Esc：灌注關鍵字視窗開著 ＝ 取消施放（還沒送出，不付代價）；複製／複合技能暫停中 ＝ 放棄施放（不付任何代價）；
// 其餘 ＝ 取消選取。（格子資訊卡的 Esc 由 `ui/hoverCard.ts` 的控制器自己處理。）

import { useEffect } from "react";
import type { Action } from "../../api/types";

export function useBattleKeys(
  infusionPicking: boolean,
  closeInfusion: () => void,
  copying: boolean,
  decideCopy: (pick: Action | null) => void,
  cancel: () => void,
): void {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      if (infusionPicking) {
        closeInfusion();
        return;
      }
      if (copying) decideCopy(null);
      else cancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [cancel, closeInfusion, copying, decideCopy, infusionPicking]);
}
