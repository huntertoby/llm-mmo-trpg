// 滑過格子的浮動卡外框（Phase 3-15；3-30 起可滑進、可釘住、可捲動）：位置仍由 cardPlacement 決定（格子旁邊、不擋住滑鼠所在格），
// 但卡片用 portal 放在 body 上、`position: fixed`（戰場區是捲動容器，放在裡面會被裁掉）：量測後夾進戰場區的可見範圍與視窗內，
// 最大高度不超出可見範圍，超出時卡片內捲動。卡片與格子之間有透明橋接區（外框 padding），滑鼠從格子移向卡片不會斷；規則見 `hoverCard.ts`。
import { useLayoutEffect, useRef, type CSSProperties, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { CARD_GAP } from "../battle/stageLayout";
import { cardMaxHeight } from "./hoverCard";
import { ParentFloat } from "./useFloatCard";
import type { TileCardApi } from "./useTileCard";

/** 橋接區寬度＝格子與卡片的間距（`CARD_GAP`）。 */
const BRIDGE = CARD_GAP;
const EDGE = 4;

interface Props {
  placement: CSSProperties;
  card: TileCardApi;
  children: ReactNode;
}

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(v, Math.max(lo, hi)));

export function HoverFloat({ placement, card, children }: Props) {
  const own = useRef<HTMLDivElement | null>(null);
  const sentinel = useRef<HTMLSpanElement | null>(null);
  const { ctl } = card;
  const setRef = (el: HTMLDivElement | null) => {
    own.current = el;
    card.cardRef.current = el;
  };
  useLayoutEffect(() => {
    const el = own.current;
    const canvas = sentinel.current?.parentElement;
    if (el == null || canvas == null) return undefined;
    const scroller = canvas.closest(".board-scroll") ?? canvas;
    const layout = () => {
      const c = canvas.getBoundingClientRect();
      const s = scroller.getBoundingClientRect();
      const vis = {
        left: Math.max(s.left, 0) + EDGE,
        top: Math.max(s.top, 0) + EDGE,
        right: Math.min(s.right, window.innerWidth) - EDGE,
        bottom: Math.min(s.bottom, window.innerHeight) - EDGE,
      };
      el.style.maxHeight = `${cardMaxHeight(vis.bottom - vis.top, window.innerHeight, EDGE)}px`;
      const w = el.offsetWidth;
      const h = el.offsetHeight;
      const px = (v: unknown) => (typeof v === "number" ? v : 0);
      // 外框往格子方向多挪 BRIDGE（橋接區 padding）
      const left = placement.left !== undefined ? c.left + px(placement.left) - BRIDGE : c.right - px(placement.right) - w + BRIDGE;
      const top = placement.top !== undefined ? c.top + px(placement.top) : c.bottom - px(placement.bottom) - h;
      el.style.left = `${clamp(left, vis.left, vis.right - w)}px`;
      el.style.top = `${clamp(top, vis.top, vis.bottom - h)}px`;
    };
    layout();
    window.addEventListener("resize", layout);
    window.addEventListener("scroll", layout, true);
    // 卡片內容展開／收合（例如裝備加成）時重新量測
    let last = el.offsetHeight;
    const ro =
      typeof ResizeObserver === "undefined"
        ? null
        : new ResizeObserver(() => {
            if (el.offsetHeight === last) return;
            layout();
            last = el.offsetHeight;
          });
    ro?.observe(el);
    return () => {
      window.removeEventListener("resize", layout);
      window.removeEventListener("scroll", layout, true);
      ro?.disconnect();
    };
  });
  // 卡片在格子右邊（用 left 定位）時橋接區在左側，反之在右側。
  const side = placement.left !== undefined ? "bridge-left" : "bridge-right";
  return (
    <>
      <span ref={sentinel} hidden />
      {createPortal(
        <ParentFloat.Provider value={ctl}>
          <div
            ref={setRef}
            className={`unit-float ${side}${ctl.pinned ? " pinned" : ""}`}
            onPointerEnter={(e) => {
              if (e.pointerType !== "touch") ctl.cardEnter();
            }}
            onPointerLeave={(e) => {
              if (e.pointerType !== "touch") ctl.cardLeave();
            }}
            // 卡片疊在戰場上：事件不能（經 React 樹）冒泡到戰場，否則會算成滑過／點選底下的格子
            onPointerMove={(e) => e.stopPropagation()}
            onContextMenu={(e) => e.stopPropagation()}
            onClick={(e) => {
              e.stopPropagation();
              ctl.pin();
            }}
          >
            {children}
          </div>
        </ParentFloat.Provider>,
        document.body,
      )}
    </>
  );
}
