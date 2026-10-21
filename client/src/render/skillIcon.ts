// 組裝式技能圖示（Phase 3-17）：圖示本身就看得出技能由哪些部件組成。
// 位置：元素＝底色與紋理、形狀＝主圖、效果原語＝底部一排、條件＝左下、骨架＝右下、特殊代價＝右上、
//       技能類型＝外框形狀、稀有度＝外框顏色、複合技能＝斜切兩半＋切線上的接續記號、修正＝主圖換成被改造的對象。
// 小圖（技能列 28–40px）只畫元素、形狀、核心效果與外框。`partsOf` 是唯一的拆解函式（資料 → 部件），
// 圖示、組裝列、工坊都用它；資料來自後端 `SkillCard.icon`（`trpg.narrative.skill_icon`）。
// 純繪圖：只有 Canvas 2D，沒有任何外部素材；確定性（沒有亂數）。
import type { SkillIconData } from "../api/types";
import { glossaryEntry, statusName, surfaceName } from "../battle/glossary";
import { SHAPE_NAMES } from "../battle/vfx";
import {
  drawMotif,
  elementGlyph,
  elementPalette,
  framePath,
  isRanged,
  paintBackground,
  rarityColor,
  SKELETON_NAME,
  skeletonGlyph,
  type Ctx,
  type MotifSpec,
} from "./skillGlyphs";
import {
  conditionPart,
  costPart,
  drawChip,
  effectPart,
  linkPart,
  modifierChangePart,
  modifierTargetPart,
  statusColor,
  statusGlyph,
  surfaceColor,
  surfaceGlyph,
  triggerPart,
  type Part,
} from "./skillParts";

const TAU = Math.PI * 2;

/** 形狀 id → 中文名（由 `vfx.ts` 的名稱表反查，只放一處）。 */
export const SHAPE_NAME_ZH: Readonly<Record<string, string>> = Object.fromEntries(Object.entries(SHAPE_NAMES).map(([zh, id]) => [id, zh]));

/** 元素在圖示上的值：字串 ＝ 元素代碼、`null` ＝ 沒有元素（紫色預設）、`undefined` ＝ 工坊還沒決定（中性）。 */
type ElementSlot = string | null | undefined;

interface SegmentParts {
  motif: MotifSpec;
  el: ElementSlot;
  effects: Part[];
}

export interface IconParts {
  kind: string;
  rarity: string;
  el: ElementSlot;
  /** 第二元素（斜向色帶）。 */
  el2: string | undefined;
  segs: SegmentParts[];
  link: Part | null;
  trigger: Part | null;
  mod: { target: Part; changes: Part[] } | null;
  condition: Part | null;
  costs: Part[];
  /** 底部一排（最多 4 個，核心效果第一個）。 */
  effects: Part[];
  core: Part | null;
}

/** 資料 → 部件清單；`icon` 缺欄位或有不認得的值時也不丟例外。 */
export function partsOf(icon: SkillIconData): IconParts {
  const kind = icon.kind || "active";
  const first = icon.elements[0];
  // 草稿還沒有形狀或效果時，元素還沒決定（中性色）；其他情況沒有元素＝紫色預設
  const el: ElementSlot = first !== undefined ? first : icon.partial ? undefined : null;
  const segs: SegmentParts[] = icon.segments.map((s, i) => ({
    motif: { shape_id: s.shape_id, skeleton: s.skeleton, ranged: isRanged(s.range, icon.weapon_req) },
    el: i === 0 ? el : (s.elements?.[0] ?? el),
    effects: s.effects.map(effectPart),
  }));
  if (segs.length === 0) segs.push({ motif: { shape_id: null, skeleton: null, ranged: false }, el, effects: [] });
  const mod =
    icon.modifier === null || icon.modifier === undefined
      ? null
      : { target: modifierTargetPart(icon.modifier.applies_to), changes: icon.modifier.changes.map((c) => modifierChangePart(c.key, c.value, c.part_ids ?? [])) };
  // 效果列：去重後，核心效果（第一個「不是單純傷害」的效果；沒有就是傷害）放第一個
  let effects: Part[] = [];
  const seen = new Set<string>();
  for (const s of segs)
    for (const e of s.effects)
      if (!seen.has(e.key)) {
        seen.add(e.key);
        effects.push(e);
      }
  if (mod !== null) effects = mod.changes;
  const coreIdx = effects.findIndex((e) => e.key !== "damage");
  const core = effects.length === 0 ? null : (effects[coreIdx === -1 ? 0 : coreIdx] ?? null);
  if (core !== null) effects = [core, ...effects.filter((e) => e !== core)];
  const isReaction = kind === "reaction";
  return {
    kind,
    rarity: icon.rarity,
    el,
    el2: icon.elements[1],
    segs,
    link: icon.link == null ? null : linkPart(icon.link),
    trigger: kind === "reaction" || kind === "passive" ? triggerPart(icon.trigger, isReaction) : null,
    mod,
    condition: icon.condition == null ? null : conditionPart(icon.condition.id, icon.condition.status),
    costs: icon.costs.map((c) => costPart(c, icon.cost_values?.[c])),
    effects: effects.slice(0, 4),
    core,
  };
}

