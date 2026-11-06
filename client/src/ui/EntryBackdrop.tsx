// 入口畫面的浮島天空背景（UI-E1；docs/art/shots/misc/home-v2.png）：首頁、角色列表與建角、開新一輪、一輪路線圖共用。
// 畫法是大世界圖第 2 版（`AtlasPainter`，`bare`：不貼字牌與外框），兩張疊在一起的 <canvas>（底層天空不動、
// 上層浮島 ±3px 漂浮），用 CSS `object-fit: cover` 蓋滿視窗；減少動態時浮島不動。
// 背景黏在視窗上（sticky），頁面內容往下捲時背景不跟著捲；不接滑鼠、不佔版面。
import { useEffect, useRef, useState } from "react";
import { coverPixels, entryScene } from "../render/entryScene";
import { H, W } from "../render/regionMapArt";
import { AtlasPainter } from "../render/worldMapPainter";
import { browserClock, prefersReducedMotion, shouldAnimate, startFrameLoop, subscribeReducedMotion } from "../world/frameLoop";
import { domSurface } from "../world/MapStage";

const SCENE = entryScene();
let shared: AtlasPainter | null = null;
function painter(): AtlasPainter {
  shared ??= new AtlasPainter(domSurface, 2, 16);
  return shared;
}

function viewportPixels(): { w: number; h: number } {
  if (typeof window === "undefined") return { w: 0, h: 0 };
  return coverPixels(window.innerWidth, window.innerHeight, W, H, Math.min(2, window.devicePixelRatio || 1));
}

export function EntryBackdrop() {
  const baseRef = useRef<HTMLCanvasElement>(null);
  const overRef = useRef<HTMLCanvasElement>(null);
  const [px, setPx] = useState(viewportPixels);
  const [reduced, setReduced] = useState(prefersReducedMotion());

  useEffect(() => subscribeReducedMotion(() => setReduced(prefersReducedMotion())), []);
  useEffect(() => {
    const onResize = () =>
      setPx((cur) => {
        const next = viewportPixels();
        return cur.w === next.w && cur.h === next.h ? cur : next;
      });
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const animate = shouldAnimate(true, reduced, px.w, px.h);
  useEffect(() => {
    if (px.w === 0) return undefined;
    const base = baseRef.current?.getContext("2d") ?? null;
    if (base !== null) painter().paintBase(base, SCENE, px.w, px.h);
    const over = overRef.current?.getContext("2d") ?? null;
    if (over === null) return undefined;
    const draw = (t: number | null) => painter().paintOverlay(over, SCENE, false, px.w, px.h, 1, { t, bare: true });
    const clock = browserClock();
    if (!animate || clock === null) {
      draw(null);
      return undefined;
    }
    return startFrameLoop((t) => draw(t), clock);
  }, [px.w, px.h, animate]);

  return (
    <div className="entry-backdrop" aria-hidden="true" data-testid="entry-backdrop">
      <div className="entry-backdrop-sticky">
        <canvas className="entry-backdrop-layer" ref={baseRef} width={px.w} height={px.h} data-layer="base" />
        <canvas className="entry-backdrop-layer" ref={overRef} width={px.w} height={px.h} data-layer="overlay" />
        <div className="entry-backdrop-veil" />
      </div>
    </div>
  );
}
