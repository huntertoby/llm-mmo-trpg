// 組裝式技能圖示（Phase 3-17）：把 `render/skillIcon.ts` 快取好的離屏 canvas 貼到畫面上。
// 技能列 40px／28px、技能卡 88px、工坊預覽 96px 都用這一個元件；邊長 ≤ 40px 自動用小圖。
import { useEffect, useRef } from "react";
import type { SkillIconData } from "../api/types";
import { assemblyFormula, iconCacheKey, optionTile, skillIconCanvas, tileCanvas, type AssemblyTile } from "../render/skillIcon";
import { PartTip } from "./PartTip";

interface IconProps {
  /** 技能卡的 `icon`；舊資料沒有時不畫。 */
  icon: SkillIconData | null | undefined;
  size: number;
  /** 強制小圖模式（元素底色、主圖、外框、核心效果）；不填就依邊長（≤ 40px）決定。 */
  small?: boolean;
  className?: string;
  /** 無障礙名稱（`aria-label`）；不是原生 tooltip（要說明請用 `Hint`）。 */
  label?: string;
}

export function SkillIconView({ icon, size, small, className, label }: IconProps) {
  const ref = useRef<HTMLCanvasElement>(null);
  const key = icon == null ? null : iconCacheKey(icon, size, small);
  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (canvas == null || ctx == null || icon == null) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(skillIconCanvas(icon, size, small), 0, 0);
    // 圖示由 key 決定；icon 物件換了但內容相同時不必重畫
  }, [key, size, small]);
  if (icon == null) return null;
  return (
    <canvas
      ref={ref}
      className={`skill-icon${className === undefined ? "" : ` ${className}`}`}
      width={size * 2}
      height={size * 2}
      style={{ width: size, height: size }}
      role="img"
      aria-label={label ?? "技能圖示"}
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
  }, [tile.id, px]);
  return <canvas ref={ref} width={px * 2} height={px * 2} style={{ width: px, height: px }} aria-hidden="true" />;
}

/** 狀態、表面等單一部件的小圖＋名稱，滑過或點一下看說明（HUD 狀態列、單位資訊用）。 */
export function TipGlyph({ tile, px = 18, text, pin = true }: { tile: AssemblyTile; px?: number; text?: string; pin?: boolean }) {
  return (
    <PartTip cat={tile.cat} label={tile.label} tip={tile.tip} pin={pin} className="tip-glyph">
      <TileCanvas tile={tile} px={px} />
      <span>{text ?? tile.label}</span>
    </PartTip>
  );
}

function TileView({ tile, px }: { tile: AssemblyTile; px: number }) {
  return (
    <PartTip cat={tile.cat} label={tile.label} tip={tile.tip} className={`f-tile${tile.cat === "接續" ? " f-link" : ""}`}>
      <TileCanvas tile={tile} px={px} />
      <span className="f-label">{tile.label}</span>
    </PartTip>
  );
}

/**
 * 技能卡的組裝算式（Phase 3-18a）：每段一行「骨架 ＋ 形狀 ＋ 效果」，段間「↓ 接續名稱」，
 * 條件與代價在細線後。每個部件都可以滑過或點一下看說明。
 */
export function AssemblyFormula({ icon }: { icon: SkillIconData | null | undefined }) {
  if (icon == null) return null;
  const { rows, links, extras } = assemblyFormula(icon);
  return (
    <div className="formula" aria-label="技能的組成部件">
      {rows.map((tiles, i) => (
        <div key={i} className="f-seg">
          {i > 0 && links[i - 1] !== undefined && (
            <PartTip cat="接續" label={(links[i - 1] as AssemblyTile).label} tip={(links[i - 1] as AssemblyTile).tip} className="f-linkrow">
              ↓ {(links[i - 1] as AssemblyTile).label}
            </PartTip>
          )}
          <div className="f-row">
            {tiles.map((t, j) => (
              <span key={`${j}:${t.id}`} className="f-item">
                {j > 0 && <span className="f-plus">＋</span>}
                <TileView tile={t} px={30} />
              </span>
            ))}
          </div>
        </div>
      ))}
      {extras.length > 0 && (
        <div className="f-extras">
          {extras.map((t, i) => (
            <PartTip key={`${i}:${t.id}`} cat={t.cat} label={t.label} tip={t.tip} className="f-extra">
              <TileCanvas tile={t} px={18} />
              <span>
                {t.cat}：{t.label}
              </span>
            </PartTip>
          ))}
        </div>
      )}
    </div>
  );
}

/** 工坊選項旁的小圖（與技能圖示共用部件）；這個欄位沒有圖示時不畫。 */
export function OptionGlyph({ field, value, px = 26 }: { field: string; value: unknown; px?: number }) {
  const tile = optionTile(field, value);
  if (tile === null) return null;
  return (
    <PartTip cat={tile.cat} label={tile.label} tip={tile.tip} pin={false} className="opt-glyph">
      <TileCanvas tile={tile} px={px} />
    </PartTip>
  );
}
