// PixiJS 繪製：照著 `DrawModel` 畫格子、物件、陷阱、單位與高亮；移動動畫只是過場，
// 播放完由呼叫端以新的 `view` 重畫（以 `view` 為準）。
// 縮放（Phase 3-8）：場景一律以「模型像素」（每格 TILE_SIZE）繪製；放大縮小只改畫布的解析度
// （devicePixelRatio × 縮放）與 CSS 大小，文字與線條因此保持清晰。滑鼠事件不經過 Pixi，
// 由 `BattleCanvas` 以 DOM 座標換算（`battle/stageLayout.ts` 的 `clientToTile`）。
import { Application, Container, Graphics, Sprite, Text, type Ticker } from "pixi.js";
import type { Pos } from "../api/types";
import type { FeedbackItem, FloatTone } from "../battle/feedback";
import { lerpPos, type MoveAnim, type MoveStyle } from "../battle/animation";
import type { DrawModel, ObjectDraw, TileDraw, UnitDraw } from "../battle/drawModel";
import { ringArrow } from "../battle/facing";
import { canvasSize, TILE_SIZE, tileCenter, tileOrigin } from "../battle/geometry";
import { scaledSize } from "../battle/stageLayout";
import { HIGHLIGHT } from "../battle/glossary";
import type { Overlay, OverlayKind } from "../battle/scenePreview";
import type { TelegraphMark } from "../battle/telegraph";
import { VFX_TIMING, type StepVfx } from "../battle/vfx";
import { tileAt } from "../battle/drawModel";
import { heightDecor, pedestalScale } from "../battle/heightModel";
import { RING } from "./artPalette";
import { ArtTextures } from "./artTextures";
import { resolveDoll } from "./appearance";
import { DOLL_FOOT_Y, DOLL_H, DOLL_W } from "./paperdoll";
import { heightBadgeText, objectArtSpec, objectKinds, tileArtSpec } from "./artSpecs";
import { hasObjectArt } from "./objectArt";
import { castEffects, hitEffects, shakeEffect, type Effect } from "./vfxEffects";

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
  followup_area: HIGHLIGHT.followup,
};

const FLOAT_COLORS: Readonly<Record<FloatTone, number>> = {
  damage: 0xff4d4d,
  heal: 0x4cd964,
  shield: 0x9fd8ff,
  text: 0xffffff,
  bad: 0xff9f43,
  good: 0xffe066,
};
const LINE_COLOR = 0xfff1a8;
const STATUS_COLOR = 0xd9a0ff;

function hpColor(ratio: number): number {
  if (ratio > 0.5) return 0x4cd964;
  if (ratio > 0.25) return 0xffcc00;
  return 0xff3b30;
}

export class BattleRenderer {
  private readonly app = new Application();
  private readonly tiles = new Container();
  /** 高度裝飾（側面、懸崖線、投影），畫在地形之上、其他圖層之下。 */
  private readonly cliffs = new Container();
  private readonly auras = new Container();
  private readonly zones = new Container();
  private readonly highlights = new Container();
  private readonly objects = new Container();
  /** 高度徽章「▲N」，畫在物件之上。 */
  private readonly badges = new Container();
  private readonly traps = new Container();
  private readonly units = new Container();
  private readonly hover = new Container();
  private readonly effects = new Container();
  private effectList: Effect[] = [];
  private effectClock = 0;
  private effectTick: ((ticker: Ticker) => void) | null = null;
  private readonly unitSprites = new Map<string, Container>();
  /** 程式繪製的地形、物件貼圖快取（Phase 3-16a）。 */
  private readonly art = new ArtTextures();
  private model: DrawModel | null = null;
  private ready = false;
  private destroyed = false;
  /** 畫面上的縮放比例（1 ＝ 每格 TILE_SIZE 個 CSS 像素）。 */
  private scale = 1;

  async init(host: HTMLElement): Promise<void> {
    await this.app.init({
      width: 8 * T,
      height: 8 * T,
      background: BACKGROUND,
      antialias: true,
      resolution: window.devicePixelRatio || 1,
      autoDensity: false,
    });
    if (this.destroyed) {
      this.app.destroy(true, { children: true });
      return;
    }
    host.appendChild(this.app.canvas);
    const stage = this.app.stage;
    stage.addChild(this.tiles, this.cliffs, this.auras, this.zones, this.objects, this.badges, this.highlights, this.traps, this.units, this.hover, this.effects);
    stage.eventMode = "none";
    this.app.canvas.style.display = "block";
    this.ready = true;
    if (this.model !== null) this.draw(this.model);
  }