// ---- 繪圖 ----

function bigGlyph(ctx: Ctx, part: Part, cx: number, cy: number, k: number): void {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.scale(k, k);
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.save();
  ctx.translate(0.8, 1);
  ctx.fillStyle = "rgba(0,0,0,0.45)";
  ctx.strokeStyle = "rgba(0,0,0,0.45)";
  ctx.lineWidth = 2.4;
  part.draw(ctx);
  ctx.restore();
  ctx.fillStyle = "#ffffff";
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 2.2;
  part.draw(ctx);
  ctx.restore();
}

function segMotif(ctx: Ctx, seg: SegmentParts, cx: number, cy: number, k: number): void {
  if (seg.motif.shape_id === null) {
    // 還沒選形狀：虛線圈
    ctx.save();
    ctx.setLineDash([6, 5]);
    ctx.strokeStyle = "rgba(255,255,255,0.45)";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(cx, cy, 22 * k, 0, TAU);
    ctx.stroke();
    ctx.restore();
    return;
  }
  ctx.save();
  ctx.translate(cx, cy);
  ctx.scale(k, k);
  ctx.translate(-50, -50);
  drawMotif(ctx, seg.motif, seg.el === undefined ? "default" : (seg.el ?? "default"), elementPalette(seg.el));
  ctx.restore();
}

function clipTriangle(ctx: Ctx, pts: ReadonlyArray<readonly [number, number]>): void {
  ctx.beginPath();
  pts.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)));
  ctx.closePath();
  ctx.clip();
}

function compositeArt(ctx: Ctx, parts: IconParts, small: boolean): void {
  const [a, b] = parts.segs as [SegmentParts, SegmentParts];
  ctx.save();
  clipTriangle(ctx, [
    [0, 0],
    [100, 0],
    [0, 100],
  ]);
  segMotif(ctx, a, 30, 30, 0.52);
  ctx.restore();
  ctx.save();
  clipTriangle(ctx, [
    [100, 0],
    [100, 100],
    [0, 100],
  ]);
  if (b.el !== a.el) paintBackground(ctx, b.el);
  else {
    ctx.fillStyle = "rgba(0,0,0,0.22)";
    ctx.fillRect(0, 0, 100, 100);
  }
  segMotif(ctx, b, 68, small ? 68 : 62, 0.52);
  ctx.restore();
  ctx.strokeStyle = "rgba(0,0,0,0.6)";
  ctx.lineWidth = 5;
  ctx.beginPath();
  ctx.moveTo(104, -4);
  ctx.lineTo(-4, 104);
  ctx.stroke();
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 2.2;
  ctx.stroke();
  if (parts.link !== null) drawChip(ctx, parts.link, 50, 50, small ? 13 : 10.5, { ring: "#ffffff" });
}

function mainArt(ctx: Ctx, parts: IconParts, small: boolean): void {
  const ky = small ? 50 : 44;
  const k = small ? 1 : 0.8;
  const first = parts.segs[0] as SegmentParts;
  if (parts.mod !== null) bigGlyph(ctx, parts.mod.target, 50, ky, small ? 3 : 2.4);
  else if (parts.trigger !== null) bigGlyph(ctx, parts.trigger, 50, ky, small ? 3 : 2.4);
  else if (parts.segs.length > 1) compositeArt(ctx, parts, small);
  else segMotif(ctx, first, 50, ky + (small ? 0 : 2), k);
}

