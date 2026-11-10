// 戰鬥畫面的「播放與送出」（由 BattleScreen 抽出，Phase 3T-7）。
// 每次送出動作或決定：鎖住操作 → 收到回應 → 先畫 `initial_view`，再依 `steps` 一步一步播放
// （標示行動者 → 移動動畫 → 該步的 `view` → 紀錄 → 停頓）→ 最後以 `res.view` 為準。
// 也負責：開場的第一次播放（「戰鬥開始」橫幅）、接續戰鬥時還原戰鬥紀錄、播放速度與震動設定的存檔。

import { useCallback, useEffect, useRef, useState, type MutableRefObject } from "react";
import { flushSync } from "react-dom";
import { api, ApiError } from "../../api/client";
import type { BattleResponse, BattleView, SkillCard } from "../../api/types";
import { frameOps, playbackPlan, remainingLines, type PlayOp, type PlaySpeed } from "../../battle/playback";
import type { LogLine } from "../../battle/log";
import { logLines } from "../../battle/log";
import { unitNames } from "../../battle/units";
import { hitHoldMs, slowTailMs } from "../../battle/impact";
import { prefersReducedMotion } from "../../world/frameLoop";
import { attackFamilyInView, creatureStrikeInView, weaponClassInView } from "../../battle/viewGrip";
import { loadShake, saveShake } from "../../battle/vfxPrefs";
import type { BattleRenderer } from "../../render/BattleRenderer";
import { needsLogRestore } from "../../run/flow";
import { loadSpeed, saveSpeed } from "../../ui/SpeedControl";
import { cueRealMs, moveCues, walkCues, type SfxCue } from "../../audio/battleSfx";
import { audio } from "../../audio";
import { battleScheduler } from "../../audio/scene";
import type { StepVfx } from "../../battle/vfx";

/** AU-3：把一步的音效交給排程（效果時鐘 → 實際時間：停頓、最後一擊放慢和畫面對齊；減少動態時照原本）。 */
function scheduleSfx(cues: readonly SfxCue[] | undefined, vfx: StepVfx | null = null): void {
  if (cues === undefined || cues.length === 0) return;
  const reduced = prefersReducedMotion();
  battleScheduler().start(cues.map((c) => ({ id: c.id, realMs: cueRealMs(c.atMs, vfx, reduced), key: c.key, count: c.count })));
}

const BANNER_MS = 1000;
/** 按住空白鍵時的暫時加速倍率（6N-1）。 */
export const HOLD_BOOST = 2;

export function errorText(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  return e instanceof Error ? e.message : String(e);
}

type Cards = Readonly<Record<string, SkillCard | undefined>>;

export interface Playback {
  response: BattleResponse;
  /** 目前畫面上顯示的視圖（播放中是逐步的中間狀態，結束後等於 `response.view`）。 */
  shown: BattleView;
  /** 逐步播放時指定的行動者；`undefined` ＝ 用視圖的 `active_unit`。 */
  acting: string | undefined;
  lines: LogLine[];
  busy: boolean;
  playing: boolean;
  banner: boolean;
  error: string | null;
  setError(e: string | null): void;
  speed: PlaySpeed;
  setSpeed(s: PlaySpeed): void;
  /** 技能特效的畫面震動（Phase 3-12，「版面」面板可關閉）。 */
  shake: boolean;
  setShake(on: boolean): void;
  rendererRef: MutableRefObject<BattleRenderer | null>;
  skipNow(): void;
  /** 送出一個會得到新回應的呼叫並播放結果；忙碌中忽略。 */
  run(call: () => Promise<BattleResponse>): Promise<void>;
}

/**
 * @param cardsRef 主角技能卡（播放特效要用；由呼叫端每次繪製後更新）
 * @param resetSelectionRef 送出時要取消選取（`BattleScreen` 的選取狀態在這個 hook 之後才宣告，所以用 ref 傳進來）
 */
