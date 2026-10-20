// 版面用的小 hook（Phase 3-8）：視窗是否窄、元素的可用大小。
import { useEffect, useState, type RefObject } from "react";
import { NARROW_WIDTH } from "../battle/skillTray";
import type { Size } from "../battle/stageLayout";

function isNarrow(): boolean {
  return typeof window !== "undefined" && window.innerWidth < NARROW_WIDTH;
}

/** 視窗寬度小於 `NARROW_WIDTH`。 */
export function useNarrow(): boolean {
  const [narrow, setNarrow] = useState(isNarrow);
  useEffect(() => {
    const onResize = () => setNarrow(isNarrow());
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);
  return narrow;
}

/** 元素內容區的大小（ResizeObserver）；還沒量到時為 `null`。 */
export function useElementSize(ref: RefObject<HTMLElement>): Size | null {
  const [size, setSize] = useState<Size | null>(null);
  useEffect(() => {
    const el = ref.current;
    if (el === null) return undefined;
    const update = () => {
      const w = el.clientWidth;
      const h = el.clientHeight;
      setSize((prev) => (prev !== null && prev.width === w && prev.height === h ? prev : { width: w, height: h }));
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, [ref]);
  return size;
}
