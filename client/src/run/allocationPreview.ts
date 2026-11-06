// 升級配點與營火重配的資源預覽（Phase 3H-5）：配點後的最大 HP、法力、耐力變化由後端算
// （`POST /api/runs/{id}/allocation-preview`，和一輪面板同一組函式），前端不寫公式。
import { useEffect, useState } from "react";
import { api } from "../api/client";
import { cleanAllocation, type Allocation } from "./flow";

/** 配點預覽的來源（大世界 5A-7 用自己的端點）。 */
export type AllocationPreviewLoader = (attributes: Record<string, number>) => Promise<{ summary_zh: string }>;

/** 依目前配點向伺服器取變化文字（例「最大 HP ＋6、耐力 ＋4」）；沒配點或沒變化時為空字串。
 *  載入新值前保留舊值（畫面不閃）；`runId` 為空時不查（`load` 有給時改用它，`runId` 只當快取鍵）。 */
export function useAllocationPreview(runId: string | null | undefined, alloc: Allocation, load?: AllocationPreviewLoader): string {
  const attrs = cleanAllocation(alloc);
  const key = `${runId ?? ""}|${JSON.stringify(attrs)}`;
  const [result, setResult] = useState<{ key: string; text: string }>({ key: "", text: "" });
  const empty = Object.keys(attrs).length === 0;
  useEffect(() => {
    if (runId === null || runId === undefined || empty) return undefined;
    let cancelled = false;
    (load ?? ((a: Record<string, number>) => api.allocationPreview(runId, a)))(attrs).then(
      (out) => {
        if (!cancelled) setResult({ key, text: out.summary_zh });
      },
      () => undefined,
    );
    return () => {
      cancelled = true;
    };
    // attrs 由 key 決定
  }, [key]);
  return empty ? "" : result.text;
}