export function usePlayback(
  initial: BattleResponse,
  cardsRef: MutableRefObject<Cards>,
  resetSelectionRef: MutableRefObject<() => void>,
): Playback {
  const battleId = initial.battle_id;
  const heroId = initial.hero_id;
  const [response, setResponse] = useState(initial);
  const [shown, setShown] = useState<BattleView>(initial.initial_view);
  const [acting, setActing] = useState<string | undefined>(undefined);
  const [lines, setLines] = useState<LogLine[]>([]);
  const [busy, setBusy] = useState(true);
  const [playing, setPlaying] = useState(false);
  const [banner, setBanner] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [speed, setSpeed] = useState<PlaySpeed>(loadSpeed);
  const [shake, setShake] = useState<boolean>(loadShake);
  const shakeRef = useRef(shake);
  /** 6H-1：最後一擊放慢在命中點之後的實際時間（勝利片段等它播完）。 */
  const tailRef = useRef(0);
  const busyRef = useRef(true);
  const speedRef = useRef(speed);
  const skipRef = useRef(false);
  const wakeRef = useRef<(() => void) | null>(null);
  const startedRef = useRef(false);
  const rendererRef = useRef<BattleRenderer | null>(null);
  // 這個回合跑過（衝刺）的單位：之後的步行用跑步片段（6M-3）；跨回應保留，由事件更新
  const runningRef = useRef(new Set<string>());

  useEffect(() => {
    speedRef.current = speed;
    saveSpeed(speed);
  }, [speed]);
  useEffect(() => {
    shakeRef.current = shake;
    saveShake(shake);
  }, [shake]);

  // 按住空白鍵暫時 2 倍速（6N-1）：畫布動畫由 ticker 加速，等待的時間照剩下的部分重算
  const boostRef = useRef(1);
  const retimeRef = useRef<(() => void) | null>(null);
  const sleep = useCallback(
    (ms: number) =>
      new Promise<void>((resolve) => {
        let left = ms;
        let rate = boostRef.current;
        let since = performance.now();
        let timer = window.setTimeout(done, left / rate);
        function done() {
          window.clearTimeout(timer);
          wakeRef.current = null;
          retimeRef.current = null;
          resolve();
        }
        retimeRef.current = () => {
          const now = performance.now();
          left -= (now - since) * rate;
          since = now;
          rate = boostRef.current;
          window.clearTimeout(timer);
          timer = window.setTimeout(done, Math.max(0, left / rate));
        };
        wakeRef.current = done;
      }),
    [],
  );

  useEffect(() => {
    const setBoost = (rate: number) => {
      if (boostRef.current === rate) return;
      boostRef.current = rate;
      rendererRef.current?.setBoost(rate);
      battleScheduler().setBoost(rate); // AU-3：聲音只改排程，不改 playbackRate（不變調）
      retimeRef.current?.();
    };
    const typing = (t: EventTarget | null) => t instanceof HTMLElement && (t.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName));
    const down = (e: KeyboardEvent) => {
      if (e.key !== " " || typing(e.target)) return;
      e.preventDefault();
      setBoost(HOLD_BOOST);
    };
    const up = (e: KeyboardEvent) => {
      if (e.key === " ") setBoost(1);
    };
    const reset = () => setBoost(1);
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    window.addEventListener("blur", reset);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
      window.removeEventListener("blur", reset);
      reset();
    };
  }, []);

  const skipNow = useCallback(() => {
    skipRef.current = true;
    battleScheduler().cancelAll(); // AU-3：跳過時不補放
    wakeRef.current?.();
  }, []);
  /** AU-3：這一格開始前的畫面（走路的腳步聲照它的地表）。 */
  const beforeRef = useRef<BattleView>(initial.initial_view);
  // AU-3：離開戰鬥畫面時，排好但還沒響的戰鬥音效一起取消
  useEffect(() => () => battleScheduler().cancelAll(), []);

  const runOp = useCallback(
    async (op: PlayOp) => {
      const skip = () => skipRef.current || speedRef.current === "skip";
      switch (op.op) {
        case "mark":
          flushSync(() => setActing(op.unitId ?? undefined));
          break;
        case "move":
          if (!skip()) scheduleSfx(moveCues(op.anim, beforeRef.current.map_id));
          await rendererRef.current?.animate([op.anim], skip);
          break;
        case "walk":
          // 一格一格走（6A-4d）：特殊地表的停頓與效果在畫布裡播；AU-3：每一格依地表踏一步
          if (!skip()) scheduleSfx(walkCues(op.walk, beforeRef.current));
          await rendererRef.current?.animateWalk(op.walk, skip);
          break;
        case "vfx":
          // 技能特效：蓄力與飛行物先播，等到命中才更新畫面與浮動數字（略過時不播）
          if (skip()) break;
          {
            // 6N-1：先播身體片段（起手 → 原語），特效從出招那一刻的作用端發出
            const origins = op.skill === undefined ? undefined : rendererRef.current?.playSkill(op.skill);
            rendererRef.current?.playVfx(op.vfx, op.impactMs, shakeRef.current, origins);
            // AU-3：起手、出招、命中、結果、原語、狀態、地表的音效，和 playVfx 同一個原點
            scheduleSfx(op.sfx, op.vfx);
          }
          // 6N-5：命中時的停頓（暴擊、擊殺、格擋）讓畫布時間停住，畫面等停頓結束才以結果重畫
          // 6H-1：停頓照扣血比例分級；最後一擊放慢時多等命中點以前放慢的部分（減少動態時都沒有）
          {
            const reduced = prefersReducedMotion();
            tailRef.current = reduced ? 0 : slowTailMs(op.vfx);
            if (op.vfx.leadMs > 0) await sleep(op.vfx.leadMs + hitHoldMs(op.vfx, reduced));
          }
          break;
        case "victory":
          // 6N-5：我方勝利：全隊舉手或收刀、浮出「勝利」，播完才顯示結束面板
          if (skip()) break;
          // 6H-1：最後一擊放慢的後半段（倒下片段）播完才接勝利
          if (tailRef.current > 0) await sleep(tailRef.current);
          tailRef.current = 0;
          rendererRef.current?.playVictory(op.victory);
          await sleep(op.victory.ms);
          break;
        case "view":
          flushSync(() => setShown(op.view));
          if (!skip()) scheduleSfx(op.sfx);
          break;
        case "lift":
          rendererRef.current?.playLift(op.shifts, op.durationMs, shakeRef.current, skip);
          break;
        case "feedback":
          rendererRef.current?.playFeedback(op.items, op.durationMs);
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
        // 6R-F：武器類別、普攻變體表列照每一步開始前的畫面算（純函式），不讀繪製器
        const plan = playbackPlan(res, heroId, speedRef.current, cardsRef.current, runningRef.current, weaponClassInView, attackFamilyInView, creatureStrikeInView, prefersReducedMotion());
        flushSync(() => {
          setActing(undefined);
          setShown(plan.initialView);
        });
        if (withBanner) {
          setBanner(true);
          // 撤離與守點多停一會兒，讓玩家讀完本場目標
          const longer = plan.initialView.objective.kind !== "eliminate";
          if (speedRef.current !== "skip") await sleep(longer ? BANNER_MS * 2 : BANNER_MS);
          setBanner(false);
        }
        let done = 0;
        beforeRef.current = plan.initialView;
        for (const frame of plan.frames) {
          if (skipRef.current) break;
          for (const op of frameOps(frame)) await runOp(op);
          beforeRef.current = frame.view;
          done += 1;
        }
        if (done < plan.frames.length) setLines((prev) => [...prev, ...remainingLines(plan, done)]);
        // AU-3：AI 行動完、輪回我方時一聲（畫面同時有字，不只靠聲音）
        if (!res.view.ended && res.view.active_unit === heroId && res.initial_view.active_unit !== heroId) audio.play("sys_my_turn");
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
    [cardsRef, heroId, runOp, sleep],
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
      resetSelectionRef.current();
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
    [battleId, play, resetSelectionRef],
  );

  return {
    response,
    shown,
    acting,
    lines,
    busy,
    playing,
    banner,
    error,
    setError,
    speed,
    setSpeed,
    shake,
    setShake,
    rendererRef,
    skipNow,
    run,
  };
}
