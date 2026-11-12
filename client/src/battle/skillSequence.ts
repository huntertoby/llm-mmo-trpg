// 技能串接器（Phase 6N-1／6N-2；需求 docs/art/動畫移植需求第二批.md 第 2.1 節，方案 docs/art/動畫方案.md 2.3 (2)）。
// 純函式、確定性：一步的事件 ＋ 技能卡部件的順序 ＋ 原本的特效時間軸（vfx.ts）→ 身體片段的時間軸，並把特效時間對齊到出招的命中點。
// 只讀事件、不改規則；LLM 不參與，也沒有新增技能欄位。
// - 片段順序：起手（每個施放者在這一步只播一次；複合技能的後段直接出招）→ 出招前的原語（加力）→ 出招 → 出招後的原語 → 收勢。
// - 命中點對齊：近身的出招命中那一刻 ＝ 特效命中；遠程的出招放出那一刻 ＝ 飛行物離手（再飛到目標）。
// - 連鎖、反應（換人施放）前停頓 0.15 秒；施放者身上一次只播一個片段（後一段開始時截掉前一段的收尾）。
// - 一招（第一段，不含連鎖與反擊）從起手到命中最長 1.8 秒：超過時等比壓縮起手與加力，命中點之後不壓。
// - 位移類原語（衝刺、跳躍、傳送…）的身體姿勢在位移動畫上播（`moveClips`）；照卡上的順序決定在出招前或出招後。
import { asEvent, type BattleView, type EventBase, type Pos, type SkillCard } from "../api/types";
import { battleVariantKey, familyApplies, pickVariant, variantIndex, type ArcSpec, type AttackFamily } from "../render/attackVariants";
import { CAST_MODES, clipDef, openerFor, primitivePlay, type Anchor, type CastMode, type ClipId, type Opener, type WeaponClass } from "../render/skillClips";
import { DASH_ROUTES, fxLookOf, LEAP_ARCS, openerClip, openerSetOf, pickSkillVariant, primitiveClip, skillVariantKey, type SkillVariantPick } from "../render/skillVariants";
import { healStyleOf } from "../render/skillVariantPoses";
import { fbKindFor, type FbPart } from "../render/qAnimFB";
import { PERCH_MS, type CreatureAttackType, type OwnFrames, type PerchRow } from "../render/creaturePose";
import type { MoveAnim } from "./animation";
import { casterMoveOf, creatureActionOf } from "./creatureAction";
import { samePos } from "./geometry";
import { meleeWeaponRange } from "./glossary";
import { chebyshev, inferShape, shapeIdOf, type SegmentIndex, type ShapeId, type StepVfx, type VfxCards } from "./vfx";
import type { Motion } from "./walkAnim";

export { CAST_MODES };

/** 連鎖、反應前的停頓（毫秒）。 */
export const CHAIN_GAP_MS = 150;
/** 一招（第一段）從起手到命中的上限（毫秒，正常速度）。 */
export const SKILL_CAP_MS = 1800;
/** 壓縮起手時最多壓到原長的幾成。 */
export const MIN_SQUEEZE = 0.3;
/** 收勢（回到站好）的時間。 */
export const RECOVER_MS = 160;
/** 有蓄力、延遲（`timing`、`activation`）的技能起手加長的倍率。 */
export const CHARGED_WINDUP = 1.5;

// ---- 施放方式 -----------------------------------------------------------------

/**
 * 施放方式（需求 2.2 的表）：自身、周圍、環、己方範圍 → 自身；指定地格、方陣 → 地面；
 * 其他形狀照射程：1 → 近身接觸，2 以上 → 飛行物、遠程。
 */
export function castMode(shape: ShapeId, range: number): CastMode {
  if (shape === "self" || shape === "allies_in_radius" || shape === "ring") return "self";
  if (shape === "ground_tile" || shape === "square3") return "ground";
  return range <= 1 ? "melee" : "ranged";
}

// ---- 事件 → 原語 ---------------------------------------------------------------

/**
 * 事件 → 原語（需求 2.1 的對照；卡片沒有部件資料時用它推出原語的順序）。對不到的事件回傳 `null`
 * （照現在的特效播，不加身體動作）。`apply_status` 的增益／減益另由 `polarityOf` 判斷。
 */
export function eventPrimitive(e: EventBase): string | null {
  switch (e.type) {
    case "damage_dealt":
      return e.cause === "backlash" && e.target_id === e.source_id ? "self_damage_of_hit" : "damage";
    case "healed":
      return "heal";
    case "shield_gained":
      return "shield";
    case "unit_revived":
      return "revive";
    case "resource_restored":
      return "restore_resource";
    case "unit_dashed":
      return "dash";
    case "unit_charged":
      return "charge_through";
    case "status_removed":
      return STATUS_REMOVED[String(e.reason)] ?? null;
    case "status_applied":
      return e.status_id === "time_bomb" ? "delayed_damage" : e.status_id === "prone" ? "knock_prone" : "apply_status";
    case "unit_moved":
      switch (e.mode) {
        case "leap":
          return "leap";
        case "teleport":
          return "teleport";
        case "shadowstep":
          return "shadowstep";
        case "swap":
          return "swap";
        case "teleported":
          return "teleport_target";
        case "dash":
          return "dash";
        default:
          return null;
      }
    default:
      return lowerHalfPrimitive(e);
  }
}