  destroy(): void {
    this.destroyed = true;
    for (const e of this.effectList) e.end?.();
    this.effectList = [];
    if (this.ready) this.app.destroy(true, { children: true });
    this.art.destroy();
    this.ready = false;
  }

  /** 設定畫面上的縮放比例（由可用空間算出）；畫布大小與解析度立即更新，場景不必重畫。 */
  setScale(scale: number): void {
    if (!(scale > 0)) return;
    this.scale = scale;
    if (this.ready && this.model !== null) this.applySize(this.model);
  }

  /** 畫布的繪製尺寸 ＝ 模型像素；解析度 ＝ 裝置像素比 × 縮放；CSS 大小 ＝ 模型像素 × 縮放。 */
  private applySize(model: DrawModel): void {
    const size = canvasSize(model);
    const resolution = (window.devicePixelRatio || 1) * this.scale;
    const r = this.app.renderer;
    if (r.screen.width !== size.width || r.screen.height !== size.height || r.resolution !== resolution) {
      r.resize(size.width, size.height, resolution);
    }
    const shown = scaledSize(model, this.scale);
    const style = this.app.canvas.style;
    style.width = `${shown.width}px`;
    style.height = `${shown.height}px`;
  }

  draw(model: DrawModel): void {
    this.model = model;
    if (!this.ready) return;
    this.applySize(model);
    clearLayer(this.tiles);
    clearLayer(this.cliffs);
    clearLayer(this.auras);
    clearLayer(this.zones);
    clearLayer(this.objects);
    clearLayer(this.badges);
    clearLayer(this.traps);
    clearLayer(this.units);
    this.unitSprites.clear();
    this.art.beginFrame();
    for (const t of model.tiles) this.tiles.addChild(this.tileSprite(model, t));
    this.drawHeight(model);
    const aura = new Graphics();
    for (const a of model.auras) {
      const o = tileOrigin(a);
      aura.rect(o.x + 2, o.y + 2, T - 4, T - 4).fill({ color: HIGHLIGHT.summon, alpha: 0.14 });
    }
    this.auras.addChild(aura);
    this.drawZones(model);
    this.drawWells(model);
    const kinds = objectKinds(model);
    for (const o of model.objects) this.objects.addChild(this.objectSprite(o, kinds));
    this.drawBadges(model);
    for (const trap of model.traps) {
      const c = tileCenter(trap);
      const glyph = label(trap.revealed ? "×" : "^", 22, trap.color, true);
      glyph.anchor.set(0.5);
      glyph.position.set(c.x + T * 0.28, c.y + T * 0.22);
      this.traps.addChild(glyph);
    }
    for (const u of model.units) {
      const sprite = this.unitSprite(u, tileAt(model, u)?.height ?? 0);
      this.units.addChild(sprite);
      if (!u.downed) this.unitSprites.set(u.id, sprite);
    }
    this.art.endFrame();
  }

