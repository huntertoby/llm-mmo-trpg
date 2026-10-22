// 裝備圖示（Phase 3G-G5a）：畫在 canvas 上，圖示由 render/gearIcon.ts 產生並快取（64／48／32px）。
import { useEffect, useRef } from "react";
import { gearIconCanvas, type GearLook } from "../render/gearIcon";

interface Props {
  look: GearLook | null | undefined;
  /** 欄位名（`main_hand`…）：物品沒有 `kind` 時用來選預設造型。 */
  slot?: string;
  size?: 32 | 48 | 64;
  /** 無障礙名稱（`aria-label`）；不是原生 tooltip（要說明請用 `Hint`／`PartTip`）。 */
  label?: string;
}

export function GearIcon({ look, slot, size = 32, label }: Props) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const target = ref.current;
    const ctx = target?.getContext("2d");
    const art = gearIconCanvas(look, size, slot);
    if (target == null || ctx == null || art === null) return;
    ctx.clearRect(0, 0, target.width, target.height);
    ctx.drawImage(art, 0, 0);
  }, [look, slot, size]);
  return <canvas ref={ref} className="gear-icon" width={size * 2} height={size * 2} style={{ width: size, height: size }} aria-label={label} role={label === undefined ? undefined : "img"} />;
}
