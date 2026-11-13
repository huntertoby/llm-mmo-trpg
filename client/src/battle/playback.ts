// 逐步播放計畫（純函式）：回應的 `steps` → 一格一格的畫面。
// 每一步的順序固定為：標示行動中的單位 → 該步的移動動畫 → 技能特效（蓄力與飛行，等到命中）→
// 畫該步的 `view` → 地形升降動畫（3-19）→ 地圖回饋 → 加入該步的紀錄 → 停頓。
// 最後一定以 `res.view` 為準（播放只是過場）。
import type { BattleResponse, BattleView, StepOut } from "../api/types";
import { moveAnimOf, type MoveAnim } from "./animation";
import { heightShifts, LIFT_MS, type HeightShift } from "./elevation";
import { feedbackFor, immobilityOf, type FeedbackItem } from "./feedback";
import { logLines, type LogLine } from "./log";
import { unitNames } from "./units";
import { isEmptyVfx, scaleVfx, vfxFor, VFX_TIMING, type StepVfx, type VfxCards } from "./vfx";
import { asEvent } from "../api/types";
import { castFromBefore, placeMotions, scaleRows, skillTimeline, type AttackOf, type SkillRow, type SkillTimeline, type StrikeOf, type WeaponOf, type CreatureStrike } from "./skillSequence";
import { ENEMY_WALK_RATE, stepMotions, trackRunning, walkDurationMs, type Motion, type WalkAnim } from "./walkAnim";
import { withImpact } from "./impact";
import { victoryOf, VICTORY_HOLD_MS, VICTORY_MS, withSpecials, type Victory } from "./specials";
import type { AttackFamily } from "../render/attackVariants";
import type { CreatureAttackType } from "../render/creaturePose";
import type { WeaponClass } from "../render/skillClips";
import { scaleCues, stepSfx, type SfxCue } from "../audio/battleSfx";

export type PlaySpeed = "crawl" | "slow" | "normal" | "fast" | "skip";

/** 顯示順序：極慢、慢、正常、快、略過（「極慢」2026-10-23 使用者：「幫我搞個極慢的速度」）。 */
export const PLAY_SPEEDS: readonly PlaySpeed[] = ["crawl", "slow", "normal", "fast", "skip"];

/** 慢速的時間倍率（正常的 2 倍時間；動畫、地圖回饋與停頓都用它）。 */
export const SLOW_FACTOR = 2;
/** 極慢的時間倍率（正常的 5 倍時間）。 */
export const CRAWL_FACTOR = 5;

/**
 * 開發用的額外放慢（網址 `?anim=0.1` ＝ 再慢 10 倍；PM／agent 逐格截圖驗收動畫用）：回傳時間倍率，
 * 沒給或不合法時為 1。`anim` 夾在 0.01～1。
 */
export function devAnimFactor(search: string): number {
  const raw = new URLSearchParams(search).get("anim");
  const v = raw === null ? Number.NaN : Number(raw);
  if (!Number.isFinite(v) || v <= 0) return 1;
  return 1 / Math.min(1, Math.max(0.01, v));
}

const DEV_SLOW = devAnimFactor(typeof window === "undefined" ? "" : window.location.search);

/** 動畫時間的倍率：極慢 ＝ 5 倍；慢 ＝ 2 倍；快 ＝ 一半；略過不播動畫（再乘上開發用的 `?anim=`）。 */
export const SPEED_SCALE: Readonly<Record<PlaySpeed, number>> = {
  crawl: CRAWL_FACTOR * DEV_SLOW,
  slow: SLOW_FACTOR * DEV_SLOW,
  normal: DEV_SLOW,
  fast: 0.5 * DEV_SLOW,
  skip: 0,
};
/** 地圖回饋（浮動數字、連線）的基準時間（毫秒），乘上 `SPEED_SCALE`。 */
export const FEEDBACK_MS = 1000;

