// 畫布動畫的逐格迴圈（Phase 6F-ART1b：大世界圖浮島漂浮）。
// 只在面板打開（元件掛著）、畫布有尺寸、使用者沒有開 prefers-reduced-motion 時跑；停的時候取消 requestAnimationFrame。
import { reducedMotion, subscribeMotion } from "../ui/motionPrefs";

export interface FrameClock {
  request(cb: (t: number) => void): number;
  cancel(id: number): void;
}

/** 瀏覽器的 requestAnimationFrame（沒有就是 null，例如 SSR、測試）。 */
export function browserClock(): FrameClock | null {
  if (typeof window === "undefined" || typeof window.requestAnimationFrame !== "function") return null;
  return { request: (cb) => window.requestAnimationFrame(cb), cancel: (id) => window.cancelAnimationFrame(id) };
}

/** 開始逐格呼叫 `draw(t)`；回傳停止函式（停了之後不會再要下一格）。 */
export function startFrameLoop(draw: (t: number) => void, clock: FrameClock): () => void {
  let stopped = false;
  let id = 0;
  const tick = (t: number): void => {
    if (stopped) return;
    draw(t);
    if (!stopped) id = clock.request(tick);
  };
  id = clock.request(tick);
  return () => {
    stopped = true;
    clock.cancel(id);
  };
}

/** 要不要跑動畫：畫法要求動畫、沒有減少動態、畫布有尺寸。 */
export const shouldAnimate = (animated: boolean, reducedMotion: boolean, pw: number, ph: number): boolean => animated && !reducedMotion && pw > 0 && ph > 0;

// 6H-1：減少動態改看遊戲內的開關（跟系統／開／關，`ui/motionPrefs.ts`）的有效值；舊的呼叫點照舊從這裡匯入。
/** 是否減少動態（遊戲內設定 ＋ 系統 `prefers-reduced-motion` 的有效值）。 */
export const prefersReducedMotion = (): boolean => reducedMotion();

/** 訂閱減少動態有效值的變化（遊戲內設定或系統設定）。 */
export function subscribeReducedMotion(cb: () => void): () => void {
  return subscribeMotion(cb);
}
