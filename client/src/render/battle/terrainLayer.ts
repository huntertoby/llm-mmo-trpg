// 地形與格子上的東西（R1e 自 `BattleRenderer.ts` 拆出，純搬移）：地形格、崖面、區域、陷阱、符文、源泉、目標格、出口、
// 薄霧、擋視線的霧、高度徽章、物件與可燃標記；地表動畫、環境動態、實地外觀的 host。
import { Container, Graphics, Sprite } from "pixi.js";
import type { DrawModel, ObjectDraw, TileDraw, TrapDraw } from "../../battle/drawModel";
import { zoneBadgeCell, zoneCellSpecs } from "../../battle/zones";
import { TILE_SIZE } from "../../battle/geometry";
import { edgeMarks, heightAt, tileLift } from "../../battle/elevation";
import { HIGHLIGHT, surfaceBlocksSight } from "../../battle/glossary";
import type { Ctx } from "../artDraw";
import { drawCasterRing, drawTrapPad, drawZoneCell, fxColor, sightVeil, turnsBadge, veilKindOf } from "../fieldFx";
import { fontEpoch } from "../fontLoad";
import { heightBadgeText, objectArtSpec, tileArtSpec } from "../artSpecs";
import { drawMistTile } from "../cloudRidgeTerrain";
import { mistLevel, type ArtTheme } from "../regionArt";
import { hasFlammableMark, hasObjectArt } from "../objectArt";
import { drawCliff, drawEdges } from "../heightArt";
import { label } from "../labels";
import { drawExitGlow, drawExitSign } from "../exitSign";
import { HEIGHT_BADGE_LABEL, MIN_HEIGHT_BADGE_FONT_PX, registerMark } from "../minMark";
import { HEIGHT_MARK_BG, HEIGHT_MARK_NUM, HEIGHT_MARK_TRI, heightMarkAtCorner, heightMarkCornerDrop, markedTileFree } from "../heightMark";
import type { AmbientHost } from "../ambientLayer";
import { SUBMERGED_ALPHA, SUBMERGED_TINT, waterline, WATERLINE_ALPHA, WATERLINE_COLOR } from "../submerged";
import { drawLethalCorners, lethalCornersOf } from "../lethalMarks";
import type { SceneryHost } from "../sceneryLayer";
import type { SurfaceHost } from "../surfaceAnimLayer";
import { RendererBase } from "./rendererBase";
import { POOL_JOINT, POOL_RIPPLE, POOL_SLAB, POOL_SLAB_LIGHT, POOL_WATER, PRACTICE_INK, RAIL_STEEL, RAIL_TIE, poolGeometry, railGeometry, rippleCurves } from "../practiceRange";

const T = TILE_SIZE;
/** 高度標記「▲N」的數字字級（世界座標；6F-9 起畫面上至少 `MIN_HEIGHT_BADGE_FONT_PX`）。 */
export const HEIGHT_BADGE_FONT = 10;
/** 可燃小火苗平時的透明度（3-38）。 */
export const FLAME_DIM = 0.4;

export abstract class TerrainLayer extends RendererBase {
  /** 重畫後：目標高度沒變的升降動畫套回目前的高度繼續播，其餘作廢。 */
  protected resumeLifts(model: DrawModel): void {
    for (const [key, st] of [...this.lifting]) {
      if (heightAt(model, st.pos) === st.to) this.rows.setLift(st.pos, tileLift(st.h));
      else this.lifting.delete(key);
    }
  }

