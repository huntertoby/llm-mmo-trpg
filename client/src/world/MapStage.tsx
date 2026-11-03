// 區域圖、大世界圖共用的畫布舞台（Phase 6F-ART1）：畫布 1280×860 等比縮放、置中放進面板；
// 底層（地景）與上層（迷霧、標記）是兩張疊在一起的 <canvas>，各自照自己的鍵決定要不要重畫；
// 透明的點擊、滑過區（DOM）用百分比疊在最上面，和畫布用同一套 `P()` 換算，所以縮放時一定對齊。
import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { fontEpoch, subscribeFonts } from "../render/fontLoad";
import { H, W } from "../render/regionMapArt";
import type { Surface, SurfaceFactory } from "../render/regionMapPainter";

/** 面板寬小於這個值時字牌不再跟著縮小（docs/art/雲嶺區域插畫.md 第 4 節第 5 點）。 */
export const READABLE_WIDTH = 900;

/** 字牌倍數：舞台寬 ≥ 900 時 1；更窄時放大到和 900 寬一樣大的字。 */
export function labelScale(stageWidth: number): number {
  if (stageWidth <= 0 || stageWidth >= READABLE_WIDTH) return 1;
  return Math.round((READABLE_WIDTH / stageWidth) * 100) / 100;
}

/** 在 `boxW`×`boxH` 的空間裡放進等比的 1280×860 舞台（CSS 像素）。 */
export function fitStage(boxW: number, boxH: number): { w: number; h: number } {
  if (boxW <= 0 || boxH <= 0) return { w: 0, h: 0 };
  const s = Math.min(boxW / W, boxH / H);
  return { w: Math.floor(W * s), h: Math.floor(H * s) };
}

/** 瀏覽器的離屏畫布。 */
export const domSurface: SurfaceFactory = (w, h) => {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  return c as Surface;
};

export interface StagePaint {
  /** 底層的鍵（區域、尺寸）：變了才重畫底層。 */
  baseKey: string;
  /** 上層的鍵（狀態、尺寸）：變了才重畫上層。 */
  overlayKey: string;
  paintBase(ctx: CanvasRenderingContext2D, pw: number, ph: number, epoch: number): void;
  paintOverlay(ctx: CanvasRenderingContext2D, pw: number, ph: number, k: number, epoch: number): void;
}

interface Props {
  className?: string;
  /** 依舞台像素尺寸、字牌倍數、字型版本算出畫法（鍵裡要含這些）。 */
  paint(pw: number, ph: number, k: number, epoch: number): StagePaint;
  /** 透明點擊區（`k`＝字牌倍數）。 */
  children(k: number): ReactNode;
  testId?: string;
}

function useFontEpoch(): number {
  const [epoch, setEpoch] = useState(fontEpoch());
  useEffect(() => subscribeFonts(() => setEpoch(fontEpoch())), []);
  return epoch;
}

export function MapStage({ className, paint, children, testId }: Props) {
  const boxRef = useRef<HTMLDivElement>(null);
  const baseRef = useRef<HTMLCanvasElement>(null);
  const overRef = useRef<HTMLCanvasElement>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const epoch = useFontEpoch();
  const painted = useRef({ base: "", overlay: "" });

  useLayoutEffect(() => {
    const box = boxRef.current;
    if (box === null) return undefined;
    const measure = (): void => setSize(fitStage(box.clientWidth, box.clientHeight));
    measure();
    if (typeof ResizeObserver === "undefined") return undefined;
    const ro = new ResizeObserver(measure);
    ro.observe(box);
    return () => ro.disconnect();
  }, []);

  const dpr = typeof window === "undefined" ? 1 : Math.min(2, window.devicePixelRatio || 1);
  const pw = Math.round(size.w * dpr);
  const ph = Math.round(size.h * dpr);
  const k = labelScale(size.w);
  const p = paint(pw, ph, k, epoch);

  useEffect(() => {
    if (pw === 0 || ph === 0) return;
    const base = baseRef.current?.getContext("2d") ?? null;
    if (base !== null && painted.current.base !== p.baseKey) {
      p.paintBase(base, pw, ph, epoch);
      painted.current.base = p.baseKey;
    }
    const over = overRef.current?.getContext("2d") ?? null;
    if (over !== null && painted.current.overlay !== p.overlayKey) {
      p.paintOverlay(over, pw, ph, k, epoch);
      painted.current.overlay = p.overlayKey;
    }
  });

  const stageStyle = size.w > 0 ? { width: `${size.w}px`, height: `${size.h}px` } : undefined;
  return (
    <div className={`map-stage-box${className !== undefined ? ` ${className}` : ""}`} ref={boxRef} data-testid={testId}>
      <div className="map-stage" style={stageStyle}>
        <canvas className="map-stage-layer" ref={baseRef} width={pw} height={ph} data-layer="base" aria-hidden="true" />
        <canvas className="map-stage-layer" ref={overRef} width={pw} height={ph} data-layer="overlay" aria-hidden="true" />
        <div className="map-stage-hits">{children(k)}</div>
      </div>
    </div>
  );
}