  /** 源泉格（Phase 3C-6a）：格子中央一顆紫色菱形，標「源」；單位站上去時才會被取用。 */
  private drawWells(model: DrawModel): void {
    const g = new Graphics();
    for (const w of model.wells) {
      const c = tileCenter(w);
      const r = T * 0.26;
      g.poly([c.x, c.y - r, c.x + r, c.y, c.x, c.y + r, c.x - r, c.y])
        .fill({ color: HIGHLIGHT.well, alpha: 0.35 })
        .stroke({ width: 2, color: HIGHLIGHT.well, alpha: 0.95 });
    }
    this.auras.addChild(g);
    for (const w of model.wells) {
      const c = tileCenter(w);
      const mark = label("源", 14, HIGHLIGHT.well, true);
      mark.anchor.set(0.5);
      mark.position.set(c.x, c.y);
      mark.style.stroke = { color: 0x000000, width: 3 };
      this.auras.addChild(mark);
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

  /** 地形格（Phase 3-16a）：一張程式繪製的貼圖（地形＋高度明暗＋表面＋陰影＋崖面＋格線）；致命標記疊在上面。 */
  private tileSprite(model: DrawModel, t: TileDraw): Container {
    const c = new Container();
    const o = tileOrigin(t);
    c.position.set(o.x, o.y);
    const texture = this.art.tile(tileArtSpec(model, t));
    const g = new Graphics();
    if (texture !== null) {
      const sprite = new Sprite(texture);
      sprite.width = T;
      sprite.height = T;
      c.addChild(sprite);
    } else {
      g.rect(0, 0, T, T).fill(t.fill).stroke({ width: 1, color: 0x000000, alpha: 0.35 }); // 無法產生貼圖：退回色塊
    }
    if (t.deadly) {
      g.rect(3, 3, T - 6, T - 6).stroke({ width: 1.5, color: HIGHLIGHT.deadly, alpha: 0.3 });
      g.moveTo(T * 0.3, T * 0.3).lineTo(T * 0.7, T * 0.7);
      g.moveTo(T * 0.7, T * 0.3).lineTo(T * 0.3, T * 0.7);
      g.stroke({ width: 1.5, color: HIGHLIGHT.deadly, alpha: 0.22 });
    }
    c.addChild(g);
    return c;
  }

  /** 高度徽章：只在高度 > 0 的格子左上角畫「▲N」。 */
  private drawBadges(model: DrawModel): void {
    for (const t of model.tiles) {
      const text = heightBadgeText(model, t);
      if (text === null) continue;
      const o = tileOrigin(t);
      const g = new Graphics();
      g.roundRect(o.x + 3, o.y + 3, 19, 13, 4).fill({ color: 0x1e1812, alpha: 0.7 });
      g.poly([o.x + 6, o.y + 13, o.x + 9.5, o.y + 6, o.x + 13, o.y + 13]).fill(0xfff3c4);
      const num = label(text, 10, 0xfff3c4, true);
      num.position.set(o.x + 14, o.y + 4);
      this.badges.addChild(g, num);
    }
  }

  /** 高度的懸崖線（Phase 3-14；高度差 ≥ 2 的邊緣）；側面、投影、崖面已畫進地形貼圖（3-16a）。 */
  private drawHeight(model: DrawModel): void {
    const decor = heightDecor(model);
    const g = new Graphics();
    for (const c of decor.cliffs) {
      const x = c.x * T;
      const y = c.y * T;
      const w = c.diff >= 3 ? 4 : 3;
      switch (c.side) {
        case "south":
          g.rect(x, y + T - w, T, w);
          break;
        case "north":
          g.rect(x, y, T, w);
          break;
        case "east":
          g.rect(x + T - w, y, w, T);
          break;
        case "west":
          g.rect(x, y, w, T);
          break;
      }
      g.fill({ color: 0x1c140c, alpha: 0.75 });
    }
    this.cliffs.addChild(g);
  }

  private objectSprite(o: ObjectDraw, kinds: ReadonlyMap<string, string>): Container {
    const c = new Container();
    const origin = tileOrigin(o);
    c.position.set(origin.x, origin.y);
    const g = new Graphics();
    const known = hasObjectArt(o.kind);
    const texture = this.art.object(objectArtSpec(o, kinds));
    const hasSprite = texture !== null;
    if (hasSprite) {
      const node = new Sprite(texture);
      node.width = T;
      node.height = T;
      if (o.floor) node.alpha = 0.95;
      c.addChild(node);
    } else if (o.floor) {
      g.rect(2, 2, T - 4, T - 4).fill({ color: o.fill, alpha: 0.75 });
    } else {
      g.roundRect(T * 0.18, T * 0.18, T * 0.64, T * 0.64, 6).fill(o.fill);
    }
    if (o.burning) {
      g.rect(1, 1, T - 2, T - 2).stroke({ width: 3, color: HIGHLIGHT.burning });
    } else if (o.flammable && !hasSprite) {
      g.circle(T - 8, 8, 4).fill(HIGHLIGHT.flammable);
    }
    c.addChild(g);
    if (o.expiresIn !== null) {
      // 暫時障礙（Phase 3-11）：淡化並在右上角顯示剩餘回合；最後一輪更淡
      c.alpha = o.expiresIn <= 1 ? 0.5 : 0.8;
      const badge = label(String(o.expiresIn), 12, 0xffffff, true);
      badge.anchor.set(1, 0);
      badge.position.set(T - 3, 2);
      c.addChild(new Graphics().circle(T - 10, 10, 9).fill({ color: 0x1a2a3a, alpha: 0.85 }));
      c.addChild(badge);
    }
    if (!hasSprite || !known || o.burning) {
      const glyph = label(o.burning ? (hasSprite && known ? "火" : `${o.glyph}火`) : o.glyph, o.floor ? 12 : 16, 0xffffff, true);
      glyph.anchor.set(0.5);
      glyph.position.set(T / 2, o.floor ? T - 10 : T / 2);
      glyph.style.stroke = { color: 0x000000, width: 3 };
      c.addChild(glyph);
    }
    if (o.hpRatio !== null && o.hpRatio < 1 && !o.floor) {
      const bar = new Graphics().rect(T * 0.18, T * 0.84, T * 0.64, 3).fill(0x000000);
      bar.rect(T * 0.18, T * 0.84, T * 0.64 * o.hpRatio, 3).fill(0xd0d0d0);
      c.addChild(bar);
    }
    return c;
  }

  private unitSprite(u: UnitDraw, standingHeight: number): Container {
    const c = new Container();
    const center = tileCenter(u);
    c.position.set(center.x, center.y);
    c.alpha = u.downed ? 0.35 : 1;
    const r = T * 0.32;
    const pedestal = pedestalScale(standingHeight);
    if (pedestal > 0) {
      // 站在高處：腳下一圈底座陰影（越高越大、越深）
      const base = new Graphics();
      base.ellipse(0, r * 0.72, r * 1.15 * pedestal, r * 0.5 * pedestal).fill({ color: 0x000000, alpha: 0.28 + 0.05 * standingHeight });
      base.ellipse(0, r * 0.72, r * 0.8 * pedestal, r * 0.32 * pedestal).fill({ color: 0x000000, alpha: 0.25 });
      c.addChild(base);
    }
    // 圖層（移植需求 4.1/2）：底圈 → 朝向尖角 → 行動中虛線圈 → 小人 → 代號小標 → 血條 → 徽章
    const ring = u.summon ? RING.summon : RING[u.team];
    const feet = T * 0.23; // 腳底（相對格子中心）
    const cy = feet - 1;
    const rx = T * 0.36;
    const ry = T * 0.15;
    const g = new Graphics();
    g.ellipse(0, cy, rx, ry).fill({ color: ring.fill, alpha: 0.8 }).stroke({ width: 1.5, color: ring.stroke });
    if (u.hero) g.ellipse(0, cy, rx + 2.5, ry + 2).stroke({ width: 2, color: HIGHLIGHT.hero });
    c.addChild(g);
    if (!u.downed) c.addChild(new Graphics().poly(ringArrow(u.facing, 0, cy, rx, ry, 5)).fill(0xffffff).stroke({ width: 1, color: 0x000000 }));
    if (u.active) c.addChild(this.dashedEllipse(cy, rx + 6, ry + 4, HIGHLIGHT.active));
    const spec = resolveDoll({ template: u.template, team: u.team, summon: u.summon, totem: u.totem, weaponId: u.weaponId });
    const texture = this.art.figure(spec, u.facing, u.downed);
    if (texture !== null) {
      const doll = new Sprite(texture);
      const k = T / 52; // 身高約 46px 在 52px 格子裡縮放 1.0
      doll.anchor.set(0.5, DOLL_FOOT_Y / DOLL_H);
      doll.width = DOLL_W * k;
      doll.height = DOLL_H * k;
      doll.position.set(0, feet);
      c.addChild(doll);
    } else {
      c.addChild(new Graphics().circle(0, 0, r).fill(u.fill)); // 無法產生貼圖：退回色塊
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
    const tag = new Graphics().circle(-T * 0.37, T * 0.22, 8).fill({ color: 0x000000, alpha: 0.78 }).stroke({ width: 1.5, color: ring.stroke });
    const marker = label(u.marker, 12, 0xffffff, true);
    marker.anchor.set(0.5);
    marker.position.set(-T * 0.37, T * 0.22);
    c.addChild(tag, marker);
    if (u.downed) this.addDownedMark(c, u, T * 0.16);
    if (u.bomb !== null) this.addBombBadge(c, u.bomb);
    if (u.charge != null) this.addChargeBadge(c, u.charge);
    const w = T * 0.8;
    const bar = new Graphics().rect(-w / 2, T * 0.36, w, 5).fill(0x000000);
    bar.rect(-w / 2, T * 0.36, w * u.hpRatio, 5).fill(hpColor(u.hpRatio));
    if (u.shieldRatio > 0) bar.rect(-w / 2, T * 0.36 - 3, w * u.shieldRatio, 2).fill(0x9fd8ff);
    c.addChild(bar);
    return c;
  }

  /** 橢圓虛線圈（行動中）：以短線段交錯畫出。 */
  private dashedEllipse(cy: number, rx: number, ry: number, color: number): Graphics {
    const g = new Graphics();
    const n = 28;
    for (let i = 0; i < n; i += 2) {
      const a0 = (i / n) * Math.PI * 2;
      const a1 = ((i + 1) / n) * Math.PI * 2;
      g.moveTo(Math.cos(a0) * rx, cy + Math.sin(a0) * ry).lineTo(Math.cos(a1) * rx, cy + Math.sin(a1) * ry);
    }
    return g.stroke({ width: 2.5, color });
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

  /** 蓄力中的單位（延遲段，Phase 3F-4b）：左下角的徽章標還要幾回合釋放。 */
  private addChargeBadge(c: Container, rounds: number): void {
    const badge = new Graphics()
      .circle(-T * 0.37, -T * 0.2, 10)
      .fill({ color: 0x000000, alpha: 0.8 })
      .stroke({ width: 2, color: HIGHLIGHT.followup });
    const text = label(`蓄${rounds}`, 11, HIGHLIGHT.followup, true);
    text.anchor.set(0.5);
    text.position.set(-T * 0.37, -T * 0.2);
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
      case "followup_area":
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
      await this.tween(sprite, tileCenter(m.from), to, m.durationMs, skip, m.style);
    }
  }

  private tween(
    sprite: Container,
    from: { x: number; y: number },
    to: { x: number; y: number },
    durationMs: number,
    skip: () => boolean,
    style: MoveStyle,
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
        const t = elapsed / durationMs;
        if (style === "fade") {
          // 前半在原地淡出，後半在新位置淡入
          sprite.position.set(t < 0.5 ? from.x : to.x, t < 0.5 ? from.y : to.y);
          sprite.alpha = Math.abs(t - 0.5) * 2;
          return;
        }
        const p = lerpPos(from, to, t);
        sprite.position.set(p.x, p.y);
      };
      const finish = () => {
        if (done) return;
        done = true;
        this.app.ticker.remove(tick);
        if (!sprite.destroyed) {
          sprite.position.set(to.x, to.y);
          sprite.alpha = 1;
        }
        resolve();
      };
      this.app.ticker.add(tick);
      // 分頁在背景時 ticker 會停：保底計時，避免動畫卡住畫面。
      window.setTimeout(finish, durationMs + 300);
    });
  }

