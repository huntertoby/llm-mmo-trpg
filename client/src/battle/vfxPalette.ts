// 技能特效的元素對照表（Phase 3-12）：每個元素一組顏色與粒子行為，加上粒子軌跡的純函式。
// 元素代碼以引擎的 `Element`（`/api/glossary` 的 `elements`）為準；不認得的元素用 `DEFAULT_VFX`。
// 畫布（`render/BattleRenderer.ts`）只照這裡算出的位置與大小畫圖，所以軌跡可以用 vitest 檢查。

/** 粒子行為：火星上飄、碎晶、鋸齒閃電、水花、綠泡、弧線、碎石、光柱、煙霧、火花、閃光。 */
export type ParticleKind =
  | "ember"
  | "shard"
  | "bolt"
  | "splash"
  | "bubble"
  | "gust"
  | "rock"
  | "pillar"
  | "smoke"
  | "spark"
  | "sparkle";

export interface ElementVfx {
  /** 主色（飛行物、光束、範圍底色）。 */
  primary: number;
  /** 副色（粒子、外圈、拖尾）。 */
  secondary: number;
  particle: ParticleKind;
  /** 每次爆發的基本粒子數（再乘上強度）。 */
  particles: number;
  /** 光束畫成鋸齒（雷）。 */
  jagged: boolean;
  /** 命中時多畫一道從上方落下的光柱（聖光）。 */
  column: boolean;
}

function vfx(primary: number, secondary: number, particle: ParticleKind, particles = 10, extra: Partial<ElementVfx> = {}): ElementVfx {
  return { primary, secondary, particle, particles, jagged: false, column: false, ...extra };
}

/**
 * 元素顏色的唯一來源（Phase 3-18a）：特效（`primary`、`secondary`）與技能圖示（`accent`、`dark`、`light`）
 * 都從這一張表取色。顏色一律寫十六進位字串，需要數字的地方用 `hexToNumber`。
 */
export interface ElementColors {
  /** 中文名。 */
  name: string;
  /** 特效主色（飛行物、光束、範圍底色）。 */
  primary: string;
  /** 特效副色（粒子、外圈、拖尾）。 */
  secondary: string;
  /** 圖示標誌與主圖的亮色。 */
  accent: string;
  /** 圖示底色漸層的暗端與亮端。 */
  dark: string;
  light: string;
}

export const ELEMENT_COLORS: Readonly<Record<string, ElementColors>> = {
  physical: { name: "物理", primary: "#f2f2f2", secondary: "#b8bcc8", accent: "#e8ebf0", dark: "#2c313b", light: "#7d8798" },
  fire: { name: "火", primary: "#ff6a1a", secondary: "#ffd23f", accent: "#ffb23a", dark: "#4a1104", light: "#e8541a" },
  ice: { name: "冰", primary: "#8fe3ff", secondary: "#ffffff", accent: "#d8f6ff", dark: "#0b2f4e", light: "#3fa6d8" },
  lightning: { name: "雷", primary: "#fff36b", secondary: "#8fd0ff", accent: "#fff36b", dark: "#1d1d4a", light: "#5a5ac8" },
  poison: { name: "毒", primary: "#7ddc3a", secondary: "#3f8f2a", accent: "#b6f06a", dark: "#12320c", light: "#4f9a28" },
  wind: { name: "風", primary: "#c8ffe8", secondary: "#7fe0c0", accent: "#dcfff1", dark: "#0b3f3a", light: "#3fb59a" },
  earth: { name: "大地", primary: "#b0814a", secondary: "#6e5236", accent: "#f0c890", dark: "#2e1d0e", light: "#9a6a36" },
  holy: { name: "聖光", primary: "#fff2b0", secondary: "#ffd75e", accent: "#fff6c8", dark: "#5a3a06", light: "#e7b23a" },
  shadow: { name: "暗影", primary: "#9a6ad8", secondary: "#2a1840", accent: "#d2b0ff", dark: "#10071e", light: "#5a3590" },
};

/** `#rrggbb` → 0xrrggbb。 */
export function hexToNumber(hex: string): number {
  return parseInt(hex.slice(1), 16);
}

function fromColors(id: string, particle: ParticleKind, particles: number, extra: Partial<ElementVfx> = {}): ElementVfx {
  const c = ELEMENT_COLORS[id];
  if (c === undefined) throw new Error(`ELEMENT_COLORS 缺少 ${id}`);
  return vfx(hexToNumber(c.primary), hexToNumber(c.secondary), particle, particles, extra);
}

/** 元素 → 特效配色與粒子（顏色取自 `ELEMENT_COLORS`，這裡只決定粒子行為）。 */
export const ELEMENT_VFX: Readonly<Record<string, ElementVfx>> = {
  physical: fromColors("physical", "spark", 8),
  fire: fromColors("fire", "ember", 12),
  ice: fromColors("ice", "shard", 10),
  lightning: fromColors("lightning", "bolt", 7, { jagged: true }),
  poison: fromColors("poison", "bubble", 9),
  wind: fromColors("wind", "gust", 7),
  earth: fromColors("earth", "rock", 9),
  holy: fromColors("holy", "pillar", 9, { column: true }),
  shadow: fromColors("shadow", "smoke", 9),
  // 水不是元素（只是表面）；保留一組水花，若之後內容加入水元素可直接使用。
  water: vfx(0x4aa8ff, 0xd8f0ff, "splash", 10),
};