const STATUS_REMOVED: Readonly<Partial<Record<string, string>>> = { cleansed: "cleanse", dispelled: "dispel", stolen: "steal_buff", consumed: "consume_status", revealed: "reveal" };

/** 一對一的事件 → 原語（6N-3 下半）。 */
const EVENT_PRIMITIVE: Readonly<Partial<Record<string, string>>> = {
  unit_summoned: "summon",
  zone_created: "zone",
  surface_blown: "blow_surface",
  object_created: "create_obstacle",
  object_toppled: "topple",
  wall_toppled: "topple",
  object_hurled: "hurl_object",
  trap_placed: "place_trap",
  rune_inscribed: "inscribe",
  form_entered: "enter_form",
  form_left: "leave_form",
  attack_intercepted: "intercept",
  damage_redirected: "redirect_damage",
  death_cheated: "cheat_death",
  trap_revealed: "reveal",
  skill_copied: "copy_skill",
  skill_granted: "grant_skill",
  ap_granted: "grant_ap",
  reactions_granted: "extra_reaction",
  ap_refunded: "refund_ap",
  gamble_rolled: "gamble",
  rule_change_triggered: "rule_change",
};

/**
 * 6N-3 下半的事件 → 原語。`skill_cooldown_changed` 不對（使用技能時本來就會設冷卻，分不出退還、重置；卡上有部件時照卡）。
 */
function lowerHalfPrimitive(e: EventBase): string | null {
  switch (e.type) {
    case "summon_expired":
      return e.reason === "sacrificed" ? "sacrifice_summon" : null;
    case "surface_changed":
      if (e.cause === "clear") return "clear_surface";
      return e.cause === "effect" && e.after !== "none" ? "create_surface" : null;
    case "terrain_changed": {
      const d = Number(e.height_after) - Number(e.height_before);
      return d > 0 ? "raise_terrain" : d < 0 ? "lower_terrain" : null;
    }
    case "object_destroyed":
      return e.cause === "effect" ? "destroy_object" : null;
    case "rune_removed":
      return e.reason === "detonated" ? "detonate_runes" : null;
    case "stacks_changed":
      return e.reason === "gained" ? "add_stack" : e.reason === "consumed" ? "consume_stack" : null;
    default:
      return EVENT_PRIMITIVE[e.type] ?? null;
  }
}

// ---- 段落 ---------------------------------------------------------------------

export interface SkillSegment {
  casterId: string;
  skillId: string | null;
  segment: SegmentIndex;
  basic: boolean;
  /** 複合技能的後段（`skill_followup`）。 */
  followup: boolean;
  /** 開這一段的事件的 `seq`（AU-3：音效的變體鍵和動畫相同）。 */
  seq: number;
  from: Pos;
  /** 原語（照卡上的順序）。 */
  primitives: string[];
  polarity: "buff" | "debuff";
  mode: CastMode;
  weapon: WeaponClass;
  opener: Opener;
  /** 有蓄力、延遲（起手加長）。 */
  charged: boolean;
  /** 這一段被撞倒（倒地狀態）的單位。 */
  felled: string[];
  /** 近身普攻挑到的攻擊變體（6N-6）；技能、遠程、沒有變體表的武器為 `null`。 */
  variant: VariantPick | null;
  /** 技能變體（6N-8：起手、原語、特效三層）；挑了攻擊變體的普攻為 `null`。 */
  skillVariant: SkillVariantPick | null;
  /** CB-2b：形狀（異形錐形招播吐息）。 */
  shape?: ShapeId;
  /** CB-2b：施放者這一段自己的位移（`creatureAction.casterMoveOf`）。 */
  casterMove?: "slide" | "warp" | null;
  /** CB-2b：施放者是異形（或頭目）時，這一段的動作類型與片段長度、出手格。 */
  creature?: CreatureStrike & { action: CreatureAttackType };
  /** CB-2c：這一段實際孵出幼體的格子（`unit_summoned` 的位置）。 */
  summonAt?: Pos;
  /** CB-3c：這一段技能本身的射程（`"weapon"` ＝ 跟武器；沒有或不知道 ＝ `null`）。 */
  skillRange?: number | "weapon" | null;
  /** CB-3c：施放者近戰武器的射程（不是近戰武器 ＝ `null`；不知道 ＝ `undefined`）。 */
  weaponRange?: number | null;
}

export type WeaponOf = (unitId: string) => WeaponClass;
/** 施放者的變體表列（6N-6，`attackVariants.attackFamilyOf`）；沒有變體表為 `null`。 */
export type AttackOf = (unitId: string) => AttackFamily | null;
/**
 * QK-5（QK-4 待決 2）：施放者是異形時，這一招播的異形攻擊片段的長度與出手格（0～1）；不是異形（或頭目）＝null。
 * 有值時出招那一列改成異形片段的長度，命中點＝片段的出手格（不再塞進人形出招的長度裡），蓄力那幾列不播（異形片段自己有蓄力）。
 */
export type StrikeOf = (unitId: string, action: CreatureAttackType) => CreatureStrike | null;

