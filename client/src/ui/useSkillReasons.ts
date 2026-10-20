// 取得灰掉技能的原因：輪到主角出手時向伺服器查一次（失敗就沒有，畫面退回本地端的說明）。
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { BattleResponse } from "../api/types";
import type { ReasonMap } from "../battle/skillReasons";

export function useSkillReasons(battleId: string, response: BattleResponse): ReasonMap | null {
  const [reasons, setReasons] = useState<{ response: BattleResponse; map: ReasonMap } | null>(null);
  const awaitingAction = response.awaiting === "action";
  useEffect(() => {
    if (!awaitingAction) return undefined;
    let cancelled = false;
    api
      .skillReasons(battleId)
      .then((r) => {
        if (!cancelled) setReasons({ response, map: r.reasons });
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [battleId, response, awaitingAction]);
  return reasons !== null && reasons.response === response ? reasons.map : null;
}
