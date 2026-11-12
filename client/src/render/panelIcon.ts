// 資訊面板的小圖示（PNL-1a；docs/art/資訊面板-移植需求.md 2.3）：一張都不新畫，全部呼叫已移植的 Q 版畫法，這裡只做畫布與快取。
// - 事件卡圖示的「圖樣本身」（不帶深底圓與色環）：`qIcon/event.ts` 的 `bareGlyph`（QI-6 裁定 6：快取在這段加）；
// - 事件卡圖示（深底圓＋色環，例：提示「資訊」級的 `info`）：`qIcon/event.ts` 的 `canvas`；
// - 第④批部件圖樣不帶圓片（例：金鎖＝`skeleton:control`、鐘＝`card:cooldown`）：照樣張 `infoPanels.js` 的 `part()`，
//   圖樣本身＝px ÷ `QP.BOX`。
// 畫布邊長＝顯示 × res（預設 `ICON_RES` 2），CSS 不縮放（上手筆記第四節第 19 點）；同一鍵只畫一次。
import { blank, ctxOf, ICON_RES } from "./qIcon/core";
import * as QE from "./qIcon/event";
import * as QP from "./qIcon/parts";

export type PanelIconKind = "bare" | "event" | "part";

/** 快取鍵：種類、圖示（部件＝`cat:id`）、顯示邊長、內部解析度。 */
export const panelIconKey = (kind: PanelIconKind, id: string, px: number, res: number = ICON_RES): string => [kind, id, px, res].join("|");

const CACHE_LIMIT = 128;
const cache = new Map<string, HTMLCanvasElement>();

function remember(key: string, make: () => HTMLCanvasElement): HTMLCanvasElement {
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  const cv = make();
  if (cache.size >= CACHE_LIMIT) {
    const oldest = cache.keys().next().value;
    if (oldest !== undefined) cache.delete(oldest);
  }
  cache.set(key, cv);
  return cv;
}

/** 事件卡圖示的圖樣本身（`QE.bareGlyph`）；沒有畫布時回空白畫布（同邊長）。 */
export function eventBareCanvas(id: string, px: number, res: number = ICON_RES): HTMLCanvasElement {
  return remember(panelIconKey("bare", id, px, res), () => QE.bareGlyph(id, px, res) ?? blank(Math.round(px * res)));
}

/** 事件卡圖示（深底圓＋色環，`QE.canvas`）。 */
export function eventIconCanvas(id: string, px: number, res: number = ICON_RES): HTMLCanvasElement {
  return remember(panelIconKey("event", id, px, res), () => QE.canvas(id, px, res));
}

/** 第④批部件圖樣（不帶圓片）：px＝整格邊長，圖樣本身＝px ÷ `QP.BOX`（樣張 `part()`）。 */
export function partGlyphCanvas(cat: string, id: string, px: number, res: number = ICON_RES): HTMLCanvasElement {
  return remember(panelIconKey("part", `${cat}:${id}`, px, res), () => {
    const cv = blank(Math.round(px * res));
    const x = ctxOf(cv);
    x.scale(res, res);
    QP.paint(x, cat, id, px / 2, px / 2, px / QP.BOX, 1, res);
    x.setTransform(1, 0, 0, 1, 0, 0);
    return cv;
  });
}

/** 測試換畫布後清快取。 */
export function clearPanelIconCache(): void {
  cache.clear();
}

/** 快取裡現在有幾張（測試用）。 */
export const panelIconCacheSize = (): number => cache.size;
