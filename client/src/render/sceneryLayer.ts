// 把只畫的外觀（Phase 6B-ART1：建築、門、室內外框、家具）放進戰鬥渲染器的逐排圖層。
// - 建築放在範圍最下一列的物件層：北邊各排（含站在屋後的人）先畫，被屋頂蓋住；同一列與南邊的人畫在上面。
//   頭頂圖示是 DOM（FieldHeads），不受影響。
// - 門是獨立節點（門框＋門板），門板以門軸為準水平縮放＝往內轉開（`setDoor`）；入口光圈在門前一格的裝飾層。
// - 室內：地板、牆邊、出口畫在各排的裝飾層（地形之上、物件之下）；後牆（1.6 格高）放在第 2 排的裝飾層，蓋住第 1 排與第 2 排的上緣。
// - 家具取代該格物件的畫法（規則照原本的物件）。
import { Container, Sprite, type Texture } from "pixi.js";
import type { Pos } from "../api/types";
import { TILE_SIZE } from "../battle/geometry";
import type { DrawModel, ObjectDraw } from "../battle/drawModel";
import type { Ctx } from "./artDraw";
import { ART_RESOLUTION, type ArtTextures } from "./artTextures";
import { ART_T } from "./terrainArt";
import type { RowStack } from "./rowLayers";
import { buildingArtKey, doorFrame, doorPanel, doorPanelScale, DOOR_W, entrance, roofRows } from "./townArt";
import { BANNER_OFFSETS, drawBanner, drawPortalPillar, drawPortalRing, paintBuilding, PORTAL_TILES, REGION_ORDER } from "./capitalArt";
import { BACK_WALL_ROWS, backWallKey, drawBackWall, drawExitCell, drawFloor, drawFurniture, drawWallCell, furnitureKey, FURNITURE_ROWS } from "./interiorArt";
import { interiorPieces, type DoorScene, type FieldScenery, type PlazaScene } from "./sceneryModel";

const T = TILE_SIZE;

/** 依格數畫一張離屏 canvas（52 單位一格，ART_RESOLUTION 倍解析度）；沒有 DOM 時 `null`。 */
function paintTiles(wTiles: number, hTiles: number, draw: (ctx: Ctx) => void): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const px = T * ART_RESOLUTION;
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.ceil(wTiles * px));
  canvas.height = Math.max(1, Math.ceil(hTiles * px));
  const ctx = canvas.getContext("2d");
  if (ctx === null) return null;
  ctx.scale(px / ART_T, px / ART_T);
  draw(ctx);
  return canvas;
}

/** 放節點：`place(node, p, x, y)` ＝ 放在 (x, y) 並跟著格子 `p` 抬高（BattleRenderer.place）。 */
export interface SceneryHost {
  art: ArtTextures;
  rows: RowStack;
  place(node: Container, p: Pos, x: number, y: number): void;
}

interface DoorNode {
  panel: Sprite;
  base: number;
}

export class SceneryLayer {
  private doors = new Map<string, DoorNode>();
  private furniture: FieldScenery["furniture"] = {};

  private sprite(host: SceneryHost, key: string, wTiles: number, hTiles: number, draw: (ctx: Ctx) => void): Sprite | null {
    const tex: Texture | null = host.art.canvas(`s|${key}`, () => paintTiles(wTiles, hTiles, draw));
    if (tex === null) return null;
    const s = new Sprite(tex);
    s.width = wTiles * T;
    s.height = hTiles * T;
    return s;
  }

  /** 重畫場景時呼叫（地形畫完之後、物件之前）。 */
  draw(host: SceneryHost, model: DrawModel, scenery: FieldScenery | undefined): void {
    this.doors.clear();
    this.furniture = scenery?.furniture ?? {};
    if (scenery === undefined) return;
    if (scenery.interior !== null) this.drawInterior(host, model, scenery);
    if (scenery.plaza != null) this.drawPlaza(host, model, scenery.plaza);
    for (const b of scenery.buildings) {
      const s = b.spec;
      const roof = roofRows(s);
      const node = this.sprite(host, buildingArtKey(s), s.w, s.h + roof, (ctx) => paintBuilding(ctx, s));
      if (node === null) continue;
      const bottom = { x: b.x, y: b.y + s.h - 1 };
      host.rows.row(bottom.y).objects.addChild(node);
      host.place(node, bottom, b.x * T, (b.y - roof) * T);
    }
    for (const d of scenery.doors) this.drawDoor(host, model, d);
  }

  /**
   * 主城的中央傳送陣（6D-ART2）：地上的光圈放在最上面那一排的裝飾層（之後各排的人與物件都畫在上面），
   * 中央晶柱放在傳送石那一排的物件層；五面區旗各放在自己那一排的物件層（只畫、不佔格）。
   */
  private drawPlaza(host: SceneryHost, model: DrawModel, plaza: PlazaScene): void {
    const half = (PORTAL_TILES - 1) / 2;
    // 光圈切成一列一條，各放進自己那一排的裝飾層（地形逐排畫，整張放在最上排會被下面幾排的地形蓋住）
    for (let k = 0; k < PORTAL_TILES; k++) {
      const row = plaza.y - half + k;
      if (row < 0 || row >= model.height) continue;
      const strip = this.sprite(host, `portal|${plaza.open.join(".")}|${k}`, PORTAL_TILES, 1, (ctx) => {
        ctx.translate(0, -k * ART_T);
        drawPortalRing(ctx, plaza.open);
      });
      if (strip === null) continue;
      host.rows.row(row).deco.addChild(strip);
      host.place(strip, { x: plaza.x, y: row }, (plaza.x - half) * T, row * T);
    }
    const at = { x: plaza.x, y: plaza.y };
    const pillar = this.sprite(host, "portal_pillar", 1, 2, (ctx) => drawPortalPillar(ctx));
    if (pillar !== null) {
      host.rows.row(plaza.y).objects.addChild(pillar);
      host.place(pillar, at, plaza.x * T, (plaza.y - 1) * T);
    }
    REGION_ORDER.forEach((region, k) => {
      const [dx, dy] = BANNER_OFFSETS[k]!;
      const p = { x: plaza.x + dx, y: plaza.y + dy };
      if (p.x < 0 || p.y < 0 || p.x >= model.width || p.y >= model.height) return;
      const flag = this.sprite(host, `banner|${region}`, 1, 2, (ctx) => drawBanner(ctx, region));
      if (flag === null) return;
      host.rows.row(p.y).objects.addChild(flag);
      host.place(flag, p, p.x * T, (p.y - 1) * T);
    });
  }

