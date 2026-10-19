// PixiJS 繪製：照著 `DrawModel` 畫格子、物件、陷阱、單位與高亮；移動動畫只是過場，
// 播放完由呼叫端以新的 `view` 重畫（以 `view` 為準）。
import {
  Application,
  Container,
  Graphics,
  Rectangle,
  Text,
  type FederatedPointerEvent,
  type Ticker,
} from "pixi.js";
import type { Pos } from "../api/types";
import { lerpPos, type MoveAnim } from "../battle/animation";
import type { DrawModel, ObjectDraw, TileDraw, UnitDraw } from "../battle/drawModel";
import { facingArrow } from "../battle/facing";
import { canvasSize, pixelToTile, TILE_SIZE, tileCenter, tileOrigin } from "../battle/geometry";
import { HIGHLIGHT } from "../battle/glossary";
import type { Overlay, OverlayKind } from "../battle/scenePreview";
import type { TelegraphMark } from "../battle/telegraph";

export interface DirectionMark {
  pos: Pos;
  arrow: string;
}

export interface Highlights {
  moves: readonly Pos[];
  /** 可攻擊或可選為技能目標的格子（紅框）。 */
  attacks: readonly Pos[];
  /** 方向型技能：相鄰的方向格（黃色，附箭頭）。 */
  directions: readonly DirectionMark[];
  /** 預覽的影響範圍（橘色）。 */
  preview: readonly Pos[];
  /** 環境預告：下一次環境回合會變化的格子（半透明外框與小圖示）。 */
  telegraph: readonly TelegraphMark[];
  /** 反應詢問的觸發者所在格（洋紅色雙框）。 */
  focus: Pos | null;
  hover: Pos | null;
  /** 場景物件的預覽標記：穿透路線與穿過的物件、推倒壓住的範圍、投擲的物件與落點（Phase 3C-5b）。 */
  overlays: readonly Overlay[];
  /** 投擲物件第二段選取時，已經選好（舉起）的物件所在格（青色粗框）。 */
  picked: readonly Pos[];
}

export interface RendererCallbacks {
  onTileClick(tile: Pos): void;
  onTileHover(tile: Pos | null): void;
}

const T = TILE_SIZE;
const BACKGROUND = 0x15151c;
const FONT = "system-ui, 'Microsoft JhengHei', 'PingFang TC', sans-serif";

function clearLayer(layer: Container): void {
  for (const child of layer.removeChildren()) child.destroy({ children: true });
}

function label(text: string, size: number, fill: number, bold = false): Text {
  return new Text({
    text,
    style: { fontFamily: FONT, fontSize: size, fill, fontWeight: bold ? "700" : "400" },
  });
}

const OVERLAY_COLORS: Readonly<Record<OverlayKind, number>> = {
  route: HIGHLIGHT.route,
  pierced: HIGHLIGHT.pierced,
  behind: HIGHLIGHT.behind,
  crush: HIGHLIGHT.crush,
  rubble: HIGHLIGHT.rubble,
  hurl_from: HIGHLIGHT.picked,
  hurl_to: HIGHLIGHT.landing,
  dash_path: HIGHLIGHT.dash,
  dash_end: HIGHLIGHT.dash,
  charge_hit: HIGHLIGHT.dash,
  leap_to: HIGHLIGHT.leap,
  swap: HIGHLIGHT.swap,
  teleport_from: HIGHLIGHT.banish,
  teleport_to: HIGHLIGHT.banish,
  teleport_lethal: HIGHLIGHT.banish_lethal,
  summon_at: HIGHLIGHT.summon,
  summon_aura: HIGHLIGHT.summon,
  summon_gone: HIGHLIGHT.banish_lethal,
  bomb_blast: HIGHLIGHT.bomb,
  bomb_at: HIGHLIGHT.bomb,
  revive_at: HIGHLIGHT.revive,
};

