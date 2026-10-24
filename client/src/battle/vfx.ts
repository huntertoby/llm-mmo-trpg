// 技能特效的推導（Phase 3-12，純函式）：一步的事件 ＋ 技能卡 → 特效描述。
// 不逐招手做：由「元素 × 形狀 × 遠程／近戰」自動組合，任何新技能（工坊、之後的 LLM 生成）都會得到特效；
// 卡片缺少或形狀不認得時，改由 `skill_used.tiles` 的幾何推斷，再不行用通用預設。
// 畫布（`render/BattleRenderer.ts` 的 `playVfx`）只負責照描述畫出來；時間在 `playback.ts` 依播放速度縮放。
import { asEvent, type BattleView, type EventBase, type Pos, type SkillCard } from "../api/types";
import { areaCenter } from "./feedback";
import { samePos } from "./geometry";
import { DEFAULT_VFX_KEY, statusVfxKey, SUPPORT_VFX_KEY, WATER_VFX_KEY } from "./vfxPalette";

/** 特效的種類：飛行物、揮砍弧、單點爆發、範圍逐格爆發、光束、扇形擴散、向外擴散的環。 */
export type VfxKind = "projectile" | "slash" | "burst" | "area" | "beam" | "cone" | "aura";

/** 技能卡形狀的分類（`content/skill_shapes.yaml` 的 id）。 */
export type ShapeId =
  | "self"
  | "single"
  | "line"
  | "cone"
  | "cross"
  | "square3"
  | "ring"
  | "ground_tile"
  | "chain"
  | "allies_in_radius"
  | "object_then_tile"
  | "unit_then_tile"
  | "unit_pair";

/**
 * 技能卡 `shape` 文字的開頭（形狀的中文名，`skill_shapes.yaml` 的 `name_zh`）→ 形狀 id。
 * **只當最後的退回**：技能卡有 `icon`（Phase 3-17）時一律讀 `icon.segments[n].shape_id`；
 * 沒有 `icon` 的舊資料才用卡片的中文一句話（例如「錐形（大小 2）」「單體（射程 6）・穿透」）對照。
 */
export const SHAPE_NAMES: Readonly<Record<string, ShapeId>> = {
  自身: "self",
  單體: "single",
  直線: "line",
  錐形: "cone",
  十字: "cross",
  方陣: "square3",
  環形: "ring",
  指定格: "ground_tile",
  連鎖: "chain",
  範圍光環: "allies_in_radius",
  物件與落點: "object_then_tile",
  單位與落點: "unit_then_tile",
  兩個單位: "unit_pair",
};

/** 形狀 → 特效種類（`single` 依遠程／近戰另外決定）。 */
const SHAPE_KIND: Readonly<Record<ShapeId, VfxKind | "single">> = {
  self: "aura",
  single: "single",
  line: "beam",
  cone: "cone",
  cross: "area",
  square3: "area",
  ring: "area",
  ground_tile: "area",
  chain: "beam",
  allies_in_radius: "aura",
  object_then_tile: "area",
  unit_then_tile: "area",
  unit_pair: "area",
};

/** 骨架是光環、姿態的技能：形狀不認得時當成向外擴散的環。 */
const AURA_SKELETONS: ReadonlySet<string> = new Set(["aura", "stance"]);

/** 暴擊的強度（粒子數、爆發大小、震動都乘上它）。 */
export const CRIT_INTENSITY = 1.6;

export interface VfxCast {
  kind: VfxKind;
  /** 元素代碼（`vfxPalette.ts` 的鍵；支援技能為 `support`，不明為 `default`）。 */
  element: string;
  /** 施放者所在格。 */
  from: Pos;
  /** 主要目標：單體的目標、光束的最遠格、範圍的中心格；自身型為施放者。 */
  to: Pos;
  /** 影響的格子。 */
  tiles: Pos[];
  /** 光束、連鎖依序經過的點（含施放者）。 */
  path: Pos[];
  /** 目標距離超過 1 格（切比雪夫距離）。 */
  ranged: boolean;
  /** 1 ＝ 一般；暴擊為 `CRIT_INTENSITY`。 */
  intensity: number;
  crit: boolean;
  /** 施放前的蓄力光（技能有，一般攻擊沒有）。 */
  charge: boolean;
  /** 傳說技能：蓄力更長、更華麗（3-18b）。 */
  legendary: boolean;
  /** 蓄力的時間（毫秒；沒有蓄力為 0）。 */
  chargeMs: number;
  /** 開始的時間（毫秒，相對這一步；多段依序排開）。 */
  startMs: number;
  /** 命中（爆發開始）的時間。 */
  impactMs: number;
}

