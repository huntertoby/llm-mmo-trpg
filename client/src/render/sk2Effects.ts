// SK-2 三個新原語的演出接線（AR-SK2）：`battle/sk2Fx.ts` 的描述 → 效果（`Effect`），畫法在 `sk2FxArt.ts`（Canvas2D）。
// 每個演出一張離屏 canvas（只框住它用到的範圍），每一格重畫後更新貼圖；單位之上的放效果層，
// 單位之下的（吸收表面的光柱、疾病擴散的範圍格與地上的 V）放那一排的表面裝飾層（重畫清掉時下一格再掛回去）。
// 時間：描述裡是未縮放的毫秒，這裡乘上播放速度的倍率 `scale`。減少動態時呼叫端不播。
import { Container, Rectangle, Sprite, Texture } from "pixi.js";
import type { Pos } from "../api/types";
import type { Sk2Absorb, Sk2Fx, Sk2Hook, Sk2Spread } from "../battle/sk2Fx";
import { TILE_SIZE } from "../battle/geometry";
import * as QP from "./qIcon/parts";
import { ABSORB_MS, ABSORB_SHRINK, absorbTop, absorbUnder, chainMinK, HOOK_FLY_MS, hookOver, moteKind, SPREAD_MS, spreadTop, spreadUnder, type Pt, type Sk2AbsorbGeom, type Sk2HookGeom, type Sk2SpreadGeom } from "./sk2FxArt";
import type { Effect } from "./vfxEffects";

const T = TILE_SIZE;
/** 離屏 canvas 的解析度（每個模型像素幾個貼圖像素）。 */
const RES = 2;
/** 腳底、胸口、頭頂相對格子中心（`unitSprite.FEET`＝T×0.23；胸口＝腳底往上 22、頭頂＝腳底往上 52）。 */
const FEET = T * 0.23;
const CHEST = FEET - 22;
const HEAD = FEET - 52;

/** 繪製器提供的操作（只畫，不碰規則）。 */
export interface Sk2Host {
  /** 格子中心（世界座標，含抬高）。 */
  center(p: Pos): Pt;
  /** 單位現在的節點（站著或倒下；被拉的人跟著它走）。 */
  unitNode(id: string): Container | null;
  /** 單位朝東（1）或朝西（-1）；不知道時 1。 */
  side(id: string): 1 | -1;
  /** 那一排的表面裝飾層（單位之下）。 */
  deco(y: number): Container;
  /** 地圖縮放（鎖鏈與虛線的畫面下限）。 */
  boardScale(): number;
  /** 吸收表面：表面提早往中心收縮（`SurfaceAnimator.absorbNow`；`delayMs` 未縮放）。 */
  absorbSurface(p: Pos, delayMs: number): void;
}

/** 演出這一刻的施放者手的位置（`playSkill` 給的作用端；沒有時呼叫端給 `null`）。 */
export type Sk2Origin = Pt | null;

export interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

export function boxOf(pts: readonly Pt[], pad: number): Box {
  const xs = pts.map((p) => p.x), ys = pts.map((p) => p.y);
  const x = Math.floor(Math.min(...xs) - pad), y = Math.floor(Math.min(...ys) - pad);
  return { x, y, w: Math.ceil(Math.max(...xs) + pad) - x, h: Math.ceil(Math.max(...ys) + pad) - y };
}

/** 一張框住 `box` 的離屏 canvas 與它的貼圖；`paint` 在世界座標畫。沒有畫布（測試環境）時回 null。 */
class FxCanvas {
  readonly tex: Texture;
  private readonly ctx: CanvasRenderingContext2D;
  constructor(
    readonly box: Box,
    canvas: HTMLCanvasElement,
    ctx: CanvasRenderingContext2D,
  ) {
    this.ctx = ctx;
    this.tex = Texture.from(canvas);
  }
  static make(box: Box): FxCanvas | null {
    if (typeof document === "undefined") return null;
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(box.w * RES));
    canvas.height = Math.max(1, Math.round(box.h * RES));
    const ctx = canvas.getContext("2d");
    return ctx === null ? null : new FxCanvas(box, canvas, ctx);
  }
  sprite(): Sprite {
    const s = new Sprite(this.tex);
    s.position.set(this.box.x, this.box.y);
    s.width = this.box.w;
    s.height = this.box.h;
    return s;
  }
  paint(draw: (ctx: CanvasRenderingContext2D) => void): void {
    const c = this.ctx;
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.clearRect(0, 0, c.canvas.width, c.canvas.height);
    c.setTransform(RES, 0, 0, RES, -this.box.x * RES, -this.box.y * RES);
    draw(c);
    this.tex.source.update();
  }
  destroy(): void {
    this.tex.destroy(true);
  }
}

/**
 * 單位之下的那一張：照排切成幾段（每一段只含那一排的高度），各掛在那一排的表面裝飾層——
 * 南邊一排的地形畫在北邊一排之後，整張掛在一排會被南邊的地形蓋掉。重畫清掉時下一格再掛回去。
 */
