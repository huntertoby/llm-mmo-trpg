// 武器小圖示（Phase 3-18b）：畫在小 canvas 上，與地圖小人手持的武器同一套畫法。
import { useEffect, useRef } from "react";
import { iconCanvasPx, weaponIconCanvas } from "../render/weaponIcon";

interface Props {
  weaponId: string;
  weaponClass: string;
  size?: number;
}

export function WeaponIcon({ weaponId, weaponClass, size = 28 }: Props) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const target = ref.current;
    const ctx = target?.getContext("2d");
    const art = weaponIconCanvas(weaponId, weaponClass, size);
    if (target == null || ctx == null || art === null) return;
    ctx.clearRect(0, 0, target.width, target.height);
    ctx.drawImage(art, 0, 0);
  }, [weaponId, weaponClass, size]);
  const cv = iconCanvasPx(size); // QI-1b：畫布寬高一律 round(顯示 CSS px × ICON_RES)，CSS 不縮放
  return <canvas ref={ref} className="weapon-icon" width={cv} height={cv} style={{ width: size, height: size }} aria-hidden="true" />;
}
