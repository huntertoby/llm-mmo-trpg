// 一格一格走的動畫（Phase 6A-4d，純函式）：一步的事件 → 每個單位的走路時間軸。
// 規則一律以引擎事件為準：走路的每一格是一個 `unit_moved`（`mode: walk`），兩格之間的
// `surface_entered`／`check_rolled`／`trap_triggered` 等事件就是「在那一格發生的事」，這裡只把它們
// 排成畫面上的停頓與效果，不自己判斷規則。
// 參考：`docs/design/05-戰鬥.md` 5.10、`docs/art/戰鬥D版樣張.md` 第 4 節。
import { asEvent, isUnitMoved, type BattleView, type EventBase, type Facing, type Pos, type UnitMovedEvent } from "../api/types";
import { feedbackFor, type FeedbackItem } from "./feedback";
import { samePos } from "./geometry";

/** 每走一格的時間（毫秒，正常速度）。 */
export const TILE_STEP_MS = 120;
/** 敵方回合走路的快轉倍率（只縮短走路，地表的停頓保留）。 */
export const ENEMY_WALK_RATE = 2;
/** 倒地後滑回最近空格的時間（倒在友軍格時；正常速度）。 */
export const SLIDE_BACK_MS = 200;

/** 在那一格發生的地表效果。 */
export type BeatKind = "ice" | "slip" | "trap" | "fire" | "oil";

/** 每種效果在那一格停頓的時間（毫秒，正常速度；冰面檢定通過時照常走過去，不停）。 */
export const BEAT_HOLD_MS: Readonly<Record<BeatKind, number>> = {
  ice: 0,
  slip: 450,
  trap: 400,
  fire: 250,
  oil: 200,
};

/** 腳下效果（冰花、夾子、火、油花）本身播多久（毫秒，正常速度；不擋住走路）。 */
export const BEAT_FX_MS: Readonly<Record<BeatKind, number>> = {
  ice: 450,
  slip: 600,
  trap: 600,
  fire: 600,
  oil: 500,
};

export interface WalkLeg {
  kind: "leg";
  from: Pos;
  to: Pos;
  /** 走這一格時面向的方向（轉彎時轉身）。 */
  facing: Facing;
  durationMs: number;
}

export interface WalkBeat {
  kind: "beat";
  beat: BeatKind;
  pos: Pos;
  /** 停頓時間（已依播放速度縮放；敵方快轉不縮短）。 */
  holdMs: number;
  /** 腳下效果的時間（已縮放）。 */
  fxMs: number;
  /** 停頓結束時在那一格跳出的傷害數字、狀態圖示（位置已改成那一格）。 */
  feedback: FeedbackItem[];
  feedbackMs: number;
}

export interface WalkSlide {
  kind: "slide";
  from: Pos;
  to: Pos;
  durationMs: number;
}

export type WalkPiece = WalkLeg | WalkBeat | WalkSlide;

export interface WalkAnim {
  unitId: string;
  pieces: WalkPiece[];
}

/** 緩入緩出（二次）：0 → 0、1 → 1，兩端速度為 0。 */
export function easeInOut(t: number): number {
  const k = Math.max(0, Math.min(1, t));
  return k < 0.5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2;
}

/** 這一格的走向 → 面向。原地（不該發生）時沿用 `fallback`。 */
export function facingOf(from: Pos, to: Pos, fallback: Facing): Facing {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  if (Math.abs(dx) >= Math.abs(dy) && dx !== 0) return dx > 0 ? "east" : "west";
  if (dy !== 0) return dy > 0 ? "south" : "north";
  return fallback;
}

/** 走路途中某一格的時間軸項目（測試與鏡頭用）。 */
export interface TimelineEntry {
  kind: WalkPiece["kind"];
  startMs: number;
  endMs: number;
}

export function walkTimeline(walk: WalkAnim): TimelineEntry[] {
  let t = 0;
  return walk.pieces.map((p) => {
    const ms = p.kind === "beat" ? p.holdMs : p.durationMs;
    const entry = { kind: p.kind, startMs: t, endMs: t + ms };
    t += ms;
    return entry;
  });
}

export function walkDurationMs(walk: WalkAnim): number {
  return walkTimeline(walk).at(-1)?.endMs ?? 0;
}

/** 停頓期間可以算進那一格的事件（陷阱效果的傷害、狀態等）；遇到其他事件（藉機攻擊、反應…）就不再收。 */
const BEAT_FOLLOWERS: ReadonlySet<string> = new Set([
  "damage_dealt",
  "shield_absorbed",
  "status_applied",
  "status_save_rolled",
  "status_resisted",
  "unit_downed",
]);

