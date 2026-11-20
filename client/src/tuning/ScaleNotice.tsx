// 數值工坊的一次性換算提示（X10-3b，05 5.4.1）：數值整體 ×10 之後，第一次進工坊時說一聲。
// 關掉後記在瀏覽器（localStorage）；讀寫都包 try/catch，私密視窗、封鎖儲存時照樣顯示、照樣能關（只是下次還會出現）。
import { useState } from "react";

export const SCALE_NOTICE_KEY = "trpg.tuning.x10Notice";
export const SCALE_NOTICE_ZH = "數值已整體放大 10 倍（2026-11-20）；舊的 5 現在是 50。";

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

function defaultStorage(): StorageLike | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

/** 提示是否已經關掉過。 */
export function scaleNoticeDismissed(storage: StorageLike | null = defaultStorage()): boolean {
  try {
    return storage?.getItem(SCALE_NOTICE_KEY) === "1";
  } catch {
    return false;
  }
}

/** 記下「已經關掉」。 */
export function dismissScaleNotice(storage: StorageLike | null = defaultStorage()): void {
  try {
    storage?.setItem(SCALE_NOTICE_KEY, "1");
  } catch {
    // 存不了就算了：這次照樣關掉，下次再出現
  }
}

export function ScaleNotice({ storage }: { storage?: StorageLike | null }) {
  const store = storage === undefined ? defaultStorage() : storage;
  const [open, setOpen] = useState(() => !scaleNoticeDismissed(store));
  if (!open) return null;
  return (
    <div className="tn-info-line" role="status" data-testid="tuning-scale-notice">
      {SCALE_NOTICE_ZH}
      <button
        type="button"
        className="small-button"
        onClick={() => {
          dismissScaleNotice(store);
          setOpen(false);
        }}
      >
        知道了
      </button>
    </div>
  );
}
