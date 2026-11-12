// 技能卡常駐行的小圖示（Phase 6A-1；畫法移植自 docs/art/sample/textless.html 第 1 組的 symbol）。
// 不帶文字；說明卡由外層的 `Hint` 提供（名稱＋現值＋原本的句子）。
// QI-2c：`ChipGlyph`（16）、`EffectGlyph`（18）、`PinGlyph`（13）改畫 Q 版 canvas（`QP.cardCanvas`，經 `render/skillIcon.ts` 的 `cardGlyphCanvas` 快取），
// 畫布寬高＝顯示 × `ICON_RES`、CSS 不縮放。圖釘收 `pinned`（已釘紅頭、未釘灰鋼 55%）：canvas 不吃 CSS 的 `currentColor`，呼叫端要傳實際狀態。
// 下面的 SVG（`LEGACY_CHIP_PATHS`、`legacyEffectPath`）是舊畫法，留著不刪（規格第 0 節第 11 列）。
import { useEffect, useRef, type ReactNode } from "react";
import { elementColor } from "../render/palette";
import { cardGlyphCanvas, cardGlyphKey, effectGlyphTint, type CardGlyphOpt } from "../render/skillIcon";
import { iconCanvasPx } from "../render/weaponIcon";
import type { ChipIcon, EffectIcon } from "./skillCardLines";

const INK = "#1c1712";

/** 舊畫法（QI-2c 前的 SVG），不再使用。 */
export const LEGACY_CHIP_PATHS: Readonly<Record<ChipIcon, ReactNode>> = {
  ap: <polygon points="11,1 4,11 9,11 7,19 16,8 11,8" fill="#ffd23a" stroke={INK} strokeWidth="1.5" />,
  mana: <path d="M10 2C6 8 4 11 4 13a6 6 0 0 0 12 0c0-2-2-5-6-11z" fill="#4a8ae0" stroke={INK} strokeWidth="1.5" />,
  stamina: <path d="M3 10h4l2-5 3 10 2-5h3" stroke="#c8a030" strokeWidth="2.2" fill="none" />,
  hp: <path d="M10 17S3 12 3 7a3.5 3.5 0 0 1 7-1 3.5 3.5 0 0 1 7 1c0 5-7 10-7 10z" fill="#e04a3a" stroke={INK} strokeWidth="1.5" />,
  source: <polygon points="10,1 13,8 19,8 14,12 16,19 10,15 4,19 6,12 1,8 7,8" fill="#c8bcff" stroke={INK} strokeWidth="1.3" />,
  uses: (
    <>
      <rect x="3" y="4" width="14" height="12" rx="2" fill="none" stroke="#e8dcc0" strokeWidth="2" />
      <path d="M7 10h6" stroke="#e8dcc0" strokeWidth="2" />
    </>
  ),
  cooldown: (
    <>
      <circle cx="10" cy="10" r="7.5" fill="none" stroke="#8ab8f0" strokeWidth="2.5" />
      <path d="M10 4v6l4 2" stroke="#8ab8f0" strokeWidth="2" fill="none" />
    </>
  ),
  range: (
    <>
      <rect x="2" y="7" width="6" height="6" fill="#ffd23a" stroke={INK} />
      <rect x="8" y="7" width="6" height="6" fill="#e04a3a" stroke={INK} />
      <rect x="14" y="7" width="4" height="6" fill="#3a3028" stroke={INK} />
    </>
  ),
  reaction: (
    <>
      <path d="M4 10a6 6 0 1 1 2 4.5" stroke="#5ad06a" strokeWidth="2.5" fill="none" />
      <path d="M3 15l3-1-1-3" stroke="#5ad06a" strokeWidth="2" fill="none" />
    </>
  ),
  trigger: <path d="M11 2 5 11h4l-1 7 6-9h-4z" fill="#f0a040" stroke={INK} strokeWidth="1.3" />,
  delayed: (
    <>
      <circle cx="10" cy="10" r="7.5" fill="#f2e6c8" stroke={INK} strokeWidth="1.5" />
      <path d="M10 5v5l3 2" stroke={INK} strokeWidth="1.8" fill="none" />
    </>
  ),
  activation: <polygon points="10,2 12.5,7.5 18,8 14,12 15,18 10,15 5,18 6,12 2,8 7.5,7.5" fill="#ffb938" stroke={INK} strokeWidth="1.3" />,
  drawback: (
    <>
      <polygon points="10,2 18.5,17 1.5,17" fill="#e0a040" stroke={INK} strokeWidth="1.3" />
      <path d="M10 7v5M10 14v1.5" stroke={INK} strokeWidth="2" />
    </>
  ),
};

