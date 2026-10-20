// 戰鬥畫面（Phase 3-8 版面）：頂端列（回合、行動順序、反應設定／隊友指令／圖例的彈出面板）、
// 中央放大的戰場（滑過單位顯示浮動資訊卡）、右側可收合的紀錄與預告、左下主角狀態、底部技能列、右下回合操作。
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
import { previewOverlays } from "../battle/scenePreview";
import { marksTextAt, telegraphMarks } from "../battle/telegraph";
import { zoneLinesAt } from "../battle/zones";
import {
  actionAtTile,
  basicModes,
  copyMode,
  DIRECTION_ARROWS,
  fallbackActions,
  hurlObjectAt,
  hurlPickPos,
  isCopyPending,
  isHurlMode,
  isSelfOnly,
  skillButtons,
  skillMode,
  targetTiles,
  type ActionMode,
} from "../battle/targeting";
import { unitNames } from "../battle/units";
import type { BattleRenderer, Highlights } from "../render/BattleRenderer";
import { ModePanel } from "../ui/ActionPanel";
import { BattleTopBar } from "../ui/BattleTopBar";
import { SidePanel } from "../ui/SidePanel";
import { TurnControls } from "../ui/TurnControls";
import { useElementSize, useNarrow } from "../ui/useLayout";
import {
  actionHintText,
  loadSideCollapsed,
  saveSideCollapsed,
  togglePopup,
  type TopPopup,
} from "../battle/skillTray";
import { cardPlacement, fitScale } from "../battle/stageLayout";
import { hasOrders, orderButton } from "../battle/orders";
import { BattleCanvas } from "../ui/BattleCanvas";
import { BattleLog } from "../ui/BattleLog";
import { CopyDialog } from "../ui/CopyDialog";
import { FollowupDialog } from "../ui/FollowupDialog";
import { followupMode, followupTargetOf, isFollowupPending } from "../battle/followup";
import { DecisionDialog } from "../ui/DecisionDialog";
import { EndPanel } from "../ui/EndPanel";
import { ErrorBanner } from "../ui/ErrorBanner";
import { NoticeBanner } from "../ui/NoticeBanner";
import { needsLogRestore } from "../run/flow";
import { logLines } from "../battle/log";
import { Hud } from "../ui/Hud";
import { OrdersPanel } from "../ui/OrdersPanel";
import { ReactionPanel } from "../ui/ReactionPanel";
import { Legend } from "../ui/Legend";
import { legendEntries } from "../battle/legend";
import { SkillBar } from "../ui/SkillBar";
import { useSkillReasons } from "../ui/useSkillReasons";
import { blockedMessage, withReasons } from "../battle/skillReasons";
import { loadSpeed, saveSpeed, SpeedControl } from "../ui/SpeedControl";
import { TelegraphPanel } from "../ui/TelegraphPanel";
import { TurnBar } from "../ui/TurnBar";
import { UnitInfo } from "../ui/UnitInfo";
import { useSkillCards, useSkillNames } from "../ui/useSkillCards";
import { usePreview } from "../ui/usePreview";

interface Props {
  initial: BattleResponse;
  onExit(): void;
  /** 有值時顯示「離開」按鈕（可隨時離開），結束面板的主按鈕也用這個文字；省略為一般戰鬥。 */
  exitLabel?: string;
  /** 從一輪（roguelite）進入時：顯示「存檔」按鈕與主角倒下提示（Phase 3-5c-1）。 */
  runMode?: RunMode;
}

export interface RunMode {
  /** 存檔，回傳要顯示的訊息。 */
  onSave(): Promise<string>;
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
  overlays: [],
  picked: [],
};

function errorText(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  return e instanceof Error ? e.message : String(e);
}

function unitAt(view: BattleView, tile: Pos | null) {
  if (tile === null) return undefined;
  const here = view.units.filter((u) => !u.escaped && !u.dismissed && samePos(u.pos, tile));
  return here.find((u) => !u.downed) ?? here[0];
}

