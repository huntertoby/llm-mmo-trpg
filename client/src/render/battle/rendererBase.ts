// `BattleRenderer` 的共用狀態（R1e 自 `BattleRenderer.ts` 拆出，純搬移）：Pixi 圖層與場景節點、單位表、效果時鐘與效果迴圈、
// 鏡頭偏移、格子抬高後的座標（`origin`／`center`／`place`）、標記的最小尺寸。各層依序繼承：
// RendererBase → TerrainLayer → HighlightLayer → UnitLayer → OcclusionLayer（OCL-1a）→ FeedbackLayer → MotionLayer → SkillLayer → VfxLayer → BattleRenderer。
import { Application, Container, Graphics, RenderLayer, Sprite, type Ticker } from "pixi.js";
import type { Pos } from "../../api/types";
import type { DrawModel, UnitDraw } from "../../battle/drawModel";
import { TILE_SIZE } from "../../battle/geometry";
import { heightAt, liftedCenter, liftedOrigin, tileLift } from "../../battle/elevation";
import { advanceClock, type Freeze } from "../hitStop";
import { ArtTextures } from "../artTextures";
import type { Effect } from "../vfxEffects";
import type { SlowSpan } from "../../battle/impact";
import { RowStack } from "../rowLayers";
import { applyMarkScale, unitMarksOf } from "../minMark";
import type { Circle } from "../rowLayout";
import { Pulses } from "../unitSprite";
import { IdleMotion } from "../idleMotion";
import { AmbientLayer } from "../ambientLayer";
import { FloatStack } from "../floatStack";
import { effectLayerOf, type EffectLayer } from "../effectLayer";
import { MotionAnims } from "../motionAnims";
import { SceneryLayer } from "../sceneryLayer";
import { DOLL_SCALE } from "../paperdoll";
import { reduceEffects } from "../reducedMotion";

const T = TILE_SIZE;
/** 紙娃娃的虛擬像素 → 格子像素（52px 格縮放 DOLL_SCALE：QK-5 起 1.06）。 */
export const DOLL_PX = (T / 52) * DOLL_SCALE;
/** 一格進行中的升降動畫。 */
export interface LiftState {
  pos: Pos;
  /** 目前補間到的高度。 */
  h: number;
  to: number;
}

