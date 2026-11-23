// 前端先走（WM-1 第 2 項）：方向鍵走路時，主角先照前端的「能不能走」（`canStep`）開始滑，請求在背景
// 照順序送（同時只有一個在路上）。遭遇、迷霧、位置照舊由伺服器判定，前端只是先演：
// - 最多領先伺服器 `lead_max` 格；看得到敵人時（伺服器依觀看者過濾過的 `field.enemies` 有人）最多
//   `lead_max_enemy_seen` 格。兩個數字在 `walkAhead.config.json`。
// - 伺服器回應和前端預測一樣：照舊套用整份畫面（主角畫在畫面上站的格子，`shown`），NPC、敵群走一格照播。
// - 對不上（遇敵、位置不同、換了地圖、請求失敗）：停止送剩下的格子，主角用滑的拉回伺服器給的格子，
//   再套用伺服器的畫面，方向鍵全部放開（要再按才走）。
// - 出口、門、傳送石不先走：等前面的格子都確認了，照舊流程（`portal`）送、等回應、播換地圖。
// 守則 14：只用畫面上本來就有的資料（地形的 `walkable`、高低差、出口、看得到的敵人），不另外要伺服器的資料。
import type { FieldView, Pos, WorldView } from "../api/types";
import config from "./walkAhead.config.json";
import { canStep, portalCells, type Direction } from "./fieldModel";
import { isDevMode } from "../run/startFlow";

export interface WalkAheadConfig {
  /** 最多領先伺服器幾格。 */
  lead_max: number;
  /** 看得到敵人時最多領先幾格。 */
  lead_max_enemy_seen: number;
}

export const WALK_AHEAD: WalkAheadConfig = config;

type Facing = FieldView["me"]["facing"];

/** 畫面上主角站的格子與面向（領先伺服器時用）。 */
export interface ShownHero {
  x: number;
  y: number;
  facing: Facing;
}

const DELTA: Readonly<Record<Direction, readonly [number, number]>> = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };
const FACE: Readonly<Record<Direction, Facing>> = { up: "n", down: "s", left: "w", right: "e" };

/**
 * 開發用的慢動作（拍拉回動畫的連續截圖用）：`?dev=1&walkms=N` 時方向鍵先走與拉回每格 N 毫秒；
 * 不帶 `?dev=1`、沒給或格式不對 → `null`（照 `STEP_MS`）。
 */
export function devWalkMs(search: string): number | null {
  if (!isDevMode(search)) return null;
  const n = Number(new URLSearchParams(search).get("walkms") ?? "");
  return Number.isInteger(n) && n > 0 ? n : null;
}

/** 這張畫面最多可以領先幾格（看得到敵人時比較少）。 */
export function leadCap(field: FieldView, cfg: WalkAheadConfig = WALK_AHEAD): number {
  const cap = (field.enemies ?? []).length > 0 ? cfg.lead_max_enemy_seen : cfg.lead_max;
  return Math.max(0, Math.floor(cap));
}

/** 從 `at` 往 `dir` 走一格：`step`＝可以先走、`portal`＝出口、門或傳送石（要等伺服器）；走不過去為 `null`。 */
export function aheadTarget(field: FieldView, at: Pos, dir: Direction): { kind: "step" | "portal"; to: Pos } | null {
  const [dx, dy] = DELTA[dir];
  const to = { x: at.x + dx, y: at.y + dy };
  if (!canStep(field, at, to)) return null;
  return { kind: portalCells(field).has(`${to.x},${to.y}`) ? "portal" : "step", to };
}

/**
 * 拉回的路線：`chain` 是伺服器確認的位置接著先走的格子（最後一格＝畫面上的主角）。
 * 伺服器的格子在路線上就沿原路倒退回去；不在路線上就直接滑過去。不含起點；已經在那裡為空。
 */
export function pullBackPath(chain: readonly Pos[], to: Pos): Pos[] {
  if (chain.length === 0) return [to];
  const end = chain[chain.length - 1]!;
  if (end.x === to.x && end.y === to.y) return [];
  const at = chain.findIndex((p) => p.x === to.x && p.y === to.y);
  if (at < 0) return [to];
  return chain.slice(at, chain.length - 1).reverse();
}

