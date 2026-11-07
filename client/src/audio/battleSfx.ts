// 戰鬥音效掛上 6N 時間軸（AU-3；docs/art/音效與音樂方案.md 2.1）。純函式、確定性：只讀一步的事件、畫面與
// 已排好時間的特效／身體片段（`skillTimeline`、`withSpecials`、`withImpact` 之後），算出「什麼音效、在效果時鐘的哪一刻」。
// - 起手：起手片段開始（技能；遠程武器的拉弓、上膛普攻也有）。
// - 出招：揮砍、突刺、拳的「咻」在命中點前 60 ms；弓、弩、火槍在放出那一刻（出招片段的命中點）。
// - 命中、結果、原語、狀態、地表、爆炸：命中點（受擊反應的時間）。同一刻同一個音效合併成一聲（`count` 次數，引擎依次數略增音量）。
// - 變體鍵和動畫相同：出招用 `skillVariantKey`／`battleVariantKey`，受擊用 `reactVariantKey`（同一場重播聲音一樣）。
// 時間是效果時鐘（毫秒，相對這一步的 `playVfx`）；停頓、最後一擊放慢由 `cueRealMs` 換成實際時間，和畫面對齊。
import { asEvent, type BattleView, type EventBase } from "../api/types";
import type { MoveAnim } from "../battle/animation";
import { slowRealMs } from "../battle/impact";
import { BOSS_TAG } from "../battle/specials";
import type { SkillRow, SkillSegment } from "../battle/skillSequence";
import type { StepVfx, VfxReaction } from "../battle/vfx";
import type { WalkAnim, WalkBeat } from "../battle/walkAnim";
import { battleVariantKey } from "../render/attackVariants";
import { reactVariantKey } from "../render/reactClips";
import { baseClipOf, PRIMITIVE_CLIPS, type WeaponClass } from "../render/skillClips";
import { skillVariantKey } from "../render/skillVariants";
import { statusAnimKinds, type StatusAnimKind } from "../render/statusAnim";
import { standing } from "../battle/hiddenInfo";
import { stepKey, stepSoundFor } from "./footsteps";

export interface SfxCue {
  id: string;
  /** 效果時鐘上的時間（毫秒，相對這一步的特效開始；播放速度已縮放或未縮放跟著 `StepVfx`）。 */
  atMs: number;
  /** 變體鍵（和動畫同一把）。 */
  key: string;
  /** 同一刻同一個音效的次數（一次打 5 人＝5；只放一聲，音量依次數略增）。 */
  count: number;
}

/** 揮砍類的「咻」比命中點早多少（毫秒，正常速度；方案 2.1）。 */
export const SWING_LEAD_MS = 60;

// ---- 對照表 -----------------------------------------------------------------------

/** 命中的元素 → 音效（`vfxPalette.ts` 的鍵）。物理與土＝鈍擊；認不得的＝魔法命中。 */
const ELEMENT_HIT: Readonly<Record<string, string>> = {
  physical: "hit_blunt",
  earth: "hit_blunt",
  fire: "elem_fire",
  ice: "elem_ice",
  lightning: "elem_lightning",
  water: "elem_water",
  poison: "elem_poison",
  holy: "elem_holy",
  shadow: "elem_dark",
  wind: "elem_mist",
};

export function hitSfxOf(element: string): string {
  return ELEMENT_HIT[element] ?? "hit_magic";
}

/** 地表出現（`surface_changed` 的 `after`）→ 元素音效。 */
const SURFACE_SFX: Readonly<Record<string, string>> = {
  fire: "elem_fire",
  ice: "elem_ice",
  water: "elem_water",
  oil: "elem_water",
  poison: "elem_poison",
  holy: "elem_holy",
  darkness: "elem_dark",
  smoke: "elem_mist",
};