/** 異形攻擊片段的長度與出手格；`blink`：挑到的片段真的是閃現（CB-2b：身形沒有閃現片段時退回普攻，不算）。 */
export interface CreatureStrike {
  ms: number;
  hitAt: number;
  blink?: boolean;
  /** CB-2c：挑到的片段真的是產卵（蛋由拋物線飛到孵化格；身形沒有產卵片段時退回遠程，不算）。 */
  egg?: boolean;
  /** CB-2c：鳥（待機在地上）：攻擊前後要有起飛、落地過場（減少動態時由 `playbackPlan` 拿掉）。 */
  perch?: boolean;
  /** CB-3：這隻鳥已經在空中（上一步剛走完、沒有落地）：不播攻擊開頭的起飛（由 `playbackPlan` 標）。 */
  airborne?: boolean;
  /** CB-3：片段照自己的格數播（第二種近戰：格數與基本長度，12 格／秒；`qCreatureAnim.creatureOwnFrames`）；沒有＝量化成 12 格。 */
  frames?: OwnFrames;
}

/** 挑到的變體：哪一列、第幾個、蓄力與出招片段、弧光。 */
export interface VariantPick {
  family: AttackFamily;
  index: number;
  id: string;
  windup: ClipId;
  strike: ClipId;
  /** 弧光；遠程變體沒有（`null`）。 */
  arc: ArcSpec | null;
}

/** 沒給 `attackOf` 時由起手對照表的列推（劍、刀、斧錘都當「劍」；魔導劍、成對、槍、鐮、鞭、拳套、弓、弩、火槍各自一列；空手 ＝ 拳套）。 */
const CLASS_FAMILY: Readonly<Partial<Record<WeaponClass, AttackFamily>>> = {
  blade: "sword",
  arcane: "arcane",
  pair: "pair",
  spear: "spear",
  scythe: "scythe",
  whip: "whip",
  fist: "fist",
  bare: "fist",
  bow: "bow",
  crossbow: "crossbow",
  gun: "gun",
};

/** 普攻挑變體：鍵 ＝「戰鬥鍵:attack_rolled 的 seq:施放者:attack_<列>」（需求第 0 節第 3 點）。 */
export function variantFor(family: AttackFamily, battleKey: string, seq: number, casterId: string): VariantPick {
  const key = battleVariantKey(battleKey, seq, casterId, family);
  const v = pickVariant(family, key);
  return { family, index: variantIndex(family, key), id: v.id, windup: v.windup, strike: v.strike, arc: v.arc };
}

const seqOf = (e: EventBase): number => (typeof e.seq === "number" ? e.seq : 0);

function posOf(v: unknown): Pos | null {
  return typeof v === "object" && v !== null && "x" in v && "y" in v ? (v as Pos) : null;
}

interface RawSeg {
  casterId: string;
  skillId: string | null;
  segment: SegmentIndex;
  basic: boolean;
  followup: boolean;
  /** 開這一段的事件的 `seq`（挑變體用）。 */
  seq: number;
  from: Pos;
  target: Pos | null;
  tiles: Pos[];
  events: EventBase[];
}

/** 和 vfx.ts 的 `opensSegment`／`openSegment` 同一套切法（段落與特效的 `casts` 一一對應）。 */
function splitSegments(events: readonly Record<string, unknown>[], view: BattleView): RawSeg[] {
  const at = (id: unknown): Pos | null => (typeof id === "string" ? (view.units.find((u) => u.id === id)?.pos ?? null) : null);
  const out: RawSeg[] = [];
  let cur: RawSeg | null = null;
  for (const raw of events) {
    const e = asEvent(raw);
    if (e.type === "rune_removed" && e.reason === "detonated") {
      // 符文引爆不開新段（和 vfx.ts 相同），但留在這一段的事件裡（推出 `detonate_runes`）
      cur?.events.push(e);
      continue;
    }
    const opens = e.type === "skill_used" || e.type === "skill_followup" || (e.type === "attack_rolled" && (cur === null || cur.casterId !== String(e.attacker_id) || cur.basic));
    if (opens) {
      let seg: RawSeg | null = null;
      if (e.type === "skill_used" || e.type === "skill_followup") {
        const caster = String(e.unit_id);
        const from = e.type === "skill_followup" ? (posOf(e.origin) ?? at(caster)) : at(caster);
        const tiles = Array.isArray(e.tiles) ? e.tiles.map(posOf).filter((p): p is Pos => p !== null) : [];
        if (from !== null) seg = { casterId: caster, skillId: String(e.skill_id), segment: e.type === "skill_followup" ? 1 : 0, basic: false, followup: e.type === "skill_followup", seq: seqOf(e), from, target: null, tiles, events: [] };
      } else {
        const caster = String(e.attacker_id);
        const from = at(caster);
        const target = at(e.target_id);
        if (from !== null && target !== null) seg = { casterId: caster, skillId: null, segment: 0, basic: true, followup: false, seq: seqOf(e), from, target, tiles: [target], events: [] };
      }
      if (seg !== null) {
        out.push(seg);
        cur = seg;
      }
      continue;
    }
    cur?.events.push(e);
  }
  return out;
}

