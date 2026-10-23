// PixiJS 繪製：照著 `DrawModel` 畫格子、物件、陷阱、單位與高亮；移動動畫只是過場，
// 播放完由呼叫端以新的 `view` 重畫（以 `view` 為準）。
// 縮放（Phase 3-8）：場景一律以「模型像素」（每格 TILE_SIZE）繪製；放大縮小只改畫布的解析度
// （devicePixelRatio × 縮放）與 CSS 大小，文字與線條因此保持清晰。滑鼠事件不經過 Pixi，
// 由 `BattleCanvas` 以 DOM 座標換算（`battle/stageLayout.ts` 的 `clientToTile`）。
// 高度「整格抬高」（Phase 3-19）：場景放在 `world`（往下移畫布上方預留的高度），由北到南一排一排畫
// （`RowStack`），格子上的所有東西都依 `tileLift` 往上移；位移只從 `battle/elevation.ts` 來。
import { Application, Container, Graphics, Sprite, type Text, type Ticker } from "pixi.js";
import type { Pos } from "../api/types";
import type { FeedbackItem, FloatTone } from "../battle/feedback";
import { lerpPos, type MoveAnim, type MoveStyle } from "../battle/animation";
import type { DrawModel, ObjectDraw, TileDraw, TrapDraw, UnitDraw } from "../battle/drawModel";
import { zoneBadgeCell, zoneCellSpecs } from "../battle/zones";
import { TILE_SIZE } from "../battle/geometry";
import { scaledSize } from "../battle/stageLayout";
import {
  edgeMarks,
  heightAt,
  liftedCenter,
  liftedOrigin,
  occluded,
  stagePixels,
  tileLift,
  topReserve,
  type HeightShift,
} from "../battle/elevation";
import { HIGHLIGHT, surfaceBlocksSight } from "../battle/glossary";
import type { Overlay, OverlayKind } from "../battle/scenePreview";
import type { TelegraphMark } from "../battle/telegraph";
import { warpPlan, type StepVfx } from "../battle/vfx";
import { RING } from "./artPalette";
import type { Ctx } from "./artDraw";
import { drawCasterRing, drawTrapPad, drawZoneCell, fxColor, sightVeil, turnsBadge, veilKindOf } from "./fieldFx";
import { fontEpoch } from "./fontLoad";
import { ArtTextures } from "./artTextures";
import { heightBadgeText, objectArtSpec, objectKinds, tileArtSpec } from "./artSpecs";
import type { ArtTheme } from "./regionArt";
import { hasObjectArt } from "./objectArt";
import { blastEffect, castEffects, hitEffects, shakeEffect, warpEffects, type Effect } from "./vfxEffects";
import { drawCliff, drawEdges, liftEffects, silhouette } from "./heightArt";
import { RowStack } from "./rowLayers";
import { clearLayer, label } from "./labels";
import { buildUnitSprite, Pulses } from "./unitSprite";

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
  /** 攀跳模式（Phase 3-21b）：可攀爬或跳躍的落點（紫色，附「攀」「跳」字樣），與一般目標的紅框分開。 */
  vaults?: readonly { pos: Pos; kind: "climb" | "jump" }[];
}

const T = TILE_SIZE;
const BACKGROUND = 0x15151c;

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

/** 一格進行中的升降動畫。 */
interface LiftState {
  pos: Pos;
  /** 目前補間到的高度。 */
  h: number;
  to: number;
}