class UnderSprite {
  private nodes: Sprite[] = [];
  private readonly bands: { row: number; tex: Texture; x: number; y: number; w: number; h: number }[] = [];
  constructor(
    fx: FxCanvas,
    private readonly host: Pick<Sk2Host, "deco">,
    rows: readonly number[],
  ) {
    const b = fx.box;
    for (const row of [...new Set(rows)].sort((p, q) => p - q)) {
      // 最北的一段往上延到畫布頂（光柱往上伸進北邊那一排），最南的一段往下延到畫布底
      const first = row === Math.min(...rows), last = row === Math.max(...rows);
      const y0 = first ? b.y : Math.max(b.y, row * T), y1 = last ? b.y + b.h : Math.min(b.y + b.h, (row + 1) * T);
      if (y1 <= y0) continue;
      const frame = new Rectangle(0, Math.round((y0 - b.y) * RES), Math.round(b.w * RES), Math.max(1, Math.round((y1 - y0) * RES)));
      if (frame.y + frame.height > fx.tex.source.height) frame.height = fx.tex.source.height - frame.y;
      if (frame.height <= 0) continue;
      this.bands.push({ row, tex: new Texture({ source: fx.tex.source, frame }), x: b.x, y: y0, w: b.w, h: frame.height / RES });
    }
  }
  attach(): void {
    if (this.nodes.length === this.bands.length && this.nodes.every((n) => !n.destroyed && n.parent !== null)) return;
    this.destroy();
    this.nodes = this.bands.map((band) => {
      const n = new Sprite(band.tex);
      n.position.set(band.x, band.y);
      n.width = band.w;
      n.height = band.h;
      this.host.deco(band.row).addChild(n);
      return n;
    });
  }
  destroy(): void {
    for (const n of this.nodes) if (!n.destroyed) n.destroy();
    this.nodes = [];
  }
}

/** 一個演出：`dur` 毫秒（未縮放），畫單位之上（`top`）與之下（`under`，可省）。 */
export function canvasEffect(host: Pick<Sk2Host, "deco">, startMs: number, dur: number, scale: number, box: Box, top: (ctx: CanvasRenderingContext2D, t: number) => void, under?: { rows: readonly number[]; draw: (ctx: CanvasRenderingContext2D, t: number) => void }): Effect | null {
  const fxTop = FxCanvas.make(box);
  if (fxTop === null) return null;
  const fxUnder = under === undefined ? null : FxCanvas.make(box);
  const node = new Container();
  const sprite = fxTop.sprite();
  node.addChild(sprite);
  node.visible = false;
  const low = fxUnder === null || under === undefined ? null : new UnderSprite(fxUnder, host, under.rows);
  return {
    node,
    startMs,
    endMs: startMs + Math.max(1, dur * scale),
    update: (u) => {
      const t = u * dur;
      node.visible = true;
      fxTop.paint((c) => top(c, t));
      if (low !== null && fxUnder !== null && under !== undefined) {
        low.attach();
        fxUnder.paint((c) => under.draw(c, t));
      }
    },
    end: () => {
      low?.destroy();
      fxTop.destroy();
      fxUnder?.destroy();
    },
  };
}

// ---- 吸收表面 ----

/** 表面的顏色（本色、亮色）：和部件圖樣同一份（`QP.surfaceTint`：照 `QS.TINT`，黑暗＝暗影色，不認得的照水；AR-SK3）。 */
const surfaceTint = (surface: string): readonly [string, string] => QP.surfaceTint(surface);

/** 收益的圖樣（第④批部件圖樣 16 px）：元素＝元素片、層數＝累積層數、治療、護盾。 */
function gainGlyph(f: Sk2Absorb): HTMLCanvasElement | null {
  const [cat, id] = f.gain === "element" ? ["element", f.element ?? "physical"] : f.gain === "stack" ? ["effect", "add_stack"] : ["effect", f.gain];
  return QP.glyph(cat, id, 16, 4);
}

function absorbEffect(host: Sk2Host, f: Sk2Absorb, now: number, scale: number, origin: Sk2Origin): Effect | null {
  const node = host.unitNode(f.casterId);
  const c = node !== null ? { x: node.x, y: node.y } : host.center(f.tile);
  const side = host.side(f.casterId);
  const geom: Sk2AbsorbGeom = {
    base: host.center(f.tile),
    hand: { x: c.x - 4 * side, y: c.y - 4 },
    head: { x: c.x, y: c.y + HEAD },
    staff: origin,
    tint: f.gain === "element" && f.element !== null ? surfaceTint(f.element) : surfaceTint(f.surface),
    glyph: gainGlyph(f),
    glyphPx: 16 * QP.BOX,
    element: f.gain === "element",
  };
  const tint = surfaceTint(f.surface);
  const g = { ...geom, tint };
  const box = boxOf([geom.base, geom.hand, geom.head, ...(origin === null ? [] : [origin])], 40);
  host.absorbSurface(f.tile, ABSORB_SHRINK.from);
  return canvasEffect(host, now, ABSORB_MS, scale, box, (ctx, t) => absorbTop(ctx, t, { ...g, tint: t > 700 ? geom.tint : tint }), { rows: [f.tile.y], draw: (ctx, t) => absorbUnder(ctx, t, g) });
}

