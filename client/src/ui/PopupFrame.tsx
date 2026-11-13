// 共用彈窗元件（UI-E2；docs/art/全遊戲一致性巡檢.md #6、#12）：深藍底、金框、RT-1 區域四角飾件、單層。
// 危險類（遇敵）只在上緣加一條紅色細帶和「！」，不換整個框色。點擊開關的面板／對話框，不是說明卡（說明卡用 Hint，6.5.1）。
// 位置三種：
// - `hud`：大世界彈窗（6F-3 的 `popupBox`）：水平置中、上緣在主角卡下方、寬度讓出左右兩欄、下緣停在功能列上方，太高就在框內捲；
// - `dialog`：戰鬥詢問視窗（3-8 的 `decision-card`）：水平置中、靠上或靠下，框內捲；
// - `inline`：疊在別的容器裡（中上方的遇敵卡、事件卡），位置由容器決定。
// 四角飾件畫在外框的 `::after`（`.rt-frame`），內容捲在 `.ui-popup-body` 裡，所以捲動時飾件不跟著跑。
import { createContext, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode, type Ref, type RefObject, type UIEvent } from "react";
/** 6F-3 `popupBox()` 的結果（CSS 像素，相對 HUD 舞台）。 */
export interface PopupBoxLike {
  top: number;
  maxHeight: number;
  maxWidth: number;
}

export type PopupPlacement = { kind: "hud"; box: PopupBoxLike } | { kind: "dialog"; low: boolean } | { kind: "inline" };

export type PopupTone = "normal" | "danger";

/** 位置的內聯樣式（只有 `hud` 有；`dialog` 的位置在 CSS `.decision-card`）。 */
export function popupPlacementStyle(p: PopupPlacement): CSSProperties | undefined {
  if (p.kind !== "hud") return undefined;
  return { top: p.box.top, maxHeight: p.box.maxHeight, width: p.box.maxWidth, maxWidth: p.box.maxWidth };
}

/** RT-3：捲動區捲下去了沒（CSS 上緣漸隱只在 `data-scrolled="1"` 時出現，沒捲時不蓋第一行）。 */
export function scrolledFlag(scrollTop: number): "1" | "0" {
  return scrollTop > 0 ? "1" : "0";
}

/** 下緣漸隱的高度（CSS `.ui-popup-body::after`）。 */
export const BOTTOM_FADE_PX = 32;

/**
 * RT-3b（6F-7 檢查小修：ue1b_09_reaction_1600 框底多出約 30px 空白）：內容有超出捲動區時才放下緣漸隱
 *（漸隱是內容最後面的一塊 sticky 色塊，沒有超出時它只是 32px 的空白）。量的時候扣掉漸隱自己佔的高度，才不會來回跳。
 */
export function overflowFlag(scrollHeight: number, clientHeight: number, fadeShown: boolean): "1" | "0" {
  return scrollHeight - (fadeShown ? BOTTOM_FADE_PX : 0) > clientHeight + 1 ? "1" : "0";
}

/**
 * 6F-8（RT-3b 檢查第 2 節 3：事件卡捲到最下面時，卡底還留著約 45px 的空白漸隱帶）：內容的最後一行已經到捲動區下緣
 * （或更下面）時算「捲到底」，CSS 把下緣漸隱的高度設成 0，空間留給內容。量的時候扣掉漸隱自己佔的高度：
 * 漸隱在的時候，內容的最後一行到下緣是 `scrollTop + clientHeight ≥ scrollHeight − 漸隱`；拿掉漸隱後捲動區變短、
 * 瀏覽器把 scrollTop 夾回最下面，條件照樣成立，不會來回跳。
 */
export function atEndFlag(scrollTop: number, clientHeight: number, scrollHeight: number, fadeShown: boolean): "1" | "0" {
  return scrollTop + clientHeight >= scrollHeight - (fadeShown ? BOTTOM_FADE_PX : 0) - 1 ? "1" : "0";
}

/** 下緣漸隱現在有沒有佔高度（CSS：有超出、而且還沒捲到底）。 */
function fadeShown(el: HTMLElement): boolean {
  return el.dataset.overflow === "1" && el.dataset.end !== "1";
}

function setFlag(el: HTMLElement, key: "scrolled" | "overflow" | "end", flag: "1" | "0"): void {
  if (el.dataset[key] !== flag) el.dataset[key] = flag;
}

function markEnd(el: HTMLElement): void {
  setFlag(el, "end", atEndFlag(el.scrollTop, el.clientHeight, el.scrollHeight, fadeShown(el)));
}

function markScrolled(e: UIEvent<HTMLDivElement>): void {
  const el = e.currentTarget;
  setFlag(el, "scrolled", scrolledFlag(el.scrollTop));
  markEnd(el);
}

