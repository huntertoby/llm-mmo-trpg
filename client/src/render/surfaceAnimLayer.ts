// 地表動畫的驅動（Phase 6N-9）：重畫場景時比較前後兩次的表面，播出現／消失／火蔓延；平常讓水、油、火面動。
// - 出現與消失：在新的格子貼圖上面疊一張「舊的樣子」，用圓形遮罩做擴散或收縮（`surfaceAnim.revealAt`）；
//   舊的樣子用同一套地形貼圖（`ArtTextures.tile`，照舊的畫面資料），播完就拿掉。
// - 轉場進行中又重畫（播放時每一步都會重畫）：表面還是同一種的轉場接著播，換了就以新畫面為準。
// - 持續的動態放在那一排的表面裝飾層（`deco`），跟著格子抬高；貼圖只有幾張共用的小圖（6V-2 起含熔岩的岩殼塊與熱光，地形也有持續動態）。
// - 「略過」或 prefers-reduced-motion 時不播轉場、表面不動（直接是結果）。
// - 時鐘是 ticker 累加的毫秒（只影響畫面）。
// - 冷卻井（CW-1，docs/art/冷卻井-移植需求.md 第 4 節）：前一次畫面有、這一次沒有的井＝打破了。漏出的水不是每格自己擴散，
//   而是從井那一格的中心長一個不規則的圓（`coolingWellArt.wellMaskRadius`，K0～K4 共 520 ms），遮罩邊一圈水沫、K3 兩圈漣漪
//   （都在那一格的轉場節點裡，地面層）；碎塊、水柱、水花、水珠（K0～K2）在井那一排的物件層；碎屑（K3 起，之後一直留著）在
//   井那一格的表面裝飾層。「略過」、減少動態時不播演出，直接留碎屑。
import { Container, Graphics, Sprite, type Texture } from "pixi.js";
import type { DrawModel, TileDraw } from "../battle/drawModel";
import { TILE_SIZE } from "../battle/geometry";
import { ANIMATED_SURFACES, changeTotalMs, revealAt, sameBoard, surfaceChanges, terrainAnimated, tileShimmer, type SurfaceChange } from "./surfaceAnim";
import type { Ctx } from "./artDraw";
import { drawWellBreakAir, drawWellRubble, WELL_BREAK_MS, WELL_GEOM, wellFrameAt, wellMaskPoints, wellMaskRadius } from "./coolingWellArt";
import { brokenWells, COOLING_WELL, spillSource, type WellPos } from "./wellBreak";
import type { ArtTheme } from "./regionArt";
import { shimmerTexture } from "./statusAnimArt";

const T = TILE_SIZE;
const K = T / 52;

/** 繪製器提供的接口（只畫，不碰規則）。 */
export interface SurfaceHost {
  /** 那一排的地形層、表面裝飾層。 */
  ground(y: number): Container;
  deco(y: number): Container;
  /** 放到格子的左上角（含抬高），升降動畫會跟著移。 */
  place(node: Container, t: TileDraw): void;
  /** 舊畫面那一格的地形貼圖。 */
  oldTile(from: DrawModel, t: TileDraw): Texture | null;
  /** 那一排的物件層（冷卻井的破壞演出；沒給時不畫演出與碎屑）。 */
  objects?(y: number): Container;
  /** 快取的離屏 canvas 貼圖（冷卻井的演出、碎屑；沒給時不畫）。 */
  canvas?(key: string, make: () => HTMLCanvasElement | null): Texture | null;
}

/** 冷卻井貼圖的解析度（同 `artTextures.ART_RESOLUTION`：每個格子像素 2 個貼圖像素）。 */
const WELL_RES = 2;

/** 冷卻井演出、碎屑的離屏 canvas：`span` 格見方（1＝那一格；3＝以那一格為中心的 3×3），座標照那一格的 52 單位。 */
function wellCanvas(span: number, draw: (ctx: Ctx) => void): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const size = Math.round(T * span * WELL_RES);
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (ctx === null) return null;
  ctx.scale(size / (52 * span), size / (52 * span));
  ctx.translate(52 * ((span - 1) / 2), 52 * ((span - 1) / 2));
  draw(ctx);
  return canvas;
}

/** 一口正在播破壞演出的井。 */
interface WellAnim {
  pos: WellPos;
  start: number;
  scale: number;
  /** 物件層的節點（K0～K2 各一張貼圖）。 */
  air: Sprite[];
  node: Container | null;
}

