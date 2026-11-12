// OCL-1a：被遮擋剪影外框的圖層（`docs/phases/PhaseOCL-1計畫.md`）。全部單位畫完後（`BattleRenderer.draw`）呼叫 `drawOcclusion`：
// 照畫的順序收集擺位 → `planOcclusion`（過濾、大型前排、比例、遲滯）→ 要畫的做成外框 Sprite 放進 `silhouettes`
// （在所有排與排內 HUD 之上、`hudTop`／`hover`／特效之下）→ 6F-22 舊剪影只畫「被地形擋、而且沒有新外框」的（D5）。
// 縮放改變（`setScale`）只重建外框貼圖（`rebuildOutlines`），比例與遲滯不重算（Q2）。
// OCL-1b（播放）：片段播放中沿用片段開始前的結果（不重算）；移動結束、出招前轉向、出招列結束時 `refreshOcclusion` 重算
// （擺位一律用「站好」的身體位置，所以片段中途重算也等於片段開始前的結果）。外框每格跟著身體節點平移、旋轉時藏起來（Q4，
// `tickOutlines`）；移動的人自己的外框藏起來、別人的沿用到移動結束（Q5）；受擊閃白只動 `tint`／`alpha`（D4、Q6，`flashOutline`）。
import { Container, Sprite } from "pixi.js";
import type { DrawModel, UnitDraw } from "../../battle/drawModel";
import { flashAlpha, flashTint, OUTLINE_ALPHA, outlineFlashK } from "../occludeOutline";
import { bareBodyOf, BODY_LABEL, bodyNodes, isProne } from "../unitSprite";
import { legacySilhouetteWanted, newOclMemo, outlineColor, outlineTexture, planOcclusion, type OclEntry, type OclSource, type OclUnit, type OutlineTex } from "./outlineLayer";
import { UnitLayer } from "./unitLayer";

/** 外框 Sprite 的節點名稱。 */
export const OUTLINE_LABEL = "occlude-outline";

/** 開發頁量測（`occlusionStats`）：最近一次 `drawOcclusion` 的耗時與每個單位的結果。 */
export interface OcclusionStats {
  /** 整段 `drawOcclusion` 的耗時（毫秒）。 */
  readonly ms: number;
  readonly entries: ReadonlyArray<Pick<OclEntry, "id" | "ratio" | "area" | "drawn" | "skip">>;
  /** 實際呼叫 `getImageData` 的累計次數與目前遮罩快取的張數。 */
  readonly alphaReads: number;
  readonly alphaMasks: number;
  /** OCL-1b：片段結束後重算的次數（擺位沒變、直接沿用的不算）。 */
  readonly refreshes?: number;
}

/** 身體節點在單位節點裡的「站好」位置與旋轉（`draw` 時記下；片段中重算用）。 */
interface RestBody {
  readonly x: number;
  readonly y: number;
  readonly rotation: number;
}

/** RGBA → 畫布（`putImageData`）；沒有 DOM 時 `null`。 */
function outlineCanvas(t: OutlineTex): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const c = document.createElement("canvas");
  c.width = t.w;
  c.height = t.h;
  const ctx = c.getContext("2d");
  if (ctx === null) return null;
  ctx.putImageData(new ImageData(t.make() as Uint8ClampedArray<ArrayBuffer>, t.w, t.h), 0, 0);
  return c;
}

/** 擺位的簽名（片段結束時和上一次算的比；相同就沿用，不重建 Sprite）。 */
function unitsSignature(units: readonly OclUnit[]): string {
  return units.map((e) => `${e.id}@${e.row ?? e.u.y}:${e.feet.x},${e.feet.y}:${e.body.key}:${e.tilted === true ? 1 : 0}:${e.u.downed ? 1 : 0}:${e.u.hiddenInfo === true ? 1 : 0}:${(e.u.statusIds ?? []).join("+")}`).join(";");
}