function hpColor(ratio: number): number {
  if (ratio > 0.5) return 0x4cd964;
  if (ratio > 0.25) return 0xffcc00;
  return 0xff3b30;
}

export class BattleRenderer {
  private readonly app = new Application();
  private readonly tiles = new Container();
  private readonly auras = new Container();
  private readonly zones = new Container();
  private readonly highlights = new Container();
  private readonly objects = new Container();
  private readonly traps = new Container();
  private readonly units = new Container();
  private readonly hover = new Container();
  private readonly unitSprites = new Map<string, Container>();
  private model: DrawModel | null = null;
  private ready = false;
  private destroyed = false;
  private readonly callbacks: RendererCallbacks;

  constructor(callbacks: RendererCallbacks) {
    this.callbacks = callbacks;
  }

  async init(host: HTMLElement): Promise<void> {
    await this.app.init({
      width: 8 * T,
      height: 8 * T,
      background: BACKGROUND,
      antialias: true,
      resolution: window.devicePixelRatio || 1,
      autoDensity: true,
    });
    if (this.destroyed) {
      this.app.destroy(true, { children: true });
      return;
    }
    host.appendChild(this.app.canvas);
    const stage = this.app.stage;
    stage.addChild(this.tiles, this.auras, this.zones, this.objects, this.highlights, this.traps, this.units, this.hover);
    stage.eventMode = "static";
    stage.on("pointermove", (e: FederatedPointerEvent) => this.callbacks.onTileHover(this.tileOf(e)));
    stage.on("pointerleave", () => this.callbacks.onTileHover(null));
    stage.on("pointertap", (e: FederatedPointerEvent) => {
      const tile = this.tileOf(e);
      if (tile !== null) this.callbacks.onTileClick(tile);
    });
    this.ready = true;
    if (this.model !== null) this.draw(this.model);
  }

  destroy(): void {
    this.destroyed = true;
    if (this.ready) this.app.destroy(true, { children: true });
    this.ready = false;
  }

  private tileOf(e: FederatedPointerEvent): Pos | null {
    if (this.model === null) return null;
    return pixelToTile(e.global.x, e.global.y, this.model);
  }

  draw(model: DrawModel): void {
    this.model = model;
    if (!this.ready) return;
    const size = canvasSize(model);
    if (this.app.screen.width !== size.width || this.app.screen.height !== size.height) {
      this.app.renderer.resize(size.width, size.height);
    }
    this.app.stage.hitArea = new Rectangle(0, 0, size.width, size.height);
    clearLayer(this.tiles);
    clearLayer(this.auras);
    clearLayer(this.zones);
    clearLayer(this.objects);
    clearLayer(this.traps);
    clearLayer(this.units);
    this.unitSprites.clear();
    for (const t of model.tiles) this.tiles.addChild(this.tileSprite(t));
    const aura = new Graphics();
    for (const a of model.auras) {
      const o = tileOrigin(a);
      aura.rect(o.x + 2, o.y + 2, T - 4, T - 4).fill({ color: HIGHLIGHT.summon, alpha: 0.14 });
    }
    this.auras.addChild(aura);
    this.drawZones(model);
    for (const o of model.objects) this.objects.addChild(this.objectSprite(o));
    for (const trap of model.traps) {
      const c = tileCenter(trap);
      const glyph = label("^", 22, trap.color, true);
      glyph.anchor.set(0.5);
      glyph.position.set(c.x + T * 0.28, c.y + T * 0.22);
      this.traps.addChild(glyph);
    }
    for (const u of model.units) {
      const sprite = this.unitSprite(u);
      this.units.addChild(sprite);
      if (!u.downed) this.unitSprites.set(u.id, sprite);
    }
  }

