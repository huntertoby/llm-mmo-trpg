// 打擊感（6H-1；需求 docs/archive/art/打擊感移植需求.md）：停頓依扣血比例分級、鏡頭微震只在三種情況、最後一擊放慢。
// 純函式：一步的事件 ＋ 已排好時間的特效描述（`vfxFor` → `withSpecials` 之後、`scaleVfx` 之前）→ 停頓、微震、放慢。
// 只讀事件與畫面資料（`before`／`after`），不改數值與規則；不用 Math.random、不讀時鐘；不跨步驟記憶
// （「一場只放慢一次」從 `before` 推：見 `finalBlowOf`），所以重播、觀戰、重新整理都一樣。「略過」時播放計畫沒有特效，也就都沒有。
import { asEvent, type BattleView, type EventBase, type Pos } from "../api/types";
import { variantHash } from "../render/attackVariants";
import { samePos } from "./geometry";
import { BOSS_TAG, specialStopMs, STEP_STOP_MAX_MS, STOP_MAX_MS, stopHoldMs, victoryOf } from "./specials";
import type { StepVfx, VfxImpact, VfxShake, VfxSlow, VfxStop } from "./vfx";

// ---- 停頓分級（需求第 2 節） ---------------------------------------------------------

/** 扣血比例的門檻（‰）：10%、25%、50%。 */
export const TIER_PERMILLE: readonly [number, number, number] = [100, 250, 500];
/** 各級的停頓（毫秒，正常速度）：0 級不停、1 輕 40、2 重擊 70、3（50% 以上或暴擊）100。 */
export const TIER_MS: readonly [number, number, number, number] = [0, 40, 70, 100];

export type ImpactTier = 0 | 1 | 2 | 3;

/** 一下的分級：比例（‰）＜ 100 → 0；100～249 → 1；250～499 → 2；≥ 500 或暴擊 → 3。 */
export function impactTier(lostPermille: number, crit: boolean): ImpactTier {
  if (crit || lostPermille >= TIER_PERMILLE[2]) return 3;
  if (lostPermille >= TIER_PERMILLE[1]) return 2;
  return lostPermille >= TIER_PERMILLE[0] ? 1 : 0;
}

/** 每個命中點的最高級（一下打多人時取最大）。 */
export function tiersAt(impacts: readonly VfxImpact[]): Map<number, ImpactTier> {
  const out = new Map<number, ImpactTier>();
  for (const m of impacts) {
    if (m.kind !== "hit") continue;
    const t = impactTier(m.lost, m.crit);
    if (t > (out.get(m.atMs) ?? 0)) out.set(m.atMs, t);
  }
  return out;
}

/**
 * 一步的停頓：同一刻只停一次，取「分級、特殊結果（擊殺 100、格擋 60，6N-5）、最後一擊（第 3 級）」裡最長的，
 * 每次不超過 `STOP_MAX_MS`；一步加起來不超過 `STEP_STOP_MAX_MS`（超過時後面的縮短，再後面的不停）。
 */
export function impactStops(vfx: StepVfx, slow: VfxSlow | null = null): VfxStop[] {
  const at = new Map<number, number>();
  const put = (atMs: number, ms: number) => {
    if (ms > 0) at.set(atMs, Math.max(at.get(atMs) ?? 0, Math.min(STOP_MAX_MS, ms)));
  };
  for (const [atMs, tier] of tiersAt(vfx.impacts ?? [])) put(atMs, TIER_MS[tier]);
  for (const s of vfx.specials ?? []) put(s.atMs, specialStopMs(s.kind));
  if (slow !== null) put(slow.atMs, TIER_MS[3]);
  const out: VfxStop[] = [];
  let left = STEP_STOP_MAX_MS;
  for (const atMs of [...at.keys()].sort((a, b) => a - b)) {
    const ms = Math.min(at.get(atMs) as number, left);
    if (ms <= 0) break;
    out.push({ atMs, ms });
    left -= ms;
  }
  return out;
}

// ---- 鏡頭微震（需求第 3 節） ---------------------------------------------------------

/** 三種微震的幅度（畫面像素）與長度（毫秒，正常速度）。 */
export const SHAKE_SPEC: Readonly<Record<VfxShake["kind"], { px: number; ms: number }>> = {
  heavy: { px: 2, ms: 120 },
  blast: { px: 3, ms: 160 },
  boss: { px: 4, ms: 220 },
};
/** 升地形的輕震（3-19；6H-1 降到 1 px）。 */
export const LIFT_SHAKE_PX = 1;
/** 左右、上下的頻率（Hz）。 */
export const SHAKE_HZ: readonly [number, number] = [28, 22];
/** 最後這一段（比例）線性收回 0。 */
export const SHAKE_TAIL = 0.3;

