// 選移動時的路徑預覽（Phase 6A-4c）：滑過格子時向伺服器要路徑預覽（節流 120ms、同一狀態下快取，見 `battle/pathFetch.ts`）。
import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { PathPreviewFetcher, PathPreviewScope } from "../battle/pathFetch";
import type { PathPreview, PathQuery } from "../battle/pathPreview";

/**
 * `stateKey` 或 `battleId` 改變時清掉快取。`query` 為 `null` 時不預覽。
 * 6C-R1：請求送到「目前」的 `battleId`（`PathPreviewScope`），不是 fetcher 建立時的那場。
 */
export function usePathPreview(battleId: string, stateKey: unknown, query: PathQuery | null): PathPreview | null {
  const [result, setResult] = useState<{ battleId: string; key: string; preview: PathPreview } | null>(null);
  const scope = useRef<PathPreviewScope | null>(null);
  if (scope.current === null) scope.current = new PathPreviewScope(battleId, stateKey);
  const fetcher = useRef<PathPreviewFetcher | null>(null);
  if (fetcher.current === null) {
    const sc = scope.current;
    fetcher.current = new PathPreviewFetcher({
      fetch: sc.fetchWith((id, body) => api.pathPreview(id, body)),
      onResult: (key, preview) => setResult(key === null || preview === null ? null : { battleId: sc.battleId, key, preview }),
      now: () => Date.now(),
      setTimer: (fn, ms) => window.setTimeout(fn, ms),
      clearTimer: (id) => window.clearTimeout(id),
    });
  }
  if (scope.current.update(battleId, stateKey)) fetcher.current.reset();
  const key = query?.key ?? null;
  useEffect(() => {
    fetcher.current?.want(query);
    // `query` 由 `key` 決定，不必列入相依。
  }, [key, stateKey, battleId]);
  useEffect(() => () => fetcher.current?.dispose(), []);
  return result !== null && result.key === key && result.battleId === battleId ? result.preview : null;
}