export interface VfxHit {
  pos: Pos;
  element: string;
  crit: boolean;
  /** 受擊閃白的時間（毫秒，相對這一步）。 */
  atMs: number;
}

/** 符文被引爆的爆發（3-28，沿用「爆發」型）：在符文所在格迸出元素色的光（標籤符文用預設色）。 */
export interface VfxBlast {
  pos: Pos;
  element: string;
  /** 爆發開始的時間（毫秒，相對這一步；接在最後一段技能命中的時間）。 */
  atMs: number;
}

/** 震動強度：0 不震、1 輕微、2 暴擊。 */
export type ShakeLevel = 0 | 1 | 2;

export interface StepVfx {
  casts: VfxCast[];
  hits: VfxHit[];
  /** 被引爆的符文（3-28）。 */
  blasts: VfxBlast[];
  shake: ShakeLevel;
  /** 命中前的準備時間（蓄力 ＋ 飛行）；播放時先等這段，再更新畫面與浮動數字。 */
  leadMs: number;
}

/** 基準時間（毫秒，正常速度；`scaleVfx` 依播放速度縮放）。 */
export const VFX_TIMING = {
  charge: 160,
  /** 傳說技能的蓄力（3-18b）。 */
  chargeLegendary: 380,
  projectileBase: 90,
  projectilePerTile: 45,
  projectileMax: 360,
  slash: 110,
  beam: 150,
  cone: 150,
  area: 140,
  aura: 120,
  burst: 80,
  /** 命中後爆發與粒子的時間。 */
  impact: 520,
} as const;

/** 切比雪夫距離。 */
export function chebyshev(a: Pos, b: Pos): number {
  return Math.max(Math.abs(a.x - b.x), Math.abs(a.y - b.y));
}

function posOf(v: unknown): Pos | null {
  if (typeof v === "object" && v !== null && "x" in v && "y" in v) return v as Pos;
  return null;
}

function tilesOf(v: unknown): Pos[] {
  return Array.isArray(v) ? v.map(posOf).filter((p): p is Pos => p !== null) : [];
}

/** 這個字串是不是已知的形狀 id。 */
function isShapeId(id: string | null | undefined): id is ShapeId {
  return id != null && Object.prototype.hasOwnProperty.call(SHAPE_KIND, id);
}

/** 複合技能的第幾段（0 ＝ 第一段、1 ＝ 第二段，對應 `icon.segments`）。 */
export type SegmentIndex = 0 | 1;

/**
 * 技能卡的形狀 id：讀 `icon.segments[segment].shape_id`；卡片沒有 `icon`（舊資料）時第一段才退回
 * 中文名對照；卡片沒有或不認得時 `null`。
 */