  /** 持續區域（Phase 3D-5）：半透明底色加細框；移動型在格子左下角畫方向箭頭。 */
  private drawZones(model: DrawModel): void {
    const g = new Graphics();
    for (const z of model.zones) {
      const o = tileOrigin(z);
      g.rect(o.x + 1, o.y + 1, T - 2, T - 2)
        .fill({ color: z.color, alpha: 0.22 })
        .stroke({ width: 1, color: z.color, alpha: 0.7 });
    }
    this.zones.addChild(g);
    for (const z of model.zones) {
      if (z.arrow === null) continue;
      const o = tileOrigin(z);
      const arrow = label(z.arrow, 16, z.color, true);
      arrow.anchor.set(0.5);
      arrow.position.set(o.x + 11, o.y + T - 11);
      arrow.style.stroke = { color: 0x000000, width: 3 };
      this.zones.addChild(arrow);
    }
  }

  private tileSprite(t: TileDraw): Container {
    const c = new Container();
    const o = tileOrigin(t);
    c.position.set(o.x, o.y);
    const g = new Graphics()
      .rect(0, 0, T, T)
      .fill(t.fill)
      .stroke({ width: 1, color: 0x000000, alpha: 0.35 });
    if (t.wall) {
      // 牆：磚紋
      g.moveTo(0, T / 2).lineTo(T, T / 2);
      g.moveTo(T / 2, 0).lineTo(T / 2, T / 2);
      g.moveTo(T / 4, T / 2).lineTo(T / 4, T);
      g.moveTo((3 * T) / 4, T / 2).lineTo((3 * T) / 4, T);
      g.stroke({ width: 2, color: 0x2a2522 });
    }
    if (t.deadly) {
      g.rect(3, 3, T - 6, T - 6).stroke({ width: 2, color: HIGHLIGHT.deadly, alpha: 0.8 });
      g.moveTo(T * 0.3, T * 0.3).lineTo(T * 0.7, T * 0.7);
      g.moveTo(T * 0.7, T * 0.3).lineTo(T * 0.3, T * 0.7);
      g.stroke({ width: 2, color: HIGHLIGHT.deadly, alpha: 0.6 });
    }
    c.addChild(g);
    if (!t.blocked || t.wall) {
      const h = label(t.heightLabel, 11, 0x000000, true);
      h.alpha = 0.55;
      h.position.set(3, 1);
      c.addChild(h);
    }
    return c;
  }

  private objectSprite(o: ObjectDraw): Container {
    const c = new Container();
    const origin = tileOrigin(o);
    c.position.set(origin.x, origin.y);
    const g = new Graphics();
    if (o.floor) {
      g.rect(2, 2, T - 4, T - 4).fill({ color: o.fill, alpha: 0.75 });
    } else {
      g.roundRect(T * 0.18, T * 0.18, T * 0.64, T * 0.64, 6).fill(o.fill);
    }
    if (o.burning) {
      g.rect(1, 1, T - 2, T - 2).stroke({ width: 3, color: HIGHLIGHT.burning });
    } else if (o.flammable) {
      g.circle(T - 8, 8, 4).fill(HIGHLIGHT.flammable);
    }
    c.addChild(g);
    const glyph = label(o.burning ? `${o.glyph}火` : o.glyph, o.floor ? 12 : 16, 0xffffff, true);
    glyph.anchor.set(0.5);
    glyph.position.set(T / 2, o.floor ? T - 10 : T / 2);
    c.addChild(glyph);
    if (o.hpRatio !== null && o.hpRatio < 1 && !o.floor) {
      const bar = new Graphics().rect(T * 0.18, T * 0.84, T * 0.64, 3).fill(0x000000);
      bar.rect(T * 0.18, T * 0.84, T * 0.64 * o.hpRatio, 3).fill(0xd0d0d0);
      c.addChild(bar);
    }
    return c;
  }