export class BattleRenderer {
  private readonly app = new Application();
  /** 整個場景（世界座標）；y ＝ 畫布上方預留的高度。震動只動 `stage`，不影響這個位移。 */
  private readonly world = new Container();
  /** 由北到南的每一排：地形與崖面、表面裝飾、物件、高度徽章、高亮、陷阱、單位。 */
  private readonly rows = new RowStack();
  /** 被南邊高格擋住的單位的虛線剪影（最上層）。 */
  private readonly silhouettes = new Container();
  private readonly silhouetteOf = new Map<string, Graphics>();
  /** 高亮（移動、預覽、目標框…）：畫在所有排之上，仍跟著所在格抬高，不被南邊的高格蓋住（3-18b）。 */
  private readonly marks = new Container();
  private readonly pulses = new Pulses();
  private readonly hover = new Container();
  private readonly effects = new Container();
  private effectList: Effect[] = [];
  private effectClock = 0;
  private effectTick: ((ticker: Ticker) => void) | null = null;
  private readonly unitSprites = new Map<string, Container>();
  /** 程式繪製的地形、物件貼圖快取（Phase 3-16a）。 */
  private readonly art = new ArtTextures();
  private model: DrawModel | null = null;
  /**
   * 進行中的升降動畫：格子 → 目前補間到的高度與目標。播放結束時常會再重畫一次（同樣的結果），
   * 目標高度沒變的動畫在重畫後接著播；目標變了（又有新的地形變化）就以新畫面為準。
   */
  private readonly lifting = new Map<string, LiftState>();
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
    stage.addChild(this.world);
    this.world.addChild(this.rows.root, this.marks, this.silhouettes, this.hover, this.effects);
    this.app.ticker.add((ticker) => this.pulses.tick(ticker.deltaMS));
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

