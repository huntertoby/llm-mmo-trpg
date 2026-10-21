// 滑過格子的浮動卡外框（Phase 3-15）：位置由 cardPlacement 決定（格子旁邊、不擋住滑鼠所在格）；
// 單位卡與地形卡合併後比較高，量測實際高度，必要時上移或下移到不超出戰場範圍。
import { useLayoutEffect, useRef, type CSSProperties, type ReactNode } from "react";

interface Props {
  placement: CSSProperties;
  children: ReactNode;
}

export function HoverFloat({ placement, children }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const el = ref.current;
    const parent = el?.offsetParent;
    if (el == null || !(parent instanceof HTMLElement)) return;
    // 先還原成預設位置再量測（每次重繪都重算）。
    el.style.top = placement.top === undefined ? "auto" : `${placement.top}px`;
    el.style.bottom = placement.bottom === undefined ? "auto" : `${placement.bottom}px`;
    const room = parent.clientHeight;
    const height = el.offsetHeight;
    if (el.offsetTop + height > room || el.offsetTop < 0) {
      el.style.top = `${Math.max(0, room - height)}px`;
      el.style.bottom = "auto";
    }
  });
  return (
    <div ref={ref} className="unit-float" style={placement}>
      {children}
    </div>
  );
}
