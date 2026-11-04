// 環境動態的圖層（Phase 6N-10）：把 ambientAnim 的時間軸套到戰鬥渲染器的節點上（實地地圖與戰場共用 BattleRenderer）。
// - 營火：火苗（貼圖疊在營火標記的火上）閃動、暖光呼吸（加亮混色）。
// - 燈籠：酒館屋簷下的燈籠、室內的燭台，光暈呼吸、輕輕閃。
// - 草叢、竹叢（`grass` 物件）：以底邊為軸斜切，依風向擺；酒館門口一面酒旗，4 格貼圖輪流（量化）。
// - 冰洞（`ice_hole` 地形）的水波一圈一圈擴散；雲嶺（有區域薄霧的地圖，室內除外）幾團薄霧順著風慢慢飄。
// 貼圖：光暈、火苗、水波、霧各 1 張＋酒旗 4 張（一個方向；往西吹時水平翻轉），全部在重畫場景時取（6M-3 的快取每輪清掉沒用到的）。
// 減少動態（prefers-reduced-motion）或關掉（截圖、量測）時停在第 0 毫秒的樣子，不再更新。只影響畫面，不碰規則與地圖資料。
import { Container, Sprite, type Texture } from "pixi.js";
import type { Pos } from "../api/types";
import type { DrawModel, ObjectDraw } from "../battle/drawModel";
import { TILE_SIZE } from "../battle/geometry";
import { enchantRingAngle, enchantRingGlow, flagFrame, flagWave, flickerAt, FLAG_FRAMES, fountainSpray, mistAt, mistCount, ripplesAt, swayAt } from "./ambientAnim";
import { windOf, windStrength, type Wind } from "./ambientModel";
import type { ArtTextures } from "./artTextures";
import type { Ctx } from "./artDraw";
import { mistLevel } from "./regionArt";
import type { RowStack } from "./rowLayers";
import { BUILDING_ART_T, lanternCenters, roofRows, type BuildingSpec } from "./townArt";
import { fountainGeom } from "./capitalArt";
import { drawEnchantRunes, ENCHANT_RING } from "./interiorArt";

/**
 * 酒館燈籠光暈的場景座標（6Q-1，純函式）：`townArt.lanternCenters` 是建築畫布裡的位置；
 * 建築照 `sceneryLayer` 放在 `(b.x, b.y - 屋頂列數)` 格、跟著最下一列的抬高 `lift`（px）；`k` ＝ 場景一格 ÷ 畫布一格。
 * `cell` 是光暈閃動的種子（和 6N-10 一樣：「燈籠所在的欄,建築的 y」）。
 */
export function lanternLights(b: { x: number; y: number; spec: BuildingSpec }, lift: number, k = T / BUILDING_ART_T): { x: number; y: number; cell: string }[] {
  const ox = b.x * T;
  const oy = (b.y - roofRows(b.spec)) * T + lift;
  return lanternCenters(b.spec).map((l) => ({ x: ox + l.x * k, y: oy + l.y * k, cell: `${b.x + l.x / BUILDING_ART_T},${b.y}` }));
}

const T = TILE_SIZE;
const RES = 2;

/**
 * 許願池噴口與落點的場景座標（6V-4，純函式）：`capitalArt.fountainGeom` 是建築畫布裡的位置；建築照 `sceneryLayer`
 * 放在 `(b.x, b.y - 屋頂列數)` 格、跟著最下一列的抬高 `lift`（px）。`reach`、`drop` 換成場景像素。
 */
export function fountainSpout(b: { x: number; y: number; spec: BuildingSpec }, lift: number, k = T / BUILDING_ART_T): { x: number; y: number; reach: number; drop: number; scale: number } {
  const g = fountainGeom(b.spec);
  const ox = b.x * T;
  const oy = (b.y - roofRows(b.spec)) * T + lift;
  return { x: ox + g.spoutX * k, y: oy + g.spoutY * k, reach: (g.rx - g.rim) * 0.6 * k, drop: (g.cy - g.spoutY) * k, scale: k };
}