  /** 畫布的繪製尺寸 ＝ 模型像素（含上方預留）；解析度 ＝ 裝置像素比 × 縮放；CSS 大小 ＝ 模型像素 × 縮放。 */
  private applySize(model: DrawModel): void {
    const size = stagePixels(model);
    this.world.y = topReserve(model);
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

  /** 格子的高度（地圖外 0）。 */
  private heightOf(p: Pos): number {
    return this.model === null ? 0 : heightAt(this.model, p);
  }

  /** 抬高後格子頂面的左上角、中心（世界座標）。 */
  private origin(p: Pos): { x: number; y: number } {
    return liftedOrigin(p, this.heightOf(p));
  }

  private center(p: Pos): { x: number; y: number } {
    return liftedCenter(p, this.heightOf(p));
  }

  /** 把節點放到格子 `p`（`x`、`y` 是未抬高的世界座標），跟著格子抬高。 */
  private place(node: Container, p: Pos, x: number, y: number): void {
    this.rows.place(node, p, x, y, tileLift(this.heightOf(p)));
  }

  draw(model: DrawModel): void {
    this.model = model;
    if (!this.ready) return;
    this.applySize(model);
    this.rows.reset(model.height);
    clearLayer(this.silhouettes);
    this.silhouetteOf.clear();
    this.unitSprites.clear();
    this.pulses.clear();
    this.art.beginFrame();
    for (const t of model.tiles) this.tileSprite(model, t);
    for (const a of model.auras) {
      const aura = new Graphics().rect(2, 2, T - 4, T - 4).fill({ color: HIGHLIGHT.summon, alpha: 0.14 });
      this.rows.row(a.y).deco.addChild(aura);
      this.place(aura, a, a.x * T, a.y * T);
    }
    this.drawZones(model);
    this.drawRunes(model);
    this.drawWells(model);
    this.drawMarkers(model);
    const kinds = objectKinds(model);
    for (const o of model.objects) {
      const node = this.objectSprite(o, kinds, { region: model.region, look: model.look });
      this.rows.row(o.y).objects.addChild(node);
      this.place(node, o, o.x * T, o.y * T);
    }
    this.drawBadges(model);
    for (const trap of model.traps) this.drawTrap(trap);
    for (const u of model.units) this.drawUnit(model, u);
    this.drawVeils(model);
    this.art.endFrame();
    this.resumeLifts(model);
  }

  /** 重畫後：目標高度沒變的升降動畫套回目前的高度繼續播，其餘作廢。 */
  private resumeLifts(model: DrawModel): void {
    for (const [key, st] of [...this.lifting]) {
      if (heightAt(model, st.pos) === st.to) this.rows.setLift(st.pos, tileLift(st.h));
      else this.lifting.delete(key);
    }
  }

  /** 一個單位：畫在所在排；被南邊高格擋住時另在最上層畫剪影。 */
  private drawUnit(model: DrawModel, u: UnitDraw): void {
    const sprite = buildUnitSprite(this.art, this.pulses, u);
    this.rows.row(u.y).units.addChild(sprite);
    this.place(sprite, u, u.x * T + T / 2, u.y * T + T / 2);
    if (!u.downed) this.unitSprites.set(u.id, sprite);
    if (!occluded(model, u)) return;
    const c = this.center(u);
    const ring = u.summon ? RING.summon : RING[u.team];
    const outline = silhouette(c.x, c.y + T * 0.23, ring.stroke, T);
    this.silhouettes.addChild(outline);
    this.silhouetteOf.set(u.id, outline);
  }

  /** 源泉格（Phase 3C-6a）：格子中央一顆紫色菱形，標「源」；單位站上去時才會被取用。 */
  private drawWells(model: DrawModel): void {
    for (const w of model.wells) {
      const node = new Container();
      const r = T * 0.26;
      node.addChild(
        new Graphics()
          .poly([0, -r, r, 0, 0, r, -r, 0])
          .fill({ color: HIGHLIGHT.well, alpha: 0.35 })
          .stroke({ width: 2, color: HIGHLIGHT.well, alpha: 0.95 }),
      );
      const mark = label("源", 14, HIGHLIGHT.well, true);
      mark.anchor.set(0.5);
      mark.style.stroke = { color: 0x000000, width: 3 };
      node.addChild(mark);
      this.rows.row(w.y).deco.addChild(node);
      this.place(node, w, w.x * T + T / 2, w.y * T + T / 2);
    }
  }

  /**
   * 符文（Phase 3-23）：菱形外框（刻下它的施放者的陣營色）＋菱形內紋與四個端點的短刻痕（元素色）；
   * 畫在格子上（跟著格子抬高），同一格有多個符文時各占一個象限、縮小。
   */
  private drawRunes(model: DrawModel): void {
    for (const r of model.runes) {
      const node = new Container();
      const multi = r.slots > 1;
      const half = multi ? T * 0.17 : T * 0.3;
      const alpha = r.fading ? 0.55 : 1;
      const dx = multi ? ((r.slot % 2) - 0.5) * T * 0.46 : 0;
      const dy = multi ? (Math.floor(r.slot / 2) % 2 === 0 ? -1 : 1) * T * 0.23 : 0;
      const diamond = (s: number): number[] => [0, -s, s, 0, 0, s, -s, 0];
      const g = new Graphics();
      g.poly(diamond(half)).fill({ color: r.color, alpha: 0.18 * alpha }).stroke({ width: 2, color: r.teamColor, alpha: 0.95 * alpha });
      g.poly(diamond(half * 0.5)).fill({ color: r.color, alpha: 0.75 * alpha });
      for (const [ux, uy] of [[0, -1], [1, 0], [0, 1], [-1, 0]] as const) {
        g.moveTo(ux * half * 0.62, uy * half * 0.62).lineTo(ux * half * 1.0, uy * half * 1.0);
      }
      g.stroke({ width: 1.5, color: r.color, alpha: 0.9 * alpha });
      node.addChild(g);
      this.rows.row(r.y).deco.addChild(node);
      this.place(node, r, r.x * T + T / 2 + dx, r.y * T + T / 2 + dy);
    }
  }

  /**
   * 勝利條件的目標格（Phase 3-22）：出口格是綠色的門形框加「出」，守點格是金色的雙圈加「守」；
   * 位置跟著格子抬高（`place`），畫在單位底下的裝飾層。
   */
  private drawMarkers(model: DrawModel): void {
    for (const m of model.markers) {
      const node = new Container();
      const color = m.kind === "exit" ? HIGHLIGHT.exit : HIGHLIGHT.point;
      const g = new Graphics();
      if (m.kind === "exit") {
        g.roundRect(3, 3, T - 6, T - 6, 6).fill({ color, alpha: 0.24 }).stroke({ width: 3, color, alpha: 0.95 });
        g.roundRect(9, 9, T - 18, T - 18, 4).stroke({ width: 1.5, color, alpha: 0.7 });
      } else {
        g.circle(T / 2, T / 2, T * 0.42).fill({ color, alpha: 0.2 }).stroke({ width: 3, color, alpha: 0.95 });
        g.circle(T / 2, T / 2, T * 0.28).stroke({ width: 1.5, color, alpha: 0.7 });
      }
      node.addChild(g);
      const mark = label(m.kind === "exit" ? "出" : "守", 14, color, true);
      mark.anchor.set(0.5);
      mark.position.set(T / 2, T / 2);
      mark.style.stroke = { color: 0x000000, width: 3 };
      node.addChild(mark);
      this.rows.row(m.y).deco.addChild(node);
      this.place(node, m, m.x * T, m.y * T);
    }
  }

  /** 一格大小的戰場效果貼圖（3-36b）；沒有 DOM 時為 `null`。 */
  private fxSprite(key: string, draw: (ctx: Ctx) => void): Sprite | null {
    const texture = this.art.fx(key, draw);
    if (texture === null) return null;
    const sprite = new Sprite(texture);
    sprite.width = T;
    sprite.height = T;
    return sprite;
  }

  /** 剩餘回合徽章（暫時物件、區域、延遲陷阱共用）：黑底圓形白字，最後 1 回合橘色。 */
  private badgeSprite(n: number, cx: number, cy: number): Sprite | null {
    const turns = Math.max(0, Math.min(99, Math.trunc(n)));
    return this.fxSprite(`badge|${turns}|${cx}|${cy}|${fontEpoch()}`, (ctx) => turnsBadge(ctx, cx, cy, turns));
  }

  /**
   * 持續區域（Phase 3D-5；3-36b 整塊一起畫）：每格底色＋（有害＝斜紋｜有益＝光點），只描區域外緣，
   * 移動型在前進側畫箭頭，跟隨型在施放者腳下畫虛線環，剩餘回合徽章在最左上那一格。
   */
  private drawZones(model: DrawModel): void {
    for (const z of model.zones) {
      const color = fxColor(z.element, z.surface);
      for (const c of zoneCellSpecs(z)) {
        const key = `zone|${color}|${z.effect}|${c.sides.join("")}|${c.arrow ?? "-"}|${c.phase}`;
        const sprite = this.fxSprite(key, (ctx) =>
          drawZoneCell(ctx, { color, harmful: z.harmful, neutral: z.effect === "none", sides: c.sides, arrow: c.arrow, phase: c.phase }),
        );
        if (sprite === null) continue;
        this.rows.row(c.y).deco.addChild(sprite);
        this.place(sprite, c, c.x * T, c.y * T);
      }
      if (z.caster !== null) {
        const ring = this.fxSprite(`ring|${color}`, (ctx) => drawCasterRing(ctx, color));
        if (ring !== null) {
          this.rows.row(z.caster.y).deco.addChild(ring);
          this.place(ring, z.caster, z.caster.x * T, z.caster.y * T);
        }
      }
      const first = zoneBadgeCell(z);
      const badge = first === null ? null : this.badgeSprite(z.turns, 9, 9);
      if (first !== null && badge !== null) {
        this.rows.row(first.y).deco.addChild(badge);
        this.place(badge, first, first.x * T, first.y * T);
      }
    }
  }

  /** 陷阱（3-36b）：地上一個圓形踏板；外圈＝陣營色，中央＝元素色的捕獸夾（enter）或沙漏（delay＋徽章）。 */
  private drawTrap(trap: TrapDraw): void {
    const color = fxColor(trap.element);
    const key = `trap|${+trap.mine}|${trap.trigger}|${color}|${fontEpoch()}`;
    const pad = this.fxSprite(key, (ctx) => drawTrapPad(ctx, { mine: trap.mine, trigger: trap.trigger, color }));
    if (pad === null) return;
    this.rows.row(trap.y).traps.addChild(pad);
    this.place(pad, trap, trap.x * T, trap.y * T);
    if (trap.trigger !== "delay") return;
    const badge = this.badgeSprite(trap.remaining, T - 9, 10);
    if (badge === null) return;
    this.rows.row(trap.y).traps.addChild(badge);
    this.place(badge, trap, trap.x * T, trap.y * T);
  }

  /** 擋視線的表面（`blocks_sight`，煙霧、黑暗…）：每格在單位之上多畫一層霧，蓋住單位下半身。 */
  private drawVeils(model: DrawModel): void {
    for (const t of model.tiles) {
      if (t.surface === "none" || !surfaceBlocksSight(t.surface)) continue;
      const kind = veilKindOf(t.surface);
      const sprite = this.fxSprite(`veil|${kind}|${t.x}|${t.y}`, (ctx) => sightVeil(ctx, kind, t.x, t.y));
      if (sprite === null) continue;
      this.rows.row(t.y).veil.addChild(sprite);
      this.place(sprite, t, t.x * T, t.y * T);
    }
  }

  /**
   * 地形格（Phase 3-16a）：崖面（3-19，頂面底下到地面）→ 程式繪製的頂面貼圖（地形＋高度明暗＋表面＋格線）
   * → 高格描邊 → 致命標記。崖面與描邊依抬高量重畫（升降動畫）。
   */
  private tileSprite(model: DrawModel, t: TileDraw): void {
    const c = new Container();
    const cliff = new Graphics();
    const edges = new Graphics();
    const marks = edgeMarks(model, t);
    const redraw = (lift: number) => {
      drawCliff(cliff, lift, T);
      drawEdges(edges, lift, marks, T);
    };
    c.addChild(cliff);
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
    c.addChild(edges);
    if (t.deadly) {
      g.rect(3, 3, T - 6, T - 6).stroke({ width: 1.5, color: HIGHLIGHT.deadly, alpha: 0.3 });
      g.moveTo(T * 0.3, T * 0.3).lineTo(T * 0.7, T * 0.7);
      g.moveTo(T * 0.7, T * 0.3).lineTo(T * 0.3, T * 0.7);
      g.stroke({ width: 1.5, color: HIGHLIGHT.deadly, alpha: 0.22 });
    }
    c.addChild(g);
    redraw(tileLift(t.height));
    this.rows.row(t.y).ground.addChild(c);
    this.rows.place(c, t, t.x * T, t.y * T, tileLift(t.height), redraw);
  }

  /** 高度徽章：只在高度 > 0 的格子左上角畫「▲N」（跟著頂面抬高）。 */
  private drawBadges(model: DrawModel): void {
    for (const t of model.tiles) {
      const text = heightBadgeText(model, t);
      if (text === null) continue;
      const node = new Container();
      const g = new Graphics();
      g.roundRect(3, 3, 19, 13, 4).fill({ color: 0x1e1812, alpha: 0.7 });
      g.poly([6, 13, 9.5, 6, 13, 13]).fill(0xfff3c4);
      const num = label(text, 10, 0xfff3c4, true);
      num.position.set(14, 4);
      node.addChild(g, num);
      this.rows.row(t.y).badges.addChild(node);
      this.place(node, t, t.x * T, t.y * T);
    }
  }

  private objectSprite(o: ObjectDraw, kinds: ReadonlyMap<string, string>, theme: ArtTheme): Container {
    const c = new Container();
    const g = new Graphics();
    const known = hasObjectArt(o.kind);
    const texture = this.art.object(objectArtSpec(o, kinds, theme));
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
      // 暫時障礙（Phase 3-11）：右上角剩餘回合徽章（3-36b：黑底圓形，最後 1 回合橘色）；
      // 有畫法的物件（冰牆、荊棘…）最後 1 回合的樣子由貼圖自己改（融化、枯萎），沒有畫法的才淡化。
      if (!hasSprite || !known) c.alpha = o.expiresIn <= 1 ? 0.5 : 0.8;
      const badge = this.badgeSprite(o.expiresIn, T - 8, 8);
      if (badge !== null) c.addChild(badge);
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

  /** 高亮畫在最上層（座標已含抬高）；所有色塊共用一個 Graphics，文字另外疊上。 */
  private markPen(): { at(p: Pos): Graphics; add(p: Pos, ...nodes: Container[]): void } {
    const g = new Graphics();
    this.marks.addChild(g);
    return {
      at: () => g,
      add: (_p, ...nodes) => {
        this.marks.addChild(...nodes);
      },
    };
  }

  setHighlights(h: Highlights): void {
    if (!this.ready) return;
    clearLayer(this.marks);
    clearLayer(this.hover);
    const pen = this.markPen();
    for (const p of h.moves) {
      const o = this.origin(p);
      pen.at(p).rect(o.x + 2, o.y + 2, T - 4, T - 4).fill({ color: HIGHLIGHT.move, alpha: 0.4 });
    }
    for (const p of h.preview) {
      const o = this.origin(p);
      pen.at(p).rect(o.x + 1, o.y + 1, T - 2, T - 2).fill({ color: HIGHLIGHT.preview, alpha: 0.38 });
    }
    for (const m of h.telegraph) {
      const o = this.origin(m.pos);
      pen
        .at(m.pos)
        .rect(o.x + 3, o.y + 3, T - 6, T - 6)
        .fill({ color: m.color, alpha: 0.16 })
        .stroke({ width: 2, color: m.color, alpha: 0.85 });
      const badge = new Graphics().circle(o.x + T - 11, o.y + 11, 9).fill({ color: 0x000000, alpha: 0.65 });
      const glyph = label(m.glyph, 12, m.color, true);
      glyph.anchor.set(0.5);
      glyph.position.set(o.x + T - 11, o.y + 11);
      pen.add(m.pos, badge, glyph);
    }
    const tags: Array<{ pos: Pos; text: Text }> = [];
    for (const o of h.overlays) {
      const tag = this.drawOverlay(pen.at(o.pos), o);
      if (tag !== null) tags.push({ pos: o.pos, text: tag });
    }
    for (const p of h.picked) {
      const o = this.origin(p);
      pen
        .at(p)
        .rect(o.x + 1, o.y + 1, T - 2, T - 2)
        .fill({ color: HIGHLIGHT.picked, alpha: 0.25 })
        .stroke({ width: 4, color: HIGHLIGHT.picked });
    }
    for (const d of h.directions) {
      const o = this.origin(d.pos);
      pen.at(d.pos).rect(o.x + 2, o.y + 2, T - 4, T - 4).fill({ color: HIGHLIGHT.direction, alpha: 0.3 });
      const arrow = label(d.arrow, 26, HIGHLIGHT.direction, true);
      arrow.anchor.set(0.5);
      arrow.position.set(o.x + T / 2, o.y + T / 2);
      pen.add(d.pos, arrow);
    }
    for (const v of h.vaults ?? []) {
      const o = this.origin(v.pos);
      pen.at(v.pos).rect(o.x + 2, o.y + 2, T - 4, T - 4).fill({ color: HIGHLIGHT.vault, alpha: 0.32 });
      pen.at(v.pos).rect(o.x + 2, o.y + 2, T - 4, T - 4).stroke({ width: 3, color: HIGHLIGHT.vault });
      const glyph = label(v.kind === "climb" ? "攀" : "跳", 24, HIGHLIGHT.vault, true);
      glyph.anchor.set(0.5);
      glyph.position.set(o.x + T / 2, o.y + T / 2);
      pen.add(v.pos, glyph);
    }
    for (const p of h.attacks) {
      const o = this.origin(p);
      pen.at(p).rect(o.x + 2, o.y + 2, T - 4, T - 4).stroke({ width: 3, color: HIGHLIGHT.attack });
    }
    for (const tag of tags) pen.add(tag.pos, tag.text); // 文字標記畫在色塊之上
    this.drawFrames(h.focus, h.hover);
  }

  /** 反應詢問的觸發者（洋紅雙框）與滑鼠所在格（白框），畫在最上層、跟著頂面抬高。 */
  private drawFrames(focus: Pos | null, hover: Pos | null): void {
    if (focus !== null) {
      const o = this.origin(focus);
      const frame = new Graphics()
        .rect(o.x + 1, o.y + 1, T - 2, T - 2)
        .stroke({ width: 3, color: HIGHLIGHT.trigger })
        .rect(o.x + 6, o.y + 6, T - 12, T - 12)
        .stroke({ width: 2, color: HIGHLIGHT.trigger, alpha: 0.8 });
      this.hover.addChild(frame);
    }
    if (hover !== null) {
      const o = this.origin(hover);
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
    const o = this.origin(overlay.pos);
    const c = this.center(overlay.pos);
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
      const outline = this.silhouetteOf.get(m.unitId);
      if (outline !== undefined) outline.visible = false; // 剪影留在原位會誤導；重畫時再依新位置判斷
      const to = this.center(m.to);
      if (m.durationMs <= 0 || skip()) {
        sprite.position.set(to.x, to.y);
        continue;
      }
      this.launch(warpEffects(warpPlan(m), this.effectClock, (p) => this.center(p))); // 傳送：起點消散、終點出現
      await this.tween(sprite, this.center(m.from), to, m.durationMs, skip, m.style);
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
    this.launch(items.map((item) => this.makeEffect(item, now, durationMs)));
  }

  /** 把一組效果放進效果圖層並啟動效果迴圈。 */
  private launch(effects: readonly Effect[]): void {
    for (const e of effects) {
      this.effects.addChild(e.node);
      this.effectList.push(e);
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
    const effects: Effect[] = [];
    const auraHits = vfx.casts.some((c) => c.kind === "aura");
    const at = (p: Pos) => this.center(p);
    for (const cast of vfx.casts) effects.push(...castEffects(cast, now, impactMs, at));
    for (const hit of vfx.hits) effects.push(...hitEffects(hit, now, impactMs, auraHits, at));
    for (const blast of vfx.blasts) effects.push(blastEffect(blast, now, impactMs, at));
    if (shake && vfx.shake > 0 && vfx.hits.length > 0) {
      const first = Math.min(...vfx.hits.map((h) => h.atMs));
      const stage = this.app.stage;
      effects.push(shakeEffect(vfx.shake === 2 ? 2 : 1, now + first, impactMs * (vfx.shake === 2 ? 0.55 : 0.35), (x, y) => stage.position.set(x, y)));
    }
    this.launch(effects);
  }

  /**
   * 地形升降動畫（Phase 3-19）：呼叫前已用新的 `view` 重畫（以結果為準），這裡把變動的格子先放回舊高度，
   * 再以 ease-out 補間到新高度（格上的物件、單位一起移動）；升起時碎土＋輕微震動（`shake` 為假時不震），
   * 下降結束時一圈塵土。`durationMs` 已依播放速度縮放；`skip()` 為真時直接跳到結果。
   */
  playLift(shifts: readonly HeightShift[], durationMs: number, shake: boolean, skip: () => boolean): void {
    const model = this.model;
    if (!this.ready || model === null || durationMs <= 0 || shifts.length === 0 || skip()) return;
    const now = this.effectClock;
    const effects: Effect[] = [];
    for (const s of shifts) {
      const shift = { ...s, to: heightAt(model, s.pos) };
      const key = `${s.pos.x},${s.pos.y}`;
      const state: LiftState = { pos: shift.pos, h: shift.from, to: shift.to };
      this.lifting.set(key, state);
      const apply = (h: number) => {
        if (this.lifting.get(key) !== state) return; // 已被新的畫面或新的動畫取代
        state.h = h;
        this.rows.setLift(shift.pos, tileLift(h));
        if (h === shift.to) this.lifting.delete(key);
      };
      apply(shift.from);
      const origin = (h: number) => liftedOrigin(shift.pos, h);
      effects.push(...liftEffects({ shift, now, durationMs, origin, apply, skip, size: T }));
    }
    if (shake && shifts.some((s) => heightAt(model, s.pos) > s.from)) {
      const stage = this.app.stage;
      effects.push(shakeEffect(1, now, durationMs * 0.6, (x, y) => stage.position.set(x * 0.6, y * 0.6)));
    }
    this.launch(effects);
  }

  private makeEffect(item: FeedbackItem, now: number, durationMs: number): Effect {
    if (item.kind === "line") return this.lineEffect(item.from, item.to, now, durationMs);
    const c = this.center(item.pos);
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
    const a = this.center(from);
    const b = this.center(to);
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
