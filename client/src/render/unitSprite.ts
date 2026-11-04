// 單位在地圖上的畫法（從 `BattleRenderer` 抽出，Phase 3-18b）：
// 底圈 → 朝向尖角 → 行動中虛線圈 → 小人 → 代號小標 → 倒地徽章 → 狀態徽章 → 血條。
// 倒地（docs/art/3-18倒地與高度.md 第 1 節）：只有小人套透明度與去色，Container 不透明，徽章與代號維持清楚。
import { ColorMatrixFilter, Container, Graphics, Sprite, Texture } from "pixi.js";
import type { UnitDraw } from "../battle/drawModel";
import { ringArrow } from "../battle/facing";
import { TILE_SIZE } from "../battle/geometry";
import { HIGHLIGHT } from "../battle/glossary";
import { resolveDoll, type DollSpec, type GearItem } from "./appearance";
import { RING } from "./artPalette";
import type { ArtTextures } from "./artTextures";
import { label } from "./labels";
import { DOLL_FOOT_Y, DOLL_H, DOLL_SCALE, DOLL_W, SUMMON_FOOT_Y, SUMMON_H, SUMMON_SCALE, SUMMON_W } from "./paperdoll";
import { CHARGING } from "../battle/followup";
import { TIME_BOMB } from "../battle/bombs";
import { statusTile, tileCanvas } from "./skillIcon";
import { bodyEffects, bodyOver, bodyUnder, CONCEALED, CONCEALED_ALPHA, effectsKey, hasOverEffect, hasUnderEffect, statusIconCanvas, statusIconKey, sortStatuses, type BodyEffects } from "./statusIcon";
import { fontEpoch } from "./fontLoad";
import { AURA_H, AURA_W, FORM_FOOT_Y, FORM_H, FORM_W, formArtOf, formAuraColor, formAuraRadius, formHeroColor } from "./inkForm";
import { hasNoRing, humanoidSpec, resolveSummonLook, type ResolvedLook } from "./summonArt";
import { CREATURE_FOOT_Y, CREATURE_H, CREATURE_W, ELITE_SCALE, HUGE_FIELD_SCALE, bodyTop, drawHumanoidFx, knownAffixes, resolveCreature, type ResolvedCreature } from "./inkCreature";
import { DOLL_HEAD_TOP } from "./inkDoll";
import { UNIT_HEADROOM } from "../battle/elevation";
import { SUMMON_BADGE_FONT, SUMMON_BADGE_RADIUS, downedLook, infusedBadge, pulseAlpha, statusBadges, summonBadgeOffset, type DownedLook, type InfusedBadge, type StatusBadge } from "./unitLook";
import { splitCreatureOffset, type CreaturePose } from "./creaturePose";
import type { InkPose } from "./inkPose";
import { proneBody } from "./motionClips";
import { downedCreaturePose } from "./reactClips";

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

/** 異形外觀（Phase 5A-ART1）：`doll_look.creature` 有值時（含召喚物，優先於 `summon_look`）；沒有時 `null`。大小用戰場的（5A-ART5）。 */
export function creatureOf(u: UnitDraw): ResolvedCreature | null {
  const look = u.dollLook?.creature;
  if (look == null) return null;
  return resolveCreature({ look, statusIds: u.statusIds, elite: u.elite, affixes: u.dollLook?.affixes, rarity: u.dollLook?.rarity, field: true });
}

/** 異形在戰場上的額外縮放：頭目（huge）再 ×0.9。 */
export function creatureFieldScale(u: Pick<UnitDraw, "dollLook">): number {
  return u.dollLook?.creature?.size === "huge" ? HUGE_FIELD_SCALE : 1;
}

/** 人形在戰場上的大小（Phase 5A-ART5，`DollLook.scale`；道童 0.9）：沒有或超出 0.5～1.5 時當作 1。 */
export function humanoidLookScale(u: Pick<UnitDraw, "dollLook">): number {
  const s = u.dollLook?.scale;
  return s != null && s >= 0.5 && s <= 1.5 ? s : 1;
}

/**
 * 異形只畫側面（docs/art/敵人外觀.md 1 節）：朝東、朝西照朝向；朝南、朝北（正面、背面）沿用側面，
 * 敵方與第三方畫成朝西、我方朝東（面向對手那一側，開發 PM 代決）。
 */
