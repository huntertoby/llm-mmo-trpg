// CB-3c：異形片段自帶的特效（白弧、星爆、塵土）在目標正南／正北時的落點。
//
// 成因（讀程式確認）：片段的特效是 `qCreaturePartPose` 給的「異形自己的側面座標」（朝東、腳底為原點，相鄰目標在 x ＝ 52），
// 跟身體一起畫進身體貼圖（`inkCreature.drawCreature` → `drawCreatureFx`），貼圖照 `creatureSide` 左右鏡射。異形只有東、西兩面，
// 出招時用 `creatureFacingTo`（同一欄維持原朝向），所以目標在正南、正北時，特效還是往東或往西畫到側邊的空格；
// 站在最右欄（或最左欄）又剛好朝外時，特效畫到地圖外被畫布裁掉。
//
// 修法：只在「同一欄」時，特效不畫進身體貼圖，另畫一張（`inkCreature.renderCreatureFxCanvas`）。把「往前」的距離轉成往南／往北：
// 腳底座標 (x, y) → (0, y ＋ 轉向 ×（x − 52）× c)，`c` 讓「相鄰目標」那一點（52, 0）剛好落在相鄰那一格的中心、異形自己（x ＝ 0）
// 留在原地；高度（y）照舊。東西向、斜向的目標不變（照舊畫進身體貼圖）。
import type { Pos } from "../api/types";
import type { CreatureFx } from "./creaturePose";
import { CREATURE_FX_TARGET_X } from "./qCreatureAnim";

/** 異形畫法的虛擬格寬（模型像素 ＝ 虛擬單位 × 格寬 / 52 × 紙娃娃縮放，見 `unitSprite.creatureOffsetPx`）。 */
const VIRTUAL_TILE = 52;

/** 目標和施放者同一欄（正南 1、正北 -1）；其他（東西向、斜向、自己、沒有目標）→ `null`。 */
export function creatureFxTurnOf(from: Pos, to: Pos | null): 1 | -1 | null {
  if (to === null || to.x !== from.x || to.y === from.y) return null;
  return to.y > from.y ? 1 : -1;
}

/**
 * 轉向時「往前一個虛擬單位」換成幾個（未乘大小的）虛擬單位往南／往北：讓 `CREATURE_FX_TARGET_X` 剛好是一格。
 * `size`：異形的大小（含精英）；`fieldScale`：戰場額外縮放（頭目）；`dollScale`：紙娃娃縮放（`DOLL_SCALE`）。
 */
export function fxTurnScale(size: number, fieldScale: number, dollScale: number): number {
  return VIRTUAL_TILE / (CREATURE_FX_TARGET_X * size * fieldScale * dollScale);
}

/** 把片段的特效轉向正南（1）／正北（-1）：橫向收到中線，往前的距離改成往南／往北，原點在「相鄰目標」那一點。 */
export function turnCreatureFx(fxs: readonly CreatureFx[], turn: 1 | -1, c: number): CreatureFx[] {
  const ty = (x: number, y: number): number => y + turn * (x - CREATURE_FX_TARGET_X) * c;
  return fxs.map((f) => {
    const out: CreatureFx = { ...f, x: 0, y: ty(f.x ?? 0, f.y ?? 0) };
    if (f.x0 !== undefined || f.y0 !== undefined) Object.assign(out, { x0: 0, y0: ty(f.x0 ?? 0, f.y0 ?? 0) });
    if (f.x1 !== undefined || f.y1 !== undefined) Object.assign(out, { x1: 0, y1: ty(f.x1 ?? 0, f.y1 ?? 0) });
    if (f.k === "cone") {
      // 吐息的方向（往前 ＝ 0）：往前的分量換成往南／往北，長度照比例
      const a = f.ang ?? 0;
      const v = turn * c * Math.cos(a) + Math.sin(a);
      Object.assign(out, { ang: v >= 0 ? Math.PI / 2 : -Math.PI / 2, max: (f.max ?? 30) * Math.abs(v) });
    }
    return out;
  });
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
 * 同一欄：剛好是相鄰那一格的中心（0, ±一格）；其他：照舊畫在身體貼圖裡的位置（朝向 × 52 個虛擬單位）。
 */
export function creatureFxAnchorPx(o: FxAnchorInput): { x: number; y: number } {
  const turn = creatureFxTurnOf(o.from, o.to);
  if (turn !== null) return { x: 0, y: turn * o.tile };
  const k = (o.tile / VIRTUAL_TILE) * o.dollScale * o.fieldScale * o.size;
  return { x: (o.side === "west" ? -1 : 1) * CREATURE_FX_TARGET_X * k + 0, y: 0 };
}