/** 附魔台符文環的中心（場景座標）：家具畫布的所在格頂就是 `cell.y` 那一格的頂，`ENCHANT_RING.cy` 是相對它往下。 */
export function enchantRingCenter(cell: Pos, lift: number, k = T / BUILDING_ART_T): { x: number; y: number; rx: number; ry: number } {
  return { x: cell.x * T + (BUILDING_ART_T / 2) * k, y: cell.y * T + lift + ENCHANT_RING.cy * k, rx: ENCHANT_RING.rx * k, ry: ENCHANT_RING.ry * k };
}

/** 畫一張離屏 canvas（`w`×`h` 個格子像素，RES 倍解析度）；沒有 DOM 時 `null`。 */
function paint(w: number, h: number, draw: (ctx: Ctx) => void): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const canvas = document.createElement("canvas");
  canvas.width = Math.ceil(w * RES);
  canvas.height = Math.ceil(h * RES);
  const ctx = canvas.getContext("2d");
  if (ctx === null) return null;
  ctx.scale(RES, RES);
  draw(ctx);
  return canvas;
}

const GLOW = 64;
const FLAME_W = 16;
const FLAME_H = 22;
const RIPPLE = 40;
const RUNE_TEX = 56;
const DROP = 8;
const WISP_W = 150;
const WISP_H = 64;
export const FLAG_W = 34;
export const FLAG_H = 74;
/** 旗桿在貼圖裡的 x。 */
const POLE_X = 3;

