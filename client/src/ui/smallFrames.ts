// 小框的四角飾件（UI-E1 追加 4；美術 PM 驗收 RT-1：docs/archive/art/RT-1與UI-E2檢查.md 第 5 節第 2 項）：
// 高度 64px 以下的框（任務追蹤只剩一兩行、戰鬥主角卡、功能列等），四角飾件縮成 70%，內容左右各多留 6px，
// 飾件才不會壓到收合鈕「—」、「▸ 詳細」或第一個、最後一個字。
// 做法：一個 ResizeObserver 量每個 `.rt-frame` 的版面高度（offsetHeight，不受 HUD 的 transform 縮放影響），
// 夠小就標 `data-rt-small="true"`（CSS 換成 `--rt-corners-small`），並把左右內距各加 6px（記住原本的值，變大了再還原）。
// 加了內距字可能折行、框變高：為了不來回跳，標上之後要高過 64＋24 才拿掉。
export const SMALL_FRAME_MAX_H = 64;
/** 標上之後的寬限（避免加內距後折行、變高又拿掉、再變矮又標上的來回跳）。 */
export const SMALL_FRAME_SLACK = 24;
export const SMALL_FRAME_PAD = 6;
/** 小框的飾件縮放。 */
export const SMALL_CORNER_SCALE = 0.7;

/**
 * 小框的左右內距下限（CSS 像素）：70% 的飾件離內緣 2px、邊長 12.6px，到 14.6px 為止；內距至少 16px，
 * 四個角的飾件就不會壓到靠邊的按鈕（任務框的「－」、戰鬥卡的「▸ 詳細」）和每行的第一個、最後一個字
 * （docs/archive/art/RT-1與UI-E2檢查.md 第 5 節第 2 項，取代第 3 節只顧第一個字的寫法）。
 */
export const SMALL_FRAME_CLEAR = 16;

/**
 * 這個框現在算不算小框（`marked`＝目前已標成小框）。高度 0（還沒排版、隱藏）不算。
 * `compact`：資訊塊本身就是小框（任務追蹤、戰鬥主角卡，`data-rt-compact`），內容變多變高也照小框處理。
 */
export function nextSmall(height: number, marked: boolean, compact = false): boolean {
  if (compact) return true;
  if (height <= 0) return marked;
  return marked ? height <= SMALL_FRAME_MAX_H + SMALL_FRAME_SLACK : height <= SMALL_FRAME_MAX_H;
}

/** 標成小框時左右內距（CSS 像素）：原本＋6，且至少 16（讓出四角飾件）。 */
export const smallPadding = (base: number): number => Math.max(base + SMALL_FRAME_PAD, SMALL_FRAME_CLEAR);

function px(v: string): number {
  const n = Number.parseFloat(v);
  return Number.isFinite(n) ? n : 0;
}

/** 依目前高度更新一個框的標記與內距。 */
export function updateSmallFrame(el: HTMLElement, win: Window): void {
  const marked = el.dataset.rtSmall === "true";
  const small = nextSmall(el.offsetHeight, marked, el.dataset.rtCompact === "true");
  if (small === marked) return;
  if (small) {
    const cs = win.getComputedStyle(el);
    el.dataset.rtPad = `${el.style.paddingLeft}|${el.style.paddingRight}`;
    el.style.paddingLeft = `${smallPadding(px(cs.paddingLeft))}px`;
    el.style.paddingRight = `${smallPadding(px(cs.paddingRight))}px`;
    el.dataset.rtSmall = "true";
  } else {
    const [left = "", right = ""] = (el.dataset.rtPad ?? "|").split("|");
    el.style.paddingLeft = left;
    el.style.paddingRight = right;
    delete el.dataset.rtPad;
    delete el.dataset.rtSmall;
  }
}

/** 開始看整頁的 `.rt-frame`（新加進來的也看）。沒有 ResizeObserver／MutationObserver 的環境（測試）不做事。 */
export function installSmallFrames(doc: Document): void {
  const win = doc.defaultView;
  if (win === null || typeof win.ResizeObserver === "undefined" || typeof win.MutationObserver === "undefined") return;
  const seen = new WeakSet<Element>();
  const ro = new win.ResizeObserver((entries) => {
    for (const e of entries) if (e.target instanceof win.HTMLElement) updateSmallFrame(e.target, win);
  });
  const watch = (el: Element): void => {
    if (seen.has(el)) return;
    seen.add(el);
    ro.observe(el);
    // HID-1b（四角飾件的舊 FAIL）：ResizeObserver 綁在算繪幀上，背景分頁、隱藏的預覽窗不會觸發，
    // `data-rt-compact` 的框（戰鬥主角卡）就一直標不上小框。這裡先量一次，不等第一次回呼。
    if (el instanceof win.HTMLElement) updateSmallFrame(el, win);
  };
  const scan = (root: Element | Document): void => {
    if (root instanceof win.Element && root.classList.contains("rt-frame")) watch(root);
    root.querySelectorAll(".rt-frame").forEach(watch);
  };
  const mo = new win.MutationObserver((muts) => {
    for (const m of muts) for (const n of m.addedNodes) if (n instanceof win.Element) scan(n);
  });
  const start = (): void => {
    scan(doc);
    mo.observe(doc.body, { childList: true, subtree: true });
  };
  if (doc.body === null) doc.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
}
