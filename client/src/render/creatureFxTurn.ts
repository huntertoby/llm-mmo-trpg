// CB-3c／CB-4：異形（含頭目）片段自帶的特效（白弧、星爆、塵土、掃尾）在目標不在同一排時的落點。
//
// 成因（讀程式確認）：片段的特效是 `qCreaturePartPose`／`bossPlan` 給的「異形自己的側面座標」（朝東、腳底為原點，相鄰目標在 x ＝ 52），
// 跟身體一起畫進身體貼圖（`inkCreature.drawCreature` → `drawCreatureFx`；頭目 `qBoss.bossAct`），貼圖照 `creatureSide` 左右鏡射。
// 異形只有東、西兩面，出招時用 `creatureFacingTo`（同一欄維持原朝向），所以目標在正南、正北、斜向時，特效還是畫在施放者那一排；
// 站在最右欄（或最左欄）又剛好朝外時，特效畫到地圖外被畫布裁掉。
//
// 修法：目標不在同一排（`creatureFxTurnOf` 回方向 (x, y)，y ≠ 0）時，特效不畫進身體貼圖，另畫一張（`inkCreature.renderCreatureFxCanvas`）。
// 「剪切」（CB-4 Q1）：以「相鄰目標」那一點為原點，u ＝ x − 52（虛擬單位）→ (|方向 x| × u, y ＋ 方向 y × u × c)：
// 橫向距離照舊（斜向）或收到中線（同一欄）、往前的距離另外加上往南／往北的分量。`c` 讓 u ＝ −52（異形自己）剛好往回一格。
// 原點放在目標方向的相鄰格中心（`creatureFxAnchorPx`）；貼圖照 `creatureSide` 鏡射。同一欄（方向 x ＝ 0）就是 CB-3c 的公式；
// 同一排（東西向）不轉，照舊畫進身體貼圖。白弧、星爆的形狀不轉，只搬位置（CB-3c 美術 PM 裁定第 3 點、CB-4 D3）。
import type { Pos } from "../api/types";
import type { CreatureFx, FxTurn } from "./creaturePose";
import { CREATURE_FX_TARGET_X } from "./qCreatureAnim";

/** 異形畫法的虛擬格寬（模型像素 ＝ 虛擬單位 × 格寬 / 52 × 紙娃娃縮放，見 `unitSprite.creatureOffsetPx`）。 */
const VIRTUAL_TILE = 52;

/** 目標相對施放者的方向（sign(dx)、sign(dy)）；同一排（東西向）、自己、沒有目標 → `null`（不轉）。 */
export function creatureFxTurnOf(from: Pos, to: Pos | null): FxTurn | null {
  if (to === null || to.y === from.y) return null;
  return { x: to.x > from.x ? 1 : to.x < from.x ? -1 : 0, y: to.y > from.y ? 1 : -1 };
}

/**
 * 轉向時「往前一個虛擬單位」換成幾個（未乘大小的）虛擬單位往南／往北：讓 `CREATURE_FX_TARGET_X` 剛好是一格。
 * `size`：異形的大小（含精英；頭目傳 1，貼圖不含大小）；`fieldScale`：戰場額外縮放（頭目 1.6）；`dollScale`：紙娃娃縮放（`DOLL_SCALE`）。
 */
export function fxTurnScale(size: number, fieldScale: number, dollScale: number): number {
  return VIRTUAL_TILE / (CREATURE_FX_TARGET_X * size * fieldScale * dollScale);
}

/**
 * 把片段的特效轉向目標方向（剪切）：原點在「相鄰目標」那一點；橫向 ×|方向 x|（同一欄收到中線），往前的距離 × c 加到南北。
 * 方向 x ＝ 0 時和 CB-3c 逐筆相同（同一條算式）。
 */
export function turnCreatureFx(fxs: readonly CreatureFx[], turn: FxTurn, c: number): CreatureFx[] {
  const sx = turn.x === 0 ? 0 : 1;
  const tx = (x: number): number => (sx === 0 ? 0 : x - CREATURE_FX_TARGET_X);
  const ty = (x: number, y: number): number => y + turn.y * (x - CREATURE_FX_TARGET_X) * c;
  return fxs.map((f) => {
    const out: CreatureFx = { ...f, x: tx(f.x ?? 0), y: ty(f.x ?? 0, f.y ?? 0) };
    if (f.x0 !== undefined || f.y0 !== undefined) Object.assign(out, { x0: tx(f.x0 ?? 0), y0: ty(f.x0 ?? 0, f.y0 ?? 0) });
    if (f.x1 !== undefined || f.y1 !== undefined) Object.assign(out, { x1: tx(f.x1 ?? 0), y1: ty(f.x1 ?? 0, f.y1 ?? 0) });
    if (f.k === "cone") Object.assign(out, turnCone(f.ang ?? 0, f.max ?? 30, sx, turn.y, c));
    return out;
  });
}

/** 吐息的方向（往前 ＝ 0）照同一規則換算：方向向量 (cos, sin) → (|方向 x| × cos, 方向 y × c × cos ＋ sin)，長度照比例。 */
function turnCone(a: number, max: number, sx: 0 | 1, ty: -1 | 1, c: number): { ang: number; max: number } {
  if (sx === 0) {
    // CB-3c 原式（同一欄）
    const v = ty * c * Math.cos(a) + Math.sin(a);
    return { ang: v >= 0 ? Math.PI / 2 : -Math.PI / 2, max: max * Math.abs(v) };
  }
  const vx = Math.cos(a);
  const vy = ty * c * Math.cos(a) + Math.sin(a);
  return { ang: Math.atan2(vy, vx), max: max * Math.hypot(vx, vy) };
}

export interface FxAnchorInput {
  from: Pos;
  to: Pos;
  /** 畫出來的那一面（`creatureSide`）。 */
  side: "east" | "west";
  /** 異形的大小（含精英；頭目傳 1，貼圖不含大小）。 */
  size: number;
  fieldScale: number;
  dollScale: number;
  /** 一格的模型像素（`TILE_SIZE`）。 */
  tile: number;
}

/**
 * 片段特效的錨點（「相鄰目標」那一點，腳底高度）相對施放者腳底的位置（模型像素，平地）。
 * 不在同一排：目標方向的相鄰格中心（方向 × 一格）；同一排（東西向）：照舊畫在身體貼圖裡的位置（朝向 × 52 個虛擬單位）。
 */
export function creatureFxAnchorPx(o: FxAnchorInput): { x: number; y: number } {
  const turn = creatureFxTurnOf(o.from, o.to);
  if (turn !== null) return { x: turn.x * o.tile + 0, y: turn.y * o.tile };
  const k = (o.tile / VIRTUAL_TILE) * o.dollScale * o.fieldScale * o.size;
  return { x: (o.side === "west" ? -1 : 1) * CREATURE_FX_TARGET_X * k + 0, y: 0 };
}
