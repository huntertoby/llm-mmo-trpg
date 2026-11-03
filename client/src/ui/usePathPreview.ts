// 選移動時的路徑預覽（Phase 6A-4c）：滑過格子時向伺服器要路徑預覽（節流 120ms、同一狀態下快取，見 `battle/pathFetch.ts`）。
import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { PathPreviewFetcher } from "../battle/pathFetch";
import type { PathPreview, PathQuery } from "../battle/pathPreview";

/** `stateKey` 改變（戰鬥狀態變了）時清掉快取。`query` 為 `null` 時不預覽。 */
export function usePathPreview(battleId: string, stateKey: unknown, query: PathQuery | null): PathPreview | null {
  const [result, setResult] = useState<{ key: string; preview: PathPreview } | null>(null);
  const fetcher = useRef<PathPreviewFetcher | null>(null);
  if (fetcher.current === null) {
    fetcher.current = new PathPreviewFetcher({
      fetch: (body) => api.pathPreview(battleId, body),
      onResult: (key, preview) => setResult(key === null || preview === null ? null : { key, preview }),
      now: () => Date.now(),
      setTimer: (fn, ms) => window.setTimeout(fn, ms),
      clearTimer: (id) => window.clearTimeout(id),
    });
  }
  const lastState = useRef<unknown>(stateKey);
  if (lastState.current !== stateKey) {
    lastState.current = stateKey;
    fetcher.current.reset();
  }
  const key = query?.key ?? null;
  useEffect(() => {
    fetcher.current?.want(query);
    // `query` 由 `key` 決定，不必列入相依。
  }, [key, stateKey]);
  useEffect(() => () => fetcher.current?.dispose(), []);
  return result !== null && result.key === key ? result.preview : null;
}