/** 卡上部件的原語順序：`icon.segments[n].effects`；沒有 icon 的舊資料第一段用 `effect_ids`；都沒有時由事件推。 */
export function primitivesOf(card: SkillCard | undefined, segment: SegmentIndex, events: readonly EventBase[], basic: boolean): string[] {
  if (basic) return ["damage"];
  const fromIcon = card?.icon?.segments?.[segment]?.effects?.map((e) => e.type);
  const fromCard = fromIcon ?? (segment === 0 ? card?.effect_ids : undefined);
  if (fromCard !== undefined && fromCard.length > 0) return [...fromCard];
  const out: string[] = [];
  for (const e of events) {
    const p = eventPrimitive(e);
    if (p !== null && !out.includes(p)) out.push(p);
  }
  return out;
}

/** 施加狀態是增益（目標和施放者同陣營）還是減益。 */
function polarityOf(seg: RawSeg, view: BattleView): "buff" | "debuff" {
  const team = (id: unknown) => view.units.find((u) => u.id === id)?.team;
  const applied = seg.events.find((e) => e.type === "status_applied" && e.source_id === seg.casterId);
  if (applied === undefined) return "debuff";
  return team(applied.target_id) === team(seg.casterId) ? "buff" : "debuff";
}

/** CB-3c：技能卡上這一段的射程（第一段跟武器的 `"weapon"`）；卡上沒有 → `null`（不用距離補）。 */
function cardRangeOf(card: SkillCard | undefined, segment: SegmentIndex): number | "weapon" | null {
  const r = card?.icon?.segments?.[segment]?.range ?? (segment === 0 ? card?.stats?.range : null);
  if (typeof r === "number") return r;
  return segment === 0 && card?.stats?.range_weapon === true ? "weapon" : null;
}

/** CB-3c：施放者（這一步開始前的畫面）近戰武器的射程；不在畫面上 → `undefined`。 */
function weaponRangeIn(view: BattleView, casterId: string): number | null | undefined {
  const u = view.units.find((x) => x.id === casterId);
  return u === undefined ? undefined : meleeWeaponRange(u.weapon_id);
}

function rangeOf(card: SkillCard | undefined, seg: RawSeg, to: Pos): number {
  const r = card?.icon?.segments?.[seg.segment]?.range ?? (seg.segment === 0 ? card?.stats?.range : null);
  return typeof r === "number" ? r : chebyshev(seg.from, to);
}

function describe(raw: RawSeg, to: Pos, view: BattleView, cards: VfxCards, weaponOf: WeaponOf, attackOf: AttackOf | undefined): SkillSegment {
  const card = raw.skillId === null ? undefined : cards[raw.skillId];
  const shape: ShapeId = raw.basic ? "single" : (shapeIdOf(card, raw.segment) ?? inferShape(raw.from, raw.tiles));
  const mode = raw.basic ? (chebyshev(raw.from, to) > 1 ? "ranged" : "melee") : castMode(shape, rangeOf(card, raw, to));
  const weapon = weaponOf(raw.casterId);
  const timing = card?.timing ?? null;
  const felled = raw.events.filter((e) => e.type === "status_applied" && e.status_id === "prone").map((e) => String(e.target_id));
  // 6N-6：近身普攻照變體表挑；6N-7：遠程的列（弓、弩、火槍）只在遠程普攻挑（技能的變體是 6N-8）
  const row = raw.basic ? (attackOf === undefined ? (CLASS_FAMILY[weapon] ?? null) : attackOf(raw.casterId)) : null;
  const family = row !== null && familyApplies(row, mode) ? row : null;
  const opener = openerFor(weapon, mode);
  // 6N-8：技能（與法器的遠程普攻）照「戰鬥鍵:seq:施放者:skill:技能 ID」挑三層的變體；挑了攻擊變體的普攻不另挑
  const set = openerSetOf(weapon, mode, raw.basic, opener.windup !== null);
  const skillVariant = family !== null || (raw.basic && set === null) ? null : pickSkillVariant(skillVariantKey(view.map_id ?? "", raw.seq, raw.casterId, raw.skillId), set);
  return {
    casterId: raw.casterId,
    skillId: raw.skillId,
    segment: raw.segment,
    basic: raw.basic,
    followup: raw.followup,
    seq: raw.seq,
    from: raw.from,
    primitives: primitivesOf(card, raw.segment, raw.events, raw.basic),
    polarity: polarityOf(raw, view),
    mode,
    weapon,
    opener,
    charged: timing === "delayed" || timing === "activation" || (card?.activation_id ?? null) !== null,
    felled: [...new Set(felled)].sort(),
    variant: family === null ? null : variantFor(family, view.map_id ?? "", raw.seq, raw.casterId),
    skillVariant,
    shape,
    casterMove: casterMoveOf(raw.casterId, raw.events),
    ...summonAtOf(raw),
    ...(raw.basic ? {} : { skillRange: cardRangeOf(card, raw.segment), weaponRange: weaponRangeIn(view, raw.casterId) }),
  };
}

/** CB-2c：這一段孵出幼體的格子（蛋的落點要對上它；引擎沒有孵出時沒有）。 */
function summonAtOf(raw: RawSeg): { summonAt?: Pos } {
  const e = raw.events.find((x) => x.type === "unit_summoned");
  const at = e === undefined ? null : posOf(e.pos);
  return at === null ? {} : { summonAt: at };
}

