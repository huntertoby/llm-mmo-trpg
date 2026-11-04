// HUD 舞台的大小（Phase 6B-5）：寬＝舞台元素的寬，高＝視窗底部到舞台頂端（至少 360）；另外回傳視窗寬（窄視窗判定）。
// UI-E1 追加 2：另外回傳舞台上緣在視窗裡的位置（`top`），大世界的詢問視窗（position: fixed）照 HUD 規則放時要加上。
import { useLayoutEffect, useRef, useState } from "react";

/** 舞台底下留的空白。 */
const BOTTOM_GAP = 8;
const MIN_HEIGHT = 360;

/** `dep`：舞台上方的東西（錯誤列、說明列）變了時重新量。 */
export function useHudStage(active: boolean, dep: unknown = null) {
  const ref = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 1024, height: 600, viewport: 1280, top: 0 });
  useLayoutEffect(() => {
    const el = ref.current;
    if (!active || el === null) return undefined;
    const measure = () => {
      const rectTop = el.getBoundingClientRect().top;
      const top = rectTop + window.scrollY;
      const height = Math.max(MIN_HEIGHT, Math.floor(window.innerHeight - top - BOTTOM_GAP));
      setSize((cur) => {
        const next = { width: el.clientWidth, height, viewport: window.innerWidth, top: Math.round(rectTop) };
        return cur.width === next.width && cur.height === next.height && cur.viewport === next.viewport && cur.top === next.top ? cur : next;
      });
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    window.addEventListener("resize", measure);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, [active, dep]);
  return { ref, ...size };
}
