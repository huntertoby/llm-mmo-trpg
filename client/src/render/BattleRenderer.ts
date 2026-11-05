// PixiJS 繪製：照著 `DrawModel` 畫格子、物件、陷阱、單位與高亮；移動動畫只是過場，
// 播放完由呼叫端以新的 `view` 重畫（以 `view` 為準）。
// 縮放（Phase 3-8）：場景一律以「模型像素」（每格 TILE_SIZE）繪製；放大縮小只改畫布的解析度
// （devicePixelRatio × 縮放）與 CSS 大小，文字與線條因此保持清晰。滑鼠事件不經過 Pixi，
// 由 `BattleCanvas` 以 DOM 座標換算（`battle/stageLayout.ts` 的 `clientToTile`）。
// 高度「整格抬高」（Phase 3-19）：場景放在 `world`（往下移畫布上方預留的高度），由北到南一排一排畫
// （`RowStack`），格子上的所有東西都依 `tileLift` 往上移；位移只從 `battle/elevation.ts` 來。
import { Application, Container, GlobalResourceRegistry, Graphics, Sprite, UPDATE_PRIORITY, type Text, type Texture, type Ticker } from "pixi.js";
import type { Pos } from "../api/types";
import type { FeedbackItem, FloatTone } from "../battle/feedback";
import { lerpPos, rowDuringMove, type MoveAnim, type MoveStyle } from "../battle/animation";
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
import { VFX_TIMING, warpPlan, type StepVfx } from "../battle/vfx";
import { reactEffects, type ReactHost } from "./reactEffects";
import { riseEffects, specialEffects, victoryEffects, type ResultHost } from "./resultEffects";
import { addFreeze, advanceClock, type Freeze } from "./hitStop";
import type { FrameVictory } from "../battle/playback";
import { creatureReact, reactFrame } from "./reactClips";
import { RING } from "./artPalette";
import type { Ctx } from "./artDraw";
import { drawCasterRing, drawTrapPad, drawZoneCell, fxColor, sightVeil, turnsBadge, veilKindOf } from "./fieldFx";
import { fontEpoch } from "./fontLoad";
import { ArtTextures, liveSpriteTextures } from "./artTextures";
import { heightBadgeText, objectArtSpec, objectKinds, tileArtSpec } from "./artSpecs";
import { drawMistTile } from "./cloudRidgeTerrain";
import { mistLevel, type ArtTheme } from "./regionArt";
import { hasFlammableMark, hasObjectArt } from "./objectArt";
import { blastEffect, castEffects, hitEffects, impactShakeEffect, shakeEffect, warpEffects, type Effect } from "./vfxEffects";
import { LIFT_SHAKE_PX, type SlowSpan } from "../battle/impact";
import { drawCliff, drawEdges, liftEffects, silhouette } from "./heightArt";
import { RowStack } from "./rowLayers";
import { clearLayer, label } from "./labels";
import { applyMarkScale, HEIGHT_BADGE_LABEL, MIN_HEIGHT_BADGE_FONT_PX, registerMark, unitMarksOf } from "./minMark";
import { BODY_LABEL, bodyNodes, bodyTexture, buildUnitSprite, creatureOf, flashTexture, hasSkeleton, isLinked, isProne, overlayFlashKind, HUMAN_TOP_Y, placeCreatureBody, PRONE, Pulses, unitTopY, type BodyFrame } from "./unitSprite";
import { clearFlash, overlayFlash } from "./silhouetteFlash";
import { eventBob, eyeOffset, eyeTexture, footprintShapes, MARK_PAD, MARK_SIZE, objectHintAlpha, thingTexture, type MapThing, type WatchEye } from "./mapMarks";
import { IdleMotion } from "./idleMotion";
import { AmbientLayer, type AmbientHost } from "./ambientLayer";
import { BIG_REST, floatBaseY, floatFit, floatFontSize, floatFrame, FLOAT_HEAD_GAP, FLOAT_RISE_MAX } from "./uiAnim";
import { capRise, clampFloatCenter, FLOAT_EDGE_PAD, FloatStack, floatTopShift, groupRise, type FloatBounds } from "./floatStack";
import { EFFECT_LAYER_ORDER, effectLayerOf, type EffectLayer } from "./effectLayer";
import { clipHighlights, mapClipRect } from "./mapClip";
import { isSubmerged, SUBMERGED_ALPHA, SUBMERGED_TINT, waterline, WATERLINE_ALPHA, WATERLINE_COLOR } from "./submerged";
import { prefersReducedMotion, subscribeReducedMotion } from "../world/frameLoop";
import { devAnimFactor } from "../battle/playback";

/** 環境動態跟著開發用的 `?anim=0.1` 放慢（6N-10，逐格驗收用；正式畫面 ＝ 1）。 */
const AMBIENT_SLOW = devAnimFactor(typeof window === "undefined" ? "" : window.location.search);
import { arriveFrame, doorOpenness, leaveFrame, type DoorMotion, type TransitFrame, type TransitKind } from "./doorClips";
import { MotionAnims } from "./motionAnims";
import { drawLethalCorners, LETHAL_TINT_ALPHA, lethalCornersOf, lethalTintCells } from "./lethalMarks";
import { objectLayerOf, SceneryLayer, type SceneryHost } from "./sceneryLayer";
import { roofCovers } from "./sceneryModel";
import type { SurfaceHost } from "./surfaceAnimLayer";
import { DOLL_SCALE } from "./paperdoll";
import type { InkPose } from "./inkPose";
import { CREATURE_CLIPS, quantizeCreaturePose } from "./creaturePose";
import { LINK_COLOR } from "./inkCreature";
import { linkPairs } from "./linkLines";
import { drawRegionBlobs, type RegionMark } from "./regionBlobs";
import type { PathDraw, PathTag } from "../battle/pathPreview";
import {
  bangCenter,
  drawFaintGrid,
  drawPathLine,
  drawPathMarks,
  drawSoftCells,
  HIT_SOFT,
  missTagNode,
  MOVE_SOFT,
  pathTagNode,
  RANGE_SOFT,
  placeTags,
  type TileGeo,
} from "./pathArt";
import { cameraNudge, facingOf, type Gait, type WalkAnim, type WalkBeat } from "../battle/walkAnim";
import { DUST_FROM, gaitPose, HUMAN_HIT_MS, humanHit, knockOffset, legFrame, proneBody, quantizeFlash, skidBody, stumbleTilt, tilePhase } from "./motionClips";
import { beatEffects, landingDust } from "./walkFx";
import { FEET, gripOf } from "./unitSprite";
import type { SkillRow } from "../battle/skillSequence";
import { anchorPoint, clipDef, clipFrame, clipHitFrame, recoverFrame, weaponClassOf, type Anchor, type ClipFrame, type FxCue, type WeaponClass } from "./skillClips";
import { leapShape, routeOffset, ZIGZAG_CORNERS } from "./skillVariants";
import { attackFamilyOf, type AttackFamily } from "./attackVariants";
import { reduceEffects, reduceVfx, REDUCED_FLASH_MS } from "./reducedMotion";
import { cueEffect } from "./skillFx";
import { weaponFrame } from "./inkWeaponFrame";
import type { Facing } from "../api/types";

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
}

const T = TILE_SIZE;
/** 高度標記「▲N」的數字字級（世界座標；6F-9 起畫面上至少 `MIN_HEIGHT_BADGE_FONT_PX`）。 */
export const HEIGHT_BADGE_FONT = 10;
/** 紙娃娃的虛擬像素 → 格子像素（52px 格縮放 0.92）。 */
const DOLL_PX = (T / 52) * DOLL_SCALE;
/** 可燃小火苗平時的透明度（3-38）。 */
export const FLAME_DIM = 0.4;
const BACKGROUND = 0x15151c;
/**
 * 銷毀時移除畫布、銷毀場景，但**不在銷毀當下釋放 Pixi 的全域資源**（UI-T1）：`app.destroy(true)` 會呼叫
 * `GlobalResourceRegistry.release()`，把所有繪製器共用的批次池、貼圖池清掉；另一個還活著的繪製器
 * 手上的批次被銷毀，下一幀就丟例外、畫面整塊黑，而且壞掉的批次會被還回池子、連下一個繪製器一起壞，要 F5 才恢復。
 * 全域資源改成「最後一個繪製器銷毀後」才釋放（見 `releaseIfLast`），同時清掉壞掉的批次。
 */
const APP_DESTROY_VIEW = { removeView: true } as const;
/** 還沒銷毀的繪製器數量（含初始化中的）。 */
let liveRenderers = 0;

/** 沒有其他繪製器活著時才釋放 Pixi 的全域池（避免累積，也清掉壞掉的批次）。 */
function releaseIfLast(): void {
  if (liveRenderers === 0) GlobalResourceRegistry.release();
}
const APP_DESTROY_SCENE = { children: true } as const;
/** WebGL context 遺失後等瀏覽器恢復的時間；超過就重建繪製器。 */
const CONTEXT_RESTORE_MS = 2000;

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

/** 量好大小、還沒放位置的浮動字（6F-6）。 */
interface FloatLabel {
  t: Text;
  big: boolean;
  isStatus: boolean;
  fit: number;
  /** 停住時的高度、寬度（已乘縮放）。 */
  restH: number;
  restW: number;
  /** 這個字自己最多往上飄多少。 */
  riseMax: number;
}