export abstract class OcclusionLayer extends UnitLayer {
  /** 開發頁 `&ocl=0`：關掉外框（效能對照；正式畫面一律開）。 */
  outlinesEnabled = true;
  /** 開發頁 `&measure=1`：每個單位都算面積與比例。 */
  outlineMeasure = false;
  /** 這一輪畫了外框的單位（縮放改變時重建貼圖用）。 */
  private readonly outlinePlan = new Map<string, { unit: OclUnit; layers: NonNullable<OclEntry["layers"]>; key: string }>();
  private readonly oclMemo = newOclMemo();
  private oclStats: OcclusionStats = { ms: 0, entries: [], alphaReads: 0, alphaMasks: 0 };
  /** OCL-1b：最近一次 `drawOcclusion` 的畫面（片段結束重算、舊剪影用）。 */
  private oclModel: DrawModel | null = null;
  /** OCL-1b：身體節點「站好」的位置（`draw` 時記下，單位 ID → 相對單位節點）。 */
  private readonly restOf = new Map<string, RestBody>();
  /** OCL-1b（Q5）：移動中的人（自己的外框藏起來；有人在移動時不重算，別人的沿用移動前的結果）。 */
  protected readonly movingIds = new Set<string>();
  /** 這次 `draw` 之後移動過的人（`model` 的格子已經不是它現在的位置：舊剪影等下次重畫）。 */
  private readonly movedSinceDraw = new Set<string>();
  /** 倒下片段中的人（不畫外框；下次 `draw` 清掉）。 */
  private readonly outlineHidden = new Set<string>();
  /** 受擊閃白中的 k（單位 ID → 0～1；結束時刪掉）。 */
  private readonly outlineK = new Map<string, number>();
  /** 上一次算外框時的擺位簽名。 */
  private lastSig = "";
  private refreshCount = 0;

  /** 身體 alpha：模型像素用（`om|`，固定解析度）與畫面解析度（`oa|`，和身體貼圖同 `res`）；同一個鍵只讀一次。 */
  protected readonly oclSource: OclSource = {
    maskImage: (b, res) => this.art.alphaMask(`om|${res}|${b.key}`, () => b.draw(res)),
    texImage: (b) => {
      const res = this.art.figureRes(b.display);
      const key = `${res}|${b.key}`;
      const img = this.art.alphaMask(`oa|${key}`, () => b.draw(res));
      return img === null ? null : { key, img };
    },
  };

  /**
   * 這一輪的擺位：照畫的順序（由北到南、同一排照 `units` 的子節點），腳底＝單位節點＋身體節點的位置。
   * `live`（OCL-1b，片段結束重算）：單位資料用繪製器目前的（轉向、滑倒後的），排用畫面上所在的排，身體位置用 `draw` 時記下的站好位置。
   */
  protected occlusionUnits(model: DrawModel, live = false): OclUnit[] {
    const idOf = new Map<Container, string>();
    for (const [id, s] of this.unitSprites) idOf.set(s, id);
    for (const [id, s] of this.downedSprites) idOf.set(s, id);
    const drawOf = new Map(model.units.map((u) => [u.id, u]));
    const out: OclUnit[] = [];
    for (let y = 0; y < model.height; y++) {
      for (const child of this.rows.row(y).units.children) {
        const id = idOf.get(child);
        const u: UnitDraw | undefined = id === undefined ? undefined : live ? (this.unitDrawOf.get(id) ?? this.downedDrawOf.get(id) ?? drawOf.get(id)) : drawOf.get(id);
        if (id === undefined || u === undefined) continue;
        const body = bodyNodes(child).find((n) => n.label === BODY_LABEL);
        if (body === undefined) continue;
        const rest = live ? (this.restOf.get(id) ?? { x: body.x, y: body.y, rotation: body.rotation }) : { x: body.x, y: body.y, rotation: body.rotation };
        if (!live) this.restOf.set(id, rest);
        const tilted = rest.rotation !== 0 || (live && isProne(u)); // 走路滑倒後躺著（`markProne`）
        out.push({ id, u, order: out.length, feet: { x: child.x + rest.x, y: child.y + rest.y }, body: bareBodyOf(u), tilted, row: y });
      }
    }
    return out;
  }