function elementChip(ctx: Ctx, el: string | null, x: number, y: number, r: number): void {
  ctx.fillStyle = "rgba(8,10,16,0.8)";
  ctx.beginPath();
  ctx.arc(x, y, r, 0, TAU);
  ctx.fill();
  elementGlyph(ctx, el ?? "default", x, y, (r / 12) * 0.8, elementPalette(el).accent);
}

function skeletonBadge(ctx: Ctx, skeleton: string, rarity: string): void {
  ctx.fillStyle = "rgba(8,10,16,0.88)";
  ctx.beginPath();
  ctx.arc(86, 86, 11, 0, TAU);
  ctx.fill();
  ctx.strokeStyle = rarity;
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.save();
  ctx.translate(86, 86);
  ctx.scale(0.85, 0.85);
  skeletonGlyph(ctx, skeleton, 0, 0);
  ctx.restore();
}

function effectRow(ctx: Ctx, parts: IconParts): void {
  const list = parts.effects;
  if (list.length === 0) return;
  const left = parts.condition !== null ? 26 : 5;
  const right = 75;
  const rc = 11.5;
  let ro = 8.5;
  const gap = 1.5;
  let total = rc * 2 + (list.length - 1) * (ro * 2 + gap);
  if (total > right - left) {
    ro = Math.max(4.5, ((right - left - rc * 2) / (list.length - 1) - gap) / 2);
    total = rc * 2 + (list.length - 1) * (ro * 2 + gap);
  }
  let x = (left + right) / 2 - total / 2;
  list.forEach((p, i) => {
    const r = i === 0 ? rc : ro;
    drawChip(ctx, p, x + r, 85 + (i === 0 ? 0 : 2), r, { ring: i === 0 ? p.color : "rgba(255,255,255,0.3)" });
    x += r * 2 + gap;
  });
}

function frame(ctx: Ctx, parts: IconParts, rarity: string): void {
  framePath(ctx, parts.kind, 1);
  ctx.lineWidth = parts.rarity === "legendary" ? 5 : 3.5;
  ctx.strokeStyle = rarity;
  ctx.stroke();
  if (parts.rarity === "legendary" || parts.rarity === "epic") {
    framePath(ctx, parts.kind, 6);
    ctx.lineWidth = 1;
    ctx.globalAlpha = 0.6;
    ctx.stroke();
    ctx.globalAlpha = 1;
  }
}

/** 小圖門檻：邊長 ≤ 這個值（px）時只畫元素、形狀、核心效果與外框。 */
export const SMALL_ICON_MAX = 40;

/**
 * 在 `ctx` 上畫一個組裝式圖示。`ctx` 已經縮放成 100×100 的座標（見 `skillIconCanvas`）；
 * `small` 為真時只畫元素、形狀、核心效果與外框。
 */
export function paintSkillIcon(ctx: Ctx, icon: SkillIconData, small: boolean): void {
  const parts = partsOf(icon);
  const rarity = rarityColor(parts.rarity);
  ctx.save();
  framePath(ctx, parts.kind);
  ctx.clip();
  paintBackground(ctx, parts.el);
  if (parts.el2 !== undefined) {
    // 第二元素：斜向色帶
    ctx.save();
    ctx.globalAlpha = 0.55;
    ctx.fillStyle = elementPalette(parts.el2).light;
    ctx.beginPath();
    ctx.moveTo(62, 0);
    ctx.lineTo(80, 0);
    ctx.lineTo(0, 80);
    ctx.lineTo(0, 62);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }
  mainArt(ctx, parts, small);
  ctx.restore();
  frame(ctx, parts, rarity);
  if (small) {
    if (parts.core !== null) drawChip(ctx, parts.core, 79, 79, 18, { ring: rarity });
    return;
  }
  // 角落：左上元素、右上代價、左下條件、右下骨架
  if (parts.el !== undefined) elementChip(ctx, parts.el, 15, 15, 11);
  const [c1, c2] = parts.costs;
  if (c1 !== undefined) drawChip(ctx, c1, 85, 15, 11, { ring: c1.color });
  if (c2 !== undefined) drawChip(ctx, c2, 85, 36, 8, { ring: c2.color });
  if (parts.condition !== null) drawChip(ctx, parts.condition, 14, 86, 11, { ring: "#ffe9a8" });
  const skeleton = parts.segs[0]?.motif.skeleton ?? null;
  if (skeleton !== null) skeletonBadge(ctx, skeleton, rarity);
  effectRow(ctx, parts);
}

