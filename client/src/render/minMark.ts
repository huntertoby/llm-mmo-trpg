// 6F-9（美術 PM 6F-8 檢查第 2 節第 1 點：800 寬地圖縮到 65% 時，腳邊狀態圖示只剩約 4px 像一個藍點、高度標記「▲1」約 6px）：
// 這兩種標記有最小的畫面尺寸，地圖縮小時不再跟著縮（反向放大節點）；地圖夠大時（1600 寬 128%）倍率是 1，和原本一樣。
//
// 純函式；`BattleRenderer` 在建立節點與 `setScale` 時呼叫 `applyMarkScale`。

import type { Container, Text } from "pixi.js";

/** 狀態圖示畫出來的圖案（`paintStatusIcon` 的大小 ＝ 方框 − 2）在畫面上至少幾 px。 */
export const MIN_STATUS_GLYPH_PX = 10;
/** 高度標記的數字字級在畫面上至少幾 px（同樣的原則：和狀態圖示一樣 10px）。 */
export const MIN_HEIGHT_BADGE_FONT_PX = 10;
/** 召喚物回合數徽章的數字在畫面上至少幾 px（6F-11，美術 PM 6F-10b 檢查）。 */
export const MIN_BADGE_FONT_PX = 10;

/** 腳邊狀態列節點的標籤（`unitSprite.statusRow`）。 */
export const STATUS_ROW_LABEL = "status-row";
/** 高度標記節點的標籤（`BattleRenderer.drawBadges`）。 */
export const HEIGHT_BADGE_LABEL = "height-badge";
/** 召喚物回合數徽章節點的標籤（6F-10；6F-11 起自己也是標記，地圖縮小時反向放大）。 */
export const SUMMON_BADGE_LABEL = "summon-badge";
/** 炸彈、蓄力、灌注徽章節點的標籤（6F-12；自己也是標記）。 */
export const BOMB_BADGE_LABEL = "bomb-badge";
export const CHARGE_BADGE_LABEL = "charge-badge";
export const INFUSED_BADGE_LABEL = "infused-badge";
/**
 * 6F-21：移到 HP 條下面的朝南三角形。它超出格子下緣一點，南邊那一排的地面會蓋住它，
 * 所以改在南邊那一排的 `under` 層畫（`RowStack.attachMarks`）：在那排的地面之上、那排的單位之下。
 */
export const SOUTH_ARROW_LABEL = "south-arrow";
/** 6F-22：HP 條（含護盾條）節點的標籤（被南邊高台擋住時改在高台之上畫，`RowStack.attachHud`）。 */
export const HP_BAR_LABEL = "hp-bar";
/**
 * PB-1e：頭目的頭頂部位小格（HP 條正下方；`bossPartArt.partStripNode`）。跟著 HP 條掛同一層（`HUD_LABELS`）；
 * 自己也是標記：地圖縮放改變時照新縮放重畫（800 寬只放大高度），大小倍率固定 1。
 */
export const PART_STRIP_LABEL = "part-strip";
/** HID-1（決定 #144）：看不到資訊的隱蔽敵人，HP 條上的「？」（自己也是標記，地圖縮小時反向放大）。 */
export const HIDDEN_HP_LABEL = "hidden-hp";
/**
 * QK-9、HID-1c：底圈超出格子下緣的那一份（頭目放大的環；精英、頭目的金菱形）。南邊那一排的地面會蓋住它，
 * 所以另畫一份掛南邊那一排的 `under`（`RowStack.attachMarks`）。
 */
export const BOSS_RING_FRONT_LABEL = "boss-ring-front";
/** 6F-22：底圈外緣的朝向三角形（沒移到 HP 條下面的那三個朝向）。朝南、有 HP 條時是 `SOUTH_ARROW_LABEL`。 */
export const FACING_ARROW_LABEL = "facing-arrow";
/** 6F-22：倒下的人頭上的徽章（愛心等）。 */
export const DOWNED_BADGE_LABEL = "downed-badge";

/**
 * 標記的反向放大倍率：`base` 是世界座標的大小（px），`boardScale` 是地圖在畫面上的縮放；
 * 畫面上的大小 `base × boardScale` 小於 `min` 時放大到剛好 `min`，否則 1（不縮小）。
 */
export function minMarkScale(base: number, min: number, boardScale: number): number {
  if (!(boardScale > 0) || !(base > 0)) return 1;
  return Math.max(1, min / (base * boardScale));
}

/** 節點上記錄的基準：`base` 世界大小、`min` 畫面下限。 */
export interface MarkSpec {
  base: number;
  min: number;
}

const specs = new WeakMap<Container, MarkSpec>();
const texts = new WeakMap<Container, Text[]>();
/** 重排：`k` 是這個節點的倍率，`boardScale` 是地圖縮放（6F-11：縮放 ≤ 70% 時狀態列換成精簡列）。 */
export type Relayout = (k: number, boardScale: number) => void;
const relayouts = new WeakMap<Container, Relayout>();

/**
 * 登記一個要保持最小尺寸的標記節點（`texts` 是裡面的文字，放大時要跟著提高解析度才不會糊）。
 * `relayout`（6F-10）：倍率改變後重新排位置（召喚物的狀態列和回合數徽章）。
 */
export function registerMark(node: Container, spec: MarkSpec, inner: Text[] = [], relayout?: Relayout): void {
  specs.set(node, spec);
  texts.set(node, inner);
  if (relayout !== undefined) relayouts.set(node, relayout);
}

/** 登記過的基準（測試用）。 */
export function markSpecOf(node: Container): MarkSpec | undefined {
  return specs.get(node);
}

/**
 * 依地圖縮放設定標記的倍率；`resolution` 是畫布的解析度（裝置像素比 × 縮放），文字的解析度 ＝ 它 × 倍率。
 * 沒登記過的節點不動。回傳倍率。
 */
export function applyMarkScale(node: Container, boardScale: number, resolution: number): number {
  const spec = specs.get(node);
  if (spec === undefined) return 1;
  const k = minMarkScale(spec.base, spec.min, boardScale);
  node.scale.set(k);
  for (const t of texts.get(node) ?? []) {
    if (!t.destroyed) t.resolution = Math.max(1, resolution * k);
  }
  relayouts.get(node)?.(k, boardScale);
  return k;
}

/** 一個單位圖層裡的腳邊狀態列（直接子節點；沒有就 `null`）。 */
export function statusRowOf(unit: Container): Container | null {
  return (unit.children.find((n) => n.label === STATUS_ROW_LABEL) as Container | undefined) ?? null;
}

/**
 * 一個單位圖層裡要保持最小尺寸的標記（直接子節點），照套用順序：回合數徽章在前、狀態列在後
 * （狀態列重排時會搬徽章，6F-11）；炸彈、蓄力、灌注徽章最後（6F-12：要避開排好的回合數徽章）。
 */
export function unitMarksOf(unit: Container): Container[] {
  const pick = (name: string) => unit.children.find((n) => n.label === name) as Container | undefined;
  const names = [SUMMON_BADGE_LABEL, STATUS_ROW_LABEL, BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, INFUSED_BADGE_LABEL, HIDDEN_HP_LABEL];
  return [PART_STRIP_LABEL, ...names].map(pick).filter((n): n is Container => n !== undefined); // PB-1e：部位小格最先（重排時挪朝南三角形）
}
