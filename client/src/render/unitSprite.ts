// 單位在地圖上的畫法（從 `BattleRenderer` 抽出，Phase 3-18b）：
// 底圈 → 朝向尖角 → 行動中虛線圈 → 小人 → 代號小標 → 倒地徽章 → 狀態徽章 → 血條。
// 倒地（docs/art/3-18倒地與高度.md 第 1 節）：只有小人套透明度與去色，Container 不透明，徽章與代號維持清楚。
import { ColorMatrixFilter, Container, Graphics, Sprite, Texture } from "pixi.js";
import type { UnitDraw } from "../battle/drawModel";
import { ringArrow } from "../battle/facing";
import { TILE_SIZE } from "../battle/geometry";
import { HIGHLIGHT } from "../battle/glossary";
import { resolveDoll, type DollSpec } from "./appearance";
import { RING } from "./artPalette";
import type { ArtTextures } from "./artTextures";
import { label } from "./labels";
import { DOLL_FOOT_Y, DOLL_H, DOLL_SCALE, DOLL_W, SUMMON_FOOT_Y, SUMMON_H, SUMMON_W } from "./paperdoll";
import { CHARGING } from "../battle/followup";
import { TIME_BOMB } from "../battle/bombs";
import { statusTile, tileCanvas } from "./skillIcon";
import { bodyEffects, bodyOver, bodyUnder, CONCEALED, CONCEALED_ALPHA, effectsKey, hasOverEffect, hasUnderEffect, ROW_ICON, statusIconCanvas, statusIconKey, statusRowLayout, type BodyEffects } from "./statusIcon";
import { fontEpoch } from "./fontLoad";
import { AURA_H, AURA_W, FORM_FOOT_Y, FORM_H, FORM_W, formArtOf, formAuraColor, formAuraRadius, formHeroColor, formRowRise } from "./inkForm";
import { hasNoRing, humanoidSpec, resolveSummonLook, type ResolvedLook } from "./summonArt";
import { SUMMON_BADGE_FONT, SUMMON_BADGE_RADIUS, downedLook, infusedBadge, pulseAlpha, statusBadges, summonBadgeOffset, type DownedLook, type InfusedBadge, type StatusBadge } from "./unitLook";

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

/** 待施放的灌注技能（Phase 3-33d）：黑底圓＋紫框＋「灌」。 */
function infusedMark(badge: InfusedBadge): Container {
  const c = new Container();
  c.position.set(badge.at.x * T, badge.at.y * T);
  c.addChild(new Graphics().circle(0, 0, 9).fill({ color: 0x000000, alpha: 0.8 }).stroke({ width: 2, color: badge.color }));
  const glyph = label(badge.glyph, 11, badge.color, true);
  glyph.anchor.set(0.5);
  c.addChild(glyph);
  return c;
}

/** 召喚物的外觀（Phase 3-33h1）：有外觀欄位的召喚物才有；一般單位與舊資料回傳 `null`（走原本的紙娃娃）。 */
function summonLookOf(u: UnitDraw): ResolvedLook | null {
  return u.summon && u.summonLook != null ? resolveSummonLook(u.summonLook) : null;
}

/** 人形召喚物用的紙娃娃規格：骷髏沿用範本外觀，殘影複製召喚者（找不到時用預設戰士）。 */
function summonHumanoidSpec(u: UnitDraw, look: ResolvedLook): DollSpec {
  const skeleton = resolveDoll({ template: "summon_skeleton_warrior", team: u.team, summon: true, weaponId: u.weaponId, weaponClass: u.weaponClass });
  const owner = u.copyOf !== undefined ? resolveDoll(u.copyOf) : resolveDoll({ template: "hero_fighter", team: "ally", summon: false });
  return humanoidSpec(look, skeleton, owner);
}

/** 形態外觀（3J-5）：單位有形態、而且認得外觀 id 時回傳畫法 id、主角主色與元素；否則 `null`（形態不認得時仍畫原角色紙娃娃）。 */
function formArtOfUnit(u: UnitDraw, spec: DollSpec): { id: string; hero: string; element: string | null } | null {
  if (u.form == null || u.summon) return null;
  const f = formArtOf(u.form.look);
  if (f === null) return null;
  return { id: f.id, hero: formHeroColor(spec.gear.body?.color, spec.gear.cloak?.color), element: u.form.element };
}

/** 形態的小人：形態貼圖取代紙娃娃（同樣的腳底錨點與縮放基準）；貼圖畫不出來時回傳 `null`。 */
function formDoll(art: ArtTextures, u: UnitDraw, look: DownedLook, feet: number, form: { id: string; hero: string; element: string | null }): Sprite | null {
  const texture = art.form(form.id, form.hero, form.element, u.facing, u.downed);
  if (texture === null) return null;
  const sprite = new Sprite(texture);
  const k = (T / 52) * DOLL_SCALE;
  sprite.anchor.set(0.5, FORM_FOOT_Y / FORM_H);
  sprite.width = FORM_W * k;
  sprite.height = FORM_H * k;
  sprite.position.set(0, feet);
  sprite.alpha = look.dollAlpha * (u.statusIds?.includes(CONCEALED) === true ? CONCEALED_ALPHA : 1);
  if (look.grayscale) {
    const gray = new ColorMatrixFilter();
    gray.desaturate();
    sprite.filters = [gray];
  }
  return sprite;
}

