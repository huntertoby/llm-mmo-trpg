// 特殊結果的強化（Phase 6N-5；需求 docs/art/動畫移植需求第二批.md 第 5 節，方案 docs/art/動畫方案.md 2.9 選項 B）。
// 純函式：一步的事件 ＋ 已排好時間的特效描述 → 哪些結果要強化、命中時停頓多久。只讀事件與畫面資料，不改數值和規則。
// - 暴擊（`damage_dealt.crit`）：停頓約 0.1 秒、震動、弧光變金色加粗、數字放大寫「暴擊」、畫面閃白一下；
// - 擊殺（`hp_after == 0` 或 `unit_downed`）：暴擊的停頓加震動；**同一輪只強化一次**；
// - 格擋成功（`block_permille < 1000`）：停頓 0.06 秒、大火花、「格擋」字樣、攻擊者被彈開半步；
// - 閃避成功（`attack_rolled.hit == false`）：殘影多一層、「閃避」字樣；
// - Boss 大招（帶 `boss` 標籤、蓄力中的單位放出蓄力的那一招）：畫面四周變暗 0.3 秒。
// - 頭目部位破了（PB-1c 占位演出，T16；`part_broken`）：該頭目一次重擊白閃（那一下的受擊升級成重擊片段）＋微震（`impact.ts`
//   重擊的參數）（PB-1c 的浮動字「{部位} 破！」在 PB-1f 拿掉了）。不新增貼圖、不動 `render/battle/unitLayer.ts`；正式演出在 PB-1e。
// 不做慢動作和鏡頭拉近。「略過」時播放計畫沒有特效，也就沒有停頓。
import { asEvent, isPartBroken, type BattleView, type EventBase, type Pos } from "../api/types";
import { CHARGING } from "./followup";
import { samePos } from "./geometry";
import { standing } from "./hiddenInfo";
import { upgradeReact, type SpecialKind, type StepVfx, type VfxReaction, type VfxSpecial, type VfxStop } from "./vfx";

/** 每種結果命中時的停頓（毫秒，正常速度；乘播放速度）。閃避、Boss 大招不停頓。 */
export const STOP_MS: Readonly<Record<Exclude<SpecialKind, "part_break">, number>> = { crit: 100, kill: 100, block: 60, dodge: 0, boss: 0 };
/** 頭目部位破了的停頓（PB-1c 占位演出：照重擊＝`impact.ts` 第 2 級的 70）。 */
export const PART_BREAK_STOP_MS = 70;
/** 一種特殊結果的停頓（毫秒，正常速度）。 */
export const specialStopMs = (kind: SpecialKind): number => (kind === "part_break" ? PART_BREAK_STOP_MS : STOP_MS[kind]);
/** 一次停頓的上限（正常速度；需求：多次暴擊每次不超過 0.1 秒）。同一刻有暴擊又有擊殺也只停一次。 */
export const STOP_MAX_MS = 100;
/** 一步裡所有停頓加起來的上限（正常速度；多段技能每段都暴擊時不明顯拖長）。 */
export const STEP_STOP_MAX_MS = 200;
/** Boss 大招：畫面四周變暗的時間（毫秒，正常速度）。 */
export const BOSS_DIM_MS = 300;
/** Boss 的單位標籤（引擎 `ids.BOSS_TAG`）。 */
export const BOSS_TAG = "boss";

const roundOf = (e: EventBase, view: BattleView): number => (typeof e.round === "number" ? e.round : view.round);

/** 暴擊：每個暴擊的命中（同一刻同一格只算一次）。 */
function crits(vfx: StepVfx, unitAt: (p: Pos) => string | null): VfxSpecial[] {
  const out: VfxSpecial[] = [];
  for (const h of vfx.hits) {
    if (!h.crit || out.some((x) => x.atMs === h.atMs && samePos(x.pos, h.pos))) continue;
    out.push({ kind: "crit", pos: h.pos, unitId: unitAt(h.pos), atMs: h.atMs });
  }
  return out;
}

/**
 * 擊殺（6R-F 起無狀態）：只看這一步的事件與 `before` 的輪數，每一輪取「這一輪第一個倒下的人」
 * （命中點最早；同一刻照事件順序）強化一次。輪數用事件的 `round`，沒有時用 `before.round`。
 * 不再跨步驟記憶，所以略過、重新整理、觀戰時結果都一樣；同一輪分在不同步驟的擊殺各自強化（見 6R-F 報告待決）。
 */