interface WalkOptions {
  /** 播放速度的時間倍率（正常 1）。 */
  scale: number;
  /** 走路的快轉倍率（敵方回合 2；地表停頓不受影響）。 */
  walkRate: number;
  /** 這一步開始前的畫面（看那一格原本的表面，例如油沒有自己的事件）。 */
  before: BattleView;
  /** 這一步結束後的畫面（回饋的位置）。 */
  after: BattleView;
  /** 回饋項目的顯示時間（已縮放）。 */
  feedbackMs: number;
}

/** 一步的移動：`walks` 依事件順序；`other` 是非走路的位移（照舊的 `MoveAnim`）在事件中的位置。 */
export type Motion<M> = { kind: "walk"; walk: WalkAnim } | { kind: "move"; anim: M };

export interface StepMotions<M> {
  motions: Motion<M>[];
  /** 已經在停頓時播過回饋的事件索引（一步結束的回饋要排除，避免重複跳數字）。 */
  consumed: Set<number>;
}

function surfaceAt(view: BattleView, p: Pos): string {
  return view.tiles.find((t) => t.x === p.x && t.y === p.y)?.surface ?? "none";
}

function beatFromEvent(e: EventBase, unitId: string): BeatKind | null {
  if (e.type === "trap_triggered" && e.unit_id === unitId) return "trap";
  if (e.type === "check_rolled" && e.unit_id === unitId && e.success === false) return "slip";
  if (e.type === "surface_entered" && e.unit_id === unitId) {
    if (e.surface === "ice") return "ice";
    if (e.surface === "fire") return "fire";
    if (e.surface === "oil") return "oil";
  }
  return null;
}

/** 同一格有多個效果時，留最重要的那一個（陷阱 > 滑倒 > 火 > 油 > 冰）。 */
const BEAT_RANK: Readonly<Record<BeatKind, number>> = { trap: 5, slip: 4, fire: 3, oil: 2, ice: 1 };

interface OpenBeat {
  kind: BeatKind;
  pos: Pos;
  events: number[];
  /** 還能不能收後續的傷害、狀態事件。 */
  open: boolean;
}

class WalkBuilder {
  readonly pieces: WalkPiece[] = [];
  private beat: OpenBeat | null = null;
  private facing: Facing;
  last: Pos;
  slipped = false;

  constructor(
    readonly unitId: string,
    start: Pos,
    facing: Facing,
    private readonly opts: WalkOptions,
    private readonly events: readonly EventBase[],
    private readonly consumed: Set<number>,
  ) {
    this.last = start;
    this.facing = facing;
  }

  leg(from: Pos, to: Pos): void {
    this.closeBeat();
    this.facing = facingOf(from, to, this.facing);
    const ms = Math.round((TILE_STEP_MS * this.opts.scale) / this.opts.walkRate);
    this.pieces.push({ kind: "leg", from, to, facing: this.facing, durationMs: ms });
    this.last = to;
    // 油沒有自己的事件：走進的那一格原本是油就濺油（只看畫面，不影響規則）
    if (surfaceAt(this.opts.before, to) === "oil") this.mark("oil", -1);
  }

  slide(from: Pos, to: Pos): void {
    this.closeBeat();
    this.pieces.push({ kind: "slide", from, to, durationMs: Math.round(SLIDE_BACK_MS * this.opts.scale) });
    this.last = to;
  }

  /** 一個事件；回傳是否屬於這次走路。 */
  take(e: EventBase, index: number): boolean {
    const kind = beatFromEvent(e, this.unitId);
    if (kind !== null) {
      this.mark(kind, index);
      if (kind === "slip") this.slipped = true;
      return true;
    }
    if (e.type === "check_rolled" && e.unit_id === this.unitId) {
      this.beat?.events.push(index); // 檢定通過：照常走過去
      return true;
    }
    if (this.beat !== null && this.beat.open && BEAT_FOLLOWERS.has(e.type)) {
      this.beat.events.push(index);
      return true;
    }
    if (this.beat !== null) this.beat.open = false;
    return false;
  }

  private mark(kind: BeatKind, index: number): void {
    if (this.beat === null || !samePos(this.beat.pos, this.last)) {
      this.closeBeat();
      this.beat = { kind, pos: this.last, events: [], open: true };
    } else if (BEAT_RANK[kind] > BEAT_RANK[this.beat.kind]) {
      this.beat.kind = kind;
    }
    if (index >= 0) this.beat.events.push(index);
  }

  closeBeat(): void {
    const b = this.beat;
    if (b === null) return;
    this.beat = null;
    const picked = b.events.map((i) => this.events[i] as EventBase);
    for (const i of b.events) this.consumed.add(i);
    this.pieces.push({
      kind: "beat",
      beat: b.kind,
      pos: b.pos,
      holdMs: Math.round(BEAT_HOLD_MS[b.kind] * this.opts.scale),
      fxMs: Math.round(BEAT_FX_MS[b.kind] * this.opts.scale),
      feedback: feedbackFor(picked, placeUnit(this.opts.after, this.unitId, b.pos)),
      feedbackMs: this.opts.feedbackMs,
    });
  }
}