interface Transition {
  change: SurfaceChange;
  start: number;
  scale: number;
  from: DrawModel;
  node: Container | null;
  mask: Graphics | null;
  /** 冷卻井漏出的水：從這口井長出來（遮罩照井的時間表，不是每格自己擴散）。 */
  well: WellPos | null;
  /** 水沫、漣漪（只有冷卻井的水）。 */
  fx: Graphics | null;
}

interface ShimmerNode {
  tile: TileDraw;
  theme: ArtTheme;
  sprites: Sprite[];
  node: Container;
}

const key = (x: number, y: number): string => `${x},${y}`;

/** 轉場整段的長度（冷卻井的水照井的時間表）。 */
const transitionMs = (tr: Transition): number => (tr.well === null ? changeTotalMs(tr.change, tr.scale) : WELL_BREAK_MS * tr.scale);

export class SurfaceAnimator {
  clock = 0;
  private enabled = true;
  private prev: DrawModel | null = null;
  private readonly transitions = new Map<string, Transition>();
  private shimmers: ShimmerNode[] = [];
  /** 正在播破壞演出的冷卻井（鍵＝格子）。 */
  private readonly wells = new Map<string, WellAnim>();
  /** 這場打破過的冷卻井（碎屑一直留著；同一格又有井時拿掉）。 */
  private readonly rubble = new Map<string, WellPos>();
  /** 碎屑節點（演出 K3 前藏起來）。 */
  private rubbleNodes = new Map<string, Container>();

  /**
   * 重畫場景時呼叫（地形畫好、單位還沒畫之前）。`timeScale`：播放速度的時間倍率；`null` ＝ 略過（不播轉場）。
   */
  draw(model: DrawModel, host: SurfaceHost, timeScale: number | null): void {
    const prev = this.prev;
    this.prev = model;
    this.shimmers = [];
    const surfaceAt = new Map(model.tiles.map((t) => [key(t.x, t.y), String(t.surface)]));
    const broken = this.trackWells(prev, model);
    if (prev !== null && this.enabled && timeScale !== null && timeScale > 0) {
      for (const w of broken) this.wells.set(key(w.x, w.y), { pos: w, start: this.clock, scale: timeScale, air: [], node: null });
      for (const c of surfaceChanges(prev, model)) {
        this.transitions.set(key(c.x, c.y), { change: c, start: this.clock, scale: timeScale, from: prev, node: null, mask: null, well: spillSource(c, broken), fx: null });
      }
    }
    // 換了地圖、表面又變了、播完了的轉場作廢；其餘重建節點（重畫時舊節點已經清掉）
    const tileAt = new Map(model.tiles.map((t) => [key(t.x, t.y), t]));
    for (const [k, tr] of [...this.transitions]) {
      const t = tileAt.get(k);
      const elapsed = this.clock - tr.start;
      if (!this.enabled || t === undefined || surfaceAt.get(k) !== tr.change.after || elapsed >= transitionMs(tr) || t.terrain !== tileOf(tr.from, t)?.terrain) {
        this.transitions.delete(k);
        continue;
      }
      this.buildTransition(tr, t, host);
    }
    this.buildWells(model, host);
    if (!this.enabled) return;
    const theme: ArtTheme = { region: model.region, look: model.look };
    for (const t of model.tiles) {
      if (!ANIMATED_SURFACES.includes(String(t.surface)) && !terrainAnimated(t.terrain, theme)) continue;
      this.buildShimmer(t, theme, host);
    }
    this.apply();
  }

  private buildTransition(tr: Transition, t: TileDraw, host: SurfaceHost): void {
    const old = tileOf(tr.from, t);
    const tex = old === undefined ? null : host.oldTile(tr.from, old);
    if (tex === null) return;
    const node = new Container();
    const sprite = new Sprite(tex);
    sprite.width = T;
    sprite.height = T;
    const mask = new Graphics();
    node.addChild(sprite, mask);
    const f = revealAt(tr.change, this.clock - tr.start, tr.scale);
    sprite.setMask({ mask, inverse: tr.well === null ? f.inverse : true });
    if (tr.well !== null) {
      // 水沫、漣漪只畫在這一格（裁在格子裡）：3×3 的每一格各畫自己那一段，地面層、單位之下
      const fx = new Graphics();
      const clip = new Graphics().rect(0, 0, T, T).fill(0xffffff);
      fx.mask = clip;
      node.addChild(clip, fx);
      tr.fx = fx;
    }
    host.ground(t.y).addChild(node);
    host.place(node, t);
    tr.node = node;
    tr.mask = mask;
  }

