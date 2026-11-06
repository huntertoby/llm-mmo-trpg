// 等待動畫元件（RT-3；docs/archive/art/等待動畫.md 第 5 節）：C 羽毛筆羊皮紙，四個場合各一種畫法（`render/waitArt.ts`）。
// - canvas＋requestAnimationFrame，元件卸載就停；減少動態時只畫一次靜態版（不跑 rAF），句子照常換但不淡入淡出；
// - 墨色、封蠟、點綴讀 RT-1 的區域主題（`region` 沒給＝目前畫面的主題；拿不到區域＝hub）；
// - 時間只用來算相位（開發用 `?anim=0.1` 會放慢），圖樣照請求編號雜湊（確定性，不用 Math.random）；
// - 完成：技能生成卡面淡入 0.3 秒、回顧闔書、判定停住、聊天直接換成文字（由呼叫端拿掉元件）；
// - 失敗：停住、變灰，句子換成「說書人停下了筆，再試一次？」，有 `onRetry` 時加重試鈕；
// - 等待聲：還在等時照場合放（`audio/waitSounds.ts`，0.7 秒規則；NPC 聊天不出聲）。
// RT-3b：出現時、失敗時把自己（加上 `revealUntil`，例如「擲骰」那一列）捲進最近的捲動區（`scrollReveal.ts`），
// 重試鈕不會被切在畫面外；NPC 聊天的「完成」＝泡泡拿掉、直接顯示回覆文字（`doneText`）。
import { useEffect, useRef, useState, useSyncExternalStore, type RefObject } from "react";
import { useWaitSound, WAIT_SOUND_DELAY_MS } from "../audio/waitSounds";
import { devAnimFactor } from "../battle/playback";
import { drawWait, waitPalette, WAIT_DONE_MS, WAIT_SIZE, type WaitStatus } from "../render/waitArt";
import { reducedMotion, subscribeMotion } from "./motionPrefs";
import { regionThemeFor, useCurrentTheme } from "./regionTheme";
import { revealInScroller } from "./scrollReveal";
import { WAIT_NARRATION, waitLine, waitSeed, type WaitSceneId } from "./waitNarration";
import "./waitScene.css";

const ANIM_SLOW = devAnimFactor(typeof window === "undefined" ? "" : window.location.search);

/** 句子多久重算一次（毫秒；輪替本身是 4 秒）。 */
const LINE_TICK_MS = 250;

export function useReducedMotion(): boolean {
  return useSyncExternalStore(subscribeMotion, reducedMotion, () => false);
}

interface Props {
  scene: WaitSceneId;
  /** 請求編號（挑第一句與技能圖樣；同一個請求每次一樣）。 */
  requestId: string;
  /** NPC 的名字（`npc` 的短句用）。 */
  name?: string;
  /** 區域 ID；省略＝目前畫面的區域主題。 */
  region?: string | null;
  status?: WaitStatus;
  /** 技能圖樣的淡色（技能的元素色）。 */
  tint?: string | null;
  onRetry?: () => void;
  /** 等待聲的延遲（毫秒）：元件比等待晚出現時扣掉已經等過的時間（預設 0.7 秒）。 */
  soundDelayMs?: number;
  /** 開發頁：固定畫某一刻（毫秒；不跑 rAF）。 */
  frozenT?: number;
  /** 開發頁：固定完成後過了多久（毫秒）。 */
  frozenDoneT?: number;
  /** 開發頁：固定減少動態（省略＝照設定）。 */
  reduced?: boolean;
  /** 開發頁：固定句子的時間（毫秒）。 */
  lineElapsed?: number;
  /** NPC 聊天完成時直接顯示的回覆（泡泡拿掉）；正式畫面由呼叫端換成對話紀錄，開發頁用這個。 */
  doneText?: string;
  /** 出現、失敗時捲進可視範圍（預設開；開發頁關掉）。 */
  reveal?: boolean;
  /** 捲動時一起帶進可視範圍的元素（例如判定的「擲骰」那一列）。 */
  revealUntil?: RefObject<HTMLElement | null>;
  testId?: string;
}

/** NPC 聊天完成＝泡泡消失、直接是文字（RT-3b 必修 5）。 */
export function npcDoneShowsText(scene: WaitSceneId, status: WaitStatus): boolean {
  return scene === "npc" && status === "done";
}

