// 高亮圖層（R1e 自 `BattleRenderer.ts` 拆出，純搬移）：移動格、範圍、預覽、目標框、方向、攀跳、環境預告、場景物件預覽、
// 路徑提示、致命淡紅、滑過與焦點框、出口滑過、實地地圖的標記（腳印、「！」、眼睛）。
import { Container, Graphics, Sprite, type Text, type Texture } from "pixi.js";
import { TELEGRAPH_BADGE_LABEL, TELEGRAPH_BADGE_R, TELEGRAPH_FONT, telegraphBadgeCenter, telegraphBadgeScale } from "../telegraphBadge";
import type { Pos } from "../../api/types";
import { occluded } from "../../battle/elevation";
import { TILE_SIZE } from "../../battle/geometry";
import { HIGHLIGHT } from "../../battle/glossary";
import type { Overlay, OverlayKind } from "../../battle/scenePreview";
import type { TelegraphMark } from "../../battle/telegraph";
import type { AimDraw, GuardDraw } from "../../battle/rgMarks";
import { clearLayer, label } from "../labels";
import { drawExitFrame, exitLabel, hoverFrameCell, type ExitSignDraw } from "../exitSign";
import { creatureOf, unitMarkTopY } from "../unitSprite";
import { roofCovers } from "../sceneryModel";
import { eventBob, eyeOffset, eyeTexture, footprintShapes, MARK_PAD, MARK_SIZE, objectHintAlpha, thingTexture, type MapThing, type WatchEye } from "../mapMarks";
import { clipHighlights } from "../mapClip";
import { LETHAL_TINT_ALPHA, lethalTintCells } from "../lethalMarks";
import { drawRegionBlobs, type RegionMark } from "../regionBlobs";
import type { PathDraw, PathTag } from "../../battle/pathPreview";
import { bangCenter, drawFaintGrid, drawPathLine, drawPathMarks, drawSoftCells, HIT_SOFT, missTagNode, MOVE_SOFT, pathTagNode, RANGE_SOFT, placeTags, type TileGeo } from "../pathArt";
import { poolInsets } from "../practiceRange";
import { TerrainLayer } from "./terrainLayer";
import { hoverCellFrame, isGiantDraw } from "../../battle/drawModel";
import { giantTargetFrame } from "../giantSprite";
import { giantMarkNodes, type GiantMarksDraw } from "./partTileMarks";

const T = TILE_SIZE;
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
  /** 選技能時淡淡浮出的施放範圍（Phase 6A-4c）：淡色圓角格＋外緣亮線，格線極淡地浮出。 */
  range?: readonly Pos[];
  /** 選移動時滑過的路徑提示（Phase 6A-4c，資料來自伺服器的路徑預覽）。 */
  path?: PathDraw;
  /** 併成一塊的格子範圍（Phase 6A-4g：實地地圖上敵人的視野）：淡色填滿、只描外緣（`regionBlobs.ts`）。 */
  regions?: readonly RegionMark[];
  /** 實地地圖上照形狀畫的東西（Phase 6C-8：事件「！」、營火、留言石碑、朋友腳印；`mapMarks.ts`）。 */
  things?: readonly MapThing[];
  /** 實地地圖上有視野的敵群頭上的眼睛（6C-8，潛行時半閉）。 */
  eyes?: readonly WatchEye[];
  /** 滑過（觸控：點一下）的出口（UI-E4）：每格綠框＋目的地名小牌。 */
  exitHover?: ExitSignDraw | null;
  /** RG-3：瞄準預告（準星＋瞄準線；`battle/rgMarks.aimDraws`，畫在 `RgMarkLayer`）。 */
  aims?: readonly AimDraw[];
  /** RG-3：選目標預覽有盾兵掩護時的小盾與連結（`battle/rgMarks.guardDraw`）。 */
  guard?: GuardDraw | null;
  /** GB-4b：3×3 巨型頭目的部位格標示（選打它的動作時；`partTileMarks.giantMarksOf`）。沒有時省略。 */
  giantMarks?: readonly GiantMarksDraw[];
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

export abstract class HighlightLayer extends TerrainLayer {
  /** BM-1：目前畫著的延遲預告字（節點、字、格子左上角）；縮放改變時重排（`telegraphRescale`）。 */
  private telegraphBadges: Array<{ node: Container; glyph: Text; o: { x: number; y: number } }> = [];

  /** BM-1：延遲預告字照目前的地圖縮放放大（畫面字 ≥ `MIN_TELEGRAPH_FONT_PX`）、錨在格子右上角；字的解析度跟著倍率提高。 */
  protected telegraphRescale(): void {
    const k = telegraphBadgeScale(this.scale);
    const c = telegraphBadgeCenter(k);
    const res = (window.devicePixelRatio || 1) * this.scale * k;
    for (const b of this.telegraphBadges) {
      if (b.node.destroyed) continue;
      b.node.scale.set(k);
      b.node.position.set(b.o.x + c.x, b.o.y + c.y);
      if (!b.glyph.destroyed) b.glyph.resolution = Math.max(1, res);
    }
  }