export abstract class RendererBase {
  protected readonly app = new Application();
  /** 整個場景（世界座標）；y ＝ 畫布上方預留的高度。震動只動 `stage`，不影響這個位移。 */
  protected readonly world = new Container();
  /** 由北到南的每一排：地形與崖面、表面裝飾、物件、高度徽章、高亮、陷阱、單位。 */
  protected readonly rows = new RowStack();
  /** 被南邊高格擋住的單位的虛線剪影（最上層）。 */
  protected readonly silhouettes = new Container();
  protected readonly silhouetteOf = new Map<string, Graphics>();
  /** OCL-1a：被大型前排擋住的單位的陣營色外框（也在 `silhouettes`；每次 `draw` 重建）。 */
  protected readonly outlineOf = new Map<string, Sprite>();
  /** OCL-1a：上一次有沒有畫外框（遲滯；**跨 `draw` 保留**，單位不在 `model.units` 時刪）。 */
  protected readonly outlineWas = new Map<string, boolean>();
  /** 6F-22：被南邊高台擋住的單位的 HUD（HP 條、狀態列、朝向三角形、徽章）：在剪影虛線之上（`RowStack.attachHud`）。 */
  protected readonly hudTop = new RenderLayer();
  /** 高亮（移動、預覽、目標框…）：畫在所有排之上，仍跟著所在格抬高，不被南邊的高格蓋住（3-18b）。 */
  protected readonly marks = new Container();
  /** HID-1b：被南邊高台、屋頂擋住的格子的攻擊紅框（看得到框；一般的框在該排 `RowLayer.frames`，單位之下）。在 `marks` 之上、`hudTop` 之下。 */
  protected readonly attackTop = new Container();
  /**
   * GB-4c：3×3 巨型頭目的部位格標示（括號、滑過亮起、紅×、背刺記號；`partTileMarks.ts`）。在 `attackTop` 之上：
   * 巨型頭目的目標紅框（`attackTop`）在標示層內排最底、不壓滑過框（美術 GB-4b 待決 1 裁定）。
   */
  protected readonly giantMarkTop = new Container();
  /** 目前的攻擊紅框格子（`rows.reset` 後 `draw` 重畫要用）。 */
  protected attackCells: readonly Pos[] = [];
  /** 6F-21b：朝南的三角形（南邊那格沒人站時）畫在移動格（`marks`）與崖面之上。 */
  protected readonly arrowTop = new RenderLayer();
  protected readonly pulses = new Pulses();
  /** 可燃小火苗的節點（3-38；每次重畫重建）與目前是否明顯。 */
  protected flameMarks: Container[] = [];
  protected flameOn = false;
  /** 浮動的事件「！」泡泡（6C-8；每次重設高亮時重建）與它們的基準高度。 */
  protected bobs: Array<{ node: Sprite; y: number }> = [];
  /** 情境物件提示的虛線圈（6C-8b，呼吸的不透明度）。 */
  protected breaths: Sprite[] = [];
  protected bobClock = 0;
  protected readonly hover = new Container();
  private readonly effects = new Container();
  /** 6F-6：地上的特效（範圍每格的爆發、光柱、扇形、目標格上的片段特效），用 `groundMask` 裁在地圖內。 */
  protected readonly groundFx = new Container();
  protected readonly groundMask = new Graphics();
  /** 6F-7：狀態光環（畫在浮動字下面，`effectLayer.ts`）。 */
  private readonly floatRings = new Container();
  protected effectList: Effect[] = [];
  /** 每一格還在播的浮動字（6F-6：新的一組接在舊的上面）。 */
  protected readonly floatStack = new FloatStack();
  protected effectClock = 0;
  /** 命中時的停頓（6N-5）：效果時鐘走到 `at` 時停住 `left` 毫秒（依時間排序）。 */
  protected freezes: Freeze[] = [];
  /** 最後一擊放慢（6H-1）：效果時鐘上的範圍（絕對時間）。 */
  protected slows: SlowSpan[] = [];
  /** 實際時間（6H-1：傷害數字照它走，停頓、放慢時照常速）。 */
  protected realClock = 0;
  private effectTick: ((ticker: Ticker) => void) | null = null;
  protected readonly unitSprites = new Map<string, Container>();
  /** 6F-13：每個單位這一輪的相鄰格的臉（轉身重建時沿用）。 */
  protected readonly facesOf = new Map<string, Circle[]>();
  /** 單位的繪製資料（走路轉彎時用新的朝向重建小人，6A-4d）。 */
  protected readonly unitDrawOf = new Map<string, UnitDraw>();
  /** 倒下的人（6N-4：只給倒下片段用；`unitSprites` 照舊不含倒下的人）。 */
  protected readonly downedSprites = new Map<string, Container>();
  protected readonly downedDrawOf = new Map<string, UnitDraw>();
  /** 移動中鏡頭稍微跟著角色（6A-4d）：目前的偏移與目標，加在戰場圖層上。 */
  protected readonly cam = { x: 0, y: 0, tx: 0, ty: 0 };
  protected camTick: ((ticker: Ticker) => void) | null = null;
  protected worldBaseY = 0;
  /** 程式繪製的地形、物件貼圖快取（Phase 3-16a）。 */
  protected readonly art = new ArtTextures();
  protected model: DrawModel | null = null;
  /**
   * 進行中的升降動畫：格子 → 目前補間到的高度與目標。播放結束時常會再重畫一次（同樣的結果），
   * 目標高度沒變的動畫在重畫後接著播；目標變了（又有新的地形變化）就以新畫面為準。
   */
  protected readonly lifting = new Map<string, LiftState>();
  /** 待機（6M-4）：站著的人呼吸、偶爾的小動作。 */
  protected readonly idle = new IdleMotion();
  /** 環境動態（6N-10）：營火、燈籠、草、酒旗、水波、薄霧。 */
  protected readonly ambient = new AmbientLayer();
  /** 減少動態（6N-10）：環境動態與待機不跑、傷害數字直接顯示。 */
  protected reduced = false;
  protected unsubscribeMotion: (() => void) | null = null;
  /** 實地地圖只畫的外觀：建築、門、室內外框、家具（6B-ART1）。 */
  protected readonly scenery = new SceneryLayer();
  /** 狀態動作與地表動畫（6N-9）。 */
  readonly motion = new MotionAnims();
  protected readonly drawWaiters: Array<() => void> = [];
  protected ready = false;
  protected destroyed = false;
  /** 算繪丟過例外或 WebGL context 一直沒恢復（UI-T1）；之後不再算繪，等 `BattleCanvas` 換新的繪製器。 */
  protected broken = false;
  protected lostTimer: number | null = null;
  /** 繪製器壞掉時呼叫一次（`BattleCanvas` 用來重建；銷毀後不再呼叫）。 */
  onBroken: (() => void) | null = null;
  /** 畫面上的縮放比例（1 ＝ 每格 TILE_SIZE 個 CSS 像素）。 */
  protected scale = 1;
  /** 這一輪畫的高度標記（6F-9：縮放改變時重設最小尺寸）。 */
  protected heightBadges: Container[] = [];

