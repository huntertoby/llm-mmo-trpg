// 單位在地圖上的畫法（從 `BattleRenderer` 抽出，Phase 3-18b）：
// 底圈 → 朝向尖角 → 行動中虛線圈 → 小人 → 代號小標 → 倒地徽章 → 狀態徽章 → 血條。
// 倒地（docs/archive/art/3-18倒地與高度.md 第 1 節）：只有小人套透明度與去色，Container 不透明，徽章與代號維持清楚。
import { ColorMatrixFilter, Container, Graphics, Sprite, Text, Texture } from "pixi.js";
import type { UnitDraw } from "../battle/drawModel";
import { ringArrow } from "../battle/facing";
import { TILE_SIZE } from "../battle/geometry";
import { HIGHLIGHT } from "../battle/glossary";
import { dollKey, resolveDoll, type DollSpec, type GearItem } from "./appearance";
import { RING } from "./artPalette";
import type { ArtTextures } from "./artTextures";
import { label } from "./labels";
import { DOLL_FOOT_Y, DOLL_H, DOLL_SCALE, DOLL_W, renderFigureCanvas, SUMMON_SCALE } from "./paperdoll";
import { CHARGING } from "../battle/followup";
import { TIME_BOMB } from "../battle/bombs";
import { statusTile, tileCanvas } from "./skillIcon";
import { bodyEffects, bodyOver, bodyUnder, CONCEALED, CONCEALED_ALPHA, effectsKey, hasOverEffect, hasUnderEffect, statusIconCanvas, statusIconKey, sortStatuses, type BodyEffects } from "./statusIcon";
import { fontEpoch } from "./fontLoad";
import { BOMB_BADGE_LABEL, BOSS_RING_FRONT_LABEL, CHARGE_BADGE_LABEL, DOWNED_BADGE_LABEL, FACING_ARROW_LABEL, HIDDEN_HP_LABEL, HP_BAR_LABEL, INFUSED_BADGE_LABEL, MIN_BADGE_FONT_PX, MIN_STATUS_GLYPH_PX, registerMark, SOUTH_ARROW_LABEL, STATUS_ROW_LABEL, SUMMON_BADGE_LABEL } from "./minMark";
import { chooseRowLayout, numberAt, INFUSED_DROP_H, INFUSED_DROP_LINE, INFUSED_DROP_W, layoutBadges, MIN_INFUSED_ICON_PX, ONE_ICON_MODES, PLUS_ONLY_MODES, SHIFT_MODES, STATUS_BADGE_FONT, STATUS_BADGE_ICON, STATUS_BADGE_LINE, STATUS_BADGE_NUM_AT, STATUS_BADGE_R, STATUS_BADGE_STROKE, type BadgeLayout, type BadgeLayoutOpts, type BadgeReq, type RowMode, type RowOverflow, type RowVariantShapes } from "./badgeLayout";
import type { Box, Circle } from "./rowLayout";
import {
  compactPlusCount,
  isCompactRow,
  oneIconRow,
  plusOnlyRow,
  ROW_EDGE,
  MARKER_RIGHT,
  ROW_ICON_FEET,
  ROW_MIN_PITCH,
  ROW_PLUS_GAP,
  moreCapBox,
  PLUS_CAP_BAR,
  PLUS_CAP_DIGIT_W,
  PLUS_CAP_EDGE,
  PLUS_CAP_FILL,
  PLUS_CAP_FILL_ALPHA,
  PLUS_CAP_FONT,
  PLUS_CAP_H,
  PLUS_CAP_LINE,
  CAP_WIDE,
  capGeom,
  type CapGeom,
  plusCapsuleWidth,
  plusCapsuleY,
  PLUS_ONLY_MIN_STATUSES,
  ROW_PLUS_OVERFLOW_MAX,
  rowShapes,
  rowSpan,
  arrowLimits,
  shapesHitArrow,
  slideClear,
  slideClearOver,
  withinOverflow,
  shapesSpan,
  NO_EDGE,
  type MapEdge,
  summonBadgeAlone,
  summonBadgeScale,
  summonRowLayout,
  unitRowLayout,
  type RowPlan,
} from "./rowLayout";
import { AURA_H, AURA_W, FORM_FOOT_Y, FORM_H, FORM_W, formArtOf, formAuraColor, formAuraRadius, formHeroColor, formKey, renderFormCanvas } from "./inkForm";
import { copiesOwner, hasNoRing, humanoidSpec, Q_SUMMON_FOOT_Y, Q_SUMMON_H, Q_SUMMON_W, renderSummonCanvas, resolveSummonLook, summonKey, summonRingSize, type ResolvedLook } from "./summonArt";
import { ELITE_SCALE, HUGE_FIELD_SCALE, bodyTop, creatureCanvasSize, creatureKey, creaturePerches, creatureTop, drawHumanoidFx, knownAffixes, renderCreatureCanvas, resolveCreature, type ResolvedCreature } from "./inkCreature";
import { DOLL_HEAD_TOP, DOLL_HEAD_TOP_C } from "./inkDoll";
import { bossHeadroom, UNIT_HEADROOM } from "../battle/elevation";
import { SUMMON_BADGE_FONT, SUMMON_BADGE_RADIUS, downedLook, infusedBadge, pulseAlpha, statusBadges, summonBadgeOffset, type DownedLook, type InfusedBadge, type StatusBadge } from "./unitLook";
import { creaturePoseKey, splitCreatureOffset, type CreaturePose } from "./creaturePose";
import type { InkPose } from "./inkPose";
import { poseKey, proneBody } from "./motionClips";
import { downedCreaturePose } from "./reactClips";
import { BOSS_TEMPLATES, type BossId } from "./qBoss";
import { drawTrainingDummy, drawTrainingDummyFlash, isTrainingDummy } from "./trainingDummy";

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
  g.label = DOWNED_BADGE_LABEL;
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

/** 炸彈、蓄力、灌注徽章節點的標籤（6F-12：自己也是標記，地圖縮小時反向放大）。 */
export const BADGE_LABEL = { bomb: BOMB_BADGE_LABEL, charge: CHARGE_BADGE_LABEL, infused: INFUSED_BADGE_LABEL } as const;

/** 一顆徽章的節點與排法要用的東西（6F-12）。 */
interface BadgeNode {
  node: Container;
  req: BadgeReq;
  /** 數字（炸彈、蓄力；灌注是 null）：倍率和圓不同，另外放大。 */
  num: Text | null;
}

/** 狀態徽章：黑底圓＋狀態顏色外框＋部件庫的狀態圖示；數字（剩餘次數或回合）在圖示右下。 */
function statusBadge(badge: StatusBadge): BadgeNode {
  const c = new Container();
  c.label = badge.statusId === TIME_BOMB ? BADGE_LABEL.bomb : BADGE_LABEL.charge;
  c.addChild(new Graphics().circle(0, 0, STATUS_BADGE_R).fill({ color: 0x000000, alpha: 0.8 }).stroke({ width: STATUS_BADGE_LINE, color: badge.color }));
  const tex = statusTexture(badge.statusId);
  if (tex !== null) {
    const icon = new Sprite(tex);
    icon.anchor.set(0.5);
    icon.width = STATUS_BADGE_ICON;
    icon.height = STATUS_BADGE_ICON;
    c.addChild(icon);
  }
  const text = String(badge.count);
  const num = label(text, STATUS_BADGE_FONT, 0xffffff, true);
  num.anchor.set(0.5);
  num.position.set(STATUS_BADGE_NUM_AT, STATUS_BADGE_NUM_AT);
  num.style.stroke = { color: 0x000000, width: STATUS_BADGE_STROKE };
  c.addChild(num);
  return { node: c, req: { kind: badge.statusId === TIME_BOMB ? "bomb" : "charge", at: badge.at, digits: text.length }, num };
}

/** 灌注水滴的深色描邊（6F-13）。 */
export const INFUSED_DROP_OUTLINE = 0x140a24;

/**
 * 小水滴的頂點路徑（6F-13；中心在原點，高 `INFUSED_DROP_H`、寬 `INFUSED_DROP_W`）：尖端朝上，下半是半圓。
 * 純函式（測試對照 `badgeShapes` 的範圍用）。
 */
export function dropPath(g: Graphics): Graphics {
  const h = INFUSED_DROP_H / 2;
  const r = INFUSED_DROP_W / 2;
  const cy = h - r; // 下半圓的圓心
  return g
    .moveTo(0, -h)
    .bezierCurveTo(r * 0.3, -h + INFUSED_DROP_H * 0.22, r, cy - r * 0.6, r, cy)
    .arc(0, cy, r, 0, Math.PI)
    .bezierCurveTo(-r, cy - r * 0.6, -r * 0.3, -h + INFUSED_DROP_H * 0.22, 0, -h)
    .closePath();
}

/**
 * 待施放的灌注技能（Phase 3-33d）。6F-13：「灌」字在 12px 還是讀不出來（美術 PM 6F-12 檢查），
 * 改成程式繪製的紫色小水滴（深色描邊＋左上一點白色反光），沒有黑底圓（佔的位置小，800 寬才放得進召喚物的左上角）。
 */
function infusedMark(badge: InfusedBadge): BadgeNode {
  const c = new Container();
  c.label = BADGE_LABEL.infused;
  const g = dropPath(new Graphics()).fill({ color: badge.color }).stroke({ width: INFUSED_DROP_LINE, color: INFUSED_DROP_OUTLINE });
  const r = INFUSED_DROP_W / 2;
  g.ellipse(-r * 0.4, INFUSED_DROP_H / 2 - r - r * 0.2, r * 0.22, r * 0.4).fill({ color: 0xffffff, alpha: 0.85 });
  c.addChild(g);
  return { node: c, req: { kind: "infused", at: badge.at, digits: 1 }, num: null };
}