  private unitSprite(u: UnitDraw): Container {
    const c = new Container();
    const center = tileCenter(u);
    c.position.set(center.x, center.y);
    c.alpha = u.downed ? 0.35 : 1;
    const r = T * 0.32;
    const g = new Graphics();
    if (u.summon) {
      // 召喚物（Phase 3D-4b）：菱形加青綠外框，和一般單位的圓形區別
      const d = r * 1.25;
      const diamond = [0, -d, d, 0, 0, d, -d, 0];
      g.poly(diamond).fill(u.fill).stroke({ width: 3, color: HIGHLIGHT.summon });
      if (u.active) g.poly([0, -d - 5, d + 5, 0, 0, d + 5, -d - 5, 0]).stroke({ width: 3, color: HIGHLIGHT.active });
    } else {
      g.circle(0, 0, r).fill(u.fill);
      if (u.hero) g.circle(0, 0, r + 2).stroke({ width: 2, color: HIGHLIGHT.hero });
      if (u.active) g.circle(0, 0, r + 5).stroke({ width: 3, color: HIGHLIGHT.active });
    }
    c.addChild(g);
    if (!u.downed) {
      // 朝向（Phase 3D-8d）：外緣的小三角形箭頭，尖端指向單位面對的方向
      const arrow = new Graphics().poly(facingArrow(u.facing, u.summon ? r * 1.25 : r)).fill(0xffffff).stroke({ width: 1, color: 0x000000 });
      c.addChild(arrow);
    }
    if (u.summon) {
      // 右上角小徽章：圖騰標「圖」，其他標剩餘輪數
      const badgeText = u.totem ? "圖" : String(u.remaining ?? "");
      const badge = new Graphics().circle(T * 0.3, -T * 0.3, 9).fill({ color: 0x000000, alpha: 0.75 }).stroke({ width: 1, color: HIGHLIGHT.summon });
      const badgeLabel = label(badgeText, 12, HIGHLIGHT.summon, true);
      badgeLabel.anchor.set(0.5);
      badgeLabel.position.set(T * 0.3, -T * 0.3);
      c.addChild(badge, badgeLabel);
    }
    const marker = label(u.marker, 18, 0xffffff, true);
    marker.anchor.set(0.5);
    c.addChild(marker);
    if (u.downed) this.addDownedMark(c, u, r);
    if (u.bomb !== null) this.addBombBadge(c, u.bomb);
    const w = T * 0.8;
    const bar = new Graphics().rect(-w / 2, T * 0.36, w, 5).fill(0x000000);
    bar.rect(-w / 2, T * 0.36, w * u.hpRatio, 5).fill(hpColor(u.hpRatio));
    if (u.shieldRatio > 0) bar.rect(-w / 2, T * 0.36 - 3, w * u.shieldRatio, 2).fill(0x9fd8ff);
    c.addChild(bar);
    return c;
  }

  /** 倒地標記（Phase 3D-8b）：紅色叉叉加「倒」徽章；可以被復活的另標「可復活」。 */
  private addDownedMark(c: Container, u: UnitDraw, r: number): void {
    const cross = new Graphics()
      .moveTo(-r, -r)
      .lineTo(r, r)
      .moveTo(r, -r)
      .lineTo(-r, r)
      .stroke({ width: 3, color: HIGHLIGHT.downed, alpha: 0.95 });
    const badge = new Graphics()
      .roundRect(-T * 0.46, -T * 0.46, 24, 16, 4)
      .fill({ color: 0x000000, alpha: 0.75 })
      .stroke({ width: 1, color: HIGHLIGHT.downed });
    const text = label(u.revivable ? "倒·復" : "倒", 11, HIGHLIGHT.downed, true);
    text.anchor.set(0.5);
    text.position.set(-T * 0.46 + 12, -T * 0.46 + 8);
    c.addChild(cross, badge, text);
  }

  /** 帶著定時炸彈的單位：右下角的徽章標還要幾次環境回合爆炸（Phase 3D-8b）。 */
  private addBombBadge(c: Container, rounds: number): void {
    const badge = new Graphics()
      .circle(T * 0.3, T * 0.12, 10)
      .fill({ color: 0x000000, alpha: 0.8 })
      .stroke({ width: 2, color: HIGHLIGHT.bomb });
    const text = label(`炸${rounds}`, 11, HIGHLIGHT.bomb, true);
    text.anchor.set(0.5);
    text.position.set(T * 0.3, T * 0.12);
    c.addChild(badge, text);
  }