export interface WalkAheadDeps {
  /** 伺服器最後確認（已套用）的實地畫面。 */
  field(): FieldView | null;
  /** 有遭遇或在戰鬥中（不再走）。 */
  blocked(): boolean;
  alive(): boolean;
  /** 現在要走的方向（不用掉）；`take` 用掉一次點按。 */
  peek(): Direction | null;
  take(): void;
  /** 全部放開（對不上時）。 */
  release(): void;
  /** 送一格的 `walk`（失敗時回 `null`，錯誤已顯示）。 */
  send(cell: Pos): Promise<WorldView | null>;
  /** 主角先走一格的動畫。 */
  step(field: FieldView, from: Pos, to: Pos): Promise<void>;
  /** 拉回：主角從 `from` 沿 `path` 滑回去。 */
  slideBack(field: FieldView, from: Pos, path: readonly Pos[]): Promise<void>;
  /** NPC、敵群走一格（套用新畫面之前）。 */
  others(before: FieldView, after: FieldView): Promise<void>;
  /** 套用伺服器的畫面（同步重畫）；`shown`＝畫面上主角站的格子（領先時），`null`＝照伺服器。 */
  commit(view: WorldView, shown: ShownHero | null): void;
  /** 換了地圖（沒預料到）：淡出。 */
  fade(): Promise<void>;
  /** 走進出口、門、傳送石：照舊流程（送、等回應、播動畫、套用）；回傳還能不能接著走。 */
  portal(cell: Pos): Promise<boolean>;
  /** 請求失敗：重畫回伺服器的位置。 */
  failed(): void;
  config?: WalkAheadConfig;
}

interface Answer {
  cell: Pos;
  view: WorldView | null;
}

/** 一次方向鍵走路（按下到放開、或對不上為止）。`run()` 跑完就丟。 */
export class WalkAhead {
  /** 先走了、伺服器還沒確認的格子（依序）。 */
  private pending: Pos[] = [];
  private unsent: Pos[] = [];
  private inflight = false;
  private broken = false;
  private answers: Answer[] = [];
  private wake: (() => void) | null = null;
  private base: FieldView | null = null;
  private mapId = "";
  private facing: Facing = "s";
  /** 同一時間最多領先幾格（測試看）。 */
  maxLead = 0;

  constructor(private readonly deps: WalkAheadDeps) {}

  /** 現在領先伺服器幾格。 */
  get lead(): number {
    return this.pending.length;
  }

  async run(): Promise<void> {
    const d = this.deps;
    this.base = d.field();
    if (this.base === null) return;
    this.mapId = this.base.map_id;
    this.facing = this.base.me.facing;
    while (d.alive() && this.base !== null) {
      const ready = this.answers.splice(0);
      const bad = ready.findIndex((a) => !this.matches(a));
      if (bad >= 0) {
        await this.mismatch(ready, bad);
        return;
      }
      const before: FieldView = this.base;
      const last = ready.length > 0 ? ready[ready.length - 1]! : null;
      const after = last?.view?.field ?? null;
      this.pending.splice(0, ready.length);
      if (after !== null) this.base = after; // 伺服器確認到這裡（畫面等這一格的動畫播完再套用）
      const basis = after ?? before;
      const plan = this.plan(basis);
      const anims: Promise<void>[] = [];
      if (plan?.kind === "step") {
        d.take();
        const from = this.shownPos();
        this.facing = facingOf(from, plan.to, this.facing);
        this.pending.push(plan.to);
        this.unsent.push(plan.to);
        this.maxLead = Math.max(this.maxLead, this.pending.length);
        this.pump();
        anims.push(d.step(basis, from, plan.to));
      }
      if (after !== null) anims.push(d.others(before, after));
      if (anims.length > 0) await Promise.all(anims);
      if (!d.alive()) return;
      if (last !== null && last.view !== null && after !== null) d.commit(last.view, this.shown());
      if (plan?.kind === "portal") {
        d.take();
        const go = await d.portal(plan.to);
        this.base = d.field();
        if (!go || this.base === null || this.base.map_id !== this.mapId) return;
        this.facing = this.base.me.facing;
        continue;
      }
      if (anims.length === 0) {
        if (this.pending.length === 0) return; // 放開了、伺服器也都確認了
        await this.nextAnswer();
      }
    }
  }