/** 狀態上身（`status_applied`）→ 音效。燃燒是全場一條的循環（`burnLoopOn`），這裡不放。 */
const STATUS_SFX: Readonly<Partial<Record<StatusAnimKind, string>>> = {
  frozen: "status_freeze",
  poison: "status_poison",
  stunned: "status_stun",
  charged: "status_shock",
};

/** 原語（卡上的部件順序）→ 音效；位移類在位移動畫上放（`moveCues`）。 */
const PRIMITIVE_SFX: Readonly<Record<string, string>> = {
  heal: "prim_heal",
  shield: "prim_shield",
  summon: "prim_summon",
  inscribe: "prim_rune_carve",
  enter_form: "prim_transform",
  place_trap: "prim_rune_carve",
};

const RANGED_WEAPONS: ReadonlySet<WeaponClass> = new Set(["bow", "crossbow", "gun"]);
const CASTER_WEAPONS: ReadonlySet<WeaponClass> = new Set(["staff", "orb", "bare"]);

/** 起手片段開始時的音效；`null`＝不出聲（近身普攻只有咻）。 */
export function windupSfx(seg: Pick<SkillSegment, "weapon" | "mode" | "basic">): string | null {
  const far = seg.mode === "ranged" || seg.mode === "ground";
  if (far && seg.weapon === "bow") return "windup_bow_draw";
  if (far && (seg.weapon === "crossbow" || seg.weapon === "gun")) return "windup_reload";
  if (seg.basic) return null;
  if (seg.weapon === "arcane" && seg.mode === "ranged") return "windup_sigil";
  if (seg.mode !== "melee" && (CASTER_WEAPONS.has(seg.weapon) || seg.weapon === "arcane")) return "windup_chant";
  return "windup_charge";
}

/** 出招的音效與時間：近身＝咻（命中點前 60 ms）；弓、弩、火槍＝放出那一刻；其他（法術放出）＝不出聲。 */
export function strikeSfx(seg: Pick<SkillSegment, "weapon" | "mode">): { id: string; lead: number } | null {
  if (seg.mode === "ranged" || seg.mode === "ground") {
    if (seg.weapon === "bow") return { id: "release_bow", lead: 0 };
    if (seg.weapon === "crossbow") return { id: "release_crossbow", lead: 0 };
    if (seg.weapon === "gun") return { id: "release_gun", lead: 0 };
    return null;
  }
  if (seg.mode !== "melee") return null;
  if (RANGED_WEAPONS.has(seg.weapon)) return { id: "swing_punch", lead: SWING_LEAD_MS }; // 弓托、槍托敲人
  if (seg.weapon === "spear") return { id: "swing_thrust", lead: SWING_LEAD_MS };
  if (seg.weapon === "fist" || seg.weapon === "bare") return { id: "swing_punch", lead: SWING_LEAD_MS };
  return { id: "swing_slash", lead: SWING_LEAD_MS };
}

// ---- 合併 -------------------------------------------------------------------------

class CueList {
  private readonly items: SfxCue[] = [];

  add(id: string | null, atMs: number, key: string): void {
    if (id === null) return;
    const at = Math.max(0, Math.round(atMs));
    const same = this.items.find((c) => c.id === id && c.atMs === at);
    if (same !== undefined) same.count += 1;
    else this.items.push({ id, atMs: at, key, count: 1 });
  }