/** 每個 AI 動作之後的停頓（毫秒）。 */
export const AI_PAUSE_MS: Readonly<Record<PlaySpeed, number>> = { crawl: 500 * CRAWL_FACTOR * DEV_SLOW, slow: 500 * SLOW_FACTOR * DEV_SLOW, normal: 500 * DEV_SLOW, fast: 150 * DEV_SLOW, skip: 0 };
/** AI 純移動之後的停頓（動畫本身已佔時間）。 */
export const MOVE_PAUSE_MS: Readonly<Record<PlaySpeed, number>> = { crawl: 150 * CRAWL_FACTOR * DEV_SLOW, slow: 150 * SLOW_FACTOR * DEV_SLOW, normal: 150 * DEV_SLOW, fast: 0, skip: 0 };
/** 主角自己的動作之後的停頓（短）。 */
export const HERO_PAUSE_MS: Readonly<Record<PlaySpeed, number>> = { crawl: 150 * CRAWL_FACTOR * DEV_SLOW, slow: 150 * SLOW_FACTOR * DEV_SLOW, normal: 150 * DEV_SLOW, fast: 0, skip: 0 };

export interface Frame {
  /** 行動中的單位；開場那一步為 `null`。 */
  actorId: string | null;
  /** 依事件順序的移動：走路是逐格的時間軸（6A-4d），其他位移（推、衝鋒、傳送…）照舊一段一段。 */
  motions: Motion<MoveAnim>[];
  /** 地圖上的回饋項目（略過時為空）。 */
  feedback: FeedbackItem[];
  /** 回饋項目顯示的時間（毫秒，已依速度縮放）。 */
  feedbackMs: number;
  /** 技能特效（Phase 3-12；時間已依速度縮放）；沒有特效或略過時為 `null`。 */
  vfx: StepVfx | null;
  /** 命中後爆發與粒子的時間（毫秒，已依速度縮放）。 */
  vfxImpactMs: number;
  /** 技能的身體片段（6N-1；時間已依速度縮放，和 `vfx` 同一個時間原點）；沒有技能、沒給武器解析或略過時沒有。 */
  skill?: SkillRow[];
  /** 出招後才播的位移（6N-1：照卡上的順序，例如「砍＋跳」的跳；被推、被拉）。 */
  after?: Motion<MoveAnim>[];
  /** 這一步高度改變的格子（3-19 升降動畫；略過時為空）。 */
  lifts: HeightShift[];
  /** 升降動畫的時間（毫秒，已依速度縮放）。 */
  liftMs: number;
  view: BattleView;
  lines: LogLine[];
  pauseMs: number;
  /** 音效（AU-3）：跟著特效的（效果時鐘，已縮放，`playVfx` 那一刻起算）；略過時沒有。 */
  sfx?: SfxCue[];
  /** 音效（AU-3）：畫面更新那一刻放的（回合開始、Boss 預告；沒有特效的步驟的狀態、地表）。 */
  viewSfx?: SfxCue[];
  /** 我方勝利（6N-5）：全隊舉手或收刀、浮出「勝利」；`ms` 是等多久才結束（已縮放），`clipMs` 是片段長度。 */
  victory?: FrameVictory;
}

export interface FrameVictory extends Victory {
  ms: number;
  clipMs: number;
}

export interface PlaybackPlan {
  initialView: BattleView;
  frames: Frame[];
  finalView: BattleView;
}

export type PlayOp =
  | { op: "mark"; unitId: string | null }
  | { op: "move"; anim: MoveAnim }
  | { op: "walk"; walk: WalkAnim }
  | { op: "vfx"; vfx: StepVfx; impactMs: number; skill?: SkillRow[]; sfx?: SfxCue[] }
  | { op: "view"; view: BattleView; sfx?: SfxCue[] }
  | { op: "lift"; shifts: HeightShift[]; durationMs: number }
  | { op: "feedback"; items: FeedbackItem[]; durationMs: number }
  | { op: "log"; lines: LogLine[] }
  | { op: "victory"; victory: FrameVictory }
  | { op: "pause"; ms: number };

function pauseFor(stepType: string | undefined, actorId: string | null, heroId: string, speed: PlaySpeed): number {
  if (actorId === null || stepType === "end_turn") return 0;
  if (actorId === heroId) return HERO_PAUSE_MS[speed];
  // 純移動的步驟已有移動動畫的時間，停頓縮短（一個單位常有「移動、攻擊、移動」好幾步）。
  return stepType === "move" ? MOVE_PAUSE_MS[speed] : AI_PAUSE_MS[speed];
}

