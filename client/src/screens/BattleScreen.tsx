// 戰鬥畫面：格子（PixiJS）＋ 回合資訊 ＋ 單位資訊 ＋ 操作 ＋ 戰鬥紀錄。
// 每次送出動作或決定：鎖住操作 → 收到回應 → 寫紀錄、播放移動動畫 → 以回應的 `view` 重畫。
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError } from "../api/client";
import type { Action, BattleResponse, BattleView, Pos } from "../api/types";
import { actionForClick, classifyActions, skillIdsOf } from "../battle/actions";
import { movePlan } from "../battle/animation";
import { buildDrawModel } from "../battle/drawModel";
import { posKey, samePos } from "../battle/geometry";
import { logLines, type LogLine } from "../battle/log";
import { unitNames } from "../battle/units";
import type { BattleRenderer, Highlights } from "../render/BattleRenderer";
import { ActionPanel } from "../ui/ActionPanel";
import { BattleCanvas } from "../ui/BattleCanvas";
import { BattleLog } from "../ui/BattleLog";
import { DecisionDialog } from "../ui/DecisionDialog";
import { EndPanel } from "../ui/EndPanel";
import { ErrorBanner } from "../ui/ErrorBanner";
import { TurnBar } from "../ui/TurnBar";
import { UnitInfo } from "../ui/UnitInfo";
import { useSkillNames } from "../ui/useSkillNames";

interface Props {
  initial: BattleResponse;
  onExit(): void;
}

const SKIP_KEY = "trpg.skipAnimation";

function loadSkip(): boolean {
  try {
    return window.localStorage.getItem(SKIP_KEY) === "1";
  } catch {
    return false;
  }
}

function saveSkip(value: boolean): void {
  try {
    window.localStorage.setItem(SKIP_KEY, value ? "1" : "0");
  } catch {
    // 無法存取 localStorage（私密視窗等）時只在本次有效。
  }
}

function errorText(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  return e instanceof Error ? e.message : String(e);
}

function unitAt(view: BattleView, tile: Pos | null) {
  if (tile === null) return undefined;
  const here = view.units.filter((u) => !u.escaped && samePos(u.pos, tile));
  return here.find((u) => !u.downed) ?? here[0];
}

export function BattleScreen({ initial, onExit }: Props) {
  const battleId = initial.battle_id;
  const heroId = initial.hero_id;
  const [response, setResponse] = useState(initial);
  const [shown, setShown] = useState<BattleView>(initial.view);
  const [lines, setLines] = useState<LogLine[]>(() =>
    logLines(initial.steps, unitNames(initial.view)),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hover, setHover] = useState<Pos | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [skipAnimation, setSkipAnimation] = useState(loadSkip);
  const busyRef = useRef(false);
  const skipRef = useRef(skipAnimation);
  const rendererRef = useRef<BattleRenderer | null>(null);

  useEffect(() => {
    skipRef.current = skipAnimation;
    saveSkip(skipAnimation);
  }, [skipAnimation]);

  const names = useMemo(() => unitNames(shown), [shown]);
  const skillNames = useSkillNames(skillIdsOf(response.legal_actions, response.view));
  const canAct = response.awaiting === "action" && !busy;
  const classified = useMemo(
    () => classifyActions(response.legal_actions, response.view, skillNames),
    [response, skillNames],
  );
  const model = useMemo(() => buildDrawModel(shown, heroId), [shown, heroId]);

  const highlights = useMemo<Highlights>(() => {
    if (!canAct) return { moves: [], attacks: [], hover };
    const moves = [...classified.moves.values()].map((m) => m.path[m.path.length - 1] as Pos);
    const attacks = [...classified.attacks.keys()].flatMap((id) => {
      const u = response.view.units.find((x) => x.id === id);
      return u === undefined ? [] : [u.pos];
    });
    return { moves, attacks, hover };
  }, [canAct, classified, hover, response]);

  const play = useCallback(async (res: BattleResponse) => {
    setLines((prev) => [...prev, ...logLines(res.steps, unitNames(res.view))]);
    await rendererRef.current?.animate(movePlan(res.steps), () => skipRef.current);
    setResponse(res);
    setShown(res.view);
  }, []);

  const run = useCallback(
    async (call: () => Promise<BattleResponse>) => {
      if (busyRef.current) return;
      busyRef.current = true;
      setBusy(true);
      setError(null);
      try {
        await play(await call());
      } catch (e) {
        setError(errorText(e));
        // 以伺服器目前的狀態為準，避免畫面與伺服器不一致而卡住。
        try {
          const fresh = await api.battle(battleId);
          setResponse(fresh);
          setShown(fresh.view);
        } catch {
          // 連不上伺服器：保留畫面，錯誤訊息已顯示。
        }
      } finally {
        busyRef.current = false;
        setBusy(false);
      }
    },
    [battleId, play],
  );

  const act = useCallback((a: Action) => void run(() => api.act(battleId, a)), [battleId, run]);
  const decide = useCallback(
    (accept: boolean) => void run(() => api.decide(battleId, accept)),
    [battleId, run],
  );

  const onTileClick = useCallback(
    (tile: Pos) => {
      const action = canAct ? actionForClick(classified, response.view, tile) : null;
      if (action !== null) {
        act(action);
        return;
      }
      setSelected(unitAt(shown, tile)?.id ?? null);
    },
    [act, canAct, classified, response, shown],
  );

  const onTileHover = useCallback((tile: Pos | null) => {
    setHover((prev) => {
      if (prev === null || tile === null) return tile;
      return posKey(prev) === posKey(tile) ? prev : tile;
    });
  }, []);

  const infoUnit =
    unitAt(shown, hover) ??
    shown.units.find((u) => u.id === selected) ??
    shown.units.find((u) => u.id === heroId) ??
    null;
  const ended = response.awaiting === "ended" || response.awaiting === "stalled";

  return (
    <div className="battle-screen">
      <TurnBar view={shown} names={names} />
      <ErrorBanner message={error} onClose={() => setError(null)} />
      <div className="battle-main">
        <div className="battle-board">
          <BattleCanvas
            model={model}
            highlights={highlights}
            onTileClick={onTileClick}
            onTileHover={onTileHover}
            rendererRef={rendererRef}
          />
        </div>
        <div className="battle-side">
          <UnitInfo unit={infoUnit} names={names} heroId={heroId} skills={skillNames} />
          {ended && !busy ? (
            <EndPanel response={response} onRestart={onExit} />
          ) : (
            <ActionPanel
              classified={classified}
              enabled={canAct}
              skipAnimation={skipAnimation}
              onSkipAnimation={setSkipAnimation}
              onAction={act}
            />
          )}
          <BattleLog lines={lines} />
        </div>
      </div>
      {response.awaiting === "decision" && response.pending !== null && !busy && (
        <DecisionDialog pending={response.pending} names={names} enabled={!busy} onDecide={decide} />
      )}
    </div>
  );
}
