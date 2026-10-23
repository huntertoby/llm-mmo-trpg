// 浮動卡的 React 接頭（Phase 3-30 第 32.1 項）：技能列的技能卡與部件說明框共用。
// 規則與計時在 `floatCard.ts`；這裡接滑鼠／鍵盤／觸控事件、量測位置、Esc 與點外面關閉。
//
//   const f = useFloatCard({ pinOn: "touch" });
//   <div {...f.triggerProps}>…按鈕…</div>
//   {f.open && <FloatCard float={f} className="skill-card-float">…卡片內容…</FloatCard>}
//
// 卡片用 portal 放在 body 上（不會被捲動區裁掉），貼齊觸發元素，兩者之間是透明橋接區。
import {
  createContext,
  useContext,
  useEffect,
  useLayoutEffect,
  useReducer,
  useRef,
  useState,
  type CSSProperties,
  type FocusEvent,
  type HTMLAttributes,
  type KeyboardEvent,
  type MouseEvent,
  type PointerEvent,
  type ReactNode,
  type MutableRefObject,
  type RefObject,
} from "react";
import { createPortal } from "react-dom";
import { FloatController, floatPlacement, type Align, type Holdable, type PinMode, type Side } from "./floatCard";

/** 卡片內容的上層控制器：卡片裡的部件說明框開著時，用它讓外面的卡片不關閉。 */
export const ParentFloat = createContext<Holdable | null>(null);

const FOCUSABLE = 'button, a[href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

/** 只有鍵盤（`:focus-visible`）取得焦點才顯示；滑鼠點擊後的焦點不算。 */
function keyboardFocus(target: EventTarget): boolean {
  if (!(target instanceof HTMLElement)) return true;
  try {
    return target.matches(":focus-visible");
  } catch {
    return true;
  }
}

export interface FloatApi {
  ctl: FloatController;
  open: boolean;
  pinned: boolean;
  nested: boolean;
  triggerRef: MutableRefObject<HTMLElement | null>;
  cardRef: MutableRefObject<HTMLDivElement | null>;
  /** 展開在觸發元素上（`<span {...f.triggerProps}>`）。 */
  triggerProps: Pick<
    HTMLAttributes<HTMLElement>,
    "onPointerEnter" | "onPointerLeave" | "onPointerDown" | "onClick" | "onFocus" | "onBlur" | "onKeyDown"
  > & { ref: RefObject<never> };
  /** 事件是不是從卡片裡面冒上來的（卡片在觸發元素的 React 子樹裡）。 */
  inCard(target: EventTarget): boolean;
  focusTrigger(): void;
}

export function useFloatCard({ pinOn = "always" }: { pinOn?: PinMode } = {}): FloatApi {
  const parent = useContext(ParentFloat);
  const [, rerender] = useReducer((n: number) => n + 1, 0);
  const ref = useRef<FloatController | null>(null);
  if (ref.current === null) ref.current = new FloatController(parent !== null);
  const ctl = ref.current;
  const triggerRef = useRef<HTMLElement | null>(null);
  const cardRef = useRef<HTMLDivElement | null>(null);
  const pointer = useRef("mouse");
  const open = ctl.visible;

  useEffect(() => {
    ctl.onChange = rerender;
    return () => {
      ctl.onChange = () => undefined;
      ctl.dispose();
    };
  }, [ctl]);

  // 巢狀的部件說明框開著，外面的卡片就不能關
  useEffect(() => {
    if (!open || parent === null) return;
    parent.hold(1);
    return () => parent.hold(-1);
  }, [open, parent]);

  // Esc 關閉（顯示中的都算）；點外面關閉（只管釘住的，滑過的本來就會自己收）
  useEffect(() => {
    if (!open) return;
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key !== "Escape") return;
      e.stopPropagation(); // 卡片處理了這次 Esc：BattleScreen 的 window 監聽不再取消瞄準
      ctl.dismiss();
    };
    const onDown = (e: globalThis.PointerEvent) => {
      if (!ctl.pinned) return;
      const t = e.target;
      if (!(t instanceof Element)) return;
      if (triggerRef.current?.contains(t) === true || cardRef.current?.contains(t) === true) return;
      if (t.closest(".float-card") !== null) return; // 卡片裡的部件說明框（portal）不算外面
      ctl.dismiss();
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onDown);
    };
  }, [open, ctl]);

  const focusTrigger = () => {
    const t = triggerRef.current;
    if (t === null) return;
    (t.matches(FOCUSABLE) ? t : t.querySelector<HTMLElement>(FOCUSABLE))?.focus();
  };

  const inCard = (t: EventTarget): boolean => t instanceof Node && cardRef.current?.contains(t) === true;

  const triggerProps: FloatApi["triggerProps"] = {
    ref: triggerRef as RefObject<never>,
    onPointerEnter: (e: PointerEvent<HTMLElement>) => {
      if (e.pointerType !== "touch") ctl.triggerEnter();
    },
    onPointerLeave: (e: PointerEvent<HTMLElement>) => {
      if (e.pointerType !== "touch") ctl.triggerLeave();
    },
    onPointerDown: (e: PointerEvent<HTMLElement>) => {
      pointer.current = e.pointerType;
    },
    onClick: (e: MouseEvent<HTMLElement>) => {
      if (inCard(e.target)) return; // 卡片在觸發元素的 React 子樹裡（portal），卡片上的點擊由卡片自己處理
      if (pinOn === "always" || (pinOn === "touch" && pointer.current === "touch")) ctl.click(true);
    },
    onFocus: (e: FocusEvent<HTMLElement>) => {
      if (keyboardFocus(e.target)) ctl.focusIn();
    },
    onBlur: (e: FocusEvent<HTMLElement>) => {
      const next = e.relatedTarget;
      if (next instanceof Node && (triggerRef.current?.contains(next) === true || cardRef.current?.contains(next) === true)) return;
      ctl.focusOut();
    },
    onKeyDown: (e: KeyboardEvent<HTMLElement>) => {
      // 卡片在 body 底下，Tab 不會自然走進去：卡片開著時，Tab 直接移到卡片
      if (inCard(e.target)) return;
      if (e.key === "Tab" && !e.shiftKey && ctl.visible && cardRef.current !== null) {
        e.preventDefault();
        cardRef.current.focus();
      }
    },
  };

  return { ctl, open, pinned: ctl.pinned, nested: parent !== null, triggerRef, cardRef, triggerProps, inCard, focusTrigger };
}