  /** 擺位改變（`draw(model)`）時算外框與舊剪影。要在全部單位畫完、`rows` 排好之後呼叫。 */
  protected drawOcclusion(model: DrawModel): void {
    const t0 = performance.now();
    this.oclModel = model;
    this.restOf.clear();
    this.movedSinceDraw.clear();
    this.outlineHidden.clear();
    const units = this.occlusionUnits(model);
    const plan = this.placeOutlines(model, units);
    // D5：6F-22 舊剪影——同一單位這一格有新外框時不畫；沒有時照現行條件畫（不能先拿掉）
    for (const u of model.units) if (legacySilhouetteWanted(this.terrainOccluded(model, u), this.outlineOf.has(u.id))) this.drawLegacySilhouette(u);
    this.oclStats = {
      ms: performance.now() - t0,
      entries: units.map((e) => {
        const p = plan.get(e.id);
        return { id: e.id, ratio: p?.ratio ?? 0, area: p?.area ?? null, drawn: p?.drawn ?? false, skip: p?.skip };
      }),
      alphaReads: this.art.alphaReads,
      alphaMasks: this.art.alphaMaskCount,
      refreshes: this.refreshCount,
    };
  }

  /** 算比例與遲滯、建外框 Sprite（舊的先拿掉）；更新遲滯狀態。 */
  private placeOutlines(model: DrawModel, units: readonly OclUnit[]): Map<string, OclEntry> {
    for (const s of this.outlineOf.values()) if (!s.destroyed) s.destroy();
    this.outlineOf.clear();
    this.outlinePlan.clear();
    this.lastSig = unitsSignature(units);
    const plan = planOcclusion(units, this.outlineWas, this.oclSource, { off: !this.outlinesEnabled, measure: this.outlineMeasure, memo: this.oclMemo });
    for (const e of units) {
      const p = plan.get(e.id);
      if (p?.drawn === true && p.layers !== undefined) this.addOutline(e, p.layers);
    }
    // 遲滯狀態：這一輪有沒有畫；不在場上的刪掉
    const ids = new Set(model.units.map((u) => u.id));
    for (const id of [...this.outlineWas.keys()]) if (!ids.has(id)) this.outlineWas.delete(id);
    for (const u of model.units) this.outlineWas.set(u.id, plan.get(u.id)?.drawn === true);
    return plan;
  }

  /**
   * OCL-1b（交付 1）：片段結束（移動結束、出招前轉向、出招列結束）時重算一次。有人在移動時延後到移動結束（Q5）；
   * 擺位和上一次一樣（站好的位置、排、身體鍵都沒變）就沿用，不重建 Sprite。舊剪影只動沒移動過的人（移動過的等下次重畫）。
   */
  protected refreshOcclusion(): void {
    const model = this.oclModel;
    if (model === null) return;
    if (this.movingIds.size > 0) return; // 移動結束（`endMove`）時再算
    const units = this.occlusionUnits(model, true);
    if (unitsSignature(units) === this.lastSig) return;
    this.refreshCount += 1;
    this.placeOutlines(model, units);
    for (const u of model.units) {
      if (this.movedSinceDraw.has(u.id)) continue;
      const want = legacySilhouetteWanted(this.terrainOccluded(model, u), this.outlineOf.has(u.id));
      const have = this.silhouetteOf.get(u.id);
      if (want && have === undefined) this.drawLegacySilhouette(u);
      else if (!want && have !== undefined) {
        have.destroy();
        this.silhouetteOf.delete(u.id);
      }
    }
    this.tickOutlines();
  }

  /** OCL-1b（Q5）：開始移動——自己的外框藏起來（別人的沿用）。 */
  protected beginMove(unitId: string): void {
    this.movingIds.add(unitId);
    this.movedSinceDraw.add(unitId);
    const s = this.outlineOf.get(unitId);
    if (s !== undefined && !s.destroyed) s.visible = false;
  }

  /** OCL-1b（Q5）：移動結束——沒有其他人在移動時重算（移動中延後的也一起）。 */
  protected endMove(unitId: string): void {
    this.movingIds.delete(unitId);
    if (this.movingIds.size === 0) this.refreshOcclusion();
  }

  /** OCL-1b（Q6）：倒下片段中不畫外框（下次 `draw` 時這個人已經是倒下的，過濾掉）。 */
  protected hideOutline(unitId: string): void {
    this.outlineHidden.add(unitId);
    const s = this.outlineOf.get(unitId);
    if (s !== undefined && !s.destroyed) s.visible = false;
  }