  setHighlights(h: Highlights): void {
    if (!this.ready) return;
    clearLayer(this.highlights);
    clearLayer(this.hover);
    const g = new Graphics();
    for (const p of h.moves) {
      const o = tileOrigin(p);
      g.rect(o.x + 2, o.y + 2, T - 4, T - 4).fill({ color: HIGHLIGHT.move, alpha: 0.4 });
    }
    for (const p of h.preview) {
      const o = tileOrigin(p);
      g.rect(o.x + 1, o.y + 1, T - 2, T - 2).fill({ color: HIGHLIGHT.preview, alpha: 0.38 });
    }
    for (const m of h.telegraph) {
      const o = tileOrigin(m.pos);
      g.rect(o.x + 3, o.y + 3, T - 6, T - 6)
        .fill({ color: m.color, alpha: 0.16 })
        .stroke({ width: 2, color: m.color, alpha: 0.85 });
      const badge = new Graphics().circle(o.x + T - 11, o.y + 11, 9).fill({ color: 0x000000, alpha: 0.65 });
      const glyph = label(m.glyph, 12, m.color, true);
      glyph.anchor.set(0.5);
      glyph.position.set(o.x + T - 11, o.y + 11);
      this.highlights.addChild(badge, glyph);
    }
    const tags: Text[] = [];
    for (const o of h.overlays) {
      const tag = this.drawOverlay(g, o);
      if (tag !== null) tags.push(tag);
    }
    for (const p of h.picked) {
      const o = tileOrigin(p);
      g.rect(o.x + 1, o.y + 1, T - 2, T - 2)
        .fill({ color: HIGHLIGHT.picked, alpha: 0.25 })
        .stroke({ width: 4, color: HIGHLIGHT.picked });
    }
    for (const d of h.directions) {
      const o = tileOrigin(d.pos);
      g.rect(o.x + 2, o.y + 2, T - 4, T - 4).fill({ color: HIGHLIGHT.direction, alpha: 0.3 });
      const arrow = label(d.arrow, 26, HIGHLIGHT.direction, true);
      arrow.anchor.set(0.5);
      arrow.position.set(o.x + T / 2, o.y + T / 2);
      this.highlights.addChild(arrow);
    }
    for (const p of h.attacks) {
      const o = tileOrigin(p);
      g.rect(o.x + 2, o.y + 2, T - 4, T - 4).stroke({ width: 3, color: HIGHLIGHT.attack });
    }
    this.highlights.addChild(g);
    for (const tag of tags) this.highlights.addChild(tag); // 文字標記畫在所有色塊之上
    if (h.focus !== null) {
      const o = tileOrigin(h.focus);
      const frame = new Graphics()
        .rect(o.x + 1, o.y + 1, T - 2, T - 2)
        .stroke({ width: 3, color: HIGHLIGHT.trigger })
        .rect(o.x + 6, o.y + 6, T - 12, T - 12)
        .stroke({ width: 2, color: HIGHLIGHT.trigger, alpha: 0.8 });
      this.hover.addChild(frame);
    }
    if (h.hover !== null) {
      const o = tileOrigin(h.hover);
      const frame = new Graphics()
        .rect(o.x + 1, o.y + 1, T - 2, T - 2)
        .stroke({ width: 2, color: 0xffffff, alpha: 0.9 });
      this.hover.addChild(frame);
    }
  }