// ---- 快取 ----

/** 穩定序列化（鍵排序），同一組合永遠得到同一個字串。 */
export function stableStringify(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
  if (typeof value === "object" && value !== null) {
    const entries = Object.entries(value as Record<string, unknown>)
      .filter(([, v]) => v !== undefined)
      .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
    return `{${entries.map(([k, v]) => `${JSON.stringify(k)}:${stableStringify(v)}`).join(",")}}`;
  }
  return JSON.stringify(value) ?? "null";
}

/** 圖示的快取鍵：`icon` 的穩定序列化 ＋ 尺寸 ＋ 大小圖（同組合共用一張貼圖，不是每個技能一張）。 */
export function iconCacheKey(icon: SkillIconData, size: number, small: boolean = size <= SMALL_ICON_MAX): string {
  return `${size}|${small ? "s" : "l"}|${stableStringify(icon)}`;
}

const DPR = 2;
const CACHE_LIMIT = 300;
const cache = new Map<string, HTMLCanvasElement>();

export function clearSkillIconCache(): void {
  cache.clear();
}
export const skillIconCacheSize = (): number => cache.size;

/** 取得（或畫出並快取）一張圖示的離屏 canvas，邊長 `size` px（內部解析度 ×2）；`small` 預設依邊長決定。 */
export function skillIconCanvas(icon: SkillIconData, size: number, small: boolean = size <= SMALL_ICON_MAX): HTMLCanvasElement {
  const key = iconCacheKey(icon, size, small);
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  const canvas = document.createElement("canvas");
  canvas.width = size * DPR;
  canvas.height = size * DPR;
  const ctx = canvas.getContext("2d");
  if (ctx !== null) {
    ctx.scale((size * DPR) / 100, (size * DPR) / 100);
    paintSkillIcon(ctx, icon, small);
  }
  if (cache.size >= CACHE_LIMIT) {
    const oldest = cache.keys().next().value;
    if (oldest !== undefined) cache.delete(oldest);
  }
  cache.set(key, canvas);
  return canvas;
}

// ---- 組裝算式（Phase 3-18a）----

export interface AssemblyTile {
  /** 部件類別（骨架、形狀、效果（核心）、效果、接續、觸發、改造對象、改變內容、條件、代價、狀態、表面……）。 */
  cat: string;
  label: string;
  /** 部件的說明（說明框的內文）。 */
  tip: string;
  /** 畫法的唯一鍵（快取用：同一個部件共用一張小圖）。 */
  id: string;
  /** 在 100×100 座標上畫這一塊的小圖。 */
  draw(ctx: Ctx): void;
}

const FAINT_RING = "rgba(255,255,255,0.3)";
const CORE_RING = "#ffffff";

function chipTile(cat: string, part: Part, ring: string): AssemblyTile {
  return { cat, label: part.label, tip: part.note, id: `${cat}|${part.key}|${part.label}|${ring}`, draw: (ctx) => drawChip(ctx, part, 50, 50, 42, { ring }) };
}

function skeletonTile(skeleton: string, second: boolean): AssemblyTile {
  return {
    cat: second ? "骨架（第二段）" : "骨架",
    label: SKELETON_NAME[skeleton] ?? skeleton,
    tip: "技能的骨架：決定這一段怎麼出手",
    id: `skeleton|${skeleton}`,
    draw: (ctx) => {
      ctx.fillStyle = "#14161c";
      ctx.beginPath();
      ctx.arc(50, 50, 40, 0, TAU);
      ctx.fill();
      ctx.save();
      ctx.translate(50, 50);
      ctx.scale(3, 3);
      skeletonGlyph(ctx, skeleton, 0, 0);
      ctx.restore();
    },
  };
}

