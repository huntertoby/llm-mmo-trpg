// 技能特效的推導（Phase 3-12，純函式）：一步的事件 ＋ 技能卡 → 特效描述。
// 不逐招手做：由「元素 × 形狀 × 遠程／近戰」自動組合，任何新技能（工坊、之後的 LLM 生成）都會得到特效；
// 卡片缺少或形狀不認得時，改由 `skill_used.tiles` 的幾何推斷，再不行用通用預設。
// 畫布（`render/BattleRenderer.ts` 的 `playVfx`）只負責照描述畫出來；時間在 `playback.ts` 依播放速度縮放。
import { asEvent, type BattleView, type EventBase, type Pos, type SkillCard } from "../api/types";
import { areaCenter, immobilityIn, type Immobility } from "./feedback";
import { samePos } from "./geometry";
import type { ArcSpec } from "../render/attackVariants";
import type { FxLook } from "../render/skillVariants";
import { dodgeSide, reactVariant } from "../render/reactClips";
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
  /** 近身弧光的形狀與方向（6N-6：普攻挑到的變體，`skillTimeline` 填）；沒有＝由上往下（原本的弧）。 */
  arc?: ArcSpec;
  /** 技能變體的特效層（6N-8：飛行物軌跡、爆發形狀、粒子分布，`skillTimeline` 填）；沒有＝原本的直線、圓形閃光、均勻粒子。 */
  look?: FxLook;
  /**
   * 身體片段瞄準的格子（VFX-1）：只有「只給自己」的那一段改畫在施放者身上時才有＝改之前的 `to`。
   * `skillTimeline` 的朝向、異形動作類型、轉向特效照它（`aimOf`），身體和改之前完全相同；特效本身照 `to`。
   */
  aim?: Pos;
}

