// 組裝式技能圖示（Phase 3-17）：把 `render/skillIcon.ts` 快取好的離屏 canvas 貼到畫面上。
// 技能列 40px／28px、技能卡 88px、工坊預覽 96px 都用這一個元件；邊長 ≤ 40px 自動用小圖。
import { useEffect, useRef } from "react";
import type { SkillIconData } from "../api/types";
import { assemblyTiles, iconCacheKey, optionTile, skillIconCanvas, tileCanvas, tileTitle, type AssemblyTile } from "../render/skillIcon";

interface IconProps {
  /** 技能卡的 `icon`；舊資料沒有時不畫。 */
  icon: SkillIconData | null | undefined;
  size: number;
  className?: string;
  title?: string;
}

export function SkillIconView({ icon, size, className, title }: IconProps) {
  const ref = useRef<HTMLCanvasElement>(null);
  const key = icon == null ? null : iconCacheKey(icon, size);
  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (canvas == null || ctx == null || icon == null) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(skillIconCanvas(icon, size), 0, 0);
    // 圖示由 key 決定；icon 物件換了但內容相同時不必重畫
  }, [key, size]); // eslint-disable-line react-hooks/exhaustive-deps
  if (icon == null) return null;
  return (
    <canvas
      ref={ref}
      className={`skill-icon${className === undefined ? "" : ` ${className}`}`}
      width={size * 2}
      height={size * 2}
      style={{ width: size, height: size }}
      title={title}
      role="img"
      aria-label={title ?? "技能圖示"}
    />
  );
}

function TileCanvas({ tile, px }: { tile: AssemblyTile; px: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (canvas == null || ctx == null) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(tileCanvas(tile, px), 0, 0);
  }, [tile.id, px]); // eslint-disable-line react-hooks/exhaustive-deps
  return <canvas ref={ref} width={px * 2} height={px * 2} style={{ width: px, height: px }} aria-hidden="true" />;
}

/** 技能卡上方的組裝列：每個部件一塊（類別、小圖、名稱），滑過顯示「部件類別：名稱（在圖示上的位置）」。 */
export function AssemblyRow({ icon, px = 44 }: { icon: SkillIconData | null | undefined; px?: number }) {
  if (icon == null) return null;
  const tiles = assemblyTiles(icon);
  return (
    <div className="asm" aria-label="技能的組成部件">
      {tiles.map((t, i) => (
        <div key={`${i}:${t.id}`} className={`asm-tile ${t.cat === "接續" ? "asm-link" : "asm-part"}`} title={tileTitle(t)}>
          <div className="asm-cat">{t.cat}</div>
          <TileCanvas tile={t} px={px} />
          <div className="asm-label">{t.label}</div>
        </div>
      ))}
    </div>
  );
}

/** 工坊選項旁的小圖（與技能圖示共用部件）；這個欄位沒有圖示時不畫。 */
export function OptionGlyph({ field, value, px = 26 }: { field: string; value: unknown; px?: number }) {
  const tile = optionTile(field, value);
  if (tile === null) return null;
  return (
    <span className="opt-glyph" title={tileTitle(tile)}>
      <TileCanvas tile={tile} px={px} />
    </span>
  );
}