export function creatureSide(u: Pick<UnitDraw, "facing" | "team">): "east" | "west" {
  if (u.facing === "east" || u.facing === "west") return u.facing;
  return u.team === "ally" ? "east" : "west";
}

/** 精英記號（Phase 5A-ART2）：`elite` 標籤或頭目外光（`rarity`）→ 金環＋金菱形；倒下不畫。 */
export function hasEliteMark(u: UnitDraw): boolean {
  return !u.downed && (u.elite === true || u.dollLook?.rarity != null);
}

/** 人形精英的大小倍率：精英 ×1.15、頭目（有外光）不放大（異形在 `resolveCreature` 裡乘）。 */
export function humanoidEliteScale(u: UnitDraw): number {
  return u.elite === true && u.dollLook?.rarity == null ? ELITE_SCALE : 1;
}

/** 人形敵人的詞綴（認得的特效 id）。 */
function humanoidAffixes(u: UnitDraw): string[] {
  return knownAffixes(u.dollLook?.affixes);
}

/** 單位有「連心的」詞綴（BattleRenderer 畫到相鄰同陣營單位的青色虛線）。 */
export function isLinked(u: UnitDraw): boolean {
  return !u.downed && knownAffixes(u.dollLook?.affixes).includes("linked");
}

/** 人形召喚物沿用的範本（骷髏）與殘影找不到召喚者時的預設（戰士）。 */
const SKELETON_TEMPLATE = "summon_skeleton_warrior";
const DEFAULT_OWNER_TEMPLATE = "hero_fighter";
let defaultOwner: DollSpec | undefined;

/** 人形召喚物用的紙娃娃規格：骷髏沿用範本外觀，殘影複製召喚者（找不到時用預設戰士；預設戰士全程只算一次）。 */
function summonHumanoidSpec(u: UnitDraw, look: ResolvedLook): DollSpec {
  const skeleton = resolveDoll({ template: SKELETON_TEMPLATE, team: u.team, summon: true, weaponId: u.weaponId, weaponClass: u.weaponClass });
  defaultOwner ??= resolveDoll({ template: DEFAULT_OWNER_TEMPLATE, team: "ally", summon: false });
  return humanoidSpec(look, skeleton, u.copyOf !== undefined ? resolveDoll(u.copyOf) : defaultOwner);
}

/** 倒地單位的灰階濾鏡：全部單位共用一個（`destroy({children:true})` 不會銷毀濾鏡，所以不能每次重畫都 new）。 */
let grayFilter: ColorMatrixFilter | undefined;
function gray(): ColorMatrixFilter {
  if (grayFilter === undefined) {
    grayFilter = new ColorMatrixFilter();
    grayFilter.desaturate();
  }
  return grayFilter;
}

