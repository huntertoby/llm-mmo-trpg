// 滑過格子的浮動卡外框（Phase 3-15；3-30 起可滑進、可釘住、可捲動）：位置由 cardPlacement 決定（格子旁邊、不擋住滑鼠所在格）；
// 量測實際高度，必要時上移或下移到不超出戰場範圍；最大高度不超出戰場區與視窗，超出時卡片內捲動。
// 卡片與格子之間有透明橋接區（外框 padding），滑鼠從格子移向卡片不會斷；規則見 `hoverCard.ts`。
import { useLayoutEffect, useRef, type CSSProperties, type ReactNode } from "react";
import { ParentFloat } from "./useFloatCard";
import { CARD_GAP } from "../battle/stageLayout";
import { cardMaxHeight } from "./hoverCard";
import type { TileCardApi } from "./useTileCard";

/** 橋接區寬度＝格子與卡片的間距（`CARD_GAP`）。 */
const BRIDGE = CARD_GAP;

interface Props {
  placement: CSSProperties;
  card: TileCardApi;
  children: ReactNode;
}

export function HoverFloat({ placement, card, children }: Props) {
  const own = useRef<HTMLDivElement | null>(null);
  const { ctl } = card;
  const setRef = (el: HTMLDivElement | null) => {
    own.current = el;
    card.cardRef.current = el;
  };
  useLayoutEffect(() => {
    const el = own.current;
    const parent = el?.offsetParent;
    if (el == null || !(parent instanceof HTMLElement)) return undefined;
    const layout = () => {
      // 先還原成預設位置再量測。
      el.style.maxHeight = `${cardMaxHeight(parent.clientHeight, window.innerHeight)}px`;
      el.style.top = placement.top === undefined ? "auto" : `${placement.top}px`;
      el.style.bottom = placement.bottom === undefined ? "auto" : `${placement.bottom}px`;
      const room = parent.clientHeight;
      const height = el.offsetHeight;
      if (el.offsetTop + height > room || el.offsetTop < 0) {
        el.style.top = `${Math.max(0, room - height)}px`;
        el.style.bottom = "auto";
      }
    };
    layout();
    // 卡片內容展開／收合（例如裝備加成）時重新量測
    if (typeof ResizeObserver === "undefined") return undefined;
    let last = el.offsetHeight;
    const ro = new ResizeObserver(() => {
      if (el.offsetHeight === last) return;
      layout();
      last = el.offsetHeight;
    });
    ro.observe(el);
    return () => ro.disconnect();
  });
  // 卡片在左邊（用 right 定位）時橋接區在右側，反之在左側。
  const side = placement.left !== undefined ? "bridge-left" : "bridge-right";
  const style: CSSProperties = { ...placement };
  if (typeof style.left === "number") style.left -= BRIDGE;
  if (typeof style.right === "number") style.right -= BRIDGE;
  return (
    <ParentFloat.Provider value={ctl}>
      <div
        ref={setRef}
        className={`unit-float ${side}${ctl.pinned ? " pinned" : ""}`}
        style={style}
        onPointerEnter={(e) => {
          if (e.pointerType !== "touch") ctl.cardEnter();
        }}
        onPointerLeave={(e) => {
          if (e.pointerType !== "touch") ctl.cardLeave();
        }}
        // 卡片疊在戰場上：事件不能冒泡到戰場（否則會算成滑過／點選底下的格子）
        onPointerMove={(e) => e.stopPropagation()}
        onContextMenu={(e) => e.stopPropagation()}
        onClick={(e) => {
          e.stopPropagation();
          ctl.pin();
        }}
      >
        {children}
      </div>
    </ParentFloat.Provider>
  );
}
