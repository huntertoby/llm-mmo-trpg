// HUD 的 Q 版小圖示畫布（Phase QI-5）：把 `render/hudIcon.ts` 的畫布貼到頁面上。
// 畫布寬高＝顯示 × `ICON_RES`（`iconCanvasPx`），CSS 顯示寬高＝`px`，不縮放；圖由 `cacheKey` 決定。
// canvas 不吃 CSS 的 `currentColor`／`fill`：狀態（已釘、亮暗）由呼叫端傳。
import { useEffect, useRef } from "react";
import { hudIconCanvas, hudIconKey, type HudIconOpt } from "../render/hudIcon";
import { iconCanvasPx } from "../render/weaponIcon";

type DataAttrs = Readonly<Record<`data-${string}`, string>>;

/** 一張圖示畫布：`make()` 回傳畫好的畫布（同 `cacheKey` 只貼一次）。 */
export function IconCanvas({ px, className, cacheKey, make, data }: { px: number; className: string; cacheKey: string; make: () => HTMLCanvasElement; data?: DataAttrs }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (canvas == null || ctx == null) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(make(), 0, 0);
    // 圖由 cacheKey 決定
  }, [cacheKey]);
  const cv = iconCanvasPx(px);
  return <canvas ref={ref} className={className} width={cv} height={cv} style={{ width: px, height: px }} aria-hidden="true" {...data} />;
}

/** HUD 圖示（`qIcon/hud.ts` 的 id）。 */
export function HudGlyph({ id, px, className, opt = {}, data }: { id: string; px: number; className: string; opt?: HudIconOpt; data?: DataAttrs }) {
  return <IconCanvas px={px} className={className} cacheKey={hudIconKey(id, px, undefined, opt)} make={() => hudIconCanvas(id, px, undefined, opt)} data={data} />;
}