/** 不是元素的技能：治療、護盾等支援技能。 */
export const SUPPORT_VFX_KEY = "support";
export const SUPPORT_VFX: ElementVfx = vfx(0x7cf29a, 0xe6ffe9, "sparkle", 9);

/** 找不到對應元素時的通用預設（奧術色閃光）。 */
export const DEFAULT_VFX_KEY = "default";
export const DEFAULT_VFX: ElementVfx = vfx(0xb8a8ff, 0xffffff, "sparkle", 9);

/** 元素代碼（或 `support`）→ 特效；不認得時回傳通用預設。 */
export function elementVfx(key: string): ElementVfx {
  if (key === SUPPORT_VFX_KEY) return SUPPORT_VFX;
  return ELEMENT_VFX[key] ?? DEFAULT_VFX;
}

/** 一顆粒子在某一刻的樣子（相對爆發中心的像素位移）。 */
export interface ParticleFrame {
  x: number;
  y: number;
  /** 半徑或邊長（像素）。 */
  size: number;
  alpha: number;
  /** 旋轉角（弧度；碎晶、碎石、弧線用）。 */
  rotation: number;
}

/** 固定的偽亂數（0–1）：同一顆粒子每一幀都一樣，不用 `Math.random`。 */
export function jitter(i: number, salt: number): number {
  const s = Math.sin((i + 1) * 12.9898 + salt * 78.233) * 43758.5453;
  return s - Math.floor(s);
}

/**
 * 第 `i` 顆（共 `n` 顆）粒子在進度 `t`（0–1）時的位置；`reach` 是擴散距離（像素，已乘強度）。
 * 各元素的行為：火星往上飄、碎晶向外飛後下墜、閃電短距離抖動、水花拋物線、綠泡緩慢上升變大、
 * 風沿弧線旋出、碎石向外拋後落下、光柱的光點往上升、煙霧原地擴大淡出。
 */
export function particleAt(kind: ParticleKind, i: number, n: number, t: number, reach: number): ParticleFrame {
  const k = Math.max(0, Math.min(1, t));
  const angle = (i / Math.max(1, n)) * Math.PI * 2 + jitter(i, 1) * 0.6;
  const speed = 0.55 + jitter(i, 2) * 0.45;
  const fade = 1 - k;
  const dx = Math.cos(angle);
  const dy = Math.sin(angle);
  const d = reach * speed * easeOut(k);
  switch (kind) {
    case "ember":
      return { x: dx * d * 0.6, y: dy * d * 0.4 - reach * 0.9 * k * speed, size: 2.5 + jitter(i, 3) * 2, alpha: fade, rotation: 0 };
    case "shard":
      return { x: dx * d, y: dy * d + reach * 0.5 * k * k, size: 3 + jitter(i, 3) * 3, alpha: fade, rotation: angle + k * 4 };
    case "bolt":
      return { x: dx * d * 0.8, y: dy * d * 0.8, size: 6 + jitter(i, 3) * 6, alpha: k < 0.5 ? 1 : fade * 2, rotation: angle };
    case "splash":
      return { x: dx * d, y: dy * d * 0.5 - reach * 0.8 * k + reach * 1.2 * k * k, size: 2 + jitter(i, 3) * 2.5, alpha: fade, rotation: 0 };
    case "bubble":
      return { x: dx * d * 0.5, y: -reach * 0.6 * k * speed + dy * reach * 0.15, size: 2 + 5 * k * speed, alpha: fade * 0.9, rotation: 0 };
    case "gust": {
      const swirl = angle + k * 2.4;
      return { x: Math.cos(swirl) * d, y: Math.sin(swirl) * d, size: 8 + jitter(i, 3) * 6, alpha: fade, rotation: swirl + Math.PI / 2 };
    }
    case "rock":
      return { x: dx * d, y: dy * d * 0.6 - reach * 0.7 * k + reach * 1.3 * k * k, size: 3 + jitter(i, 3) * 3, alpha: k < 0.7 ? 1 : (1 - k) / 0.3, rotation: angle + k * 3 };
    case "pillar":
      return { x: (jitter(i, 4) - 0.5) * reach * 0.6, y: -reach * 1.2 * k * speed, size: 2 + jitter(i, 3) * 2, alpha: fade, rotation: 0 };
    case "smoke":
      return { x: dx * d * 0.5, y: dy * d * 0.5 - reach * 0.2 * k, size: 5 + 10 * k * speed, alpha: fade * 0.6, rotation: 0 };
    case "spark":
      return { x: dx * d, y: dy * d, size: 4 + jitter(i, 3) * 5, alpha: fade, rotation: angle };
    case "sparkle":
      return { x: dx * d * 0.8, y: dy * d * 0.8 - reach * 0.2 * k, size: 2 + jitter(i, 3) * 2, alpha: Math.sin(Math.PI * k), rotation: k * 3 };
  }
}

function easeOut(t: number): number {
  return 1 - (1 - t) * (1 - t);
}
