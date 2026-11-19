// AR-AP2（美術 PM 裁定 4，docs/art/AP-2-美術.md 第 9 節）：AP 列預支記號（橘菱形、下回合的紅斜線，`.stat-pip.ap.fresh`）的 200 ms 淡入
// 延後到預支演出的 215 ms（菱形到胸口）才開始。播放器在畫面更新前設 CSS 變數 `--ap-fresh-delay`，淡入播完就清掉（之後重新掛上的圓點照舊不延後）。

/** CSS 變數名（`status-card.css` 的 `.stat-pip.ap.fresh` 讀它）。 */
export const AP_FRESH_DELAY_VAR = "--ap-fresh-delay";
/** 淡入本身的長度（`status-card.css` 的 `ap-borrow-in 0.2s`，不動）。 */
export const AP_FRESH_FADE_MS = 200;

let timer: ReturnType<typeof setTimeout> | null = null;

/** 這次畫面更新的預支記號延後 `ms` 毫秒才淡入（0＝照舊）；`root` 給測試用。 */
export function delayApFade(ms: number, root: { style: { setProperty(k: string, v: string): void; removeProperty(k: string): void } } | null = typeof document === "undefined" ? null : document.documentElement): void {
  if (root === null) return;
  if (timer !== null) clearTimeout(timer);
  timer = null;
  if (ms <= 0) {
    root.style.removeProperty(AP_FRESH_DELAY_VAR);
    return;
  }
  root.style.setProperty(AP_FRESH_DELAY_VAR, `${Math.round(ms)}ms`);
  timer = setTimeout(() => {
    root.style.removeProperty(AP_FRESH_DELAY_VAR);
    timer = null;
  }, ms + AP_FRESH_FADE_MS + 50);
}
