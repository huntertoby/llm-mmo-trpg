// 戰鬥中主角的技能卡（Phase 3-41c）：向伺服器取「施放者當下的實際值」版本——傷害算法的目前加成、
// 召喚物資訊（和引擎生成召喚物同一組函式）。輪到主角出手時查一次；失敗就沒有，畫面退回基本卡片。
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { BattleResponse, SkillCard } from "../api/types";

type Cards = Readonly<Record<string, SkillCard | undefined>>;

/** 把實際值版本的卡片蓋在基本卡片上（只換伺服器有給的技能）。 */
export function overlayCards(base: Cards, live: Cards | null): Cards {
  return live === null ? base : { ...base, ...live };
}

export function useHeroCards(battleId: string, response: BattleResponse, base: Cards): Cards {
  const [live, setLive] = useState<{ battleId: string; cards: Cards } | null>(null);
  const awaitingAction = response.awaiting === "action";
  useEffect(() => {
    if (!awaitingAction) return undefined;
    let cancelled = false;
    api
      .heroCards(battleId)
      .then((r) => {
        if (!cancelled) setLive({ battleId, cards: r.cards });
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [battleId, response, awaitingAction]);
  return useMemo(() => overlayCards(base, live !== null && live.battleId === battleId ? live.cards : null), [base, live, battleId]);
}