interface StepSkill {
  vfx: StepVfx | null;
  /** AU-3：這一步的音效（已縮放）。 */
  sfx: { vfx: SfxCue[]; view: SfxCue[] };
  skill?: SkillRow[];
  motions: Motion<MoveAnim>[];
  after?: Motion<MoveAnim>[];
}

/**
 * 施放者的武器類別、普攻變體表列（6R-F）：照這一步開始前的畫面（`before`）算的純函式，
 * 正式的播放器用 `viewGrip.ts` 的 `weaponClassInView`、`attackFamilyInView`。
 */
export type ViewWeaponOf = (unitId: string, before: BattleView) => WeaponClass;
export type ViewAttackOf = (unitId: string, before: BattleView) => AttackFamily | null;
/** QK-5：施放者是異形時，異形攻擊片段的長度與出手格（照 `before` 算；`viewGrip.creatureStrikeInView`）。 */
export type ViewStrikeOf = (unitId: string, before: BattleView, action: CreatureAttackType) => CreatureStrike | null;

/**
 * 技能串接（6N-1）：特效對齊出招的命中點、施放者的身體片段、位移照卡上的順序分到出招前後。
 * 沒給 `weaponOf`（舊呼叫端、測試）或這一步不是技能時，照舊只有特效。
 */
function stepSkill(step: StepOut, before: BattleView, cards: VfxCards, scale: number, motions: Motion<MoveAnim>[], viewWeapon: ViewWeaponOf | undefined, viewAttack: ViewAttackOf | undefined, heroId = "", viewStrike?: ViewStrikeOf, reduced = false, airborne = false): StepSkill {
  const raw = vfxFor(step.events, step.view, cards, immobilityOf(step.events, before)); // 6F-6：打的那一刻能不能動
  const sfxOf = (v: StepVfx | null, tl?: { segments: SkillTimeline["segments"]; rows: SkillRow[] } | null) => {
    const out = stepSfx({ events: step.events, before, after: step.view, vfx: v, segments: tl?.segments ?? null, rows: tl?.rows ?? null });
    return { vfx: scaleCues(out.vfx, scale), view: out.view };
  };
  if (isEmptyVfx(raw)) return { vfx: null, motions, sfx: sfxOf(null) };
  // 6N-5：特殊結果與停頓照排好的命中點（未縮放），再一起縮放
  // 6H-1：停頓分級、微震、最後一擊放慢（同樣未縮放）
  const special = (v: StepVfx) => withImpact(withSpecials(v, step.events, before, step.view), step.events, before, step.view, heroId);
  const weaponOf: WeaponOf | undefined = viewWeapon === undefined ? undefined : (id) => viewWeapon(id, before);
  const attackOf: AttackOf | undefined = viewAttack === undefined ? undefined : (id) => viewAttack(id, before);
  // CB-2c：減少動態時鳥不播起飛、落地過場（時間軸也不留位置）
  const strikeOf: StrikeOf | undefined =
    viewStrike === undefined
      ? undefined
      : (id, action) => {
          const s = viewStrike(id, before, action);
          if (s === null || s.perch !== true) return s;
          // CB-3：上一步剛走完還在空中的鳥，這一步的攻擊不再起飛
          if (!reduced) return airborne && id === step.actor_id ? { ...s, airborne: true } : s;
          const { perch: _perch, ...rest } = s;
          return rest;
        };
  const tl = weaponOf === undefined ? null : skillTimeline(step.events, step.view, cards, raw, weaponOf, attackOf, strikeOf, before);
  if (tl === null) {
    const v = special(raw);
    return { vfx: scaleVfx(v, scale), motions, sfx: sfxOf(v) };
  }
  const placed = placeMotions(motions, tl.segments, before, scale);
  const caster = tl.segments[0]?.casterId;
  const end = step.view.units.find((u) => u.id === caster)?.pos ?? null;
  const v = special(castFromBefore(tl.vfx, placed.casterFrom, end));
  return { vfx: scaleVfx(v, scale), skill: scaleRows(tl.rows, scale), motions: placed.before, after: placed.after, sfx: sfxOf(v, tl) };
}

