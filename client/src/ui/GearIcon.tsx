// 裝備圖示（Phase 3G-G5a）：畫在 canvas 上，圖示由 render/gearIcon.ts 產生並快取。
// QI-1b（D3）：直接畫在顯示尺寸（畫布寬高 ＝ iconCanvasPx(顯示 CSS px)），CSS 不再縮放畫布（縮放會讓瀏覽器重新取樣、1px 外框發糊）。
// `fit`：身上裝備格這種跟著面板寬度變的格子——量外層格子的內容寬，取 `fitIconPx`（整數 CSS px、最大 48），尺寸變了就重畫。
// QI-2c：`fit` 的圖示在格子裡置中後，左上角可能落在小數位置（瀏覽器重新取樣、1px 外框發糊）；量出位置後用 `position: relative` 挪
// `pixelSnapNudge`（`Math.round(x × dpr) / dpr − x`）對齊裝置像素（美術 PM QI-1b 驗收）。`__layoutSmoke.icons()` 檢查 `canvas.gear-fit` 的位置。
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { fitIconPx, gearIconCanvas, pixelSnapNudge, type GearLook } from "../render/gearIcon";
import { iconCanvasPx } from "../render/weaponIcon";

interface Props {
  look: GearLook | null | undefined;
  /** 欄位名（`main_hand`…）：物品沒有 `kind` 時用來選預設造型。 */
  slot?: string;
  /** 顯示邊長（整數 CSS px：32、40、42、48、64…）；`fit` 時是量到之前的初始值。 */
  size?: number;
  /** 量外層格子的內容寬決定尺寸（身上裝備格）。 */
  fit?: boolean;
  /** 無障礙名稱（`aria-label`）；不是原生 tooltip（要說明請用 `Hint`／`PartTip`）。 */
  label?: string;
}

/** 外層格子的內容寬（扣掉邊框與內距；CSS px，可能是小數）。 */
function contentWidth(el: HTMLElement): number {
  const cs = getComputedStyle(el);
  const n = (v: string): number => Number.parseFloat(v) || 0;
  return el.getBoundingClientRect().width - n(cs.borderLeftWidth) - n(cs.borderRightWidth) - n(cs.paddingLeft) - n(cs.paddingRight);
}

interface Nudge {
  x: number;
  y: number;
}
const NO_NUDGE: Nudge = { x: 0, y: 0 };

export function GearIcon({ look, slot, size = 32, fit = false, label }: Props) {
  const ref = useRef<HTMLCanvasElement>(null);
  const [px, setPx] = useState(size);
  const [nudge, setNudge] = useState<Nudge>(NO_NUDGE);
  useLayoutEffect(() => {
    if (!fit) {
      setPx(size);
      return undefined;
    }
    const box = ref.current?.parentElement;
    if (box == null) return undefined;
    const measure = (): void => setPx(fitIconPx(contentWidth(box)));
    measure();
    if (typeof ResizeObserver === "undefined") return undefined;
    const ro = new ResizeObserver(measure);
    ro.observe(box);
    return () => ro.disconnect();
  }, [fit, size]);
  // fit：置中後的左上角對齊裝置像素（量「沒挪之前」的位置＝目前位置減掉已挪的量）
  useLayoutEffect(() => {
    if (!fit) {
      setNudge(NO_NUDGE);
      return undefined;
    }
    const cv = ref.current;
    if (cv == null) return undefined;
    const align = (): void => {
      const r = cv.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      setNudge((prev) => {
        const next = { x: pixelSnapNudge(r.left - prev.x, dpr), y: pixelSnapNudge(r.top - prev.y, dpr) };
        return Math.abs(next.x - prev.x) < 1e-4 && Math.abs(next.y - prev.y) < 1e-4 ? prev : next;
      });
    };
    align();
    window.addEventListener("resize", align);
    const box = cv.parentElement;
    const ro = typeof ResizeObserver === "undefined" || box == null ? null : new ResizeObserver(align);
    if (ro !== null && box != null) ro.observe(box);
    return () => {
      window.removeEventListener("resize", align);
      ro?.disconnect();
    };
  }, [fit, px]);
  useEffect(() => {
    const target = ref.current;
    const ctx = target?.getContext("2d");
    const art = gearIconCanvas(look, px, slot);
    if (target == null || ctx == null || art === null) return;
    ctx.clearRect(0, 0, target.width, target.height);
    ctx.drawImage(art, 0, 0);
  }, [look, slot, px]);
  const cv = iconCanvasPx(px);
  const style = fit ? { width: px, height: px, position: "relative" as const, left: nudge.x, top: nudge.y } : { width: px, height: px };
  return <canvas ref={ref} className={fit ? "gear-icon gear-fit" : "gear-icon"} width={cv} height={cv} style={style} aria-label={label} role={label === undefined ? undefined : "img"} />;
}