/** 舊畫法（QI-2c 前的 SVG），不再使用。 */
export function legacyEffectPath(icon: EffectIcon, color: string): ReactNode {
  switch (icon) {
    case "damage":
      return (
        <>
          <path d="M3 17L16 4" stroke={INK} strokeWidth="5" />
          <path d="M3 17L16 4" stroke={color} strokeWidth="2.5" />
        </>
      );
    case "heal":
      return <path d="M8 3h4v5h5v4h-5v5H8v-5H3V8h5z" fill="#7dffb0" stroke={INK} strokeWidth="1.3" />;
    case "shield":
      return <path d="M10 2l7 3v5c0 4-3 7-7 8-4-1-7-4-7-8V5z" fill="#9ab8d8" stroke={INK} strokeWidth="1.5" />;
    case "move":
      return <path d="M3 10h10M10 5l5 5-5 5" stroke="#f2e6c8" strokeWidth="3" fill="none" strokeLinecap="round" />;
    case "status":
      return <circle cx="10" cy="10" r="6.5" fill="#c8a0d8" stroke={INK} strokeWidth="1.5" />;
    case "surface":
      return <path d="M2 8q4-4 8 0t8 0M2 14q4-4 8 0t8 0" stroke="#5ab0f0" strokeWidth="2.5" fill="none" />;
    case "summon":
      return (
        <>
          <circle cx="10" cy="7" r="4" fill="#7dffb0" stroke={INK} strokeWidth="1.3" />
          <path d="M3 18c1-5 4-6 7-6s6 1 7 6z" fill="#7dffb0" stroke={INK} strokeWidth="1.3" />
        </>
      );
    case "stack":
      return (
        <>
          <rect x="4" y="11" width="12" height="5" rx="1" fill="#e8bb48" stroke={INK} />
          <rect x="4" y="6" width="12" height="5" rx="1" fill="#e8bb48" stroke={INK} />
        </>
      );
  }
}

/** 一個卡片小圖的 canvas（`id`＝`QP.CARD` 的鍵，`px`＝顯示邊長）。 */
function CardGlyphCanvas({ id, px, className, opt = {} }: { id: string; px: number; className: string; opt?: CardGlyphOpt }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const key = cardGlyphKey(id, px, undefined, opt);
  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (canvas == null || ctx == null) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(cardGlyphCanvas(id, px, undefined, opt), 0, 0);
    // 圖由 key 決定
  }, [key]);
  const cv = iconCanvasPx(px);
  return <canvas ref={ref} className={className} width={cv} height={cv} style={{ width: px, height: px }} aria-hidden="true" />;
}

/** 卡片小圖的顯示邊長（常駐行 16、效果行 18、圖釘 13；需求 4.4 第 25 點）。 */
export const CARD_GLYPH_PX = { chip: 16, effect: 18, pin: 13 } as const;

export function ChipGlyph({ icon }: { icon: ChipIcon }) {
  return <CardGlyphCanvas id={icon} px={CARD_GLYPH_PX.chip} className="skill-chip-glyph" />;
}

export function EffectGlyph({ icon, element }: { icon: EffectIcon; element: string | null }) {
  return <CardGlyphCanvas id={icon} px={CARD_GLYPH_PX.effect} className="skill-effect-glyph" opt={{ tint: effectGlyphTint(icon, element) }} />;
}

/** 縮放屬性：圓形徽章裡寫屬性的第一個字（力、敏、體、智、感、意）。 */
export function AttrGlyph({ label }: { label: string }) {
  return (
    <span className="skill-attr-glyph" aria-hidden="true">
      {label.slice(0, 1)}
    </span>
  );
}

/** 圖釘（QI-2c：Q 版 canvas；`pinned` 預設 true＝已釘紅頭，false＝未釘灰鋼 55%）。`HoverFloat` 的 `PinIcon` 不換（第 0.0 節）。 */
export function PinGlyph({ pinned = true }: { pinned?: boolean }) {
  return <CardGlyphCanvas id="pin" px={CARD_GLYPH_PX.pin} className="pin-glyph" opt={{ pinned }} />;
}

/** 舊畫法的效果色（QI-2c 前 `EffectGlyph` 的 SVG 用；現在由 `effectGlyphTint` 算同一個色）。 */
export const legacyEffectColor = (element: string | null): string => (element === null || element === "physical" ? "#e8eef4" : elementColor(element));
