// 四角飾件（RT-1；docs/art/區域主題移植需求.md 第 1 節「四角飾件的畫法」、樣張 docs/art/sample/region-themes.html 的 corner()）。
// 每種約 18×18，程式繪製成 SVG（左上角的方向），其他三角左右／上下鏡射。結果是 CSS 背景圖層（`--rt-corners`），
// 疊在主框的 `::after` 上（不接滑鼠、不佔版面），所以版面、字型、按鈕都不變。純函式。
export const CORNER_KINDS = ["filigree", "cloud", "rivet", "shard", "gear", "shell"] as const;
export type CornerKind = (typeof CORNER_KINDS)[number];

/** 飾件邊長（CSS 像素）與離主框外緣的距離。 */
export const CORNER_SIZE = 18;
export const CORNER_INSET = 2;

const GOLD2 = "#e8bb48";

interface CornerColors {
  accent: string;
  seal: string;
}

/** 一種飾件的 SVG 內容（左上角方向、18×18 座標）。 */
export function cornerShapes(kind: CornerKind, c: CornerColors): string {
  switch (kind) {
    case "cloud": // 雲嶺：雲紋兩捲加朱紅點
      return (
        `<path d="M4 10A6 6 0 0 1 15.4 7.4" fill="none" stroke="${c.accent}" stroke-width="1.6" stroke-linecap="round"/>` +
        `<path d="M12 5A3 3 0 0 1 17.5 4" fill="none" stroke="${c.accent}" stroke-width="1.6" stroke-linecap="round"/>` +
        `<path d="M6 14A3 3 0 0 1 6 8" fill="none" stroke="${c.accent}" stroke-width="1.2" stroke-linecap="round"/>` +
        `<circle cx="4" cy="4" r="2.5" fill="${c.seal}"/>`
      );
    case "rivet": // 荒原：鐵角加三顆鉚釘、一點餘燼
      return (
        `<path d="M0 0H18V6H6V18H0Z" fill="#5a5a60"/>` +
        `<path d="M0 0H18V1H1V18H0Z" fill="#7a7a80"/>` +
        `<circle cx="3" cy="3" r="1.6" fill="#9a9aa0"/><circle cx="12" cy="3" r="1.6" fill="#9a9aa0"/><circle cx="3" cy="12" r="1.6" fill="#9a9aa0"/>` +
        `<rect x="15" y="2" width="3" height="2" fill="${c.accent}" opacity="0.75"/>`
      );
    case "shard": // 晶冠：藍紫晶片
      return (
        `<path d="M1 1L11 3L4 10Z" fill="${c.accent}" stroke="#eef2ff" stroke-width="0.6"/>` +
        `<path d="M12 1L17 2L13 6Z" fill="${c.seal}" stroke="#eef2ff" stroke-width="0.5"/>` +
        `<path d="M1 12L3 17L6 13Z" fill="${c.seal}" stroke="#eef2ff" stroke-width="0.5"/>`
      );
    case "gear": // 樞市：黃銅半齒輪
      return (
        `<g fill="#b08a3a" stroke="#5a4418" stroke-width="0.6">` +
        `<path d="M0 0H10A10 10 0 0 1 0 10Z"/>` +
        `<rect x="9" y="-1.5" width="4" height="3" transform="rotate(15)"/>` +
        `<rect x="9" y="-1.5" width="4" height="3" transform="rotate(45)"/>` +
        `<rect x="9" y="-1.5" width="4" height="3" transform="rotate(75)"/>` +
        `</g>` +
        `<circle cx="0" cy="0" r="4" fill="${c.accent}"/>`
      );
    case "shell": // 霜潮：貝殼加浪紋
      return (
        `<path d="M2 2L13 4A9 9 0 0 1 4 13Z" fill="#efe2d2" stroke="#8a6a5a" stroke-width="0.6"/>` +
        `<path d="M2 2L11 8M2 2L8 11" stroke="#8a6a5a" stroke-width="0.6"/>` +
        `<path d="M0 17Q2 15 4 17T8 17T12 17" fill="none" stroke="${c.accent}" stroke-width="1.2" stroke-linecap="round"/>` +
        `<circle cx="15" cy="4" r="1.4" fill="${c.seal}"/>`
      );
    case "filigree": // 主城、hub：金色捲紋加紫晶菱形
    default:
      return (
        `<path d="M0 16Q0 0 16 0" fill="none" stroke="${GOLD2}" stroke-width="1.6"/>` +
        `<path d="M7 2L10 7L7 12L4 7Z" fill="${c.accent}" stroke="#f2eaff" stroke-width="0.6"/>`
      );
  }
}

export type CornerAt = "tl" | "tr" | "bl" | "br";
export const CORNER_AT: readonly CornerAt[] = ["tl", "tr", "bl", "br"];

/** 一角的 SVG（`tr` 左右鏡射、`bl` 上下鏡射、`br` 兩個都鏡射）。 */
export function cornerSvg(kind: CornerKind, c: CornerColors, at: CornerAt = "tl"): string {
  const sx = at === "tr" || at === "br" ? -1 : 1;
  const sy = at === "bl" || at === "br" ? -1 : 1;
  const tx = sx < 0 ? CORNER_SIZE : 0;
  const ty = sy < 0 ? CORNER_SIZE : 0;
  const s = CORNER_SIZE;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${s}" height="${s}" viewBox="0 0 ${s} ${s}"><g transform="translate(${tx} ${ty}) scale(${sx} ${sy})">${cornerShapes(kind, c)}</g></svg>`;
}

const POS: Readonly<Record<CornerAt, string>> = {
  tl: `left ${CORNER_INSET}px top ${CORNER_INSET}px`,
  tr: `right ${CORNER_INSET}px top ${CORNER_INSET}px`,
  bl: `left ${CORNER_INSET}px bottom ${CORNER_INSET}px`,
  br: `right ${CORNER_INSET}px bottom ${CORNER_INSET}px`,
};

/** 四角的 CSS 背景圖層（逗號分隔，給 `background:`）。 */
export function cornerLayers(kind: CornerKind, c: CornerColors): string {
  return CORNER_AT.map((at) => `url("data:image/svg+xml,${encodeURIComponent(cornerSvg(kind, c, at))}") ${POS[at]} / ${CORNER_SIZE}px ${CORNER_SIZE}px no-repeat`).join(", ");
}
