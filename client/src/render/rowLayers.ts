// 由北到南一排一排的圖層（Phase 3-19 整格抬高）：每排依序畫地形與崖面、表面裝飾、物件、陷阱、單位、
// 高度徽章、上層霧、HUD，讓南邊的高格自然蓋住北邊一排。6F-10 曾把高度徽章移到同一排的單位之上；6R-1c 改回單位之下
// （跳躍飛過那一格時人物蓋過「▲N」）。另外記下每個「跟著格子抬高」的節點，升降動畫時一起移動。
import { Container, RenderLayer } from "pixi.js";
import { clearLayer } from "./labels";
import type { Pos } from "../api/types";
import { tileLift } from "../battle/elevation";
import { posKey } from "../battle/geometry";
import { BOMB_BADGE_LABEL, BOSS_RING_FRONT_LABEL, CHARGE_BADGE_LABEL, DOWNED_BADGE_LABEL, FACING_ARROW_LABEL, HIDDEN_HP_LABEL, HP_BAR_LABEL, INFUSED_BADGE_LABEL, SOUTH_ARROW_LABEL, STATUS_ROW_LABEL, SUMMON_BADGE_LABEL } from "./minMark";

export interface RowLayer {
  root: Container;
  ground: Container;
  deco: Container;
  /**
   * 6F-21：北邊一排的單位伸進這一排、要畫在這一排地面之上的東西（移到 HP 條下面的朝南三角形 `SOUTH_ARROW_LABEL`、
   * 頭目的環與精英金菱形 `BOSS_RING_FRONT_LABEL`、HID-1c 的「？」徽章 `HIDDEN_HP_LABEL`）。
   * 在表面裝飾之上、物件與單位之下（這一排的人、物件照常蓋過去）。
   */
  under: RenderLayer;
  objects: Container;
  /**
   * 高度徽章「▲N」：在同一排的單位之下（6R-1c，美術 PM 11-06：人物站著或飛過那一格都蓋過標籤；
   * 6F-18 起有人站著的格子本來就不畫）。物件、陷阱之上。
   */
  badges: Container;
  traps: Container;
  /** HID-1b（美術 PM 11-07）：攻擊紅框（`Highlights.attacks`）：在單位之下、物件與高度徽章之上（HighlightLayer.drawAttackFrames）。 */
  frames: Container;
  /** RG-3：瞄準線照所在的排切段放這裡（攻擊紅框那一級：紅框之上、單位之下；`RgMarkLayer`）。和紅框分開，`clearFrames` 不清。 */
  aims: Container;
  units: Container;
  /** 擋視線表面（煙霧、黑暗）的上層霧：在單位之上（Phase 3-36b）。 */
  veil: Container;
  /**
   * 6F-13：單位身上的炸彈、蓄力、灌注徽章（`UNIT_MARK_LABELS`）改在這一層畫：在同一排的高度徽章「▲N」之上（美術 PM 決定），
   * 仍在南邊一排之下（徽章避不開南邊單位的臉時，畫在那個單位的下層）。徽章節點照舊是單位圖層的子節點（位置、透明度跟著單位），
   * 只有畫的順序由這一層決定（Pixi `RenderLayer`）。
   * HID-1b（美術 PM 11-07）：在上層霧之上（人物留在霧下），而且 HP 條、「？」、狀態列（`ROW_HUD_LABELS`）也在這一層。
   * HID-1c：「？」的圓底超出格子下緣，改掛南邊一排的 `under`（最南一排照舊在這一層；`RowStack.attachMarks`）。
   */
  marks: RenderLayer;
}

/** 改在 `RowLayer.marks` 畫的單位子節點（6F-13）。 */
export const UNIT_MARK_LABELS: readonly string[] = [BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, INFUSED_BADGE_LABEL];

/**
 * 6F-22：被南邊高台擋住時改在高台之上畫的 HUD（`RowStack.attachHud`）：HP 條（含護盾條）、狀態列（含「+N」膠囊）、
 * 朝向三角形（朝南移到 HP 條下面的那個照 6F-21b，不在這裡）、召喚物回合數、倒下徽章，以及炸彈、蓄力、灌注徽章（`UNIT_MARK_LABELS`）。
 */
