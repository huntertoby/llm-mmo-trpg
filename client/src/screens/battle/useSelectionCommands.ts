// 戰鬥畫面的選取操作（由 BattleScreen 抽出，Phase 3T-7）：取消、選模式／技能／隊友指令、召喚物指揮與灌注的取得選項。
// 狀態在 `useSelection`；這裡只放「改狀態的動作」。

import { useCallback, useMemo } from "react";
import { api } from "../../api/client";
import type { Action, BattleView, OrderSet, Pos } from "../../api/types";
import { withOrder, type OrderKind } from "../../battle/orders";
import { controllableSummons } from "../../battle/summonControl";
import { isSelfOnly, type ActionMode } from "../../battle/targeting";
import { errorText } from "./usePlayback";
import type { Selection } from "./useSelection";

export interface SelectionCommands {
  cancel(): void;
  summons: ReturnType<typeof controllableSummons>;
  startCommand(summonId: string): void;
  startInfuse(summonId: string): void;
  pickCommandDest(dest: Pos): void;
  pickMode(m: ActionMode): void;
  pickSkill(skillId: string): void;
  pickOrder(kind: OrderKind): void;
}

export function useSelectionCommands(
  battleId: string,
  heroId: string,
  view: BattleView,
  orders: OrderSet,
  modes: ReadonlyMap<string, ActionMode>,
  sel: Selection,
  act: (a: Action) => void,
  issueOrders: (orders: OrderSet) => void,
  setError: (message: string) => void,
): SelectionCommands {
  const {
    setModeKey,
    setPanelPreview,
    setOrderPick,
    setHurlPick,
    setCommand,
    setInfuse,
    setLoadingCommand,
    setLoadingInfuse,
  } = sel;
  const cancel = useCallback(() => {
    setModeKey(null);
    setPanelPreview(null);
    setOrderPick(null);
    setHurlPick(null);
    setCommand(null);
    setInfuse(null);
  }, [setModeKey, setPanelPreview, setOrderPick, setHurlPick, setCommand, setInfuse]);

  // ---- 召喚物操控（3-33c）-----------------------------------------------------
  const summons = useMemo(() => controllableSummons(view, heroId), [view, heroId]);
  const startCommand = useCallback(
    (summonId: string) => {
      setModeKey(null);
      setOrderPick(null);
      setPanelPreview(null);
      setInfuse(null);
      setLoadingCommand(true);
      api
        .commandOptions(battleId, summonId)
        .then((options) => setCommand({ summonId, options, dest: null }))
        .catch((e: unknown) => setError(errorText(e)))
        .finally(() => setLoadingCommand(false));
    },
    [battleId, setModeKey, setOrderPick, setPanelPreview, setInfuse, setLoadingCommand, setCommand, setError],
  );
  // 灌注技能（3-33d）：取得技能選單（不能灌注的附原因），滑過技能預覽召喚物從自己位置施放的範圍
  const startInfuse = useCallback(
    (summonId: string) => {
      setModeKey(null);
      setOrderPick(null);
      setPanelPreview(null);
      setCommand(null);
      setLoadingInfuse(true);
      api
        .infuseOptions(battleId, summonId)
        .then((options) => setInfuse({ summonId, options }))
        .catch((e: unknown) => setError(errorText(e)))
        .finally(() => setLoadingInfuse(false));
    },
    [battleId, setModeKey, setOrderPick, setPanelPreview, setCommand, setLoadingInfuse, setInfuse, setError],
  );
  const pickCommandDest = useCallback(
    (dest: Pos) => {
      setCommand((cur) => (cur === null ? cur : { ...cur, dest }));
    },
    [setCommand],
  );

  const pickMode = useCallback(
    (m: ActionMode) => {
      const instant = m.kind !== "skill" && isSelfOnly(m.targets) && m.targets.self !== null;
      if (instant && m.targets.self !== null) {
        act(m.targets.self);
        return;
      }
      setPanelPreview(null);
      setOrderPick(null);
      setModeKey((cur) => (cur === m.key ? null : m.key));
    },
    [act, setPanelPreview, setOrderPick, setModeKey],
  );

  const pickSkill = useCallback(
    (skillId: string) => {
      const m = modes.get(`skill:${skillId}`);
      if (m !== undefined) pickMode(m);
    },
    [modes, pickMode],
  );

  const pickOrder = useCallback(
    (kind: OrderKind) => {
      setModeKey(null);
      setPanelPreview(null);
      if (kind === "use_environment") {
        issueOrders(withOrder(orders, { kind }));
        return;
      }
      setOrderPick((cur) => (cur === kind ? null : kind));
    },
    [issueOrders, orders, setModeKey, setPanelPreview, setOrderPick],
  );

  return { cancel, summons, startCommand, startInfuse, pickCommandDest, pickMode, pickSkill, pickOrder };
}