/** CB-2b：施放者是異形時，照美術 PM 的順序挑動作類型，帶上片段的長度與出手格；不是異形原樣回傳。 */
function withCreature(seg: SkillSegment, to: Pos, strikeOf: StrikeOf | undefined): SkillSegment {
  if (strikeOf === undefined) return seg;
  const dist = chebyshev(seg.from, to);
  const action = creatureActionOf({
    basic: seg.basic,
    skillId: seg.skillId,
    primitives: seg.primitives,
    shape: seg.shape ?? "single",
    strikeClip: bodyPlan(seg, true, 1).strike,
    dist,
    range: seg.skillRange ?? null,
    ...(seg.weaponRange === undefined ? {} : { weaponRange: seg.weaponRange }),
  });
  const cr = strikeOf(seg.casterId, action);
  return cr === null ? seg : { ...seg, creature: { ...cr, action } };
}

// ---- 時間軸 -------------------------------------------------------------------

export interface SkillRow {
  unitId: string;
  clip: ClipId;
  /** 收勢：從這個片段最後的姿勢回到站好（`clip` 仍填該片段）。 */
  recover: boolean;
  /** 沒有身體動作的片段（退還、層數類；6N-3）：不套姿勢、只播特效，和前一個片段同時開始。 */
  still: boolean;
  /** 共用片段的分辨圖示（`PrimitivePlay.icon`）。 */
  icon: string | null;
  startMs: number;
  ms: number;
  /** 命中點（相對這一步；沒有＝不命中）。 */
  hitMs: number | null;
  anchor: Anchor;
  /** 第幾段（對應 `vfx.casts`）。 */
  cast: number;
  /** 這一列是該段的出招（特效從它的作用端發出）。 */
  strike: boolean;
  /** 特效提示的目標位置與目標單位（目標片段為自己）。 */
  target: Pos | null;
  element: string;
  /** QK-5：蓄力、出招、收勢這三列（kind：朝南、朝北時改播 Q 版正面、背面五類出招；側面的雙手武器、弓接 Q 版關鍵姿勢 atk、bowAim）；沒有＝照片段。 */
  fb?: FbPart;
  /** QK-4b：異形出招片段自己的飛向目標特效也畫進貼圖（普攻沒有飛行物、射線時；`creaturePose.fxAll`）。 */
  ownFx?: boolean;
  /** CB-2b：異形出招的動作類型；`inPlace`：引擎已經位移過，片段不再整隻往前衝（不和 `dash` 疊加）。 */
  creature?: { action: CreatureAttackType; inPlace?: true; frames?: OwnFrames };
  /** CB-2c：出招列：蛋要拋到這一格，命中點（`hitMs`）就是落地、孵化的那一刻。 */
  eggTo?: Pos;
  /** CB-2c：鳥的起飛、落地過場列（`recover` 為真：不算蓄力、不放片段的特效提示）。 */
  perch?: PerchRow;
}

export interface SkillTimeline {
  rows: SkillRow[];
  /** 對齊後的特效（時間已依出招的命中點移動）。 */
  vfx: StepVfx;
  segments: SkillSegment[];
}

interface Laid {
  rows: SkillRow[];
  shift: number[];
}

/** 出招時「特效開始 → 對齊點」的時間：遠程（飛行物、光束、扇形）＝ 蓄力；其他 ＝ 蓄力＋到命中。 */
function alignOffset(c: StepVfx["casts"][number]): number {
  return c.kind === "projectile" || c.kind === "beam" || c.kind === "cone" ? c.chargeMs : c.impactMs - c.startMs;
}

interface PostClip {
  clip: ClipId;
  icon: string | null;
}

function bodyPlan(seg: SkillSegment, withWindup: boolean, squeeze: number): { pre: Array<{ clip: ClipId; ms: number; windup?: true }>; strike: ClipId; post: PostClip[] } {
  const pre: Array<{ clip: ClipId; ms: number; windup?: true }> = [];
  const sv = seg.skillVariant;
  // 6N-8：起手層的衍生片段和原本一樣長、命中點一樣（只有這一段有播蓄力時，出招才接衍生的第一格）
  const windup = seg.variant?.windup ?? (seg.opener.windup === null ? null : openerClip(seg.opener.windup, sv));
  if (withWindup && windup !== null) pre.push({ clip: windup, ms: clipDef(windup).ms * (seg.charged ? CHARGED_WINDUP : 1) * squeeze, windup: true });
  const post: PostClip[] = [];
  for (const p of seg.primitives) {
    const play = primitivePlay(p, seg.polarity);
    if (play === null || play.clip === null || play.role === "move") continue;
    const icon = play.icon ?? null;
    const prev = post[post.length - 1];
    if (play.role === "pre") pre.push({ clip: play.clip, ms: clipDef(play.clip).ms * squeeze });
    else if (prev === undefined || prev.clip !== play.clip || prev.icon !== icon) post.push({ clip: play.clip, icon });
  }
  const strike = seg.variant?.strike ?? (withWindup ? openerClip(seg.opener.strike, sv) : seg.opener.strike);
  // 原語層：召喚法陣、治療增益只換特效（片段長度照原本）
  const heal = (c: ClipId) => healStyleOf(clipDef(c));
  return { pre, strike, post: post.map((c) => ({ ...c, clip: primitiveClip(c.clip, sv, heal) })) };
}