interface CardProps {
  float: FloatApi;
  /** 外框 class（技能卡 `skill-card-float`、部件說明框 `part-tip-box`……）。 */
  className?: string;
  align?: Align;
  role?: string;
  children: ReactNode;
}

/** 浮動卡本體：量測後貼齊觸發元素；滑進卡片（含橋接區）不關閉；點卡片釘住。 */
export function FloatCard({ float: f, className, align = "start", role, children }: CardProps) {
  const [pos, setPos] = useState<{ style: CSSProperties; side: Side }>({
    style: { left: 0, top: 0, visibility: "hidden" },
    side: "above",
  });
  useLayoutEffect(() => {
    const place = () => {
      const a = f.triggerRef.current?.getBoundingClientRect();
      const c = f.cardRef.current;
      if (a === undefined || c === null) return;
      const p = floatPlacement(
        { left: a.left, top: a.top, width: a.width, height: a.height },
        { width: c.offsetWidth, height: c.offsetHeight },
        { width: window.innerWidth, height: window.innerHeight },
        align,
      );
      setPos({ style: { left: p.left, top: p.top }, side: p.side });
    };
    place();
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    // 卡片內容展開／收合（例如技能卡的「召喚物資訊」）會改變高度：重新貼齊，避免長出視窗（3-41 美術 PM 驗收）
    const card = f.cardRef.current;
    let last = card?.offsetHeight ?? 0;
    const ro =
      typeof ResizeObserver === "undefined" || card === null
        ? null
        : new ResizeObserver(() => {
            if (card.offsetHeight === last) return;
            last = card.offsetHeight;
            place();
          });
    if (card !== null) ro?.observe(card);
    return () => {
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
      ro?.disconnect();
    };
  }, [f, align]);

  const { ctl } = f;
  return createPortal(
    <ParentFloat.Provider value={ctl}>
      <div
        ref={f.cardRef}
        className={`float-card side-${pos.side}${f.pinned ? " pinned" : ""}${className === undefined ? "" : ` ${className}`}`}
        style={pos.style}
        role={role}
        tabIndex={f.nested ? undefined : 0}
        onPointerEnter={(e) => {
          if (e.pointerType !== "touch") ctl.cardEnter();
        }}
        onPointerLeave={(e) => {
          if (e.pointerType !== "touch") ctl.cardLeave();
        }}
        onClick={() => ctl.click(false)}
        onFocus={(e) => {
          if (e.target === e.currentTarget && keyboardFocus(e.target)) ctl.focusIn();
        }}
        onBlur={(e) => {
          const next = e.relatedTarget;
          if (next instanceof Node && (f.cardRef.current?.contains(next) === true || f.triggerRef.current?.contains(next) === true)) return;
          ctl.focusOut();
        }}
        onKeyDown={(e) => {
          if (e.key === "Tab" && e.shiftKey && e.target === e.currentTarget) {
            e.preventDefault();
            f.focusTrigger();
          }
        }}
      >
        <div className="float-card-body">{children}</div>
      </div>
    </ParentFloat.Provider>,
    document.body,
  );
}
