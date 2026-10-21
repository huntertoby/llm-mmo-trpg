// 單位在地圖上的畫法（從 `BattleRenderer` 抽出，Phase 3-18b）：
// 底圈 → 朝向尖角 → 行動中虛線圈 → 小人 → 代號小標 → 倒地徽章 → 狀態徽章 → 血條。
// 倒地（docs/art/3-18倒地與高度.md 第 1 節）：只有小人套透明度與去色，Container 不透明，徽章與代號維持清楚。
import { ColorMatrixFilter, Container, Graphics, Sprite, Texture } from "pixi.js";
import type { UnitDraw } from "../battle/drawModel";
import { ringArrow } from "../battle/facing";
import { TILE_SIZE } from "../battle/geometry";
import { HIGHLIGHT } from "../battle/glossary";
import { resolveDoll } from "./appearance";
import { RING } from "./artPalette";
import type { ArtTextures } from "./artTextures";
import { label } from "./labels";
import { DOLL_FOOT_Y, DOLL_H, DOLL_W } from "./paperdoll";
import { statusTile, tileCanvas } from "./skillIcon";
import { downedLook, pulseAlpha, statusBadges, type DownedLook, type StatusBadge } from "./unitLook";

const T = TILE_SIZE;

/** 會閃動的節點（可復活單位腳下的綠色虛線圈）；由 `BattleRenderer` 的 ticker 驅動。 */
export class Pulses {
  private items: Array<{ node: Graphics; look: NonNullable<DownedLook["dashed"]> }> = [];
  private clock = 0;

  clear(): void {
    this.items = [];
  }

  add(node: Graphics, look: NonNullable<DownedLook["dashed"]>): void {
    this.items.push({ node, look });
    node.alpha = pulseAlpha(look, this.clock);
  }

  tick(deltaMs: number): void {
    this.clock += deltaMs;
    for (const { node, look } of this.items) if (!node.destroyed) node.alpha = pulseAlpha(look, this.clock);
  }
}

function hpColor(ratio: number): number {
  if (ratio > 0.5) return 0x4cd964;
  if (ratio > 0.25) return 0xffcc00;
  return 0xff3b30;
}

/** 橢圓虛線圈：以短線段交錯畫出。 */
function dashedEllipse(cy: number, rx: number, ry: number, color: number, width = 2.5): Graphics {
  const g = new Graphics();
  const n = 28;
  for (let i = 0; i < n; i += 2) {
    const a0 = (i / n) * Math.PI * 2;
    const a1 = ((i + 1) / n) * Math.PI * 2;
    g.moveTo(Math.cos(a0) * rx, cy + Math.sin(a0) * ry).lineTo(Math.cos(a1) * rx, cy + Math.sin(a1) * ry);
  }
  return g.stroke({ width, color });
}

/** 倒地徽章（左上角，直徑約 18px）：愛心（救得回來）或墓碑（救不回）；不寫字。 */
function downedBadge(look: NonNullable<DownedLook["badge"]>): Graphics {
  const g = new Graphics();
  g.circle(0, 0, 9).fill({ color: 0x000000, alpha: 0.8 }).stroke({ width: 2, color: look.edge });
  if (look.kind === "heart") {
    g.moveTo(0, 5.5)
      .bezierCurveTo(-8, 0, -4.5, -6.5, 0, -2.5)
      .bezierCurveTo(4.5, -6.5, 8, 0, 0, 5.5)
      .fill(look.glyph);
    g.rect(-0.9, -2.6, 1.8, 5.2).fill(0x0a200a);
    g.rect(-2.6, -0.9, 5.2, 1.8).fill(0x0a200a);
  } else {
    g.moveTo(-4, 5).lineTo(-4, -1).arc(0, -1, 4, Math.PI, 0).lineTo(4, 5).closePath().fill(look.glyph);
    g.rect(-0.8, -3.2, 1.6, 5).fill(0x222222);
    g.rect(-2.4, -1.8, 4.8, 1.5).fill(0x222222);
  }
  return g;
}

const statusTextures = new Map<string, Texture>();

/** 狀態部件的貼圖（技能部件庫的狀態圖示；每種狀態共用一張）。沒有 DOM 時回傳 `null`。 */
function statusTexture(statusId: string): Texture | null {
  if (typeof document === "undefined") return null;
  const hit = statusTextures.get(statusId);
  if (hit !== undefined) return hit;
  const tex = Texture.from(tileCanvas(statusTile(statusId), 24));
  statusTextures.set(statusId, tex);
  return tex;
}

/** 狀態徽章：黑底圓＋狀態顏色外框＋部件庫的狀態圖示；數字（剩餘次數或回合）在圖示右下。 */
function statusBadge(badge: StatusBadge): Container {
  const c = new Container();
  c.position.set(badge.at.x * T, badge.at.y * T);
  c.addChild(new Graphics().circle(0, 0, 10).fill({ color: 0x000000, alpha: 0.8 }).stroke({ width: 2, color: badge.color }));
  const tex = statusTexture(badge.statusId);
  if (tex !== null) {
    const icon = new Sprite(tex);
    icon.anchor.set(0.5);
    icon.width = 16;
    icon.height = 16;
    c.addChild(icon);
  }
  const num = label(String(badge.count), 10, 0xffffff, true);
  num.anchor.set(0.5);
  num.position.set(8, 8);
  num.style.stroke = { color: 0x000000, width: 3 };
  c.addChild(num);
  return c;
}