  /** 滑過的出口：每格綠框（原本的「出」框），出口上方一個「往目的地」小牌。 */
  private drawExitHover(exit: ExitSignDraw): void {
    const g = new Graphics();
    for (const c of exit.cells) {
      const o = this.origin(c);
      drawExitFrame(g, o.x, o.y, T, HIGHLIGHT.exit);
    }
    this.hover.addChild(g);
    if (exit.cells.length === 0) return;
    const tag = label(exitLabel(exit.name), 13, 0xeafff0, true);
    tag.anchor.set(0.5, 1);
    tag.style.stroke = { color: 0x0c1a10, width: 4 };
    const xs = exit.cells.map((c) => this.origin(c).x);
    const top = Math.min(...exit.cells.map((c) => this.origin(c).y));
    const half = tag.width / 2 + 2;
    const right = (this.model?.width ?? 1) * T - half;
    tag.position.set(Math.min(right, Math.max(half, (Math.min(...xs) + Math.max(...xs)) / 2 + T / 2)), Math.max(16, top - 2));
    this.hover.addChild(tag);
  }

  /**
   * HID-1b（美術 PM 11-07）：攻擊紅框畫在該排單位之下（`RowLayer.frames`），HP 條、「？」自然在紅框之上；不縮框。
   * 被南邊高台、屋頂擋住的格子（身體和剪影畫法同一判斷）改畫在 `attackTop`（仍在 `hudTop` 之下），框才看得到。
   */
  protected drawAttackFrames(): void {
    this.rows.clearFrames();
    clearLayer(this.attackTop);
    const model = this.model;
    if (model === null) return;
    const insetOf = this.poolInset();
    // GB-4b（美術移植需求第 7 節第 3 條）：3×3 巨型頭目的 9 格都是目標時改畫一個框住整個 3×3 的紅框。照建議先放在南排的 `frames`
    // （單位之下）實拍：本體幾乎蓋滿 3×3，紅框只剩外緣零星幾 px 看不出來，所以照第 3 條後半改到標示層（`attackTop`：單位之上）。
    // GB-4c（美術 GB-4b 待決 1 裁定）：紅框在標示層內排最底——部位格標示另放 `giantMarkTop`（`attackTop` 之上），不壓滑過框
    const giantCells = new Set<string>();
    for (const u of model.units) {
      const tiles = u.tiles ?? [];
      if (!isGiantDraw(u) || u.downed || !tiles.every((t) => this.attackCells.some((c) => c.x === t.x && c.y === t.y))) continue;
      for (const t of tiles) giantCells.add(`${t.x},${t.y}`);
      const nw = { x: Math.min(...tiles.map((t) => t.x)), y: Math.min(...tiles.map((t) => t.y)) };
      this.attackTop.addChild(giantTargetFrame(this.origin(nw), HIGHLIGHT.attack));
    }
    for (const p of this.attackCells) {
      if (giantCells.has(`${p.x},${p.y}`)) continue;
      const o = this.origin(p);
      // PR-2d：測試模式貼水池的紅框讓出石條；實戰 `insetOf` 是 undefined，走改前那一行
      const i = insetOf?.(p) ?? null;
      const frame =
        i === null
          ? new Graphics().roundRect(o.x + 2, o.y + 2, T - 4, T - 4, 8).stroke({ width: 3, color: HIGHLIGHT.attack })
          : new Graphics().roundRect(o.x + 2 + i.w, o.y + 2 + i.n, T - 4 - i.w - i.e, T - 4 - i.n - i.s, 8).stroke({ width: 3, color: HIGHLIGHT.attack });
      const hiddenCell = occluded(model, p) || roofCovers(model.scenery, p);
      (hiddenCell ? this.attackTop : this.rows.row(p.y).frames).addChild(frame);
    }
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

  setHighlights(all: Highlights): void {
    if (!this.ready) return;
    const h = this.model === null ? all : clipHighlights(this.model, all); // 6F-6：範圍預覽不畫到地圖外
    clearLayer(this.marks);
    clearLayer(this.giantMarkTop);
    clearLayer(this.hover);
    const pen = this.markPen();
    const geo = this.geo();
    // 6A-4c：選移動、選技能時格子淡色圓角浮出，範圍外緣加亮線；選技能時格線極淡地浮出
    const range = h.range ?? [];
    if (range.length > 0 && this.model !== null) drawFaintGrid(pen.at(range[0] as Pos), this.model.tiles, geo);
    // PR-2d：測試模式（`DrawModel.practice`）貼水池的格子往內縮、不壓石條；實戰 `insetOf` 是 undefined
    const insetOf = this.poolInset();
    drawSoftCells(pen.at(h.moves[0] ?? { x: 0, y: 0 }), h.moves, geo, MOVE_SOFT, insetOf);
    drawSoftCells(pen.at(range[0] ?? { x: 0, y: 0 }), range, geo, RANGE_SOFT, insetOf);
    drawSoftCells(pen.at(h.preview[0] ?? { x: 0, y: 0 }), h.preview, geo, HIT_SOFT, insetOf);
    if ((h.regions?.length ?? 0) > 0) {
      const rg = new Graphics();
      drawRegionBlobs(rg, h.regions ?? [], T, (p) => this.origin(p));
      this.marks.addChild(rg);
    }
    this.drawThings(h.things ?? [], h.eyes ?? []);
    this.telegraphBadges = [];
    for (const m of h.telegraph) {
      const o = this.origin(m.pos);
      pen
        .at(m.pos)
        .rect(o.x + 3, o.y + 3, T - 6, T - 6)
        .fill({ color: m.color, alpha: 0.16 })
        .stroke({ width: 2, color: m.color, alpha: 0.85 });
      // BM-1：右上角的預告字有最小畫面尺寸（`telegraphBadge.ts`；800 寬放大、往格子角長）
      const node = new Container();
      node.label = TELEGRAPH_BADGE_LABEL;
      const badge = new Graphics().circle(0, 0, TELEGRAPH_BADGE_R).fill({ color: 0x000000, alpha: 0.65 });
      const glyph = label(m.glyph, TELEGRAPH_FONT, m.color, true);
      glyph.anchor.set(0.5);
      node.addChild(badge, glyph);
      this.telegraphBadges.push({ node, glyph, o });
      pen.add(m.pos, node);
    }
    this.telegraphRescale();
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
    this.attackCells = h.attacks;
    this.drawAttackFrames();
    for (const tag of tags) pen.add(tag.pos, tag.text); // 文字標記畫在色塊之上
    if (h.path !== undefined) this.drawPath(h.path, geo);
    this.drawLethalTints(h);
    if (h.exitHover != null) this.drawExitHover(h.exitHover);
    // GB-4c（美術 GB-4b 可修 1）：滑到巨型頭目的佔格上不畫單格白框（交給部位框、3×3 目標紅框）
    const hoverCell = hoverFrameCell(h.hover, h.exitHover);
    this.drawFrames(h.focus, this.model === null ? hoverCell : hoverCellFrame(this.model.units, hoverCell));
    this.drawGiantMarks(h.giantMarks ?? []);
  }

  /** GB-4b：部位格標示（單位之上；GB-4c 起放 `giantMarkTop`，在 3×3 目標紅框之上；`partTileMarks.ts`）。 */
  private drawGiantMarks(list: readonly GiantMarksDraw[]): void {
    for (const d of list) {
      const draw = this.model?.units.find((u) => u.id === d.unitId);
      const look = draw === undefined ? null : (creatureOf(draw)?.boss?.giant ?? null);
      for (const n of giantMarkNodes(this.art, d, look, this.center(d.pos), this.scale, window.devicePixelRatio || 1)) this.giantMarkTop.addChild(n);
    }
  }

  /** 6V-2：滑過、路徑預覽、選目標碰到致命格時整格疊淡紅（只是畫法；致命判定與路徑規則不動）。 */
  private drawLethalTints(h: Highlights): void {
    if (this.model === null) return;
    const cells = lethalTintCells(this.model, { hover: h.hover, path: h.path, preview: h.preview, attacks: h.attacks, picked: h.picked });
    if (cells.length === 0) return;
    const g = new Graphics();
    for (const p of cells) {
      const o = this.origin(p);
      g.rect(o.x + 1, o.y + 1, T - 2, T - 2).fill({ color: HIGHLIGHT.deadly, alpha: LETHAL_TINT_ALPHA });
    }
    this.hover.addChild(g);
  }

  /**
   * 實地地圖的標記（6C-8，`mapMarks.ts`）：腳印用 Graphics 畫兩步鞋印，其他是程式繪製的貼圖（格子左上角對齊、四周多留 `MARK_PAD`）；
   * 事件「！」的泡泡另一張、上下浮動；眼睛放在敵群頭上。不畫格子框、不寫字。
   */
  private drawThings(things: readonly MapThing[], eyes: readonly WatchEye[]): void {
    this.bobs = [];
    this.breaths = [];
    const prints = new Graphics();
    for (const t of things) {
      const o = this.origin(t.pos);
      if (t.kind === "footprint") {
        for (const e of footprintShapes(t.facing, T)) {
          prints.ellipse(o.x + e.cx, o.y + e.cy, e.rx, e.ry).fill({ color: 0xe8f0ff, alpha: t.alpha }).stroke({ width: 0.9, color: 0x281e14, alpha: 0.55 * t.alpha });
        }
        continue;
      }
      const tex = thingTexture(t);
      if (tex === null) continue;
      const main = this.markSprite(tex, o.x - MARK_PAD, o.y - MARK_PAD);
      this.marks.addChild(main);
      if (t.kind === "object_hint") {
        // 6C-8b：虛線圈呼吸（`objectHintAlpha`），右上小手不動
        this.breaths.push(main);
        main.alpha = objectHintAlpha(this.bobClock);
        const hand = thingTexture(t, "bubble");
        if (hand !== null) this.marks.addChild(this.markSprite(hand, o.x - MARK_PAD, o.y - MARK_PAD));
        continue;
      }
      if (t.kind === "event") {
        const bubble = thingTexture(t, "bubble");
        if (bubble === null) continue;
        const node = this.markSprite(bubble, o.x - MARK_PAD, o.y - MARK_PAD);
        this.bobs.push({ node, y: node.y });
        node.y += eventBob(this.bobClock);
        this.marks.addChild(node);
      }
    }
    if (prints.context.instructions.length > 0) this.marks.addChildAt(prints, 0);
    else prints.destroy();
    for (const e of eyes) {
      const tex = eyeTexture(e.sneaking);
      if (tex === null) continue;
      const o = this.origin(e.pos);
      // 6C-8b：眼睛放在這個單位實際畫出來的頂端再往上 6px（大型異形、頭目不被蓋住）
      const unit = this.model?.units.find((u) => u.x === e.pos.x && u.y === e.pos.y && u.team !== "ally");
      const at = eyeOffset(T, unit === undefined ? null : unitMarkTopY(unit)); // QK-9：頭目從 HUD 上方
      const node = new Sprite(tex);
      node.anchor.set(0.5);
      node.width = MARK_SIZE;
      node.height = MARK_SIZE;
      node.position.set(o.x + at.x, o.y + at.y);
      this.marks.addChild(node);
    }
  }

  private markSprite(tex: Texture, x: number, y: number): Sprite {
    const node = new Sprite(tex);
    node.width = MARK_SIZE;
    node.height = MARK_SIZE;
    node.position.set(x, y);
    return node;
  }

  /** 事件「！」上下浮動（6C-8；週期 1.6 秒、幅度 3px）。 */
  protected tickBobs(dt: number): void {
    this.bobClock += dt;
    if (this.breaths.length > 0) {
      const a = objectHintAlpha(this.bobClock);
      for (const n of this.breaths) if (!n.destroyed) n.alpha = a;
    }
    if (this.bobs.length === 0) return;
    const dy = eventBob(this.bobClock);
    for (const b of this.bobs) if (!b.node.destroyed) b.node.y = b.y + dy;
  }

  /** PR-2d：測試模式的水池石條要讓出的內縮（`practiceRange.poolInsets`）；實戰、技能工坊沒有 `model.practice`，回 undefined。 */
  private poolInset(): ReturnType<typeof poolInsets> {
    const m = this.model;
    return m === null ? undefined : poolInsets(m.practice, m.width, m.height, T);
  }

  /** 抬高後的格子幾何（給 `pathArt` 用）。 */
  private geo(): TileGeo {
    return { origin: (p) => this.origin(p), center: (p) => this.center(p) };
  }

  /** 選移動時的路徑提示（6A-4c）：外框與停點標記、路徑線與點、結果小牌，畫在其他高亮之上。 */
  private drawPath(path: PathDraw, geo: TileGeo): void {
    const hasAny = path.segments.length > 0 || path.frames.length > 0 || path.missEnd !== null || path.tags.length > 0;
    if (!hasAny) return;
    const g = new Graphics();
    drawPathMarks(g, { ...path, bangs: [], slipStops: [] }, geo);
    drawPathLine(g, path, geo);
    this.marks.addChild(g);
    const bangs = new Graphics();
    drawPathMarks(bangs, { ...path, frames: [], missEnd: null }, geo); // 驚嘆號、滑倒停點 ◆ 畫在線與小牌之上（最後加入）
    const nodes = path.tags.map((tag) => pathTagNode(tag));
    const spots = placeTags(
      nodes.map((n, i) => ({ o: this.origin((path.tags[i] as PathTag).pos), w: n.width })),
      path.bangs.map((p) => bangCenter(this.center(p))),
    );
    nodes.forEach((n, i) => {
      const at = spots[i] as { x: number; y: number };
      n.position.set(at.x, at.y);
      this.marks.addChild(n);
    });
    if (path.missEnd !== null) this.marks.addChild(missTagNode(this.origin(path.missEnd)));
    this.marks.addChild(bangs);
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
}