/** 相位（0～1）：照「戰鬥鍵:事件 seq」的雜湊。 */
export const shakePhase = (battleKey: string, seq: number): number => (variantHash(`${battleKey}:${seq}`) % 1000) / 1000;

function shake(kind: VfxShake["kind"], atMs: number, seq: number, battleKey: string, targets: Pos[]): VfxShake {
  const spec = SHAKE_SPEC[kind];
  return { kind, atMs, ms: spec.ms, baseMs: spec.ms, px: spec.px, phase: shakePhase(battleKey, seq), targets };
}

const uniqPos = (ps: readonly Pos[]): Pos[] => ps.filter((p, i) => ps.findIndex((q) => samePos(p, q)) === i);

/** Boss 大招的那一下：6N-5 的判斷（`specials` 的 `boss`），震在那一段的命中點。 */
function bossShakes(vfx: StepVfx, events: readonly EventBase[], battleKey: string): VfxShake[] {
  const s = (vfx.specials ?? []).find((x) => x.kind === "boss");
  if (s === undefined) return [];
  const cast = vfx.casts.find((c) => c.startMs === s.atMs && samePos(c.from, s.pos)) ?? vfx.casts.find((c) => c.startMs === s.atMs) ?? vfx.casts[0];
  const cue = events.find((e) => (e.type === "skill_used" || e.type === "skill_followup") && e.unit_id === s.unitId);
  return [shake("boss", cast?.impactMs ?? s.atMs, typeof cue?.seq === "number" ? cue.seq : 0, battleKey, [])];
}

/**
 * 頭目部位破了（PB-1c 占位演出，T16）：在那一刻加一次重擊的微震（`SHAKE_SPEC.heavy`）；那一刻已經有重擊微震時不重複。
 */
function partBreakShakes(vfx: StepVfx, events: readonly EventBase[], battleKey: string, already: readonly VfxShake[]): VfxShake[] {
  const out: VfxShake[] = [];
  for (const s of vfx.specials ?? []) {
    if (s.kind !== "part_break" || already.some((x) => x.kind === "heavy" && x.atMs === s.atMs) || out.some((x) => x.atMs === s.atMs)) continue;
    const cue = events.find((e) => e.type === "part_broken" && e.target_id === s.unitId);
    out.push(shake("heavy", s.atMs, typeof cue?.seq === "number" ? cue.seq : 0, battleKey, [s.pos]));
  }
  return out;
}

/**
 * 一步的微震（只有三種；其他命中一律不震；PB-1c 起頭目部位破壞也加一次重擊微震）：
 * - 重擊：停頓第 2、3 級的命中點（含暴擊、最後一擊）；
 * - 爆炸：`object_exploded`、`bomb_exploded`、符文引爆（`rune_removed` 的 `detonated`）；
 * - Boss 大招：6N-5 的判斷。
 * 同一種同一刻只一個；同時有好幾個時繪製器取最大的（`shakeOffset`），不疊加。
 */
export function shakesFor(vfx: StepVfx, events: readonly EventBase[], battleKey: string, slow: VfxSlow | null = null): VfxShake[] {
  const impacts = vfx.impacts ?? [];
  const out: VfxShake[] = [];
  const tiers = tiersAt(impacts);
  if (slow !== null && (tiers.get(slow.atMs) ?? 0) < 2) tiers.set(slow.atMs, 3);
  for (const atMs of [...tiers.keys()].sort((a, b) => a - b)) {
    if ((tiers.get(atMs) as number) < 2) continue;
    const heavy = impacts.filter((m) => m.kind === "hit" && m.atMs === atMs && impactTier(m.lost, m.crit) >= 2);
    const killed = slow !== null && slow.atMs === atMs ? impacts.filter((m) => m.kind === "hit" && m.atMs === atMs && m.unitId === slow.unitId) : [];
    const top = [...heavy, ...killed].sort((a, b) => b.lost - a.lost || a.seq - b.seq)[0];
    out.push(shake("heavy", atMs, top?.seq ?? 0, battleKey, uniqPos([...heavy, ...killed].map((m) => m.pos))));
  }
  const booms = impacts.filter((m) => m.kind === "boom");
  for (const atMs of [...new Set(booms.map((m) => m.atMs))].sort((a, b) => a - b)) {
    const here = booms.filter((m) => m.atMs === atMs);
    const hit = impacts.filter((m) => m.kind === "hit" && m.atMs === atMs).map((m) => m.pos);
    out.push(shake("blast", atMs, (here[0] as VfxImpact).seq, battleKey, uniqPos([...here.map((m) => m.pos), ...hit])));
  }
  out.push(...bossShakes(vfx, events, battleKey));
  out.push(...partBreakShakes(vfx, events, battleKey, out));
  return out.sort((a, b) => a.atMs - b.atMs || b.px - a.px);
}