function markOverflow(el: HTMLElement): void {
  setFlag(el, "overflow", overflowFlag(el.scrollHeight, el.clientHeight, fadeShown(el)));
  markEnd(el);
}

/** 伺服器端（測試的 renderToStaticMarkup）沒有版面：用 useEffect，避免 useLayoutEffect 的警告。 */
const useIsoLayoutEffect = typeof window === "undefined" ? useEffect : useLayoutEffect;

/** 每次重繪、捲動區大小改變時重量一次有沒有超出。 */
function useOverflowFlag(ref: RefObject<HTMLDivElement | null>): void {
  useIsoLayoutEffect(() => {
    if (ref.current !== null) markOverflow(ref.current);
  });
  useEffect(() => {
    const el = ref.current;
    if (el === null || typeof ResizeObserver === "undefined") return undefined;
    const ro = new ResizeObserver(() => markOverflow(el));
    ro.observe(el);
    for (const child of Array.from(el.children)) ro.observe(child);
    return () => ro.disconnect();
  }, [ref]);
}

interface Props {
  placement: PopupPlacement;
  tone?: PopupTone;
  /** 外框額外的 class（例如 `world-hud-panel`、`decision-card`、`world-encounter`）。 */
  className?: string;
  role?: "dialog" | "region";
  label?: string;
  testId?: string;
  /** 外框上的 `data-*`（例如 `data-panel`）。 */
  data?: Readonly<Record<string, string>>;
  /** 框頂端、不跟著捲的那一列（戰鬥詢問視窗的標題與「移到下方」）。 */
  head?: ReactNode;
  /** 框底端、不跟著捲的那一段（FL-1b：選變體的下固定區；照 `head` 的做法放在 `ui-popup-body` 後面）。 */
  foot?: ReactNode;
  /**
   * 開「上下固定區的插槽」（FL-1b，大世界 HUD 面板）：框頂端與底端各放一個 `ui-popup-head`／`ui-popup-foot`，
   * 捲動區裡的元件可以用 `usePopupSlots()` 拿到這兩個元素、把自己的標頭與確定列 portal 進去（同一個元件的狀態，不用往上提）。
   * 插槽空著時 CSS 不顯示（`:empty`），其他面板的排版不變。
   */
  slots?: boolean;
  /** 外框的 ref（點擊式面板判斷「點到外面」用，例如大世界的設定面板）。 */
  frameRef?: Ref<HTMLDivElement>;
  children: ReactNode;
}

/** 上下固定區的插槽元素（`PopupFrame slots`）；不在有插槽的框裡為 `null`。 */
export interface PopupSlots {
  head: HTMLElement | null;
  foot: HTMLElement | null;
}

const PopupSlotsContext = createContext<PopupSlots | null>(null);

/** 捲動區裡的元件拿框的上下固定區插槽（FL-1b）；`null`＝不在有插槽的框裡，自己畫在原地。 */
export function usePopupSlots(): PopupSlots | null {
  return useContext(PopupSlotsContext);
}
export function PopupFrame({ placement, tone = "normal", className, role, label, testId, data, head, foot, slots = false, frameRef, children }: Props) {
  const body = useRef<HTMLDivElement | null>(null);
  const [headEl, setHeadEl] = useState<HTMLElement | null>(null);
  const [footEl, setFootEl] = useState<HTMLElement | null>(null);
  const slotValue = useMemo<PopupSlots | null>(() => (slots ? { head: headEl, foot: footEl } : null), [slots, headEl, footEl]);
  useOverflowFlag(body);
  const attrs = Object.fromEntries(Object.entries(data ?? {}).map(([k, v]) => [`data-${k}`, v]));
  const cls = ["ui-popup", "rt-frame", `ui-popup-${placement.kind}`, tone === "danger" ? "danger" : "", placement.kind === "dialog" && placement.low ? "low" : "", className ?? ""]
    .filter((c) => c !== "")
    .join(" ");
  return (
    <div ref={frameRef} className={cls} style={popupPlacementStyle(placement)} role={role} aria-label={label} data-testid={testId} data-popup={placement.kind} data-tone={tone} {...attrs}>
      {tone === "danger" && (
        <div className="ui-popup-band" aria-hidden="true">
          <span>！</span>
        </div>
      )}
      {slots ? (
        <div ref={setHeadEl} className="ui-popup-head">
          {head}
        </div>
      ) : (
        head
      )}
      <div ref={body} className="ui-popup-body" onScroll={markScrolled}>
        {slots ? <PopupSlotsContext.Provider value={slotValue}>{children}</PopupSlotsContext.Provider> : children}
      </div>
      {(slots || foot !== undefined) && (
        <div ref={slots ? setFootEl : undefined} className="ui-popup-foot">
          {foot}
        </div>
      )}
    </div>
  );
}