/** CB-2b：這一段的閃現片段由傳送的位移動畫播（`placeMotions` 的 `creatureBlink`），出招那一列不再播，免得落地後在原地多閃一次。 */
const blinkInMove = (seg: SkillSegment): boolean => seg.creature?.blink === true && seg.casterMove === "warp";

function lay(segs: readonly SkillSegment[], vfx: StepVfx, squeeze: number): Laid {
  const rows: SkillRow[] = [];
  const shift: number[] = [];
  const busy = new Map<string, number>();
  let prevShift = 0;
  const seen = new Set<string>();
  for (let i = 0; i < segs.length; i++) {
    const seg = segs[i]!;
    const cast = vfx.casts[i]!;
    const first = !seen.has(seg.casterId);
    seen.add(seg.casterId);
    const plan0 = bodyPlan(seg, first && !seg.followup, i === 0 ? squeeze : 1);
    const cr = seg.creature === undefined ? null : blinkInMove(seg) ? { ms: 0, hitAt: 0.5 } : seg.creature;
    const plan = cr === null ? plan0 : { ...plan0, pre: [] };
    const strike = cr === null ? clipDef(plan.strike) : { ...clipDef(plan.strike), ms: cr.ms, hitAt: cr.hitAt };
    const preMs = plan.pre.reduce((s, p) => s + p.ms, 0);
    // CB-2c：鳥的起飛只在這隻第一次出招前（同一步連續幾段不重複起落），落地只在最後一段後
    const perches = seg.creature?.perch === true;
    const takeoffMs = perches && first && seg.creature?.airborne !== true ? PERCH_MS : 0;
    const hitRel = takeoffMs + preMs + strike.ms * (strike.hitAt ?? 0.5);
    const gap = i > 0 && (seg.followup || segs[i - 1]!.casterId !== seg.casterId) ? CHAIN_GAP_MS : 0;
    let start = cast.startMs + prevShift + gap;
    let body = start + alignOffset(cast) - hitRel;
    if (body < 0) {
      start -= body;
      body = 0;
    }
    const free = busy.get(seg.casterId) ?? 0;
    if (i > 0 && body < free) {
      start += free - body;
      body = free;
    }
    // 施放者一次只播一個片段：截掉前一段在這之後的收尾
    for (const r of rows) if (r.unitId === seg.casterId && !r.strike && !r.still && r.startMs + r.ms > body) r.ms = Math.max(0, body - r.startMs);
    const s = start - cast.startMs;
    shift.push(s);
    prevShift = s;
    const base = { unitId: seg.casterId, recover: false, still: false, icon: null, cast: i, target: cast.to, element: cast.element };
    const fbk = fbKindFor(seg.weapon, seg.mode);
    let t = body;
    if (takeoffMs > 0) {
      rows.push({ ...base, clip: plan.strike, recover: true, startMs: t, ms: takeoffMs, hitMs: null, anchor: strike.anchor, strike: false, perch: "up", creature: { action: seg.creature!.action } });
      t += takeoffMs;
    }
    for (const p of plan.pre) {
      rows.push({ ...base, clip: p.clip, startMs: t, ms: p.ms, hitMs: null, anchor: clipDef(p.clip).anchor, strike: false, ...(p.windup ? { fb: { kind: fbk, part: "windup" as const } } : {}) });
      t += p.ms;
    }
    // QK-4b：異形（頭目）的普攻沒有飛出去的特效（揮砍、爆開）時，片段自己的射線、飛行物照畫（晶塔普攻射線）
    const ownFx = cr !== null && seg.basic && cast.kind !== "projectile" && cast.kind !== "beam" && cast.kind !== "cone";
    const inPlace = seg.creature?.action === "charge" && seg.casterMove === "slide";
    const creature = seg.creature === undefined ? {} : { creature: { action: seg.creature.action, ...(inPlace ? { inPlace: true as const } : {}), ...(seg.creature.frames === undefined ? {} : { frames: seg.creature.frames }) } };
    const eggTo = seg.creature?.egg === true ? { eggTo: seg.summonAt ?? cast.to } : {};
    rows.push({ ...base, clip: plan.strike, startMs: t, ms: strike.ms, hitMs: t + strike.ms * (strike.hitAt ?? 0.5), anchor: strike.anchor, strike: true, fb: { kind: fbk, part: "strike" as const, hitAt: strike.hitAt ?? 0.5 }, ...(ownFx ? { ownFx: true } : {}), ...creature, ...eggTo });
    t += strike.ms;
    const strikeEnd = t;
    busy.set(seg.casterId, t);
    let last: ClipId = plan.strike;
    const impact = cast.impactMs + s;
    for (const c of plan.post) {
      const d = clipDef(c.clip);
      if (d.still === true) {
        // 沒有身體動作：不佔時間，只有頭上的圖示；6N-4（美術 PM 6N-3 驗收第 3 點）起對齊這一段的命中點出現
        rows.push({ ...base, clip: c.clip, still: true, icon: c.icon, startMs: impact, ms: d.ms, hitMs: null, anchor: d.anchor, strike: false });
        continue;
      }
      rows.push({ ...base, clip: c.clip, icon: c.icon, startMs: t, ms: d.ms, hitMs: d.hitAt === undefined ? null : t + d.ms * d.hitAt, anchor: d.anchor, strike: false });
      t += d.ms;
      last = c.clip;
    }
    const lands = perches && !segs.slice(i + 1).some((s) => s.casterId === seg.casterId);
    if (lands) rows.push({ ...base, clip: plan.strike, recover: true, startMs: strikeEnd, ms: PERCH_MS, hitMs: null, anchor: strike.anchor, strike: false, perch: "down", creature: { action: seg.creature!.action } });
    else rows.push({ ...base, clip: last, recover: true, startMs: t, ms: RECOVER_MS, hitMs: null, anchor: clipDef(last).anchor, strike: false, ...(last === plan.strike ? { fb: { kind: fbk, part: "recover" as const } } : {}) });
    for (const id of seg.felled) {
      const d = clipDef("knocked_down");
      rows.push({ unitId: id, clip: "knocked_down", recover: false, still: false, icon: null, startMs: impact, ms: d.ms, hitMs: impact, anchor: d.anchor, cast: i, strike: false, target: null, element: cast.element });
    }
  }
  return { rows: rows.filter((r) => r.ms > 0), shift };
}