export const HUD_LABELS: readonly string[] = [HP_BAR_LABEL, HIDDEN_HP_LABEL, STATUS_ROW_LABEL, FACING_ARROW_LABEL, SUMMON_BADGE_LABEL, DOWNED_BADGE_LABEL];

/**
 * HID-1b（美術 PM 11-07）：畫在上層霧之上的 HUD（`RowLayer.marks`）：HP 條、「？」、狀態列、召喚物回合數、倒下徽章。
 * 朝向三角形不在這裡：畫在身體之下的那一種要被身體蓋（`HUD_LABELS` 只管「被高台擋住」時）。
 */
export const ROW_HUD_LABELS: readonly string[] = HUD_LABELS.filter((l) => l !== FACING_ARROW_LABEL);

function makeRow(): RowLayer {
  const row: RowLayer = {
    root: new Container(),
    ground: new Container(),
    deco: new Container(),
    under: new RenderLayer(),
    objects: new Container(),
    badges: new Container(),
    traps: new Container(),
    frames: new Container(),
    aims: new Container(),
    units: new Container(),
    veil: new Container(),
    marks: new RenderLayer(),
  };
  row.root.addChild(row.ground, row.deco, row.under, row.objects, row.traps, row.badges, row.frames, row.aims, row.units, row.veil, row.marks);
  return row;
}

/** 跟著格子抬高的節點：`baseY` 是未抬高時的 y；`redraw` 給崖面這類會跟著抬高量改形狀的圖。 */
interface LiftNode {
  node: Container;
  baseY: number;
  redraw?: (lift: number) => void;
}

export class RowStack {
  readonly root = new Container();
  private rows: RowLayer[] = [];
  private readonly nodes = new Map<string, LiftNode[]>();

  /** 重建 `n` 排空圖層（舊的全部銷毀）。 */
  reset(n: number): void {
    for (const child of this.root.removeChildren()) child.destroy({ children: true });
    this.nodes.clear();
    this.rows = Array.from({ length: Math.max(0, n) }, makeRow);
    for (const r of this.rows) this.root.addChild(r.root);
  }

  /** 第 y 排；超出範圍時取最近的一排（不會發生在正常的模型上）。 */
  row(y: number): RowLayer {
    const i = Math.max(0, Math.min(this.rows.length - 1, y));
    return this.rows[i] as RowLayer;
  }

  /** HID-1b：清掉每一排的攻擊紅框。 */
  clearFrames(): void {
    for (const r of this.rows) clearLayer(r.frames);
  }

  /**
   * 6F-13：單位圖層 `sprite` 的徽章（`UNIT_MARK_LABELS`）改在它所在那一排的 `marks` 層畫；HID-1b：HP 條、「？」、狀態列（`ROW_HUD_LABELS`）也是。
   * 照單位圖層子節點的順序掛（徽章仍在 HP 條、狀態列之上）。`sprite` 要已經放進某一排的 `units`（走路途中換排時再呼叫一次）；不在任何一排時不動。
   */
  attachMarks(sprite: Container, top: RenderLayer | null = null): void {
    const i = this.rows.findIndex((r) => r.units === sprite.parent);
    if (i < 0) return;
    const row = this.rows[i] as RowLayer;
    // 6F-22：高台之上的 HUD 回到所在那一排（移動途中、重新判斷前；擋住時由 `attachHud` 再掛上去）
    const southUnder = this.rows[i + 1]?.under ?? null;
    for (const n of sprite.children) {
      if (n.label === HIDDEN_HP_LABEL) {
        // HID-1c：圓底超出格子下緣；掛南邊一排的 `under`，地面蓋不到、那排的人照舊蓋得過（最南一排沒有南邊，留在 `marks`）
        const layer = southUnder ?? row.marks;
        if (n.parentRenderLayer !== layer) layer.attach(n);
      } else if (ROW_HUD_LABELS.includes(n.label) || UNIT_MARK_LABELS.includes(n.label)) {
        if (n.parentRenderLayer !== row.marks) row.marks.attach(n);
      } else if (n.label === FACING_ARROW_LABEL) n.parentRenderLayer?.detach(n);
      else if (n.label === BOSS_RING_FRONT_LABEL) {
        // QK-9、HID-1c：伸進南邊一排的環、金菱形（最南一排沒有南邊，跟著單位畫）；走路換排、轉身重建時一起更新
        if (southUnder === null) n.parentRenderLayer?.detach(n);
        else if (n.parentRenderLayer !== southUnder) southUnder.attach(n);
      }
    }
    // 6F-21：朝南的三角形在南邊一排的地面之上（最南一排沒有人蓋它，照舊跟著單位畫）；
    // 6F-21b：南邊那格沒人站時改在 `top`（移動格、崖面之上；`southArrowPlace`）
    const south = southUnder === null ? null : (top ?? southUnder);
    for (const n of sprite.children) {
      if (n.label !== SOUTH_ARROW_LABEL || n.parentRenderLayer === south) continue;
      if (south === null) n.parentRenderLayer?.detach(n);
      else south.attach(n);
    }
  }