/** 6F-13：狀態列的「只留 +N」控制（`statusRow` 登記；徽章重排時決定用哪一種）。 */
interface RowControl {
  /** 每一種顯示方式畫出來的形狀（照目前的倍率與縮放；不是精簡列時只有 `normal`）。 */
  variants(): Partial<Record<RowMode, RowVariantShapes>>;
  /** 套用一種顯示方式（同時更新 `rowShapesNow`）；6F-19：平移的排法另外帶 `over`。 */
  set(mode: RowMode, over?: RowOverflow): void;
  /** 目前的顯示方式（測試用）。 */
  mode(): RowMode;
  /** 6F-17：不是精簡列時的「只留 +N」（徽章怎麼放都會蓋到狀態列時才用；精簡列時空的，已經在 `variants` 裡）。 */
  rescue(): Partial<Record<RowMode, RowVariantShapes>>;
  /**
   * 6F-18：狀態 2 個以內（`PLUS_ONLY_MIN_STATUSES`）時的「只留 +N」：只在徽章在任何顯示方式都放不下
   * （格子裡沒有不碰臉、狀態圖示的位置）時才用（見 Phase6F-18報告「待 PM 決定」）。其他時候空的。
   */
  lastResort(): Partial<Record<RowMode, RowVariantShapes>>;
  /** 6F-19：平移（可以超出格子一點）的排法（徽章放不好時才用；見 `RowOverflow`）。 */
  overflow(): RowOverflow[];
  /** 6F-19：`lastResort` 的只留「+N」平移（可以超出格子一點）。 */
  lastOverflow(): RowOverflow[];
}
const rowControls = new WeakMap<Container, RowControl>();

/** 狀態列目前的顯示方式（6F-13，測試用；沒有狀態列時 `null`）。 */
export function rowModeOf(row: Container): RowMode | null {
  return rowControls.get(row)?.mode() ?? null;
}

/** 狀態列目前可以選的顯示方式（6F-14，測試用：讓位的排法都不碰朝向三角形）。 */
export function rowVariantsOf(row: Container): Partial<Record<RowMode, RowVariantShapes>> {
  return rowControls.get(row)?.variants() ?? {};
}

/** 徽章節點上記下的排法結果（6F-13，測試用：`faceOk` 是否避開了相鄰格的臉）。 */
const badgeLays = new WeakMap<Container, BadgeLayout>();
export function badgeLayoutOf(node: Container): BadgeLayout | undefined {
  return badgeLays.get(node);
}

/**
 * 6F-12：炸彈、蓄力、灌注徽章登記成標記（`badgeLayout.ts`）。地圖縮放改變時重排：
 * 數字畫面上至少 10px、整顆在格子裡、不蓋到臉，後面的避開前面的與召喚物回合數徽章（`turns`，狀態列重排完才讀它的位置）。
 * 6F-13：也避開相鄰格單位的臉（`faces`）；精簡列擁擠時狀態列只留「+N」（`chooseRowMode`）。
 */
function registerBadges(badges: BadgeNode[], turns: Container | null, row: Container | null, faces: readonly Circle[], marks: BadgeMarks, hudDy = 0): void {
  const extra = (): Circle[] => (turns === null ? [] : [{ x: turns.position.x, y: turns.position.y, r: turns.scale.x * (SUMMON_BADGE_RADIUS + 0.5) }]);
  const rowBoxes = (): Box[] => {
    const sh = row === null ? undefined : rowShapesNow.get(row);
    if (sh === undefined) return [];
    // 角標是圓：用外接方框（保守）
    return [...sh.boxes, ...sh.circles.map((c) => ({ l: c.x - c.r, r: c.x + c.r, t: c.y - c.r, b: c.y + c.r }))];
  };
  const reqs = badges.map((b) => b.req);
  // 同一次重排（同一個縮放）只算一次；每一顆都再套用一次顯示方式（狀態列自己的重排會先回到 `normal`）
  let memo: { s: number; mode: RowMode; lays: BadgeLayout[]; over: RowOverflow | undefined } | null = null;
  const compute = (s: number): BadgeLayout[] => {
    const ctl = row === null ? undefined : rowControls.get(row);
    if (memo === null || memo.s !== s) {
      const variants = ctl?.variants() ?? {};
      // 6F-14：避開朝向三角形（`firmBoxes`）；6F-15：也避開 HP 條（`hpBoxes`）
      // （6F-18：有人站的格子不畫「▲N」，6F-14～6F-17 避開「▲N」的排法拿掉）
      const firmBoxes = marks.arrow === null ? [] : [marks.arrow];
      // 6F-17：不是精簡列時的「只留 +N」（量字寬要用畫布：用到時才算）
      let rescueMemo: Partial<Record<RowMode, RowVariantShapes>> | null = null;
      const rescue = () => (rescueMemo ??= ctl?.rescue() ?? {});
      let lastMemo: Partial<Record<RowMode, RowVariantShapes>> | null = null;
      const lastResort = () => (lastMemo ??= ctl?.lastResort() ?? {});
      let overMemo: RowOverflow[] | null = null;
      const overflow = () => (overMemo ??= ctl?.overflow() ?? []);
      let lastOverMemo: RowOverflow[] | null = null;
      const lastOverflow = () => (lastOverMemo ??= ctl?.lastOverflow() ?? []);
      const more = { arrowPoly: marks.arrowPoly ?? undefined, hpBoxes: marks.hp === null ? [] : [marks.hp], ...(ctl !== undefined ? { lastResort, overflow, lastOverflow, ...(!isCompactRow(s) ? { rescue } : {}) } : {}) };
      const chosen = ctl === undefined ? null : chooseRowLayout(reqs, s, extra(), variants, isCompactRow(s), faces, firmBoxes, more);
      const mode = chosen?.mode ?? "normal";
      const v = chosen?.over?.shapes ?? variants[mode] ?? (ctl === undefined ? undefined : (rescue()[mode] ?? lastResort()[mode]));
      const lays = chosen?.lays ?? layoutBadges(reqs, s, extra(), v?.boxes ?? rowBoxes(), { faces, plusBoxes: v?.plus ?? [], rowNums: v?.nums ?? v?.plus ?? [], firmBoxes, ...more });
      memo = { s, mode, lays, over: chosen?.over };
    }
    ctl?.set(memo.mode, memo.over);
    return memo.lays;
  };
  badges.forEach((b, i) => {
    const inner = b.num !== null ? [b.num] : (b.node.children.filter((n) => n instanceof Text) as Text[]);
    const spec = b.req.kind === "infused" ? { base: INFUSED_DROP_H, min: MIN_INFUSED_ICON_PX } : { base: STATUS_BADGE_ICON, min: MIN_STATUS_GLYPH_PX };
    const relayout = (k: number, s: number) => {
      const lay = compute(s)[i]!;
      badgeLays.set(b.node, lay);
      b.node.position.set(lay.at.x, lay.at.y + hudDy); // QK-4b：頭目整組 HUD 平移
      if (b.num !== null) {
        // 數字的倍率是 `kn`，節點已經放大 `k`（＝ `ki`）：數字自己再放大 kn ÷ k，解析度跟著提高
        const r = lay.sc.kn / k;
        b.num.scale.set(r);
        const o = numberAt(lay.corner, lay.sc); // 6F-13：擁擠時數字換到正下方或左下（6F-19：正下方照倍率貼著圓）
        b.num.position.set(o.x, o.y);
        b.num.resolution = Math.max(1, b.num.resolution * r);
      }
    };
    registerMark(b.node, spec, inner, relayout);
    relayout(1, 1);
  });
}

/** 召喚物的外觀（Phase 3-33h1）：有外觀欄位的召喚物才有；一般單位與舊資料回傳 `null`（走原本的紙娃娃）。 */
function summonLookOf(u: UnitDraw): ResolvedLook | null {
  return u.summon && u.summonLook != null ? resolveSummonLook(u.summonLook) : null;
}

/** 異形外觀（Phase 5A-ART1）：`doll_look.creature` 有值時（含召喚物，優先於 `summon_look`）；沒有時 `null`。大小用戰場的（5A-ART5）。 */
export function creatureOf(u: UnitDraw): ResolvedCreature | null {
  const look = u.dollLook?.creature;
  if (look == null) return null;
  return resolveCreature({ look, statusIds: u.statusIds, elite: u.elite, affixes: u.dollLook?.affixes, rarity: u.dollLook?.rarity, field: true, template: u.template, bossPhase: u.bossPhase });
}

/** 異形在戰場上的額外縮放：頭目照 huge ×1.6（QK-4b；頭目貼圖不含大小，其他異形的大小已畫進貼圖）。 */
export function creatureFieldScale(u: Pick<UnitDraw, "dollLook" | "template">): number {
  return u.dollLook?.creature != null && BOSS_TEMPLATES[u.template] !== undefined ? HUGE_FIELD_SCALE : 1;
}

/** HUD 底下與頭目剪影頂端之間的空隙（px）。 */
export const BOSS_HUD_GAP = 2;

/**
 * QK-4b：頭目的 HUD（HP 條、狀態列、炸彈／蓄力／灌注徽章、朝向三角形）整組往上搬到剪影上方的位移（px，≤ 0）；其他單位 0。
 * 整組照一般單位的相對位置排好（避讓不變），只整體平移：最下面那個（HP 條或朝南三角形）離頭頂 `BOSS_HUD_GAP`；
 * QK-9：最上排的上限改用頭目自己的頭頂預留（`bossHeadroom`，畫布照它加高），所以 HUD 不再被卡住疊到剪影上。
 */