/** 微震的包絡（0～1，`u` ＝ 這一震的進度 0～1）：前段由 1 衰減到 0.5，最後 30% 線性收回 0。 */
export function shakeEnvelope(u: number): number {
  if (u <= 0 || u >= 1) return u <= 0 ? 1 : 0;
  const head = 1 - SHAKE_TAIL;
  return u < head ? 1 - 0.5 * (u / head) : (0.5 * (1 - u)) / SHAKE_TAIL;
}

/**
 * 時間 `t`（和 `shakes` 同一個時間原點）的鏡頭位移（畫面像素）：在震的那幾個裡取目前幅度最大的一個（不疊加）。
 * 頻率照正常速度的長度算（`baseMs`），慢放時震得一樣慢；同輸入同輸出。
 */
export function shakeOffset(shakes: readonly VfxShake[], t: number): { x: number; y: number } {
  let best: { x: number; y: number; a: number } = { x: 0, y: 0, a: 0 };
  for (const s of shakes) {
    if (t < s.atMs || t >= s.atMs + s.ms || s.ms <= 0) continue;
    const u = (t - s.atMs) / s.ms;
    const a = s.px * shakeEnvelope(u);
    if (a <= best.a) continue;
    const sec = (u * s.baseMs) / 1000;
    const p = s.phase * Math.PI * 2;
    best = { x: a * Math.sin(2 * Math.PI * SHAKE_HZ[0] * sec + p), y: a * Math.sin(2 * Math.PI * SHAKE_HZ[1] * sec + p * 1.7), a };
  }
  return { x: best.x, y: best.y };
}

// ---- 最後一擊放慢（需求第 4 節） -----------------------------------------------------

/** 放慢的範圍（毫秒，正常速度）：命中點前 120、後 280；前後各 60 漸變；最慢 0.4 倍。 */
export const SLOW_BEFORE_MS = 120;
export const SLOW_AFTER_MS = 280;
export const SLOW_RAMP_MS = 60;
export const SLOW_RATE = 0.4;

const isBoss = (u: BattleView["units"][number] | undefined): boolean => (u?.tags ?? []).includes(BOSS_TAG);
const isDown = (u: BattleView["units"][number]): boolean => u.downed === true || (u.hp !== null && u.hp <= 0); // HID-1：看不到 HP（null）不算倒下

/** 這一步倒下的人（照事件順序，不重複）：`unit_downed`，或扣血扣到 0。 */
function downsOf(events: readonly EventBase[]): string[] {
  const out: string[] = [];
  for (const e of events) {
    const id = e.type === "unit_downed" ? e.unit_id : e.type === "damage_dealt" && e.hp_after === 0 && typeof e.amount === "number" && e.amount > 0 ? e.target_id : null;
    if (typeof id === "string" && !out.includes(id)) out.push(id);
  }
  return out;
}

/**
 * 最後一擊（無狀態）：這一步擊倒 Boss，或打倒敵方最後一個單位（這一步有我方勝利的 `battle_ended`）。
 * **一場只一次**：`before` 裡已經有倒下的 Boss（之前那一步已經放慢過）就不再放慢；沒有 Boss 的戰鬥只有勝利那一步。
 * 時間是倒下那個人的反應時間（那一段的命中點）。不是時 `null`。
 */
export function finalBlowOf(vfx: StepVfx, events: readonly EventBase[], before: BattleView, after: BattleView, heroId: string): VfxSlow | null {
  if (before.units.some((u) => isBoss(u) && isDown(u))) return null;
  const downs = downsOf(events);
  if (downs.length === 0) return null;
  const was = new Map(before.units.map((u) => [u.id, u]));
  const heroTeam = after.units.find((u) => u.id === heroId)?.team ?? before.units.find((u) => u.id === heroId)?.team ?? after.team;
  const boss = downs.find((id) => isBoss(was.get(id)) && !isDown(was.get(id) as BattleView["units"][number]));
  const won = victoryOf(events as unknown as Record<string, unknown>[], after, heroId) !== null;
  const last = won ? [...downs].reverse().find((id) => (was.get(id)?.team ?? null) !== heroTeam && was.get(id) !== undefined) : undefined;
  const unitId = boss ?? last;
  if (unitId === undefined) return null;
  const atMs = vfx.reactions?.find((r) => r.unitId === unitId)?.atMs ?? vfx.leadMs;
  return { atMs, fromMs: atMs - SLOW_BEFORE_MS, toMs: atMs + SLOW_AFTER_MS, rampMs: SLOW_RAMP_MS, rate: SLOW_RATE, reason: boss !== undefined ? "boss" : "last", unitId };
}

/** 一段放慢（時間單位隨意，只要一致）。 */
export type SlowSpan = Pick<VfxSlow, "fromMs" | "toMs" | "rampMs" | "rate">;

