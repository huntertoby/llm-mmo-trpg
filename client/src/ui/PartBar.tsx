// 頭目部位的小血條與部位圖示（PB-1c；美術移植需求 docs/art/頭目部位-移植需求.md 2.1、2.2、3.1）。
// 選部位小選單（`PartMenu`）與角色卡（`UnitInfo`）共用。顏色在 CSS `.part-bar`（完好米白、空槽灰紫、已破壞暗紅底＋紅「×」、
// 未露出或看不到資訊＝幾乎黑、不寫數字）；圖示是 `render/qIcon/bossParts.ts` 的 Q 版畫布（20px，畫布＝顯示 × 2）。
import type { PartBarState } from "../battle/partMenu";
import { ICON_RES } from "../render/qIcon/core";
import { blank, ctxOf, OUT } from "../render/qIcon/core";
import { bossPartIcon, bossPartIconKey, grayIcon, type BossDoll } from "../render/qIcon/bossParts";
import { IconCanvas } from "./HudGlyph";

/** 選單圖示的顯示邊長（CSS px）。 */
export const PART_ICON_PX = 20;
/** 原因「從背後」的小圖（CSS px）。 */
export const PART_BACK_PX = 16;
/** 已破壞的紅「×」（選單圖示上；樣張 drawMenu 的 `UI.danger`）。 */
const ICON_X = "#ff6a5a";

/** 部位條（`.part-bar`）。`numbers`：完好時在條右邊寫「hp/max」。 */
export function PartBar({ state, numbers = true }: { state: PartBarState; numbers?: boolean }) {
  if (state.kind === "hidden") return <span className="part-bar hidden" data-state="hidden" aria-label="未露出" />;
  if (state.kind === "broken")
    return (
      <span className="part-bar broken" data-state="broken" aria-label="已破壞">
        <svg className="part-bar-x" viewBox="0 0 10 10" aria-hidden="true">
          <path d="M2 2 L8 8 M8 2 L2 8" stroke={OUT} strokeWidth="3.4" strokeLinecap="round" />
          <path d="M2 2 L8 8 M8 2 L2 8" stroke="#ff5a4a" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
      </span>
    );
  const ratio = state.max <= 0 ? 0 : Math.max(0, Math.min(1, state.hp / state.max));
  return (
    <>
      <span className="part-bar" data-state="ok" role="img" aria-label={`${state.hp}/${state.max}`}>
        <i className="part-bar-fill" style={{ width: `${ratio * 100}%` }} />
      </span>
      {numbers && (
        <span className="part-bar-num">
          {state.hp}/{state.max}
        </span>
      )}
    </>
  );
}

/** 部位圖示的畫布：打不到灰掉、已破壞再壓紅「×」（外框色襯邊）。 */
function partIconCanvas(id: string, px: number, ok: boolean, broken: boolean, doll: BossDoll | null): HTMLCanvasElement {
  const base = bossPartIcon(id, px, ICON_RES, doll);
  const S = Math.round(px * ICON_RES);
  const out = blank(S, S);
  if (base === null) return out;
  const c = ctxOf(out);
  c.drawImage(ok ? base : grayIcon(base), 0, 0);
  if (broken) {
    c.save();
    c.scale(ICON_RES, ICON_RES);
    c.lineCap = "round";
    const k = px / 20;
    for (const [col, lw] of [
      [OUT, 3.4],
      [ICON_X, 1.8],
    ] as const) {
      c.strokeStyle = col;
      c.lineWidth = lw;
      c.beginPath();
      c.moveTo(3 * k, 3 * k);
      c.lineTo(17 * k, 17 * k);
      c.moveTo(17 * k, 3 * k);
      c.lineTo(3 * k, 17 * k);
      c.stroke();
    }
    c.restore();
  }
  return out;
}

/** 部位圖示（`body`＝頭目小頭像）。 */
export function PartIcon({ id, ok, broken, doll, px = PART_ICON_PX }: { id: string; ok: boolean; broken: boolean; doll: BossDoll | null; px?: number }) {
  const key = `${bossPartIconKey(id, px, ICON_RES, doll)}|${ok ? 1 : 0}|${broken ? 1 : 0}`;
  return <IconCanvas px={px} className="part-icon" cacheKey={key} make={() => partIconCanvas(id, px, ok, broken, doll)} data={{ "data-part": id }} />;
}