  /**
   * OCL-1b（D4、Q6）：受擊閃白。`flash` ＝ 當下的白閃、`peak` ＝ 這個效果自己的峰值（呼叫點傳入）；k ＝ flash ÷ peak，
   * `tint` ＝ mix(陣營色, 白, k)、`alpha` ＝ 0.8 + 0.2k，不換外框貼圖。白閃結束傳 `flash` 0 回到原色。
   */
  protected flashOutline(unitId: string, flash: number, peak: number): void {
    const k = outlineFlashK(flash, peak);
    if (k > 0) this.outlineK.set(unitId, k);
    else this.outlineK.delete(unitId);
    const s = this.outlineOf.get(unitId);
    const u = this.unitDrawOf.get(unitId) ?? this.downedDrawOf.get(unitId) ?? this.outlinePlan.get(unitId)?.unit.u;
    if (s !== undefined && !s.destroyed && u !== undefined) this.applyFlash(s, u, k);
  }

  private applyFlash(s: Sprite, u: Pick<UnitDraw, "summon" | "team">, k: number): void {
    s.tint = k > 0 ? flashTint(outlineColor(u), k) : outlineColor(u);
    s.alpha = k > 0 ? flashAlpha(k) : OUTLINE_ALPHA;
  }

  /**
   * OCL-1b（Q4、Q5）：每格把外框對齊身體節點的平移（含擊退、異形的位移、前推）；身體有旋轉（空翻、倒下、側彎）、
   * 移動中、倒下片段中、小人不在畫面上時藏起來。只動位置與 `visible`，不換貼圖。
   */
  protected tickOutlines(): void {
    for (const [id, s] of this.outlineOf) {
      if (s.destroyed) continue;
      const c = this.unitSprites.get(id) ?? this.downedSprites.get(id);
      const body = c === undefined || c.destroyed ? undefined : bodyNodes(c).find((n) => n.label === BODY_LABEL);
      const show = c !== undefined && body !== undefined && c.parent !== null && c.visible && body.visible && body.rotation === 0 && !this.movingIds.has(id) && !this.outlineHidden.has(id);
      s.visible = show;
      if (show) s.position.set(c.x + body.x, c.y + body.y);
    }
  }

  private addOutline(unit: OclUnit, layers: NonNullable<OclEntry["layers"]>): void {
    const t = outlineTexture(unit, layers, this.oclSource, this.scale, this.oclMemo);
    if (t === null) return;
    const tex = this.art.outline(t.key, () => outlineCanvas(t));
    if (tex === null) return;
    const s = new Sprite(tex);
    s.label = OUTLINE_LABEL;
    const { box, k } = unit.body;
    s.anchor.set(0.5, box.foot / box.h);
    s.width = box.w * k;
    s.height = box.h * k;
    s.position.set(unit.feet.x, unit.feet.y);
    this.applyFlash(s, unit.u, this.outlineK.get(unit.id) ?? 0);
    s.visible = !this.movingIds.has(unit.id) && !this.outlineHidden.has(unit.id);
    this.silhouettes.addChild(s);
    this.outlineOf.set(unit.id, s);
    this.art.holdFor(`ol:${unit.id}`, tex);
    this.outlinePlan.set(unit.id, { unit, layers, key: t.key });
  }

  /** Q2：縮放改變時只重建外框貼圖（量化線寬或貼圖解析度變了才換）；比例、遲滯、裁切的前排不重算。 */
  protected rebuildOutlines(): void {
    for (const [id, p] of this.outlinePlan) {
      const s = this.outlineOf.get(id);
      if (s === undefined || s.destroyed) continue;
      const t = outlineTexture(p.unit, p.layers, this.oclSource, this.scale, this.oclMemo);
      if (t === null || t.key === p.key) continue;
      const tex = this.art.outline(t.key, () => outlineCanvas(t));
      if (tex === null) continue;
      s.texture = tex;
      const { box, k } = p.unit.body;
      s.width = box.w * k;
      s.height = box.h * k;
      this.art.holdFor(`ol:${id}`, tex);
      this.outlinePlan.set(id, { ...p, key: t.key });
    }
  }

  /** 開發頁量測：最近一次 `drawOcclusion` 的結果。 */
  occlusionStats(): OcclusionStats {
    return { ...this.oclStats, refreshes: this.refreshCount };
  }
}