// ---- 疾病擴散 ----

function spreadEffect(host: Sk2Host, f: Sk2Spread, now: number, scale: number): Effect | null {
  const a = host.center(f.from), b = host.center(f.to), K = chainMinK(host.boardScale());
  const geom: Sk2SpreadGeom = {
    from: { x: a.x + 6, y: a.y - 4 },
    dst: { x: b.x, y: b.y + CHEST },
    floorFrom: { x: a.x, y: a.y + 15 },
    floorTo: { x: host.center(f.chosen).x, y: host.center(f.chosen).y + 15 },
    range: f.range.map((p) => ({ x: p.x * T, y: p.y * T })),
    chosen: { x: f.chosen.x * T, y: f.chosen.y * T },
    kind: moteKind(f.statusId),
    K,
  };
  const corners = geom.range.flatMap((p) => [p, { x: p.x + T, y: p.y + T }]);
  const box = boxOf([geom.from, geom.dst, { x: geom.dst.x, y: geom.dst.y - 40 }, ...corners], 24);
  const rows = [f.from.y, f.chosen.y, ...f.range.map((p) => p.y)];
  return canvasEffect(host, now + f.atMs * scale, SPREAD_MS, scale, box, (ctx, t) => spreadTop(ctx, t, geom), { rows, draw: (ctx, t) => spreadUnder(ctx, t, geom, T) });
}

// ---- 鉤 ----

/** 單位節點的位置（格子中心）；沒有節點時照格子。 */
function nodeAt(host: Sk2Host, id: string, fallback: Pos): Pt {
  const n = host.unitNode(id);
  return n !== null && !n.destroyed ? { x: n.x, y: n.y } : host.center(fallback);
}

function hookEffect(host: Sk2Host, f: Sk2Hook, startMs: number, hitMs: number, scale: number, origin: Sk2Origin, startAt: number): Effect | null {
  const casterC = host.center(f.caster), side = Math.sign(casterC.x - host.center(f.hookTile).x) || 0, sideY = Math.sign(casterC.y - host.center(f.hookTile).y) || 0;
  const hand = origin ?? { x: casterC.x + 6 * host.side(f.casterId), y: casterC.y - 2 };
  const K = chainMinK(host.boardScale());
  const target = (): Pt => {
    if (f.mode === "immovable") {
      const c = host.center(f.hookTile);
      return { x: c.x + side * (T / 2 - 8), y: c.y - 4 + sideY * (T / 2 - 8) };
    }
    const c = nodeAt(host, f.targetId, f.to);
    return { x: c.x + side * 6, y: c.y + CHEST + 4 };
  };
  const feet = (): Pt => {
    const c = nodeAt(host, f.targetId, f.to);
    return { x: c.x, y: c.y + FEET };
  };
  const geom: Sk2HookGeom = { hand, target, mode: f.mode, hazard: f.hazard === null ? null : host.center(f.hazard), feet, K };
  const pullFrom = Math.max(hitMs, f.pullAtMs - startAt);
  const pullTo = pullFrom + Math.max(f.pullMs, f.mode === "pull" ? 300 : 220) + 80;
  const dur = f.mode === "immovable" ? hitMs + 530 : pullTo + (f.mode === "brake" ? 320 : 180);
  const pts = [hand, host.center(f.from), host.center(f.to), host.center(f.hookTile), ...(f.hazard === null ? [] : [host.center(f.hazard)])];
  const box = boxOf(pts, 40 * K);
  return canvasEffect(host, startMs, dur, scale, box, (ctx, t) => hookOver(ctx, t, geom, { hitMs, pullFrom, pullTo }));
}

/**
 * 這一步的 SK-2 演出 → 效果。`now`＝這一步特效的原點（效果時鐘）；`scale`＝播放速度倍率；
 * `casts`（已縮放）給鉤的出手與命中時間；`origins`＝`playSkill` 的作用端（第 i 段）。
 */
export function sk2Effects(host: Sk2Host, list: readonly Sk2Fx[], now: number, scale: number, casts: readonly { startMs: number; impactMs: number }[], origins: ReadonlyMap<number, Pt>): Effect[] {
  const out: Effect[] = [];
  for (const f of list) {
    let e: Effect | null = null;
    if (f.kind === "absorb") e = absorbEffect(host, f, now, scale, origins.get(0) ?? null);
    else if (f.kind === "spread") e = spreadEffect(host, f, now, scale);
    else {
      const cast = casts[f.castIndex];
      const start = cast === undefined ? 0 : cast.startMs / scale;
      const hit = cast === undefined ? HOOK_FLY_MS : Math.max(120, (cast.impactMs - cast.startMs) / scale);
      e = hookEffect(host, f, now + start * scale, hit, scale, origins.get(f.castIndex) ?? null, start);
    }
    if (e !== null) out.push(e);
  }
  return out;
}
