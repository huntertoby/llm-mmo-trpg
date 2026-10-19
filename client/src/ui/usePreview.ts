// 預覽：滑過合法目標時呼叫 /preview（防抖，避免每次滑動都送；同一狀態下的結果快取）。
import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { Action, PreviewOut } from "../api/types";

export const PREVIEW_DEBOUNCE_MS = 120;

/** `stateKey` 改變（戰鬥狀態變了）時清掉快取。`action` 為 `null` 時不預覽。 */
export function usePreview(battleId: string, stateKey: unknown, action: Action | null): PreviewOut | null {
  const [result, setResult] = useState<{ key: string; preview: PreviewOut } | null>(null);
  const cache = useRef(new Map<string, PreviewOut>());
  const lastState = useRef<unknown>(stateKey);
  if (lastState.current !== stateKey) {
    lastState.current = stateKey;
    cache.current.clear();
  }
  const key = action === null ? "" : JSON.stringify(action);

  useEffect(() => {
    if (action === null) return undefined;
    const cached = cache.current.get(key);
    if (cached !== undefined) {
      setResult({ key, preview: cached });
      return undefined;
    }
    let cancelled = false;
    const timer = window.setTimeout(() => {
      api
        .preview(battleId, action)
        .then((p) => {
          cache.current.set(key, p);
          if (!cancelled) setResult({ key, preview: p });
        })
        .catch(() => {
          // 預覽失敗（例如狀態剛變）：不顯示，不打擾玩家。
        });
    }, PREVIEW_DEBOUNCE_MS);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
    // `action` 由 `key` 決定，不必列入相依。
  }, [battleId, key, stateKey]);

  return result !== null && result.key === key ? result.preview : null;
}