export function shapeIdOf(
  card: Pick<SkillCard, "shape"> & Partial<Pick<SkillCard, "icon">> | undefined | null,
  segment: SegmentIndex = 0,
): ShapeId | null {
  if (card == null) return null;
  const segments = card.icon?.segments;
  if (segments !== undefined) {
    const id = segments[segment]?.shape_id;
    return isShapeId(id) ? id : null;
  }
  if (segment > 0) return null;
  const name = card.shape.split(/[（(・\s]/u)[0] ?? "";
  return SHAPE_NAMES[name] ?? null;
}

/** 從影響的格子推斷形狀（卡片缺少或與實際範圍不符時）。 */
export function inferShape(from: Pos, tiles: readonly Pos[]): ShapeId {
  if (tiles.length === 0 || tiles.every((p) => samePos(p, from))) return "self";
  if (tiles.length === 1) return "single";
  if (isRay(from, tiles)) return "line";
  return "square3";
}

/** 所有格子都在施放者的同一個正方向上、從相鄰格起連續排開。 */
function isRay(from: Pos, tiles: readonly Pos[]): boolean {
  const first = tiles[0] as Pos;
  const dx = Math.sign(first.x - from.x);
  const dy = Math.sign(first.y - from.y);
  if ((dx !== 0) === (dy !== 0)) return false;
  const steps = tiles.map((p) => (dx !== 0 ? (p.x - from.x) * dx : (p.y - from.y) * dy));
  const offAxis = tiles.some((p) => (dx !== 0 ? p.y !== from.y : p.x !== from.x));
  if (offAxis) return false;
  const sorted = [...steps].sort((a, b) => a - b);
  return sorted.every((s, i) => s === i + 1);
}

/** 卡片的形狀和實際影響的格子不符（修正規則轉換形狀等）時，以格子推斷為準。 */
function effectiveShape(card: SkillCard | undefined, segment: SegmentIndex, from: Pos, tiles: readonly Pos[]): ShapeId {
  const fromCard = shapeIdOf(card, segment);
  if (fromCard === null) {
    const skeleton = card?.icon?.segments[segment]?.skeleton ?? (segment === 0 ? card?.skeleton : undefined);
    if (skeleton != null && AURA_SKELETONS.has(skeleton) && tiles.every((p) => chebyshev(p, from) <= 3)) {
      return tiles.length <= 1 ? "self" : "allies_in_radius";
    }
    return inferShape(from, tiles);
  }
  if (fromCard === "single" && tiles.length > 1) return inferShape(from, tiles);
  if (fromCard === "self" && tiles.some((p) => !samePos(p, from))) return inferShape(from, tiles);
  return fromCard;
}

/** 最遠的一格（光束的終點）。 */
function farthest(from: Pos, tiles: readonly Pos[]): Pos {
  let best = tiles[0] as Pos;
  for (const p of tiles) if (chebyshev(p, from) > chebyshev(best, from)) best = p;
  return best;
}

interface Segment {
  caster: string;
  from: Pos;
  tiles: Pos[];
  card: SkillCard | undefined;
  /** 複合技能的第幾段（第二段讀 `icon.segments[1]`）。 */
  segment: SegmentIndex;
  /** 一般攻擊（沒有技能）。 */
  basic: boolean;
  /** 一般攻擊的目標。 */
  target: Pos | null;
  element: string | null;
  touched: string | null;
  support: boolean;
  /** 這一段生成了水表面（3-18b：沒有傷害元素時用水花配色）。 */
  water: boolean;
  /** 這一段施放者施加的第一個狀態（3-18b：沒有傷害的技能依它上色）。 */
  status: string | null;
  /** 傳說技能（卡片稀有度）。 */
  legendary: boolean;
  crit: boolean;
  /** 這一段命中的單位位置（依序；連鎖用）。 */
  hitPath: Pos[];
  hits: Array<{ pos: Pos; element: string; crit: boolean }>;
}

export type VfxCards = Readonly<Record<string, SkillCard | undefined>>;

/** 單體形狀：遠程 → 飛行物；近戰 → 揮砍弧；目標是自己 → 原地爆發。 */
function singleKind(from: Pos, to: Pos): VfxKind {
  if (samePos(from, to)) return "burst";
  return chebyshev(from, to) > 1 ? "projectile" : "slash";
}

function castKind(seg: Segment, shape: ShapeId, to: Pos): VfxKind {
  const kind = SHAPE_KIND[shape];
  return kind === "single" ? singleKind(seg.from, to) : kind;
}

function castTarget(seg: Segment, shape: ShapeId): Pos {
  if (seg.target !== null) return seg.target;
  if (seg.tiles.length === 0) return seg.from;
  switch (SHAPE_KIND[shape]) {
    case "aura":
      return seg.from;
    case "single":
      return seg.tiles[0] as Pos;
    case "beam":
    case "cone":
      return farthest(seg.from, seg.tiles);
    default:
      return areaCenter(seg.tiles);
  }
}

function leadOf(kind: VfxKind, from: Pos, to: Pos): number {
  switch (kind) {
    case "projectile":
      return Math.min(VFX_TIMING.projectileMax, VFX_TIMING.projectileBase + VFX_TIMING.projectilePerTile * chebyshev(from, to));
    case "slash":
      return VFX_TIMING.slash;
    case "beam":
      return VFX_TIMING.beam;
    case "cone":
      return VFX_TIMING.cone;
    case "area":
      return VFX_TIMING.area;
    case "aura":
      return VFX_TIMING.aura;
    case "burst":
      return VFX_TIMING.burst;
  }
}

/**
 * 這一段的配色鍵：傷害元素 → 觸及的元素 → 生成水表面（水花）→ 治療護盾（支援）→ 施加的狀態色
 * → 一般攻擊的物理 → 通用預設。
 */
function segmentElement(seg: Segment): string {
  if (seg.element !== null) return seg.element;
  if (seg.touched !== null) return seg.touched;
  if (seg.water) return WATER_VFX_KEY;
  if (seg.support) return SUPPORT_VFX_KEY;
  if (seg.status !== null) return statusVfxKey(seg.status);
  return seg.basic ? "physical" : DEFAULT_VFX_KEY;
}

function toCast(seg: Segment, startMs: number): VfxCast {
  const shape = seg.basic ? "single" : effectiveShape(seg.card, seg.segment, seg.from, seg.tiles);
  const to = castTarget(seg, shape);
  const kind = castKind(seg, shape, to);
  const tiles = seg.tiles.length > 0 ? seg.tiles : [to];
  const path = shape === "chain" && seg.hitPath.length > 0 ? [seg.from, ...seg.hitPath] : [seg.from, to];
  const charge = !seg.basic;
  const chargeMs = !charge ? 0 : seg.legendary ? VFX_TIMING.chargeLegendary : VFX_TIMING.charge;
  const impactMs = startMs + chargeMs + leadOf(kind, seg.from, to);
  return {
    kind,
    element: segmentElement(seg),
    from: seg.from,
    to,
    tiles,
    path,
    ranged: chebyshev(seg.from, to) > 1,
    intensity: seg.crit ? CRIT_INTENSITY : 1,
    crit: seg.crit,
    charge,
    legendary: charge && seg.legendary,
    chargeMs,
    startMs,
    impactMs,
  };
}

type Locate = (id: unknown) => Pos | null;

function openSegment(e: EventBase, at: Locate, cards: VfxCards): Segment | null {
  const base = { element: null, touched: null, support: false, water: false, status: null, legendary: false, crit: false, hitPath: [], hits: [] };
  if (e.type === "skill_used" || e.type === "skill_followup") {
    const caster = String(e.unit_id);
    const from = e.type === "skill_followup" ? (posOf(e.origin) ?? at(caster)) : at(caster);
    if (from === null) return null;
    // 第二段讀 `icon.segments[1]`（沒有 icon 的舊資料交給格子推斷）
    const card = cards[String(e.skill_id)];
    const segment: SegmentIndex = e.type === "skill_followup" ? 1 : 0;
    const legendary = card?.rarity_id === "legendary" || card?.icon?.rarity === "legendary";
    return { ...base, legendary, caster, from, tiles: tilesOf(e.tiles), card, segment, basic: false, target: null };
  }
  const caster = String(e.attacker_id);
  const from = at(caster);
  const target = at(e.target_id);
  if (from === null || target === null) return null;
  return { ...base, caster, from, tiles: [target], card: undefined, segment: 0, basic: true, target };
}

/** 事件是否開啟新的一段（技能、複合技能第二段、不屬於目前技能的一般攻擊）。 */
function opensSegment(e: EventBase, current: Segment | null): boolean {
  if (e.type === "skill_used" || e.type === "skill_followup") return true;
  return e.type === "attack_rolled" && (current === null || current.caster !== String(e.attacker_id) || current.basic);
}

/** 把一個事件的資訊記到目前這一段（元素、暴擊、命中）；不屬於任何一段的傷害另外回傳。 */
function absorb(seg: Segment | null, e: EventBase, at: Locate): VfxHit | null {
  if (e.type === "damage_dealt") {
    const amount = typeof e.amount === "number" ? e.amount : 0;
    const pos = at(e.target_id);
    const element = typeof e.element === "string" ? e.element : DEFAULT_VFX_KEY;
    const crit = e.crit === true;
    const ours = seg !== null && e.source_id === seg.caster;
    if (ours) {
      seg.element ??= element;
      seg.crit ||= crit;
      if (pos !== null && !seg.hitPath.some((p) => samePos(p, pos))) seg.hitPath.push(pos);
    }
    if (amount <= 0 || pos === null) return null;
    if (ours) {
      seg.hits.push({ pos, element, crit });
      return null;
    }
    return { pos, element, crit, atMs: 0 };
  }
  if (seg === null) return null;
  if (e.type === "element_touched" && e.source_id === seg.caster && typeof e.element === "string") seg.touched ??= e.element;
  // 吹送（3-54a）：沒有傷害的吹送技能也用風的特效
  if (e.type === "surface_blown" && e.source_id === seg.caster) seg.touched ??= "wind";
  if (e.type === "healed" || e.type === "shield_gained") seg.support = true;
  if (e.type === "surface_changed" && e.cause === "effect" && e.after === "water") seg.water = true;
  if (e.type === "status_applied" && e.source_id === seg.caster && typeof e.status_id === "string") seg.status ??= e.status_id;
  return null;
}

/**
 * 一步的事件 → 特效描述。`view` 是該步結束時的畫面（單位位置以它為準，與地圖回饋相同）；
 * `cards` 是技能 ID → 技能卡（缺的技能以格子推斷形狀）。
 */
export function vfxFor(events: readonly Record<string, unknown>[], view: BattleView, cards: VfxCards): StepVfx {
  const positions = new Map(view.units.map((u) => [u.id, u.pos]));
  const at: Locate = (id) => (typeof id === "string" ? (positions.get(id) ?? null) : null);
  const segments: Segment[] = [];
  const loose: VfxHit[] = [];
  const blasts: VfxBlast[] = [];
  let current: Segment | null = null;
  for (const raw of events) {
    const e = asEvent(raw);
    if (e.type === "rune_removed" && e.reason === "detonated") {
      const pos = posOf(e.pos);
      if (pos !== null) blasts.push({ pos, element: typeof e.element === "string" ? e.element : DEFAULT_VFX_KEY, atMs: 0 });
      continue;
    }
    if (opensSegment(e, current)) {
      const seg = openSegment(e, at, cards);
      if (seg !== null) {
        segments.push(seg);
        current = seg;
      }
      continue;
    }
    const hit = absorb(current, e, at);
    if (hit !== null) loose.push(hit);
  }
  return assemble(segments, loose, blasts);
}

function assemble(segments: readonly Segment[], loose: readonly VfxHit[], rawBlasts: readonly VfxBlast[]): StepVfx {
  const casts: VfxCast[] = [];
  const hits: VfxHit[] = [];
  let clock = 0;
  for (const seg of segments) {
    const cast = toCast(seg, clock);
    casts.push(cast);
    for (const h of seg.hits) hits.push({ ...h, atMs: cast.impactMs });
    clock = cast.impactMs;
  }
  for (const h of loose) hits.push({ ...h, atMs: clock });
  const blasts = rawBlasts.map((b) => ({ ...b, atMs: clock }));
  const shake: ShakeLevel = hits.some((h) => h.crit) ? 2 : segments.some((s) => s.hits.length > 0) ? 1 : 0;
  return { casts, hits, blasts, shake, leadMs: clock };
}

/** 依播放速度縮放所有時間（慢 2、正常 1、快 0.5）。 */
export function scaleVfx(vfx: StepVfx, scale: number): StepVfx {
  const s = (ms: number) => Math.round(ms * scale);
  return {
    casts: vfx.casts.map((c) => ({ ...c, startMs: s(c.startMs), impactMs: s(c.impactMs), chargeMs: s(c.chargeMs) })),
    hits: vfx.hits.map((h) => ({ ...h, atMs: s(h.atMs) })),
    blasts: vfx.blasts.map((b) => ({ ...b, atMs: s(b.atMs) })),
    shake: vfx.shake,
    leadMs: s(vfx.leadMs),
  };
}

/** 沒有任何特效（略過、純移動、結束回合）。 */
export function isEmptyVfx(vfx: StepVfx): boolean {
  return vfx.casts.length === 0 && vfx.hits.length === 0 && vfx.blasts.length === 0;
}

// ---- 傳送的消散與出現（3-18b） -------------------------------------------------

/** 傳送類位移（淡出淡入）的特效：起點消散、終點出現。時間相對這一步位移動畫的開始。 */
export interface VfxWarp {
  kind: "vanish" | "appear";
  pos: Pos;
  startMs: number;
  endMs: number;
}

/**
 * 位移動畫 → 特效：只有淡出淡入的位移（傳送、交換、瞬步）才有。前半（單位在原地淡出）起點消散，
 * 後半（在新格淡入）終點出現；`durationMs` 為 0（略過）時沒有。
 */
export function warpPlan(move: { style: string; from: Pos; to: Pos; durationMs: number }): VfxWarp[] {
  if (move.style !== "fade" || move.durationMs <= 0) return [];
  const half = move.durationMs / 2;
  return [
    { kind: "vanish", pos: move.from, startMs: 0, endMs: half },
    { kind: "appear", pos: move.to, startMs: half, endMs: move.durationMs },
  ];
}