/**
 * CB-3（美術 PM `docs/art/CB-2b檢查.md` 第 4 題）：上一格畫面是純走路（沒有技能特效）、最後一段是 `actor` 自己走完（最後一塊是走一格，不是滑倒、滑回），
 * 而且這隻是待機落地的鳥（`strikeOf` 的 `perch`）→ 回傳那一段走路；否則 null。這一步是不是真的接它的攻擊由呼叫端看排出來的列。
 */
function aloftLink(prev: Frame | undefined, step: StepOut, before: BattleView, strikeOf: ViewStrikeOf | undefined): WalkAnim | null {
  if (prev === undefined || strikeOf === undefined || step.actor_id === null || prev.vfx !== null || prev.actorId !== step.actor_id || prev.victory !== undefined) return null;
  const last = prev.motions[prev.motions.length - 1];
  if (last === undefined || last.kind !== "walk" || last.walk.unitId !== step.actor_id || last.walk.pieces[last.walk.pieces.length - 1]?.kind !== "leg") return null;
  return strikeOf(step.actor_id, before, "melee")?.perch === true ? last.walk : null;
}

/**
 * `cards`：技能 ID → 技能卡（推導技能特效的形狀用；缺的技能以影響的格子推斷）。
 * `running`（6M-3）：這個回合跑過的單位（呼叫端跨回應保留同一個集合，這裡依事件原地更新；跑過的人走路用跑步片段）。
 * `weaponOf`／`attackOf`（6R-F）：照每一步的 `before` 畫面算，不讀繪製器（見 `ViewWeaponOf`）。
 * `reduced`（CB-2c）：減少動態（呼叫端讀設定傳入）；鳥不播起飛、落地過場。
 */
export function playbackPlan(
  res: BattleResponse,
  heroId: string,
  speed: PlaySpeed,
  cards: VfxCards = {},
  running: Set<string> = new Set(),
  weaponOf?: ViewWeaponOf,
  attackOf?: ViewAttackOf,
  strikeOf?: ViewStrikeOf,
  reduced = false,
): PlaybackPlan {
  if (speed === "skip" || res.steps.length === 0) {
    for (const step of res.steps) for (const raw of step.events) trackRunning(running, asEvent(raw));
    const lines = logLines(res.steps, unitNames(res.view));
    const frames: Frame[] =
      res.steps.length === 0
        ? []
        : [{ actorId: null, motions: [], feedback: [], feedbackMs: 0, vfx: null, vfxImpactMs: 0, lifts: [], liftMs: 0, view: res.view, lines, pauseMs: 0 }];
    return { initialView: res.initial_view, frames, finalView: res.view };
  }
  const scale = SPEED_SCALE[speed];
  const feedbackMs = Math.round(FEEDBACK_MS * scale);
  const frames: Frame[] = [];
  res.steps.forEach((step, i) => {
    const before = i === 0 ? res.initial_view : (res.steps[i - 1] as StepOut).view;
    const walkRate = walkRateOf(step, before, heroId);
    const opts = { scale, walkRate, before, after: step.view, feedbackMs, running };
    const { motions: moved, consumed } = stepMotions(step.events, opts, (e) => moveAnimOf(e, scale));
    // CB-3：上一步是這隻鳥走路、這一步緊接它的攻擊 → 略過走路結尾的落地與攻擊開頭的起飛
    const prev = i === 0 ? undefined : frames[i - 1];
    const link = reduced ? null : aloftLink(prev, step, before, strikeOf);
    let sk = stepSkill(step, before, cards, scale, moved, weaponOf, attackOf, heroId, strikeOf, reduced, link !== null);
    if (link !== null && prev !== undefined) {
      const own = sk.skill?.filter((r) => r.unitId === step.actor_id) ?? [];
      if (sk.motions.length === 0 && own.some((r) => r.strike) && !own.some((r) => r.perch === "up")) prev.motions = [...prev.motions.slice(0, -1), { kind: "walk", walk: { ...link, aloft: true } }];
      else sk = stepSkill(step, before, cards, scale, moved, weaponOf, attackOf, heroId, strikeOf, reduced); // 接不起來：照舊落地再起飛
    }
    const won = victoryOf(step.events, step.view, heroId);
    frames.push({
      ...(won === null ? {} : { victory: { ...won, ms: Math.round(VICTORY_HOLD_MS * scale), clipMs: Math.max(160, Math.round(VICTORY_MS * scale)) } }),
      actorId: step.actor_id,
      motions: sk.motions,
      // 停頓時已在那一格跳過的數字與狀態，一步結束時不再跳一次
      feedback: feedbackFor(
        step.events.filter((_, k) => !consumed.has(k)),
        step.view,
        immobilityOf(step.events, before), // 6F-6：照打的那一刻判斷閃避／失手
      ),
      feedbackMs,
      vfx: sk.vfx,
      ...(sk.sfx.vfx.length === 0 ? {} : { sfx: sk.sfx.vfx }),
      ...(sk.sfx.view.length === 0 ? {} : { viewSfx: sk.sfx.view }),
      ...(sk.skill === undefined ? {} : { skill: sk.skill }),
      ...(sk.after === undefined || sk.after.length === 0 ? {} : { after: sk.after }),
      vfxImpactMs: Math.round(VFX_TIMING.impact * scale),
      lifts: heightShifts(step.events),
      liftMs: Math.round(LIFT_MS * scale),
      view: step.view,
      lines: logLines([step], unitNames(step.view)),
      pauseMs: pauseFor(step.step?.type, step.actor_id, heroId, speed),
    });
  });
  return { initialView: res.initial_view, frames, finalView: res.view };
}