/** 效果時鐘在 `c` 的倍速：範圍外 1；前後 `rampMs` 由 1 線性變到 `rate`；中間 `rate`。 */
export function slowRate(c: number, s: SlowSpan): number {
  if (c <= s.fromMs || c >= s.toMs) return 1;
  const ramp = Math.max(0, Math.min(s.rampMs, (s.toMs - s.fromMs) / 2));
  if (ramp > 0 && c < s.fromMs + ramp) return 1 + (s.rate - 1) * ((c - s.fromMs) / ramp);
  if (ramp > 0 && c > s.toMs - ramp) return 1 + (s.rate - 1) * ((s.toMs - c) / ramp);
  return s.rate;
}

/** 線性倍速 `r0`→`r1`（在 `p0`～`p1`）下，效果時鐘從 `x0` 走到 `x1` 要花的實際時間。 */
function rampReal(p0: number, p1: number, r0: number, r1: number, x0: number, x1: number): number {
  if (x1 <= x0) return 0;
  if (r1 === r0) return (x1 - x0) / r0;
  const r = (x: number) => r0 + ((r1 - r0) * (x - p0)) / (p1 - p0);
  return ((p1 - p0) / (r1 - r0)) * Math.log(r(x1) / r(x0));
}

/** 效果時鐘從 `a` 走到 `b`（`a ≤ b`）要花的實際時間（放慢範圍內變長；範圍外照原本）。 */
export function slowRealMs(s: SlowSpan, a: number, b: number): number {
  if (b <= a) return 0;
  const ramp = Math.max(0, Math.min(s.rampMs, (s.toMs - s.fromMs) / 2));
  const pieces: Array<[number, number, number, number]> = [
    [Number.NEGATIVE_INFINITY, s.fromMs, 1, 1],
    [s.fromMs, s.fromMs + ramp, 1, s.rate],
    [s.fromMs + ramp, s.toMs - ramp, s.rate, s.rate],
    [s.toMs - ramp, s.toMs, s.rate, 1],
    [s.toMs, Number.POSITIVE_INFINITY, 1, 1],
  ];
  let sum = 0;
  for (const [p0, p1, r0, r1] of pieces) {
    const x0 = Math.max(a, p0);
    const x1 = Math.min(b, p1);
    if (x1 > x0) sum += Number.isFinite(p0) && Number.isFinite(p1) ? rampReal(p0, p1, r0, r1, x0, x1) : (x1 - x0) / r0;
  }
  return sum;
}

/** 整段放慢多出來的實際時間（正常速度約 0.48 秒）。 */
export const slowExtraMs = (s: SlowSpan): number => slowRealMs(s, s.fromMs, s.toMs) - (s.toMs - s.fromMs);

/** 播放等命中時要多等的時間（放慢在命中點以前的部分）。 */
export function slowHoldMs(vfx: StepVfx): number {
  const s = vfx.slow;
  if (s === undefined || vfx.leadMs <= 0) return 0;
  return Math.max(0, Math.round(slowRealMs(s, 0, vfx.leadMs) - vfx.leadMs));
}

/**
 * 播放等命中時要多等的時間（停頓 ＋ 命中點以前的放慢；6N-5、6H-1）。減少動態時繪製器不停頓、不放慢，所以是 0。
 */
export function hitHoldMs(vfx: StepVfx, reduced: boolean): number {
  return reduced ? 0 : stopHoldMs(vfx) + slowHoldMs(vfx);
}

/** 命中點之後還要放慢多久（實際時間；勝利片段等它播完再開始）。 */
export function slowTailMs(vfx: StepVfx): number {
  const s = vfx.slow;
  if (s === undefined || s.toMs <= vfx.leadMs) return 0;
  return Math.round(slowRealMs(s, Math.max(0, vfx.leadMs), s.toMs));
}

// ---- 放進特效描述 ------------------------------------------------------------------

/**
 * 把停頓分級、微震、最後一擊放慢放進特效描述（`withSpecials` 之後、`scaleVfx` 之前；時間未縮放）。
 * `heroId` 是主角（我方陣營照主角那一隊）。
 */
export function withImpact(vfx: StepVfx, rawEvents: readonly Record<string, unknown>[], before: BattleView, after: BattleView, heroId: string): StepVfx {
  const events = rawEvents.map(asEvent);
  const slow = finalBlowOf(vfx, events, before, after, heroId);
  const stops = impactStops(vfx, slow);
  const shakes = shakesFor(vfx, events, after.map_id ?? "", slow);
  const { stops: _old, ...rest } = vfx;
  return { ...rest, ...(stops.length === 0 ? {} : { stops }), ...(shakes.length === 0 ? {} : { shakes }), ...(slow === null ? {} : { slow }) };
}
