// RT-3b（docs/archive/art/RT-3檢查.md 必修 1、2）：等待區出現、失敗出現重試鈕時，把它捲進可視範圍。
// 只捲最近的捲動區（彈窗的 `.ui-popup-body`），不用 `scrollIntoView`（它會連外層 overflow: hidden 的舞台一起捲）。
// 上下各讓出漸隱遮罩的高度（遮罩 32～48px），重試鈕不會被下緣漸隱切掉一半。

/** 捲動區上下要讓出的距離（CSS 像素）：比下緣漸隱（32px）多一點。 */
export const REVEAL_MARGIN = 40;

export interface Span {
  top: number;
  bottom: number;
}

/**
 * 要捲多少（正＝往下捲）才能讓 `target` 落在 `view` 裡、上下各留 `margin`。
 * - 已經在裡面：0；
 * - 比可視範圍高：對齊上緣（先看到開頭，例如沙漏）。
 */
export function revealDelta(view: Span, target: Span, margin: number = REVEAL_MARGIN): number {
  const top = view.top + margin;
  const bottom = view.bottom - margin;
  if (target.bottom - target.top > bottom - top) return target.top - top;
  if (target.top < top) return target.top - top;
  if (target.bottom > bottom) return target.bottom - bottom;
  return 0;
}

/**
 * PNL-4：和 `revealDelta` 一樣讓 `target` 落在 `view` 裡，但比可視範圍高時**對齊下緣**（先看到最下面的操作列，例如「擲骰」），
 * 上緣只讓 `top`（不用讓出漸隱的 40）。放得下時整段都看得到。
 */
export function revealBottomDelta(view: Span, target: Span, top = 8, margin: number = REVEAL_MARGIN): number {
  const vTop = view.top + top;
  const vBottom = view.bottom - margin;
  if (target.bottom - target.top > vBottom - vTop) return target.bottom - vBottom;
  if (target.top < vTop) return target.top - vTop;
  if (target.bottom > vBottom) return target.bottom - vBottom;
  return 0;
}

/** 只捲最近的一層捲動區，照 `revealBottomDelta` 把 `el`～`until` 的下緣捲進來；回傳捲了多少。 */
export function revealBottomInScroller(el: Element, until: Element | null = null): number {
  const scroller = scrollerOf(el);
  if (scroller === null) return 0;
  const v = scroller.getBoundingClientRect();
  const a = el.getBoundingClientRect();
  const b = until?.getBoundingClientRect();
  const d = revealBottomDelta({ top: v.top, bottom: v.bottom }, { top: a.top, bottom: Math.max(a.bottom, b?.bottom ?? a.bottom) });
  if (d === 0) return 0;
  const before = scroller.scrollTop;
  scroller.scrollTop = before + d;
  return scroller.scrollTop - before;
}

/** 最近的捲動區（`overflow-y` 是 auto／scroll 的祖先）。 */
export function scrollerOf(el: Element): HTMLElement | null {
  for (let p = el.parentElement; p !== null; p = p.parentElement) {
    const oy = getComputedStyle(p).overflowY;
    if (oy === "auto" || oy === "scroll") return p;
  }
  return null;
}

/** 最多往外找幾層捲動區（對話紀錄 → 面板 → …）。 */
const MAX_SCROLLERS = 4;

/**
 * 把 `el`（加上 `until` 的下緣，例如「擲骰」那一列）捲進捲動區；由內往外每一層捲動區都捲一次
 * （NPC 的對話紀錄本身是捲動區但沒有超出，真正要捲的是外面的面板）。回傳各層捲了多少的總和。
 */
export function revealInScroller(el: Element, until: Element | null = null): number {
  let total = 0;
  let from: Element = el;
  for (let i = 0; i < MAX_SCROLLERS; i++) {
    const scroller = scrollerOf(from);
    if (scroller === null) break;
    const v = scroller.getBoundingClientRect();
    const a = el.getBoundingClientRect();
    const b = until?.getBoundingClientRect();
    const target: Span = { top: a.top, bottom: Math.max(a.bottom, b?.bottom ?? a.bottom) };
    const d = revealDelta({ top: v.top, bottom: v.bottom }, target);
    if (d !== 0) {
      const before = scroller.scrollTop;
      scroller.scrollTop = before + d;
      total += scroller.scrollTop - before;
    }
    from = scroller;
  }
  return total;
}
