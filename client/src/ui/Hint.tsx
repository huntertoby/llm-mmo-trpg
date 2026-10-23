// 一句話說明（Phase 3-32b）：取代原生 `title=` 的共用浮動卡。包住任何一個元素（按鈕、標籤、晶片……），
// 滑過／取得鍵盤焦點時顯示一張只有文字的浮動卡，規則與技能卡、部件說明框相同（`useFloatCard`：延遲、橋接、Esc 關閉、貼齊、不出畫面、
// 超高時卡內捲動、portal 到 body）。按鈕本身有動作，所以不做「點一下釘住」（`pinOn: "never"`，同 `PartTip` 的 `pin={false}`）。
//
//   <Hint text="縮小（Ctrl＋滾輪）"><button …>－</button></Hint>
//
// Phase 3-47：**不產生外層元素**。事件處理與 ref 用 `cloneElement` 直接掛到唯一的子元素上（子元素自己的同名處理函式照常先執行），
// 所以 `父 > 子` 的 CSS 選擇器不會被說明卡打斷（舊版外包 `<span class="hint-tip">` 造成拖曳線、結束回合、播放列的排版錯誤）。
// 子元素必須是單一個 DOM 元素（不是元件、不是陣列）；`text` 為空就原樣回傳子元素。浮動卡 portal 到 body，不在子元素底下。
import { Children, cloneElement, isValidElement, useLayoutEffect, type ReactElement, type ReactNode, type Ref } from "react";
import { FloatCard, useFloatCard } from "./useFloatCard";

interface Props {
  text: string | null | undefined;
  children: ReactNode;
}

type Handler = (e: never) => void;
const HANDLERS = ["onPointerEnter", "onPointerLeave", "onPointerDown", "onClick", "onFocus", "onBlur", "onKeyDown"] as const;

/** 唯一的子元素；不是單一 DOM 元素就丟出清楚的開發錯誤。 */
export function hintChild(children: ReactNode): ReactElement<Record<string, unknown>> {
  const only = Children.toArray(children);
  const child = only[0];
  if (only.length !== 1 || !isValidElement(child) || typeof child.type !== "string") {
    throw new Error("<Hint> 的子元素必須是單一個 DOM 元素（<button>、<span>……）；元件請在 Hint 裡面再包一層元素。");
  }
  return child as ReactElement<Record<string, unknown>>;
}

/** 觸發元素自己的選單開著（`aria-expanded="true"`，例如「更多動作」）。 */
export function isExpanded(props: Record<string, unknown>): boolean {
  const v = props["aria-expanded"];
  return v === true || v === "true";
}

export function Hint({ text, children }: Props) {
  const f = useFloatCard({ pinOn: "never" });
  const empty = text === null || text === undefined || text === "";
  const child = empty ? null : hintChild(children);
  // 觸發元素自己的選單開著時不顯示說明卡，開著的也立刻關，免得蓋住選單
  // （使用者：「彈出的視窗會沒有辦法按裝填」；規則見 docs/開發PM交接.md 6.5.1）
  const expanded = child !== null && isExpanded(child.props);
  useLayoutEffect(() => {
    if (expanded && f.open) f.ctl.dismiss();
  });
  if (child === null) return <>{children}</>;
  const own = (child as unknown as { ref?: Ref<HTMLElement> }).ref;
  const { ref: _ref, ...handlers } = f.triggerProps;
  void _ref;
  const merged: Record<string, unknown> = {
    ref: (node: HTMLElement | null) => {
      f.triggerRef.current = node;
      if (typeof own === "function") own(node);
      else if (own !== null && own !== undefined) (own as { current: HTMLElement | null }).current = node;
    },
  };
  if (!expanded) {
    for (const name of HANDLERS) {
      const mine = handlers[name] as Handler | undefined;
      const theirs = child.props[name] as Handler | undefined;
      merged[name] = (e: never) => {
        theirs?.(e);
        mine?.(e);
      };
    }
  }
  return (
    <>
      {cloneElement(child, merged)}
      {!expanded && f.open && (
        <FloatCard float={f} className="part-tip-box hint-tip-box" align="center" role="tooltip">
          <div className="hint-tip-text">{text}</div>
        </FloatCard>
      )}
    </>
  );
}