/**
 * 走路的快轉倍率：敵方（和主角不同陣營）回合 2 倍速（戰鬥D版樣張第 4 節）；主角、友軍照常。
 * 只縮短走路，地表的停頓保留。
 */
export function walkRateOf(step: StepOut, before: BattleView, heroId: string): number {
  if (step.actor_id === null) return 1;
  const team = (id: string) => (step.view.units.find((u) => u.id === id) ?? before.units.find((u) => u.id === id))?.team;
  const heroTeam = team(heroId) ?? "ally";
  const actorTeam = team(step.actor_id);
  return actorTeam !== undefined && actorTeam !== heroTeam ? ENEMY_WALK_RATE : 1;
}

/** 一格畫面要依序做的事。 */
export function frameOps(frame: Frame): PlayOp[] {
  const ops: PlayOp[] = [{ op: "mark", unitId: frame.actorId }];
  const motion = (m: Motion<MoveAnim>): PlayOp => (m.kind === "walk" ? { op: "walk", walk: m.walk } : { op: "move", anim: m.anim });
  for (const m of frame.motions) ops.push(motion(m));
  if (frame.vfx !== null) ops.push({ op: "vfx", vfx: frame.vfx, impactMs: frame.vfxImpactMs, ...(frame.skill === undefined ? {} : { skill: frame.skill }), ...(frame.sfx === undefined ? {} : { sfx: frame.sfx }) });
  for (const m of frame.after ?? []) ops.push(motion(m));
  ops.push({ op: "view", view: frame.view, ...(frame.viewSfx === undefined ? {} : { sfx: frame.viewSfx }) });
  if (frame.lifts.length > 0) ops.push({ op: "lift", shifts: frame.lifts, durationMs: frame.liftMs });
  if (frame.feedback.length > 0) ops.push({ op: "feedback", items: frame.feedback, durationMs: frame.feedbackMs });
  if (frame.lines.length > 0) ops.push({ op: "log", lines: frame.lines });
  if (frame.victory !== undefined) ops.push({ op: "victory", victory: frame.victory });
  if (frame.pauseMs > 0) ops.push({ op: "pause", ms: frame.pauseMs });
  return ops;
}

/** 一個移動的總時間（毫秒）：走路 ＝ 逐格加停頓；其他位移 ＝ 該段時間。 */
export function motionMs(m: Motion<MoveAnim>): number {
  return m.kind === "walk" ? walkDurationMs(m.walk) : m.anim.durationMs;
}

/** 從第 `from` 格開始的所有紀錄（中途按「略過」時一次補上）。 */
export function remainingLines(plan: PlaybackPlan, from: number): LogLine[] {
  return plan.frames.slice(from).flatMap((f) => f.lines);
}