export function bossHudDy(u: UnitDraw): number {
  const g = bossHudGeom(u);
  if (g === null) return 0;
  const cap = -(Math.max(0, u.y) * T) - T / 2 - Math.max(UNIT_HEADROOM, bossHeadroom(u.template)) - g.high;
  return Math.min(0, Math.max(g.dy, cap));
}

/** 頭目 HUD 照一般位置排時的上緣 `high`（相對格子中心）與貼頭頂需要的位移 `dy`；不是頭目 → `null`。 */
function bossHudGeom(u: UnitDraw): { dy: number; high: number } | null {
  const cr = creatureOf(u);
  if (cr === null || cr.boss === undefined) return null;
  const top = FEET + creatureTop(cr) * (T / 52) * DOLL_SCALE * creatureFieldScale(u);
  const arrow = arrowPolyOf(u);
  const ys = arrow === null ? [] : arrow.filter((_, i) => i % 2 === 1);
  const hp = hpBoxOf(u);
  const low = Math.max(hp === null ? FEET : hp.b, ...ys.map((y) => y + ARROW_STROKE / 2));
  const high = Math.min(ROW_Y_FEET - ROW_ICON_FEET / 2, hp === null ? Infinity : hp.t, ...ys.map((y) => y - ARROW_STROKE / 2));
  return { dy: top - BOSS_HUD_GAP - low, high };
}

/**
 * QK-9：頭頂標記（浮動字、敵群眼睛）的起點（相對格子中心，往上為負）：一般單位＝`unitTopY`；
 * 頭目＝HUD 搬到剪影上方後的上緣（和頭頂取較高者），字和眼睛不穿過 HUD。
 */
export function unitMarkTopY(u: UnitDraw): number {
  const top = unitTopY(u);
  const g = bossHudGeom(u);
  return g === null ? top : Math.min(top, g.high + bossHudDy(u));
}

/**
 * QK-9（美術 PM QK-4 檢查第 5 節第 2 題）：頭目的陣營環、精英金環照樣張（`qBoss.js` 頭目自己的環：灰燼之心半徑 40、
 * 碎晶之主 26 單位）跟著戰場 ×1.6 放大：是腳下的扁圓，可以壓到隔壁格地面，不被剪影蓋到只剩金菱形。
 * 回傳環半徑相對一般單位（`T × 0.36`）的倍率；其他單位 1。線寬另外只乘 ×1.6（`ringLineScale`），同樣張。
 */
export function ringScale(u: UnitDraw): number {
  const b = creatureOf(u)?.boss;
  if (b === undefined) return 1;
  return (BOSS_RING_UNITS[b.id] * creatureFieldScale(u) * (T / 52) * DOLL_SCALE) / (T * 0.36);
}

/** 頭目環的扁度（短半徑／長半徑；樣張 `ring` 的 0.3）。 */
export const BOSS_RING_FLAT = 0.3;
/** 頭目的環、精英的金菱形伸進南邊一排的那一份（`bossRingFront`）的節點名稱。 */
export { BOSS_RING_FRONT_LABEL };

/** 橢圓在 y ≥ `edge` 那一段的點（由東往西；`edge` 以下沒有時空陣列）。 */
function ellipseBelow(cy: number, rx: number, ry: number, edge: number): number[] {
  const k = (edge - cy) / ry;
  if (k >= 1) return [];
  const a0 = Math.asin(Math.max(-1, k));
  const n = 24;
  const out: number[] = [];
  for (let i = 0; i <= n; i++) {
    const a = a0 + ((Math.PI - 2 * a0) * i) / n;
    out.push(rx * Math.cos(a), cy + ry * Math.sin(a));
  }
  return out;
}

/**
 * QK-9：頭目的環（含精英金環、金菱形）在格子南緣（y ≥ T/2）以下的那一段：南邊一排的地面畫在這一排的單位之後，
 * 會把伸過去的環蓋掉；這一份掛到南邊一排的 `under`（地面之上、那一排的物件與單位之下）。畫法同 `buildUnitSprite` 的環。
 * HID-1c：一般大小的精英也要（環本身在格子內，只有金菱形的尖端超出下緣）。
 */
function bossRingFront(cy: number, rx: number, ry: number, ring: { fill: number; stroke: number }, elite: boolean, lk: number): Graphics {
  const g = new Graphics();
  g.label = BOSS_RING_FRONT_LABEL;
  const edge = T / 2;
  const fill = ellipseBelow(cy, rx, ry, edge);
  if (fill.length > 0) {
    g.poly(fill).fill({ color: ring.fill, alpha: 0.8 });
    g.poly(fill, false).stroke({ width: 1.5 * lk, color: ring.stroke });
  }
  if (!elite) return g;
  const s = ((T * 0.36) / 13) * lk;
  const gx = rx + 2.2 * s;
  const gy = ry * (gx / rx);
  const arc = ellipseBelow(cy, gx, gy, edge);
  if (arc.length > 0) {
    g.poly(arc, false).stroke({ width: 2.4 * s, color: ELITE_INK });
    g.poly(arc, false).stroke({ width: 1.2 * s, color: ELITE_GOLD });
  }
  const top = cy + gy - 0.4 * s;
  g.poly([0, top, 2.6 * s, top + 2.6 * s, 0, top + 5.2 * s, -2.6 * s, top + 2.6 * s]).stroke({ width: 1.6 * s, color: ELITE_INK, join: "round" }).fill(ELITE_GOLD);
  g.rect(-0.5 * s, top + 1.2 * s, 1 * s, 1 * s).fill(0xfff2c0);
  return g;
}

/** 頭目的環在樣張裡的半徑（單位，`qBoss.js` 的 `ring(ctx, 40／26)`）。 */
export const BOSS_RING_UNITS: Readonly<Record<BossId, number>> = { ah: 40, sl: 26 };