  /**
   * 播放一步的地圖回饋（浮動數字、字樣、行動連線、狀態彈出）；不等待結束，效果畫在獨立的圖層，
   * 場景重畫不會清掉。`durationMs` 是整組回饋的時間（已依播放速度縮放）。
   */
  playFeedback(items: readonly FeedbackItem[], durationMs: number): void {
    if (!this.ready || durationMs <= 0) return;
    const now = this.effectClock;
    for (const item of items) {
      const effect = this.makeEffect(item, now, durationMs);
      this.effects.addChild(effect.node);
      this.effectList.push(effect);
    }
    this.ensureEffectTick();
  }

  /**
   * 播放一步的技能特效（Phase 3-12）：蓄力、飛行物或光束、命中爆發、受擊閃白與震動。不等待結束；
   * 描述內的時間已依播放速度縮放，`impactMs` 是命中後爆發的時間。`shake` 為假時不震動（版面設定）。
   */
  playVfx(vfx: StepVfx, impactMs: number, shake: boolean): void {
    if (!this.ready || impactMs <= 0) return;
    const now = this.effectClock;
    const scale = impactMs / VFX_TIMING.impact;
    const chargeMs = Math.round(VFX_TIMING.charge * scale);
    const effects: Effect[] = [];
    const auraHits = vfx.casts.some((c) => c.kind === "aura");
    for (const cast of vfx.casts) effects.push(...castEffects(cast, now, impactMs, chargeMs));
    for (const hit of vfx.hits) effects.push(...hitEffects(hit, now, impactMs, auraHits));
    if (shake && vfx.shake > 0 && vfx.hits.length > 0) {
      const first = Math.min(...vfx.hits.map((h) => h.atMs));
      const stage = this.app.stage;
      effects.push(shakeEffect(vfx.shake === 2 ? 2 : 1, now + first, impactMs * (vfx.shake === 2 ? 0.55 : 0.35), (x, y) => stage.position.set(x, y)));
    }
    for (const e of effects) {
      this.effects.addChild(e.node);
      this.effectList.push(e);
    }
    this.ensureEffectTick();
  }