  /**
   * 測試模式的滑軌與方角水池（PR-2c，`DrawModel.practice`；畫法照 `obSamples.js` 的 `rail()`、`pool()`）。實戰沒有 `practice`，什麼都不畫。
   * - 水面：每一格一塊方角的水（地形層，蓋掉原本圓角的水面），兩道波紋；水面的飄動反光（6N-9）照舊疊在上面。
   * - 石條：表面裝飾層，放在石條所在那一排（那一排的人站在石條上面）；
   * - 滑軌：表面裝飾層，枕木在下、兩條鐵軌在上。
   * 位置都跟著格子抬高（`place`，以世界座標畫好整塊、節點放在原點）。
   */
  protected drawPracticeScene(model: DrawModel): void {
    const scene = model.practice;
    if (scene === undefined) return;
    const isWater = (p: { x: number; y: number }) => model.tiles[p.y * model.width + p.x]?.surface === "water";
    const geom = poolGeometry(scene.pool, isWater, model.width, model.height, T);
    for (const w of geom.water) {
      const g = new Graphics().rect(w.rect.x0, w.rect.y0, w.rect.x1 - w.rect.x0, w.rect.y1 - w.rect.y0).fill(POOL_WATER);
      for (const c of rippleCurves(w.seed, T)) g.moveTo(c.x, c.y).quadraticCurveTo(c.cx, c.cy, c.ex, c.ey);
      g.stroke({ width: POOL_RIPPLE.width, color: POOL_RIPPLE.color, alpha: POOL_RIPPLE.alpha, cap: "round" });
      this.rows.row(w.row).ground.addChild(g);
      this.place(g, w.tile, 0, 0);
    }
    for (const s of geom.slabs) {
      const g = new Graphics()
        .rect(s.rect.x0, s.rect.y0, s.rect.x1 - s.rect.x0, s.rect.y1 - s.rect.y0)
        .fill({ color: s.light ? POOL_SLAB_LIGHT : POOL_SLAB, alpha: 0.94 })
        .stroke({ width: 0.8, color: PRACTICE_INK, alpha: 0.9, join: "miter" });
      for (const [x0, y0, x1, y1] of s.joints) g.moveTo(x0, y0).lineTo(x1, y1);
      if (s.joints.length > 0) g.stroke({ width: 0.7, color: POOL_JOINT, cap: "round" });
      this.rows.row(s.row).deco.addChild(g);
      this.place(g, s.tile, 0, 0);
    }
    for (const rail of scene.rails) {
      const r = railGeometry(rail, T);
      const g = new Graphics();
      for (const t of r.ties) g.rect(t.x0, t.y0, t.x1 - t.x0, t.y1 - t.y0);
      g.fill(RAIL_TIE).stroke({ width: 0.6, color: PRACTICE_INK, alpha: 0.9 });
      for (const y of r.rails) g.moveTo(r.x0, y).lineTo(r.x1, y);
      g.stroke({ width: r.steel, color: RAIL_STEEL, cap: "round" });
      this.rows.row(r.row).deco.addChild(g);
      this.place(g, { x: rail.x0, y: rail.y }, 0, 0);
    }
  }