function drawGlow(ctx: Ctx): void {
  const g = ctx.createRadialGradient(GLOW / 2, GLOW / 2, 1, GLOW / 2, GLOW / 2, GLOW / 2);
  g.addColorStop(0, "rgba(255,190,90,0.9)");
  g.addColorStop(0.45, "rgba(255,150,50,0.35)");
  g.addColorStop(1, "rgba(255,140,40,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, GLOW, GLOW);
}

function drawFlame(ctx: Ctx): void {
  const cx = FLAME_W / 2;
  ctx.beginPath();
  ctx.moveTo(cx - 6, FLAME_H);
  ctx.quadraticCurveTo(cx - 7, FLAME_H * 0.45, cx, 0);
  ctx.quadraticCurveTo(cx + 7, FLAME_H * 0.45, cx + 6, FLAME_H);
  ctx.closePath();
  ctx.fillStyle = "rgba(255,122,42,0.85)";
  ctx.fill();
  ctx.beginPath();
  ctx.moveTo(cx - 3, FLAME_H);
  ctx.quadraticCurveTo(cx - 3.5, FLAME_H * 0.6, cx, FLAME_H * 0.38);
  ctx.quadraticCurveTo(cx + 3.5, FLAME_H * 0.6, cx + 3, FLAME_H);
  ctx.closePath();
  ctx.fillStyle = "rgba(255,214,70,0.95)";
  ctx.fill();
}

function drawDrop(ctx: Ctx): void {
  const g = ctx.createRadialGradient(DROP / 2 - 1, DROP / 2 - 1, 0.5, DROP / 2, DROP / 2, DROP / 2);
  g.addColorStop(0, "rgba(255,255,255,1)");
  g.addColorStop(0.6, "rgba(200,232,255,0.9)");
  g.addColorStop(1, "rgba(160,210,250,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, DROP, DROP);
}

function drawRuneRing(ctx: Ctx): void {
  drawEnchantRunes(ctx, RUNE_TEX / 2, RUNE_TEX / 2, RUNE_TEX / 2 - 4);
}

function drawRipple(ctx: Ctx): void {
  ctx.strokeStyle = "rgba(230,245,255,0.95)";
  ctx.lineWidth = 1.6;
  ctx.beginPath();
  ctx.ellipse(RIPPLE / 2, RIPPLE / 2, RIPPLE / 2 - 2, RIPPLE / 4 - 1, 0, 0, Math.PI * 2);
  ctx.stroke();
}

function drawWisp(ctx: Ctx): void {
  ctx.save();
  ctx.translate(WISP_W / 2, WISP_H / 2);
  ctx.scale(1, WISP_H / WISP_W);
  const g = ctx.createRadialGradient(0, 0, 2, 0, 0, WISP_W / 2);
  g.addColorStop(0, "rgba(240,242,236,0.9)");
  g.addColorStop(1, "rgba(240,242,236,0)");
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(0, 0, WISP_W / 2, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

/** 酒旗第 `frame` 格（往東吹）：旗桿＋橫桿，米白布、朱紅邊，中間一個酒罈圖示（不寫字）。 */
export function drawFlag(ctx: Ctx, frame: number): void {
  ctx.fillStyle = "#5a3a24";
  ctx.fillRect(POLE_X - 1.5, 2, 3, FLAG_H - 2);
  ctx.fillRect(POLE_X, 5, 22, 2.4);
  const top = 7;
  const h = 40;
  const x0 = POLE_X + 3;
  const x1 = POLE_X + 21;
  const dx = (y: number) => {
    const along = (y - top) / h;
    return flagWave(frame, along) * 4 + along * 3;
  };
  const steps = 8;
  ctx.beginPath();
  ctx.moveTo(x0, top);
  for (let i = 0; i <= steps; i++) {
    const y = top + (h * i) / steps;
    ctx.lineTo(x0 + dx(y), y);
  }
  // 下緣三個燕尾
  const by = top + h;
  const d = dx(by);
  ctx.lineTo(x0 + d + 4, by - 4);
  ctx.lineTo(x0 + d + 9, by + 1);
  ctx.lineTo(x0 + d + 13, by - 4);
  for (let i = steps; i >= 0; i--) {
    const y = top + (h * i) / steps;
    ctx.lineTo(x1 + dx(y), y);
  }
  ctx.closePath();
  ctx.fillStyle = "#f2e6c8";
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = "#b8322a";
  ctx.stroke();
  // 酒罈
  const cy = top + h * 0.45;
  const cx = (x0 + x1) / 2 + dx(cy);
  ctx.fillStyle = "#3a2a1e";
  ctx.beginPath();
  ctx.ellipse(cx, cy + 2, 5, 6, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillRect(cx - 2.5, cy - 6, 5, 3);
}

/** 放節點用的宿主（BattleRenderer 提供）。 */
export interface AmbientHost {
  art: ArtTextures;
  rows: RowStack;
  /** 放在 (x, y) 並跟著格子 `p` 抬高。 */
  place(node: Container, p: Pos, x: number, y: number): void;
  /** 格子左上角（含抬高）。 */
  origin(p: Pos): { x: number; y: number };
}

interface FireNode {
  seed: string;
  glow: Sprite;
  /** 光暈、火苗畫好時的縮放（呼吸、閃動在這上面乘）。 */
  gx: number;
  gy: number;
  flame: Sprite | null;
  fx: number;
  fy: number;
  small: boolean;
}

interface RingNode {
  seed: string;
  sprite: Sprite;
}

interface SprayNode {
  seed: string;
  x: number;
  y: number;
  reach: number;
  drop: number;
  /** 水珠畫好時的縮放（每幀乘上水珠自己的大小）。 */
  base: number;
  drops: Sprite[];
}

interface FlagNode {
  seed: string;
  sprite: Sprite;
}

export class AmbientLayer {
  /** 疊在高亮之上的一層（火光、燈光、薄霧）；BattleRenderer 放進世界圖層。 */
  readonly root = new Container();
  clock = 0;
  enabled = true;
  reduced = false;
  private wind: Wind = 1;
  private strength = 0.8;
  private width = 0;
  private height = 0;
  private key = "";
  private fires: FireNode[] = [];
  private grass: Array<{ seed: string; sprite: Sprite }> = [];
  private flags: FlagNode[] = [];
  private flagTex: Texture[] = [];
  private ripples: Array<{ seed: string; rings: Sprite[] }> = [];
  private wisps: Array<{ i: number; sprite: Sprite; boost: number }> = [];
  private rings: RingNode[] = [];
  private sprays: SprayNode[] = [];

  /** 重畫場景前（物件放進去之前）：清掉上一輪的節點，記下風向。 */
  begin(model: DrawModel): void {
    for (const c of this.root.removeChildren()) c.destroy({ children: true });
    this.fires = [];
    this.grass = [];
    this.flags = [];
    this.flagTex = [];
    this.ripples = [];
    this.wisps = [];
    this.rings = [];
    this.sprays = [];
    this.key = model.ambient?.key ?? `${model.region}:${model.width}x${model.height}`;
    this.wind = windOf(this.key);
    this.strength = windStrength(this.key, model.weather ?? "");
    this.width = model.width;
    this.height = model.height;
  }

  /** 物件放好之後：草叢、竹叢改成以底邊為軸（之後每幀斜切）。家具外觀、地面物件不擺。 */
  object(node: Container, o: ObjectDraw): void {
    if (o.kind !== "grass" || o.floor) return;
    const sprite = node.children.find((c): c is Sprite => c instanceof Sprite);
    if (sprite === undefined) return;
    sprite.anchor.set(0, 1);
    sprite.position.set(0, T);
    this.grass.push({ seed: `${this.key}:${o.x},${o.y}`, sprite });
  }

  /** 物件、單位都畫好之後：營火、燈籠、酒旗、水波、薄霧。 */
  draw(host: AmbientHost, model: DrawModel): void {
    const art = host.art;
    const glowTex = art.canvas("amb|glow", () => paint(GLOW, GLOW, drawGlow));
    const flameTex = art.canvas("amb|flame", () => paint(FLAME_W, FLAME_H, drawFlame));
    if (glowTex === null) return; // 沒有 DOM（單元測試）
    for (const f of model.ambient?.fires ?? []) this.addFire(host, glowTex, flameTex, f);
    this.drawLights(host, model, glowTex);
    this.drawEnchantRings(host, model);
    this.drawSprays(host, model);
    this.drawFlags(host, model);
    const rippleTex = art.canvas("amb|ripple", () => paint(RIPPLE, RIPPLE, drawRipple));
    if (rippleTex !== null) for (const t of model.tiles) if (t.terrain === "ice_hole") this.addRipple(host, rippleTex, t);
    const mist = mistLevel(model.region, model.weather ?? "");
    const wispTex = mist === null || model.scenery?.interior != null ? null : art.canvas("amb|wisp", () => paint(WISP_W, WISP_H, drawWisp));
    if (wispTex !== null && mist !== null) {
      const boost = mist.level === "fog" ? 1.6 : 1;
      for (let i = 0; i < mistCount(model.width, model.height); i++) {
        const sprite = new Sprite(wispTex);
        sprite.anchor.set(0.5);
        sprite.width = WISP_W;
        sprite.height = WISP_H;
        this.root.addChild(sprite);
        this.wisps.push({ i, sprite, boost });
      }
    }
    this.apply();
  }

  private addFire(host: AmbientHost, glowTex: Texture, flameTex: Texture | null, p: Pos): void {
    const o = host.origin(p);
    const cx = o.x + T / 2;
    const cy = o.y + T * 0.62;
    const glow = new Sprite(glowTex);
    glow.anchor.set(0.5);
    glow.position.set(cx, cy - 6);
    glow.width = GLOW * 1.4;
    glow.height = GLOW * 1.1;
    glow.blendMode = "add";
    this.root.addChild(glow);
    let flame: Sprite | null = null;
    if (flameTex !== null) {
      flame = new Sprite(flameTex);
      flame.anchor.set(0.5, 1);
      flame.position.set(cx, cy + 1);
      flame.width = FLAME_W;
      flame.height = FLAME_H;
      this.root.addChild(flame);
    }
    this.fires.push({ seed: `${this.key}:${p.x},${p.y}`, glow, gx: glow.scale.x, gy: glow.scale.y, flame, fx: flame?.scale.x ?? 1, fy: flame?.scale.y ?? 1, small: false });
  }

  private addLight(glowTex: Texture, x: number, y: number, seed: string, size: number): void {
    const glow = new Sprite(glowTex);
    glow.anchor.set(0.5);
    glow.position.set(x, y);
    glow.width = size;
    glow.height = size;
    glow.blendMode = "add";
    this.root.addChild(glow);
    this.fires.push({ seed, glow, gx: glow.scale.x, gy: glow.scale.y, flame: null, fx: 1, fy: 1, small: true });
  }

  /** 酒館屋簷下的燈籠（位置同 townArt 的 `lantern`）與室內燭台的光。 */
  private drawLights(host: AmbientHost, model: DrawModel, glowTex: Texture): void {
    const scenery = model.scenery;
    if (scenery === undefined) return;
    // 6Q-1：燈籠的位置和 townArt 畫燈籠用同一個公式（lanternCenters），再照 sceneryLayer 放建築的方式換成場景座標
    const k = T / BUILDING_ART_T;
    for (const b of scenery.buildings) {
      for (const p of lanternLights(b, host.origin({ x: b.x, y: b.y + b.spec.h - 1 }).y - (b.y + b.spec.h - 1) * T, k)) {
        this.addLight(glowTex, p.x, p.y, `${this.key}:lantern:${p.cell}`, 38);
      }
    }
    for (const [cell, spec] of Object.entries(scenery.furniture).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))) {
      if (spec.look !== "candle") continue;
      const [x, y] = cell.split(",").map(Number) as [number, number];
      const o = host.origin({ x, y });
      this.addLight(glowTex, o.x + T / 2, o.y + (8 * T) / 52, `${this.key}:candle:${cell}`, 34);
    }
  }

  /** 附魔台的符文環（6V-3）：從正上方看的符文圈壓扁成透視（外層 Container 縮 y），裡面的 Sprite 慢慢轉。 */
  private drawEnchantRings(host: AmbientHost, model: DrawModel): void {
    const furniture = model.scenery?.furniture ?? {};
    const cells = Object.entries(furniture)
      .filter(([, spec]) => spec.look === "enchant")
      .map(([cell]) => cell)
      .sort();
    if (cells.length === 0) return;
    const tex = host.art.canvas("amb|runes", () => paint(RUNE_TEX, RUNE_TEX, drawRuneRing));
    if (tex === null) return;
    for (const cell of cells) {
      const [x, y] = cell.split(",").map(Number) as [number, number];
      const lift = host.origin({ x, y }).y - y * T;
      const c = enchantRingCenter({ x, y }, lift);
      const holder = new Container();
      holder.position.set(c.x, c.y);
      holder.scale.set(1, c.ry / c.rx);
      const sprite = new Sprite(tex);
      sprite.anchor.set(0.5);
      sprite.width = c.rx * 2;
      sprite.height = c.rx * 2;
      sprite.blendMode = "add";
      holder.addChild(sprite);
      this.root.addChild(holder);
      this.rings.push({ seed: `${this.key}:enchant:${cell}`, sprite });
    }
  }

  /** 許願池的噴水（6V-4）：左右兩道水弧＋中央短水柱，每顆水珠一個小 Sprite。 */
  private drawSprays(host: AmbientHost, model: DrawModel): void {
    const pools = (model.scenery?.buildings ?? []).filter((b) => b.spec.kind === "fountain");
    if (pools.length === 0) return;
    const tex = host.art.canvas("amb|drop", () => paint(DROP, DROP, drawDrop));
    if (tex === null) return;
    for (const b of pools) {
      const bottom = b.y + b.spec.h - 1;
      const sp = fountainSpout(b, host.origin({ x: b.x, y: bottom }).y - bottom * T);
      const seed = `${this.key}:spray:${b.x},${b.y}`;
      const drops = fountainSpray(seed, 0, sp.reach, sp.drop).map(() => {
        const s = new Sprite(tex);
        s.anchor.set(0.5);
        s.width = DROP * sp.scale;
        s.height = DROP * sp.scale;
        this.root.addChild(s);
        return s;
      });
      this.sprays.push({ seed, x: sp.x, y: sp.y, reach: sp.reach, drop: sp.drop, base: drops[0]?.scale.x ?? 1, drops });
    }
  }

  /** 酒館門面右端一面酒旗（旗桿在建築最下一列的右緣）。 */
  private drawFlags(host: AmbientHost, model: DrawModel): void {
    const taverns = (model.scenery?.buildings ?? []).filter((b) => b.spec.kind === "tavern");
    if (taverns.length === 0) return;
    this.flagTex = [];
    for (let f = 0; f < FLAG_FRAMES; f++) {
      const tex = host.art.canvas(`amb|flag|${f}`, () => paint(FLAG_W, FLAG_H, (ctx) => drawFlag(ctx, f)));
      if (tex === null) return;
      this.flagTex.push(tex);
    }
    for (const b of taverns) {
      const bottom = { x: b.x, y: b.y + b.spec.h - 1 };
      const sprite = new Sprite(this.flagTex[0]);
      sprite.anchor.set(POLE_X / FLAG_W, 1);
      sprite.width = FLAG_W;
      sprite.height = FLAG_H;
      if (this.wind < 0) sprite.scale.x *= -1; // 往西吹：以旗桿為軸翻過來
      host.rows.row(bottom.y).objects.addChild(sprite);
      host.place(sprite, bottom, (b.x + b.spec.w) * T - 8, (bottom.y + 1) * T - 4);
      this.flags.push({ seed: `${this.key}:flag:${b.x},${b.y}`, sprite });
    }
  }

  private addRipple(host: AmbientHost, tex: Texture, p: Pos): void {
    const rings: Sprite[] = [];
    for (let k = 0; k < 2; k++) {
      const s = new Sprite(tex);
      s.anchor.set(0.5);
      host.rows.row(p.y).deco.addChild(s);
      host.place(s, p, p.x * T + T / 2, p.y * T + T * 0.55);
      rings.push(s);
    }
    this.ripples.push({ seed: `${this.key}:${p.x},${p.y}`, rings });
  }

  /** 推進 `dt` 毫秒並套用。減少動態或關掉時不動（停在畫好時的樣子）。 */
  tick(dt: number): void {
    if (!this.enabled || this.reduced) return;
    this.clock += dt;
    this.apply();
  }

  /** 照目前的時鐘擺好所有節點（減少動態時用第 0 毫秒）。 */
  private apply(): void {
    const ms = this.enabled && !this.reduced ? this.clock : 0;
    for (const f of this.fires) {
      if (f.glow.destroyed) continue;
      const k = flickerAt(f.seed, ms, f.small);
      f.glow.alpha = k.glow;
      f.glow.scale.set(f.gx * k.glowScale, f.gy * k.glowScale);
      if (f.flame !== null && !f.flame.destroyed) {
        f.flame.scale.set(f.fx * k.sx, f.fy * k.sy);
        f.flame.skew.x = this.wind * 0.04 + k.skew; // 頂端往下風偏一點，再加上閃動
      }
    }
    for (const g of this.grass) if (!g.sprite.destroyed) g.sprite.skew.x = swayAt(g.seed, ms, this.wind, this.strength);
    for (const f of this.flags) {
      if (f.sprite.destroyed) continue;
      const tex = this.flagTex[flagFrame(f.seed, ms, this.strength)];
      if (tex !== undefined && f.sprite.texture !== tex) f.sprite.texture = tex;
    }
    for (const r of this.ripples) {
      ripplesAt(r.seed, ms).forEach((q, i) => {
        const s = r.rings[i];
        if (s === undefined || s.destroyed) return;
        s.scale.set((T * 0.85 * q.scale) / s.texture.width);
        s.alpha = q.alpha;
      });
    }
    for (const r of this.rings) {
      if (r.sprite.destroyed) continue;
      r.sprite.rotation = enchantRingAngle(r.seed, ms);
      r.sprite.alpha = enchantRingGlow(r.seed, ms);
    }
    for (const sp of this.sprays) {
      fountainSpray(sp.seed, ms, sp.reach, sp.drop).forEach((d, i) => {
        const s = sp.drops[i];
        if (s === undefined || s.destroyed) return;
        s.position.set(sp.x + d.x, sp.y + d.y);
        s.alpha = d.alpha;
        s.scale.set(sp.base * d.scale);
      });
    }
    for (const w of this.wisps) {
      if (w.sprite.destroyed) continue;
      const m = mistAt(this.key, w.i, ms, this.wind, this.width, this.height);
      w.sprite.position.set(m.x * T, m.y * T);
      w.sprite.alpha = Math.min(0.4, m.alpha * w.boost);
    }
  }

  /** 目前有幾個會動的節點（測試、量測用）。 */
  get counts(): { fires: number; grass: number; flags: number; ripples: number; wisps: number; rings: number; sprays: number } {
    return {
      fires: this.fires.length,
      grass: this.grass.length,
      flags: this.flags.length,
      ripples: this.ripples.length,
      wisps: this.wisps.length,
      rings: this.rings.length,
      sprays: this.sprays.length,
    };
  }
}