  /** 依時間、再依 id 排序（確定性）。 */
  done(): SfxCue[] {
    return [...this.items].sort((a, b) => a.atMs - b.atMs || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  }
}

// ---- 一步的音效 -----------------------------------------------------------------------

export interface StepSfxInput {
  events: readonly Record<string, unknown>[];
  before: BattleView;
  after: BattleView;
  /** 這一步的特效（`withImpact` 之後；時間未縮放或已縮放都可以，輸出跟著它）；沒有特效為 `null`。 */
  vfx: StepVfx | null;
  /** 技能時間軸（`skillTimeline`）；沒有（舊呼叫端、不是技能）為 `null`。 */
  segments?: readonly SkillSegment[] | null;
  rows?: readonly SkillRow[] | null;
}

export interface StepSfx {
  /** 跟著特效（`playVfx` 那一刻起算）。 */
  vfx: SfxCue[];
  /** 這一步沒有特效、或和特效無關的事件（回合開始、Boss 預告…）：畫面更新那一刻。 */
  view: SfxCue[];
}

const isPrimitiveClip = (clip: string): boolean => baseClipOf(clip as never) in PRIMITIVE_CLIPS;

function segmentKey(battleKey: string, seg: SkillSegment): string {
  if (seg.skillVariant !== null) return seg.skillVariant.key;
  if (seg.variant !== null) return battleVariantKey(battleKey, seg.seq, seg.casterId, seg.variant.family);
  return skillVariantKey(battleKey, seg.seq, seg.casterId, seg.skillId);
}

function segmentCues(out: CueList, vfx: StepVfx, segs: readonly SkillSegment[], rows: readonly SkillRow[], battleKey: string): void {
  segs.forEach((seg, i) => {
    const key = segmentKey(battleKey, seg);
    const mine = rows.filter((r) => r.cast === i && r.unitId === seg.casterId);
    const strike = mine.find((r) => r.strike);
    const windup = strike === undefined ? undefined : mine.find((r) => !r.strike && !r.recover && !r.still && r.startMs < strike.startMs && !isPrimitiveClip(r.clip));
    if (windup !== undefined) out.add(windupSfx(seg), windup.startMs, key);
    const sw = strikeSfx(seg);
    if (strike !== undefined && strike.hitMs !== null && sw !== null) out.add(sw.id, strike.hitMs - sw.lead, key);
    const impact = vfx.casts[i]?.impactMs ?? vfx.leadMs;
    for (const p of seg.primitives) out.add(PRIMITIVE_SFX[p] ?? null, impact, key);
  });
}

/** 沒有技能時間軸時（舊呼叫端）：揮砍弧照舊在命中前咻一聲。 */
function castFallbackCues(out: CueList, vfx: StepVfx, battleKey: string): void {
  vfx.casts.forEach((c, i) => {
    if (c.kind === "slash") out.add("swing_slash", c.impactMs - SWING_LEAD_MS, `${battleKey}:cast:${i}`);
  });
}

const REACTION_SFX: Readonly<Partial<Record<VfxReaction["kind"], string>>> = { block: "res_block", dodge: "res_dodge", down: "res_down", rise: "res_revive" };

function reactionCues(out: CueList, vfx: StepVfx, battleKey: string): void {
  const reactions = vfx.reactions;
  if (reactions === undefined) {
    for (const h of vfx.hits) out.add(hitSfxOf(h.element), h.atMs, `${battleKey}:${h.pos.x},${h.pos.y}`);
    for (const s of vfx.specials ?? []) if (s.kind === "block" || s.kind === "dodge") out.add(s.kind === "block" ? "res_block" : "res_dodge", s.atMs, `${battleKey}:${s.unitId ?? ""}`);
    return;
  }
  for (const r of reactions) {
    const key = reactVariantKey(battleKey, r.seq, r.unitId, r.kind === "dodge" ? "dodge" : "hit");
    if (r.kind === "hit" || r.kind === "heavy" || r.kind === "down") {
      const hit = vfx.hits.find((h) => h.atMs === r.atMs && h.pos.x === r.pos.x && h.pos.y === r.pos.y);
      const element = hit?.element ?? vfx.casts[r.cast]?.element ?? "physical";
      out.add(hitSfxOf(element), r.atMs, key);
    }
    out.add(REACTION_SFX[r.kind] ?? null, r.atMs, key);
  }
}

function specialCues(out: CueList, vfx: StepVfx, battleKey: string): void {
  for (const s of vfx.specials ?? []) {
    const key = `${battleKey}:${s.unitId ?? ""}:${s.kind}`;
    if (s.kind === "crit") out.add("res_crit", s.atMs, key);
    else if (s.kind === "kill") out.add("res_kill", s.atMs, key);
    else if (s.kind === "boss") out.add("sys_boss_ult", s.atMs, key);
  }
  for (const m of vfx.impacts ?? []) if (m.kind === "boom") out.add("explosion", m.atMs, `${battleKey}:${m.seq}:boom`);
  for (const b of vfx.blasts) out.add("prim_rune_burst", b.atMs, `${battleKey}:${b.pos.x},${b.pos.y}:rune`);
}

/** 狀態、地表、回合等事件的音效；`at(e)` 給時間（有特效＝那個人的命中點，沒有＝0）。 */
function eventCues(out: CueList, events: readonly EventBase[], before: BattleView, battleKey: string, at: (e: EventBase) => number): void {
  const bossIds = new Set(before.units.filter((u) => (u.tags ?? []).includes(BOSS_TAG)).map((u) => u.id));
  for (const e of events) {
    const seq = typeof e.seq === "number" ? e.seq : 0;
    if (e.type === "status_applied" && typeof e.status_id === "string") {
      for (const k of statusAnimKinds([e.status_id], false)) out.add(STATUS_SFX[k] ?? null, at(e), `${battleKey}:${seq}:${String(e.target_id)}:status`);
    } else if (e.type === "surface_changed" && typeof e.after === "string" && e.after !== "none") {
      const id = e.cause === "effect" ? (SURFACE_SFX[e.after] ?? null) : e.after === "fire" ? "surface_fire_spread" : null;
      out.add(id, at(e), `${battleKey}:${seq}:surface`);
    } else if (e.type === "round_started") {
      out.add("sys_round_start", 0, `${battleKey}:round:${String(e.round)}`);
    } else if (e.type === "followup_charged" && typeof e.unit_id === "string" && bossIds.has(e.unit_id)) {
      out.add("sys_boss_warn", 0, `${battleKey}:${seq}:boss_warn`);
    }
  }
}

/** 這個事件在效果時鐘上的時間：目標（或施放者）的受擊反應時間，找不到時用命中點。 */
function eventTime(vfx: StepVfx): (e: EventBase) => number {
  return (e) => {
    const who = typeof e.target_id === "string" ? e.target_id : typeof e.unit_id === "string" ? e.unit_id : null;
    const r = who === null ? undefined : vfx.reactions?.find((x) => x.unitId === who);
    return r?.atMs ?? vfx.leadMs;
  };
}

/** 一步的音效（純函式）。同一刻同一個音效合併。 */
export function stepSfx(input: StepSfxInput): StepSfx {
  const battleKey = input.after.map_id ?? "";
  const events = input.events.map(asEvent);
  const view = new CueList();
  const vfxOut = new CueList();
  const vfx = input.vfx;
  if (vfx === null) {
    eventCues(view, events, input.before, battleKey, () => 0);
    return { vfx: [], view: view.done() };
  }
  const segs = input.segments ?? null;
  if (segs !== null && input.rows != null) segmentCues(vfxOut, vfx, segs, input.rows, battleKey);
  else castFallbackCues(vfxOut, vfx, battleKey);
  reactionCues(vfxOut, vfx, battleKey);
  specialCues(vfxOut, vfx, battleKey);
  // 回合開始、Boss 預告放在畫面更新時；狀態、地表跟著命中點
  const timed = events.filter((e) => e.type === "status_applied" || e.type === "surface_changed");
  eventCues(vfxOut, timed, input.before, battleKey, eventTime(vfx));
  eventCues(
    view,
    events.filter((e) => e.type === "round_started" || e.type === "followup_charged"),
    input.before,
    battleKey,
    () => 0,
  );
  return { vfx: vfxOut.done(), view: view.done() };
}

/** 依播放速度縮放（`scaleVfx` 的同一個倍率）。 */
export function scaleCues(cues: readonly SfxCue[], scale: number): SfxCue[] {
  return cues.map((c) => ({ ...c, atMs: Math.round(c.atMs * scale) }));
}

// ---- 效果時鐘 → 實際時間 ---------------------------------------------------------------

/**
 * 效果時鐘的 `atMs` 在正常倍速（沒按住加速）下是實際的第幾毫秒：命中前的停頓加進來、最後一擊放慢的範圍拉長。
 * 停頓在 `atMs` 那一刻本身不算（命中聲在停住的那一刻響）。減少動態時繪製器不停頓、不放慢，所以照原本。
 * 和 `render/hitStop.ts` 的 `advanceClock` 同一套規則。按住加速時再除以倍率（`CueScheduler`）。
 */
export function cueRealMs(atMs: number, vfx: Pick<StepVfx, "stops" | "slow"> | null, reduced: boolean): number {
  if (vfx === null || reduced) return atMs;
  const base = vfx.slow === undefined ? atMs : slowRealMs(vfx.slow, 0, atMs);
  let stops = 0;
  for (const s of vfx.stops ?? []) if (s.atMs < atMs) stops += s.ms;
  return base + stops;
}

// ---- 位移、走路 --------------------------------------------------------------------

/** 位移動畫的音效（衝刺＝風、跳躍＝落地悶響、傳送＝扭曲掃頻），時間相對這段位移開始。 */
export function moveCues(anim: Pick<MoveAnim, "mode" | "durationMs" | "unitId" | "to">, battleKey: string): SfxCue[] {
  const key = `${battleKey}:${anim.unitId}:${anim.to.x},${anim.to.y}:${anim.mode}`;
  switch (anim.mode) {
    case "dash":
      return [{ id: "prim_dash", atMs: 0, key, count: 1 }];
    case "leap":
      return [{ id: "prim_land", atMs: Math.max(0, Math.round(anim.durationMs)), key, count: 1 }];
    case "teleport":
    case "shadowstep":
    case "swap":
    case "teleported":
      return [{ id: "prim_teleport", atMs: 0, key, count: 1 }];
    default:
      return [];
  }
}

const BEAT_SFX: Readonly<Partial<Record<WalkBeat["beat"], string>>> = { stumble: "surface_slip", slip: "surface_slip", trap: "surface_trap", fire: "elem_fire", oil: "elem_water" };

/** 一格一格走的音效：每一格開始踏一步（依那一格的地表），地表停頓放滑倒、陷阱、冒火。時間相對走路開始。 */
export function walkCues(walk: WalkAnim, view: Pick<BattleView, "tiles" | "map_id" | "region">): SfxCue[] {
  const out = new CueList();
  const tile = (x: number, y: number) => view.tiles.find((t) => t.x === x && t.y === y) ?? null;
  const place = { region: view.region ?? null };
  let t = 0;
  let n = 0;
  for (const p of walk.pieces) {
    if (p.kind === "leg") {
      out.add(stepSoundFor(tile(p.to.x, p.to.y), place), t, `${stepKey(view.map_id, p.to.x, p.to.y, n)}:${walk.unitId}`);
      n += 1;
    } else if (p.kind === "beat") {
      out.add(BEAT_SFX[p.beat] ?? null, t, `${view.map_id}:${walk.unitId}:${p.pos.x},${p.pos.y}:${p.beat}`);
    }
    t += p.kind === "beat" ? p.holdMs : p.durationMs;
  }
  return out.done();
}

// ---- 燃燒循環 ---------------------------------------------------------------------------

/** 畫面上有沒有人在燃燒（倒下的不算）：全場只放一條劈啪循環。 */
export function burnLoopOn(view: Pick<BattleView, "units">): boolean {
  return view.units.some((u) => standing(u) && statusAnimKinds(u.statuses.map((s) => s.status_id), false).includes("burning"));
}