/** 環的線寬倍率：頭目 ×1.6（同造型），其他 1。 */
function ringLineScale(u: UnitDraw): number {
  return ringScale(u) === 1 ? 1 : creatureFieldScale(u);
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

/** QK-3：召喚物的陣營環比身體寬（樣張審查第 3 輪；石像、戰狼的環不被身體蓋住）；其他單位照原本大小。 */
function summonRing(u: UnitDraw, sl: ResolvedLook | null, rx: number, ry: number): { rx: number; ry: number; dx: number } {
  if (sl === null || sl.body === "humanoid" || creatureOf(u) !== null) return { rx, ry, dx: 0 };
  const k = (T / 52) * DOLL_SCALE;
  const r = summonRingSize(sl, u.facing);
  const R = Math.max(rx, r.rx * k);
  return { rx: R, ry: (ry * R) / rx, dx: r.dx * k };
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
  sprite.alpha = look.dollAlpha * (u.hiddenInfo === true || u.statusIds?.includes(CONCEALED) === true ? CONCEALED_ALPHA : 1);
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

export function specOfUnit(u: UnitDraw): DollSpec {
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
  if (isTrainingDummy(u)) return dummyTexture(art); // PR-2c：木樁沒有骨架，走路、待機都用同一張
  if (summonLookOf(u) !== null) return null;
  const spec = specOfUnit(u);
  if (formArtOfUnit(u, spec) !== null) return null;
  const cr = creatureOf(u);
  if (cr !== null) {
    // 6R-F：動畫中的異形只畫身體（位移改移節點、影子另一張，見 `placeCreatureBody`）
    if (frame.creature != null) {
      const { perch, ...rest } = frame.creature;
      return art.creatureBody(cr, creatureSide(u), perch !== undefined && !creaturePerches(cr) ? rest : frame.creature);
    }
    return art.creature(cr, creatureSide(u), creatureRestPose(u, cr));
  }
  return art.figure(spec, u.facing, u.downed, frame.pose ?? (isProne(u) ? proneBody(1, u.facing).pose : null), frame.flash ?? 0);
}

/** 戰場上站好（沒有動畫）的異形姿勢：倒地圖示；鳥（QK-4b）是待機第 0 格的落地收翅；其他靜態。 */
function creatureRestPose(u: UnitDraw, cr: ResolvedCreature): CreaturePose | null {
  if (u.downed) return downedCreaturePose();
  return creaturePerches(cr) ? PERCH_REST : null;
}
const PERCH_REST: CreaturePose = { clip: "idle", u: 0 };

/** 異形動畫時留在原地的影子節點名稱（6R-F；不在 `bodyNodes` 裡，不跟著位移）。 */
export const CREATURE_SHADOW_LABEL = "creature-shadow";

/** 異形姿勢的位移（虛擬像素）→ 戰場像素：照畫布的大小（`r.size`）、朝西鏡像、戰場縮放（6R-F）。 */
export function creatureOffsetPx(u: UnitDraw, cr: ResolvedCreature, pose: CreaturePose): { x: number; y: number } {
  const k = (T / 52) * DOLL_SCALE * creatureFieldScale(u) * (cr.boss === undefined ? cr.size : 1); // 頭目貼圖不含大小（QK-4b）
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
  if (summonLookOf(u) !== null || creatureOf(u) !== null || isTrainingDummy(u)) return null;
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
export function overlayFlashKind(u: UnitDraw): "dummy" | "form" | "summon" | "downed" | null {
  if (isTrainingDummy(u)) return "dummy"; // PR-2c：靶場木樁（`trainingDummy.ts`）
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
  if (kind === "dummy") return art.dollFx(DUMMY_FLASH_KEY, drawTrainingDummyFlash);
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

/**
 * OCL-1a：被遮擋外框用的「只有身體」畫法（不含地上影子、環、HUD、特效），和 `dollNode` 選貼圖的順序相同、同畫布大小與腳底錨點。
 * 姿勢一律是站好（第 0 格）：異形照 `creatureRestPose`、倒地狀態的人照躺著的骨架。
 */
export interface BareBody {
  /** 快取鍵（不含解析度）。 */
  readonly key: string;
  /** 畫布大小與腳底（虛擬像素）。 */
  readonly box: { readonly w: number; readonly h: number; readonly foot: number };
  /** 1 虛擬像素 ＝ 幾個模型像素（和身體 Sprite 的寬高一致）。 */
  readonly k: number;
  /** 身體貼圖解析度的基準（`ArtTextures.figureRes(display)`；頭目含 ×1.6）。 */
  readonly display: number;
  /** 畫一張 `res` 倍（每虛擬像素 `res` 個畫布像素）的畫布；沒有 DOM 時 `null`。 */
  draw(res: number): HTMLCanvasElement | null;
  /**
   * OCL-1b：身體最多佔畫布的比例（0～1；沒寫 ＝ 1）。大型前排的預篩用：畫布 × 這個比例不到 4000 模型 px² 的，
   * 不畫遮罩、不讀 alpha（冷啟動：紙娃娃一張 12～37 ms）。只給紙娃娃（人形、人形召喚物）。
   */
  readonly fill?: number;
}

/**
 * OCL-1b：紙娃娃身體最多佔畫布的比例。實測 `unitDolls.json` 的 31 個紙娃娃範本 × 4 個朝向 × 精英與否（bare、res 1）最大 0.298
 * （`bandit_boss` 朝南），取 1.5 倍。基本大小 64×92 × 0.957 ＝ 5637 → 2537、精英 1.15 倍 → 3355，都不到 4000；
 * 外觀大小 ≥ 約 1.23 倍（`dollLook.scale`）的才會畫遮罩判斷。
 */
export const DOLL_MAX_FILL = 0.45;

const BARE_HUMAN_DISPLAY = (T / 52) * DOLL_SCALE;
const BARE_DUMMY_KEY = "training-dummy-bare|v1";

/** 單位的「只有身體」畫法；退回色塊（沒有外觀）時也回傳畫法，畫不出來由 `draw` 回 `null`。 */
export function bareBodyOf(u: UnitDraw): BareBody {
  const dollBox = { w: DOLL_W, h: DOLL_H, foot: DOLL_FOOT_Y };
  if (isTrainingDummy(u)) {
    return {
      key: BARE_DUMMY_KEY,
      box: dollBox,
      k: T / 52,
      display: BARE_HUMAN_DISPLAY,
      draw: (res) => {
        if (typeof document === "undefined") return null;
        const c = document.createElement("canvas");
        c.width = DOLL_W * res;
        c.height = DOLL_H * res;
        const ctx = c.getContext("2d");
        if (ctx === null) return null;
        ctx.scale(res, res);
        ctx.translate(DOLL_W / 2, DOLL_FOOT_Y);
        drawTrainingDummy(ctx, false);
        return c;
      },
    };
  }
  const sl = summonLookOf(u);
  const spec = specOfUnit(u);
  const form = formArtOfUnit(u, spec);
  if (form !== null) {
    return { key: `g|${formKey(form.id, form.hero, form.element, u.facing, u.downed)}`, box: { w: FORM_W, h: FORM_H, foot: FORM_FOOT_Y }, k: (T / 52) * DOLL_SCALE, display: BARE_HUMAN_DISPLAY, draw: (res) => renderFormCanvas(form.id, form.hero, form.element, u.facing, u.downed, res, DOLL_SCALE, false) };
  }
  const cr = creatureOf(u);
  if (cr !== null) {
    const side = creatureSide(u);
    const rest = creatureRestPose(u, cr);
    const box = creatureCanvasSize(cr);
    return {
      key: `c|${creatureKey(cr, side)}${rest === null ? "" : `|p:${creaturePoseKey(rest)}`}`,
      box,
      k: (T / 52) * DOLL_SCALE * creatureFieldScale(u),
      display: cr.boss === undefined ? BARE_HUMAN_DISPLAY : BARE_HUMAN_DISPLAY * HUGE_FIELD_SCALE,
      draw: (res) => renderCreatureCanvas(cr, side, res, rest, "body"),
    };
  }
  if (sl !== null && !(u.downed && sl.body === "humanoid")) {
    const humanoid = sl.body === "humanoid";
    const hs = humanoid ? summonHumanoidSpec(u, sl) : null;
    const owner = copiesOwner(sl.variant) && hs !== null ? dollKey(hs, u.facing, false) : "";
    return {
      key: `s|${summonKey(sl, u.facing, owner)}`,
      box: humanoid ? dollBox : { w: Q_SUMMON_W, h: Q_SUMMON_H, foot: Q_SUMMON_FOOT_Y },
      k: (T / 52) * (humanoid ? DOLL_SCALE * humanoidEliteScale(u) * humanoidLookScale(u) : DOLL_SCALE),
      display: humanoid ? BARE_HUMAN_DISPLAY : (T / 52) * SUMMON_SCALE,
      draw: (res) => renderSummonCanvas(sl, u.facing, hs, res, false),
      ...(humanoid ? { fill: DOLL_MAX_FILL } : {}),
    };
  }
  const prone = sl === null && isProne(u) ? proneBody(1, u.facing).pose : null;
  return {
    key: `f|${dollKey(spec, u.facing, u.downed)}${prone === null ? "" : `|p:${poseKey(prone)}`}`,
    box: dollBox,
    k: dollPx(u),
    display: BARE_HUMAN_DISPLAY,
    draw: (res) => renderFigureCanvas(spec, u.facing, u.downed, res, false, prone),
    fill: DOLL_MAX_FILL,
  };
}

/** 有紙娃娃骨架的人形（不是異形、形態、召喚物）：受擊、待機的小動作會換骨架姿勢（6M-4）。 */
export function hasSkeleton(u: UnitDraw): boolean {
  if (u.downed || summonLookOf(u) !== null || creatureOf(u) !== null || isTrainingDummy(u)) return false;
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
    const tex = art.creature(cr, creatureSide(u), creatureRestPose(u, cr));
    if (tex !== null) {
      const sprite = new Sprite(tex);
      const k = (T / 52) * DOLL_SCALE * creatureFieldScale(u);
      const box = creatureCanvasSize(cr); // QK-4：頭目的畫布較大
      sprite.anchor.set(0.5, box.foot / box.h);
      sprite.width = box.w * k;
      sprite.height = box.h * k;
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
  // 人形與紙娃娃：52px 格縮放 0.92（3U-2）；QK-3 起非人形召喚物（Q 版）和紙娃娃同一個縮放、畫布 Q_SUMMON_W×Q_SUMMON_H（大小已畫進貼圖）
  const humanoid = sl === null || sl.body === "humanoid";
  const k = (T / 52) * (humanoid ? DOLL_SCALE * humanoidEliteScale(u) * humanoidLookScale(u) : DOLL_SCALE);
  const [w, h, footY] = humanoid ? [DOLL_W, DOLL_H, DOLL_FOOT_Y] : [Q_SUMMON_W, Q_SUMMON_H, Q_SUMMON_FOOT_Y];
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

/** 精英金環（Q 版外框底＋金線，在陣營環外）＋環前方金菱形（Phase 5A-ART2；QK-4 照 qCreature.js 的 ring：外框色、金菱形加亮點）。 */
export const ELITE_GOLD = 0xffbf3a;
const ELITE_INK = 0x16121a;
function eliteRing(g: Graphics, cy: number, rx: number, ry: number, line = rx / 13): void {
  const s = line; // 樣張的環半徑是 13（線寬照一般單位的環算；頭目另外 ×1.6）
  const gx = rx + 2.2 * s;
  const gy = ry * (gx / rx);
  g.ellipse(0, cy, gx, gy).stroke({ width: 2.4 * s, color: ELITE_INK });
  g.ellipse(0, cy, gx, gy).stroke({ width: 1.2 * s, color: ELITE_GOLD });
  const top = cy + gy - 0.4 * s;
  g.poly([0, top, 2.6 * s, top + 2.6 * s, 0, top + 5.2 * s, -2.6 * s, top + 2.6 * s]).stroke({ width: 1.6 * s, color: ELITE_INK, join: "round" }).fill(ELITE_GOLD);
  g.rect(-0.5 * s, top + 1.2 * s, 1 * s, 1 * s).fill(0xfff2c0);
}

/** 回合數徽章數字的深色描邊寬度（6F-11）。 */
export const SUMMON_BADGE_STROKE = 3;

function summonBadge(u: UnitDraw): Container {
  // 右下角小徽章（血條上方，不擋漂浮靈的上緣）：圖騰標「圖」，其他標剩餘輪數；撞到炸彈徽章時往左 16px
  const c = new Container();
  const badgeText = u.totem ? "圖" : String(u.remaining ?? "");
  // 6F-10：圓心放在節點原點、節點放到徽章位置，狀態列放大時可以整個搬（`summonRowLayout`）
  const at = summonBadgeOffset(u, T);
  const badge = new Graphics().circle(0, 0, SUMMON_BADGE_RADIUS).fill({ color: 0x000000, alpha: 0.75 }).stroke({ width: 1, color: HIGHLIGHT.summon });
  const badgeLabel = label(badgeText, SUMMON_BADGE_FONT, HIGHLIGHT.summon, true);
  badgeLabel.anchor.set(0.5);
  // 6F-11：數字粗體加深色描邊（800 寬讀得出來）
  badgeLabel.style.stroke = { color: 0x000000, width: SUMMON_BADGE_STROKE };
  c.addChild(badge, badgeLabel);
  c.label = SUMMON_BADGE_LABEL;
  c.position.set(at.x, at.y);
  // 6F-11：地圖縮小時反向放大（數字畫面上至少 10px）；沒有狀態列時自己決定位置（有狀態列時由狀態列重排）
  registerMark(c, { base: SUMMON_BADGE_FONT, min: MIN_BADGE_FONT_PX }, [badgeLabel], (k, s) => {
    const p = summonBadgeAlone(at, k, isCompactRow(s));
    c.position.set(p.x, p.y);
  });
  return c;
}

/** 6F-22b：護盾條外框的粗細（世界座標 px）。 */
export const SHIELD_OUTLINE = 1;

/** HID-1：看不到資訊時 HP 條的顏色（灰）與「？」的字級（世界座標 px）。 */
export const HIDDEN_HP_FILL = 0xb4b4c0;
export const HIDDEN_HP_FONT = 12;

function hpBar(u: UnitDraw): Graphics {
  const w = T * 0.8;
  const bar = new Graphics().rect(-w / 2, T * 0.36, w, 5).fill(0x000000);
  bar.label = HP_BAR_LABEL;
  if (u.hiddenInfo === true) {
    // HID-1（決定 #144）：伺服器沒給 HP、護盾：黑框裡整條灰色（內縮 1px，黑框和移動格的淺藍分得開），「？」另外畫（`hiddenHpMark`）
    bar.rect(-w / 2 + 1, T * 0.36 + 1, w - 2, 3).fill(HIDDEN_HP_FILL);
    return bar;
  }
  bar.rect(-w / 2, T * 0.36, w * u.hpRatio, 5).fill(hpColor(u.hpRatio));
  if (u.shieldRatio > 0) {
    // 6F-22b（美術 PM 6F-22 檢查第 2 節第 3 題）：護盾條 2px，外面一圈 1px 深色外框（和 HP 條的黑底同色），和移動格的淺藍框線分得開
    const o = SHIELD_OUTLINE;
    bar.rect(-w / 2 - o, T * 0.36 - 3 - o, w * u.shieldRatio + 2 * o, 2 + 2 * o).fill(0x000000);
    bar.rect(-w / 2, T * 0.36 - 3, w * u.shieldRatio, 2).fill(0x9fd8ff);
  }
  return bar;
}

/** 畫布上用半形「?」（全形「？」在小字級時字形太小）。 */
export const HIDDEN_HP_GLYPH = "?";

/** HID-1：HP 條中間的「？」徽章（黑底圓＋白字，選取時的紅框蓋住 HP 條也讀得到；地圖縮小時反向放大，畫面上至少 `MIN_BADGE_FONT_PX`）。 */
export function hiddenHpMark(hudDy: number): Container {
  const c = new Container();
  const r = HIDDEN_HP_FONT * 0.62;
  const disc = new Graphics().circle(0, 0, r).fill({ color: 0x000000, alpha: 0.82 }).stroke({ width: 1, color: HIDDEN_HP_FILL });
  const q = label(HIDDEN_HP_GLYPH, HIDDEN_HP_FONT, 0xffffff, true);
  q.anchor.set(0.5);
  c.addChild(disc, q);
  c.label = HIDDEN_HP_LABEL;
  c.position.set(0, T * 0.36 + 2.5 + hudDy);
  registerMark(c, { base: HIDDEN_HP_FONT, min: MIN_BADGE_FONT_PX }, [q]);
  return c;
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

// 6F-11：狀態列與回合數徽章的排法搬到 `rowLayout.ts`（純函式），這裡照舊匯出給既有的呼叫端與測試
export {
  HUMANOID_ARM_REACH,
  ROW_BADGE_GAP,
  ROW_EDGE,
  ROW_ICON_FEET,
  ROW_MORE_OUT,
  SUMMON_BADGE_EDGE_X,
  SUMMON_MORE_AT,
  SUMMON_MORE_DX_MAX,
  SUMMON_MORE_OUT_Y,
  SUMMON_MORE_R,
  SUMMON_MORE_SQUEEZE_DX,
  summonMoreAt,
  summonRowLayout,
  type SummonRowLayout,
} from "./rowLayout";
export { SUMMON_BADGE_LABEL } from "./minMark";

/** 狀態列圖示與 HP 條（含護盾條）之間的空隙。 */
const ROW_GAP_HP = 4;

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
 * 腳邊狀態列的中心 y（Phase 5A-ART5，`docs/archive/art/5A-ART檢查.md` 1 第 2 點）：非浮空的異形畫出來比人形矮時，
 * 移到身體最高點上方 1px（圖示中心 ＝ 最高點 − 圖示/2 − 1）；不比原位低、不超出上限（兩個上限取較低的位置）。
 * 人形、浮空的、和人一樣高的維持原位。`fieldScale` ＝ 戰場上的額外縮放（頭目 ×0.9）。
 */
export function statusRowY(cr: ResolvedCreature | null, fieldScale = 1): number {
  if (cr === null || cr.boss !== undefined) return ROW_Y_FEET; // QK-4b：頭目的狀態列照一般位置排，整組 HUD 由 `bossHudDy` 搬到剪影上方
  const hover = cr.boss === undefined && bodyTop(cr.body).hover;
  const height = -creatureTop(cr) * fieldScale; // 虛擬單位（QK-4：頭目照 qBoss 的頭頂）
  // 異形仍是 C 畫風的尺寸（QK-4 才換 Q 版），和 C 人形的頭頂比
  if (hover || height >= DOLL_HEAD_TOP_C * SHORT_CREATURE_RATIO) return ROW_Y_FEET;
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
  if (cr !== null) return FEET + creatureTop(cr) * creatureFieldScale(u) * px;
  return FEET - DOLL_HEAD_TOP * humanoidEliteScale(u) * humanoidLookScale(u) * px;
}

/** 標準人形（不是精英、外觀大小 1）的頂端；和 `unitTopY` 同一個算法（6N-7 浮動字找不到人時用）。 */
export const HUMAN_TOP_Y = FEET - DOLL_HEAD_TOP * (T / 52) * DOLL_SCALE;

/** 狀態列最多顯示的圖示數（3U-2c）；超過時在第 2 個圖示右上角疊「+N」，不多佔一格。 */
export const ROW_MAX_ICONS = 2;

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

/** 6F-19：狀態列平移（`RowOverflow`）時搜尋的間距（世界座標）。 */
const OVER_STEP = 1;

/** 「+N」膠囊的標籤（6F-19，測試用）。 */
export const PLUS_CAP_LABEL = "plus-cap";

/** 狀態列目前看得到的「+N」（6F-19，測試用：膠囊的「+」是畫的，這裡拼回「+N」）。 */
export function rowPlusTexts(row: Container): string[] {
  return row.children
    .filter((n) => n.label === PLUS_CAP_LABEL && n.visible)
    .map((n) => `+${n.children.find((t): t is Text => t instanceof Text)?.text ?? ""}`);
}

/**
 * 「+N」膠囊（6F-19，美術 PM 6F-18 檢查第 2 節）：圓角膠囊底（狀態列的深藍、金色細框），「+」用兩條白色矩形畫
 * （粗細 `PLUS_CAP_BAR`，畫面上至少 2px），數字白色粗體。徽章的數字維持黑底白字，兩者一眼分得開。
 * 節點的原點是膠囊外框的左上角（本地座標），大小 `plusCapsuleWidth(count)` × `PLUS_CAP_H`。
 */
function plusCapsule(count: number): { node: Container; text: Text; draw: (geom: CapGeom) => void } {
  const node = new Container();
  node.label = PLUS_CAP_LABEL;
  const h = PLUS_CAP_H;
  const e = PLUS_CAP_LINE / 2;
  const g = new Graphics();
  node.addChild(g);
  const digits = String(count);
  const text = label(digits, PLUS_CAP_FONT, 0xffffff, true);
  text.anchor.set(0.5);
  node.addChild(text);
  let drawn: CapGeom | null = null;
  // 6F-20（決定 Y）：「+」的長度照地圖縮放（`capGeom`：1600、1040 寬 6.5，800 寬 6）；換了才重畫
  const draw = (geom: CapGeom) => {
    if (drawn === geom) return;
    drawn = geom;
    const w = plusCapsuleWidth(count, geom);
    const cx = e + geom.pad + geom.plus / 2;
    const cy = h / 2;
    g.clear()
      .roundRect(e, e, w - 2 * e, h - 2 * e, (h - 2 * e) / 2)
      .fill({ color: PLUS_CAP_FILL, alpha: PLUS_CAP_FILL_ALPHA })
      .stroke({ width: PLUS_CAP_LINE, color: PLUS_CAP_EDGE });
    g.rect(cx - geom.plus / 2, cy - PLUS_CAP_BAR / 2, geom.plus, PLUS_CAP_BAR)
      .rect(cx - PLUS_CAP_BAR / 2, cy - geom.plus / 2, PLUS_CAP_BAR, geom.plus)
      .fill(0xffffff);
    text.position.set(e + geom.pad + geom.plus + geom.sep + (PLUS_CAP_DIGIT_W * digits.length) / 2, cy);
  };
  draw(CAP_WIDE);
  return { node, text, draw };
}

/**
 * 底圈外緣朝向三角形的外接方框（世界座標、含描邊；6F-13 狀態列要避開）；倒下或沒有底圈（土牆）時不畫，回傳 `null`。
 * 和 `buildUnitSprite` 畫的同一個三角形（`ringArrow(facing, 0, FEET − 1, T × 0.36, T × 0.15, 5)`）。
 */
export function arrowOf(u: Pick<UnitDraw, "downed" | "facing" | "summon" | "summonLook"> & Partial<Pick<UnitDraw, "noBar" | "shieldRatio">>): Box | null {
  if (u.downed) return null;
  const sl = summonLookOf(u as UnitDraw);
  if (sl !== null && hasNoRing(sl)) return null;
  const p = facingArrowPoly(u);
  const xs = [p[0]!, p[2]!, p[4]!];
  const ys = [p[1]!, p[3]!, p[5]!];
  const e = 0.5;
  return { l: Math.min(...xs) - e, r: Math.max(...xs) + e, t: Math.min(...ys) - e, b: Math.max(...ys) + e };
}

/** 6F-14 畫在狀態列上面的那一份朝向三角形的標籤（6F-15 拿掉了，美術 PM：像靴子上的白色飾扣；留著給測試確認沒有這個節點）。 */
export const ARROW_TOP_LABEL = "arrow-top";

/** 6F-12：狀態列目前畫出來的形狀（世界座標，每次重排更新）；炸彈、蓄力、灌注徽章要避開。 */
const rowShapesNow = new WeakMap<Container, { boxes: Box[]; circles: Circle[]; cap: Box | null }>();
/** 狀態列目前畫出來的形狀（6F-13，測試用；沒有時 `null`）。 */
export function rowShapesOf(row: Container): { boxes: Box[]; circles: Circle[]; cap: Box | null } | null {
  return rowShapesNow.get(row) ?? null;
}

/**
 * 腳邊狀態列（HP 條正上方，畫在小人之上）：倒下的單位不畫；炸彈與蓄力已有自己的徽章，不重複。
 * 6F-11：地圖縮放 ≤ 70% 時只顯示 1 個圖示，後面接一般大小的「+N」字；其他時候最多 2 個圖示，超過時第 2 個右上角外接「+N」角標。
 * 地圖縮放改變時重排（`rowLayout.ts`），召喚物的回合數徽章一起搬。
 */
function statusRow(u: UnitDraw, badge: Container | null, edge: MapEdge = NO_EDGE): Container | null {
  if (u.downed) return null;
  const ids = sortStatuses((u.statusIds ?? []).filter((id) => id !== TIME_BOMB && id !== CHARGING));
  const shown = ids.slice(0, ROW_MAX_ICONS);
  if (shown.length === 0) return null;
  const extra = ids.length - shown.length;
  const bottom = statusRowY(creatureOf(u), creatureFieldScale(u)) + ROW_ICON_FEET / 2;
  const row = new Container();
  row.label = STATUS_ROW_LABEL;
  // 6F-9：地圖縮小時整排反向放大（`minMark.ts`）；以圖示下緣為基準往上長，和 HP 條的空隙不變
  row.pivot.set(0, ROW_ICON_FEET / 2);
  row.position.set(0, bottom + bossHudDy(u)); // QK-4b：頭目整組 HUD 在剪影上方（排法照一般位置，只平移）
  const inner: Text[] = [];
  const icons: Array<Sprite | null> = [];
  for (const id of shown) {
    const tex = rowIconTexture(id);
    if (tex !== null) {
      const icon = new Sprite(tex);
      icon.anchor.set(0.5);
      icon.width = ROW_ICON_FEET;
      icon.height = ROW_ICON_FEET;
      row.addChild(icon);
      icons.push(icon);
    } else icons.push(null);
  }
  // 6F-19：「+N」一律是膠囊（角標、精簡列、只留「+N」三種；大小照位數算，不量字寬）
  const more = extra > 0 ? plusCapsule(extra) : null;
  if (more !== null) {
    row.addChild(more.node);
    inner.push(more.text);
  }
  const plusN = compactPlusCount(ids.length);
  const plus = plusN > 0 ? plusCapsule(plusN) : null;
  if (plus !== null) {
    row.addChild(plus.node);
    inner.push(plus.text);
  }
  let geom: CapGeom = CAP_WIDE; // 6F-20：照地圖縮放（`relayout` 更新）
  let plusW = plusN > 0 ? plusCapsuleWidth(plusN, geom) : 0;
  // 6F-13：擁擠時只留「+N」（N ＝ 全部的狀態數，膠囊的左緣在第 1 個圖示的左緣）
  const plusAll = plusCapsule(ids.length);
  plusAll.node.visible = false;
  row.addChild(plusAll.node);
  inner.push(plusAll.text);
  const allW = (): number => plusCapsuleWidth(ids.length, geom);
  let rowK = 1;
  let rowS = 1;
  let base: RowPlan | null = null;
  let mode: RowMode = "normal";
  const widthOf = (lay: RowPlan) => (lay.plusOnly === true ? allW() : lay.compact ? plusW : 0);
  const shapesOf = (lay: RowPlan) => rowShapes(lay, shown.length, rowK, bottom, extra > 0, widthOf(lay));
  const arrow = arrowOf(u);
  const apply = (lay: RowPlan) => {
    const sh = shapesOf(lay);
    rowShapesNow.set(row, sh);
    row.position.x = lay.shift;
    const only = lay.plusOnly === true;
    const n = lay.compact ? 1 : shown.length;
    const x0 = -((n - 1) * lay.pitch) / 2;
    icons.forEach((icon, i) => {
      if (icon === null) return;
      icon.visible = !only && i < n;
      icon.position.set(x0 + i * lay.pitch, 0);
    });
    if (more !== null) {
      more.node.visible = !lay.compact;
      const m = moreCapBox(x0 + (n - 1) * lay.pitch, lay.moreDx, extra);
      more.node.position.set(m.l, m.t);
    }
    const capY = plusCapsuleY();
    if (plus !== null) {
      plus.node.visible = lay.compact && !only;
      plus.node.position.set(ROW_ICON_FEET / 2 + ROW_PLUS_GAP, capY.t);
    }
    plusAll.node.visible = only;
    plusAll.node.position.set(-ROW_ICON_FEET / 2, capY.t);
  };
  const rowLeft = u.marker !== "" ? MARKER_RIGHT + 1 : -ROW_EDGE;
  // 6F-14：只留「+N」時也避開朝向三角形（平移到三角形內側；放不下換到另一側）
  const plusOnlyPlan = (m: RowMode): RowPlan => {
    const p = plusOnlyRow(rowK, rowLeft, ROW_EDGE, allW(), m === "plus-r" ? "r" : m === "plus-l" ? "l" : "c");
    // 6F-15：格子裡放不下時字超出格子邊緣一點（`slideClearOver`）
    return arrow === null ? p : (slideClearOver(p, shapesOf, arrow, rowLeft, m === "plus-l" ? "l" : "r", edge) ?? p);
  };
  // 6F-20（美術 PM 6F-19 檢查決定 X）：1 個圖示＋「+1」膠囊（2 個狀態、有徽章、放不下 2 個圖示時才用），也避開朝向三角形
  const onePlan = (m: RowMode): RowPlan => {
    const p = oneIconRow(rowK, rowLeft, ROW_EDGE, plusW, m === "one-r" ? "r" : m === "one-l" ? "l" : "c");
    return arrow === null ? p : (slideClear(p, shapesOf, arrow, rowLeft) ?? slideClearOver(p, shapesOf, arrow, rowLeft, m === "one-l" ? "l" : "r", edge) ?? p);
  };
  // 6F-13：圖示照舊、整排靠右或靠左（夾在朝向三角形內側）；和原本差不到 0.5 時不算另一種
  const shiftPlan = (b: RowPlan, m: RowMode): RowPlan | null => {
    const lim = arrowLimits(arrow, rowLeft, ROW_EDGE);
    const span = rowSpan(b, shown.length, rowK, extra > 0, widthOf(b));
    const d = m === "shift-r" ? lim.right - span.r : lim.left - span.l;
    return Math.abs(d) < 0.5 ? null : { ...b, shift: b.shift + d };
  };
  const planOf = (b: RowPlan, m: RowMode): RowPlan => (m === "normal" ? b : m === "shift-r" || m === "shift-l" ? (shiftPlan(b, m) ?? b) : ONE_ICON_MODES.includes(m) ? onePlan(m) : plusOnlyPlan(m));
  const split = (lay: RowPlan): RowVariantShapes => {
    const sh = shapesOf(lay);
    // 6F-19：「+N」一律是膠囊（`cap`，也在 `boxes` 裡）
    const caps = sh.cap === null ? [] : [sh.cap];
    const plusBox = lay.compact || lay.plusOnly === true ? caps : [];
    return { boxes: [...sh.boxes], plus: plusBox, nums: caps };
  };
  // 6F-18（美術 PM 6F-17 檢查必修 2）：狀態 2 個以內時不為了徽章收成只留「+N」（每個圖示都要整個看得到），3 個以上照 6F-17。
  // 原本的排法就只留「+N」時（朝向三角形擋住，6F-14 起）照舊可以換位置（靠左、靠右）
  const plusAllowed = () => ids.length >= PLUS_ONLY_MIN_STATUSES || base?.plusOnly === true;
  const plusVariants = (force = false): Partial<Record<RowMode, RowVariantShapes>> => {
    const out: Partial<Record<RowMode, RowVariantShapes>> = {};
    if (base === null || (!force && !plusAllowed())) return out;
    const clear = (p: RowPlan) => !shapesHitArrow(shapesOf(p), arrow);
    const inMap = (p: RowPlan) => {
      const sp = shapesSpan(shapesOf(p));
      return sp === null || ((!edge.left || sp.l >= -T / 2 - 1e-6) && (!edge.right || sp.r <= T / 2 + 1e-6));
    };
    for (const m of PLUS_ONLY_MODES) {
      const p = plusOnlyPlan(m);
      if ((clear(p) || !clear(base)) && inMap(p)) out[m] = split(p);
    }
    return out;
  };
  // 6F-19（美術 PM 6F-18 檢查 A、B）：徽章放不好時整排（3 個狀態以上也可以只留「+N」）左右平移，可以超出格子
  // 最多 `ROW_PLUS_OVERFLOW_MAX`（不超出地圖、有字母標記的那一邊不超出），不碰朝向三角形
  const overFrom = (b: RowPlan, from: RowOverflow["from"]): RowPlan => (from === "base" ? b : from === "one" ? onePlan("one-c") : plusOnlyPlan("plus-c"));
  const overPlan = (b: RowPlan, o: RowOverflow): RowPlan => {
    const p = overFrom(b, o.from);
    return { ...p, shift: p.shift + (o.mode === "over-r" ? o.d : -o.d) };
  };
  const overflowVariants = (b: RowPlan, last = false): RowOverflow[] => {
    const out: RowOverflow[] = [];
    const lo = rowLeft > -ROW_EDGE + 1e-9 ? rowLeft : edge.left ? -T / 2 : -T / 2 - ROW_PLUS_OVERFLOW_MAX;
    const hi = edge.right ? T / 2 : T / 2 + ROW_PLUS_OVERFLOW_MAX;
    const froms: Array<RowOverflow["from"]> = last ? (oneAllowed() ? ["one", "plus"] : ["plus"]) : b.plusOnly === true || !plusAllowed() ? ["base"] : ["base", "plus"];
    for (const from of froms) {
      const p = overFrom(b, from);
      const sp = shapesSpan(shapesOf(p));
      if (sp === null) continue;
      for (const [m, room] of [
        ["over-r", hi - sp.r],
        ["over-l", sp.l - lo],
      ] as const)
        for (let d = OVER_STEP; d <= room + 1e-9; d += OVER_STEP) {
          const o: RowOverflow = { mode: m, from, d, shapes: { boxes: [], plus: [] } };
          const q = overPlan(b, o);
          if (shapesHitArrow(shapesOf(q), arrow)) continue;
          out.push({ ...o, shapes: split(q) });
        }
    }
    return out;
  };
  // 6F-20（決定 X）：剛好 2 個狀態才退回「1 個圖示＋『+1』」（放得下「+1」膠囊）
  const oneAllowed = () => ids.length === 2 && plusW > 0;
  const oneVariants = (): Partial<Record<RowMode, RowVariantShapes>> => {
    const out: Partial<Record<RowMode, RowVariantShapes>> = {};
    if (base === null || !oneAllowed()) return out;
    const inMap = (p: RowPlan) => {
      const sp = shapesSpan(shapesOf(p));
      return sp === null || ((!edge.left || sp.l >= -T / 2 - 1e-6) && (!edge.right || sp.r <= T / 2 + 1e-6));
    };
    for (const m of ONE_ICON_MODES) {
      const p = onePlan(m);
      if (!shapesHitArrow(shapesOf(p), arrow) && inMap(p) && withinOverflow(shapesOf(p), rowLeft, edge)) out[m] = split(p);
    }
    return out;
  };
  rowControls.set(row, {
    variants: () => {
      const out: Partial<Record<RowMode, RowVariantShapes>> = {};
      if (base === null) return out;
      out.normal = split(base);
      // 6F-14：讓位的排法不可以碰到朝向三角形（原本的排法已經避開了，或避不開）
      const clear = (p: RowPlan) => !shapesHitArrow(shapesOf(p), arrow);
      // 6F-16：站在地圖最左、最右欄時，讓位的排法不超出地圖那一邊
      const inMap = (p: RowPlan) => {
        const sp = shapesSpan(shapesOf(p));
        return sp === null || ((!edge.left || sp.l >= -T / 2 - 1e-6) && (!edge.right || sp.r <= T / 2 + 1e-6));
      };
      if (!u.summon)
        for (const m of SHIFT_MODES) {
          const p = shiftPlan(base, m);
          if (p !== null && clear(p) && inMap(p)) out[m] = split(p);
        }
      if (isCompactRow(rowS)) Object.assign(out, plusVariants());
      return out;
    },
    rescue: () => (base === null || isCompactRow(rowS) || u.summon ? {} : plusVariants()),
    lastResort: () => (base === null || plusAllowed() || (u.summon && !isCompactRow(rowS)) ? {} : { ...oneVariants(), ...plusVariants(true) }),
    overflow: () => (base === null || u.summon ? [] : overflowVariants(base)),
    lastOverflow: () => (base === null || u.summon || plusAllowed() ? [] : overflowVariants(base, true)),
    set: (m, over) => {
      mode = m;
      if (base !== null) apply(over !== undefined ? overPlan(base, over) : planOf(base, m));
    },
    mode: () => mode,
  });
  // 6F-10、6F-11：倍率或縮放改變時重排（和回合數徽章不重疊、不超出格子）
  const relayout = (k: number, s: number) => {
    rowK = k;
    rowS = s;
    mode = "normal";
    // 6F-20：膠囊裡「+」的長度照縮放（1600 寬的角標只在縮放 > 0.85 出現，一律 `CAP_WIDE`）
    geom = capGeom(s);
    plusW = plusN > 0 ? plusCapsuleWidth(plusN, geom) : 0;
    for (const cap of [more, plus, plusAll]) cap?.draw(geom);
    const compact = isCompactRow(s);
    if (u.summon && badge !== null) {
      const kb = summonBadgeScale(s);
      const lay = summonRowLayout(shown.length, k, summonBadgeOffset(u, T), bottom, extra > 0, u.marker !== "", kb, compact, plusW);
      base = lay;
      apply(lay);
      badge.position.set(lay.badge.x, lay.badge.y);
    } else {
      base = unitRowLayout(shown.length, k, extra > 0, u.marker !== "", s, plusW, arrow, { bottom, allW, edge, total: ids.length }); // 6F-14：避開朝向三角形；6F-16：不超出地圖；6F-18：狀態數
      apply(base);
    }
  };
  registerMark(row, { base: ROW_ICON_FEET - 2, min: MIN_STATUS_GLYPH_PX }, inner, relayout);
  relayout(1, 1);
  return row;
}

/**
 * 一個單位的所有圖層（圖層順序見檔頭）；位置由呼叫端放到格子中心。
 * `faces`（6F-13）：相鄰格單位伸進這一格的臉（`neighborFaces`），炸彈、蓄力、灌注徽章要避開。
 */
export function buildUnitSprite(art: ArtTextures, pulses: Pulses, u: UnitDraw, faces: readonly Circle[] = [], opts: UnitSpriteOpts = {}): Container {
  if (isTrainingDummy(u)) return buildDummySprite(art, u, faces, opts);
  const c = new Container();
  const r = T * 0.32;
  const look = downedLook(u.downed, u.revivable);
  const teamRing = u.summon ? RING.summon : RING[u.team];
  const ring = look.ring ?? teamRing;
  const feet = FEET; // 腳底（相對格子中心）
  const cy = feet - 1;
  const rk = ringScale(u); // QK-9：頭目的環照樣張放大
  const rx = T * 0.36 * rk;
  const ry = rk === 1 ? T * 0.15 : rx * BOSS_RING_FLAT; // 頭目照樣張的扁圓（短半徑 0.3）
  const g = new Graphics();
  const sl = summonLookOf(u);
  const noRing = sl !== null && hasNoRing(sl); // 土牆沒有底圈
  const sr = summonRing(u, sl, rx, ry);
  const lk = ringLineScale(u);
  if (!noRing) g.ellipse(sr.dx, cy, sr.rx, sr.ry).fill({ color: ring.fill, alpha: 0.8 }).stroke({ width: 1.5 * lk, color: ring.stroke });
  if (u.hero) g.ellipse(0, cy, rx + 2.5, ry + 2).stroke({ width: 2, color: HIGHLIGHT.hero });
  if (hasEliteMark(u) && !noRing) eliteRing(g, cy, rx, ry, ((T * 0.36) / 13) * lk);
  c.addChild(g);
  // QK-9：頭目的環伸進南邊一排；那一排的地面會蓋掉，伸出去的部分另畫一份（`RowStack.attachMarks` 掛到南邊一排的 `under`）
  // HID-1c：精英的金菱形尖端同因
  if ((rk > 1 || hasEliteMark(u)) && !noRing) c.addChild(bossRingFront(cy, rx, ry, ring, hasEliteMark(u), lk));
  if (look.dashed !== null) {
    const dashed = dashedEllipse(cy, T * 0.4, T * 0.18, look.dashed.color, 2.5);
    c.addChild(dashed);
    pulses.add(dashed, look.dashed);
  }
  let arrowOnTop: Graphics | null = null;
  const hudDy = bossHudDy(u);
  if (!u.downed && !noRing) {
    const arrow = new Graphics().poly(facingArrowPoly(u)).fill(0xffffff).stroke({ width: ARROW_STROKE, color: 0x000000 });
    // 6F-21：朝南時在 HP 條下面，改在南邊一排的地面之上畫；QK-4b：頭目的三角形跟著 HUD 搬到剪影上方（不掛南邊一排）
    arrow.label = southArrowMoved(u) && hudDy === 0 ? SOUTH_ARROW_LABEL : FACING_ARROW_LABEL;
    arrow.position.y = hudDy;
    // QK-3b：四足召喚物朝北時，底圈後緣的三角形整個被橫著的身體蓋住，改畫在身體上面；QK-4b：頭目的三角形在剪影上方，也畫在身體之後
    if (arrowAboveBody(u) || hudDy !== 0) arrowOnTop = arrow;
    else c.addChild(arrow);
  }
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
  if (arrowOnTop !== null) c.addChild(arrowOnTop);
  if (effects !== null && hasOverEffect(effects)) {
    const over = effectSprite("over", effects, feet);
    if (over !== null) c.addChild(over);
  }
  const turns = u.summon ? summonBadge(u) : null;
  if (turns !== null) c.addChild(turns);
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
  const badges = statusBadges(u).map(statusBadge);
  const infused = infusedBadge(u);
  if (infused !== null) badges.push(infusedMark(infused));
  if (u.noBar !== true) {
    const bar = hpBar(u);
    bar.position.y = hudDy;
    c.addChild(bar);
    if (u.hiddenInfo === true) c.addChild(hiddenHpMark(hudDy));
  }
  // 6F-15：6F-14 另外畫在狀態列上面的那一份三角形拿掉了（避不開時「+N」超出格子一點讓開，`rowLayout.slideClearOver`）
  const row = statusRow(u, turns, opts.edge);
  if (row !== null) c.addChild(row);
  // 6F-12：徽章畫在 HP 條與狀態列上面：800 寬格子太擠、避不開時，數字照樣讀得出來（狀態列的圖示被蓋一角）
  for (const b of badges) c.addChild(b.node);
  if (badges.length > 0) registerBadges(badges, turns, row, faces, badgeMarks(u), hudDy);
  return c;
}

/** 木樁貼圖的鍵（`ArtTextures.dollFx`）；改畫法時換版號。 */
const DUMMY_KEY = "training-dummy|v1";
const DUMMY_FLASH_KEY = "training-dummy-flash|v1";

/** 木樁的貼圖（紙娃娃大小的畫布、腳底為原點；`trainingDummy.ts`）；沒有 DOM 時 `null`。 */
export function dummyTexture(art: ArtTextures): Texture | null {
  return art.dollFx(DUMMY_KEY, (ctx) => drawTrainingDummy(ctx));
}

/**
 * 靶場木樁（PR-2c，`docs/art/靶場移植需求.md` 第 2 節）：只畫木樁本身（影子畫在貼圖裡），沒有陣營圈、朝向三角形、血條、字母標記；
 * 行動中的虛線圈、狀態列與徽章照一般單位。倒下（技能工坊打倒時）照倒地的透明度與去色。
 */
function buildDummySprite(art: ArtTextures, u: UnitDraw, faces: readonly Circle[], opts: UnitSpriteOpts): Container {
  const c = new Container();
  if (u.active) c.addChild(dashedEllipse(FEET - 1, T * 0.36 + 6, T * 0.15 + 4, HIGHLIGHT.active));
  const tex = dummyTexture(art);
  const body = tex === null ? new Graphics().rect(-4, FEET - T * 0.6, 8, T * 0.6).fill(0x9a7046) : new Sprite(tex);
  body.label = BODY_LABEL;
  if (body instanceof Sprite) {
    const k = T / 52; // 樣張的木樁縮放（0.86）已畫進貼圖
    body.anchor.set(0.5, DOLL_FOOT_Y / DOLL_H);
    body.width = DOLL_W * k;
    body.height = DOLL_H * k;
    body.position.set(0, FEET);
    applyLook(body, u, downedLook(u.downed, false));
  }
  c.addChild(body);
  const row = statusRow(u, null, opts.edge);
  if (row !== null) c.addChild(row);
  const badges = statusBadges(u).map(statusBadge);
  const infused = infusedBadge(u);
  if (infused !== null) badges.push(infusedMark(infused));
  for (const b of badges) c.addChild(b.node);
  if (badges.length > 0) registerBadges(badges, null, row, faces, badgeMarks(u), 0);
  return c;
}

/** `buildUnitSprite` 的選項（6F-18：有人站的格子不畫「▲N」，6F-14 的 `heightDigits` 拿掉）。 */
export interface UnitSpriteOpts {
  /** 6F-16：站在地圖的最左、最右欄（狀態列的「+N」超出格子時不超出地圖）。 */
  edge?: MapEdge;
}

/**
 * 炸彈、蓄力、灌注徽章排法的選項（6F-15，測試與舊介面用；繪製時走 `badgeMarks`）：朝向三角形（方框與形狀）、HP 條。
 */
export function badgeOptsOf(u: UnitDraw): BadgeLayoutOpts {
  const m = badgeMarks(u);
  return { firmBoxes: m.arrow === null ? [] : [m.arrow], ...(m.arrowPoly === null ? {} : { arrowPoly: m.arrowPoly }), hpBoxes: m.hp === null ? [] : [m.hp] };
}

/** HP 條（含護盾條）畫出來的方框（相對格子中心；6F-15 徽章不蓋到）。沒有 HP 條時 `null`。 */
export function hpBoxOf(u: Pick<UnitDraw, "noBar" | "shieldRatio">): Box | null {
  if (u.noBar === true) return null;
  const w = T * 0.8;
  const o = u.shieldRatio > 0 ? SHIELD_OUTLINE : 0; // 6F-22b：護盾條的外框
  return { l: -w / 2 - o, r: w / 2 + o, t: T * 0.36 - (u.shieldRatio > 0 ? 3 + o : 0), b: T * 0.36 + 5 };
}

/** 朝向三角形的三個頂點（世界座標；和 `arrowOf` 同一個三角形）。倒下或沒有底圈時 `null`。 */
export function arrowPolyOf(u: Pick<UnitDraw, "downed" | "facing" | "summon" | "summonLook"> & Partial<Pick<UnitDraw, "noBar" | "shieldRatio">>): number[] | null {
  if (arrowOf(u) === null) return null;
  return facingArrowPoly(u);
}

/** 6F-21：朝南的三角形和 HP 條下緣之間的空隙（世界座標，含描邊之外）。 */
export const SOUTH_ARROW_GAP = 0.5;
/** 朝向三角形的描邊寬度（`buildUnitSprite` 畫的 `stroke width 1`）。 */
const ARROW_STROKE = 1;

/** 6F-21：朝向三角形移到 HP 條下面（朝南、有 HP 條）。 */
export function southArrowMoved(u: Pick<UnitDraw, "facing"> & Partial<Pick<UnitDraw, "noBar">>): boolean {
  return u.facing === "south" && u.noBar !== true;
}

/**
 * 朝向三角形的三個頂點（世界座標，不管倒下或底圈；`buildUnitSprite`、`arrowOf`、`arrowPolyOf` 共用）。
 * 底圈外緣的尖角（`ringArrow(facing, 0, FEET − 1, T × 0.36, T × 0.15, 5)`）；
 * 6F-21（美術 PM 6F-14 檢查第 3 節）：朝南、有 HP 條時，原位幾乎整個被 HP 條蓋住，整個往下移到 HP 條下緣外面
 * （三角形上緣含描邊離 HP 條下緣 `SOUTH_ARROW_GAP`），形狀不變。其他朝向、沒有 HP 條時照原位。
 */
export function facingArrowPoly(u: Pick<UnitDraw, "facing"> & Partial<Pick<UnitDraw, "noBar" | "shieldRatio" | "summon" | "summonLook" | "dollLook">>): number[] {
  const ring = arrowRing(u);
  const p = ringArrow(u.facing, ring.cx, FEET - 1, ring.rx, ring.ry, 5);
  const hp = southArrowMoved(u) ? hpBoxOf({ noBar: u.noBar, shieldRatio: u.shieldRatio ?? 0 }) : null;
  if (hp === null) return p;
  const top = Math.min(p[1]!, p[3]!, p[5]!) - ARROW_STROKE / 2;
  const dy = hp.b + SOUTH_ARROW_GAP - top;
  return dy <= 0 ? p : p.map((v, i) => (i % 2 === 1 ? v + dy : v));
}

/**
 * 朝向三角形貼著哪個底圈（QK-3b，docs/art/QK-3檢查.md 第 3 節）：四足召喚物（戰狼等，側面畫的 `beast`）身體橫著、頭伸到一般底圈外，
 * 原位的三角形被頭蓋住；改貼在召喚物放寬、往頭那邊移的底圈（`summonRing`）前緣。其他單位照一般底圈。
 */
export function arrowRing(u: Partial<Pick<UnitDraw, "summon" | "summonLook" | "dollLook" | "facing">>): { cx: number; rx: number; ry: number } {
  const rx = T * 0.36;
  const ry = T * 0.15;
  if (!isBeastSummon(u)) return { cx: 0, rx, ry };
  const draw = u as UnitDraw;
  const sr = summonRing(draw, summonLookOf(draw)!, rx, ry);
  return { cx: sr.dx, rx: sr.rx, ry: sr.ry };
}

/** QK-3b：朝向三角形要畫在身體上面（四足召喚物朝北：底圈後緣被身體蓋住）。 */
export function arrowAboveBody(u: Partial<Pick<UnitDraw, "summon" | "summonLook" | "dollLook" | "facing">>): boolean {
  return u.facing === "north" && isBeastSummon(u);
}

function isBeastSummon(u: Partial<Pick<UnitDraw, "summon" | "summonLook" | "dollLook">>): boolean {
  if (u.summon !== true || u.summonLook == null || u.dollLook?.creature != null) return false;
  return summonLookOf(u as UnitDraw)?.body === "beast";
}

/** 6F-14：徽章要避開的朝向三角形（`registerBadges`）；6F-15：也避開 HP 條。 */
interface BadgeMarks {
  arrow: Box | null;
  /** 6F-15：三角形的形狀（算圓蓋到多少）。 */
  arrowPoly: number[] | null;
  /** 6F-15：HP 條（含護盾條）。 */
  hp: Box | null;
}

function badgeMarks(u: UnitDraw): BadgeMarks {
  return { arrow: arrowOf(u), arrowPoly: arrowPolyOf(u), hp: hpBoxOf(u) };
}
