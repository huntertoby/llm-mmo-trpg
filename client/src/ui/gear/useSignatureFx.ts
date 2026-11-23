// 撿到時的一次性強調（E6-b2；美術移植需求第 1 節第 3 項）：同一件（物品 ID）這次開遊戲只播一次；減少動態時不播；不加音效。
// 決定播不播在第一次畫的時候（純讀取，StrictMode 呼叫兩次也一樣），掛上之後才記下「播過了」。
import { useEffect, useState } from "react";
import { fxPending, markFxShown } from "../../gear/signature";
import { reducedMotion } from "../motionPrefs";

export function useSignatureFx(id: string, enabled: boolean): boolean {
  const [play] = useState(() => enabled && fxPending(id) && !reducedMotion());
  useEffect(() => {
    if (enabled) markFxShown(id);
  }, [id, enabled]);
  return play;
}
