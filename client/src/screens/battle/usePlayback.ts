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
import { loadShake, saveShake } from "../../battle/vfxPrefs";
import type { BattleRenderer } from "../../render/BattleRenderer";
import { needsLogRestore } from "../../run/flow";
import { loadSpeed, saveSpeed } from "../../ui/SpeedControl";

const BANNER_MS = 1000;

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
  useEffect(() => {
    shakeRef.current = shake;
    saveShake(shake);
  }, [shake]);

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
        case "vfx":
          // 技能特效：蓄力與飛行物先播，等到命中才更新畫面與浮動數字（略過時不播）
          if (skip()) break;
          rendererRef.current?.playVfx(op.vfx, op.impactMs, shakeRef.current);
          if (op.vfx.leadMs > 0) await sleep(op.vfx.leadMs);
          break;
        case "view":
          flushSync(() => setShown(op.view));
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
        const plan = playbackPlan(res, heroId, speedRef.current, cardsRef.current);
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
