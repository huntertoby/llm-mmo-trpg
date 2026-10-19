// 戰鬥畫面：格子（PixiJS）＋ 回合列 ＋ HUD ＋ 技能列 ＋ 操作 ＋ 戰鬥紀錄。
// 每次送出動作或決定：鎖住操作 → 收到回應 → 先畫 `initial_view`，再依 `steps` 一步一步播放
// （標示行動者 → 移動動畫 → 該步的 `view` → 紀錄 → 停頓）→ 最後以 `res.view` 為準。
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { flushSync } from "react-dom";
import { api, ApiError } from "../api/client";
import type { Action, BattleResponse, BattleView, OrderSet, Pos, ReactionMode } from "../api/types";
import { actionForClick, actionLabel, classifyActions, type LabeledAction } from "../battle/actions";
import { buildDrawModel } from "../battle/drawModel";
import { posKey, samePos } from "../battle/geometry";
import type { LogLine } from "../battle/log";
import {
  EMPTY_ORDERS,
  orderFromTile,
  orderTargetTiles,
  withOrder,
  type OrderKind,
} from "../battle/orders";
import {
  frameOps,
  playbackPlan,
  remainingLines,
  type PlayOp,
  type PlaySpeed,
} from "../battle/playback";
import {
  pendingAutoActions,
  queueAuto,
  ruleOfPending,
  setModeAction,
  triggerEventText,
} from "../battle/reactions";
import { marksTextAt, telegraphMarks } from "../battle/telegraph";
import {
  actionAtTile,
  basicModes,
  DIRECTION_ARROWS,
  fallbackActions,
  isSelfOnly,
  skillButtons,
  skillMode,
  targetTiles,
  type ActionMode,
} from "../battle/targeting";
import { unitNames } from "../battle/units";
import type { BattleRenderer, Highlights } from "../render/BattleRenderer";
import { ActionPanel } from "../ui/ActionPanel";
import { BattleCanvas } from "../ui/BattleCanvas";
import { BattleLog } from "../ui/BattleLog";
import { DecisionDialog } from "../ui/DecisionDialog";
import { EndPanel } from "../ui/EndPanel";
import { ErrorBanner } from "../ui/ErrorBanner";
import { Hud } from "../ui/Hud";
import { OrdersPanel } from "../ui/OrdersPanel";
import { ReactionPanel } from "../ui/ReactionPanel";
import { SkillBar } from "../ui/SkillBar";
import { loadSpeed, saveSpeed, SpeedControl } from "../ui/SpeedControl";
import { TelegraphPanel } from "../ui/TelegraphPanel";
import { TurnBar } from "../ui/TurnBar";
import { UnitInfo } from "../ui/UnitInfo";
import { useSkillCards, useSkillNames } from "../ui/useSkillCards";
import { usePreview } from "../ui/usePreview";

interface Props {
  initial: BattleResponse;
  onExit(): void;
}

