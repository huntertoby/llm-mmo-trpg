// 開局畫面的資源預覽（Phase 3-41c）：選了武器、配了點之後主角的最大 HP、法力、耐力。
// 數字全部由後端算（`/api/runs/start-resources`，和開新一輪建立主角同一個函式），前端不寫公式。
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { StartResources } from "../api/types";
import { cleanAllocation, type Allocation } from "./flow";

/** 預覽文字：「HP 38・法力 12・耐力 34」；還沒載入時只寫「HP …」。 */
export function resourceText(r: StartResources | null): string {
  if (r === null) return "HP …・法力 …・耐力 …";
  return `HP ${r.hp}・法力 ${r.mana}・耐力 ${r.stamina}`;
}

/** 依武器與目前配點向伺服器取預覽；`weapon` 為空時不查。載入新值前保留舊值（畫面不閃）。 */
export function useStartResources(weapon: string, alloc: Allocation): StartResources | null {
  const [resources, setResources] = useState<{ key: string; value: StartResources } | null>(null);
  const attrs = cleanAllocation(alloc);
  const key = `${weapon}|${JSON.stringify(attrs)}`;
  useEffect(() => {
    if (weapon === "") return undefined;
    let cancelled = false;
    api.startResources(weapon, attrs).then(
      (value) => {
        if (!cancelled) setResources({ key, value });
      },
      () => undefined,
    );
    return () => {
      cancelled = true;
    };
    // attrs 由 key 決定
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return resources?.value ?? null;
}