function doll(art: ArtTextures, u: UnitDraw, look: DownedLook, feet: number, r: number): Sprite | Graphics {
  const spec = resolveDoll({ template: u.template, team: u.team, summon: u.summon, totem: u.totem, weaponId: u.weaponId, weaponClass: u.weaponClass });
  const texture = art.figure(spec, u.facing, u.downed);
  if (texture === null) return new Graphics().circle(0, 0, r).fill(u.fill); // 無法產生貼圖：退回色塊
  const sprite = new Sprite(texture);
  const k = T / 52; // 身高約 46px 在 52px 格子裡縮放 1.0
  sprite.anchor.set(0.5, DOLL_FOOT_Y / DOLL_H);
  sprite.width = DOLL_W * k;
  sprite.height = DOLL_H * k;
  sprite.position.set(0, feet);
  sprite.alpha = look.dollAlpha;
  if (look.grayscale) {
    const gray = new ColorMatrixFilter();
    gray.desaturate();
    sprite.filters = [gray];
  }
  return sprite;
}

function summonBadge(u: UnitDraw): Container {
  // 右上角小徽章：圖騰標「圖」，其他標剩餘輪數
  const c = new Container();
  const badgeText = u.totem ? "圖" : String(u.remaining ?? "");
  const badge = new Graphics().circle(T * 0.3, -T * 0.3, 9).fill({ color: 0x000000, alpha: 0.75 }).stroke({ width: 1, color: HIGHLIGHT.summon });
  const badgeLabel = label(badgeText, 12, HIGHLIGHT.summon, true);
  badgeLabel.anchor.set(0.5);
  badgeLabel.position.set(T * 0.3, -T * 0.3);
  c.addChild(badge, badgeLabel);
  return c;
}

function hpBar(u: UnitDraw): Graphics {
  const w = T * 0.8;
  const bar = new Graphics().rect(-w / 2, T * 0.36, w, 5).fill(0x000000);
  bar.rect(-w / 2, T * 0.36, w * u.hpRatio, 5).fill(hpColor(u.hpRatio));
  if (u.shieldRatio > 0) bar.rect(-w / 2, T * 0.36 - 3, w * u.shieldRatio, 2).fill(0x9fd8ff);
  return bar;
}

/** 一個單位的所有圖層（圖層順序見檔頭）；位置由呼叫端放到格子中心。 */
export function buildUnitSprite(art: ArtTextures, pulses: Pulses, u: UnitDraw): Container {
  const c = new Container();
  const r = T * 0.32;
  const look = downedLook(u.downed, u.revivable);
  const teamRing = u.summon ? RING.summon : RING[u.team];
  const ring = look.ring ?? teamRing;
  const feet = T * 0.23; // 腳底（相對格子中心）
  const cy = feet - 1;
  const rx = T * 0.36;
  const ry = T * 0.15;
  const g = new Graphics();
  g.ellipse(0, cy, rx, ry).fill({ color: ring.fill, alpha: 0.8 }).stroke({ width: 1.5, color: ring.stroke });
  if (u.hero) g.ellipse(0, cy, rx + 2.5, ry + 2).stroke({ width: 2, color: HIGHLIGHT.hero });
  c.addChild(g);
  if (look.dashed !== null) {
    const dashed = dashedEllipse(cy, T * 0.4, T * 0.18, look.dashed.color, 2.5);
    c.addChild(dashed);
    pulses.add(dashed, look.dashed);
  }
  if (!u.downed) c.addChild(new Graphics().poly(ringArrow(u.facing, 0, cy, rx, ry, 5)).fill(0xffffff).stroke({ width: 1, color: 0x000000 }));
  if (u.active) c.addChild(dashedEllipse(cy, rx + 6, ry + 4, HIGHLIGHT.active));
  c.addChild(doll(art, u, look, feet, r));
  if (u.summon) c.addChild(summonBadge(u));
  const tag = new Graphics().circle(-T * 0.37, T * 0.22, 8).fill({ color: 0x000000, alpha: 0.78 }).stroke({ width: 1.5, color: ring.stroke });
  const marker = label(u.marker, 12, 0xffffff, true);
  marker.anchor.set(0.5);
  marker.position.set(-T * 0.37, T * 0.22);
  c.addChild(tag, marker);
  if (look.badge !== null) {
    const badge = downedBadge(look.badge);
    badge.position.set(-T * 0.5 + 11, -T * 0.5 + 11);
    c.addChild(badge);
  }
  for (const b of statusBadges(u)) c.addChild(statusBadge(b));
  c.addChild(hpBar(u));
  return c;
}