/** 小人貼圖共通的外觀：透明度（含隱匿）與倒地灰階。 */
function applyLook(sprite: Sprite, u: UnitDraw, look: DownedLook): Sprite {
  sprite.alpha = look.dollAlpha * (u.statusIds?.includes(CONCEALED) === true ? CONCEALED_ALPHA : 1);
  if (look.grayscale) sprite.filters = [gray()];
  return sprite;
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
  return applyLook(sprite, u, look);
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

function specOfUnit(u: UnitDraw): DollSpec {
  return resolveDoll({ template: u.template, team: u.team, summon: u.summon, totem: u.totem, dollLook: u.dollLook, raceLook: u.raceLook, weaponId: u.weaponId, weaponClass: u.weaponClass, equipment: u.equipment, attackElement: u.attackElement });
}

/** 倒地狀態（`prone`，例如冰面滑倒）：還站得起來、只是躺著；和 HP 歸零的倒下（`downed`）不同。 */
export const PRONE = "prone";
export function isProne(u: Pick<UnitDraw, "downed" | "statusIds">): boolean {
  return !u.downed && u.statusIds?.includes(PRONE) === true;
}

/** 小人本身（紙娃娃、異形、形態、召喚物）的節點名稱；走路、倒地、受擊時只動小人，底圈與血條不動。 */
export const BODY_LABEL = "body";
/** 跟著小人的詞綴特效、人形特徵（同畫布、同錨點）：跟著小人位移、旋轉，但不換貼圖。 */
export const BODY_FX_LABEL = "body-fx";

/** 小人與跟著它的特效（動畫時一起動）。 */
export function bodyNodes(unit: Container): Sprite[] {
  return unit.children.filter((n): n is Sprite => n instanceof Sprite && (n.label === BODY_LABEL || n.label === BODY_FX_LABEL)); // 退回的色塊（沒有 DOM）不動
}

function bodyPart(node: Sprite, u: UnitDraw, feet: number): Sprite {
  node.label = BODY_FX_LABEL;
  layDown(node, u, feet);
  return node;
}

/** 一格動畫：紙娃娃的骨架姿勢、異形的姿勢（都已量化）。 */
export interface BodyFrame {
  pose?: InkPose | null;
  creature?: CreaturePose | null;
  /** 紙娃娃受擊白閃（6M-4；0～1，只閃剪影）；異形的白閃在 `creature.flash`。 */
  flash?: number;
}

/**
 * 動畫中這一格的小人貼圖（6M-3）：紙娃娃照骨架姿勢、異形照異形姿勢；形態與召喚物沒有骨架，回傳 `null`（照舊整個平移）。
 * 倒地狀態的紙娃娃沒給姿勢時照躺著的姿勢。
 */
export function bodyTexture(art: ArtTextures, u: UnitDraw, frame: BodyFrame): Texture | null {
  if (summonLookOf(u) !== null) return null;
  const spec = specOfUnit(u);
  if (formArtOfUnit(u, spec) !== null) return null;
  const cr = creatureOf(u);
  if (cr !== null) {
    // 6R-F：動畫中的異形只畫身體（位移改移節點、影子另一張，見 `placeCreatureBody`）
    if (frame.creature != null) return art.creatureBody(cr, creatureSide(u), frame.creature);
    return art.creature(cr, creatureSide(u), u.downed ? downedCreaturePose() : null);
  }
  return art.figure(spec, u.facing, u.downed, frame.pose ?? (isProne(u) ? proneBody(1, u.facing).pose : null), frame.flash ?? 0);
}

/** 異形動畫時留在原地的影子節點名稱（6R-F；不在 `bodyNodes` 裡，不跟著位移）。 */
export const CREATURE_SHADOW_LABEL = "creature-shadow";

/** 異形姿勢的位移（虛擬像素）→ 戰場像素：照畫布的大小（`r.size`）、朝西鏡像、戰場縮放（6R-F）。 */
export function creatureOffsetPx(u: UnitDraw, cr: ResolvedCreature, pose: CreaturePose): { x: number; y: number } {
  const k = (T / 52) * DOLL_SCALE * creatureFieldScale(u) * cr.size;
  const { dx, dy } = splitCreatureOffset(pose);
  const mirror = creatureSide(u) === "west" ? -1 : 1;
  return { x: dx * k * mirror + 0, y: dy * k + 0 };
}

/**
 * 6R-F（前端審查第 9 點）：異形的身體貼圖換好之後呼叫。`base` 是身體在沒有位移時的位置。
 * - 有姿勢（`frame.creature`）：身體移到 `base ＋ 位移`；影子用另一張貼圖留在 `base`（和原本把位移畫進貼圖時一樣）。
 * - 沒有姿勢（站好、倒地圖示）：身體回到 `base`，影子藏起來（貼圖本身有影子）。
 * 不是異形時什麼都不做。
 */
export function placeCreatureBody(art: ArtTextures, unitId: string, unit: Container, u: UnitDraw, frame: BodyFrame, base: { x: number; y: number }): void {
  const cr = creatureOf(u);
  if (cr === null || unit.destroyed) return;
  const body = unit.children.find((n): n is Sprite => n instanceof Sprite && n.label === BODY_LABEL);
  if (body === undefined) return;
  const shadow = unit.children.find((n): n is Sprite => n instanceof Sprite && n.label === CREATURE_SHADOW_LABEL);
  const pose = frame.creature;
  if (pose == null) {
    body.position.set(base.x, base.y);
    if (shadow !== undefined) shadow.visible = false;
    art.holdFor(`cshadow:${unitId}`, null);
    return;
  }
  const off = creatureOffsetPx(u, cr, pose);
  body.position.set(base.x + off.x, base.y + off.y);
  const tex = art.creatureShadow(cr, creatureSide(u));
  if (tex === null) return;
  let node = shadow;
  if (node === undefined) {
    node = new Sprite(tex);
    node.label = CREATURE_SHADOW_LABEL;
    unit.addChildAt(node, unit.getChildIndex(body));
  } else if (node.texture !== tex) node.texture = tex;
  art.holdFor(`cshadow:${unitId}`, tex);
  node.anchor.copyFrom(body.anchor);
  node.scale.copyFrom(body.scale);
  node.rotation = body.rotation;
  node.alpha = body.alpha;
  const want = body.filters ?? null; // 灰階等外觀跟著身體（只在改變時換，不每幀建新陣列）
  if ((node.filters?.length ?? 0) !== (want?.length ?? 0)) node.filters = want === null ? null : [...want];
  node.position.set(base.x, base.y);
  node.visible = body.visible;
}

/**
 * 倒下片段（6N-4）用的站姿紙娃娃：不管 `downed` 都畫站著的人（姿勢、白閃照 `frame`），`bare` 不含地上影子（側倒時用，
 * 和倒地圖示一樣沒有影子）。沒有骨架（異形、形態、召喚物）回傳 `null`。
 */
export function uprightTexture(art: ArtTextures, u: UnitDraw, frame: BodyFrame, bare: boolean): Texture | null {
  if (summonLookOf(u) !== null || creatureOf(u) !== null) return null;
  const spec = specOfUnit(u);
  if (formArtOfUnit(u, spec) !== null) return null;
  const pose = frame.pose ?? null;
  return bare ? art.figureBare(spec, u.facing, pose, frame.flash ?? 0) : art.figure(spec, u.facing, false, pose, frame.flash ?? 0);
}

/** 紙娃娃 1 虛擬像素 ＝ 幾個模型像素（含精英、外觀大小；和 `dollNode` 的縮放相同）。 */
export function dollPx(u: UnitDraw): number {
  return (T / 52) * DOLL_SCALE * humanoidEliteScale(u) * humanoidLookScale(u);
}

/**
 * 受擊時疊白色剪影閃白的單位（6C-8）：形態、有外觀的召喚物、倒下或倒地狀態的人；異形（6M-3）與站著的紙娃娃（6M-4）
 * 有自己的受擊片段，回傳 `null`。判斷順序和 `dollNode` 選貼圖的順序相同。
 */
export function overlayFlashKind(u: UnitDraw): "form" | "summon" | "downed" | null {
  if (creatureOf(u) !== null) return null;
  if (formArtOfUnit(u, specOfUnit(u)) !== null) return "form";
  const sl = summonLookOf(u);
  if (sl !== null && !(u.downed && sl.body === "humanoid")) return "summon";
  return u.downed || isProne(u) ? "downed" : null;
}

/** `overlayFlashKind` 的白色剪影貼圖（同一張圖不含地上影子、轉白；和小人的貼圖同畫布大小）；不需要或畫不出來時 `null`。 */
export function flashTexture(art: ArtTextures, u: UnitDraw): Texture | null {
  const kind = overlayFlashKind(u);
  if (kind === null) return null;
  const spec = specOfUnit(u);
  if (kind === "form") {
    const form = formArtOfUnit(u, spec)!;
    return art.formFlash(form.id, form.hero, form.element, u.facing, u.downed);
  }
  if (kind === "summon") {
    const sl = summonLookOf(u)!;
    return art.summonFlash(sl, u.facing, sl.body === "humanoid" ? summonHumanoidSpec(u, sl) : null);
  }
  const prone = summonLookOf(u) === null && isProne(u) ? proneBody(1, u.facing).pose : null;
  return art.figureFlash(spec, u.facing, u.downed, prone);
}

/** 有紙娃娃骨架的人形（不是異形、形態、召喚物）：受擊、待機的小動作會換骨架姿勢（6M-4）。 */
export function hasSkeleton(u: UnitDraw): boolean {
  if (u.downed || summonLookOf(u) !== null || creatureOf(u) !== null) return false;
  return formArtOfUnit(u, specOfUnit(u)) === null;
}

/** 紙娃娃的主手、副手（技能起手對照表用，6N-1）；沒有骨架的單位（異形、形態、召喚物、倒下）回傳 `null`。 */
export function gripOf(u: UnitDraw): { main: GearItem | undefined; off: GearItem | undefined } | null {
  if (!hasSkeleton(u)) return null;
  const gear = specOfUnit(u).gear;
  return { main: gear.main_hand, off: gear.off_hand };
}

/** 倒地狀態持續躺著（6M-3）：小人以腳底為軸轉倒、往前溜一點（和滑倒動畫的最後一格相同）。 */
function layDown(node: Container, u: UnitDraw, feet: number): void {
  if (!isProne(u)) return;
  const p = proneBody(1, u.facing);
  node.rotation = p.rotation;
  node.position.set(p.x, feet + p.y);
}

function doll(art: ArtTextures, u: UnitDraw, look: DownedLook, feet: number, r: number): Sprite | Graphics {
  const node = dollNode(art, u, look, feet, r);
  node.label = BODY_LABEL;
  layDown(node, u, feet);
  return node;
}

function dollNode(art: ArtTextures, u: UnitDraw, look: DownedLook, feet: number, r: number): Sprite | Graphics {
  const sl = summonLookOf(u);
  const spec = specOfUnit(u);
  const form = formArtOfUnit(u, spec);
  const formSprite = form === null ? null : formDoll(art, u, look, feet, form);
  if (formSprite !== null) return formSprite;
  const cr = creatureOf(u);
  if (cr !== null) {
    // 6N-4：倒下的異形停在倒下片段的最後一格（塌扁、往後倒），倒下動畫播完不會跳回站著
    const tex = art.creature(cr, creatureSide(u), u.downed ? downedCreaturePose() : null);
    if (tex !== null) {
      const sprite = new Sprite(tex);
      const k = (T / 52) * DOLL_SCALE * creatureFieldScale(u);
      sprite.anchor.set(0.5, CREATURE_FOOT_Y / CREATURE_H);
      sprite.width = CREATURE_W * k;
      sprite.height = CREATURE_H * k;
      sprite.position.set(0, feet);
      return applyLook(sprite, u, look);
    }
  }
  // 倒地的人形召喚物沿用紙娃娃的躺下姿勢；其他體型（圖騰、構造體、植物…）不躺下
  const useSummonArt = sl !== null && !(u.downed && sl.body === "humanoid");
  const prone = sl === null && isProne(u) ? proneBody(1, u.facing).pose : null; // 倒地狀態：骨架躺著的姿勢（6M-3）
  const texture = useSummonArt ? art.summon(sl, u.facing, sl.body === "humanoid" ? summonHumanoidSpec(u, sl) : null) : art.figure(spec, u.facing, u.downed, prone);
  if (texture === null) return new Graphics().circle(0, 0, r).fill(u.fill); // 無法產生貼圖：退回色塊
  const sprite = new Sprite(texture);
  // C 骨架（人形與紙娃娃）：52px 格縮放 0.92（3U-2），人約 48px 高；非人形召喚物沿用舊的 64×64 畫布，縮放 1.15
  const humanoid = sl === null || sl.body === "humanoid";
  const k = (T / 52) * (humanoid ? DOLL_SCALE * humanoidEliteScale(u) * humanoidLookScale(u) : SUMMON_SCALE);
  const [w, h, footY] = humanoid ? [DOLL_W, DOLL_H, DOLL_FOOT_Y] : [SUMMON_W, SUMMON_H, SUMMON_FOOT_Y];
  sprite.anchor.set(0.5, footY / h);
  sprite.width = w * k;
  sprite.height = h * k;
  sprite.position.set(0, feet);
  applyLook(sprite, u, look);
  if (sl === null && humanoidAffixes(u).includes("mist_hidden")) sprite.alpha *= 0.75; // 霧隱的：本體 75%
  return sprite;
}

/** 人形敵人的詞綴特效與人形特徵（Phase 5A-ART2）：`under` ＝ 身體後面（霧氣繞身）。異形、形態、召喚物、倒下不畫。 */
function humanoidFxSprite(art: ArtTextures, u: UnitDraw, feet: number, under: boolean): Sprite | null {
  if (u.downed || u.summon || u.form != null || creatureOf(u) !== null) return null;
  const affixes = under ? [] : humanoidAffixes(u);
  const traits = [...(u.dollLook?.traits ?? [])];
  if (affixes.length === 0 && traits.length === 0) return null;
  const tex = art.dollFx(`${under ? "u" : "o"}|${affixes.join("+")}|${traits.join("+")}`, (ctx) => drawHumanoidFx(ctx, affixes, traits, under));
  if (tex === null) return null;
  const k = (T / 52) * DOLL_SCALE * humanoidEliteScale(u) * humanoidLookScale(u);
  const s = new Sprite(tex);
  s.anchor.set(0.5, DOLL_FOOT_Y / DOLL_H);
  s.width = DOLL_W * k;
  s.height = DOLL_H * k;
  s.position.set(0, feet);
  return s;
}

/** 精英金環（墨線底＋金線，在陣營環外）＋環前方金菱形（Phase 5A-ART2，`docs/art/敵人外觀.md` 3 第 2 段）。 */
export const ELITE_GOLD = 0xffbf3a;
const ELITE_INK = 0x2b1e16;
function eliteRing(g: Graphics, cy: number, rx: number, ry: number): void {
  const s = rx / 13; // 樣張的環半徑是 13
  const gx = rx + 2.2 * s;
  const gy = ry * (gx / rx);
  g.ellipse(0, cy, gx, gy).stroke({ width: 2.2 * s, color: ELITE_INK });
  g.ellipse(0, cy, gx, gy).stroke({ width: 1.2 * s, color: ELITE_GOLD });
  const top = cy + gy + 0.2 * s;
  g.poly([0, top, 2.4 * s, top + 2.4 * s, 0, top + 4.8 * s, -2.4 * s, top + 2.4 * s]).fill(ELITE_GOLD).stroke({ width: 0.6 * s, color: ELITE_INK });
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

/** 身上特效（`over`）精靈的標籤（6N-9：狀態動作換掉會動的部分時用來找它）。 */
export const FX_OVER_LABEL = "fx-over";

/** 身上特效的貼圖（`under` ＝ 腳下、`over` ＝ 身上；同一組特效共用一張）。沒有 DOM 時回傳 `null`。 */
export function effectTextureOf(kind: "under" | "over", e: BodyEffects): Texture | null {
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
  const tex = effectTextureOf(kind, e);
  if (tex === null) return null;
  const k = T / 52;
  const s = new Sprite(tex);
  s.anchor.set(0.5, FX_FEET / FX_H);
  s.width = FX_W * k;
  s.height = FX_H * k;
  s.position.set(0, feet);
  if (kind === "over") s.label = FX_OVER_LABEL;
  return s;
}

const rowTextures = new Map<string, Texture>();

function rowIconTexture(id: string): Texture | null {
  const canvas = statusIconCanvas(id, ROW_ICON_FEET);
  if (canvas === null) return null;
  const key = `${statusIconKey(id, ROW_ICON_FEET)}|${fontEpoch()}`;
  const hit = rowTextures.get(key);
  if (hit !== undefined) return hit;
  const tex = Texture.from(canvas);
  rowTextures.set(key, tex);
  return tex;
}

/** 腳邊狀態列的圖示邊長（3U-2b；舊 14，約 60～80%：48px 格 11、88px 格約 20px）。 */
export const ROW_ICON_FEET = 11;
/** 狀態列圖示與 HP 條（含護盾條）之間的空隙。 */
const ROW_GAP_HP = 4;
/** 字母標記圓（左下）的右緣 x；狀態列左緣至少離它 1px。 */
const MARKER_RIGHT = -T * 0.37 + 8;

/** 腳邊狀態列的中心 y（相對格子中心）：HP 條正上方；不隨體型、形態、頭頂高度改變。 */
export const ROW_Y_FEET = T * 0.36 - ROW_GAP_HP - ROW_ICON_FEET / 2;

/** 腳底（相對格子中心）。 */
export const FEET = T * 0.23;
/** 異形畫出來的高度不到人形頭頂（`DOLL_HEAD_TOP`）的 90% 才算「比人形矮」；差 10% 內（傀儡）視為一樣高（5A-ART5 代決）。 */
export const SHORT_CREATURE_RATIO = 0.9;
/** 狀態列往上移的上限（圖示中心 y）：圖示上緣不超出最上排的頭頂預留 `UNIT_HEADROOM`。 */
export const ROW_Y_HEADROOM_CAP = -T / 2 - UNIT_HEADROOM + ROW_ICON_FEET / 2;
/** 狀態列往上移的上限（圖示中心 y）：圖示上緣離上一排單位 HP 條的下緣至少 1px（同高的格子；5A-ART5 驗收「不蓋到上一排的 HP 條」）。 */
export const ROW_Y_UPPER_HP_CAP = T * 0.36 + 5 - T + 1 + ROW_ICON_FEET / 2;

/**
 * 腳邊狀態列的中心 y（Phase 5A-ART5，`docs/art/5A-ART檢查.md` 1 第 2 點）：非浮空的異形畫出來比人形矮時，
 * 移到身體最高點上方 1px（圖示中心 ＝ 最高點 − 圖示/2 − 1）；不比原位低、不超出上限（兩個上限取較低的位置）。
 * 人形、浮空的、和人一樣高的維持原位。`fieldScale` ＝ 戰場上的額外縮放（頭目 ×0.9）。
 */
export function statusRowY(cr: ResolvedCreature | null, fieldScale = 1): number {
  if (cr === null) return ROW_Y_FEET;
  const { top, hover } = bodyTop(cr.body);
  const height = -top * cr.size * fieldScale; // 虛擬單位
  if (hover || height >= DOLL_HEAD_TOP * SHORT_CREATURE_RATIO) return ROW_Y_FEET;
  const y = FEET - height * (T / 52) * DOLL_SCALE - ROW_ICON_FEET / 2 - 1;
  return Math.min(ROW_Y_FEET, Math.max(ROW_Y_HEADROOM_CAP, ROW_Y_UPPER_HP_CAP, y));
}

/**
 * 單位圖實際畫出來的頂端（相對格子中心的 y，往上為負；6C-8b 敵群頭上的眼睛用）。
 * 異形：身體最高點（`bodyTop`，浮空的含浮起的高度）× 體型（含精英）× 戰場縮放（頭目 ×0.9），同 `statusRowY` 的算法；
 * 人形（含紙娃娃、形態與召喚物的退回）：頭頂 `DOLL_HEAD_TOP` × 精英 × 外觀大小。腳底一律 `FEET`。
 */
export function unitTopY(u: UnitDraw): number {
  const px = (T / 52) * DOLL_SCALE;
  const cr = creatureOf(u);
  if (cr !== null) return FEET + bodyTop(cr.body).top * cr.size * creatureFieldScale(u) * px;
  return FEET - DOLL_HEAD_TOP * humanoidEliteScale(u) * humanoidLookScale(u) * px;
}

/** 標準人形（不是精英、外觀大小 1）的頂端；和 `unitTopY` 同一個算法（6N-7 浮動字找不到人時用）。 */
export const HUMAN_TOP_Y = FEET - DOLL_HEAD_TOP * (T / 52) * DOLL_SCALE;

/** 狀態列最多顯示的圖示數（3U-2c）；超過時在第 2 個圖示右上角疊「+N」，不多佔一格。 */
export const ROW_MAX_ICONS = 2;
/** 圖示最小間距（px）：召喚物回合數徽章擠壓時才會小於 `ROW_ICON_FEET + 1`。 */
const ROW_MIN_PITCH = 6;

/** 狀態列整排往右讓字母標記所需的位移（px，>= 0）：`n` 為排內項目數，`pitch` 為圖示間距。 */
export function rowShiftForMarker(n: number, pitch = ROW_ICON_FEET + 1): number {
  const left = -((n - 1) * pitch) / 2 - ROW_ICON_FEET / 2;
  return Math.max(0, MARKER_RIGHT + 1 - left);
}

/**
 * 狀態列在字母標記（左）與召喚物回合數徽章（右，`badgeLeft` 為其左緣 x，無則 null）之間的排法。
 * 空間不夠時縮小間距（圖示輕微重疊），大小不變。
 */
export function rowPlacement(n: number, badgeLeft: number | null): { shift: number; pitch: number } {
  let pitch = ROW_ICON_FEET + 1;
  if (n > 1 && badgeLeft !== null) {
    const room = badgeLeft - 1 - (MARKER_RIGHT + 1) - ROW_ICON_FEET;
    pitch = Math.max(ROW_MIN_PITCH, Math.min(pitch, room / (n - 1)));
  }
  return { shift: rowShiftForMarker(n, pitch), pitch };
}

/** 腳邊狀態列（HP 條正上方，畫在小人之上）：最多 2 個圖示，超過時第 2 個右上角疊「+N」；倒下的單位不畫。炸彈與蓄力已有自己的徽章，不重複。 */
function statusRow(u: UnitDraw): Container | null {
  if (u.downed) return null;
  const ids = sortStatuses((u.statusIds ?? []).filter((id) => id !== TIME_BOMB && id !== CHARGING));
  const shown = ids.slice(0, ROW_MAX_ICONS);
  if (shown.length === 0) return null;
  const extra = ids.length - shown.length;
  const badgeLeft = u.summon ? summonBadgeOffset(u, T).x - SUMMON_BADGE_RADIUS : null;
  const { shift, pitch } = rowPlacement(shown.length, badgeLeft);
  const row = new Container();
  row.position.set(shift, statusRowY(creatureOf(u), creatureFieldScale(u)));
  let x = -((shown.length - 1) * pitch) / 2;
  let lastX = x;
  for (const id of shown) {
    lastX = x;
    const tex = rowIconTexture(id);
    if (tex !== null) {
      const icon = new Sprite(tex);
      icon.anchor.set(0.5);
      icon.width = ROW_ICON_FEET;
      icon.height = ROW_ICON_FEET;
      icon.position.set(x, 0);
      row.addChild(icon);
    }
    x += pitch;
  }
  if (extra > 0) {
    const cx = lastX + ROW_ICON_FEET / 2 - 2;
    const cy = -ROW_ICON_FEET / 2 + 2;
    row.addChild(new Graphics().circle(cx, cy, 4.5).fill({ color: 0x0c0c10, alpha: 0.95 }).stroke({ width: 1, color: 0xffffff }));
    const more = label(`+${extra}`, 7, 0xffffff, true);
    more.anchor.set(0.5);
    more.position.set(cx, cy + 0.5);
    row.addChild(more);
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
  const feet = FEET; // 腳底（相對格子中心）
  const cy = feet - 1;
  const rx = T * 0.36;
  const ry = T * 0.15;
  const g = new Graphics();
  const sl = summonLookOf(u);
  const noRing = sl !== null && hasNoRing(sl); // 土牆沒有底圈
  if (!noRing) g.ellipse(0, cy, rx, ry).fill({ color: ring.fill, alpha: 0.8 }).stroke({ width: 1.5, color: ring.stroke });
  if (u.hero) g.ellipse(0, cy, rx + 2.5, ry + 2).stroke({ width: 2, color: HIGHLIGHT.hero });
  if (hasEliteMark(u) && !noRing) eliteRing(g, cy, rx, ry);
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
  const fxUnder = humanoidFxSprite(art, u, feet, true);
  if (fxUnder !== null) c.addChild(bodyPart(fxUnder, u, feet));
  c.addChild(doll(art, u, look, feet, r));
  const fxOver = humanoidFxSprite(art, u, feet, false);
  if (fxOver !== null) c.addChild(bodyPart(fxOver, u, feet));
  if (effects !== null && hasOverEffect(effects)) {
    const over = effectSprite("over", effects, feet);
    if (over !== null) c.addChild(over);
  }
  if (u.summon) c.addChild(summonBadge(u));
  if (u.marker !== "") {
    // 沒有代號（戰場不顯示字母，6M-4 併入美術 PM 檢查）時不畫黑色小圓：陣營看腳下的圓盤，字母只在滑過與行動順序列出現
    const tag = new Graphics().circle(-T * 0.37, T * 0.22, 8).fill({ color: 0x000000, alpha: 0.78 }).stroke({ width: 1.5, color: ring.stroke });
    const marker = label(u.marker, 12, 0xffffff, true);
    marker.anchor.set(0.5);
    marker.position.set(-T * 0.37, T * 0.22);
    c.addChild(tag, marker);
  }
  if (look.badge !== null) {
    const badge = downedBadge(look.badge);
    badge.position.set(-T * 0.5 + 11, -T * 0.5 + 11);
    c.addChild(badge);
  }
  for (const b of statusBadges(u)) c.addChild(statusBadge(b));
  const infused = infusedBadge(u);
  if (infused !== null) c.addChild(infusedMark(infused));
  if (u.noBar !== true) c.addChild(hpBar(u));
  const row = statusRow(u);
  if (row !== null) c.addChild(row);
  return c;
}
