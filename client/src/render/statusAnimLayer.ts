// 狀態動作的驅動（Phase 6N-9）：每幀把 statusAnim 的粒子與身體動作套到有狀態的人身上（戰場與探索共用 BattleRenderer）。
// - 粒子放在小人容器裡、身上特效之上（跟著人移動、抬高），HP 條與狀態列仍在最上面。
// - 暈眩的星星、火與毒的腳邊粒子原本畫在靜態的身上特效貼圖裡；動畫開著時那張貼圖換成「拿掉這幾樣」的版本，
//   由動畫畫會動的版本；關掉（prefers-reduced-motion）時換回原本的靜態貼圖，畫面和 6N-9 之前一樣。
// - 正在走、受擊、進出門的人（待機的 `hold`）不動身體（避免和那些片段搶旋轉、透明度），粒子照畫。
// - 時鐘是 ticker 累加的毫秒（只影響畫面）。
import { Container, Sprite, type Texture } from "pixi.js";
import type { UnitDraw } from "../battle/drawModel";
import { TILE_SIZE } from "../battle/geometry";
import { STILL_FRAME, hasAnimatedStatic, staticRemainder, statusAnimKinds, statusFrame, type Particle, type StatusAnimKind, type StatusFrame } from "./statusAnim";
import { particleTexture } from "./statusAnimArt";
import { bodyEffects } from "./statusIcon";
import { BODY_FX_LABEL, BODY_LABEL, bodyNodes, effectTextureOf, FEET, FX_OVER_LABEL, isProne } from "./unitSprite";

const T = TILE_SIZE;
const K = T / 52;
export const STATUS_ANIM_LABEL = "status-anim";

interface BodyBase {
  rot: number;
  skewX: number;
  alpha: number;
  tint: number;
}

interface Entry {
  sprite: Container;
  kinds: StatusAnimKind[];
  layer: Container;
  pool: Sprite[];
  over: Sprite | null;
  overStatic: Texture | null;
  overAnim: Texture | null;
}

/** 腳底的 y 是 `FEET`；粒子座標（虛擬 52）換成小人容器裡的座標。 */
export function particlePlace(p: Particle): { x: number; y: number } {
  return { x: p.x * K, y: FEET + p.y * K };
}

export class StatusAnimator {
  clock = 0;
  enabled = true;
  private readonly entries = new Map<string, Entry>();
  private readonly bases = new WeakMap<Sprite, BodyBase>();
  /** 站在水面上的單位（潮濕）。 */
  private wet = new Set<string>();

  /** 重畫場景後（小人都重建了）：忘掉舊的，下一幀重新掛上。`wet` ＝ 站在水上的單位 ID。 */
  reset(wet: ReadonlySet<string>): void {
    this.entries.clear();
    this.wet = new Set(wet);
  }

  /** 開關（prefers-reduced-motion）；關掉時馬上換回靜態的身上特效、拿掉粒子、身體回原位。 */
  setEnabled(on: boolean): void {
    if (this.enabled === on) return;
    this.enabled = on;
    for (const e of this.entries.values()) this.applyStatic(e, !on);
  }

  private applyStatic(e: Entry, still: boolean): void {
    if (e.sprite.destroyed) return;
    if (e.over !== null && !e.over.destroyed) {
      const tex = still ? e.overStatic : (e.overAnim ?? e.overStatic);
      if (tex !== null && e.over.texture !== tex) e.over.texture = tex;
    }
    if (still) {
      for (const s of e.pool) s.visible = false;
      this.body(e.sprite, STILL_FRAME, false);
    }
  }

