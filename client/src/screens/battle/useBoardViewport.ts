// 戰鬥畫面的版面與地圖視角（由 BattleScreen 抽出，Phase 3T-7）：欄寬與底部列高度的偏好（存在瀏覽器）、
// 右側窄欄收合、地圖縮放（Ctrl＋滾輪、自動填滿）與中鍵拖曳平移。

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
  type RefObject,
} from "react";
import type { DrawModel } from "../../battle/drawModel";
import {
  clampLayout,
  clampZoom,
  DEFAULT_LAYOUT,
  layoutLimits,
  loadLayout,
  saveLayout,
  zoomBy,
  ZOOM_STEP,
  type LayoutPrefs,
} from "../../battle/layoutPrefs";
import { loadSidePref, saveSideCollapsed, sideCollapsed } from "../../battle/skillTray";
import { fitScale } from "../../battle/stageLayout";
import { useElementSize, useNarrow, useViewportSize } from "../../ui/useLayout";

export interface BoardViewport {
  narrow: boolean;
  /** 戰場捲動區（地圖縮放與平移的對象）。 */
  scrollRef: RefObject<HTMLDivElement>;
  layout: LayoutPrefs;
  limits: ReturnType<typeof layoutLimits>;
  patchLayout(patch: Partial<LayoutPrefs>): void;
  resetLayout(): void;
  /** 版面欄寬的 CSS 變數（`--side-w`、`--bottom-h`、`--hero-w`）。 */
  layoutStyle: CSSProperties;
  /** 右側窄欄是否收合，與切換。 */
  collapsed: boolean;
  toggleSide(): void;
  /** 目前縮放比例（手動縮放或自動填滿）與縮放一步。 */
  scale: number;
  zoomStep(factor: number): void;
  panning: boolean;
  /** 中鍵拖曳平移的事件處理，掛在捲動區上。 */
  panHandlers: {
    onPointerDown(e: ReactPointerEvent<HTMLDivElement>): void;
    onPointerMove(e: ReactPointerEvent<HTMLDivElement>): void;
    onPointerUp(): void;
    onPointerCancel(): void;
  };
}

export function useBoardViewport(model: DrawModel): BoardViewport {
  const narrow = useNarrow();
  /** 玩家記下的右側窄欄收合狀態（沒有記錄時 `null`，依視窗寬度決定）。 */
  const [sidePref, setSidePref] = useState<boolean | null>(loadSidePref);
  const scrollRef = useRef<HTMLDivElement>(null);
  const boardSize = useElementSize(scrollRef);
  const viewport = useViewportSize();
  const [layoutPref, setLayoutPref] = useState<LayoutPrefs>(loadLayout);
  const layout = useMemo(() => clampLayout(layoutPref, viewport), [layoutPref, viewport]);
  const limits = useMemo(() => layoutLimits(viewport), [viewport]);
  const patchLayout = useCallback((patch: Partial<LayoutPrefs>) => setLayoutPref((p) => ({ ...p, ...patch })), []);
  const resetLayout = useCallback(() => setLayoutPref(DEFAULT_LAYOUT), []);
  useEffect(() => saveLayout(layoutPref), [layoutPref]);
  const [panning, setPanning] = useState(false);
  const panRef = useRef<{ x: number; y: number; left: number; top: number } | null>(null);
  /** 縮放前記下捲動區中心的相對位置，縮放後還原，讓畫面不跳。 */
  const anchorRef = useRef<{ fx: number; fy: number } | null>(null);

  const fit = boardSize === null ? 1 : fitScale({ width: boardSize.width - 16, height: boardSize.height - 16 }, model);
  const scale = layout.zoom ?? fit;
  const scaleRef = useRef(scale);
  scaleRef.current = scale;
  const zoomTo = useCallback(
    (next: number) => {
      const el = scrollRef.current;
      if (el !== null && el.scrollWidth > 0 && el.scrollHeight > 0) {
        anchorRef.current = {
          fx: (el.scrollLeft + el.clientWidth / 2) / el.scrollWidth,
          fy: (el.scrollTop + el.clientHeight / 2) / el.scrollHeight,
        };
      }
      patchLayout({ zoom: clampZoom(next) });
    },
    [patchLayout],
  );
  const zoomStep = useCallback((factor: number) => zoomTo(zoomBy(scaleRef.current, factor)), [zoomTo]);
  useLayoutEffect(() => {
    const el = scrollRef.current;
    const a = anchorRef.current;
    if (el === null || a === null) return;
    anchorRef.current = null;
    el.scrollLeft = a.fx * el.scrollWidth - el.clientWidth / 2;
    el.scrollTop = a.fy * el.scrollHeight - el.clientHeight / 2;
  }, [scale]);
  // Ctrl＋滾輪縮放地圖（要擋掉瀏覽器自己的縮放，所以用非被動的原生監聽）
  useEffect(() => {
    const el = scrollRef.current;
    if (el === null) return undefined;
    const onWheel = (e: WheelEvent) => {
      if (!e.ctrlKey) return;
      e.preventDefault();
      zoomStep(e.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP);
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [zoomStep]);

  const collapsed = sideCollapsed(sidePref, narrow);
  const toggleSide = () => {
    saveSideCollapsed(!collapsed);
    setSidePref(!collapsed);
  };
  const layoutStyle = {
    "--side-w": `${layout.sideWidth}px`,
    "--bottom-h": `${layout.bottomHeight}px`,
    "--hero-w": `${layout.heroWidth}px`,
  } as CSSProperties;

  const panHandlers = {
    onPointerDown: (e: ReactPointerEvent<HTMLDivElement>) => {
      const el = scrollRef.current;
      if (e.button !== 1 || el === null) return;
      e.preventDefault();
      el.setPointerCapture(e.pointerId);
      panRef.current = { x: e.clientX, y: e.clientY, left: el.scrollLeft, top: el.scrollTop };
      setPanning(true);
    },
    onPointerMove: (e: ReactPointerEvent<HTMLDivElement>) => {
      const el = scrollRef.current;
      const p = panRef.current;
      if (el === null || p === null) return;
      el.scrollLeft = p.left - (e.clientX - p.x);
      el.scrollTop = p.top - (e.clientY - p.y);
    },
    onPointerUp: () => {
      panRef.current = null;
      setPanning(false);
    },
    onPointerCancel: () => {
      panRef.current = null;
      setPanning(false);
    },
  };

  return {
    narrow,
    scrollRef,
    layout,
    limits,
    patchLayout,
    resetLayout,
    layoutStyle,
    collapsed,
    toggleSide,
    scale,
    zoomStep,
    panning,
    panHandlers,
  };
}