const BANNER_MS = 1000;
const NO_HIGHLIGHTS: Highlights = {
  moves: [],
  attacks: [],
  directions: [],
  preview: [],
  telegraph: [],
  focus: null,
  hover: null,
};

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
  const [shown, setShown] = useState<BattleView>(initial.initial_view);
  /** 逐步播放時指定的行動者；`undefined` ＝ 用視圖的 `active_unit`。 */
  const [acting, setActing] = useState<string | undefined>(undefined);
  const [lines, setLines] = useState<LogLine[]>([]);
  const [busy, setBusy] = useState(true);
  const [playing, setPlaying] = useState(false);
  const [banner, setBanner] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hover, setHover] = useState<Pos | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [speed, setSpeed] = useState<PlaySpeed>(loadSpeed);
  const [modeKey, setModeKey] = useState<string | null>(null);
  const [panelPreview, setPanelPreview] = useState<Action | null>(null);
  /** 正在等玩家在戰場上點目標的隊友指令。 */
  const [orderPick, setOrderPick] = useState<OrderKind | null>(null);
  /** 詢問視窗勾了「之後都自動」：輪到主角時才能送 set_reaction_mode，先記在這裡。 */
  const [autoQueue, setAutoQueue] = useState<string[]>([]);
  const busyRef = useRef(true);
  const speedRef = useRef(speed);
  const skipRef = useRef(false);
  const wakeRef = useRef<(() => void) | null>(null);
  const startedRef = useRef(false);
  const rendererRef = useRef<BattleRenderer | null>(null);

  useEffect(() => {
    speedRef.current = speed;
    saveSpeed(speed);
  }, [speed]);

  // ---- 派生資料 --------------------------------------------------------------
  const view = response.view;
  const hero = useMemo(() => view.units.find((u) => u.id === heroId) ?? null, [view, heroId]);
  const skillIds = useMemo(() => {
    const ids = new Set<string>(hero?.skills ?? []);
    for (const a of response.legal_actions) if (a.type === "use_skill") ids.add(a.skill_id);
    for (const id of Object.keys(hero?.cooldowns ?? {})) ids.add(id);
    return [...ids].sort();
  }, [hero, response.legal_actions]);
  const cards = useSkillCards(skillIds);
  const skillNames = useSkillNames(cards);
  const names = useMemo(() => unitNames(shown), [shown]);
  const liveNames = useMemo(() => unitNames(view), [view]);
  const canAct = response.awaiting === "action" && !busy;
  const classified = useMemo(
    () => classifyActions(response.legal_actions, view, skillNames),
    [response, view, skillNames],
  );
  const buttons = useMemo(
    () => (hero === null ? [] : skillButtons(hero, response.legal_actions, cards)),
    [hero, response.legal_actions, cards],
  );
  const basic = useMemo(() => basicModes(response.legal_actions), [response.legal_actions]);
  const modes = useMemo(() => {
    const map = new Map<string, ActionMode>();
    for (const m of basic) map.set(m.key, m);
    for (const b of buttons) if (b.disabledReason === null) map.set(`skill:${b.skillId}`, skillMode(b));
    return map;
  }, [basic, buttons]);
  const mode = canAct && modeKey !== null ? (modes.get(modeKey) ?? null) : null;
  const fallback = useMemo<LabeledAction[]>(
    () =>
      hero === null
        ? []
        : fallbackActions(response.legal_actions, hero).map((action) => ({
            action,
            label: actionLabel(action, view, skillNames, liveNames),
          })),
    [hero, response.legal_actions, view, skillNames, liveNames],
  );
  const model = useMemo(() => buildDrawModel(shown, heroId, acting), [shown, heroId, acting]);
  const marks = useMemo(
    () => (busy || view.ended ? [] : telegraphMarks(response.telegraph, view)),
    [busy, view, response.telegraph],
  );
  const focusTile = useMemo<Pos | null>(() => {
    const trigger = response.pending?.trigger_unit_id;
    if (response.awaiting !== "decision" || trigger == null) return null;
    return view.units.find((u) => u.id === trigger)?.pos ?? null;
  }, [response, view]);
  const canOrder = !busy && response.awaiting !== "ended" && response.awaiting !== "stalled";

  // 回應換了（動作送出、狀態改變）就取消選取。
  useEffect(() => {
    setModeKey(null);
    setPanelPreview(null);
  }, [response]);

  // ---- 預覽 -----------------------------------------------------------------
  const hoverAction = useMemo<Action | null>(() => {
    if (!canAct || hover === null || hero === null) return null;
    if (mode !== null) return actionAtTile(mode, view, hero, hover);
    const target = view.units.find((u) => !u.downed && !u.escaped && samePos(u.pos, hover));
    return target === undefined ? null : (classified.attacks.get(target.id) ?? null);
  }, [canAct, hover, hero, mode, view, classified]);
  const selfAction = mode !== null && isSelfOnly(mode.targets) ? mode.targets.self : null;
  const preview = usePreview(battleId, response, canAct ? (hoverAction ?? panelPreview ?? selfAction) : null);

  // ---- 高亮 -----------------------------------------------------------------
  const highlights = useMemo<Highlights>(() => {
    const common = { telegraph: marks, focus: focusTile, hover };
    if (orderPick !== null && canOrder) {
      return { ...NO_HIGHLIGHTS, ...common, attacks: orderTargetTiles(orderPick, view, heroId) };
    }
    if (!canAct || hero === null) return { ...NO_HIGHLIGHTS, ...common };
    const previewTiles = (preview?.affected_tiles ?? []).map(([x, y]): Pos => ({ x: x as number, y: y as number }));
    if (mode !== null) {
      const tt = targetTiles(mode, view, hero);
      return {
        moves: [],
        attacks: tt.targets,
        directions: tt.directions.map((d) => ({ pos: d.pos, arrow: DIRECTION_ARROWS[d.direction] })),
        preview: previewTiles,
        ...common,
      };
    }
    const moves = [...classified.moves.values()].map((m) => m.path[m.path.length - 1] as Pos);
    const attacks = [...classified.attacks.keys()].flatMap((id) => {
      const u = view.units.find((x) => x.id === id);
      return u === undefined ? [] : [u.pos];
    });
    return { moves, attacks, directions: [], preview: previewTiles, ...common };
  }, [canAct, canOrder, hero, heroId, mode, classified, view, preview, hover, marks, focusTile, orderPick]);

  // ---- 播放 -----------------------------------------------------------------
  const sleep = useCallback(
    (ms: number) =>
      new Promise<void>((resolve) => {
        const timer = window.setTimeout(done, ms);
        function done() {
          window.clearTimeout(timer);
          wakeRef.current = null;
          resolve();
        }
        wakeRef.current = done;
      }),
    [],
  );

  const skipNow = useCallback(() => {
    skipRef.current = true;
    wakeRef.current?.();
  }, []);

  const runOp = useCallback(
    async (op: PlayOp) => {
      const skip = () => skipRef.current || speedRef.current === "skip";
      switch (op.op) {
        case "mark":
          flushSync(() => setActing(op.unitId ?? undefined));
          break;
        case "move":
          await rendererRef.current?.animate([op.anim], skip);
          break;
        case "view":
          flushSync(() => setShown(op.view));
          break;
        case "log":
          setLines((prev) => [...prev, ...op.lines]);
          break;
        case "pause":
          if (!skip()) await sleep(op.ms);
          break;
      }
    },
    [sleep],
  );

  const play = useCallback(
    async (res: BattleResponse, withBanner: boolean) => {
      skipRef.current = false;
      setPlaying(true);
      try {
        const plan = playbackPlan(res, heroId, speedRef.current);
        flushSync(() => {
          setActing(undefined);
          setShown(plan.initialView);
        });
        if (withBanner) {
          setBanner(true);
          if (speedRef.current !== "skip") await sleep(BANNER_MS);
          setBanner(false);
        }
        let done = 0;
        for (const frame of plan.frames) {
          if (skipRef.current) break;
          for (const op of frameOps(frame)) await runOp(op);
          done += 1;
        }
        if (done < plan.frames.length) setLines((prev) => [...prev, ...remainingLines(plan, done)]);
      } finally {
        setBanner(false);
        flushSync(() => {
          setActing(undefined);
          setResponse(res);
          setShown(res.view);
        });
        setPlaying(false);
      }
    },
    [heroId, runOp, sleep],
  );

  // 建立戰鬥後的第一次播放：「戰鬥開始」橫幅 ＋ 開場到主角回合之間的 AI 行動。
  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    void (async () => {
      try {
        await play(initial, true);
      } catch (e) {
        setError(errorText(e));
        setShown(initial.view);
      } finally {
        busyRef.current = false;
        setBusy(false);
      }
    })();
  }, [initial, play]);

  const run = useCallback(
    async (call: () => Promise<BattleResponse>) => {
      if (busyRef.current) return;
      busyRef.current = true;
      setBusy(true);
      setError(null);
      setModeKey(null);
      setPanelPreview(null);
      try {
        await play(await call(), false);
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
    [battleId, run],
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

  // ---- 選取與點選 -------------------------------------------------------------
  const cancel = useCallback(() => {
    setModeKey(null);
    setPanelPreview(null);
    setOrderPick(null);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") cancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [cancel]);

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
    [act],
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
        issueOrders(withOrder(response.orders, { kind }));
        return;
      }
      setOrderPick((cur) => (cur === kind ? null : kind));
    },
    [issueOrders, response.orders],
  );

  const onTileClick = useCallback(
    (tile: Pos) => {
      if (orderPick !== null && canOrder) {
        const order = orderFromTile(orderPick, view, tile);
        if (order !== null) issueOrders(withOrder(response.orders, order));
        return;
      }
      if (canAct && hero !== null) {
        if (mode !== null) {
          if (mode.kind === "shove_aside") return; // 撥開要用面板選方向
          const a = actionAtTile(mode, view, hero, tile);
          if (a !== null) act(a);
          return;
        }
        const action = actionForClick(classified, view, tile);
        if (action !== null) {
          act(action);
          return;
        }
      }
      setSelected(unitAt(shown, tile)?.id ?? null);
    },
    [act, canAct, canOrder, classified, hero, issueOrders, mode, orderPick, response.orders, shown, view],
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
  const shownHero = shown.units.find((u) => u.id === heroId) ?? null;
  const ended = (response.awaiting === "ended" || response.awaiting === "stalled") && !busy;

  return (
    <div className="battle-screen">
      <TurnBar view={shown} names={names} acting={acting} />
      <ErrorBanner message={error} onClose={() => setError(null)} />
      <div className="battle-main">
        <div className="battle-board">
          <BattleCanvas
            model={model}
            highlights={highlights}
            onTileClick={onTileClick}
            onTileHover={onTileHover}
            onCancel={cancel}
            rendererRef={rendererRef}
          />
          {banner && <div className="battle-banner">戰鬥開始</div>}
        </div>
        <div className="battle-side">
          <Hud view={shown} hero={shownHero} skills={skillNames} />
          <ReactionPanel hero={hero} enabled={canAct} queued={autoQueue} onSet={setReaction} />
          <SkillBar
            buttons={buttons}
            cards={cards}
            selectedKey={mode?.key ?? null}
            enabled={canAct}
            onSelect={pickSkill}
          />
          {ended ? (
            <EndPanel response={response} onRestart={onExit} />
          ) : (
            <ActionPanel
              enabled={canAct}
              basic={basic}
              mode={mode}
              endTurn={classified.endTurn}
              fallback={fallback}
              moveCount={classified.moves.size}
              attackCount={classified.attacks.size}
              preview={preview}
              view={view}
              interactOptions={response.interact_options}
              names={liveNames}
              onPickMode={pickMode}
              onCancel={cancel}
              onAction={act}
              onPreviewAction={setPanelPreview}
            />
          )}
          <SpeedControl speed={speed} playing={playing} onSpeed={setSpeed} onSkipNow={skipNow} />
          <TelegraphPanel
            telegraph={response.telegraph}
            marks={marks}
            hoverTexts={marksTextAt(marks, hover)}
          />
          <OrdersPanel
            orders={response.orders}
            ignored={response.orders_ignored}
            names={liveNames}
            enabled={canOrder}
            picking={orderPick}
            onPick={pickOrder}
            onProtectHero={() => issueOrders(withOrder(response.orders, { kind: "protect", ward: heroId }))}
            onCancelPick={() => setOrderPick(null)}
            onClear={() => issueOrders(EMPTY_ORDERS)}
          />
          <UnitInfo unit={infoUnit} names={names} heroId={heroId} skills={skillNames} />
          <BattleLog lines={lines} />
        </div>
      </div>
      {response.awaiting === "decision" && response.pending !== null && !busy && (
        <DecisionDialog
          pending={response.pending}
          rule={ruleOfPending(hero, response.pending)}
          names={liveNames}
          eventText={triggerEventText(response)}
          enabled={!busy}
          onDecide={decideWith}
        />
      )}
    </div>
  );
}