  private attach(id: string, sprite: Container, draw: UnitDraw): Entry {
    const kinds = draw.downed ? [] : statusAnimKinds(draw.statusIds ?? [], this.wet.has(id));
    const layer = new Container();
    layer.label = STATUS_ANIM_LABEL;
    // 放在身上特效之上（沒有就放在小人之上），HP 條、狀態列在它上面
    let at = -1;
    sprite.children.forEach((n, i) => {
      if (n.label === FX_OVER_LABEL || n.label === BODY_LABEL || n.label === BODY_FX_LABEL) at = Math.max(at, i);
    });
    sprite.addChildAt(layer, at + 1);
    const over = (sprite.children.find((n) => n.label === FX_OVER_LABEL) as Sprite | undefined) ?? null;
    let overAnim: Texture | null = null;
    if (over !== null && kinds.length > 0) {
      const fx = bodyEffects(draw.statusIds ?? []);
      if (hasAnimatedStatic(fx)) overAnim = effectTextureOf("over", staticRemainder(fx));
    }
    const e: Entry = { sprite, kinds, layer, pool: [], over, overStatic: over?.texture ?? null, overAnim };
    this.entries.set(id, e);
    this.applyStatic(e, !this.enabled);
    return e;
  }

  /** 推進 `dt` 毫秒並套用。`held(id)`：這個人正在播別的動畫（不動身體）。回傳這一幀畫了幾顆粒子（量測用）。 */
  tick(dt: number, units: ReadonlyMap<string, Container>, draws: ReadonlyMap<string, UnitDraw>, held: (id: string) => boolean): number {
    this.clock += dt;
    if (!this.enabled) return 0;
    let shown = 0;
    for (const [id, sprite] of units) {
      if (sprite.destroyed) continue;
      const draw = draws.get(id);
      if (draw === undefined) continue;
      let e = this.entries.get(id);
      // 走路轉彎會重建小人（6A-4d）：換了容器就重新掛上
      if (e === undefined || e.sprite !== sprite) e = this.attach(id, sprite, draw);
      if (e.kinds.length === 0) continue;
      const f = statusFrame(e.kinds, id, this.clock);
      shown += this.paint(e, f.particles);
      if (!held(id)) this.body(sprite, f, isProne(draw));
    }
    return shown;
  }

  private paint(e: Entry, particles: readonly Particle[]): number {
    let n = 0;
    for (const p of particles) {
      const t = particleTexture(p.tex);
      if (t === null) continue;
      let s = e.pool[n];
      if (s === undefined) {
        s = new Sprite(t.texture);
        e.pool.push(s);
        e.layer.addChild(s);
      }
      if (s.texture !== t.texture) s.texture = t.texture;
      s.anchor.set(t.ax, t.ay);
      const k = (K * p.scale * t.w) / t.texture.width;
      s.scale.set(p.flip === true ? -k : k, k);
      const at = particlePlace(p);
      s.position.set(at.x, at.y);
      s.rotation = p.flip === true ? -p.rot : p.rot;
      s.alpha = p.alpha;
      s.visible = p.alpha > 0.01;
      n += 1;
    }
    for (let i = n; i < e.pool.length; i++) e.pool[i]!.visible = false;
    return n;
  }

  private body(sprite: Container, f: StatusFrame, prone: boolean): void {
    for (const node of bodyNodes(sprite)) {
      let base = this.bases.get(node);
      if (base === undefined) {
        base = { rot: node.rotation, skewX: node.skew.x, alpha: node.alpha, tint: node.tint };
        this.bases.set(node, base);
      }
      node.rotation = base.rot + (prone ? 0 : f.body.rot);
      node.skew.x = base.skewX + f.body.skewX;
      node.alpha = base.alpha * f.body.alphaMul;
      const tint = node.label === BODY_LABEL && f.body.tint !== null ? f.body.tint : base.tint;
      if (node.tint !== tint) node.tint = tint;
    }
  }

  /** 目前掛著的單位數與粒子精靈數（量測用）。 */
  stats(): { units: number; sprites: number } {
    let sprites = 0;
    let units = 0;
    for (const e of this.entries.values()) {
      if (e.kinds.length === 0) continue;
      units += 1;
      sprites += e.pool.length;
    }
    return { units, sprites };
  }
}