export function WaitScene({ scene, requestId, name, region, status = "wait", tint, onRetry, soundDelayMs = WAIT_SOUND_DELAY_MS, frozenT, frozenDoneT, reduced, lineElapsed, doneText, reveal = true, revealUntil, testId = "wait-scene" }: Props) {
  const prefReduced = useReducedMotion();
  const still = reduced ?? prefReduced;
  const current = useCurrentTheme();
  const theme = region === undefined ? current : regionThemeFor(region);
  const palette = waitPalette(theme, { grey: status === "fail", tint });
  const seed = waitSeed(requestId);
  const size = WAIT_SIZE[scene];
  const canvas = useRef<HTMLCanvasElement | null>(null);
  const startedAt = useRef<number>(typeof performance === "undefined" ? 0 : performance.now());
  /** 停住的那一刻（動畫時間）：完成或失敗時記下。 */
  const stopT = useRef<number | null>(null);
  const stopAt = useRef<number>(0);
  const [elapsed, setElapsed] = useState(0);
  const root = useRef<HTMLDivElement | null>(null);
  const textOnly = npcDoneShowsText(scene, status);

  // 出現時、狀態改變（失敗＝多了重試鈕）時捲進可視範圍；等版面排好（下一格）再量
  useEffect(() => {
    if (!reveal || status === "done") return undefined;
    const raf = window.requestAnimationFrame(() => {
      if (root.current !== null) revealInScroller(root.current, revealUntil?.current ?? null);
    });
    return () => window.cancelAnimationFrame(raf);
  }, [reveal, status, revealUntil]);

  useWaitSound(scene, status === "wait" && frozenT === undefined, soundDelayMs);

  // 句子：真實時間（不跟著 ?anim= 放慢）
  useEffect(() => {
    if (lineElapsed !== undefined || status !== "wait") return undefined;
    const timer = window.setInterval(() => setElapsed(performance.now() - startedAt.current), LINE_TICK_MS);
    return () => window.clearInterval(timer);
  }, [lineElapsed, status]);

  // 畫布：rAF 迴圈（減少動態、固定時間時只畫一次）
  useEffect(() => {
    const el = canvas.current;
    if (textOnly) return undefined;
    const ctx = el?.getContext("2d") ?? null;
    if (el === null || ctx === null) return undefined;
    const dpr = Math.max(1, Math.min(3, window.devicePixelRatio || 1));
    el.width = Math.round(size.w * dpr);
    el.height = Math.round(size.h * dpr);
    const now = (): number => (performance.now() - startedAt.current) / ANIM_SLOW;
    if (status !== "wait" && stopT.current === null) {
      stopT.current = now();
      stopAt.current = now();
    }
    if (status === "wait") stopT.current = null;
    let raf = 0;
    const paint = (): boolean => {
      const t = frozenT ?? stopT.current ?? now();
      const doneT = frozenDoneT ?? (status === "done" ? now() - stopAt.current : undefined);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, size.w, size.h);
      drawWait(ctx, { scene, t, seed, palette, reduced: still, status, doneT });
      // 還要不要畫下一格：等待中、或完成的收尾還沒結束
      if (frozenT !== undefined || still || status === "fail") return false;
      return status === "wait" || (doneT ?? 0) < WAIT_DONE_MS;
    };
    const loop = (): void => {
      if (paint()) raf = window.requestAnimationFrame(loop);
    };
    loop();
    return () => window.cancelAnimationFrame(raf);
    // palette 由這幾個值決定；物件每次重算，不放進依賴
  }, [scene, seed, status, still, frozenT, frozenDoneT, theme.id, tint, size.w, size.h, textOnly]);

  const line = waitLine(scene, lineElapsed ?? elapsed, requestId, { name, failed: status === "fail" });
  const done = status === "done";
  if (textOnly)
    return (
      <div ref={root} className={`wait-scene wait-${scene} wait-done-text`} data-testid={testId} data-scene={scene} data-status={status} data-region={theme.id} role="status" aria-live="polite">
        <span className="wait-reply" data-testid={`${testId}-reply`}>
          {doneText ?? ""}
        </span>
      </div>
    );
  return (
    <div ref={root} className={`wait-scene wait-${scene}${still ? " still" : ""}`} data-testid={testId} data-scene={scene} data-status={status} data-region={theme.id} role="status" aria-live="polite">
      <canvas ref={canvas} className="wait-canvas" style={{ width: size.w, height: size.h }} aria-hidden="true" data-testid={`${testId}-canvas`} />
      {!done && (
        <div className="wait-text">
          <span key={`${line.slot}:${status}`} className={`wait-line${line.long ? " long" : ""}`} data-testid={`${testId}-line`} data-slot={line.slot}>
            {line.text}
          </span>
          {status === "fail" && onRetry !== undefined && (
            <button type="button" className="small-button wait-retry" onClick={onRetry} data-testid={`${testId}-retry`}>
              再試一次
            </button>
          )}
        </div>
      )}
    </div>
  );
}

/** 輪替的時間（測試、開發頁用）。 */
export const WAIT_ROTATE_MS = WAIT_NARRATION.rotate_ms;