/** 浮動字在同一格那一組裡的位置（6F-6 `FloatStack`）。 */
interface FloatSpot {
  offset: number;
  /** 這一組第一個字停住時的高度（位移從它貼頭頂時的中心算，6F-10b）。 */
  firstH: number;
  /** 這一格整疊往下推的量（實際時間；頭頂放不下時，`FloatStack.placeGroup`）。 */
  shiftAt: (nowMs: number) => number;
  /** 這一組晚多久才出現（同一格的舊字要滑下來時等它們滑完；6F-10b）。 */
  waitMs: number;
  order: number;
  /** 整組一起飄的距離（組內最大的）。 */
  riseMax: number;
}

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
  /** 可燃小火苗的節點（3-38；每次重畫重建）與目前是否明顯。 */
  private flameMarks: Container[] = [];
  private flameOn = false;
  /** 浮動的事件「！」泡泡（6C-8；每次重設高亮時重建）與它們的基準高度。 */
  private bobs: Array<{ node: Sprite; y: number }> = [];
  /** 情境物件提示的虛線圈（6C-8b，呼吸的不透明度）。 */
  private breaths: Sprite[] = [];
  private bobClock = 0;
  private readonly hover = new Container();
  private readonly effects = new Container();
  /** 6F-6：地上的特效（範圍每格的爆發、光柱、扇形、目標格上的片段特效），用 `groundMask` 裁在地圖內。 */
  private readonly groundFx = new Container();
  private readonly groundMask = new Graphics();
  /** 6F-7：狀態光環（畫在浮動字下面，`effectLayer.ts`）。 */
  private readonly floatRings = new Container();
  private effectList: Effect[] = [];
  /** 每一格還在播的浮動字（6F-6：新的一組接在舊的上面）。 */
  private readonly floatStack = new FloatStack();
  private effectClock = 0;
  /** 命中時的停頓（6N-5）：效果時鐘走到 `at` 時停住 `left` 毫秒（依時間排序）。 */
  private freezes: Freeze[] = [];
  /** 最後一擊放慢（6H-1）：效果時鐘上的範圍（絕對時間）。 */
  private slows: SlowSpan[] = [];
  /** 實際時間（6H-1：傷害數字照它走，停頓、放慢時照常速）。 */
  private realClock = 0;
  private effectTick: ((ticker: Ticker) => void) | null = null;
  private readonly unitSprites = new Map<string, Container>();
  /** 單位的繪製資料（走路轉彎時用新的朝向重建小人，6A-4d）。 */
  private readonly unitDrawOf = new Map<string, UnitDraw>();
  /** 倒下的人（6N-4：只給倒下片段用；`unitSprites` 照舊不含倒下的人）。 */
  private readonly downedSprites = new Map<string, Container>();
  private readonly downedDrawOf = new Map<string, UnitDraw>();
  /** 移動中鏡頭稍微跟著角色（6A-4d）：目前的偏移與目標，加在戰場圖層上。 */
  private readonly cam = { x: 0, y: 0, tx: 0, ty: 0 };
  private camTick: ((ticker: Ticker) => void) | null = null;
  private worldBaseY = 0;
  /** 程式繪製的地形、物件貼圖快取（Phase 3-16a）。 */
  private readonly art = new ArtTextures();
  private model: DrawModel | null = null;
  /**
   * 進行中的升降動畫：格子 → 目前補間到的高度與目標。播放結束時常會再重畫一次（同樣的結果），
   * 目標高度沒變的動畫在重畫後接著播；目標變了（又有新的地形變化）就以新畫面為準。
   */
  private readonly lifting = new Map<string, LiftState>();
  /** 待機（6M-4）：站著的人呼吸、偶爾的小動作。 */
  private readonly idle = new IdleMotion();
  /** 環境動態（6N-10）：營火、燈籠、草、酒旗、水波、薄霧。 */
  private readonly ambient = new AmbientLayer();
  /** 減少動態（6N-10）：環境動態與待機不跑、傷害數字直接顯示。 */
  private reduced = false;
  private unsubscribeMotion: (() => void) | null = null;
  /** 實地地圖只畫的外觀：建築、門、室內外框、家具（6B-ART1）。 */
  private readonly scenery = new SceneryLayer();
  /** 狀態動作與地表動畫（6N-9）。 */
  readonly motion = new MotionAnims();
  private readonly drawWaiters: Array<() => void> = [];
  private ready = false;
  private destroyed = false;
  /** 算繪丟過例外或 WebGL context 一直沒恢復（UI-T1）；之後不再算繪，等 `BattleCanvas` 換新的繪製器。 */
  private broken = false;
  private lostTimer: number | null = null;
  /** 繪製器壞掉時呼叫一次（`BattleCanvas` 用來重建；銷毀後不再呼叫）。 */
  onBroken: (() => void) | null = null;
  /** 畫面上的縮放比例（1 ＝ 每格 TILE_SIZE 個 CSS 像素）。 */
  private scale = 1;
  /** 這一輪畫的高度標記（6F-9：縮放改變時重設最小尺寸）。 */
  private heightBadges: Container[] = [];

  constructor() {
    liveRenderers += 1;
  }

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
      this.app.destroy(APP_DESTROY_VIEW, APP_DESTROY_SCENE);
      releaseIfLast();
      return;
    }
    host.appendChild(this.app.canvas);
    const stage = this.app.stage;
    stage.addChild(this.world);
    // 6F-6：地上的特效在 groundFx（裁在地圖矩形內，`mapClip.ts`），其他特效與浮動字在 effects（不裁）
    this.groundFx.mask = this.groundMask;
    this.world.addChild(this.rows.root, this.marks, this.ambient.root, this.silhouettes, this.hover, this.groundMask, ...EFFECT_LAYER_ORDER.map((id) => this.effectLayer(id)));
    // 6R-F（前端審查第 2 點）：銷毀貼圖前先看畫面上活著的 Sprite 還拿著哪些（安全網）
    this.art.setLiveProbe(() => liveSpriteTextures(stage));
    if (import.meta.env.DEV) (window as unknown as { __texStats?: () => ReturnType<ArtTextures["stats"]> }).__texStats = () => this.art.stats();
    this.applyReducedMotion();
    this.unsubscribeMotion = subscribeReducedMotion(() => this.applyReducedMotion());
    // 自動算繪換成有防護的版本（UI-T1）：Pixi 的 ticker 只要有一個監聽丟例外就不再排下一幀，畫布會停在
    // 最後一幀（剛改過大小時是整塊黑）；改成接住例外並通知 `onBroken`，由 `BattleCanvas` 換一個新的繪製器。
    const ticker = this.app.ticker;
    ticker.remove(this.app.render, this.app);
    ticker.add(this.safeRender, this, UPDATE_PRIORITY.LOW);
    ticker.add((t) => this.guard(() => this.pulses.tick(t.deltaMS)));
    ticker.add((t) => this.guard(() => this.tickIdle(t.deltaMS)));
    ticker.add((t) => this.guard(() => this.ambient.tick(t.deltaMS / AMBIENT_SLOW)));
    ticker.add((t) => this.guard(() => this.tickBobs(t.deltaMS)));
    ticker.add((t) => this.guard(() => this.motion.tick(t.deltaMS, this.unitSprites, this.unitDrawOf, (id) => this.idle.isHeld(id))));
    this.motion.start();
    this.app.canvas.addEventListener("webglcontextlost", this.onContextLost);
    this.app.canvas.addEventListener("webglcontextrestored", this.onContextRestored);
    stage.eventMode = "none";
    this.app.canvas.style.display = "block";
    this.ready = true;
    if (this.model !== null) this.draw(this.model);
  }

  destroy(): void {
    if (this.destroyed) return;
    this.destroyed = true;
    liveRenderers -= 1;
    this.onBroken = null;
    this.unsubscribeMotion?.();
    this.unsubscribeMotion = null;
    this.clearLostTimer();
    for (const e of this.effectList) e.end?.();
    this.effectList = [];
    this.motion.stop();
    if (this.ready && this.camTick !== null) this.app.ticker?.remove(this.camTick);
    this.camTick = null;
    if (this.ready) {
      this.app.canvas.removeEventListener("webglcontextlost", this.onContextLost);
      this.app.canvas.removeEventListener("webglcontextrestored", this.onContextRestored);
      this.app.destroy(APP_DESTROY_VIEW, APP_DESTROY_SCENE);
      releaseIfLast();
    }
    this.art.destroy();
    this.ready = false;
  }

  /** 自動算繪（取代 Pixi 預設的 `app.render`）：例外時標記壞掉並通知，不讓 ticker 停擺。 */
  private safeRender(): void {
    if (this.broken) return;
    this.guard(() => this.app.render());
  }

  /** 執行 ticker 上的一段工作；丟例外時視為繪製器壞掉。 */
  private guard(work: () => void): void {
    if (this.broken) return;
    try {
      work();
    } catch (e) {
      this.fail(e);
    }
  }

  /** 繪製器壞掉：只通知一次（非同步，避免在 ticker 或 React 繪製中途換掉繪製器）。 */
  private fail(reason: unknown): void {
    if (this.broken || this.destroyed) return;
    this.broken = true;
    console.error("[BattleRenderer] 戰場繪製失敗，重建繪製器", reason);
    window.setTimeout(() => this.onBroken?.(), 0);
  }

  private readonly onContextLost = (): void => {
    // Pixi 已呼叫 preventDefault 等瀏覽器恢復；太久沒恢復（瀏覽器不再給 WebGL）就重建。
    this.clearLostTimer();
    this.lostTimer = window.setTimeout(() => {
      this.lostTimer = null;
      this.fail(new Error("WebGL context 遺失後沒有恢復"));
    }, CONTEXT_RESTORE_MS);
  };

  private readonly onContextRestored = (): void => {
    this.clearLostTimer();
    if (this.model !== null && !this.broken) this.draw(this.model);
  };

  private clearLostTimer(): void {
    if (this.lostTimer === null) return;
    window.clearTimeout(this.lostTimer);
    this.lostTimer = null;
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
    this.worldBaseY = topReserve(model);
    const clip = mapClipRect(model); // 6F-6：地上特效的裁切矩形
    this.groundMask.clear().rect(clip.x, clip.y, clip.width, clip.height).fill({ color: 0xffffff });
    this.world.y = this.worldBaseY + this.cam.y;
    const resolution = (window.devicePixelRatio || 1) * this.scale;
    this.art.setScreenScale(resolution);
    const r = this.app.renderer;
    if (r.screen.width !== size.width || r.screen.height !== size.height || r.resolution !== resolution) {
      r.resize(size.width, size.height, resolution);
    }
    const shown = scaledSize(model, this.scale);
    const style = this.app.canvas.style;
    style.width = `${shown.width}px`;
    style.height = `${shown.height}px`;
    this.scaleMarks();
  }

  /** 6F-9：一個標記節點依目前縮放保持最小尺寸（`minMark.ts`；沒登記過的節點不動）。 */
  private scaleMark(node: Container | null): void {
    if (node === null || node.destroyed) return;
    applyMarkScale(node, this.scale, (window.devicePixelRatio || 1) * this.scale);
  }

  /** 6F-11：一個單位的回合數徽章與腳邊狀態列（徽章先，狀態列重排時會搬它）。 */
  private scaleUnitMarks(unit: Container): void {
    for (const n of unitMarksOf(unit)) this.scaleMark(n);
  }

  /** 6F-9：縮放改變時，現有的高度標記與腳邊狀態列一起重設（場景不必重畫）。 */
  private scaleMarks(): void {
    for (const n of this.heightBadges) this.scaleMark(n);
    for (const s of this.unitSprites.values()) if (!s.destroyed) this.scaleUnitMarks(s);
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
    this.unitDrawOf.clear();
    this.downedSprites.clear();
    this.downedDrawOf.clear();
    this.idle.reset();
    this.idle.scene = model.ambient ?? null;
    this.pulses.clear();
    this.art.beginFrame();
    this.ambient.begin(model);
    this.flameMarks = [];
    this.heightBadges = [];
    for (const t of model.tiles) this.tileSprite(model, t);
    this.motion.drawSurfaces(model, this.surfaceHost);
    this.scenery.draw(this.sceneryHost(), model, model.scenery);
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
      const look = this.scenery.objectNode(this.sceneryHost(), o); // 6B-ART1：家具外觀取代物件畫法（規則不變）
      const node = look?.node ?? this.objectSprite(o, kinds, { region: model.region, look: model.look }, isSubmerged(model, o));
      objectLayerOf(this.rows, o).addChild(node); // 6F-6：家具照所在排 y 排序（同 6V-4b 站著的裝飾）
      this.place(node, o, o.x * T, o.y * T + (look?.dy ?? 0));
      if (look === null) this.ambient.object(node, o); // 6N-10：草叢、竹叢依風向擺
    }
    this.drawBadges(model);
    for (const trap of model.traps) this.drawTrap(trap);
    this.drawLinks(model);
    for (const u of model.units) this.drawUnit(model, u);
    this.motion.drawUnits(model);
    this.drawVeils(model);
    this.drawMist(model);
    this.ambient.draw(this.ambientHost(), model);
    this.art.endFrame();
    this.resumeLifts(model);
    const waiters = this.drawWaiters.splice(0);
    for (const w of waiters) w();
  }

  /** 重畫後：目標高度沒變的升降動畫套回目前的高度繼續播，其餘作廢。 */
  private resumeLifts(model: DrawModel): void {
    for (const [key, st] of [...this.lifting]) {
      if (heightAt(model, st.pos) === st.to) this.rows.setLift(st.pos, tileLift(st.h));
      else this.lifting.delete(key);
    }
  }

  /** 「連心的」精英到相鄰（曼哈頓 1）同陣營單位的青色虛線（Phase 5A-ART2），畫在腳邊、單位底下。 */
  private drawLinks(model: DrawModel): void {
    const color = parseInt(LINK_COLOR.slice(1), 16);
    for (const [a, b] of linkPairs(model.units, isLinked)) {
      const p = this.center(a);
      const q = this.center(b);
      const y0 = p.y + T * 0.2;
      const y1 = q.y + T * 0.2;
      const g = new Graphics();
      const n = 9;
      for (let i = 0; i < n; i += 2) {
        const t0 = i / n;
        const t1 = (i + 1) / n;
        g.moveTo(p.x + (q.x - p.x) * t0, y0 + (y1 - y0) * t0).lineTo(p.x + (q.x - p.x) * t1, y0 + (y1 - y0) * t1);
      }
      g.stroke({ width: 2, color, alpha: 0.9 });
      this.rows.row(Math.max(a.y, b.y)).deco.addChild(g);
    }
  }

  /** 一個單位：畫在所在排；被南邊高格擋住時另在最上層畫剪影。 */
  private drawUnit(model: DrawModel, u: UnitDraw): void {
    const sprite = buildUnitSprite(this.art, this.pulses, u);
    this.scaleUnitMarks(sprite); // 6F-9、6F-11
    this.holdBody(u.id, sprite); // 6R-F：這一輪畫到的人；沒畫到的（死掉、離場、換地圖）在 endFrame 放開
    this.rows.row(u.y).units.addChild(sprite);
    this.place(sprite, u, u.x * T + T / 2, u.y * T + T / 2);
    if (!u.downed) {
      this.unitSprites.set(u.id, sprite);
      this.unitDrawOf.set(u.id, u);
    } else {
      // 6N-4：倒下的人只給倒下片段找（命中那一刻重畫後，片段要接在倒地圖示的新節點上播完）；待機、狀態、走路照舊不碰
      this.downedSprites.set(u.id, sprite);
      this.downedDrawOf.set(u.id, u);
    }
    if (!occluded(model, u) && !roofCovers(model.scenery, u)) return; // 6B-ART1：屋頂蓋住屋後的人也畫剪影
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

  /** 區域的裝飾薄霧（3-37b；雲嶺）：每格一團淡淡的霧白，霧天加濃。只是裝飾，不影響視線規則。 */
  private drawMist(model: DrawModel): void {
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
      g.rect(0, 0, T, T).fill(t.fill); // 無法產生貼圖：退回色塊（6A-4a：待機不畫格線）
    }
    c.addChild(edges);
    if (t.deadly) drawLethalCorners(g, T, lethalCornersOf(model, t)); // 6V-2：小紅角標，6V-2b 起只畫在致命區外圍；滑過、預覽時的淡紅在 setHighlights
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
      const num = label(text, HEIGHT_BADGE_FONT, 0xfff3c4, true);
      num.position.set(14, 4);
      node.addChild(g, num);
      // 6F-9：數字在畫面上至少 10px（地圖縮小時以格子左上角為基準反向放大）
      node.label = HEIGHT_BADGE_LABEL;
      registerMark(node, { base: HEIGHT_BADGE_FONT, min: MIN_HEIGHT_BADGE_FONT_PX }, [num]);
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

  private objectSprite(o: ObjectDraw, kinds: ReadonlyMap<string, string>, theme: ArtTheme, submerged = false): Container {
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
    clearLayer(this.hover);
    const pen = this.markPen();
    const geo = this.geo();
    // 6A-4c：選移動、選技能時格子淡色圓角浮出，範圍外緣加亮線；選技能時格線極淡地浮出
    const range = h.range ?? [];
    if (range.length > 0 && this.model !== null) drawFaintGrid(pen.at(range[0] as Pos), this.model.tiles, geo);
    drawSoftCells(pen.at(h.moves[0] ?? { x: 0, y: 0 }), h.moves, geo, MOVE_SOFT);
    drawSoftCells(pen.at(range[0] ?? { x: 0, y: 0 }), range, geo, RANGE_SOFT);
    drawSoftCells(pen.at(h.preview[0] ?? { x: 0, y: 0 }), h.preview, geo, HIT_SOFT);
    if ((h.regions?.length ?? 0) > 0) {
      const rg = new Graphics();
      drawRegionBlobs(rg, h.regions ?? [], T, (p) => this.origin(p));
      this.marks.addChild(rg);
    }
    this.drawThings(h.things ?? [], h.eyes ?? []);
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
      pen.at(p).roundRect(o.x + 2, o.y + 2, T - 4, T - 4, 8).stroke({ width: 3, color: HIGHLIGHT.attack });
    }
    for (const tag of tags) pen.add(tag.pos, tag.text); // 文字標記畫在色塊之上
    if (h.path !== undefined) this.drawPath(h.path, geo);
    this.drawLethalTints(h);
    this.drawFrames(h.focus, h.hover);
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
      const at = eyeOffset(T, unit === undefined ? null : unitTopY(unit));
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
  private tickBobs(dt: number): void {
    this.bobClock += dt;
    if (this.breaths.length > 0) {
      const a = objectHintAlpha(this.bobClock);
      for (const n of this.breaths) if (!n.destroyed) n.alpha = a;
    }
    if (this.bobs.length === 0) return;
    const dy = eventBob(this.bobClock);
    for (const b of this.bobs) if (!b.node.destroyed) b.node.y = b.y + dy;
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

  /**
   * 依序播放移動動畫；`skip()` 為真時剩下的移動直接跳到終點。
   * 6M-3：步行（探索的主角、NPC 逐格走）用走路片段、衝鋒（`dash`）用跑步片段，腳步隨格子高低差走上去或跳上去；
   * 水平照舊等速（探索的鏡頭用同樣的時間等速平移）。其他位移照舊整個小人滑動或淡出淡入。
   */
  async animate(plan: readonly MoveAnim[], skip: () => boolean): Promise<void> {
    if (!this.ready) return;
    for (const m of plan) {
      const sprite = this.unitSprites.get(m.unitId);
      if (sprite === undefined) continue;
      this.idle.hold(m.unitId, sprite); // 移動中不播待機（6M-4）
      try {
        await this.moveOne(m, sprite, skip);
      } finally {
        this.idle.release(m.unitId);
      }
    }
  }

  private async moveOne(m: MoveAnim, start: Container, skip: () => boolean): Promise<void> {
    let sprite = start;
    const outline = this.silhouetteOf.get(m.unitId);
    if (outline !== undefined) outline.visible = false; // 剪影留在原位會誤導；重畫時再依新位置判斷
    const to = this.center(m.to);
    // 途中跟著當下所在的排換圖層（較南的那排），結束時回到終點那排
    const toRow = (s: Container) => (t: number) => {
      const units = this.rows.row(rowDuringMove(m.from.y, m.to.y, t)).units;
      if (!s.destroyed && s.parent !== units) units.addChild(s);
    };
    if (m.durationMs <= 0 || skip()) {
      sprite.position.set(to.x, to.y);
      toRow(sprite)(1);
      return;
    }
    const clipped = this.clipMove(m, sprite, skip, toRow);
    if (clipped !== null) {
      await clipped;
      return;
    }
    const gait: Gait | null = m.mode === "walk" ? "walk" : m.mode === "dash" ? "run" : null;
    if (gait !== null && m.style === "slide") {
      const facing = facingOf(m.from, m.to, this.unitDrawOf.get(m.unitId)?.facing ?? "south");
      if (facing !== this.unitDrawOf.get(m.unitId)?.facing) sprite = this.turn(m.unitId, sprite, facing);
      const tile = this.strideOf(m.unitId);
      await this.stepLeg(m.unitId, sprite, m.from, m.to, m.durationMs, skip, { gait, tile, linear: true, onRow: toRow(sprite) });
      this.restBody(m.unitId, sprite);
      return;
    }
    this.launch(warpEffects(warpPlan(m), this.effectClock, (p) => this.center(p))); // 傳送：起點消散、終點出現
    toRow(sprite)(0);
    await this.tween(sprite, this.center(m.from), to, m.durationMs, skip, m.style, toRow(sprite));
  }

  /**
   * 位移途中的身體片段（6N-2）：衝刺前傾、肩撞、跳躍（只抬小人）、傳送、瞬步、交換、被推（後仰）、被拉（前傾）。
   * 只有紙娃娃人形才換姿勢；沒有片段或沒有骨架回傳 `null`（照舊平移）。
   */
  private clipMove(m: MoveAnim, start: Container, skip: () => boolean, toRow: (s: Container) => (t: number) => void): Promise<void> | null {
    const draw = this.unitDrawOf.get(m.unitId);
    const clip = m.clip;
    // 6R-F：減少動態時不播位移片段（前傾、跳躍弧度、Z 字殘影、空翻），照舊平移
    if (clip === undefined || draw === undefined || !hasSkeleton(draw) || this.reduced) return null;
    return (async () => {
      let sprite = start;
      const target = m.clip === "pushed" || m.clip === "pulled";
      if (!target && m.style === "slide") {
        const facing = facingOf(m.from, m.to, draw.facing);
        if (facing !== draw.facing) sprite = this.turn(m.unitId, sprite, facing);
      }
      const now = this.effectClock;
      // 重畫場景時小人可能已被銷毀：特效停在最後的位置（6N-8 dev 頁重畫時遇到）
      let lastFeet = { x: sprite.x, y: sprite.y + FEET };
      const feet = () => (sprite.destroyed ? lastFeet : (lastFeet = { x: sprite.x, y: sprite.y + FEET }));
      const fxs = (clipDef(clip).fx ?? []).map((c) =>
        cueEffect(c.kind, feet, "default", now + m.durationMs * c.from, now + m.durationMs * c.to, c.where === "link" ? { from: this.center(m.to), to: () => this.center(m.from) } : undefined),
      );
      if (m.style === "fade") fxs.push(...warpEffects(warpPlan(m), now, (p) => this.center(p)));
      this.launch(fxs);
      // 6N-8：跳躍的弧度（低弧＝原本、高弧、空翻）只改離地高度與身體的旋轉
      const frame = (t: number) => {
        const f = clipFrame(clip, t);
        if (m.hop === undefined) return this.poseClip(m.unitId, sprite, f);
        const hop = leapShape(m.hop, t);
        this.poseClip(m.unitId, sprite, { ...f, air: f.air * hop.airScale });
        if (hop.spin !== 0) this.spinBody(sprite, hop.spin * (draw.facing === "west" ? -1 : 1));
      };
      frame(0);
      toRow(sprite)(0);
      if (m.style === "slide") {
        const a = this.center(m.from);
        const b = this.center(m.to);
        // 6N-8：衝刺的路線（直線、略彎、Z 字殘影）：往旁邊偏移，兩頭為 0，終點照舊是目標格
        const len = Math.hypot(b.x - a.x, b.y - a.y) || 1;
        const normal = { x: -(b.y - a.y) / len, y: (b.x - a.x) / len };
        const route = m.route;
        const corners = route === "zigzag" ? [...ZIGZAG_CORNERS] : [];
        await this.during(m.durationMs, skip, (t) => {
          if (sprite.destroyed) return;
          const p = lerpPos(a, b, t);
          const off = route === undefined ? 0 : routeOffset(route, t) * T;
          sprite.position.set(p.x + normal.x * off, p.y + normal.y * off);
          toRow(sprite)(t);
          frame(t);
          while (corners.length > 0 && t >= corners[0]!) {
            corners.shift();
            this.launch([this.afterimage(m.unitId, sprite, this.effectClock, m.durationMs * 0.8)]);
          }
        });
        if (sprite.destroyed) return;
        sprite.position.set(b.x, b.y);
        toRow(sprite)(1);
      } else {
        await this.tween(sprite, this.center(m.from), this.center(m.to), m.durationMs, skip, m.style, toRow(sprite));
      }
      this.restBody(m.unitId, sprite);
    })();
  }

  /** 一格片段畫面套到小人：骨架姿勢、離地高度、往面向方向的位移（南北向只走一半，有透視）。 */
  private poseClip(unitId: string, sprite: Container, f: ClipFrame): void {
    const draw = this.unitDrawOf.get(unitId);
    if (draw === undefined || sprite.destroyed) return;
    this.poseBody(unitId, sprite, { pose: f.pose }, f.air * DOLL_PX);
    const off = knockOffset(draw.facing, -f.forward * DOLL_PX);
    for (const node of bodyNodes(sprite)) {
      node.x = off.x;
      node.y += off.y;
    }
  }

  /** 6N-8 空翻：小人以腰（腳底往上 16 個虛擬像素）為軸轉 `angle`（順時針為正）；`restBody` 會轉回來。 */
  private spinBody(sprite: Container, angle: number): void {
    const h = 16 * DOLL_PX;
    for (const node of bodyNodes(sprite)) {
      node.rotation = angle;
      node.x += -h * Math.sin(angle);
      node.y += h * Math.cos(angle) - h;
    }
  }

  /** 6N-8 Z 字衝刺的殘影：在當下的位置留一張同樣的小人（偏藍、半透明），淡掉（只在效果圖層）。 */
  private afterimage(unitId: string, sprite: Container, now: number, ms: number): Effect {
    const node = new Container();
    const body = bodyNodes(sprite).find((n) => n.label === BODY_LABEL);
    const key = this.art.uniqueOwner(`afterimage:${unitId}`);
    if (body !== undefined) {
      const ghost = new Sprite(body.texture);
      this.art.holdFor(key, body.texture); // 殘影用的貼圖釘住（重畫場景時不被銷毀）
      ghost.anchor.copyFrom(body.anchor);
      ghost.scale.copyFrom(body.scale);
      ghost.tint = 0xcfe6ff;
      ghost.position.set(sprite.x + body.x, sprite.y + body.y);
      node.addChild(ghost);
    }
    return {
      node,
      startMs: now,
      endMs: now + Math.max(1, ms),
      motion: "fx",
      update: (t) => {
        node.alpha = 0.55 * (1 - t);
      },
      end: () => {
        this.art.holdFor(key, null);
      },
    };
  }

  /** 施放者的武器種類（起手對照表的列；6N-1）。沒有骨架的單位當空手。 */
  weaponClassOf(unitId: string): WeaponClass {
    const u = this.unitDrawOf.get(unitId);
    const g = u === undefined ? null : gripOf(u);
    return g === null ? "bare" : weaponClassOf(g.main, g.off);
  }

  /** 施放者普攻的變體表列（6N-6）；沒有骨架（異形、形態、召喚物）或不是近戰武器為 `null`（異形出招照舊播通用的「撲」）。 */
  attackFamilyOf(unitId: string): AttackFamily | null {
    const u = this.unitDrawOf.get(unitId);
    const g = u === undefined ? null : gripOf(u);
    return g === null ? null : attackFamilyOf(g.main, g.off);
  }

  /** 按住空白鍵暫時加速（6N-1）：畫布上所有動畫（片段、特效、走路、待機）的時間一起快 `rate` 倍。 */
  setBoost(rate: number): void {
    if (this.ready) this.app.ticker.speed = rate > 0 ? rate : 1;
  }

  /** 片段起點在畫面上的位置（紙娃娃座標 → 模型像素；作用端照武器的長度）。 */
  private anchorWorld(unitId: string, f: ClipFrame, anchor: Anchor): { x: number; y: number } | null {
    const sprite = this.unitSprites.get(unitId);
    const draw = this.unitDrawOf.get(unitId);
    if (sprite === undefined || sprite.destroyed || draw === undefined) return null;
    const grip = gripOf(draw);
    const main = grip?.main;
    const len = anchor === "tip" && main !== undefined ? (weaponFrame(main, { side: draw.facing === "east" || draw.facing === "west" })?.len ?? 0) : 0;
    const a = anchorPoint(f.pose, anchor, draw.facing, len);
    const off = knockOffset(draw.facing, -f.forward);
    return { x: sprite.x + (a.x + off.x) * DOLL_PX, y: sprite.y + FEET + (a.y + off.y - f.air) * DOLL_PX };
  }

  /**
   * 技能的身體片段（6N-1／6N-2；`battle/skillSequence.ts` 的時間軸，時間已依速度縮放、和 `playVfx` 同一個原點）：
   * 施放者先轉向目標，再照時間軸播起手、加力、出招、出招後的原語、收勢；被撞倒的人倒下。異形只有出招播「撲」，
   * 形態、召喚物不動。回傳每一段出招在命中那一刻的作用端位置（特效從那裡發出）。
   */
  playSkill(rows: readonly SkillRow[]): Map<number, { x: number; y: number }> {
    const origins = new Map<number, { x: number; y: number }>();
    if (!this.ready || rows.length === 0) return origins;
    const now = this.effectClock;
    const turned = new Set<string>();
    for (const r of rows) {
      if (turned.has(r.unitId) || r.clip === "knocked_down" || r.target === null) continue;
      turned.add(r.unitId);
      const draw = this.unitDrawOf.get(r.unitId);
      const sprite = this.unitSprites.get(r.unitId);
      if (draw === undefined || sprite === undefined || (draw.x === r.target.x && draw.y === r.target.y)) continue;
      const facing = facingOf({ x: draw.x, y: draw.y }, r.target, draw.facing);
      if (facing !== draw.facing) this.turn(r.unitId, sprite, facing);
    }
    const effects: Effect[] = [];
    for (const r of rows) {
      if (!r.still) effects.push(this.rowEffect(r, now));
      if (!r.recover) effects.push(...this.rowCues(r, now));
      if (r.strike && r.hitMs !== null) {
        const def = clipDef(r.clip);
        const o = this.anchorWorld(r.unitId, clipHitFrame(r.clip), def.anchor);
        if (o !== null) origins.set(r.cast, o);
      }
    }
    this.launch(effects);
    return origins;
  }

  private rowFrame(r: SkillRow, t: number): ClipFrame {
    return r.recover ? recoverFrame(r.clip, t) : clipFrame(r.clip, t);
  }

  private rowEffect(r: SkillRow, now: number): Effect {
    let held = false;
    const current = () => {
      const s = this.unitSprites.get(r.unitId);
      return s === undefined || s.destroyed ? null : s;
    };
    return {
      node: new Container(),
      startMs: now + r.startMs,
      endMs: now + r.startMs + r.ms,
      motion: "body",
      update: (t) => {
        const s = current();
        const draw = this.unitDrawOf.get(r.unitId);
        if (s === null || draw === undefined) return;
        if (!held) {
          held = true;
          this.idle.hold(r.unitId, s);
        }
        if (r.clip === "knocked_down") {
          if (creatureOf(draw) !== null) {
            this.poseBody(r.unitId, s, { creature: quantizeCreaturePose(CREATURE_CLIPS.fall.pose(t)) });
            return;
          }
          const lie = proneBody(t, draw.facing);
          for (const node of bodyNodes(s)) {
            node.position.set(lie.x, FEET + lie.y);
            node.rotation = lie.rotation;
          }
          // 6N-4：被撞倒的人不另播受擊，命中那一刻的白閃（只閃剪影）由這個片段帶
          const flash = humanHit(Math.min(1, (t * clipDef("knocked_down").ms) / HUMAN_HIT_MS)).flash;
          if (hasSkeleton(draw) || isProne(draw)) this.poseBody(r.unitId, s, { pose: lie.pose, flash });
          for (const node of bodyNodes(s)) node.position.set(lie.x, FEET + lie.y);
          return;
        }
        if (hasSkeleton(draw)) this.poseClip(r.unitId, s, this.rowFrame(r, t));
        else if (r.strike && creatureOf(draw) !== null) this.poseBody(r.unitId, s, { creature: quantizeCreaturePose(CREATURE_CLIPS.pounce.pose(t)) });
      },
      end: () => {
        const s = current();
        if (r.clip === "knocked_down") this.markProne(r.unitId);
        if (s !== null) this.restBody(r.unitId, s);
        if (held) this.idle.release(r.unitId);
        held = false;
      },
    };
  }

  /** 片段的特效提示（武器發光、符陣、光點、連線…）。 */
  private rowCues(r: SkillRow, now: number): Effect[] {
    const def = clipDef(r.clip);
    const cues: readonly FxCue[] = def.fx ?? [];
    if (cues.length === 0) return [];
    const rowT = () => Math.max(0, Math.min(1, (this.effectClock - now - r.startMs) / r.ms));
    const anchor = () => this.anchorWorld(r.unitId, this.rowFrame(r, rowT()), def.anchor) ?? this.feetOf(r.unitId);
    const tc = r.target === null ? null : this.center(r.target);
    const target = (dy: number) => () => (tc === null ? this.feetOf(r.unitId) : { x: tc.x, y: tc.y + dy });
    const head = () => {
      const f = this.feetOf(r.unitId);
      return { x: f.x, y: f.y - T * 0.95 };
    };
    const chest = () => ({ x: this.feetOf(r.unitId).x, y: this.feetOf(r.unitId).y - T * 0.35 });
    return cues.map((c) => {
      const pos = c.where === "anchor" ? anchor : c.where === "feet" ? () => this.feetOf(r.unitId) : c.where === "head" ? head : c.where === "targetFeet" ? target(FEET) : c.where === "targetHead" ? target(-T * 0.75) : target(-T * 0.05);
      const link =
        c.where === "link" ? { from: tc ?? this.feetOf(r.unitId), to: chest } : c.where === "linkOut" ? { from: chest(), to: () => (tc === null ? chest() : { x: tc.x, y: tc.y - T * 0.05 }) } : undefined;
      const e = cueEffect(c.kind, pos, r.element, now + r.startMs + r.ms * c.from, now + r.startMs + r.ms * c.to, link, r.icon);
      // 6R-F：減少動態時不畫；6F-6：落在目標格上的（光柱、地上的法陣…）裁在地圖內
      const ground = c.where === "target" || c.where === "targetFeet";
      return { ...e, motion: "fx" as const, ...(ground ? { clip: "map" as const } : {}) };
    });
  }

  private feetOf(unitId: string): { x: number; y: number } {
    const s = this.unitSprites.get(unitId);
    return s === undefined || s.destroyed ? { x: 0, y: 0 } : { x: s.x, y: s.y + FEET };
  }

  // ---- 待機、進出門（6M-4）----------------------------------------------------

  /** 每幀推進待機：站著的人呼吸、偶爾換小動作的貼圖。 */
  private tickIdle(dt: number): void {
    this.idle.tick(dt, this.unitSprites, this.unitDrawOf, (id, sprite, pose, facing) => this.idlePose(id, sprite, pose, facing));
  }

  /** `facing`：NPC 職業動作時只畫的側面（6Q-1；底圈的朝向箭頭照規則的朝向不動）。 */
  private idlePose(unitId: string, sprite: Container, pose: InkPose | null, facing?: Facing): void {
    const base = this.unitDrawOf.get(unitId);
    if (base === undefined || sprite.destroyed) return;
    const draw = facing === undefined || facing === base.facing ? base : { ...base, facing };
    for (const node of bodyNodes(sprite)) {
      if (node.label !== BODY_LABEL) continue;
      const tex = bodyTexture(this.art, draw, { pose });
      if (tex !== null && node.texture !== tex) this.setBodyTexture(unitId, node, tex);
    }
  }

  /** 換小人的貼圖，並把它釘在 LRU 裡直到下次換（6N-4：美術 PM 6N-3 驗收第 4 點，站著不動的人不會被淘汰後閃一下）。 */
  private setBodyTexture(unitId: string, node: Sprite, tex: Texture): void {
    node.texture = tex;
    this.art.holdFor(unitId, tex);
  }

  /** 受擊與結果（6N-4，`reactEffects.ts`）用的操作。 */
  private readonly reactHost: ReactHost = {
    art: this.art,
    sprite: (id) => {
      const s = this.unitSprites.get(id) ?? this.downedSprites.get(id);
      return s === undefined || s.destroyed ? null : s;
    },
    draw: (id) => this.unitDrawOf.get(id) ?? this.downedDrawOf.get(id),
    hold: (id, s) => this.idle.hold(id, s),
    release: (id) => this.idle.release(id),
    setTexture: (id, node, tex) => this.setBodyTexture(id, node, tex),
    restBody: (id, s) => {
      if (this.unitDrawOf.has(id)) {
        this.restBody(id, s);
        return;
      }
      // 倒下的人：回到倒地圖示（重畫時 `unitSprite` 畫的樣子）
      const draw = this.downedDrawOf.get(id);
      if (draw === undefined || s.destroyed) return;
      for (const node of bodyNodes(s)) {
        node.position.set(0, FEET);
        node.rotation = 0;
        if (node.label !== BODY_LABEL) continue;
        const tex = bodyTexture(this.art, draw, {});
        if (tex !== null) this.setBodyTexture(id, node, tex);
      }
    },
  };

  /** 特殊結果、復活、勝利（6N-5，`resultEffects.ts`）用的操作：受擊的操作再加地圖大小。 */
  private readonly resultHost: ResultHost = {
    ...this.reactHost,
    bounds: () => ({ w: (this.model?.width ?? 0) * T, h: (this.model?.height ?? 0) * T }),
  };

  /**
   * 我方勝利（6N-5）：站著的我方每人播舉手或收刀、地圖上方浮出「勝利」。不等待結束（呼叫端照 `v.ms` 等）。
   */
  playVictory(v: FrameVictory): void {
    if (!this.ready || v.ms <= 0) return;
    this.launch(victoryEffects(this.resultHost, v, this.effectClock));
  }

  /** 地表動畫畫在哪裡（6N-9）：每一排的地形層、表面裝飾層，跟著格子抬高；舊的樣子用同一套地形貼圖。 */
  private readonly surfaceHost: SurfaceHost = {
    ground: (y) => this.rows.row(y).ground,
    deco: (y) => this.rows.row(y).deco,
    place: (node, t) => this.rows.place(node, t, t.x * T, t.y * T, tileLift(t.height)),
    oldTile: (from, t) => this.art.tile(tileArtSpec(from, t)),
  };

  /** 開關待機（截圖、量測用；關掉時下一幀全員站好）。 */
  setIdle(on: boolean): void {
    this.idle.enabled = on;
    this.ambient.enabled = on; // 6N-10：環境動態一起開關
  }

  /** 待機時鐘歸零（截圖時固定相位用；環境動態的時鐘一起設）。 */
  setIdleClock(ms: number): void {
    this.idle.clock = ms;
    this.ambient.clock = ms;
  }

  /** 讀系統的減少動態設定（6N-10）：待機、環境動態停下，傷害數字直接顯示。 */
  private applyReducedMotion(): void {
    this.reduced = prefersReducedMotion();
    this.idle.reduced = this.reduced;
    this.ambient.reduced = this.reduced;
  }

  private ambientHost(): AmbientHost {
    return { art: this.art, rows: this.rows, place: (node, p, x, y) => this.place(node, p, x, y), origin: (p) => this.origin(p) };
  }

  /** 等下一次重畫場景（換地圖後等新地圖畫好）；`timeoutMs` 內沒有重畫也繼續。 */
  nextDraw(timeoutMs: number): Promise<void> {
    return new Promise((resolve) => {
      let done = false;
      const finish = () => {
        if (done) return;
        done = true;
        resolve();
      };
      this.drawWaiters.push(finish);
      window.setTimeout(finish, timeoutMs);
    });
  }

  /** 目前快取的小人／地形貼圖數（效能量測用）。 */
  textureCount(): number {
    return this.art.size;
  }

  /** 把進出門、換地圖的一格畫到小人身上（整個人一起縮放、透明；走路時換姿勢）。 */
  private transitPose(unitId: string, sprite: Container, base: { x: number; y: number }, f: TransitFrame): void {
    if (sprite.destroyed) return;
    sprite.position.set(base.x + f.dx * T, base.y + f.dy * T - f.rise);
    sprite.scale.set(f.scale);
    sprite.alpha = f.alpha;
    if (f.pose !== null) this.poseBody(unitId, sprite, { pose: f.pose });
    else this.restBody(unitId, sprite);
  }

  /**
   * 離開這張地圖（進門／走出邊緣出口）：`ms` 毫秒內播離開片段，結束時停在看不見的樣子（之後換地圖會重畫）。
   * `facing` ＝ 走進門格／出口格的方向；門的話先轉身朝門。
   */
  async playLeave(unitId: string, kind: TransitKind, facing: Facing, ms: number, skip: () => boolean): Promise<void> {
    if (!this.ready) return;
    let sprite = this.unitSprites.get(unitId);
    if (sprite === undefined) return;
    if (facing !== this.unitDrawOf.get(unitId)?.facing) sprite = this.turn(unitId, sprite, facing);
    const s = sprite;
    const base = { x: s.position.x, y: s.position.y };
    this.idle.hold(unitId, s);
    try {
      await this.during(ms, skip, (u) => this.transitPose(unitId, s, base, leaveFrame(kind, facing, u)));
      this.transitPose(unitId, s, base, leaveFrame(kind, facing, 1));
    } finally {
      this.idle.release(unitId);
    }
  }

  private sceneryHost(): SceneryHost {
    return { art: this.art, rows: this.rows, place: (node, p, x, y) => this.place(node, p, x, y) };
  }

  /** 建築的門板轉開／關上（6B-ART1；`DOOR_OPEN_MS`）；那格沒有建築的門就馬上結束。 */
  async playDoor(cell: Pos, motion: DoorMotion, ms: number, skip: () => boolean): Promise<void> {
    if (!this.ready || !this.scenery.hasDoor(cell)) return;
    this.scenery.setDoor(cell, doorOpenness(motion, 0));
    await this.during(ms, skip, (u) => this.scenery.setDoor(cell, doorOpenness(motion, u)));
    this.scenery.setDoor(cell, doorOpenness(motion, 1));
  }

  /** 抵達新地圖（出門／從對面入口走進來一步）：從看不見播到站好。 */
  async playArrive(unitId: string, kind: TransitKind, facing: Facing, ms: number, skip: () => boolean): Promise<void> {
    if (!this.ready) return;
    let sprite = this.unitSprites.get(unitId);
    if (sprite === undefined) return;
    if (facing !== this.unitDrawOf.get(unitId)?.facing) sprite = this.turn(unitId, sprite, facing);
    const s = sprite;
    const base = { x: s.position.x, y: s.position.y };
    this.idle.hold(unitId, s);
    try {
      this.transitPose(unitId, s, base, arriveFrame(kind, facing, 0));
      await this.during(ms, skip, (u) => this.transitPose(unitId, s, base, arriveFrame(kind, facing, u)));
    } finally {
      this.transitPose(unitId, s, base, arriveFrame(kind, facing, 1));
      this.idle.release(unitId);
    }
  }

  /** 探索逐格走時左右腳交替：每個單位記下走過幾步（只影響畫面）。 */
  private readonly strides = new Map<string, number>();
  private strideOf(unitId: string): number {
    const n = this.strides.get(unitId) ?? 0;
    this.strides.set(unitId, n + 1);
    return n;
  }

  /**
   * 走一格（6M-3）：腳底照高低差抬高（差一級走上去、兩級以上跳上去），小人換走路／跳躍的姿勢，跳躍落地揚塵。
   * `linear`：水平等速（探索）；否則緩入緩出（戰場逐格，6A-4d）。`offset`：倒地後的位移（滑回時用）。
   */
  private async stepLeg(
    unitId: string,
    sprite: Container,
    from: Pos,
    to: Pos,
    durationMs: number,
    skip: () => boolean,
    opt: { gait: Gait; tile: number; linear?: boolean; onRow?: (t: number) => void },
  ): Promise<void> {
    const a = { x: from.x * T + T / 2, y: from.y * T + T / 2 };
    const b = { x: to.x * T + T / 2, y: to.y * T + T / 2 };
    const hA = this.heightOf(from);
    const hB = this.heightOf(to);
    let dusted = false;
    const frame = (u: number) => {
      if (sprite.destroyed) return;
      const f = legFrame(u, hA, hB, opt.gait, opt.tile);
      const p = lerpPos(a, b, opt.linear === true && f.mode === "walk" ? u : f.t);
      sprite.position.set(p.x, p.y - f.lift);
      opt.onRow?.(u);
      for (const node of bodyNodes(sprite)) {
        node.rotation = 0; // 走路時站起來（倒地狀態的人起身後才會走）
        node.x = 0;
      }
      this.poseBody(unitId, sprite, { pose: f.pose, creature: f.creature }, f.air);
      if (f.dust > 0 && !dusted) {
        dusted = true;
        const ms = Math.max(120, durationMs * (1 - DUST_FROM) + 200);
        this.launch([landingDust({ x: b.x, y: b.y - tileLift(hB) + FEET }, this.effectClock, ms)]);
      }
    };
    frame(0);
    await this.during(durationMs, skip, frame);
    frame(1);
  }

  /** 小人換姿勢（6M-3）：紙娃娃、異形換成這一格的貼圖（形態、召喚物沒有骨架，不換）；`air` ＝ 跳躍離地高度（只抬小人，底圈不動）。 */
  private poseBody(unitId: string, sprite: Container, frame: BodyFrame, air = 0): void {
    const draw = this.unitDrawOf.get(unitId);
    if (draw === undefined || sprite.destroyed) return;
    for (const node of bodyNodes(sprite)) {
      node.y = FEET - air;
      if (node.label !== BODY_LABEL || !(node instanceof Sprite)) continue;
      const tex = bodyTexture(this.art, draw, frame);
      if (tex !== null && node.texture !== tex) this.setBodyTexture(unitId, node, tex);
    }
    placeCreatureBody(this.art, unitId, sprite, draw, frame, { x: 0, y: FEET - air }); // 6R-F：異形的位移移節點
  }

  /** 滑倒後到下次重畫之前，把這個人當作倒地狀態（待機不套用、受擊不站起來；6M-4）。 */
  private markProne(unitId: string): void {
    const draw = this.unitDrawOf.get(unitId);
    if (draw === undefined || isProne(draw)) return;
    this.unitDrawOf.set(unitId, { ...draw, statusIds: [...(draw.statusIds ?? []), PRONE] });
  }

  /** 走完：小人回到站好（倒地狀態＝躺著）的貼圖與位置（之後的 `view` 會再以結果重畫）。 */
  private restBody(unitId: string, sprite: Container): void {
    const draw = this.unitDrawOf.get(unitId);
    if (draw === undefined || sprite.destroyed) return;
    const lie = isProne(draw) ? proneBody(1, draw.facing) : { x: 0, y: 0, rotation: 0 };
    for (const node of bodyNodes(sprite)) {
      node.position.set(lie.x, FEET + lie.y);
      node.rotation = lie.rotation;
      if (node.label !== BODY_LABEL || !(node instanceof Sprite)) continue;
      const tex = bodyTexture(this.art, draw, {});
      if (tex !== null) this.setBodyTexture(unitId, node, tex);
    }
    placeCreatureBody(this.art, unitId, sprite, draw, {}, { x: lie.x, y: FEET + lie.y }); // 6R-F：藏起動畫時的影子
  }

  /**
   * 一格一格走（6A-4d）：每格緩入緩出、轉彎時轉身；踩到特殊地表時在那一格停頓並播效果（冰花、滑倒、
   * 陷阱夾住、冒火、濺油），停頓結束才跳傷害數字與狀態圖示；倒在友軍格時短短滑回空格。鏡頭稍微跟著走路的人。
   * `skip()` 為真時直接跳到終點。6M-3：每格播走路（衝刺過的人播跑步）片段，照高低差走上去或跳上去；
   * 滑倒時只有小人倒下（底圈、血條不動），之後倒地狀態持續躺著（重畫時 `unitSprite` 照同一個姿勢畫）。
   */
  async animateWalk(walk: WalkAnim, skip: () => boolean): Promise<void> {
    if (!this.ready) return;
    let sprite = this.unitSprites.get(walk.unitId);
    if (sprite === undefined) return;
    this.idle.hold(walk.unitId, sprite); // 走路中不播待機（6M-4）
    const outline = this.silhouetteOf.get(walk.unitId);
    if (outline !== undefined) outline.visible = false;
    let facing: Facing = this.unitDrawOf.get(walk.unitId)?.facing ?? "south";
    const gait: Gait = walk.gait ?? "walk";
    const units = (row: number) => this.rows.row(row).units;
    const track = (s: Container, from: Pos, to: Pos) => (t: number) => {
      const layer = units(rowDuringMove(from.y, to.y, t));
      if (!s.destroyed && s.parent !== layer) layer.addChild(s);
      if (!s.destroyed) this.follow(s.position);
    };
    let last: Pos | null = null;
    let tile = 0;
    let lying = false;
    let skidding = false;
    try {
      for (const piece of walk.pieces) {
        if (sprite.destroyed || skip()) break;
        if (piece.kind === "beat") {
          if (await this.playBeat(walk.unitId, sprite, piece, facing, skip, tile, skidding)) lying = true;
          continue;
        }
        if (piece.kind === "leg") {
          if (piece.facing !== facing) {
            sprite = this.turn(walk.unitId, sprite, piece.facing);
            facing = piece.facing;
          }
          await this.stepLeg(walk.unitId, sprite, piece.from, piece.to, piece.durationMs, skip, { gait, tile, onRow: track(sprite, piece.from, piece.to) });
          tile += 1;
        } else if (piece.kind === "skid") {
          // 冰面滑行（#123）：不踏步、等速，身體往後仰、雙手張開
          const lean = skidBody(piece.facing);
          for (const node of bodyNodes(sprite)) node.rotation = lean.rotation;
          this.poseBody(walk.unitId, sprite, { pose: lean.pose });
          await this.tween(sprite, this.center(piece.from), this.center(piece.to), piece.durationMs, skip, "slide", track(sprite, piece.from, piece.to));
          skidding = true;
        } else {
          // 倒地後滑回空格：身體保持躺著，整個單位滑過去
          await this.tween(sprite, this.center(piece.from), this.center(piece.to), piece.durationMs, skip, "slide", track(sprite, piece.from, piece.to), (t) => 1 - (1 - t) ** 2);
        }
        last = piece.to;
      }
    } finally {
      // 略過：直接放到終點（之後的 `view` 會以結果重畫）
      const end = [...walk.pieces].reverse().find((p): p is Exclude<typeof p, WalkBeat> => p.kind !== "beat");
      if (end !== undefined && last !== end.to && !sprite.destroyed) {
        const c = this.center(end.to);
        sprite.position.set(c.x, c.y);
        const layer = units(end.to.y);
        if (sprite.parent !== layer) layer.addChild(sprite);
      }
      if (!lying) this.restBody(walk.unitId, sprite);
      else this.markProne(walk.unitId);
      this.follow(null);
      this.idle.release(walk.unitId);
    }
  }

  /** 走路途中的一個停頓：腳下效果 →（滑倒時只有小人倒下）→ 停頓 → 跳數字與狀態圖示。回傳是否倒下了。 */
  private async playBeat(unitId: string, sprite: Container, beat: WalkBeat, facing: Facing, skip: () => boolean, tile: number, skidding = false): Promise<boolean> {
    const c = this.center(beat.pos);
    if (beat.fxMs > 0) this.launch(beatEffects(beat.beat, { x: c.x, y: c.y + FEET }, this.effectClock, beat.fxMs));
    let fell = false;
    if (beat.beat === "stumble") {
      // 冰面第一格檢定失敗（#123）：踉蹌晃兩下，接著滑行
      const walking = gaitPose(tilePhase(tile, 0));
      this.poseBody(unitId, sprite, { pose: walking });
      await this.during(beat.holdMs, skip, (t) => {
        if (sprite.destroyed) return;
        for (const node of bodyNodes(sprite)) node.rotation = stumbleTilt(t);
      });
      for (const node of bodyNodes(sprite)) node.rotation = 0;
    } else if (beat.beat === "slip") {
      // 從走路（滑行後＝滑行姿勢）的最後一個姿勢倒下：腳往前溜，再以腳底為軸往後倒，最後躺著（和倒地狀態重畫時的樣子相同）
      const walking = skidding ? skidBody(facing).pose : gaitPose(tilePhase(tile, 0));
      const lay = (t: number) => {
        if (sprite.destroyed) return;
        const p = proneBody(t, facing, walking);
        for (const node of bodyNodes(sprite)) {
          node.rotation = p.rotation;
          node.position.set(p.x, FEET + p.y);
        }
        this.poseBody(unitId, sprite, { pose: p.pose }, -p.y);
      };
      await this.during(beat.holdMs, skip, lay);
      lay(1);
      fell = true;
    } else if (beat.beat === "trap") {
      // 陷阱夾住（6N-4）：夾子合上那一刻白閃、身體一縮、膝蓋彎，腳定在那一格；停頓結束才跳數字與定身圖示
      const draw = this.unitDrawOf.get(unitId);
      const creature = draw !== undefined && creatureOf(draw) !== null;
      const skeleton = draw !== undefined && hasSkeleton(draw);
      await this.during(beat.holdMs, skip, (t) => {
        if (sprite.destroyed) return;
        if (creature) this.poseBody(unitId, sprite, { creature: creatureReact("trapped", t) });
        else if (skeleton) {
          const f = reactFrame("trapped", t);
          this.poseBody(unitId, sprite, { pose: f.pose, flash: f.flash });
          const back = knockOffset(facing, f.back * DOLL_PX);
          for (const node of bodyNodes(sprite)) node.position.set(back.x, FEET + back.y);
        }
      });
      this.restBody(unitId, sprite);
    } else {
      await this.during(beat.holdMs, skip, () => undefined);
    }
    if (!skip()) this.playFeedback(beat.feedback, beat.feedbackMs);
    return fell;
  }

  /** 等 `ms` 毫秒（跟著畫面的 ticker），每幀呼叫 `step(t)`；`skip()` 為真時立刻結束。 */
  private during(ms: number, skip: () => boolean, step: (t: number) => void): Promise<void> {
    if (ms <= 0 || skip()) return Promise.resolve();
    return new Promise((resolve) => {
      let elapsed = 0;
      let done = false;
      const finish = () => {
        if (done) return;
        done = true;
        this.app.ticker?.remove(tick);
        resolve();
      };
      const tick = (ticker: Ticker) => {
        elapsed += ticker.deltaMS;
        if (skip() || elapsed >= ms) {
          finish();
          return;
        }
        this.guard(() => step(elapsed / ms));
      };
      this.app.ticker.add(tick);
      window.setTimeout(finish, ms + 300); // 分頁在背景時 ticker 會停
    });
  }

  /** 小人身體目前的貼圖釘在 LRU（owner ＝ 單位 ID；6R-F）。 */
  private holdBody(unitId: string, sprite: Container): void {
    const body = bodyNodes(sprite).find((n) => n.label === BODY_LABEL);
    this.art.holdFor(unitId, body?.texture ?? null);
  }

  /** 轉身：用新的朝向重建小人，放在原位與原圖層（重畫場景時再以 `view` 為準）。 */
  private turn(unitId: string, old: Container, facing: Facing): Container {
    const draw = this.unitDrawOf.get(unitId);
    if (draw === undefined || old.destroyed) return old;
    const next = { ...draw, facing };
    const fresh = buildUnitSprite(this.art, this.pulses, next);
    this.scaleUnitMarks(fresh); // 6F-9、6F-11
    this.holdBody(unitId, fresh); // 6R-F：兩次重畫之間新畫的朝向也要釘住，不然會被淘汰銷毀
    fresh.position.copyFrom(old.position);
    const parent = old.parent;
    if (parent !== null) parent.addChildAt(fresh, parent.getChildIndex(old));
    old.destroy({ children: true });
    this.unitSprites.set(unitId, fresh);
    this.unitDrawOf.set(unitId, next);
    return fresh;
  }

  /** 鏡頭跟著 `p`（戰場像素位置）；`null` ＝ 回到原位。偏移平滑地追上目標。 */
  private follow(p: { x: number; y: number } | null): void {
    const model = this.model;
    if (!this.ready || model === null) return;
    const target = p === null ? { x: 0, y: 0 } : cameraNudge(p, { width: model.width * T, height: model.height * T });
    this.cam.tx = target.x;
    this.cam.ty = target.y;
    if (this.camTick !== null) return;
    const tick = (ticker: Ticker) => {
      const cam = this.cam;
      const k = 1 - Math.exp(-ticker.deltaMS / 140);
      cam.x += (cam.tx - cam.x) * k;
      cam.y += (cam.ty - cam.y) * k;
      const settled = Math.abs(cam.tx - cam.x) < 0.05 && Math.abs(cam.ty - cam.y) < 0.05;
      if (settled) {
        cam.x = cam.tx;
        cam.y = cam.ty;
      }
      this.world.x = cam.x;
      this.world.y = this.worldBaseY + cam.y;
      if (settled && cam.tx === 0 && cam.ty === 0) {
        this.app.ticker?.remove(tick);
        this.camTick = null;
      }
    };
    this.camTick = tick;
    this.app.ticker.add(tick);
  }

  private tween(
    sprite: Container,
    from: { x: number; y: number },
    to: { x: number; y: number },
    durationMs: number,
    skip: () => boolean,
    style: MoveStyle,
    onProgress?: (t: number) => void,
    ease: (t: number) => number = (t) => t,
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
          onProgress?.(t < 0.5 ? 0 : 1);
          sprite.position.set(t < 0.5 ? from.x : to.x, t < 0.5 ? from.y : to.y);
          sprite.alpha = Math.abs(t - 0.5) * 2;
          return;
        }
        const p = lerpPos(from, to, ease(t));
        onProgress?.(t);
        sprite.position.set(p.x, p.y);
      };
      const finish = () => {
        if (done) return;
        done = true;
        this.app.ticker?.remove(tick);
        if (!sprite.destroyed) {
          onProgress?.(1);
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
    // 6H-1：傷害數字照實際時間走（停頓、最後一擊放慢時照常速彈出）
    const now = this.realClock;
    // 6F-6：同一格的字先量好高度，照實際高度錯開往上堆；這一格前幾步的字還沒播完時接在上面（`floatStack.ts`）
    const labels = items.map((item) => (item.kind === "line" ? null : this.floatLabel(item)));
    const groups = new Map<string, number[]>();
    items.forEach((item, i) => {
      if (item.kind === "line") return;
      const k = `${item.pos.x},${item.pos.y}`;
      groups.set(k, [...(groups.get(k) ?? []), i]);
    });
    const offsets = new Map<number, FloatSpot>();
    for (const [k, idx] of [...groups.entries()].sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))) {
      const heights = idx.map((i) => labels[i]?.restH ?? 0);
      const first = items[idx[0] ?? 0];
      // 6F-10b：頭頂上方放不下時這一格整疊一起往下推（`FloatStack.placeGroup`），推回畫面內的字也照同一格的規則錯開
      const room = first === undefined || first.kind === "line" ? Number.POSITIVE_INFINITY : this.floatRoom(first.pos);
      const placed = this.floatStack.placeGroup(k, now, now + durationMs, heights, room);
      const firstH = heights[0] ?? 0;
      // 6F-11：停住時整組在戰場上緣以內的，飄到最高也不飄出去（`capRise`；最上排的「−7」）
      const fullRise = Math.max(...idx.map((i) => labels[i]?.riseMax ?? 0));
      const riseMax = first === undefined || first.kind === "line" ? fullRise : capRise(fullRise, this.groupRestTop(first.pos, firstH, heights, placed.offsets) + placed.shiftAt(now), this.mapTopY());      const waitMs = Math.min(placed.waitMs, durationMs * 0.4);
      idx.forEach((i, order) => offsets.set(i, { offset: placed.offsets[order] ?? 0, firstH, shiftAt: placed.shiftAt, waitMs, order, riseMax }));
    }
    const effects: Effect[] = [];
    items.forEach((item, i) => {
      const label = labels[i];
      const at = offsets.get(i);
      if (item.kind === "line") effects.push(this.lineEffect(item.from, item.to, now, durationMs));
      else if (label != null && at !== undefined) effects.push(...this.makeEffect(item, label, at, now, durationMs));
    });
    this.launch(effects.map((e) => ({ ...e, clock: "real" as const })));
  }

  /** 浮動字的字（還沒放位置）：停住時的高度、寬度、飄的最大距離。 */
  private floatLabel(item: Exclude<FeedbackItem, { kind: "line" }>): FloatLabel {
    const isStatus = item.kind === "status";
    const text = isStatus ? `＋${item.text}` : item.text;
    const color = isStatus ? STATUS_COLOR : FLOAT_COLORS[item.tone];
    const big = item.kind === "float" && item.big;
    const t = label(text, floatFontSize(big), color, true);
    t.anchor.set(0.5);
    t.style.stroke = { color: 0x000000, width: 4 };
    // 6N-6：放大字（暴擊）停住時 ＝ 一般字 1.3 倍，整串不超過格寬 1.8 倍
    const fit = floatFit(t.width, T, big);
    const rest = fit * (big ? BIG_REST : 1);
    return { t, big, isStatus, fit, restH: t.height * rest, restW: t.width * rest, riseMax: floatFrame(1, big).rise };
  }

  /** 站在 `p` 的異形單位 ID；沒有為 `null`。 */
  private creatureAt(p: Pos): string | null {
    for (const [id, u] of this.unitDrawOf) if (u.x === p.x && u.y === p.y && creatureOf(u) !== null) return id;
    return null;
  }

  /**
   * 異形受擊（6M-2 的片段，6M-3 接上戰場）：`ms` 毫秒內播「受擊」片段——往後彈、仰、白閃只閃剪影（貼圖裡疊白色剪影）。
   * 每幀照單位 ID 找目前的小人（重畫場景後換成新的節點也跟得上）；結束時回到站好的貼圖。
   */
  private creatureHit(unitId: string, startMs: number, ms: number): Effect {
    const node = new Container();
    let held = false;
    const current = () => {
      const s = this.unitSprites.get(unitId);
      return s === undefined || s.destroyed ? null : s;
    };
    return {
      node,
      startMs,
      endMs: startMs + ms,
      motion: "body",
      update: (t) => {
        const s = current();
        if (s === null) return;
        if (!held) {
          held = true;
          this.idle.hold(unitId, s);
        }
        const pose = quantizeCreaturePose(CREATURE_CLIPS.hit.pose(t));
        this.poseBody(unitId, s, { creature: pose });
      },
      end: () => {
        const s = current();
        if (s !== null) this.restBody(unitId, s);
        if (held) this.idle.release(unitId);
        held = false;
      },
    };
  }

  /** 站在 `p`、有紙娃娃骨架、沒有倒地的人形單位 ID；沒有為 `null`。 */
  private dollAt(p: Pos): string | null {
    for (const [id, u] of this.unitDrawOf) if (u.x === p.x && u.y === p.y && hasSkeleton(u) && !isProne(u)) return id;
    return null;
  }

  /**
   * 人形受擊（6M-4）：`ms` 毫秒內播「受擊」片段——仰一下、往後彈、白閃只閃剪影（不含地上的影子、不整格變白）。
   * 和異形一樣每幀照單位 ID 找目前的小人；結束時回到站好的貼圖。
   */
  private dollHit(unitId: string, startMs: number, ms: number): Effect {
    let held = false;
    const current = () => {
      const s = this.unitSprites.get(unitId);
      return s === undefined || s.destroyed ? null : s;
    };
    return {
      node: new Container(),
      startMs,
      endMs: startMs + ms,
      motion: "body",
      update: (t) => {
        const s = current();
        if (s === null) return;
        if (!held) {
          held = true;
          this.idle.hold(unitId, s);
        }
        const h = humanHit(t);
        this.poseBody(unitId, s, { pose: h.pose, flash: h.flash });
        const off = knockOffset(this.unitDrawOf.get(unitId)?.facing ?? "south", h.knock * DOLL_PX);
        for (const node of bodyNodes(s)) node.position.set(off.x, FEET + off.y);
      },
      end: () => {
        const s = current();
        if (s !== null) this.restBody(unitId, s);
        if (held) this.idle.release(unitId);
        held = false;
      },
    };
  }

  /** 站在 `p`、受擊時疊白色剪影閃白的單位（形態、召喚物、倒地的人；6C-8）ID；沒有為 `null`。 */
  private overlayFlashAt(p: Pos): string | null {
    for (const [id, u] of this.unitDrawOf) if (u.x === p.x && u.y === p.y && overlayFlashKind(u) !== null) return id;
    return null;
  }

  /**
   * 形態、召喚物、倒地的人受擊（6C-8）：沒有骨架，不換姿勢，只在小人上疊一層白色剪影（同一張圖不含地上影子、轉白），
   * 不透明度照人形受擊片段的白閃（開頭 0.85、播到 1/4 消失）；不畫整片白圓、不整格變白。結束時拿掉。
   */
  private overlayHit(unitId: string, startMs: number, ms: number): Effect {
    const current = () => {
      const s = this.unitSprites.get(unitId);
      return s === undefined || s.destroyed ? null : s;
    };
    const owner = this.art.uniqueOwner(`flash:${unitId}`); // 6R-F：白閃疊層的貼圖也釘住
    return {
      node: new Container(),
      startMs,
      endMs: startMs + ms,
      motion: "body",
      update: (t) => {
        const s = current();
        const draw = this.unitDrawOf.get(unitId);
        if (s === null || draw === undefined) return;
        const body = bodyNodes(s).find((n) => n.label === BODY_LABEL);
        const tex = flashTexture(this.art, draw);
        if (body === undefined || tex === null) return;
        this.art.holdFor(owner, tex);
        overlayFlash(body, tex, humanHit(t).flash);
      },
      end: () => {
        const s = current();
        if (s !== null) clearFlash(s);
        this.art.holdFor(owner, null);
      },
    };
  }

  /** 把一組效果放進效果圖層並啟動效果迴圈。 */
  private effectLayer(id: EffectLayer): Container {
    return id === "groundFx" ? this.groundFx : id === "floatRings" ? this.floatRings : this.effects;
  }

  private launch(effects: readonly Effect[]): void {
    for (const e of reduceEffects(effects, this.reduced)) {
      // 6R-F：減少動態時閃白、震動、變暗、弧光殘影火花不播，身體片段直接跳到結果
      this.effectLayer(effectLayerOf(e)).addChild(e.node);
      this.effectList.push(e);
    }
    this.ensureEffectTick();
  }

  /**
   * 播放一步的技能特效（Phase 3-12）：蓄力、飛行物或光束、命中爆發、受擊閃白與震動。不等待結束；
   * 描述內的時間已依播放速度縮放，`impactMs` 是命中後爆發的時間。`shake` 為假時不震動（版面設定）。
   */
  playVfx(raw: StepVfx, impactMs: number, shake: boolean, origins: ReadonlyMap<number, { x: number; y: number }> = new Map()): void {
    if (!this.ready || impactMs <= 0) return;
    const vfx = reduceVfx(raw, this.reduced); // 6R-F：減少動態時沒有停頓、沒有技能變體的特效層
    const now = this.effectClock;
    const effects: Effect[] = [];
    const auraHits = vfx.casts.some((c) => c.kind === "aura");
    const at = (p: Pos) => this.center(p);
    vfx.casts.forEach((cast, i) => {
      // 6N-1：飛行物、光束、扇形從出招那一刻的作用端（杖頭、劍尖、槍口、弓弦）發出，不從格子中心
      const o = origins.get(i);
      const from = o !== undefined && (cast.kind === "projectile" || cast.kind === "beam" || cast.kind === "cone") ? o : null;
      const atCast = from === null ? at : (p: Pos) => (p.x === cast.from.x && p.y === cast.from.y ? from : at(p));
      effects.push(...castEffects(cast, now, impactMs, atCast));
    });
    // 6N-4：有反應資料時，受擊者的身體由反應決定（受擊、重擊、格擋、閃避、倒下；`reactEffects.ts`），在各自那一段的命中點開始
    const reactions = vfx.reactions;
    const scale = impactMs / VFX_TIMING.impact;
    if (reactions !== undefined) {
      // 6N-5：復活（從倒地站起、一圈綠光）在 resultEffects.ts
      for (const r of reactions) effects.push(...(r.kind === "rise" ? riseEffects(this.resultHost, r, now + r.atMs, scale) : reactEffects(this.reactHost, r, now + r.atMs, scale)));
    }
    // 6N-5：特殊結果（暴擊閃白、擊殺震動、大火花與彈開、多一層殘影、Boss 四周變暗）與命中時的停頓
    const stage = this.app.stage;
    effects.push(...specialEffects(this.resultHost, vfx, { now, impactMs, scale, shake, apply: (x, y) => stage.position.set(x, y) }));
    for (const s of vfx.stops ?? []) addFreeze(this.freezes, now + s.atMs, s.ms, this.effectClock);
    for (const hit of vfx.hits) {
      // 異形（6M-3）：受擊只閃角色的剪影（不畫整片白圓），身體往後彈一下
      // 有骨架的人形（6M-4，美術 PM 檢查）：同樣只閃剪影、往後彈；形態、召喚物、倒地的人（6C-8）疊白色剪影閃白、不畫白圓
      const foe = this.creatureAt(hit.pos);
      const doll = foe === null ? this.dollAt(hit.pos) : null;
      const flat = foe === null && doll === null ? this.overlayFlashAt(hit.pos) : null;
      effects.push(...hitEffects(hit, now, impactMs, auraHits, at, foe === null && doll === null && flat === null));
      if (reactions !== undefined) continue;
      if (foe !== null) effects.push(this.creatureHit(foe, now + hit.atMs, Math.max(160, impactMs)));
      if (doll !== null) effects.push(this.dollHit(doll, now + hit.atMs, Math.max(160, impactMs)));
      if (flat !== null) effects.push(this.overlayHit(flat, now + hit.atMs, Math.max(160, impactMs)));
    }
    for (const blast of vfx.blasts) effects.push(blastEffect(blast, now, impactMs, at));
    // 6H-1：鏡頭微震只在重擊、爆炸、Boss 大招（`battle/impact.ts`）；版面設定關掉、減少動態時不震
    const quake = shake ? impactShakeEffect(vfx.shakes ?? [], now, (x, y) => stage.position.set(x / this.scale, y / this.scale)) : null; // 幅度是畫面像素：場景座標要除以縮放
    if (quake !== null) effects.push(quake);
    // 6H-1：最後一擊放慢（效果時鐘在命中點前後以 0.4 倍走）；減少動態時 `reduceVfx` 已拿掉
    if (vfx.slow !== undefined) this.slows.push({ fromMs: now + vfx.slow.fromMs, toMs: now + vfx.slow.toMs, rampMs: vfx.slow.rampMs, rate: vfx.slow.rate });
    // 6H-1：減少動態時，重擊、爆炸改成目標身上的白閃加長
    // （倒下、復活的人不閃：減少動態時他們直接是結果的姿勢，白閃會把姿勢換回站著）
    const lying = new Set((reactions ?? []).filter((r) => r.kind === "down" || r.kind === "rise").map((r) => r.unitId));
    if (this.reduced) for (const s of vfx.shakes ?? []) if (s.kind !== "boss") for (const p of s.targets) this.steadyFlashAt(p, now + s.atMs, Math.max(60, Math.round(REDUCED_FLASH_MS * scale)), effects, lying);
    this.launch(effects);
  }

  /**
   * 減少動態時的白閃（6H-1）：不換姿勢、不位移，只把目標的剪影閃白後淡掉（`ms` 已縮放）。
   * 人形、異形換成帶白閃的身體貼圖；形態、召喚物、倒地的人疊白色剪影。效果沒有動態標記，減少動態時照播。
   */
  private steadyFlashAt(p: Pos, startMs: number, ms: number, out: Effect[], skip: ReadonlySet<string>): void {
    const unitId = this.creatureAt(p) ?? this.dollAt(p) ?? this.overlayFlashAt(p);
    if (unitId === null || skip.has(unitId)) return;
    const current = () => {
      const s = this.unitSprites.get(unitId);
      return s === undefined || s.destroyed ? null : s;
    };
    const owner = this.art.uniqueOwner(`flash:${unitId}`);
    const kind = this.creatureAt(p) !== null ? "creature" : this.dollAt(p) !== null ? "doll" : "overlay";
    out.push({
      node: new Container(),
      startMs,
      endMs: startMs + ms,
      update: (t) => {
        const s = current();
        const draw = this.unitDrawOf.get(unitId);
        if (s === null || draw === undefined) return;
        const flash = 0.85 * (1 - t);
        if (kind === "doll") this.poseBody(unitId, s, { flash: quantizeFlash(flash) });
        else if (kind === "creature") this.poseBody(unitId, s, { creature: quantizeCreaturePose({ flash }) });
        else {
          const body = bodyNodes(s).find((n) => n.label === BODY_LABEL);
          const tex = flashTexture(this.art, draw);
          if (body === undefined || tex === null) return;
          this.art.holdFor(owner, tex);
          overlayFlash(body, tex, flash);
        }
      },
      end: () => {
        const s = current();
        if (s === null) return;
        if (kind === "overlay") clearFlash(s);
        else this.restBody(unitId, s);
        this.art.holdFor(owner, null);
      },
    });
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
      effects.push(shakeEffect(LIFT_SHAKE_PX, now, durationMs * 0.6, (x, y) => stage.position.set(x / this.scale, y / this.scale))); // 6H-1：降到 1 px
    }
    this.launch(effects);
  }

  private makeEffect(item: Exclude<FeedbackItem, { kind: "line" }>, l: FloatLabel, at: FloatSpot, now: number, durationMs: number): Effect[] {
    const c = this.center(item.pos);
    // 同一組的字照順序延後出現（彈一下），但一起往上飄（6F-6 `groupRise`：後出現的字不會被先出現的追上）
    const delayFrac = Math.min(0.6, at.order * 0.15);
    const delay = at.waitMs + delayFrac * (durationMs - at.waitMs);
    const { t, big, isStatus, fit } = l;
    const node = new Container();
    node.addChild(t);
    // 6N-7：浮動字從單位頭頂往上冒（`unitTopY`，同 6N-4／6C-8b）；6N-8：狀態字（＋狀態）也一樣，光環另外畫
    // 6F-6：同一格的字照實際高度錯開（`at.offset`）；頭頂上方放不下時整格一起往下推（6F-10b `FloatStack.placeGroup`）
    // 6F-10b：位移從這一組第一個字貼頭頂時的中心算（`at.firstH`），頭頂放不下時整格一起往下推（`at.shiftAt`）
    const baseY = floatBaseY(c.y, this.floatTopY(item.pos), at.firstH, 0) - at.offset;
    const x0 = c.x + (isStatus ? T * 0.12 : 0);
    // 6F-10：每一幀照當下的大小（彈一下時比停住時大）把整個字夾在戰場裡，四個邊都一樣（`clampFloatCenter`）
    const put = (y: number, scale: number) => this.placeFloat(node, t, x0, y + at.shiftAt(this.realClock), scale);
    put(baseY, (big ? BIG_REST : 1) * fit);
    node.alpha = 0;
    const rise = (p: number) => (this.reduced ? 0 : groupRise(p, delayFrac, at.riseMax));
    if (!isStatus) {
      return [{
        node,
        startMs: now + delay,
        endMs: now + durationMs,
        update: (p) => {
          // 6N-10：彈一下再淡出（暴擊放大）；減少動態時直接顯示
          const f = floatFrame(p, big, this.reduced);
          node.alpha = f.alpha;
          put(baseY - rise(p), f.scale * fit);
        },
      }];
    }
    // 狀態：格子先閃一圈光環（6N-8 拆成自己的節點，位置、動態照 6N-7 以前：中心在格中心、跟著字的節奏往上飄一點）
    const ringY = c.y - T * 0.3 - at.order * 22;
    const ring = new Graphics().circle(0, T * 0.3, T * 0.4).stroke({ width: 3, color: STATUS_COLOR });
    ring.position.set(this.clampFloatX(c.x + T * 0.12, (t.width * fit) / 2), ringY);
    ring.alpha = 0;
    // 6F-7：光環放進浮動字下面那一層（`layer: "under"`），不會蓋住同一格前一步的「暴擊 −9」
    return [
      {
        node: ring,
        startMs: now + delay,
        endMs: now + durationMs,
        layer: "under",
        update: (p) => {
          const f = floatFrame(p, big, this.reduced);
          ring.alpha = f.alpha;
          ring.position.y = ringY - f.rise;
          ring.scale.set(f.scale * fit);
        },
      },
      {
        node,
        startMs: now + delay,
        endMs: now + durationMs,
        update: (p) => {
          const f = floatFrame(p, big, this.reduced);
          node.alpha = f.alpha;
          put(baseY - rise(p), f.scale * fit);
        },
      },
    ];
  }

  /** 6F-11：一組浮動字停住時（還沒往下推）最上面那個字的上緣 y（世界座標，和 `makeEffect` 的 `baseY` 同一個算法）。 */
  private groupRestTop(p: Pos, firstH: number, heights: readonly number[], offsets: readonly number[]): number {
    const last = heights.length - 1;
    return floatBaseY(this.center(p).y, this.floatTopY(p), firstH, 0) - (offsets[last] ?? 0) - (heights[last] ?? 0) / 2;
  }

  /** 6F-11：戰場（地圖）上緣的 y（世界座標，扣掉鏡頭偏移；畫布上緣再往上是頭頂預留）。 */
  private mapTopY(): number {
    return -this.cam.y;
  }

  /** 浮動字所在格的單位頂端（`unitTopY`）；那一格沒有人（已經移走）時用標準人形的頭頂。 */
  private floatTopY(p: Pos): number {
    const u = this.model?.units.find((x) => x.x === p.x && x.y === p.y);
    return u === undefined ? HUMAN_TOP_Y : unitTopY(u);
  }

  /**
   * 6F-10b：`p` 那一格頭頂上方給浮動字的空間（從頭頂線往上算）：字停住時的上緣最高到戰場上緣（`floatBounds`）
   * 再往下留飄的距離（`FLOAT_RISE_MAX`）和邊緣空隙（`FLOAT_EDGE_PAD`），飄到最高也不會被夾回來、壓到下面的字。
   * 6F-11：再往下 `FLOAT_TOP_SHIFT_PX`（畫面 px），最上排的字留在戰場上緣以內。
   */
  private floatRoom(p: Pos): number {
    const line = this.center(p).y + this.floatTopY(p) - FLOAT_HEAD_GAP;
    return line - (this.floatBounds().top + FLOAT_RISE_MAX + FLOAT_EDGE_PAD + floatTopShift(this.scale));
  }

  /**
   * 浮動字的畫布可見範圍（世界座標，扣掉鏡頭偏移）：左右是地圖兩緣，上面是畫布上緣（含頭頂預留），下面是地圖下緣。
   */
  private floatBounds(): FloatBounds {
    const w = (this.model?.width ?? 0) * T;
    const h = (this.model?.height ?? 0) * T;
    return { left: -this.cam.x, top: -this.worldBaseY - this.cam.y, right: w - this.cam.x, bottom: h - this.cam.y };
  }

  /** 6F-10：把浮動字放在 (x, y)、縮放 `scale`，整個字（含黑邊）往內推到戰場裡（`clampFloatCenter`）。 */
  private placeFloat(node: Container, t: Text, x: number, y: number, scale: number): void {
    node.scale.set(scale);
    const p = clampFloatCenter(x, y, (t.width * scale) / 2, (t.height * scale) / 2, this.floatBounds());
    node.position.set(p.x, p.y);
  }

  /** 浮動文字的水平位置往內推，不超出地圖左右邊緣（UI-T1：邊緣格的「跑步 移動＋N」被切掉）。 */
  private clampFloatX(x: number, half: number): number {
    const width = (this.model?.width ?? 0) * T;
    if (width <= 0 || half * 2 >= width) return x;
    return Math.min(Math.max(x, half + 2), width - half - 2);
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
      this.effectClock = advanceClock(this.effectClock, ticker.deltaMS, this.freezes, this.slows);
      this.realClock += ticker.deltaMS;
      if (this.slows.length > 0) this.slows = this.slows.filter((s) => s.toMs > this.effectClock);
      const alive: Effect[] = [];
      this.guard(() => {
        for (const e of this.effectList) {
          const clock = e.clock === "real" ? this.realClock : this.effectClock; // 6H-1：傷害數字照實際時間
          if (clock >= e.endMs) {
            e.end?.();
            e.node.destroy({ children: true });
            continue;
          }
          if (clock >= e.startMs) e.update((clock - e.startMs) / (e.endMs - e.startMs));
          alive.push(e);
        }
      });
      this.effectList = alive;
      if (alive.length === 0) {
        this.freezes = [];
        this.slows = [];
        this.app.ticker?.remove(tick);
        this.effectTick = null;
      }
    };
    this.effectTick = tick;
    this.app.ticker.add(tick);
  }
}
