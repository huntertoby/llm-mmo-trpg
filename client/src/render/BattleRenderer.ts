// PixiJS 繪製：照著 `DrawModel` 畫格子、物件、陷阱、單位與高亮；移動動畫只是過場，
// 播放完由呼叫端以新的 `view` 重畫（以 `view` 為準）。
// 縮放（Phase 3-8）：場景一律以「模型像素」（每格 TILE_SIZE）繪製；放大縮小只改畫布的解析度
// （devicePixelRatio × 縮放）與 CSS 大小，文字與線條因此保持清晰。滑鼠事件不經過 Pixi，
// 由 `BattleCanvas` 以 DOM 座標換算（`battle/stageLayout.ts` 的 `clientToTile`）。
// 高度「整格抬高」（Phase 3-19）：場景放在 `world`（往下移畫布上方預留的高度），由北到南一排一排畫
// （`RowStack`），格子上的所有東西都依 `tileLift` 往上移；位移只從 `battle/elevation.ts` 來。
// R1e：類別按職責拆到 `render/battle/`（純搬移）：共用狀態 `rendererBase`、地形 `terrainLayer`、高亮 `highlightLayer`、
// 單位與 HUD `unitLayer`、浮動字 `feedbackLayer`、移動 `motionLayer`、技能片段 `skillLayer`、特效與受擊 `vfxLayer`；
// 這裡留下生命週期（初始化、銷毀、壞掉重建）、縮放、整場重畫 `draw` 與待機開關。
import { GlobalResourceRegistry, Graphics, UPDATE_PRIORITY } from "pixi.js";
import type { DrawModel } from "../battle/drawModel";
import { TILE_SIZE } from "../battle/geometry";
import { scaledSize } from "../battle/stageLayout";
import { stagePixels, topReserve } from "../battle/elevation";
import { HIGHLIGHT } from "../battle/glossary";
import { ArtTextures, liveSpriteTextures } from "./artTextures";
import { objectKinds } from "./artSpecs";
import { clearLayer } from "./labels";
import { EFFECT_LAYER_ORDER } from "./effectLayer";
import { mapClipRect } from "./mapClip";
import { isSubmerged } from "./submerged";
import { prefersReducedMotion, subscribeReducedMotion } from "../world/frameLoop";
import { devAnimFactor } from "../battle/playback";
import { objectLayerOf } from "./sceneryLayer";
import { VfxLayer } from "./battle/vfxLayer";
export type { DirectionMark, Highlights } from "./battle/highlightLayer";
export { FLAME_DIM, HEIGHT_BADGE_FONT } from "./battle/terrainLayer";

/** 環境動態跟著開發用的 `?anim=0.1` 放慢（6N-10，逐格驗收用；正式畫面 ＝ 1）。 */
const AMBIENT_SLOW = devAnimFactor(typeof window === "undefined" ? "" : window.location.search);

const T = TILE_SIZE;
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

export class BattleRenderer extends VfxLayer {
  constructor() {
    super();
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
    this.world.addChild(this.rows.root, this.marks, this.attackTop, this.arrowTop, this.ambient.root, this.silhouettes, this.hudTop, this.hover, this.headMarks, this.groundMask, ...EFFECT_LAYER_ORDER.map((id) => this.effectLayer(id)));
    // 6R-F（前端審查第 2 點）：銷毀貼圖前先看畫面上活著的 Sprite 還拿著哪些（安全網）
    this.art.setLiveProbe(() => liveSpriteTextures(stage));
    if (import.meta.env.DEV) (window as unknown as { __texStats?: () => ReturnType<ArtTextures["stats"]> }).__texStats = () => this.art.stats();
    // 6F-12：開發時讀目前的鏡頭偏移與震動位移（截圖找「震動中的那一幀」用；只讀）
    if (import.meta.env.DEV) (window as unknown as { __fieldShift?: () => { cam: { x: number; y: number }; shake: { x: number; y: number } } }).__fieldShift = () => ({ cam: { x: this.cam.x, y: this.cam.y }, shake: { x: stage.position.x, y: stage.position.y } });
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
    // OCL-1b（Q4）：外框跟著身體節點平移；在所有動畫（含效果迴圈）之後、算繪之前
    ticker.add(() => this.guard(() => this.tickOutlines()), this, UPDATE_PRIORITY.LOW + 1);
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
    this.rgDestroy();
    this.ready = false;
  }

  /** 自動算繪（取代 Pixi 預設的 `app.render`）：例外時標記壞掉並通知，不讓 ticker 停擺。 */
  private safeRender(): void {
    if (this.broken) return;
    this.guard(() => this.app.render());
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
    if (this.ready && this.model !== null) {
      this.applySize(this.model);
      this.rebuildOutlines(); // OCL-1a（Q2）：只重建外框貼圖，比例與遲滯不重算
      this.rgRescale(); // RG-3：準星、小盾、「？」的反向放大倍率跟著縮放
    }
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

  draw(model: DrawModel): void {
    this.model = model;
    if (!this.ready) return;
    this.applySize(model);
    this.rows.reset(model.height);
    clearLayer(this.silhouettes);
    this.silhouetteOf.clear();
    this.unitSprites.clear();
    this.facesOf.clear();
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
    this.drawPracticeScene(model); // PR-2c：測試模式的滑軌與方角水池（實戰沒有）
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
    this.drawExitSigns(model);
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
    this.drawRgTraces(model); // RG-3：可疑痕跡（陷阱層）
    this.drawLinks(model);
    for (const u of model.units) this.drawUnit(model, u);
    this.drawOcclusion(model); // OCL-1a：被大型前排擋住的外框＋6F-22 舊剪影（有新外框的不畫）
    this.reposeAloft(); // CB-3：留在空中的鳥重畫後換回飛行姿勢
    this.motion.drawUnits(model);
    this.drawVeils(model);
    this.drawMist(model);
    this.drawAttackFrames(); // HID-1b：紅框在該排單位之下，rows.reset 會清掉，要重畫
    this.drawRgOverlay(); // RG-3：瞄準線在每排 `aims`（rows.reset 會清掉）、準星與小盾跟著新的頭頂
    this.ambient.draw(this.ambientHost(), model);
    this.art.endFrame();
    this.resumeLifts(model);
    const waiters = this.drawWaiters.splice(0);
    for (const w of waiters) w();
  }

  /** 按住空白鍵暫時加速（6N-1）：畫布上所有動畫（片段、特效、走路、待機）的時間一起快 `rate` 倍。 */
  setBoost(rate: number): void {
    if (this.ready) this.app.ticker.speed = rate > 0 ? rate : 1;
  }

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
}