function kill(vfx: StepVfx, events: readonly EventBase[], before: BattleView, after: BattleView): VfxSpecial[] {
  const reactions = vfx.reactions ?? [];
  const pos = new Map(after.units.map((u) => [u.id, u.pos]));
  const first = new Map<number, VfxSpecial>();
  for (const e of events) {
    const id = e.type === "unit_downed" ? e.unit_id : e.type === "damage_dealt" && e.hp_after === 0 && typeof e.amount === "number" && e.amount > 0 ? e.target_id : null;
    if (typeof id !== "string") continue;
    const p = pos.get(id);
    if (p === undefined) continue;
    const r = reactions.find((x) => x.unitId === id);
    const atMs = r?.atMs ?? vfx.leadMs;
    const round = roundOf(e, before);
    const best = first.get(round);
    if (best === undefined || atMs < best.atMs) first.set(round, { kind: "kill", pos: p, unitId: id, atMs });
  }
  return [...first.keys()].sort((a, b) => a - b).map((k) => first.get(k) as VfxSpecial);
}

/** 格擋成功（帶被彈開的攻擊者）、閃避成功：照 6N-4 的反應（同一段同一人只有一個）。 */
function guards(vfx: StepVfx, events: readonly EventBase[]): VfxSpecial[] {
  const out: VfxSpecial[] = [];
  for (const r of vfx.reactions ?? []) {
    if (r.kind === "dodge") out.push({ kind: "dodge", pos: r.pos, unitId: r.unitId, atMs: r.atMs });
    if (r.kind !== "block") continue;
    const hit = events.find((e) => e.type === "damage_dealt" && e.target_id === r.unitId && typeof e.block_permille === "number" && e.block_permille < 1000);
    const attacker = typeof hit?.source_id === "string" && hit.source_id !== r.unitId ? hit.source_id : undefined;
    out.push({ kind: "block", pos: r.pos, unitId: r.unitId, atMs: r.atMs, ...(attacker === undefined ? {} : { attackerId: attacker }) });
  }
  return out;
}

/** Boss 大招：出招的人在這一步開始前帶 `boss` 標籤、正在蓄力，這一步放出技能（延遲段的第二段或技能本身）。 */
function boss(vfx: StepVfx, events: readonly EventBase[], before: BattleView): VfxSpecial[] {
  for (const e of events) {
    if (e.type !== "skill_followup" && e.type !== "skill_used") continue;
    const u = before.units.find((x) => x.id === e.unit_id);
    if (u === undefined || !(u.tags ?? []).includes(BOSS_TAG) || !(u.statuses ?? []).some((s) => s.status_id === CHARGING)) continue;
    const cast = vfx.casts.find((c) => samePos(c.from, u.pos)) ?? vfx.casts[0];
    return [{ kind: "boss", pos: u.pos, unitId: u.id, atMs: cast?.startMs ?? 0 }];
  }
  return [];
}

/**
 * 頭目部位破了（PB-1c）：在那個頭目的受擊時間點（沒有受擊時用命中點、再沒有用 `leadMs`）；同一步同一隻同一刻只一次。
 * 停頓照重擊（`PART_BREAK_STOP_MS` ＝ 70，`impact.ts` 的第 2 級）。
 */
function partBreaks(vfx: StepVfx, events: readonly EventBase[], before: BattleView, after: BattleView): VfxSpecial[] {
  const out: VfxSpecial[] = [];
  for (const e of events) {
    if (!isPartBroken(e)) continue;
    const u = after.units.find((x) => x.id === e.target_id) ?? before.units.find((x) => x.id === e.target_id);
    if (u === undefined) continue;
    const r = (vfx.reactions ?? []).find((x) => x.unitId === u.id);
    const hit = vfx.hits.find((h) => samePos(h.pos, u.pos));
    const atMs = r?.atMs ?? hit?.atMs ?? vfx.leadMs;
    if (out.some((s) => s.unitId === u.id && s.atMs === atMs)) continue;
    const partId = typeof e.part_id === "string" ? e.part_id : undefined;
    out.push({ kind: "part_break", pos: u.pos, unitId: u.id, atMs, ...(partId === undefined ? {} : { partId }) });
  }
  return out;
}

/** 部位破壞的那一下：頭目的受擊升級成重擊片段（重擊白閃；倒下、格擋照舊不降級）。 */
function heavierReactions(reactions: readonly VfxReaction[] | undefined, breaks: readonly VfxSpecial[]): VfxReaction[] | undefined {
  if (reactions === undefined || breaks.length === 0) return reactions === undefined ? undefined : [...reactions];
  return reactions.map((r) => {
    if (!breaks.some((b) => b.unitId === r.unitId && b.atMs === r.atMs)) return r;
    const up = { ...r };
    upgradeReact(up, { kind: "heavy", seq: r.seq, ...(r.variant === undefined ? {} : { variant: r.variant }) });
    return up;
  });
}