  private makeEffect(item: FeedbackItem, now: number, durationMs: number): Effect {
    if (item.kind === "line") return this.lineEffect(item.from, item.to, now, durationMs);
    const c = tileCenter(item.pos);
    const delay = item.slot * durationMs * 0.15;
    const isStatus = item.kind === "status";
    const text = isStatus ? `＋${item.text}` : item.text;
    const color = isStatus ? STATUS_COLOR : FLOAT_COLORS[item.tone];
    const big = item.kind === "float" && item.big;
    const node = new Container();
    const t = label(text, big ? 30 : 20, color, true);
    t.anchor.set(0.5);
    t.style.stroke = { color: 0x000000, width: 4 };
    node.addChild(t);
    const baseY = c.y - T * 0.3 - item.slot * 22;
    node.position.set(c.x + (isStatus ? T * 0.12 : 0), baseY);
    node.alpha = 0;
    if (isStatus) {
      // 狀態：格子先閃一圈光環
      const ring = new Graphics().circle(0, T * 0.3, T * 0.4).stroke({ width: 3, color: STATUS_COLOR });
      node.addChildAt(ring, 0);
    }
    return {
      node,
      startMs: now + delay,
      endMs: now + durationMs,
      update: (p) => {
        node.alpha = p < 0.7 ? 1 : 1 - (p - 0.7) / 0.3;
        node.position.y = baseY - Math.min(1, p * 1.5) * (big ? 22 : 16);
        const pop = big ? 1 + 0.35 * Math.max(0, 1 - p * 5) : 1;
        node.scale.set(pop);
      },
    };
  }