function retime(vfx: StepVfx, shift: readonly number[], felled: ReadonlySet<string> = new Set()): StepVfx {
  const last = shift[shift.length - 1] ?? 0;
  const casts = vfx.casts.map((c, i) => ({ ...c, startMs: c.startMs + (shift[i] ?? last), impactMs: c.impactMs + (shift[i] ?? last) }));
  // 命中點（受擊、扣血）跟著自己那一段的命中點移：和哪一段的 `impactMs` 同一刻就用那一段的位移；都不是（放在最後的）用最後一段的
  const shiftAt = (atMs: number): number => {
    const i = vfx.casts.findIndex((c) => c.impactMs === atMs);
    return i >= 0 ? (shift[i] ?? last) : last;
  };
  const hits = vfx.hits.map((h) => ({ ...h, atMs: h.atMs + shiftAt(h.atMs) }));
  const blasts = vfx.blasts.map((b) => ({ ...b, atMs: b.atMs + last }));
  const leadMs = Math.max(vfx.leadMs + last, ...casts.map((c) => c.impactMs), ...hits.map((h) => h.atMs));
  // 6H-1b：扣血與爆炸（停頓分級、微震的時間點）照同一套規則移，停頓的起點才會和畫面的命中點同一刻
  const impacts = vfx.impacts === undefined ? {} : { impacts: vfx.impacts.map((m) => ({ ...m, atMs: m.atMs + shiftAt(m.atMs) })) };
  if (vfx.reactions === undefined) return { ...vfx, casts, hits, blasts, leadMs, ...impacts };
  // 6N-4：反應跟著自己那一段的命中點移；被撞倒的人（`knocked_down` 片段，自帶白閃）不另播受擊、格擋、閃避
  const reactions = vfx.reactions
    .filter((r) => r.kind === "down" || !felled.has(r.unitId))
    .map((r) => ({ ...r, atMs: r.atMs + (r.cast >= 0 ? (shift[r.cast] ?? last) : last) }));
  return { ...vfx, casts, hits, blasts, leadMs, reactions, ...impacts };
}

/**
 * 一步的技能時間軸（時間是正常速度；`scaleTimeline` 再乘播放速度）。沒有技能或一般攻擊、或段落和特效對不起來時回傳 `null`
 * （照舊只播特效）。`vfx` 是這一步原本的特效（`vfxFor`，未縮放）；`weaponOf` 給施放者的武器種類。
 */
export function skillTimeline(events: readonly Record<string, unknown>[], view: BattleView, cards: VfxCards, vfx: StepVfx, weaponOf: WeaponOf, attackOf?: AttackOf, strikeOf?: StrikeOf): SkillTimeline | null {
  const raws = splitSegments(events, view);
  if (raws.length === 0 || raws.length !== vfx.casts.length) return null;
  const segs = raws.map((r, i) => withCreature(describe(r, vfx.casts[i]!.to, view, cards, weaponOf, attackOf), vfx.casts[i]!.to, strikeOf));
  let laid = lay(segs, vfx, 1);
  const impact0 = vfx.casts[0]!.impactMs + (laid.shift[0] ?? 0);
  if (impact0 > SKILL_CAP_MS) {
    const plan = bodyPlan(segs[0]!, true, 1);
    const squeezable = plan.pre.reduce((s, p) => s + p.ms, 0);
    if (squeezable > 0) laid = lay(segs, vfx, Math.max(MIN_SQUEEZE, 1 - (impact0 - SKILL_CAP_MS) / squeezable));
  }
  return { rows: laid.rows, vfx: withArcs(retime(vfx, laid.shift, new Set(segs.flatMap((s) => s.felled))), segs), segments: segs };
}

/**
 * 6N-6：挑到變體的那一段，弧光照變體的方向畫（`VfxCast.arc`；其餘照舊由上往下）。
 * 6N-8：技能的每一段帶特效層的變體（`VfxCast.look`：飛行物軌跡、爆發形狀、粒子分布）；元素、格子、時間不動。
 * 法器的普攻只換起手（6N-7 待決 1 的保守做法），不帶特效層。
 */