  /**
   * 6F-22（美術 PM 11-06）：單位被南邊高台擋住時，HUD（`HUD_LABELS` 與 `UNIT_MARK_LABELS`）改在 `hud` 畫
   * （高台與剪影虛線之上的全域層），身體照舊被擋。照單位圖層子節點的順序掛（徽章仍在 HP 條、狀態列之上）。
   * 要在 `attachMarks` 之後呼叫；`hud` ＝ `null`（沒被擋）時不動。節點照舊是單位圖層的子節點（位置、透明度跟著單位）。
   */
  attachHud(sprite: Container, hud: RenderLayer | null): void {
    if (hud === null) return;
    for (const n of sprite.children) {
      if ((HUD_LABELS.includes(n.label) || UNIT_MARK_LABELS.includes(n.label)) && n.parentRenderLayer !== hud) hud.attach(n);
    }
  }

  /** 把節點放在 (x, y − lift)，並登記成跟著格子 `p` 抬高。 */
  place(node: Container, p: Pos, x: number, y: number, lift: number, redraw?: (lift: number) => void): void {
    node.position.set(x, y - lift);
    const key = posKey(p);
    const list = this.nodes.get(key) ?? [];
    list.push({ node, baseY: y, redraw });
    this.nodes.set(key, list);
  }

  /** 升降動畫：把格子 `p` 上登記的節點移到抬高 `lift` 的位置。 */
  setLift(p: Pos, lift: number): void {
    for (const n of this.nodes.get(posKey(p)) ?? []) {
      if (n.node.destroyed) continue;
      n.node.y = n.baseY - lift;
      n.redraw?.(lift);
    }
  }
}

/** 6F-21b：朝南三角形畫在哪裡（`top` ＝ 移動格與崖面之上的全域層；`south` ＝ 南邊一排的 `under` 層）與往上移多少。 */
export interface SouthArrowPlace {
  layer: "top" | "south";
  /** 往上移的量（世界座標）：南邊那格比自己高時，跟著那格的高度移到那格的地面上。 */
  lift: number;
}

/**
 * 6F-21b（美術 PM 11-06 決定）：朝南三角形畫在移動格之上（蓋到移動格框線一小段可以）；南邊那格是高台時跟著那格的高度
 * 往上移到地面，且畫在崖面之上。南邊那格站著人（沒倒下）時照 6F-21：畫在南邊一排的地面之上、那個人之下
 * （有人站的格子本來就沒有移動格）。`ownH`／`southH` ＝ 自己與南邊那格的高度（南邊在地圖外時呼叫端不用這個）。
 */
export function southArrowPlace(ownH: number, southH: number, southOccupied: boolean): SouthArrowPlace {
  const lift = Math.max(0, tileLift(southH) - tileLift(ownH));
  return { layer: southOccupied ? "south" : "top", lift };
}