  private lineEffect(from: Pos, to: Pos, now: number, durationMs: number): Effect {
    const a = tileCenter(from);
    const b = tileCenter(to);
    const angle = Math.atan2(b.y - a.y, b.x - a.x);
    const head = 10;
    const g = new Graphics()
      .moveTo(a.x, a.y)
      .lineTo(b.x, b.y)
      .stroke({ width: 4, color: LINE_COLOR })
      .poly([
        b.x,
        b.y,
        b.x - head * Math.cos(angle - 0.45),
        b.y - head * Math.sin(angle - 0.45),
        b.x - head * Math.cos(angle + 0.45),
        b.y - head * Math.sin(angle + 0.45),
      ])
      .fill(LINE_COLOR);
    const node = new Container();
    node.addChild(g);
    node.alpha = 0;
    return {
      node,
      startMs: now,
      endMs: now + durationMs * 0.6,
      update: (p) => {
        node.alpha = p < 0.4 ? 0.95 : 0.95 * (1 - (p - 0.4) / 0.6);
      },
    };
  }

  private ensureEffectTick(): void {
    if (this.effectTick !== null) return;
    const tick = (ticker: Ticker) => {
      this.effectClock += ticker.deltaMS;
      const alive: Effect[] = [];
      for (const e of this.effectList) {
        if (this.effectClock >= e.endMs) {
          e.end?.();
          e.node.destroy({ children: true });
          continue;
        }
        if (this.effectClock >= e.startMs) e.update((this.effectClock - e.startMs) / (e.endMs - e.startMs));
        alive.push(e);
      }
      this.effectList = alive;
      if (alive.length === 0) {
        this.app.ticker.remove(tick);
        this.effectTick = null;
      }
    };
    this.effectTick = tick;
    this.app.ticker.add(tick);
  }
}