  /** 記下這次重畫打破的井（回傳）與這場打破過的井（碎屑）；同一格又有井（新的一場）時拿掉碎屑，換地圖時全清。 */
  private trackWells(prev: DrawModel | null, model: DrawModel): WellPos[] {
    if (prev !== null && !sameBoard(prev, model)) {
      this.rubble.clear();
      this.wells.clear();
    }
    for (const o of model.objects) if (o.kind === COOLING_WELL) this.rubble.delete(key(o.x, o.y));
    const broken = prev === null ? [] : brokenWells(prev, model);
    for (const w of broken) this.rubble.set(key(w.x, w.y), w);
    return broken;
  }

  /** 冷卻井的碎屑（表面裝飾層）與還在播的破壞演出（物件層）。 */
  private buildWells(model: DrawModel, host: SurfaceHost): void {
    this.rubbleNodes = new Map();
    const tileAt = new Map(model.tiles.map((t) => [key(t.x, t.y), t]));
    for (const [k, w] of [...this.wells]) {
      if (!this.enabled || !tileAt.has(k) || this.clock - w.start >= WELL_BREAK_MS * w.scale) this.wells.delete(k);
    }
    const canvas = host.canvas;
    const objects = host.objects;
    if (canvas === undefined || objects === undefined) return;
    for (const [k, w] of this.wells) {
      const t = tileAt.get(k);
      if (t === undefined) continue;
      const node = new Container();
      w.air = [0, 1, 2].map((f) => {
        const tex = canvas(`cw|air|${w.pos.x}|${w.pos.y}|${f}`, () => wellCanvas(3, (ctx) => drawWellBreakAir(ctx, w.pos, f)));
        const sprite = tex === null ? new Sprite() : new Sprite(tex);
        sprite.position.set(-T, -T);
        sprite.width = 3 * T;
        sprite.height = 3 * T;
        sprite.visible = false;
        node.addChild(sprite);
        return sprite;
      });
      objects(t.y).addChild(node);
      host.place(node, t);
      w.node = node;
    }
    for (const [k, w] of this.rubble) {
      const t = tileAt.get(k);
      const tex = canvas(`cw|rubble|${w.x}|${w.y}`, () => wellCanvas(1, (ctx) => drawWellRubble(ctx, w)));
      if (t === undefined || tex === null) continue;
      const node = new Container();
      const sprite = new Sprite(tex);
      sprite.width = T;
      sprite.height = T;
      node.addChild(sprite);
      host.deco(t.y).addChild(node);
      host.place(node, t);
      this.rubbleNodes.set(k, node);
    }
    this.applyWells();
  }

  /** 冷卻井演出這一刻的畫面：K0～K2 物件層換貼圖，K3 起露出碎屑；播完拿掉。 */
  private applyWells(): void {
    for (const [k, w] of [...this.wells]) {
      const ms = (this.clock - w.start) / w.scale;
      const f = wellFrameAt(ms);
      const done = ms >= WELL_BREAK_MS;
      w.air.forEach((s, i) => {
        if (!s.destroyed) s.visible = !done && i === f;
      });
      const rubble = this.rubbleNodes.get(k);
      if (rubble !== undefined && !rubble.destroyed) rubble.visible = done || f >= 3;
      if (done) {
        if (w.node !== null && !w.node.destroyed) w.node.destroy({ children: true });
        this.wells.delete(k);
      }
    }
  }

  /** 冷卻井漏出的水：遮罩照井的時間表從井心長出來，遮罩邊一圈水沫（K1～K3）、K3 兩圈漣漪。播完回傳 `true`。 */
  private applySpill(tr: Transition): boolean {
    const well = tr.well as WellPos;
    const ms = (this.clock - tr.start) / tr.scale;
    if (ms >= WELL_BREAK_MS) return true;
    const mask = tr.mask;
    if (mask === null || mask.destroyed) return false;
    const R = wellMaskRadius(ms);
    const ox = (well.x - tr.change.x) * T;
    const oy = (well.y - tr.change.y) * T;
    const pts = R > 0 ? wellMaskPoints(R).flatMap(([x, y]) => [ox + x * K, oy + y * K]) : [];
    mask.clear();
    if (pts.length > 0) mask.poly(pts).fill(0xffffff);
    else mask.circle(T / 2, T / 2, 0.01).fill(0xffffff);
    const fx = tr.fx;
    if (fx === null || fx.destroyed) return false;
    fx.clear();
    const f = wellFrameAt(ms);
    if (f >= 1 && pts.length > 0) fx.poly(pts).stroke({ width: 1.5 * K, color: 0x8fd4ff, alpha: 0.6, join: "round" });
    if (f === 3) {
      for (const q of [44, 74]) fx.ellipse(ox + WELL_GEOM.cx * K, oy + 26 * K, q * K, q * 0.92 * K).stroke({ width: 1.6 * K, color: 0xebf8ff, alpha: 0.6 });
    }
    return false;
  }

