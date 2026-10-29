// 戰鬥畫面的「送出」動作（由 BattleScreen 抽出，Phase 3T-7）：送出動作、詢問視窗的決定、複製／複合技能第二段的選目標、
// 反應設定、隊友指令；召喚技能多一步選灌注的關鍵字；詢問視窗勾了「之後都自動」的補送。

import { useCallback, useEffect, useState, type MutableRefObject } from "react";
import { api } from "../../api/client";
import type { Action, BattleResponse, OrderSet, SkillCard, UnitView } from "../../api/types";
import { followupTargetOf } from "../../battle/followup";
import { infusionChoices } from "../../battle/infusion";
import { pendingAutoActions, queueAuto, setModeAction } from "../../battle/reactions";
import type { ReactionMode } from "../../api/types";

type Cards = Readonly<Record<string, SkillCard | undefined>>;

export interface BattleActions {
  /** 送出動作（不經灌注選擇）。 */
  send(a: Action): void;
  /** 送出動作；召喚技能有可選的灌注關鍵字時先開選擇視窗。 */
  act(a: Action): void;
  infusionPick: Action | null;
  setInfusionPick(a: Action | null): void;
  infusionOptions: ReturnType<typeof infusionChoices>;
  decide(accept: boolean): void;
  /** 複製技能的選目標：`null` ＝ 放棄施放（不付代價）；複合技能第二段的選目標：`null` ＝ 放棄第二段。 */
  decideCopy(pick: Action | null): void;
  decideWith(accept: boolean, always: boolean): void;
  setReaction(reaction: string, m: ReactionMode): void;
  issueOrders(orders: OrderSet): void;
  autoQueue: string[];
}

export function useBattleActions(
  battleId: string,
  heroId: string,
  hero: UnitView | null,
  response: BattleResponse,
  cards: Cards,
  cardsRef: MutableRefObject<Cards>,
  run: (call: () => Promise<BattleResponse>) => Promise<void>,
  canAct: boolean,
  followPaused: boolean,
  setOrderPick: (kind: null) => void,
): BattleActions {
  const send = useCallback((a: Action) => void run(() => api.act(battleId, a)), [battleId, run]);
  // 召喚技能（3-33b）：目標選好後多一步選灌注的關鍵字（可選 2 個以上時才問）
  const [infusionPick, setInfusionPick] = useState<Action | null>(null);
  /** 詢問視窗勾了「之後都自動」：輪到主角時才能送 set_reaction_mode，先記在這裡。 */
  const [autoQueue, setAutoQueue] = useState<string[]>([]);
  const act = useCallback(
    (a: Action) => {
      if (infusionChoices(hero, a, cardsRef.current).length > 0) setInfusionPick(a);
      else send(a);
    },
    [cardsRef, hero, send],
  );
  const infusionOptions = infusionPick === null ? [] : infusionChoices(hero, infusionPick, cards);
  const decide = useCallback(
    (accept: boolean) => void run(() => api.decide(battleId, accept)),
    [battleId, run],
  );
  const decideCopy = useCallback(
    (pick: Action | null) => {
      if (pick !== null && pick.type !== "use_skill") return;
      if (followPaused) {
        const target = followupTargetOf(pick);
        void run(() => api.decide(battleId, target !== null, null, target));
        return;
      }
      void run(() => api.decide(battleId, pick !== null, pick));
    },
    [battleId, run, followPaused],
  );
  const decideWith = useCallback(
    (accept: boolean, always: boolean) => {
      const reaction = response.pending?.reaction;
      if (accept && always && reaction !== undefined) setAutoQueue((q) => queueAuto(q, reaction));
      decide(accept);
    },
    [decide, response.pending],
  );
  const setReaction = useCallback(
    (reaction: string, m: ReactionMode) => act(setModeAction(heroId, reaction, m)),
    [act, heroId],
  );
  const issueOrders = useCallback(
    (orders: OrderSet) => {
      setOrderPick(null);
      void run(() => api.setOrders(battleId, orders));
    },
    [battleId, run, setOrderPick],
  );

  // 詢問視窗勾了「之後都自動」：輪到主角時（可以送動作）才補送 set_reaction_mode。
  useEffect(() => {
    if (!canAct || hero === null || autoQueue.length === 0) return;
    const [first] = pendingAutoActions(autoQueue, hero);
    if (first === undefined || first.type !== "set_reaction_mode") {
      setAutoQueue([]);
      return;
    }
    setAutoQueue((q) => q.filter((r) => r !== first.reaction));
    act(first);
  }, [canAct, hero, autoQueue, act]);

  return {
    send,
    act,
    infusionPick,
    setInfusionPick,
    infusionOptions,
    decide,
    decideCopy,
    decideWith,
    setReaction,
    issueOrders,
    autoQueue,
  };
}