  /** 下一步：可以先走的格子、要等伺服器的出口，或 `null`（不走或要先等回應）。 */
  private plan(basis: FieldView): { kind: "step" | "portal"; to: Pos } | null {
    const d = this.deps;
    if (d.blocked()) return null;
    const dir = d.peek();
    if (dir === null) return null;
    const target = aheadTarget(basis, this.shownPos(), dir);
    if (target === null) {
      d.take(); // 走不過去：這次按鍵用掉（按住的照舊按著）
      return null;
    }
    if (target.kind === "portal") return this.pending.length === 0 ? target : null;
    return this.pending.length < leadCap(basis, d.config) ? target : null;
  }

  private shownPos(): Pos {
    const p = this.pending[this.pending.length - 1] ?? this.base!.me;
    return { x: p.x, y: p.y };
  }

  private shown(): ShownHero | null {
    const p = this.pending[this.pending.length - 1];
    return p === undefined ? null : { x: p.x, y: p.y, facing: this.facing };
  }

  private matches(a: Answer): boolean {
    const v = a.view;
    if (v === null || v.encounter != null || v.battle_id != null) return false;
    const f = v.field;
    return f != null && f.map_id === this.mapId && f.me.x === a.cell.x && f.me.y === a.cell.y;
  }

  /** 背景照順序送（同時一個）；對不上之後不再送。 */
  private pump(): void {
    if (this.inflight || this.broken || this.unsent.length === 0) return;
    const cell = this.unsent.shift()!;
    this.inflight = true;
    void this.deps
      .send(cell)
      .catch(() => null)
      .then((view) => {
        this.inflight = false;
        const answer = { cell, view };
        this.answers.push(answer);
        if (this.matches(answer)) this.pump();
        else {
          this.broken = true;
          this.unsent = [];
        }
        const wake = this.wake;
        this.wake = null;
        wake?.();
      });
  }

  private nextAnswer(): Promise<void> {
    if (this.answers.length > 0) return Promise.resolve();
    return new Promise((resolve) => {
      this.wake = resolve;
    });
  }

  /** 對不上：前面對得上的照算，主角滑回伺服器的格子，套用伺服器的畫面，停下。 */
  private async mismatch(ready: readonly Answer[], bad: number): Promise<void> {
    const d = this.deps;
    const base = this.base!;
    const good = ready.slice(0, bad);
    const lastGood = good.length > 0 ? good[good.length - 1]!.view : null;
    const confirmed = lastGood?.field ?? base;
    const answer = ready[bad]!;
    const view = answer.view;
    const chain = [{ x: base.me.x, y: base.me.y }, ...this.pending];
    const from = this.shownPos();
    const sameMap = view !== null && view.field != null && view.field.map_id === this.mapId;
    const at = view === null ? confirmed.me : sameMap ? view.field!.me : null;
    const target = at === null ? null : { x: at.x, y: at.y };
    this.pending = [];
    this.unsent = [];
    d.release();
    if (target !== null) {
      const back = pullBackPath(chain, target);
      if (back.length > 0 && d.alive()) await d.slideBack(base, from, back);
    }
    if (!d.alive()) return;
    if (view === null) {
      if (lastGood !== null) {
        this.base = confirmed;
        d.commit(lastGood, null);
      }
      d.failed();
      return;
    }
    if (!sameMap) await d.fade();
    if (!d.alive()) return;
    this.base = view.field ?? null;
    d.commit(view, null);
  }
}

function facingOf(from: Pos, to: Pos, was: Facing): Facing {
  if (to.x > from.x) return FACE.right;
  if (to.x < from.x) return FACE.left;
  if (to.y > from.y) return FACE.down;
  if (to.y < from.y) return FACE.up;
  return was;
}
