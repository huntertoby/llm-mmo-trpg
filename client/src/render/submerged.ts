// 半沉在深水裡的物件（Phase 6F-6；美術 PM 6V-2b 檢查第 3 節第 1 點：灰渡口「半沉的舊渡船」兩個木箱
// 看起來像浮在深水上的乾箱子）。只改畫法：物件站在畫成深水的深淵格（`look.chasm_style: deep_water`）上時，
// 下緣加一條水線，水線以下半透明並蓋一層水色。規則（地形仍是 chasm、物件照舊）都不動。純函式。
import { chasmStyleOf } from "./regionArt";

/** 水線在格子裡的高度（0 ＝ 格頂、1 ＝ 格底）；木箱畫在 0.2～0.85 之間，水線落在中間偏下。 */
export const WATERLINE = 0.6;
/** 水線以下那一段物件的不透明度。 */
export const SUBMERGED_ALPHA = 0.45;
/** 水線以下疊的水色（同深水的底色 `DEEP_WATER.base` #34495c）。 */
export const SUBMERGED_TINT = 0x34495c;
/** 水線的顏色（淡淡的亮藍，同深水波紋的 `DEEP_WATER.ripple` 色相）與不透明度。 */
export const WATERLINE_COLOR = 0xb0c8de;
export const WATERLINE_ALPHA = 0.7;

interface Grid {
  width: number;
  look: string;
  tiles: ReadonlyArray<{ terrain: string }>;
}

/** 這個物件半沉在水裡：所在格是深淵、而且這張地圖的深淵畫成深水。 */
export function isSubmerged(model: Grid, o: { x: number; y: number }): boolean {
  if (chasmStyleOf(model.look) !== "deep_water") return false;
  return model.tiles[o.y * model.width + o.x]?.terrain === "chasm";
}

/**
 * 水線（模型像素，相對格子左上）：一條橫線加兩個小波紋弧，左右各留 `inset` 不碰格邊；
 * 回傳線段與弧的資料，畫布照著畫（`BattleRenderer.objectSprite`）。
 */
export function waterline(cell: number, inset = 0.14): { y: number; x0: number; x1: number; ripples: Array<{ x: number; r: number }> } {
  const y = Math.round(cell * WATERLINE);
  const x0 = Math.round(cell * inset);
  const x1 = Math.round(cell * (1 - inset));
  return { y, x0, x1, ripples: [{ x: Math.round(cell * 0.3), r: 3 }, { x: Math.round(cell * 0.68), r: 4 }] };
}