  /** 執行 ticker 上的一段工作；丟例外時視為繪製器壞掉。 */
  protected guard(work: () => void): void {
    if (this.broken) return;
    try {
      work();
    } catch (e) {
      this.fail(e);
    }
  }

  /** 繪製器壞掉：只通知一次（非同步，避免在 ticker 或 React 繪製中途換掉繪製器）。 */
  protected fail(reason: unknown): void {
    if (this.broken || this.destroyed) return;
    this.broken = true;
    console.error("[BattleRenderer] 戰場繪製失敗，重建繪製器", reason);
    window.setTimeout(() => this.onBroken?.(), 0);
  }

  /** 6F-9：一個標記節點依目前縮放保持最小尺寸（`minMark.ts`；沒登記過的節點不動）。 */
  protected scaleMark(node: Container | null): void {
    if (node === null || node.destroyed) return;
    applyMarkScale(node, this.scale, (window.devicePixelRatio || 1) * this.scale);
  }

  /** 6F-11：一個單位的回合數徽章與腳邊狀態列（徽章先，狀態列重排時會搬它）。 */
  protected scaleUnitMarks(unit: Container): void {
    for (const n of unitMarksOf(unit)) this.scaleMark(n);
  }

  /** 6F-9：縮放改變時，現有的高度標記與腳邊狀態列一起重設（場景不必重畫）。 */
  protected scaleMarks(): void {
    for (const s of this.unitSprites.values()) if (!s.destroyed) this.scaleUnitMarks(s);
    for (const n of this.heightBadges) this.scaleMark(n);
  }

  /** 格子的高度（地圖外 0）。 */
  protected heightOf(p: Pos): number {
    return this.model === null ? 0 : heightAt(this.model, p);
  }

  /** 抬高後格子頂面的左上角、中心（世界座標）。 */
  protected origin(p: Pos): { x: number; y: number } {
    return liftedOrigin(p, this.heightOf(p));
  }

  protected center(p: Pos): { x: number; y: number } {
    return liftedCenter(p, this.heightOf(p));
  }

  /** 把節點放到格子 `p`（`x`、`y` 是未抬高的世界座標），跟著格子抬高。 */
  protected place(node: Container, p: Pos, x: number, y: number): void {
    this.rows.place(node, p, x, y, tileLift(this.heightOf(p)));
  }

  /** 把一組效果放進效果圖層並啟動效果迴圈。 */
  protected effectLayer(id: EffectLayer): Container {
    return id === "groundFx" ? this.groundFx : id === "floatRings" ? this.floatRings : this.effects;
  }

  protected launch(effects: readonly Effect[]): void {
    for (const e of reduceEffects(effects, this.reduced)) {
      // 6R-F：減少動態時閃白、震動、變暗、弧光殘影火花不播，身體片段直接跳到結果
      this.effectLayer(effectLayerOf(e)).addChild(e.node);
      this.effectList.push(e);
    }
    this.ensureEffectTick();
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
