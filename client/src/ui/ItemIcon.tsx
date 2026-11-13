// 物品圖示（Phase QI-7，第⑥批 Q 版；畫法 `render/qIcon/items.ts`、快取 `render/itemIcon.ts`）：照 `GearIcon` 的寫法，畫布寬高＝`iconCanvasPx(size)`，CSS 不縮放畫布。
// `frame` 呼叫端明寫：背包格、信件附件、清單列寫 "bag"，飛進背包寫 "fly"（物品的飛行圓是 GainIcon 的 28 格直徑 26 的圓，和裝備飛行的 32 不同，
// 開發 PM 定需求第 5 節第 8 點選 (a)）。
// 停在版面裡的圖示（"bag"）掛載後量一次位置，用 `position: relative` 挪 `pixelSnapNudge` 讓左上角落在裝置像素上（清單列的 24 是 flex 置中，
// 列高、字高可能讓它落在小數 CSS px，瀏覽器重新取樣會讓 1px 外框發糊；需求第 4 節第 5 點）。飛行中的不挪（Web Animations 在動）。
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { pixelSnapNudge } from "../render/gearIcon";
import { hasItemIcon, itemIconCanvas, type ItemIconFrame } from "../render/itemIcon";
import { iconCanvasPx } from "../render/weaponIcon";

interface Props {
  /** 物品 id（`content/world/items.yaml`）或通用的 `gain_item`／`gain_gear`。 */
  id: string;
  /** 顯示邊長（整數 CSS px：42 背包格、32 信件附件、28 飛行、24 清單列）。 */
  size: number;
  frame: ItemIconFrame;
  /** 後端物品 view 的 `color`（染料）。 */
  color?: string | null | undefined;
  /** 後端物品 view 的 `rare`（材料）。 */
  rare?: boolean | null | undefined;
  /** 無障礙名稱（`aria-label`）；不是原生 tooltip（要說明請用 `Hint`）。沒給時 `aria-hidden`。 */
  label?: string;
}

interface Nudge {
  x: number;
  y: number;
}
const NO_NUDGE: Nudge = { x: 0, y: 0 };

export function ItemIcon({ id, size, frame, color, rare, label }: Props) {
  const ref = useRef<HTMLCanvasElement>(null);
  const [nudge, setNudge] = useState<Nudge>(NO_NUDGE);
  const snap = frame === "bag";
  useLayoutEffect(() => {
    const cv = ref.current;
    if (!snap || cv == null || typeof window === "undefined") return undefined;
    const align = (): void => {
      const r = cv.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      setNudge((prev) => {
        const next = { x: pixelSnapNudge(r.left - prev.x, dpr), y: pixelSnapNudge(r.top - prev.y, dpr) };
        return Math.abs(next.x - prev.x) < 1e-4 && Math.abs(next.y - prev.y) < 1e-4 ? prev : next;
      });
    };
    align();
    window.addEventListener("resize", align);
    return () => window.removeEventListener("resize", align);
  }, [snap, size]);
  useEffect(() => {
    const target = ref.current;
    const ctx = target?.getContext("2d");
    const art = itemIconCanvas(id, size, undefined, { frame, color, rare });
    if (target == null || ctx == null || art === null) return;
    ctx.clearRect(0, 0, target.width, target.height);
    ctx.drawImage(art, 0, 0);
  }, [id, size, frame, color, rare]);
  const cv = iconCanvasPx(size);
  const style = snap && (nudge.x !== 0 || nudge.y !== 0) ? { width: size, height: size, position: "relative" as const, left: nudge.x, top: nudge.y } : { width: size, height: size };
  return (
    <canvas
      ref={ref}
      className={`item-icon item-icon-${frame}`}
      width={cv}
      height={cv}
      style={style}
      data-item-icon={id}
      aria-label={label}
      role={label === undefined ? undefined : "img"}
      aria-hidden={label === undefined ? true : undefined}
    />
  );
}

/** 清單列裡沒有物品圖示的列（裝備、表裡沒有的物品）：24 寬的空位，名字照樣對齊（開發 PM 定需求第 5 節第 3、4 點）。 */
export function ItemIconPad({ size }: { size: number }) {
  return <span className="item-icon-pad" style={{ width: size, height: size }} aria-hidden="true" />;
}

/** 清單列的圖示大小（商店買、賣、整理腰包、背包滿了、鐵匠特色材料；需求第 1.1 節第 5 列）。 */
export const LIST_ICON_PX = 24;

/** 清單列名字前的圖示：物品畫 24 的 Q 版圖示（背包框）；裝備、表裡沒有的物品留 24 寬的空位對齊名字（開發 PM 定第 5 節第 3、4 點）。 */
export function ItemListIcon({ id, gear, color, rare }: { id: string; gear?: boolean | undefined; color?: string | null | undefined; rare?: boolean | null | undefined }) {
  if (gear === true || !hasItemIcon(id, color)) return <ItemIconPad size={LIST_ICON_PX} />;
  return <ItemIcon id={id} size={LIST_ICON_PX} frame="bag" color={color} rare={rare} />;
}
