// 部件說明框（Phase 3-18a）：包住任何一個部件（技能圖示的小圓、狀態、表面……），滑過顯示「類別、名稱、說明」，
// 點一下釘住（觸控也能用），點外面或按 Esc 關閉。說明框用 portal 放在 body 上，不會被卡片裁掉，也不會超出視窗。
import { useEffect, useLayoutEffect, useReducer, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { tipPlacement, tipReduce, tipVisible, TIP_CLOSED } from "./tipState";

interface Props {
  /** 部件類別（骨架、形狀、效果、狀態……）。 */
  cat: string;
  label: string;
  /** 說明；空字串就不寫。 */
  tip: string;
  children: ReactNode;
  /** 包在可點選的東西裡面（例如工坊選項按鈕）時設為 false：只在滑過時顯示，不攔截點擊。 */
  pin?: boolean;
  className?: string;
}

export function PartTip({ cat, label, tip, children, pin = true, className }: Props) {
  const [state, dispatch] = useReducer(tipReduce, TIP_CLOSED);
  const anchor = useRef<HTMLSpanElement>(null);
  const box = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<CSSProperties>({ left: 0, top: 0, visibility: "hidden" });
  const open = tipVisible(state);

  useLayoutEffect(() => {
    const a = anchor.current?.getBoundingClientRect();
    const b = box.current;
    if (!open || a === undefined || b === null) return;
    const p = tipPlacement(
      { left: a.left, top: a.top, width: a.width, height: a.height },
      { width: b.offsetWidth, height: b.offsetHeight },
      { width: window.innerWidth, height: window.innerHeight },
    );
    setPos({ left: p.left, top: p.top });
  }, [open, cat, label, tip]);

  useEffect(() => {
    if (!state.pinned) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") dispatch("escape");
    };
    const onDown = (e: PointerEvent) => {
      const t = e.target;
      if (t instanceof Node && (anchor.current?.contains(t) === true || box.current?.contains(t) === true)) return;
      dispatch("outside");
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onDown);
    };
  }, [state.pinned]);

  return (
    <span
      ref={anchor}
      className={`part-tip${className === undefined ? "" : ` ${className}`}`}
      onMouseEnter={() => dispatch("enter")}
      onMouseLeave={() => dispatch("leave")}
      onClick={pin ? () => dispatch("click") : undefined}
      onKeyDown={(e) => {
        if (pin && (e.key === "Enter" || e.key === " ")) {
          e.preventDefault();
          dispatch("click");
        }
      }}
      role={pin ? "button" : undefined}
      tabIndex={pin ? 0 : undefined}
      aria-label={`${cat}：${label}`}
      aria-expanded={pin ? open : undefined}
    >
      {children}
      {open &&
        createPortal(
          <div ref={box} className={`part-tip-box${state.pinned ? " pinned" : ""}`} style={pos} role="tooltip">
            <div className="part-tip-cat">{cat}</div>
            <div className="part-tip-name">{label}</div>
            {tip !== "" && <div className="part-tip-text">{tip}</div>}
          </div>,
          document.body,
        )}
    </span>
  );
}