  private buildShimmer(t: TileDraw, theme: ArtTheme, host: SurfaceHost): void {
    const node = new Container();
    const sprites: Sprite[] = [];
    for (const s of tileShimmer(t.terrain, String(t.surface), t.x, t.y, this.clock, theme)) {
      const tex = shimmerTexture(s.tex);
      if (tex === null) continue;
      const sprite = new Sprite(tex.texture);
      sprite.anchor.set(tex.ax, tex.ay);
      sprite.blendMode = s.blend ?? "add";
      node.addChild(sprite);
      sprites.push(sprite);
    }
    if (sprites.length === 0) return;
    host.deco(t.y).addChild(node);
    host.place(node, t);
    this.shimmers.push({ tile: t, theme, sprites, node });
  }

  /** 開關（prefers-reduced-motion）；關掉時拿掉轉場、表面停下來（下一次重畫前先藏起來）。 */
  setEnabled(on: boolean): void {
    if (this.enabled === on) return;
    this.enabled = on;
    if (on) return;
    for (const tr of this.transitions.values()) if (tr.node !== null && !tr.node.destroyed) tr.node.destroy({ children: true });
    this.transitions.clear();
    for (const w of this.wells.values()) if (w.node !== null && !w.node.destroyed) w.node.destroy({ children: true });
    this.wells.clear();
    for (const n of this.rubbleNodes.values()) if (!n.destroyed) n.visible = true;
    for (const s of this.shimmers) if (!s.node.destroyed) s.node.visible = false;
  }

  get isEnabled(): boolean {
    return this.enabled;
  }

  tick(dt: number): void {
    this.clock += dt;
    if (!this.enabled) return;
    this.apply();
  }

  private apply(): void {
    /** 還在出現中的格子：表面動態跟著擴散的程度淡入（還沒燒到的油格不先發光）。 */
    const reveal = new Map<string, number>();
    this.applyWells();
    for (const [k, tr] of [...this.transitions]) {
      if (tr.well !== null) {
        reveal.set(k, Math.min(1, (this.clock - tr.start) / tr.scale / WELL_BREAK_MS));
        if (!this.applySpill(tr)) continue;
        if (tr.node !== null && !tr.node.destroyed) tr.node.destroy({ children: true });
        this.transitions.delete(k);
        continue;
      }
      const f = revealAt(tr.change, this.clock - tr.start, tr.scale);
      if (tr.change.kind === "appear" && !f.done) reveal.set(k, f.radius / 0.75);
      if (f.done) {
        if (tr.node !== null && !tr.node.destroyed) tr.node.destroy({ children: true });
        this.transitions.delete(k);
        continue;
      }
      if (tr.mask === null || tr.mask.destroyed) continue;
      tr.mask.clear();
      // 收縮到 0 時遮罩是空的：普通遮罩會把舊的樣子整個藏起來（正是要的）
      tr.mask.circle(T / 2, T / 2, Math.max(0.01, f.radius * T)).fill(0xffffff);
    }
    for (const s of this.shimmers) {
      if (s.node.destroyed) continue;
      const frames = tileShimmer(s.tile.terrain, String(s.tile.surface), s.tile.x, s.tile.y, this.clock, s.theme);
      const fade = reveal.get(key(s.tile.x, s.tile.y)) ?? 1;
      frames.forEach((f, i) => {
        const sprite = s.sprites[i];
        if (sprite === undefined || sprite.destroyed) return;
        const tex = shimmerTexture(f.tex);
        if (tex === null) return;
        const k = (K * f.scale * tex.w) / sprite.texture.width;
        sprite.scale.set(k);
        sprite.position.set(f.x * T, f.y * T);
        sprite.rotation = f.rot;
        sprite.alpha = f.alpha * fade;
        sprite.tint = f.tint;
      });
    }
  }

  /** 進行中的轉場數、表面動態的格數（量測、測試用）。 */
  stats(): { transitions: number; shimmers: number } {
    return { transitions: this.transitions.size, shimmers: this.shimmers.length };
  }

  /** 冷卻井：正在播演出的井數、留著碎屑的井（測試、dev 頁用）。 */
  wellStats(): { breaking: number; rubble: WellPos[] } {
    return { breaking: this.wells.size, rubble: [...this.rubble.values()] };
  }

  /** 進行中的轉場（測試、dev 頁用）。 */
  activeChanges(): SurfaceChange[] {
    return [...this.transitions.values()].map((t) => t.change);
  }
}

function tileOf(model: DrawModel, p: { x: number; y: number }): TileDraw | undefined {
  return model.tiles.find((t) => t.x === p.x && t.y === p.y);
}