  private drawDoor(host: SceneryHost, model: DrawModel, d: DoorScene): void {
    const { x, style } = d;
    const y = d.drawY ?? d.y; // 側牆的門畫在建築正面同一欄
    const at = { x, y };
    const frame = this.sprite(host, `doorframe|${style}`, 1, 1, (ctx) => doorFrame(ctx, ART_T / 2, ART_T, style));
    const panel = this.sprite(host, `doorpanel|${style}`, 1, 1, (ctx) => doorPanel(ctx, ART_T / 2 - DOOR_W / 2, ART_T, style));
    if (frame === null || panel === null) return;
    const c = new Container();
    c.addChild(frame);
    // 門板的錨點在門軸（左緣）：縮放時往門軸收（往內轉開）
    const hinge = ((ART_T / 2 - DOOR_W / 2) / ART_T) * T;
    panel.anchor.set(hinge / T, 0);
    panel.position.set(hinge, 0);
    panel.width = T;
    c.addChild(panel);
    host.rows.row(y).objects.addChild(c);
    host.place(c, at, x * T, y * T);
    this.doors.set(`${d.x},${d.y}`, { panel, base: panel.scale.x }); // 門動畫照真正的門格
    const front = d.side === "w" ? { x: d.x - 1, y: d.y } : d.side === "e" ? { x: d.x + 1, y: d.y } : { x, y: y + 1 };
    if (front.x >= 0 && front.x < model.width && front.y < model.height) {
      const ring = this.sprite(host, "entrance", 1, 1, (ctx) => entrance(ctx, ART_T / 2, ART_T * 0.45));
      if (ring !== null) {
        host.rows.row(front.y).deco.addChild(ring);
        host.place(ring, front, front.x * T, front.y * T);
      }
    }
  }

  private drawInterior(host: SceneryHost, model: DrawModel, scenery: FieldScenery): void {
    const room = scenery.interior;
    if (room === null) return;
    const p = room.palette;
    const walls = new Set(model.tiles.filter((t) => t.terrain === "wall").map((t) => `${t.x},${t.y}`));
    for (const piece of interiorPieces(room, model.width, model.height, walls)) {
      const { x, y } = piece;
      let node: Sprite | null;
      if (piece.kind === "floor") {
        const r = piece.rug;
        const rk = r === null ? "-" : `${+r.n}${+r.e}${+r.s}${+r.w}`;
        node = this.sprite(host, `floor|${p.floor}|${p.style}|${(x * 7 + y * 3) % 5}|${(x + y) % 2}|${rk}`, 1, 1, (ctx) => drawFloor(ctx, x, y, p, r));
      } else if (piece.kind === "wall") {
        const sd = piece.side;
        node = this.sprite(host, `iwall|${p.wall}|${+sd.n}${+sd.e}${+sd.w}`, 1, 1, (ctx) => drawWallCell(ctx, sd, p));
      } else {
        node = this.sprite(host, `iexit|${p.floor}|${p.style}|${(x * 7 + y * 3) % 5}|${(x + y) % 2}`, 1, 1, (ctx) => drawExitCell(ctx, x, y, p));
      }
      if (node === null) continue;
      host.rows.row(y).deco.addChild(node);
      host.place(node, { x, y }, x * T, y * T);
    }
    const wall = this.sprite(host, backWallKey(model.width, p, room.decor), model.width, BACK_WALL_ROWS, (ctx) => drawBackWall(ctx, model.width, p, room.decor));
    if (wall !== null) {
      const row = Math.min(1, model.height - 1);
      host.rows.row(row).deco.addChild(wall);
      host.place(wall, { x: 0, y: 0 }, 0, 0);
    }
  }

  /** 這個物件有家具外觀時的節點（取代原本的物件畫法；畫布 1×2 格，下面那格是物件所在格）；沒有＝`null`。 */
  objectNode(host: SceneryHost, o: ObjectDraw): { node: Container; dy: number } | null {
    const spec = this.furniture[`${o.x},${o.y}`];
    if (spec === undefined) return null;
    const node = this.sprite(host, furnitureKey(spec), 1, FURNITURE_ROWS, (ctx) => drawFurniture(ctx, spec));
    if (node === null) return null;
    return { node, dy: -(FURNITURE_ROWS - 1) * T };
  }

  /** 門板轉開到 `open`（0 關～1 開）；那格沒有建築的門就不做事。 */
  setDoor(cell: Pos, open: number): boolean {
    const d = this.doors.get(`${cell.x},${cell.y}`);
    if (d === undefined || d.panel.destroyed) return false;
    d.panel.scale.x = d.base * doorPanelScale(open);
    d.panel.tint = open > 0 ? 0xb8b0a8 : 0xffffff;
    return true;
  }

  hasDoor(cell: Pos): boolean {
    return this.doors.has(`${cell.x},${cell.y}`);
  }
}
