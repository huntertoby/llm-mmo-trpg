// 地表動畫的驅動（Phase 6N-9）：重畫場景時比較前後兩次的表面，播出現／消失／火蔓延；平常讓水、油、火面動。
// - 出現與消失：在新的格子貼圖上面疊一張「舊的樣子」，用圓形遮罩做擴散或收縮（`surfaceAnim.revealAt`）；
//   舊的樣子用同一套地形貼圖（`ArtTextures.tile`，照舊的畫面資料），播完就拿掉。
// - 轉場進行中又重畫（播放時每一步都會重畫）：表面還是同一種的轉場接著播，換了就以新畫面為準。
// - 持續的動態放在那一排的表面裝飾層（`deco`），跟著格子抬高；貼圖只有幾張共用的小圖（6V-2 起含熔岩的岩殼塊與熱光，地形也有持續動態）。
// - 「略過」或 prefers-reduced-motion 時不播轉場、表面不動（直接是結果）。
// - 時鐘是 ticker 累加的毫秒（只影響畫面）。
import { Container, Graphics, Sprite, type Texture } from "pixi.js";
import type { DrawModel, TileDraw } from "../battle/drawModel";
import { TILE_SIZE } from "../battle/geometry";
import { ANIMATED_SURFACES, ANIMATED_TERRAINS, changeTotalMs, revealAt, surfaceChanges, tileShimmer, type SurfaceChange } from "./surfaceAnim";
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
}

interface Transition {
  change: SurfaceChange;
  start: number;
  scale: number;
  from: DrawModel;
  node: Container | null;
  mask: Graphics | null;
}

interface ShimmerNode {
  tile: TileDraw;
  sprites: Sprite[];
  node: Container;
}

const key = (x: number, y: number): string => `${x},${y}`;

export class SurfaceAnimator {
  clock = 0;
  private enabled = true;
  private prev: DrawModel | null = null;
  private readonly transitions = new Map<string, Transition>();
  private shimmers: ShimmerNode[] = [];

  /**
   * 重畫場景時呼叫（地形畫好、單位還沒畫之前）。`timeScale`：播放速度的時間倍率；`null` ＝ 略過（不播轉場）。
   */
  draw(model: DrawModel, host: SurfaceHost, timeScale: number | null): void {
    const prev = this.prev;
    this.prev = model;
    this.shimmers = [];
    const surfaceAt = new Map(model.tiles.map((t) => [key(t.x, t.y), String(t.surface)]));
    if (prev !== null && this.enabled && timeScale !== null && timeScale > 0) {
      for (const c of surfaceChanges(prev, model)) this.transitions.set(key(c.x, c.y), { change: c, start: this.clock, scale: timeScale, from: prev, node: null, mask: null });
    }
    // 換了地圖、表面又變了、播完了的轉場作廢；其餘重建節點（重畫時舊節點已經清掉）
    const tileAt = new Map(model.tiles.map((t) => [key(t.x, t.y), t]));
    for (const [k, tr] of [...this.transitions]) {
      const t = tileAt.get(k);
      const elapsed = this.clock - tr.start;
      if (!this.enabled || t === undefined || surfaceAt.get(k) !== tr.change.after || elapsed >= changeTotalMs(tr.change, tr.scale) || t.terrain !== tileOf(tr.from, t)?.terrain) {
        this.transitions.delete(k);
        continue;
      }
      this.buildTransition(tr, t, host);
    }
    if (!this.enabled) return;
    for (const t of model.tiles) {
      if (!ANIMATED_SURFACES.includes(String(t.surface)) && !ANIMATED_TERRAINS.includes(t.terrain)) continue;
      this.buildShimmer(t, host);
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
    sprite.setMask({ mask, inverse: f.inverse });
    host.ground(t.y).addChild(node);
    host.place(node, t);
    tr.node = node;
    tr.mask = mask;
  }

  private buildShimmer(t: TileDraw, host: SurfaceHost): void {
    const node = new Container();
    const sprites: Sprite[] = [];
    for (const s of tileShimmer(t.terrain, String(t.surface), t.x, t.y, this.clock)) {
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
    this.shimmers.push({ tile: t, sprites, node });
  }

  /** 開關（prefers-reduced-motion）；關掉時拿掉轉場、表面停下來（下一次重畫前先藏起來）。 */
  setEnabled(on: boolean): void {
    if (this.enabled === on) return;
    this.enabled = on;
    if (on) return;
    for (const tr of this.transitions.values()) if (tr.node !== null && !tr.node.destroyed) tr.node.destroy({ children: true });
    this.transitions.clear();
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
    for (const [k, tr] of [...this.transitions]) {
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
      const frames = tileShimmer(s.tile.terrain, String(s.tile.surface), s.tile.x, s.tile.y, this.clock);
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

  /** 進行中的轉場（測試、dev 頁用）。 */
  activeChanges(): SurfaceChange[] {
    return [...this.transitions.values()].map((t) => t.change);
  }
}

function tileOf(model: DrawModel, p: { x: number; y: number }): TileDraw | undefined {
  return model.tiles.find((t) => t.x === p.x && t.y === p.y);
}