/** 回饋要跳在停頓的那一格：把走路的人暫時放到那一格。 */
function placeUnit(view: BattleView, unitId: string, pos: Pos): BattleView {
  return { ...view, units: view.units.map((u) => (u.id === unitId ? { ...u, pos } : u)) };
}

function facingIn(view: BattleView, unitId: string): Facing {
  return view.units.find((u) => u.id === unitId)?.facing ?? "south";
}

/**
 * 一步的事件 → 依序的移動：連續的 `walk` 合成一段走路（每格一段、地表效果插入停頓），
 * 緊接在滑倒之後同一人的 `teleport`（倒在友軍格滑回最近空格）改成短短的滑行；其餘位移交給 `toMove`。
 */
export function stepMotions<M>(
  rawEvents: readonly Record<string, unknown>[],
  opts: WalkOptions,
  toMove: (e: UnitMovedEvent) => M,
): StepMotions<M> {
  const events = rawEvents.map(asEvent);
  const consumed = new Set<number>();
  const motions: Motion<M>[] = [];
  let walk: WalkBuilder | null = null;
  const flush = () => {
    if (walk === null) return;
    walk.closeBeat();
    motions.push({ kind: "walk", walk: { unitId: walk.unitId, pieces: walk.pieces } });
    walk = null;
  };
  events.forEach((e, i) => {
    const cur: WalkBuilder | null = walk;
    if (!isUnitMoved(e)) {
      // 不屬於走路的事件（藉機攻擊、反應…）不收；走路還沒結束，下一格照常接著走
      cur?.take(e, i);
      return;
    }
    const continues = cur !== null && cur.unitId === e.unit_id && samePos(cur.last, e.from_pos);
    if (e.mode === "walk") {
      let w = continues ? cur : null;
      if (w === null) {
        flush();
        w = new WalkBuilder(e.unit_id, e.from_pos, facingIn(opts.before, e.unit_id), opts, events, consumed);
        walk = w;
      }
      w.leg(e.from_pos, e.to_pos);
      return;
    }
    if (e.mode === "teleport" && continues && cur.slipped) {
      cur.slide(e.from_pos, e.to_pos);
      return;
    }
    flush();
    motions.push({ kind: "move", anim: toMove(e) });
  });
  flush();
  return { motions, consumed };
}

// ---- 畫面用的小算式（畫布 `render/BattleRenderer.ts` 用；放這裡好測試） -----------------------------

/** 倒地時身體轉的角度（弧度）：往面向的反方向倒（腳往前一溜、往後倒）。 */
export const SLIP_ANGLE = 1.35;

/**
 * 滑倒的姿勢（`t` 0～1）：前 35% 腳往前溜 `slide` 像素，接著 35% 以腳底為軸往後倒，最後躺著。
 * 回傳相對格子中心的位移與旋轉；`feet` 是腳底相對格子中心的 y（旋轉軸）。
 */
export function slipPose(t: number, facing: Facing, feet: number, slide = 6): { x: number; y: number; rotation: number } {
  const k = Math.max(0, Math.min(1, t));
  const dir = facing === "west" ? -1 : 1; // 往東（或南北）走時往左後方倒
  const dx = facing === "north" || facing === "south" ? 0 : dir;
  const dy = facing === "south" ? 1 : facing === "north" ? -1 : 0;
  const s = easeInOut(Math.min(1, k / 0.35));
  const fall = easeInOut(Math.max(0, Math.min(1, (k - 0.35) / 0.35)));
  const rotation = -dir * SLIP_ANGLE * fall;
  // 以腳底 (0, feet) 為軸：旋轉後腳底留在原處（再加上往前溜的距離）
  return {
    x: dx * slide * s + feet * Math.sin(rotation),
    y: dy * slide * 0.5 * s + feet - feet * Math.cos(rotation),
    rotation,
  };
}

/** 鏡頭跟隨的上限（像素）與比例：只是「稍微」跟著，不捲動整張圖。 */
export const CAMERA_MAX_PX = 10;
export const CAMERA_FOLLOW = 0.08;

/**
 * 移動中鏡頭的偏移（加在戰場圖層上）：把走路的人往畫面中央帶一點，夾在 ±`CAMERA_MAX_PX`。
 * `unit` 是單位在戰場上的像素位置，`size` 是戰場的像素大小。暗角是畫布外的 DOM，不跟著動。
 */
export function cameraNudge(unit: { x: number; y: number }, size: { width: number; height: number }): { x: number; y: number } {
  const clamp = (v: number) => Math.max(-CAMERA_MAX_PX, Math.min(CAMERA_MAX_PX, v)) + 0; // +0：不要 -0
  return { x: clamp(-(unit.x - size.width / 2) * CAMERA_FOLLOW), y: clamp(-(unit.y - size.height / 2) * CAMERA_FOLLOW) };
}