/** 腳下的形態光環（手繪虛線橢圓＋18% 填色）：元素色、無元素 #9a86ff；不認得的形態也畫。 */
function formAuraSprite(art: ArtTextures, u: UnitDraw, feet: number): Sprite | null {
  if (u.form == null || u.summon) return null;
  const tex = art.formAura(formAuraColor(u.form.element), formAuraRadius(u.form.look, DOLL_SCALE));
  if (tex === null) return null;
  const k = T / 52;
  const s = new Sprite(tex);
  s.anchor.set(0.5);
  s.width = AURA_W * k;
  s.height = AURA_H * k;
  s.position.set(0, feet);
  return s;
}

function doll(art: ArtTextures, u: UnitDraw, look: DownedLook, feet: number, r: number): Sprite | Graphics {
  const sl = summonLookOf(u);
  const spec = resolveDoll({ template: u.template, team: u.team, summon: u.summon, totem: u.totem, dollLook: u.dollLook, raceLook: u.raceLook, weaponId: u.weaponId, weaponClass: u.weaponClass, equipment: u.equipment, attackElement: u.attackElement });
  const form = formArtOfUnit(u, spec);
  const formSprite = form === null ? null : formDoll(art, u, look, feet, form);
  if (formSprite !== null) return formSprite;
  // 倒地的人形召喚物沿用紙娃娃的躺下姿勢；其他體型（圖騰、構造體、植物…）不躺下
  const useSummonArt = sl !== null && !(u.downed && sl.body === "humanoid");
  const texture = useSummonArt ? art.summon(sl, u.facing, sl.body === "humanoid" ? summonHumanoidSpec(u, sl) : null) : art.figure(spec, u.facing, u.downed);
  if (texture === null) return new Graphics().circle(0, 0, r).fill(u.fill); // 無法產生貼圖：退回色塊
  const sprite = new Sprite(texture);
  // C 骨架（人形與紙娃娃）：52px 格縮放約 0.74，人約 40px 高；非人形召喚物沿用舊的 64×64 畫布與縮放 1.0
  const humanoid = sl === null || sl.body === "humanoid";
  const k = (T / 52) * (humanoid ? DOLL_SCALE : 1);
  const [w, h, footY] = humanoid ? [DOLL_W, DOLL_H, DOLL_FOOT_Y] : [SUMMON_W, SUMMON_H, SUMMON_FOOT_Y];
  sprite.anchor.set(0.5, footY / h);
  sprite.width = w * k;
  sprite.height = h * k;
  sprite.position.set(0, feet);
  sprite.alpha = look.dollAlpha * (u.statusIds?.includes(CONCEALED) === true ? CONCEALED_ALPHA : 1);
  if (look.grayscale) {
    const gray = new ColorMatrixFilter();
    gray.desaturate();
    sprite.filters = [gray];
  }
  return sprite;
}