function shapeTile(seg: SegmentParts): AssemblyTile | null {
  if (seg.motif.shape_id === null) return null;
  const shape = seg.motif.shape_id;
  return {
    cat: "形狀",
    label: SHAPE_NAME_ZH[shape] ?? shape,
    tip: "技能的作用範圍",
    id: `shape|${shape}|${String(seg.el)}|${seg.motif.skeleton ?? ""}|${seg.motif.ranged ? 1 : 0}`,
    draw: (ctx) => {
      paintBackground(ctx, seg.el);
      segMotif(ctx, seg, 50, 50, 0.95);
    },
  };
}

/** 一段的部件：骨架 ＋ 形狀 ＋ 效果（核心效果白外圈）。元素、類型、稀有度不是部件，已由圖示本身表達。 */
function segmentTiles(seg: SegmentParts, index: number, core: Part | null): AssemblyTile[] {
  const out: AssemblyTile[] = [];
  if (seg.motif.skeleton !== null) out.push(skeletonTile(seg.motif.skeleton, index > 0));
  const shape = shapeTile(seg);
  if (shape !== null) out.push(shape);
  const unique = seg.effects.filter((x, i, a) => a.findIndex((y) => y.key === x.key) === i);
  for (const e of unique) {
    const isCore = e.key === core?.key;
    out.push(chipTile(isCore ? "效果（核心）" : "效果", e, isCore ? CORE_RING : FAINT_RING));
  }
  return out;
}

/** 組裝算式：每段一行（骨架 ＋ 形狀 ＋ 效果），段間是接續；條件與代價在最下面一條細線後。 */
export interface AssemblyFormula {
  rows: AssemblyTile[][];
  /** `links[i]` 在 `rows[i]` 與 `rows[i + 1]` 之間。 */
  links: AssemblyTile[];
  /** 條件與代價（18px 小圓，「類別：名稱」）。 */
  extras: AssemblyTile[];
}

export function assemblyFormula(icon: SkillIconData): AssemblyFormula {
  const parts = partsOf(icon);
  const rows: AssemblyTile[][] = [];
  const links: AssemblyTile[] = [];
  if (parts.mod !== null) {
    rows.push([chipTile("改造對象", parts.mod.target, CORE_RING), ...parts.mod.changes.map((c) => chipTile("改變內容", c, FAINT_RING))]);
  } else {
    const [a, b] = parts.segs as [SegmentParts, SegmentParts | undefined];
    const first = segmentTiles(a, 0, parts.core);
    rows.push(parts.trigger === null ? first : [chipTile("觸發", parts.trigger, CORE_RING), ...first]);
    if (parts.link !== null && b !== undefined) {
      links.push(chipTile("接續", parts.link, CORE_RING));
      rows.push(segmentTiles(b, 1, parts.core));
    }
  }
  const extras: AssemblyTile[] = [];
  if (parts.condition !== null) extras.push(chipTile("條件", parts.condition, "#ffe9a8"));
  // 接續本身就是延遲時，代價裡的「延遲」不重複寫
  for (const c of parts.costs) if (!(c.key === "delay" && parts.link?.key === "delayed")) extras.push(chipTile("代價", c, c.color));
  return { rows, links, extras };
}

/** 狀態的部件小圖（說明取名詞對照表的描述）。 */
export function statusTile(id: string): AssemblyTile {
  const entry = glossaryEntry("statuses", id);
  const tip = [entry?.description_zh ?? "", ...(entry?.rules_zh ?? [])].filter((x) => x !== "").join(" ");
  return {
    cat: "狀態",
    label: statusName(id),
    tip: tip === "" ? "狀態" : tip,
    id: `status|${id}`,
    draw: (ctx) => drawChip(ctx, { cat: "effect", key: `status:${id}`, color: statusColor(id), draw: (c) => statusGlyph(c, id), label: id, note: "" }, 50, 50, 42, { ring: FAINT_RING }),
  };
}

/** 表面的部件小圖（說明取名詞對照表的描述與規則）。 */
export function surfaceTile(id: string): AssemblyTile {
  const entry = glossaryEntry("surfaces", id);
  const tip = [entry?.description_zh ?? "", ...(entry?.rules_zh ?? [])].filter((x) => x !== "").join(" ");
  return {
    cat: "表面",
    label: surfaceName(id),
    tip: tip === "" ? "地面上的表面" : tip,
    id: `surface|${id}`,
    draw: (ctx) => drawChip(ctx, { cat: "effect", key: `surface:${id}`, color: surfaceColor(id), draw: (c) => surfaceGlyph(c, id), label: id, note: "" }, 50, 50, 42, { ring: FAINT_RING }),
  };
}