  /** 源泉格（Phase 3C-6a）：格子中央一顆紫色菱形，標「源」；單位站上去時才會被取用。 */
  protected drawWells(model: DrawModel): void {
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
  protected drawRunes(model: DrawModel): void {
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
  protected drawMarkers(model: DrawModel): void {
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

  /**
   * 實地地圖的出口（UI-E4）：每格一個淡淡的地面光圈（裝飾層），路牌插在出口的第一格（物件層，照 y 排序）；
   * 室內（`bare`）不畫，已經有門墊與入口光。
   */
  protected drawExitSigns(model: DrawModel): void {
    for (const e of model.exitSigns ?? []) {
      if (e.bare) continue;
      for (const c of e.cells) {
        const glow = new Graphics();
        drawExitGlow(glow, 0, 0, T);
        this.rows.row(c.y).deco.addChild(glow);
        this.place(glow, c, c.x * T, c.y * T);
      }
      const sign = new Graphics();
      drawExitSign(sign, 0, 0, T, e.dir);
      this.rows.row(e.sign.y).objects.addChild(sign);
      this.place(sign, e.sign, e.sign.x * T, e.sign.y * T);
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
  protected drawZones(model: DrawModel): void {
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
  protected drawTrap(trap: TrapDraw): void {
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

  /** 區域的裝飾薄霧（3-37b；雲嶺）：每格一團淡淡的霧白，霧天加濃。只是裝飾，不影響視線規則。 */
  protected drawMist(model: DrawModel): void {
    const mist = mistLevel(model.region, model.weather ?? "");
    if (mist === null || model.scenery?.interior != null) return; // 6B-ART1：室內不飄區域的裝飾薄霧
    for (const t of model.tiles) {
      const sprite = this.fxSprite(`mist|${mist.level}|${t.x}|${t.y}`, (ctx) => drawMistTile(ctx, t.x, t.y, mist.alpha));
      if (sprite === null) continue;
      this.rows.row(t.y).veil.addChild(sprite);
      this.place(sprite, t, t.x * T, t.y * T);
    }
  }

  /** 擋視線的表面（`blocks_sight`，煙霧、黑暗…）：每格在單位之上多畫一層霧，蓋住單位下半身。 */
  protected drawVeils(model: DrawModel): void {
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
  protected tileSprite(model: DrawModel, t: TileDraw): void {
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
      g.rect(0, 0, T, T).fill(t.fill); // 無法產生貼圖：退回色塊（6A-4a：待機不畫格線）
    }
    c.addChild(edges);
    if (t.deadly) drawLethalCorners(g, T, lethalCornersOf(model, t)); // 6V-2：小紅角標，6V-2b 起只畫在致命區外圍；滑過、預覽時的淡紅在 setHighlights
    c.addChild(g);
    redraw(tileLift(t.height));
    this.rows.row(t.y).ground.addChild(c);
    this.rows.place(c, t, t.x * T, t.y * T, tileLift(t.height), redraw);
  }

  /**
   * 高度徽章：只在高度 > 0 的格子左上角畫「▲N」（跟著頂面抬高）。
   * 6F-18（美術 PM 6F-17 檢查第 2 節）：格子上有人站著（沒倒下）時不畫，所有寬度都一樣；高度看地形的高低差、
   * 單位浮動卡與目標說明的「高地 ▲N」。6F-14～6F-17 為了讓開站著的人而移動、縮成角標的畫法拿掉。
   */
  protected drawBadges(model: DrawModel): void {
    for (const t of model.tiles) {
      const text = heightBadgeText(model, t);
      if (text === null || !markedTileFree(model.units, t)) continue;
      const node = new Container();
      const g = new Graphics();
      const bg = HEIGHT_MARK_BG;
      g.roundRect(bg.x, bg.y, bg.w, bg.h, bg.r).fill({ color: 0x1e1812, alpha: 0.7 });
      g.poly([...HEIGHT_MARK_TRI]).fill(0xfff3c4);
      const num = label(text, HEIGHT_BADGE_FONT, 0xfff3c4, true);
      num.position.set(HEIGHT_MARK_NUM.x, HEIGHT_MARK_NUM.y);
      node.addChild(g, num);
      // 6F-9：數字在畫面上至少 10px（地圖縮小時以格子左上角為基準反向放大）
      node.label = HEIGHT_BADGE_LABEL;
      // 6F-22b：北邊的人的 HUD 畫在高台之上、會蓋到左上角時，改放左下角
      const corner = heightMarkAtCorner(model, model.units, t);
      registerMark(node, { base: HEIGHT_BADGE_FONT, min: MIN_HEIGHT_BADGE_FONT_PX }, [num], corner ? (k) => {
        g.y = heightMarkCornerDrop(k);
        num.y = HEIGHT_MARK_NUM.y + g.y;
      } : undefined);
      this.heightBadges.push(node);
      this.scaleMark(node);
      this.rows.row(t.y).badges.addChild(node);
      this.place(node, t, t.x * T, t.y * T);
    }
  }

  /** 可燃小火苗（3-38）：獨立一層，平時淡化、`flameOn` 時明顯；全場一起切換（不重畫）。 */
  private addFlammableMark(c: Container, o: ObjectDraw, hasSprite: boolean): void {
    if (!hasFlammableMark(o.kind, o.flammable)) return;
    let node: Container | null = null;
    if (hasSprite) {
      const tex = this.art.flammableMark();
      if (tex !== null) {
        const sprite = new Sprite(tex);
        sprite.width = T;
        sprite.height = T;
        node = sprite;
      }
    } else {
      node = new Graphics().circle(T - 8, 8, 4).fill(HIGHLIGHT.flammable);
    }
    if (node === null) return;
    node.alpha = this.flameOn ? 1 : FLAME_DIM;
    this.flameMarks.push(node);
    c.addChild(node);
  }

  /** 設定可燃標記明顯（`true`）或淡化（`false`）；只改透明度。 */
  setFlameEmphasis(on: boolean): void {
    this.flameOn = on;
    const alpha = on ? 1 : FLAME_DIM;
    for (const n of this.flameMarks) if (!n.destroyed) n.alpha = alpha;
  }

  protected objectSprite(o: ObjectDraw, kinds: ReadonlyMap<string, string>, theme: ArtTheme, submerged = false): Container {
    const c = new Container();
    const g = new Graphics();
    const known = hasObjectArt(o.kind);
    const texture = this.art.object(objectArtSpec(o, kinds, theme));
    const hasSprite = texture !== null;
    if (hasSprite && submerged) {
      // 6F-6：半沉在深水裡（灰渡口的舊渡船）：水線以上照常，水線以下半透明、蓋水色，再畫一條水線
      const line = waterline(T);
      const part = (y0: number, y1: number, alpha: number, tint: number) => {
        const s = new Sprite(texture);
        s.width = T;
        s.height = T;
        s.alpha = alpha;
        s.tint = tint;
        const m = new Graphics().rect(0, y0, T, y1 - y0).fill({ color: 0xffffff });
        s.mask = m;
        c.addChild(m, s);
      };
      part(0, line.y, 1, 0xffffff);
      part(line.y, T, SUBMERGED_ALPHA, SUBMERGED_TINT);
      const w = new Graphics().moveTo(line.x0, line.y).lineTo(line.x1, line.y).stroke({ width: 1.5, color: WATERLINE_COLOR, alpha: WATERLINE_ALPHA });
      for (const r of line.ripples) w.arc(r.x, line.y + 1, r.r, Math.PI * 1.1, Math.PI * 1.9).stroke({ width: 1, color: WATERLINE_COLOR, alpha: WATERLINE_ALPHA * 0.7 });
      c.addChild(w);
    } else if (hasSprite) {
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
    }
    c.addChild(g);
    this.addFlammableMark(c, o, hasSprite);
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

  /** 地表動畫畫在哪裡（6N-9）：每一排的地形層、表面裝飾層，跟著格子抬高；舊的樣子用同一套地形貼圖。 */
  protected readonly surfaceHost: SurfaceHost = {
    ground: (y) => this.rows.row(y).ground,
    deco: (y) => this.rows.row(y).deco,
    place: (node, t) => this.rows.place(node, t, t.x * T, t.y * T, tileLift(t.height)),
    oldTile: (from, t) => this.art.tile(tileArtSpec(from, t)),
    objects: (y) => this.rows.row(y).objects, // CW-1：冷卻井的破壞演出
    canvas: (key, make) => this.art.canvas(key, make), // CW-1：冷卻井的演出、碎屑貼圖
  };

  protected ambientHost(): AmbientHost {
    return { art: this.art, rows: this.rows, place: (node, p, x, y) => this.place(node, p, x, y), origin: (p) => this.origin(p) };
  }

  protected sceneryHost(): SceneryHost {
    return { art: this.art, rows: this.rows, place: (node, p, x, y) => this.place(node, p, x, y) };
  }
}