function withArcs(vfx: StepVfx, segs: readonly SkillSegment[]): StepVfx {
  if (segs.every((s) => s.variant?.arc == null && (s.basic || s.skillVariant === null))) return vfx;
  return {
    ...vfx,
    casts: vfx.casts.map((c, i) => {
      const s = segs[i];
      const arc = s?.variant?.arc ?? null;
      const sv = s === undefined || s.basic ? null : s.skillVariant;
      return { ...c, ...(arc === null ? {} : { arc }), ...(sv === null ? {} : { look: fxLookOf(sv) }) };
    }),
  };
}

/** 依播放速度縮放時間軸（特效另用 `scaleVfx`）。 */
export function scaleRows(rows: readonly SkillRow[], scale: number): SkillRow[] {
  const s = (ms: number) => Math.round(ms * scale);
  return rows.map((r) => ({ ...r, startMs: s(r.startMs), ms: Math.max(1, s(r.ms)), hitMs: r.hitMs === null ? null : s(r.hitMs) }));
}

// ---- 位移的片段與前後 -----------------------------------------------------------

const MODE_PRIMITIVE: Readonly<Partial<Record<string, string>>> = { dash: "dash", leap: "leap", teleport: "teleport", shadowstep: "shadowstep", swap: "swap" };

/**
 * 位移動畫加上原語片段，並照卡上的順序分成「出招前」與「出招後」：施放者自己的位移照原語在卡上的位置
 * （排在第一個 `damage` 之後的放到出招後，例如「砍＋跳」）；被推、被拉、被傳送的人一律在出招後（被推、被拉播目標片段）。
 * 走路照舊在前面。
 */
export function placeMotions(motions: readonly Motion<MoveAnim>[], segs: readonly SkillSegment[], before: BattleView, scale = 1): { before: Motion<MoveAnim>[]; after: Motion<MoveAnim>[]; casterFrom: Pos | null } {
  const seg = segs[0];
  if (seg === undefined) return { before: [...motions], after: [], casterFrom: null };
  const caster = seg.casterId;
  const prims = seg.primitives;
  const strikeAt = prims.indexOf("damage");
  const casterPos = before.units.find((u) => u.id === caster)?.pos ?? seg.from;
  const out = { before: [] as Motion<MoveAnim>[], after: [] as Motion<MoveAnim>[], casterFrom: null as Pos | null };
  let swapAfter = false;
  for (const m of motions) {
    if (m.kind === "walk") {
      out.before.push(m);
      continue;
    }
    const a = m.anim;
    if (a.unitId === caster) {
      const prim = a.mode === "dash" && prims.includes("charge_through") ? "charge_through" : a.mode === "swap" && prims.includes("swap_any") ? "swap_any" : MODE_PRIMITIVE[a.mode];
      const play = prim === undefined ? null : primitivePlay(prim);
      const routed = play?.clip == null ? a : withRoute({ ...a, clip: play.clip }, seg.skillVariant);
      // CB-2b：閃現片段（淡出 → 換格 → 淡入）照片段的長度播在傳送上，換格落在片段完全透明的中段
      const anim = blinkInMove(seg) && a.style === "fade" ? { ...routed, creatureBlink: true as const, durationMs: Math.round(seg.creature!.ms * scale) } : routed;
      const idx = prim === undefined ? -1 : prims.indexOf(prim);
      const after = strikeAt >= 0 && idx > strikeAt;
      if (a.mode === "swap") swapAfter = after;
      if (after && out.casterFrom === null) out.casterFrom = a.from;
      (after ? out.after : out.before).push({ kind: "move", anim });
      continue;
    }
    if (a.mode === "forced") {
      const away = chebyshev(a.to, casterPos) > chebyshev(a.from, casterPos);
      out.after.push({ kind: "move", anim: { ...a, clip: away ? "pushed" : "pulled" } });
      continue;
    }
    if (a.mode === "swap") {
      (swapAfter ? out.after : out.before).push({ kind: "move", anim: { ...a, clip: "swap_pose" } });
      continue;
    }
    if (a.mode === "teleported") {
      out.after.push(m);
      continue;
    }
    out.before.push(m);
  }
  return out;
}

/** 6N-8 原語層：施放者自己的衝刺（`dash_lean`）帶路線、跳躍（`leap_air`）帶弧度；起訖格、長度不變。 */
function withRoute(a: MoveAnim, sv: SkillVariantPick | null | undefined): MoveAnim {
  if (sv == null) return a;
  if (a.clip === "dash_lean") return { ...a, route: DASH_ROUTES[sv.dash]!.id };
  if (a.clip === "leap_air") return { ...a, hop: LEAP_ARCS[sv.leap]!.id };
  return a;
}

/** 施放者在出招後才位移時，特效從位移前的格子發出（`vfx.ts` 以這一步結束的位置為準）。 */
export function castFromBefore(vfx: StepVfx, casterFrom: Pos | null, castFromPos: Pos | null): StepVfx {
  if (casterFrom === null || castFromPos === null) return vfx;
  const casts = vfx.casts.map((c) => (samePos(c.from, castFromPos) ? { ...c, from: casterFrom, path: c.path.map((p, i) => (i === 0 ? casterFrom : p)), ranged: chebyshev(casterFrom, c.to) > 1 } : c));
  return { ...vfx, casts };
}