/**
 * 一步的特殊結果（時間沿用 `vfx` 已排好的命中點；`vfx` 未縮放或已縮放都可以，時間單位跟著它）。
 * `before`／`after` 是這一步開始前、結束時的畫面（6R-F 起不跨步驟記憶）。
 */
export function specialsFor(vfx: StepVfx, events: readonly Record<string, unknown>[], before: BattleView, after: BattleView): VfxSpecial[] {
  const evs = events.map(asEvent);
  const unitAt = (p: Pos) => after.units.find((u) => samePos(u.pos, p) && !u.downed)?.id ?? after.units.find((u) => samePos(u.pos, p))?.id ?? null;
  const all = [...boss(vfx, evs, before), ...crits(vfx, unitAt), ...kill(vfx, evs, before, after), ...guards(vfx, evs), ...partBreaks(vfx, evs, before, after)];
  return all.sort((a, b) => a.atMs - b.atMs);
}

/**
 * 特殊結果 → 停頓：同一刻只停一次（取最長、不超過 `STOP_MAX_MS`），一步加起來不超過 `STEP_STOP_MAX_MS`。
 * 時間是正常速度的毫秒（`scaleVfx` 再乘播放速度）。
 */
export function stopsOf(specials: readonly VfxSpecial[]): VfxStop[] {
  const at = new Map<number, number>();
  for (const s of specials) {
    const ms = Math.min(STOP_MAX_MS, specialStopMs(s.kind));
    if (ms > 0) at.set(s.atMs, Math.max(at.get(s.atMs) ?? 0, ms));
  }
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

/** 把特殊結果與停頓放進特效描述（未縮放的時間；之後 `scaleVfx` 一起縮放）。 */
export function withSpecials(vfx: StepVfx, events: readonly Record<string, unknown>[], before: BattleView, after: BattleView): StepVfx {
  const specials = specialsFor(vfx, events, before, after);
  if (specials.length === 0) return vfx;
  const stops = stopsOf(specials);
  const breaks = specials.filter((s) => s.kind === "part_break");
  const reactions = breaks.length === 0 ? undefined : heavierReactions(vfx.reactions, breaks);
  return { ...vfx, specials, ...(stops.length === 0 ? {} : { stops }), ...(reactions === undefined ? {} : { reactions }) };
}

/** 命中點（含）以前的停頓加起來（播放等命中時要多等這麼久，畫面才在停頓結束後以結果重畫）。 */
export function stopHoldMs(vfx: StepVfx): number {
  return (vfx.stops ?? []).reduce((sum, s) => (s.atMs <= vfx.leadMs ? sum + s.ms : sum), 0);
}

/** 有沒有這種強化。 */
export function hasSpecial(vfx: StepVfx, kind: SpecialKind): boolean {
  return (vfx.specials ?? []).some((s) => s.kind === kind);
}

// ---- 勝利（6N-4 需求表的最後一列，6N-5 補做） ------------------------------------------

/** 勝利片段的長度（毫秒，正常速度；全隊舉手或收刀）。 */
export const VICTORY_MS = 520;
/** 「勝利」字樣浮出的時間（毫秒，正常速度）；播放等這麼久才顯示結束面板。 */
export const VICTORY_HOLD_MS = 1000;

export interface Victory {
  /** 站著的我方（主角那一隊）單位，照畫面資料的順序。 */
  unitIds: string[];
  /** `battle_ended` 的 `seq`（挑「舉手／收刀」的雜湊用）。 */
  seq: number;
  /** 戰鬥鍵（同 6N-4 的閃避：畫面資料的 `map_id`）。 */
  battleKey: string;
}

/** 這一步的 `battle_ended` 是主角那一隊贏：全隊播勝利片段；不是時 `null`。 */
export function victoryOf(events: readonly Record<string, unknown>[], view: BattleView, heroId: string): Victory | null {
  const team = view.units.find((u) => u.id === heroId)?.team ?? view.team;
  for (const raw of events) {
    const e = asEvent(raw);
    if (e.type !== "battle_ended" || e.winner !== team) continue;
    const unitIds = view.units.filter((u) => u.team === team && standing(u)).map((u) => u.id);
    return { unitIds, seq: typeof e.seq === "number" ? e.seq : 0, battleKey: view.map_id ?? "" };
  }
  return null;
}