function summonBadge(u: UnitDraw): Container {
  // 右下角小徽章（血條上方，不擋漂浮靈的上緣）：圖騰標「圖」，其他標剩餘輪數；撞到炸彈徽章時往左 16px
  const c = new Container();
  const badgeText = u.totem ? "圖" : String(u.remaining ?? "");
  const at = summonBadgeOffset(u, T);
  const badge = new Graphics().circle(at.x, at.y, SUMMON_BADGE_RADIUS).fill({ color: 0x000000, alpha: 0.75 }).stroke({ width: 1, color: HIGHLIGHT.summon });
  const badgeLabel = label(badgeText, SUMMON_BADGE_FONT, HIGHLIGHT.summon, true);
  badgeLabel.anchor.set(0.5);
  badgeLabel.position.set(at.x, at.y);
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

// ---- 身上特效與頭頂狀態列（Phase 3-36a）----

const FX_W = 80;
const FX_H = 90;
const FX_FEET = 70; // 特效畫布裡腳底的 y（虛擬格 52px 為單位）
const FX_DPR = 2;
const effectTextures = new Map<string, Texture>();

/** 身上特效的貼圖（`under` ＝ 腳下、`over` ＝ 身上；同一組特效共用一張）。沒有 DOM 時回傳 `null`。 */
function effectTexture(kind: "under" | "over", e: BodyEffects): Texture | null {
  if (typeof document === "undefined") return null;
  const key = `${kind}|${effectsKey(e)}`;
  const hit = effectTextures.get(key);
  if (hit !== undefined) return hit;
  const canvas = document.createElement("canvas");
  canvas.width = FX_W * FX_DPR;
  canvas.height = FX_H * FX_DPR;
  const ctx = canvas.getContext("2d");
  if (ctx === null) return null;
  ctx.scale(FX_DPR, FX_DPR);
  if (kind === "under") bodyUnder(ctx, e, FX_W / 2, FX_FEET);
  else bodyOver(ctx, e, FX_W / 2, FX_FEET);
  const tex = Texture.from(canvas);
  effectTextures.set(key, tex);
  return tex;
}

function effectSprite(kind: "under" | "over", e: BodyEffects, feet: number): Sprite | null {
  const tex = effectTexture(kind, e);
  if (tex === null) return null;
  const k = T / 52;
  const s = new Sprite(tex);
  s.anchor.set(0.5, FX_FEET / FX_H);
  s.width = FX_W * k;
  s.height = FX_H * k;
  s.position.set(0, feet);
  return s;
}

const rowTextures = new Map<string, Texture>();

function rowIconTexture(id: string): Texture | null {
  const canvas = statusIconCanvas(id, ROW_ICON);
  if (canvas === null) return null;
  const key = `${statusIconKey(id, ROW_ICON)}|${fontEpoch()}`;
  const hit = rowTextures.get(key);
  if (hit !== undefined) return hit;
  const tex = Texture.from(canvas);
  rowTextures.set(key, tex);
  return tex;
}

/** 頭頂狀態列的圖示中心（相對格子中心）：略低於格子頂端，圖示上緣不蓋住上一格單位的血條。 */
const ROW_Y = -T / 2 + 5.5;
/** 有「灌」徽章（左上）時，狀態列最多 2 格並右移，避免重疊。 */
const ROW_INFUSED_SHIFT = 9;

/** 頭頂狀態列：最多 3 個圖示（超過時 2 個加「+N」），倒下的單位不畫。炸彈與蓄力已有自己的徽章，不重複。 */
function statusRow(u: UnitDraw): Container | null {
  if (u.downed) return null;
  const ids = (u.statusIds ?? []).filter((id) => id !== TIME_BOMB && id !== CHARGING);
  const infused = u.infused === true;
  const items = statusRowLayout(ids, infused ? 2 : 3, ROW_ICON);
  if (items.length === 0) return null;
  const row = new Container();
  row.position.set(infused ? ROW_INFUSED_SHIFT : 0, ROW_Y - (u.form != null && !u.summon ? formRowRise(u.form.look, T, DOLL_SCALE) : 0));
  for (const item of items) {
    if (item.kind === "icon") {
      const tex = rowIconTexture(item.id);
      if (tex === null) continue;
      const icon = new Sprite(tex);
      icon.anchor.set(0.5);
      icon.width = ROW_ICON;
      icon.height = ROW_ICON;
      icon.position.set(item.x, 0);
      row.addChild(icon);
    } else {
      const half = ROW_ICON / 2;
      row.addChild(new Graphics().roundRect(item.x - half, -half, ROW_ICON, ROW_ICON, 4).fill({ color: 0x0c0c10, alpha: 0.88 }).stroke({ width: 1.5, color: 0x9aa0aa }));
      const more = label(`+${item.extra}`, 9, 0xffffff, true);
      more.anchor.set(0.5);
      more.position.set(item.x, 0.5);
      row.addChild(more);
    }
  }
  return row;
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
  const sl = summonLookOf(u);
  const noRing = sl !== null && hasNoRing(sl); // 土牆沒有底圈
  if (!noRing) g.ellipse(0, cy, rx, ry).fill({ color: ring.fill, alpha: 0.8 }).stroke({ width: 1.5, color: ring.stroke });
  if (u.hero) g.ellipse(0, cy, rx + 2.5, ry + 2).stroke({ width: 2, color: HIGHLIGHT.hero });
  c.addChild(g);
  if (look.dashed !== null) {
    const dashed = dashedEllipse(cy, T * 0.4, T * 0.18, look.dashed.color, 2.5);
    c.addChild(dashed);
    pulses.add(dashed, look.dashed);
  }
  if (!u.downed && !noRing) c.addChild(new Graphics().poly(ringArrow(u.facing, 0, cy, rx, ry, 5)).fill(0xffffff).stroke({ width: 1, color: 0x000000 }));
  if (u.active) c.addChild(dashedEllipse(cy, rx + 6, ry + 4, HIGHLIGHT.active));
  const aura = formAuraSprite(art, u, cy);
  if (aura !== null) c.addChild(aura);
  const effects = u.downed ? null : bodyEffects(u.statusIds ?? []);
  if (effects !== null && hasUnderEffect(effects)) {
    const under = effectSprite("under", effects, feet);
    if (under !== null) c.addChild(under);
  }
  c.addChild(doll(art, u, look, feet, r));
  if (effects !== null && hasOverEffect(effects)) {
    const over = effectSprite("over", effects, feet);
    if (over !== null) c.addChild(over);
  }
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
  const infused = infusedBadge(u);
  if (infused !== null) c.addChild(infusedMark(infused));
  c.addChild(hpBar(u));
  const row = statusRow(u);
  if (row !== null) c.addChild(row);
  return c;
}