export function BattleScreen({ initial, onExit, exitLabel, runMode }: Props) {
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
  /** 中性提示（例如灰掉技能的原因），幾秒後自動消失。 */
  const [hint, setHint] = useState<string | null>(null);
  const closeHint = useCallback(() => setHint(null), []);
  const [saveNote, setSaveNote] = useState<string | null>(null);
  const [hover, setHover] = useState<Pos | null>(null);
  /** 頂端列開著的彈出面板（同時只開一個）。 */
  const [popup, setPopup] = useState<TopPopup | null>(null);
  const narrow = useNarrow();
  const [sideCollapsed, setSideCollapsed] = useState(() => loadSideCollapsed(narrow));
  const boardRef = useRef<HTMLDivElement>(null);
  const boardSize = useElementSize(boardRef);
  const [speed, setSpeed] = useState<PlaySpeed>(loadSpeed);
  const [modeKey, setModeKey] = useState<string | null>(null);
  /** 投擲物件的兩段選取：第一段選好（舉起）的物件 ID；`null` ＝ 還在選物件。 */
  const [hurlPick, setHurlPick] = useState<string | null>(null);
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
    for (const g of hero?.granted_skills ?? []) ids.add(g.skill_id); // 暫時獲得的技能（Phase 3D-8c）
    for (const a of response.legal_actions) if (a.type === "use_skill") ids.add(a.skill_id);
    for (const id of Object.keys(hero?.cooldowns ?? {})) ids.add(id);
    const copied = response.pending?.copy_skill_id; // 複製技能暫停時，被複製的技能（要顯示名稱）
    if (copied != null) ids.add(copied);
    return [...ids].sort();
  }, [hero, response.legal_actions, response.pending]);
  const cards = useSkillCards(skillIds, battleId);
  const skillNames = useSkillNames(cards);
  const names = useMemo(() => unitNames(shown), [shown]);
  const liveNames = useMemo(() => unitNames(view), [view]);
  const canAct = response.awaiting === "action" && !busy;
  const classified = useMemo(
    () => classifyActions(response.legal_actions, view, skillNames),
    [response, view, skillNames],
  );
  const skillReasons = useSkillReasons(battleId, response);
  const buttons = useMemo(
    () => (hero === null ? [] : withReasons(skillButtons(hero, response.legal_actions, cards), skillReasons)),
    [hero, response.legal_actions, cards, skillReasons],
  );
  const basic = useMemo(() => basicModes(response.legal_actions), [response.legal_actions]);
  const modes = useMemo(() => {
    const map = new Map<string, ActionMode>();
    for (const m of basic) map.set(m.key, m);
    for (const b of buttons) if (b.disabledReason === null) map.set(`skill:${b.skillId}`, skillMode(b));
    return map;
  }, [basic, buttons]);
  // 複製技能（copy_skill）暫停：第二段選取，伺服器給的 copy_options 當成一個模式（點目標即送出）。
  // 複合技能第二段（「動作 → 位移」「擊殺 → 接下一段」，Phase 3F-4b）的暫停也走同一套：伺服器給的
  // followup_options 當成模式，滑過預覽、點目標送出；下面的 `copying` 代表「暫停中為第二段選目標」。
  const copyPaused = response.awaiting === "decision" && isCopyPending(response.pending) && !busy;
  const followPaused = response.awaiting === "decision" && isFollowupPending(response.pending) && !busy;
  const copying = copyPaused || followPaused;
  const pausedSkill = followPaused ? response.pending?.skill_id : response.pending?.copy_skill_id;
  const copyName = pausedSkill == null ? "" : (skillNames[pausedSkill] ?? pausedSkill);
  const copyPick = useMemo(() => {
    if (!copying || response.pending === null) return null;
    if (followPaused) return followupMode(response.pending, response.followup_options ?? [], copyName);
    return copyMode(response.pending, response.copy_options, copyName);
  }, [copying, followPaused, response.pending, response.copy_options, response.followup_options, copyName]);
  const mode = copying ? copyPick : canAct && modeKey !== null ? (modes.get(modeKey) ?? null) : null;
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
    setHurlPick(null);
  }, [response]);
  // 換了模式（選了別的技能或取消）就重新從第一段選物件。
  useEffect(() => {
    setHurlPick(null);
  }, [modeKey]);

  // ---- 預覽 -----------------------------------------------------------------
  const hoverAction = useMemo<Action | null>(() => {
    if (!(canAct || copying) || hover === null || hero === null) return null;
    if (mode !== null) return actionAtTile(mode, view, hero, hover, hurlPick);
    const target = view.units.find((u) => !u.downed && !u.escaped && !u.dismissed && samePos(u.pos, hover));
    return target === undefined ? null : (classified.attacks.get(target.id) ?? null);
  }, [canAct, copying, hover, hero, mode, view, classified, hurlPick]);
  const selfAction = mode !== null && isSelfOnly(mode.targets) ? mode.targets.self : null;
  // 複製技能暫停時也能預覽：伺服器把滑過的選取當成「被複製技能的目標」，預覽整個施放（3C-6a）。
  const preview = usePreview(
    battleId,
    response,
    canAct || copying ? (hoverAction ?? panelPreview ?? selfAction) : null,
  );

  // ---- 高亮 -----------------------------------------------------------------
  const highlights = useMemo<Highlights>(() => {
    const common = { telegraph: marks, focus: focusTile, hover };
    if (orderPick !== null && canOrder) {
      return { ...NO_HIGHLIGHTS, ...common, attacks: orderTargetTiles(orderPick, view, heroId) };
    }
    if (!(canAct || copying) || hero === null) return { ...NO_HIGHLIGHTS, ...common };
    const previewTiles = (preview?.affected_tiles ?? []).map(([x, y]): Pos => ({ x: x as number, y: y as number }));
    const overlays = previewOverlays(preview, view);
    if (mode !== null) {
      const tt = targetTiles(mode, view, hero, hurlPick);
      const pickedAt = hurlPickPos(mode, view, hurlPick);
      return {
        moves: [],
        attacks: tt.targets,
        directions: tt.directions.map((d) => ({ pos: d.pos, arrow: DIRECTION_ARROWS[d.direction] })),
        preview: previewTiles,
        overlays,
        picked: pickedAt === undefined ? [] : [pickedAt],
        ...common,
      };
    }
    const moves = [...classified.moves.values()].map((m) => m.path[m.path.length - 1] as Pos);
    const attacks = [...classified.attacks.keys()].flatMap((id) => {
      const u = view.units.find((x) => x.id === id);
      return u === undefined ? [] : [u.pos];
    });
    return { moves, attacks, directions: [], preview: previewTiles, overlays, picked: [], ...common };
  }, [
    canAct,
    copying,
    canOrder,
    hero,
    heroId,
    mode,
    classified,
    view,
    preview,
    hover,
    marks,
    focusTile,
    orderPick,
    hurlPick,
  ]);

  const legend = useMemo(() => legendEntries(highlights.overlays, mode), [highlights.overlays, mode]);

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

  // 接續進行中的戰鬥或讀檔回來：開場的步驟不在回應裡，向伺服器取回已發生的事件還原戰鬥紀錄（Phase 3-6）。
  useEffect(() => {
    if (!needsLogRestore(initial)) return undefined;
    let cancelled = false;
    api
      .battleHistory(initial.battle_id)
      .then((h) => {
        if (cancelled) return;
        const restored = logLines(h.steps, unitNames(initial.view));
        setLines((prev) => [...restored, ...prev]);
      })
      .catch(() => undefined); // 取不到時紀錄從這裡開始，不影響操作
    return () => {
      cancelled = true;
    };
  }, [initial]);

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
  /** 複製技能的選目標：`null` ＝ 放棄施放（不付代價）；複合技能第二段的選目標：`null` ＝ 放棄第二段。 */
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
    setHurlPick(null);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      if (popup !== null) {
        // 開著彈出面板時 Esc 先關面板（並取消隊友指令的選目標），不放棄複製技能的施放
        setPopup(null);
        if (!copying) cancel();
        return;
      }
      if (copying) decideCopy(null); // 複製技能暫停時，Esc ＝ 放棄施放（不付任何代價）
      else cancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [cancel, copying, decideCopy, popup]);

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
      if ((canAct || copying) && hero !== null) {
        if (mode !== null) {
          if (mode.kind === "shove_aside") return; // 撥開要用面板選方向
          if (isHurlMode(mode)) {
            // 投擲物件：第 1 段選物件、第 2 段選落點（落點優先；再點別的物件改選，點同一個取消）
            const landing = actionAtTile(mode, view, hero, tile, hurlPick);
            if (landing !== null) {
              if (copying) decideCopy(landing);
              else act(landing);
              return;
            }
            const object = hurlObjectAt(mode, view, tile);
            if (object !== null) setHurlPick(object === hurlPick ? null : object);
            return;
          }
          const a = actionAtTile(mode, view, hero, tile);
          if (a !== null) {
            if (copying) decideCopy(a);
            else act(a);
          }
          return;
        }
        const action = actionForClick(classified, view, tile);
        if (action !== null) {
          act(action);
        }
      }
    },
    [
      act,
      canAct,
      copying,
      decideCopy,
      canOrder,
      classified,
      hero,
      hurlPick,
      issueOrders,
      mode,
      orderPick,
      response.orders,
      view,
    ],
  );

  const onTileHover = useCallback((tile: Pos | null) => {
    setHover((prev) => {
      if (prev === null || tile === null) return tile;
      return posKey(prev) === posKey(tile) ? prev : tile;
    });
  }, []);

  /** 浮動資訊卡：只在滑過單位時出現（取代固定的單位資訊欄，Phase 3-8）。 */
  const hoverUnit = unitAt(shown, hover) ?? null;
  const shownHero = shown.units.find((u) => u.id === heroId) ?? null;
  const ended = (response.awaiting === "ended" || response.awaiting === "stalled") && !busy;

  async function saveRun() {
    if (runMode === undefined) return;
    try {
      setSaveNote(await runMode.onSave());
    } catch (e) {
      setSaveNote(null);
      setError(errorText(e));
    }
  }

  const scale = boardSize === null ? 1 : fitScale({ width: boardSize.width - 16, height: boardSize.height - 16 }, model);
  const hoverTexts = [...zoneLinesAt(shown, hover, liveNames), ...marksTextAt(marks, hover)];
  const defendMode = basic.find((m) => m.kind === "defend") ?? null;
  const toggleSide = () =>
    setSideCollapsed((c) => {
      saveSideCollapsed(!c);
      return !c;
    });
  const tools = [
    {
      id: "reactions" as const,
      label: "反應設定",
      content: <ReactionPanel hero={hero} enabled={canAct} queued={autoQueue} onSet={setReaction} />,
    },
    {
      id: "orders" as const,
      label: "隊友指令",
      badge: hasOrders(response.orders) ? "●" : "",
      content: (
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
      ),
    },
    { id: "legend" as const, label: "圖例", content: <Legend entries={legend} /> },
  ];

  return (
    <div className={`battle-screen${sideCollapsed ? " side-collapsed" : ""}${narrow ? " narrow" : ""}`}>
      <BattleTopBar
        turnBar={<TurnBar view={shown} names={names} acting={acting} />}
        tools={tools}
        open={popup}
        onToggle={(id) => setPopup((cur) => togglePopup(cur, id))}
        exit={exitLabel !== undefined && !ended ? { label: exitLabel, onExit } : null}
        save={runMode !== undefined && !ended ? { busy, note: saveNote, onSave: () => void saveRun() } : null}
      />
      <div className="battle-board" ref={boardRef}>
        <BattleCanvas
          model={model}
          highlights={highlights}
          scale={scale}
          onTileClick={onTileClick}
          onTileHover={onTileHover}
          onCancel={cancel}
          rendererRef={rendererRef}
        >
          {hover !== null && (hoverUnit !== null || hoverTexts.length > 0) && (
            <div className="unit-float" style={cardPlacement(hover, model, scale)}>
              {hoverUnit !== null && (
                <UnitInfo unit={hoverUnit} names={names} heroId={heroId} skills={skillNames} view={view} />
              )}
              {hoverTexts.length > 0 && (
                <ul className="panel telegraph-hover">
                  {hoverTexts.map((t, i) => (
                    <li key={`${i}:${t}`}>{t}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </BattleCanvas>
        {banner && <div className="battle-banner">戰鬥開始</div>}
        <div className="board-toasts">
          <ErrorBanner message={error} onClose={() => setError(null)} />
          <NoticeBanner message={hint} onClose={closeHint} />
          {runMode !== undefined && shownHero?.downed === true && (
            <div className="hero-downed-notice" role="status">
              主角倒下，隊友繼續作戰
            </div>
          )}
        </div>
        <ModePanel
          enabled={canAct || copying}
          mode={mode}
          hurlPick={hurlPick}
          onHurlReset={() => setHurlPick(null)}
          preview={preview}
          view={view}
          interactOptions={response.interact_options}
          names={liveNames}
          legend={legend}
          orderHint={orderPick !== null && canOrder ? orderButton(orderPick).hint : null}
          onProtectHero={
            orderPick === "protect" && canOrder
              ? () => issueOrders(withOrder(response.orders, { kind: "protect", ward: heroId }))
              : null
          }
          cancellable={!copying}
          onCancel={cancel}
          onAction={copying ? decideCopy : act}
          onPreviewAction={setPanelPreview}
        />
      </div>
      <SidePanel
        collapsed={sideCollapsed}
        onToggle={toggleSide}
        telegraph={<TelegraphPanel telegraph={response.telegraph} marks={marks} hoverTexts={hoverTexts} />}
        log={<BattleLog lines={lines} />}
      />
      <div className="battle-bottom">
        <div className="battle-hero">
          <Hud view={shown} hero={shownHero} skills={skillNames} compact={narrow} />
        </div>
        <SkillBar
          basic={copying ? [] : basic.filter((m) => m.kind !== "defend")}
          buttons={copying ? [] : buttons}
          cards={cards}
          selectedKey={mode?.key ?? null}
          enabled={canAct}
          hint={actionHintText({
            copying,
            canAct,
            ended,
            moveCount: classified.moves.size,
            attackCount: classified.attacks.size,
          })}
          onPickMode={pickMode}
          onSelect={pickSkill}
          onBlocked={(b) => setHint(blockedMessage(b))}
        />
        <div className="battle-turn">
          {ended ? (
            <EndPanel response={response} onRestart={onExit} restartLabel={exitLabel} />
          ) : (
            <TurnControls
              enabled={canAct}
              endTurn={copying ? null : classified.endTurn}
              defend={copying ? null : defendMode}
              selectedKey={mode?.key ?? null}
              fallback={copying ? [] : fallback}
              onPickMode={pickMode}
              onAction={act}
              speed={<SpeedControl speed={speed} playing={playing} onSpeed={setSpeed} onSkipNow={skipNow} />}
            />
          )}
        </div>
      </div>
      {followPaused && response.pending !== null && (
        <FollowupDialog
          skillName={copyName}
          optionCount={(response.followup_options ?? []).length}
          enabled={!busy}
          onCancel={() => decideCopy(null)}
        />
      )}
      {copyPaused && response.pending !== null && (
        <CopyDialog
          pending={response.pending}
          skillName={copyName}
          optionCount={response.copy_options.length}
          enabled={!busy}
          onCancel={() => decideCopy(null)}
        />
      )}
      {response.awaiting === "decision" && response.pending !== null && !busy && !copying && (
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
