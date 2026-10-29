// 戰鬥畫面的「選取與目標」狀態（由 BattleScreen 抽出，Phase 3T-7）：選中的技能／動作模式、投擲的第一段物件、
// 召喚物指揮與灌注、面板滑過的預覽動作、等待點目標的隊友指令。回應換了就全部取消選取。

import { useEffect, useState } from "react";
import type { Action, BattleResponse } from "../../api/types";
import type { OrderKind } from "../../battle/orders";
import type { CommandSession, InfuseSession } from "../../battle/summonControl";
import type { ActionMode } from "../../battle/targeting";

export interface Selection {
  modeKey: string | null;
  setModeKey(k: string | null | ((cur: string | null) => string | null)): void;
  /** 目前選取的模式（複製／複合第二段暫停時是暫停給的模式）。 */
  mode: ActionMode | null;
  /** 投擲物件的兩段選取：第一段選好（舉起）的物件 ID；`null` ＝ 還在選物件。 */
  hurlPick: string | null;
  setHurlPick(id: string | null): void;
  // 召喚物指揮（3-33c）：進行中的指揮（伺服器給的終點與目標、目前選的終點）與取得選項中的旗標
  command: CommandSession | null;
  setCommand(c: CommandSession | null | ((cur: CommandSession | null) => CommandSession | null)): void;
  loadingCommand: boolean;
  setLoadingCommand(on: boolean): void;
  infuse: InfuseSession | null;
  setInfuse(i: InfuseSession | null): void;
  loadingInfuse: boolean;
  setLoadingInfuse(on: boolean): void;
  panelPreview: Action | null;
  setPanelPreview(a: Action | null): void;
  /** 正在等玩家在戰場上點目標的隊友指令。 */
  orderPick: OrderKind | null;
  setOrderPick(k: OrderKind | null | ((cur: OrderKind | null) => OrderKind | null)): void;
  /** 送出動作時的取消（只清技能與面板預覽；其餘等回應換了再清）。 */
  resetOnRun(): void;
}

export function useSelection(
  response: BattleResponse,
  canAct: boolean,
  copying: boolean,
  copyPick: ActionMode | null,
  modes: ReadonlyMap<string, ActionMode>,
): Selection {
  const [modeKey, setModeKey] = useState<string | null>(null);
  const [hurlPick, setHurlPick] = useState<string | null>(null);
  const [command, setCommand] = useState<CommandSession | null>(null);
  const [loadingCommand, setLoadingCommand] = useState(false);
  const [infuse, setInfuse] = useState<InfuseSession | null>(null);
  const [loadingInfuse, setLoadingInfuse] = useState(false);
  const [panelPreview, setPanelPreview] = useState<Action | null>(null);
  const [orderPick, setOrderPick] = useState<OrderKind | null>(null);
  const mode = copying ? copyPick : canAct && modeKey !== null ? (modes.get(modeKey) ?? null) : null;

  // 回應換了（動作送出、狀態改變）就取消選取。
  useEffect(() => {
    setModeKey(null);
    setPanelPreview(null);
    setHurlPick(null);
    setCommand(null);
    setInfuse(null);
  }, [response]);
  // 換了模式（選了別的技能或取消）就重新從第一段選物件。
  useEffect(() => {
    setHurlPick(null);
  }, [modeKey]);

  const resetOnRun = () => {
    setModeKey(null);
    setPanelPreview(null);
  };

  return {
    modeKey,
    setModeKey,
    mode,
    hurlPick,
    setHurlPick,
    command,
    setCommand,
    loadingCommand,
    setLoadingCommand,
    infuse,
    setInfuse,
    loadingInfuse,
    setLoadingInfuse,
    panelPreview,
    setPanelPreview,
    orderPick,
    setOrderPick,
    resetOnRun,
  };
}