/** 部件的說明字串：「部件類別：名稱（說明）」。 */
export const tileTitle = (t: AssemblyTile): string => `${t.cat}：${t.label}（${t.tip}）`;

/** 組裝列方塊的快取鍵（同一個部件共用一張小圖）。 */
export const tileKey = (t: AssemblyTile, px: number): string => `${px}|${t.id}`;

const tileCache = new Map<string, HTMLCanvasElement>();

/** 一塊組裝列方塊的離屏 canvas（`px` 邊長，內部解析度 ×2；同一個部件共用）。 */
export function tileCanvas(tile: AssemblyTile, px = 44): HTMLCanvasElement {
  const key = tileKey(tile, px);
  const hit = tileCache.get(key);
  if (hit !== undefined) return hit;
  const canvas = document.createElement("canvas");
  canvas.width = px * DPR;
  canvas.height = px * DPR;
  const ctx = canvas.getContext("2d");
  if (ctx !== null) {
    ctx.scale((px * DPR) / 100, (px * DPR) / 100);
    // 每個部件都是圓：形狀、骨架等原本的方塊裁成圓
    ctx.beginPath();
    ctx.arc(50, 50, 49, 0, TAU);
    ctx.clip();
    tile.draw(ctx);
  }
  if (tileCache.size >= CACHE_LIMIT) {
    const oldest = tileCache.keys().next().value;
    if (oldest !== undefined) tileCache.delete(oldest);
  }
  tileCache.set(key, canvas);
  return canvas;
}

// ---- 工坊選項的小圖 ----

const OPTION_ID = (field: string, value: string) => `option|${field}|${value}`;

const PART_CAT_NAME: Readonly<Record<string, string>> = { effect: "效果", condition: "條件", cost: "代價", trigger: "觸發", link: "接續", target: "改造對象", change: "改變內容" };

function partTile(field: string, value: string, part: Part): AssemblyTile {
  return { cat: PART_CAT_NAME[part.cat] ?? part.cat, label: part.label, tip: part.note, id: OPTION_ID(field, value), draw: (ctx) => drawChip(ctx, part, 50, 50, 46, { ring: "rgba(255,255,255,0.3)" }) };
}

/**
 * 工坊某個欄位的某個選項的小圖（與技能圖示共用同一套部件）；沒有圖示的欄位回傳 `null`。
 * 欄位：`skeleton`、`shape`、`condition`、`event`（觸發／反應時機）、效果列表的 `type`、
 * 效果參數的 `status`、`surface`、`element`。
 */
export function optionTile(field: string, value: unknown): AssemblyTile | null {
  if (typeof value !== "string" || value === "") return null;
  const name = field.split(".").pop() ?? field;
  switch (name) {
    case "skeleton":
      return skeletonTile(value, false);
    case "shape": {
      const motif: SegmentParts = { motif: { shape_id: value, skeleton: null, ranged: true }, el: null, effects: [] };
      return {
        cat: "形狀",
        label: SHAPE_NAME_ZH[value] ?? value,
        tip: "技能的作用範圍",
        id: OPTION_ID(field, value),
        draw: (ctx) => {
          paintBackground(ctx, null);
          segMotif(ctx, motif, 50, 50, 0.95);
        },
      };
    }
    case "condition":
    case "condition_type": {
      const part = conditionPart(value);
      return part === null ? null : partTile(field, value, part);
    }
    case "event": {
      const part = triggerPart(value, false);
      return part === null ? null : partTile(field, value, part);
    }
    case "effects":
      return partTile(field, value, effectPart({ type: value }));
    case "status":
      return statusTile(value);
    case "surface":
      return surfaceTile(value);
    case "element":
      return {
        cat: "元素",
        label: elementPalette(value).name,
        tip: "技能的元素",
        id: OPTION_ID(field, value),
        draw: (ctx) => {
          paintBackground(ctx, value);
          elementGlyph(ctx, value, 50, 50, 2.6, "#ffffff");
        },
      };
    default:
      return null;
  }
}
