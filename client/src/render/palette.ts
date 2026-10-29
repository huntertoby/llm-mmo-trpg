// 元素、關鍵字、表面的配色（Phase 3T-4）：全站的唯一來源。
// 之前分散在 artPalette、vfxPalette、glossary、skillParts、statusIcon、inkForm、summonArt、gearIcon 八處，數值互相矛盾
// （火 #ff7a1a／#ff6a1a、雷 #ffe14a／#fff36b）。數值以美術 PM 定案的 `artPalette`（裝備關鍵字色 ignite／charged／frozen／wet）為準，
// 它與技能特效 `ELEMENT_COLORS` 的主色本來就一致；Phase 4 新增元素只改這個檔。
// 這個檔案是葉節點（不匯入任何其他 render 檔），誰都可以匯入。

export interface ElementColors {
  /** 中文名。 */
  name: string;
  /** 特效主色（飛行物、光束、範圍底色）；也是元素的代表色（狀態圖樣、地上的區域、形態、附魔）。 */
  primary: string;
  /** 特效副色（粒子、外圈、拖尾）。 */
  secondary: string;
  /** 圖示標誌與主圖的亮色。 */
  accent: string;
  /** 圖示底色漸層的暗端與亮端。 */
  dark: string;
  light: string;
  /** 形態的亮部、高光（龍的吐息、元素化身的內光）。 */
  bright: string;
  /** 狀態圖樣用的色（持續傷害）；沒有就用 `primary`（物理的持續傷害是流血，用紅色而不是特效的白）。 */
  mark?: string;
}

export const ELEMENT_COLORS: Readonly<Record<string, ElementColors>> = {
  physical: { name: "物理", primary: "#f2f2f2", secondary: "#b8bcc8", accent: "#e8ebf0", dark: "#2c313b", light: "#7d8798", bright: "#ffffff", mark: "#e05050" },
  fire: { name: "火", primary: "#ff6a1a", secondary: "#ffd23f", accent: "#ffb23a", dark: "#4a1104", light: "#e8541a", bright: "#ffd04a" },
  ice: { name: "冰", primary: "#8fe3ff", secondary: "#ffffff", accent: "#d8f6ff", dark: "#0b2f4e", light: "#3fa6d8", bright: "#e8fbff" },
  lightning: { name: "雷", primary: "#fff36b", secondary: "#8fd0ff", accent: "#fff36b", dark: "#1d1d4a", light: "#5a5ac8", bright: "#fff7c0" },
  poison: { name: "毒", primary: "#7ddc3a", secondary: "#3f8f2a", accent: "#b6f06a", dark: "#12320c", light: "#4f9a28", bright: "#d6f59a" },
  wind: { name: "風", primary: "#c8ffe8", secondary: "#7fe0c0", accent: "#dcfff1", dark: "#0b3f3a", light: "#3fb59a", bright: "#effff8" },
  earth: { name: "大地", primary: "#b0814a", secondary: "#6e5236", accent: "#f0c890", dark: "#2e1d0e", light: "#9a6a36", bright: "#e6c89a" },
  holy: { name: "聖光", primary: "#fff2b0", secondary: "#ffd75e", accent: "#fff6c8", dark: "#5a3a06", light: "#e7b23a", bright: "#fffbe0" },
  shadow: { name: "暗影", primary: "#9a6ad8", secondary: "#2a1840", accent: "#d2b0ff", dark: "#10071e", light: "#5a3590", bright: "#c8a8f0" },
};

/** 水不是元素（只是表面與「濕」關鍵字）；保留一個水色，若之後內容加入水元素可直接放進 `ELEMENT_COLORS`。 */
export const WATER_COLOR = "#4aa8ff";
/** 沒有元素、不認得的元素。 */
export const NEUTRAL_COLOR = "#d8d8e0";

/** 元素的代表色（狀態圖樣、腳邊粒子、陷阱與區域）；水＝水色，不認得 → 中性色。 */
export function elementColor(el: string | null | undefined): string {
  if (el == null) return NEUTRAL_COLOR;
  if (el === "water") return WATER_COLOR;
  const c = ELEMENT_COLORS[el];
  return c === undefined ? NEUTRAL_COLOR : (c.mark ?? c.primary);
}

/** 「會替物品與形態上色」的元素色：物理與不認得的元素回傳 `undefined`（不套元素色）；水套水色。 */
export function elementTintColors(el: string | null | undefined): Pick<ElementColors, "primary" | "bright"> | undefined {
  if (el == null || el === "physical") return undefined;
  if (el === "water") return { primary: WATER_COLOR, bright: "#d8f0ff" };
  return ELEMENT_COLORS[el];
}

// ---- 關鍵字（id 同 skill_keywords.yaml）----

/** 關鍵字色；元素關鍵字（ignite／wet／charged／frozen）取元素色。 */
export const KEYWORD_COLOR: Readonly<Record<string, string>> = {
  ignite: ELEMENT_COLORS["fire"]!.primary,
  wet: WATER_COLOR,
  charged: ELEMENT_COLORS["lightning"]!.primary,
  frozen: ELEMENT_COLORS["ice"]!.primary,
  prone: "#e0b080",
  collision: "#ff9a4a",
  marked: "#d06aff",
  high_ground: "#ffe9a8",
  concealed: "#a0a0c8",
  summon: "#7dffb0",
  poisoned: "#7ad04a",
  form: "#e0a35a",
};

/** 這些關鍵字是元素：裝備圖示上的主色會混入它的顏色。 */
export const TINT_KEYWORDS: ReadonlySet<string> = new Set(["ignite", "wet", "charged", "frozen"]);

// ---- 表面（落在地上的東西）----

/** 技能圖示上「表面」小圖樣的顏色（畫在深色底上，偏亮）；火取元素色。 */
export const SURFACE_ICON_COLOR: Readonly<Record<string, string>> = {
  fire: ELEMENT_COLORS["fire"]!.primary,
  ice: "#cdeeff",
  oil: "#5a4a30",
  water: "#4a9af0",
  holy: "#ffe58a",
  darkness: "#8a5ad0",
  smoke: "#c0c0c8",
  poison: "#86d84a",
};

/** 戰場上表面蓋在地形上的顏色（半透明疊色，偏暗）；火取元素色。 */
export const SURFACE_GROUND_COLOR: Readonly<Record<string, string>> = {
  oil: "#2b2416",
  water: "#3a7bd5",
  fire: ELEMENT_COLORS["fire"]!.primary,
  ice: "#c8ecff",
  poison: "#7bc043",
  holy: "#fff1a8",
  darkness: "#3b1f4f",
  smoke: "#b8b8c0",
};