  /** 場景物件與自身位移預覽的一個標記（穿透路線、穿過的物件、後方單位、壓住的格子、倒塌物、投擲物件與
 * 落點，以及衝鋒路線、跳躍落點、交換位置的兩格）。 */
  private drawOverlay(g: Graphics, overlay: Overlay): Text | null {
    const color = OVERLAY_COLORS[overlay.kind];
    const o = tileOrigin(overlay.pos);
    const c = tileCenter(overlay.pos);
    switch (overlay.kind) {
      case "route":
      case "dash_path":
        g.circle(c.x, c.y, 6).fill({ color, alpha: 0.95 }).stroke({ width: 1, color: 0x000000, alpha: 0.6 });
        return null;
      case "crush":
        g.rect(o.x + 1, o.y + 1, T - 2, T - 2).fill({ color, alpha: 0.4 });
        g.moveTo(o.x + 4, o.y + T - 4).lineTo(o.x + T - 4, o.y + 4);
        g.moveTo(o.x + 4, o.y + T / 2).lineTo(o.x + T / 2, o.y + 4);
        g.moveTo(o.x + T / 2, o.y + T - 4).lineTo(o.x + T - 4, o.y + T / 2);
        g.stroke({ width: 2, color: 0xffffff, alpha: 0.5 });
        break;
      case "rubble":
        g.rect(o.x + 5, o.y + 5, T - 10, T - 10).stroke({ width: 3, color });
        break;
      case "behind":
        g.rect(o.x + 2, o.y + 2, T - 4, T - 4).stroke({ width: 3, color });
        break;
      case "summon_aura":
      case "bomb_blast":
        g.rect(o.x + 2, o.y + 2, T - 4, T - 4).fill({ color, alpha: 0.22 });
        break;
      case "pierced":
      case "hurl_from":
      case "hurl_to":
      case "dash_end":
      case "charge_hit":
      case "leap_to":
      case "swap":
      case "teleport_from":
      case "teleport_to":
      case "teleport_lethal":
      case "summon_at":
      case "summon_gone":
      case "bomb_at":
      case "revive_at":
        g.rect(o.x + 3, o.y + 3, T - 6, T - 6)
          .fill({ color, alpha: 0.18 })
          .stroke({ width: 3, color });
        break;
    }
    if (overlay.label === "") return null;
    const text = label(overlay.label, 13, 0xffffff, true);
    text.anchor.set(0, 1);
    text.position.set(o.x + 4, o.y + T - 3);
    text.style.stroke = { color: 0x000000, width: 3 };
    return text;
  }

  /** 依序播放移動動畫；`skip()` 為真時剩下的移動直接跳到終點。 */
  async animate(plan: readonly MoveAnim[], skip: () => boolean): Promise<void> {
    if (!this.ready) return;
    for (const m of plan) {
      const sprite = this.unitSprites.get(m.unitId);
      if (sprite === undefined) continue;
      const to = tileCenter(m.to);
      if (m.durationMs <= 0 || skip()) {
        sprite.position.set(to.x, to.y);
        continue;
      }
      await this.tween(sprite, tileCenter(m.from), to, m.durationMs, skip);
    }
  }

  private tween(
    sprite: Container,
    from: { x: number; y: number },
    to: { x: number; y: number },
    durationMs: number,
    skip: () => boolean,
  ): Promise<void> {
    return new Promise((resolve) => {
      let elapsed = 0;
      let done = false;
      const tick = (ticker: Ticker) => {
        elapsed += ticker.deltaMS;
        if (sprite.destroyed || skip() || elapsed >= durationMs) {
          finish();
          return;
        }
        const p = lerpPos(from, to, elapsed / durationMs);
        sprite.position.set(p.x, p.y);
      };
      const finish = () => {
        if (done) return;
        done = true;
        this.app.ticker.remove(tick);
        if (!sprite.destroyed) sprite.position.set(to.x, to.y);
        resolve();
      };
      this.app.ticker.add(tick);
      // 分頁在背景時 ticker 會停：保底計時，避免動畫卡住畫面。
      window.setTimeout(finish, durationMs + 300);
    });
  }
}