/** 身體片段要朝的格子（VFX-1）：有 `aim` 用它，否則＝`to`。 */
export function aimOf(cast: Pick<VfxCast, "to" | "aim">): Pos {
  return cast.aim ?? cast.to;
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

/** 舊的震動強度（3-12：0 不震、1 輕微、2 暴擊）。6H-1 起繪製器改看 `shakes`（只在重擊、爆炸、Boss 大招震），這個欄位只留著給舊的呼叫端。 */
export type ShakeLevel = 0 | 1 | 2;

/**
 * 一下扣血或一次爆炸（6H-1；`impact.ts` 由它推停頓分級與微震）：
 * - `hit`：`damage_dealt` 有扣血；`lost` ＝ 實際扣掉目標最大 HP 的比例（‰，取整數下限，事件沒有 `hp_before`／`hp_after` 時 0）；
 * - `boom`：爆炸事件（`object_exploded`、`bomb_exploded`、`rune_removed` 的 `reason: detonated`）。
 */
export interface VfxImpact {
  kind: "hit" | "boom";
  pos: Pos;
  /** 受擊者（`hit`）；爆炸沒有。 */
  unitId?: string;
  lost: number;
  crit: boolean;
  /** 事件的 `seq`（震動相位的雜湊用）。 */
  seq: number;
  /** 時間（毫秒，相對這一步；＝那一段的命中點）。 */
  atMs: number;
}

type RawImpact = Omit<VfxImpact, "atMs">;

/** 爆炸事件（6H-1 微震）。 */
const BOOM_EVENTS: ReadonlySet<string> = new Set(["object_exploded", "bomb_exploded"]);

/** 事件 → 扣血或爆炸（只讀事件欄位與畫面的最大 HP）；都不是時 `null`。 */
function impactOf(e: EventBase, at: (id: unknown) => Pos | null, maxHp: (id: string) => number): RawImpact | null {
  const seq = typeof e.seq === "number" ? e.seq : 0;
  if (BOOM_EVENTS.has(e.type) || (e.type === "rune_removed" && e.reason === "detonated")) {
    const pos = posOf(e.pos);
    return pos === null ? null : { kind: "boom", pos, lost: 0, crit: false, seq };
  }
  if (e.type !== "damage_dealt") return null;
  const id = typeof e.target_id === "string" ? e.target_id : null;
  const pos = at(e.target_id);
  const amount = typeof e.amount === "number" ? e.amount : 0;
  if (id === null || pos === null || amount <= 0) return null;
  const max = maxHp(id);
  const lost = typeof e.hp_before === "number" && typeof e.hp_after === "number" && max > 0 ? Math.floor((Math.max(0, e.hp_before - e.hp_after) * 1000) / max) : 0;
  return { kind: "hit", pos, unitId: id, lost, crit: e.crit === true, seq };
}

export interface StepVfx {
  casts: VfxCast[];
  hits: VfxHit[];
  /** 被引爆的符文（3-28）。 */
  blasts: VfxBlast[];
  shake: ShakeLevel;
  /** 命中前的準備時間（蓄力 ＋ 飛行）；播放時先等這段，再更新畫面與浮動數字。 */
  leadMs: number;
  /** 受擊者的身體反應（6N-4）；舊的呼叫端沒有。 */
  reactions?: VfxReaction[];
  /** 特殊結果的強化（6N-5，`specials.ts`）：暴擊、擊殺、格擋成功、閃避成功、Boss 大招。 */
  specials?: VfxSpecial[];
  /** 命中時的停頓（6N-5；效果時鐘停在 `atMs` 那一刻 `ms` 毫秒）；依時間排序、同一刻只有一個。 */
  stops?: VfxStop[];
  /** 這一步的扣血與爆炸（6H-1）；沒有時省略。 */
  impacts?: VfxImpact[];
  /** 鏡頭微震（6H-1，`impact.ts`）：只有重擊、爆炸、Boss 大招。 */
  shakes?: VfxShake[];
  /** 最後一擊放慢（6H-1，`impact.ts`）：一場最多一次。 */
  slow?: VfxSlow;
}

/** 鏡頭微震（6H-1；需求 docs/archive/art/打擊感移植需求.md 第 3 節）。 */
export interface VfxShake {
  kind: "heavy" | "blast" | "boss";
  /** 開始（毫秒，相對這一步；已縮放或未縮放跟著 `StepVfx`）。 */
  atMs: number;
  /** 長度（跟著播放速度縮放）。 */
  ms: number;
  /** 正常速度的長度（震的頻率照它算，慢放時震得一樣慢）。 */
  baseMs: number;
  /** 幅度（畫面像素，不隨格子大小放大、不隨播放速度改變）。 */
  px: number;
  /** 相位（0～1，照「戰鬥鍵:事件 seq」的雜湊）。 */
  phase: number;
  /** 震的那一下打到的格子（減少動態時改成這些人身上的白閃加長）。 */
  targets: Pos[];
}

/** 最後一擊放慢（6H-1；需求第 4 節）：效果時鐘在 `fromMs`～`toMs` 之間以 `rate` 倍速走，前後 `rampMs` 漸變。 */
export interface VfxSlow {
  /** 命中點（擊倒的那一下）。 */
  atMs: number;
  fromMs: number;
  toMs: number;
  rampMs: number;
  /** 最慢時的倍速（0.4）。 */
  rate: number;
  /** 觸發：打倒最後一個敵人、擊倒 Boss。 */
  reason: "last" | "boss";
  unitId: string;
}

/** 特殊結果（6N-5；需求第二批第 5 節，選項 B：特效加停頓，不做慢動作和鏡頭拉近）。 */
export type SpecialKind = "crit" | "kill" | "block" | "dodge" | "boss" | "part_break";

export interface VfxSpecial {
  kind: SpecialKind;
  /** 出現的位置（暴擊、擊殺、格擋、閃避＝受擊者；Boss 大招＝施放者）。 */
  pos: Pos;
  unitId: string | null;
  /** 開始的時間（毫秒，相對這一步；＝那一段的命中點，Boss 大招＝出招開始）。 */
  atMs: number;
  /** 格擋成功：被彈開半步的攻擊者。 */
  attackerId?: string;
}

export interface VfxStop {
  atMs: number;
  ms: number;
}

/**
 * 受擊者的身體反應（6N-4；需求第二批第 4 節，只讀事件）：
 * - `hit` 受擊：`damage_dealt`（扣血）；`heavy`：扣血 ≥ 最大 HP 的 25%（多一點震動）；
 * - `block` 格擋：`damage_dealt` 的 `block_permille < 1000`；
 * - `dodge` 閃避：`attack_rolled` 的 `hit: false`；
 * - `down` 倒下：`unit_downed`（取代同一段的受擊）；
 * - `rise` 復活（6N-5）：`unit_revived`（倒地者站起來、一圈綠光）。
 */
export type ReactKind = "hit" | "heavy" | "block" | "dodge" | "down" | "rise";

export interface VfxReaction {
  unitId: string;
  pos: Pos;
  kind: ReactKind;
  /** 開始的時間（毫秒，相對這一步；＝那一段的命中點）。 */
  atMs: number;
  /** 觸發事件的 `seq`（挑變體的雜湊用）。 */
  seq: number;
  /** 屬於第幾段（`casts` 的索引）；不屬於任何一段為 -1。 */
  cast: number;
  /** 閃避往哪一邊（1 ＝ 面向的右手邊）；照「戰鬥鍵:seq:單位:dodge」的雜湊（`reactClips.dodgeSide`）。 */
  side?: 1 | -1;
  /** 受擊、重擊、閃避的變體（6N-7；`reactClips.reactVariant`，鍵用受擊者 ID）。 */
  variant?: number;
}

/** 扣血達最大 HP 的這個比例（‰）以上算重擊（多一點震動）。 */
export const HEAVY_HIT_PERMILLE = 250;

/** 同一段同一人只留一個反應：復活 ＞ 倒下 ＞ 格擋 ＞ 重擊 ＞ 受擊 ＞ 閃避。 */
const REACT_RANK: Readonly<Record<ReactKind, number>> = { rise: 6, down: 5, block: 4, heavy: 3, hit: 2, dodge: 1 };

interface RawReact {
  unitId: string;
  pos: Pos;
  kind: ReactKind;
  seq: number;
  side?: 1 | -1;
  variant?: number;
}

/**
 * 同一人已有反應 `old` 時合併 `r`：只往上升級（復活 ＞ 倒下 ＞ 格擋 ＞ 重擊 ＞ 受擊 ＞ 閃避），
 * 升級時種類、seq、變體、閃避方向都跟著升級後的那個事件（6R-F：`addReact` 和最後一刻的合併共用）。
 */
export function upgradeReact(old: Pick<RawReact, "kind" | "seq" | "side" | "variant">, r: Pick<RawReact, "kind" | "seq" | "side" | "variant">): void {
  if (REACT_RANK[r.kind] <= REACT_RANK[old.kind]) return;
  old.kind = r.kind;
  old.seq = r.seq;
  if (r.variant === undefined) delete old.variant;
  else old.variant = r.variant;
  if (r.side === undefined) delete old.side;
  else old.side = r.side;
}

/** 記一個反應：同一人已有的反應只往上升級（變體跟著升級後的那個事件）。 */
function addReact(list: RawReact[], r: RawReact): void {
  const old = list.find((x) => x.unitId === r.unitId);
  if (old === undefined) list.push({ ...r });
  else upgradeReact(old, r);
}

/** 事件 → 受擊者的反應（只讀事件欄位）。不是反應事件、或找不到人時 `null`。 */
export function reactOf(e: EventBase, at: (id: unknown) => Pos | null, maxHp: (id: string) => number, battleKey = "", immobile: (id: unknown) => boolean = () => false): RawReact | null {
  const seq = typeof e.seq === "number" ? e.seq : 0;
  if (e.type === "damage_dealt") {
    const id = typeof e.target_id === "string" ? e.target_id : null;
    const pos = at(e.target_id);
    const amount = typeof e.amount === "number" ? e.amount : 0;
    if (id === null || pos === null || amount <= 0) return null;
    const block = typeof e.block_permille === "number" && e.block_permille < 1000;
    const lost = typeof e.hp_before === "number" && typeof e.hp_after === "number" ? e.hp_before - e.hp_after : 0;
    const max = maxHp(id);
    const heavy = max > 0 && lost * 1000 >= max * HEAVY_HIT_PERMILLE;
    if (block) return { unitId: id, pos, kind: "block", seq };
    return { unitId: id, pos, kind: heavy ? "heavy" : "hit", seq, variant: reactVariant(battleKey, seq, id, "hit") };
  }
  // 6N-6：目標不能動（冰凍、暈眩、倒地、定身）時沒打中不播閃避片段
  if (e.type === "attack_rolled" && e.hit === false && !immobile(e.target_id)) {
    const id = typeof e.target_id === "string" ? e.target_id : null;
    const pos = at(e.target_id);
    return id === null || pos === null ? null : { unitId: id, pos, kind: "dodge", seq, side: dodgeSide(battleKey, seq, id), variant: reactVariant(battleKey, seq, id, "dodge") };
  }
  if (e.type === "unit_downed" || e.type === "unit_revived") {
    const id = typeof e.unit_id === "string" ? e.unit_id : null;
    const pos = at(e.unit_id);
    return id === null || pos === null ? null : { unitId: id, pos, kind: e.type === "unit_downed" ? "down" : "rise", seq };
  }
  return null;
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
  /** 受擊者的身體反應（6N-4）。 */
  reacts: RawReact[];
  /** 這一段的扣血與爆炸（6H-1；停頓分級、微震用）。 */
  impacts: RawImpact[];
  /** 施放者這一步結束時的位置（VFX-1；複合技能第二段的 `from` 是落點，不一定是施放者）。 */
  casterPos: Pos | null;
  /** 這一段有治療、護盾或狀態落在施放者自己身上（VFX-1）。 */
  selfFx: boolean;
  /** 這一段碰到施放者以外的單位或格子（命中判定、傷害、別人的治療／護盾／狀態、地面與物件…；VFX-1）。 */
  elsewhere: boolean;
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
  const cast: VfxCast = {
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
  const self = onlySelfAt(seg);
  return self === null ? cast : onCaster(cast, self);
}

/**
 * VFX-1（美術 PM，`docs/art/QI-4b與BAL-21b驗收.md` 2.2 (a)）：這一段「只給自己」時回施放者的位置，否則 `null`。
 * 三個條件全部成立才算：(a) 沒有碰到施放者以外的任何單位或格子（沒有命中）；(b) 治療、護盾、狀態只落在施放者自己身上
 * （至少一個）；(c) 施放者不在這一段的格子裡（形狀本來就是自身、範圍包含施放者的照舊）。一般攻擊不算。
 */
function onlySelfAt(seg: Segment): Pos | null {
  if (seg.basic || seg.casterPos === null || !seg.selfFx || seg.elsewhere || seg.tiles.length === 0) return null;
  const at = seg.casterPos;
  return seg.tiles.some((p) => samePos(p, at)) ? null : at;
}

/** 特效改成施放者身上的光環（顏色、時間照舊）；身體照原本的目標（`aim`）。 */
function onCaster(cast: VfxCast, at: Pos): VfxCast {
  return { ...cast, kind: "aura", from: at, to: at, tiles: [at], path: [at, at], ranged: false, aim: cast.to };
}

type Locate = (id: unknown) => Pos | null;

function openSegment(e: EventBase, at: Locate, cards: VfxCards): Segment | null {
  const base = { element: null, touched: null, support: false, water: false, status: null, legendary: false, crit: false, hitPath: [], hits: [], reacts: [], impacts: [], selfFx: false, elsewhere: false };
  if (e.type === "skill_used" || e.type === "skill_followup") {
    const caster = String(e.unit_id);
    const casterPos = at(caster);
    const from = e.type === "skill_followup" ? (posOf(e.origin) ?? casterPos) : casterPos;
    if (from === null) return null;
    // 第二段讀 `icon.segments[1]`（沒有 icon 的舊資料交給格子推斷）
    const card = cards[String(e.skill_id)];
    const segment: SegmentIndex = e.type === "skill_followup" ? 1 : 0;
    const legendary = card?.rarity_id === "legendary" || card?.icon?.rarity === "legendary";
    return { ...base, legendary, caster, casterPos, from, tiles: tilesOf(e.tiles), card, segment, basic: false, target: null };
  }
  const caster = String(e.attacker_id);
  const from = at(caster);
  const target = at(e.target_id);
  if (from === null || target === null) return null;
  return { ...base, caster, casterPos: from, from, tiles: [target], card: undefined, segment: 0, basic: true, target };
}

/** 落在單位身上的增益事件 → 受益者欄位（VFX-1）。 */
const SUPPORT_TARGET: Readonly<Record<string, string>> = { healed: "target_id", shield_gained: "unit_id", status_applied: "target_id" };

/** 蓄力預告（落點是下一段的事，不算這一段碰到的格子；VFX-1）。 */
const NEUTRAL_EVENTS: ReadonlySet<string> = new Set(["followup_charged"]);

/**
 * VFX-1：記下這一段碰到誰（`onlySelfAt` 用）。治療、護盾、狀態看受益者是不是施放者；命中判定、傷害一律算碰到別人；
 * 其他事件只要欄位裡出現施放者以外的單位、或施放者所在格以外的格子，就算碰到別人（保守：地面、物件、位移都算）。
 */
function noteReach(seg: Segment, e: EventBase, at: Locate): void {
  if (seg.basic || NEUTRAL_EVENTS.has(e.type)) return;
  const field = SUPPORT_TARGET[e.type];
  if (field !== undefined) {
    if (e[field] === seg.caster) seg.selfFx = true;
    else seg.elsewhere = true;
    return;
  }
  if (e.type === "damage_dealt" || e.type === "attack_rolled") {
    seg.elsewhere = true;
    return;
  }
  if (reachesOthers(e, seg, at)) seg.elsewhere = true;
}

function reachesOthers(e: EventBase, seg: Segment, at: Locate): boolean {
  const self = seg.casterPos;
  const otherPos = (p: Pos | null) => p !== null && (self === null || !samePos(p, self));
  for (const [key, v] of Object.entries(e)) {
    if (key === "type" || key === "seq" || key === "round") continue;
    if (typeof v === "string" && v !== seg.caster && at(v) !== null) return true;
    if (otherPos(posOf(v))) return true;
    if (Array.isArray(v) && v.some((x) => otherPos(posOf(x)))) return true;
  }
  return false;
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
 * `immobility`：打的那一刻能不能動（6F-6 `feedback.immobilityOf`；省略時只看 `view`）。
 */
export function vfxFor(events: readonly Record<string, unknown>[], view: BattleView, cards: VfxCards, immobility: Immobility = immobilityIn(view)): StepVfx {
  const positions = new Map(view.units.map((u) => [u.id, u.pos]));
  const hpMax = new Map(view.units.map((u) => [u.id, u.max_hp]));
  const at: Locate = (id) => (typeof id === "string" ? (positions.get(id) ?? null) : null);
  const maxHp = (id: string) => hpMax.get(id) ?? 0;
  const segments: Segment[] = [];
  const loose: VfxHit[] = [];
  const looseReacts: RawReact[] = [];
  const blasts: VfxBlast[] = [];
  const looseImpacts: RawImpact[] = [];
  let current: Segment | null = null;
  for (const raw of events) {
    const e = asEvent(raw);
    // 戰鬥鍵：戰鬥畫面資料裡同一場戰鬥不變的地圖 ID（沒有戰鬥 ID；見 6N-4 報告）
    const react = reactOf(e, at, maxHp, view.map_id ?? "", (id) => immobility(e, id));
    const imp = impactOf(e, at, maxHp); // 6H-1：停頓分級、微震
    if (imp !== null) (impactBelongs(current, e, imp) ?? looseImpacts).push(imp);
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
        if (react !== null) addReact(seg.reacts, react); // 一般攻擊沒打中（開段的那個命中判定）
      }
      continue;
    }
    const hit = absorb(current, e, at);
    if (hit !== null) loose.push(hit);
    if (current !== null) noteReach(current, e, at);
    if (react !== null) addReact(reactBelongs(current, e) ?? looseReacts, react);
  }
  return assemble(segments, loose, blasts, looseReacts, looseImpacts);
}

/** 扣血、爆炸算哪一段（6H-1）：這一段施放者打的算這一段；別人打的、爆炸（環境連鎖）放到最後（`null`）。 */
function impactBelongs(seg: Segment | null, e: EventBase, imp: RawImpact): RawImpact[] | null {
  if (seg === null || imp.kind === "boom") return null;
  return e.source_id === seg.caster ? seg.impacts : null;
}

/** 反應算哪一段：這一段施放者打的、這一段裡倒下的算這一段；別人打的（反擊、持續傷害）放到最後（`null`）。 */
function reactBelongs(seg: Segment | null, e: EventBase): RawReact[] | null {
  if (seg === null) return null;
  if (e.type === "unit_downed") return seg.reacts;
  if (e.type === "unit_revived") return e.source_id === seg.caster ? seg.reacts : null; // 6N-5：這一段施放者救起來的
  const source = e.type === "damage_dealt" ? e.source_id : e.attacker_id;
  return source === seg.caster ? seg.reacts : null;
}

function assemble(segments: readonly Segment[], loose: readonly VfxHit[], rawBlasts: readonly VfxBlast[], looseReacts: readonly RawReact[] = [], looseImpacts: readonly RawImpact[] = []): StepVfx {
  const casts: VfxCast[] = [];
  const hits: VfxHit[] = [];
  const reactions: VfxReaction[] = [];
  const impacts: VfxImpact[] = [];
  let clock = 0;
  segments.forEach((seg, i) => {
    const cast = toCast(seg, clock);
    casts.push(cast);
    for (const h of seg.hits) hits.push({ ...h, atMs: cast.impactMs });
    for (const r of seg.reacts) reactions.push({ ...r, atMs: cast.impactMs, cast: i });
    for (const m of seg.impacts) impacts.push({ ...m, atMs: cast.impactMs });
    clock = cast.impactMs;
  });
  for (const h of loose) hits.push({ ...h, atMs: clock });
  for (const m of looseImpacts) impacts.push({ ...m, atMs: clock });
  for (const r of looseReacts) {
    // 同一人在最後那一刻已有反應時合併（例如反擊打中、又倒下）
    const same = reactions.find((x) => x.unitId === r.unitId && x.atMs === clock);
    if (same === undefined) reactions.push({ ...r, atMs: clock, cast: -1 });
    else upgradeReact(same, r);
  }
  const blasts = rawBlasts.map((b) => ({ ...b, atMs: clock }));
  const shake: ShakeLevel = hits.some((h) => h.crit) ? 2 : segments.some((s) => s.hits.length > 0) ? 1 : 0;
  return { casts, hits, blasts, shake, leadMs: clock, reactions, ...(impacts.length === 0 ? {} : { impacts }) };
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
    ...(vfx.reactions === undefined ? {} : { reactions: vfx.reactions.map((r) => ({ ...r, atMs: s(r.atMs) })) }),
    ...(vfx.specials === undefined ? {} : { specials: vfx.specials.map((x) => ({ ...x, atMs: s(x.atMs) })) }),
    ...(vfx.stops === undefined ? {} : { stops: vfx.stops.map((x) => ({ atMs: s(x.atMs), ms: s(x.ms) })) }),
    // 6H-1：扣血與爆炸、微震（幅度不縮放）、最後一擊放慢（倍速不縮放）
    ...(vfx.impacts === undefined ? {} : { impacts: vfx.impacts.map((x) => ({ ...x, atMs: s(x.atMs) })) }),
    ...(vfx.shakes === undefined ? {} : { shakes: vfx.shakes.map((x) => ({ ...x, atMs: s(x.atMs), ms: s(x.ms) })) }),
    ...(vfx.slow === undefined ? {} : { slow: { ...vfx.slow, atMs: s(vfx.slow.atMs), fromMs: s(vfx.slow.fromMs), toMs: s(vfx.slow.toMs), rampMs: s(vfx.slow.rampMs) } }),
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
