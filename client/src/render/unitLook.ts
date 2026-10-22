// 單位裝飾的繪製資料（Phase 3-18b；純資料，不碰 Pixi，可用 vitest 檢查）。
// 倒地：小人已經躺下，徽章只回答「救不救得回來」（docs/art/3-18倒地與高度.md 第 1 節），不寫字。
// 狀態徽章：地圖上單位身上的狀態（炸彈倒數、蓄力）改用技能部件庫的狀態圖示（`skillParts.statusGlyph`）。
import { HIGHLIGHT } from "../battle/glossary";
import { TIME_BOMB } from "../battle/bombs";
import { CHARGING } from "../battle/followup";

export type DownedState = "up" | "revivable" | "lost";

export interface DownedLook {
  state: DownedState;
  /** 小人（只有小人，不含徽章與代號）的透明度。 */
  dollAlpha: number;
  /** 小人去色（灰階）。 */
  grayscale: boolean;
  /** 底圈的顏色；`null` ＝ 沿用隊伍色。 */
  ring: { fill: number; stroke: number } | null;
  /** 左上角徽章：愛心或墓碑；`null` ＝ 不畫。 */
  badge: { kind: "heart" | "grave"; edge: number; glyph: number } | null;
  /** 腳下閃動的虛線橢圓；`null` ＝ 不畫。 */
  dashed: { color: number; minAlpha: number; maxAlpha: number; periodMs: number } | null;
}

export const GRAVE_GRAY = 0xa8acb4;
export const LOST_RING = { fill: 0x5a5e66, stroke: 0x8a8f99 } as const;

/** 只看 `downed`、`revivable` 兩個欄位。 */
export function downedLook(downed: boolean, revivable: boolean): DownedLook {
  if (!downed) return { state: "up", dollAlpha: 1, grayscale: false, ring: null, badge: null, dashed: null };
  if (revivable) {
    return {
      state: "revivable",
      dollAlpha: 0.6,
      grayscale: false,
      ring: null,
      badge: { kind: "heart", edge: HIGHLIGHT.revive, glyph: HIGHLIGHT.revive },
      dashed: { color: HIGHLIGHT.revive, minAlpha: 0.4, maxAlpha: 1, periodMs: 1500 },
    };
  }
  return {
    state: "lost",
    dollAlpha: 0.45,
    grayscale: true,
    ring: { ...LOST_RING },
    badge: { kind: "grave", edge: GRAVE_GRAY, glyph: GRAVE_GRAY },
    dashed: null,
  };
}

/** 虛線橢圓在 `ms` 毫秒時的透明度（0.4 ↔ 1，餘弦往返）。 */
export function pulseAlpha(look: NonNullable<DownedLook["dashed"]>, ms: number): number {
  const phase = (ms % look.periodMs) / look.periodMs;
  const wave = (1 - Math.cos(phase * Math.PI * 2)) / 2;
  return look.minAlpha + (look.maxAlpha - look.minAlpha) * wave;
}

// ---- 狀態徽章 ----

export interface StatusBadge {
  /** 狀態 ID（技能部件庫的狀態圖示以此取得）。 */
  statusId: string;
  /** 剩餘的次數或回合（顯示在圖示旁的數字）。 */
  count: number;
  /** 徽章的外框顏色。 */
  color: number;
  /** 徽章中心（相對格子中心的比例，乘上格子大小）。 */
  at: { x: number; y: number };
}

export interface BadgeSource {
  bomb: number | null;
  charge?: number | null | undefined;
}

/** 一個單位身上要畫的狀態徽章：定時炸彈（右下）、蓄力（左下）。 */
export function statusBadges(u: BadgeSource): StatusBadge[] {
  const out: StatusBadge[] = [];
  if (u.bomb !== null) out.push({ statusId: TIME_BOMB, count: u.bomb, color: HIGHLIGHT.bomb, at: { x: 0.3, y: 0.12 } });
  if (u.charge != null) out.push({ statusId: CHARGING, count: u.charge, color: HIGHLIGHT.followup, at: { x: -0.37, y: -0.2 } });
  return out;
}

// ---- 待施放的灌注技能（Phase 3-33d）----

export interface InfusedBadge {
  /** 徽章裡的字。 */
  glyph: string;
  /** 外框與字的顏色。 */
  color: number;
  /** 徽章中心（相對格子中心的比例，乘上格子大小）：左上，避開右上的剩餘輪數與左下的蓄力。 */
  at: { x: number; y: number };
}

/** 召喚物身上有待施放的灌注技能（下一個自己的回合開始時施放）時的「灌」徽章；沒有時 `null`。 */
export function infusedBadge(u: { infused?: boolean | undefined; downed: boolean }): InfusedBadge | null {
  if (u.infused !== true || u.downed) return null;
  return { glyph: "灌", color: HIGHLIGHT.followup, at: { x: -0.3, y: -0.4 } };
}
