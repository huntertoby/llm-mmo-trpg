// OCL-1a：被遮擋剪影外框的圖層（`docs/phases/PhaseOCL-1計畫.md`）。全部單位畫完後（`BattleRenderer.draw`）呼叫 `drawOcclusion`：
// 照畫的順序收集擺位 → `planOcclusion`（過濾、大型前排、比例、遲滯）→ 要畫的做成外框 Sprite 放進 `silhouettes`
// （在所有排與排內 HUD 之上、`hudTop`／`hover`／特效之下）→ 6F-22 舊剪影只畫「被地形擋、而且沒有新外框」的（D5）。
// 縮放改變（`setScale`）只重建外框貼圖（`rebuildOutlines`），比例與遲滯不重算（Q2）。
import { Container, Sprite } from "pixi.js";
import type { DrawModel } from "../../battle/drawModel";
import { OUTLINE_ALPHA } from "../occludeOutline";
import { bareBodyOf, BODY_LABEL, bodyNodes } from "../unitSprite";
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

export abstract class OcclusionLayer extends UnitLayer {
  /** 開發頁 `&ocl=0`：關掉外框（效能對照；正式畫面一律開）。 */
  outlinesEnabled = true;
  /** 開發頁 `&measure=1`：每個單位都算面積與比例。 */
  outlineMeasure = false;
  /** 這一輪畫了外框的單位（縮放改變時重建貼圖用）。 */
  private readonly outlinePlan = new Map<string, { unit: OclUnit; layers: NonNullable<OclEntry["layers"]>; key: string }>();
  private readonly oclMemo = newOclMemo();
  private oclStats: OcclusionStats = { ms: 0, entries: [], alphaReads: 0, alphaMasks: 0 };

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

  /** 這一輪的擺位：照畫的順序（由北到南、同一排照 `units` 的子節點），腳底＝單位節點＋身體節點的位置。 */
  protected occlusionUnits(model: DrawModel): OclUnit[] {
    const idOf = new Map<Container, string>();
    for (const [id, s] of this.unitSprites) idOf.set(s, id);
    for (const [id, s] of this.downedSprites) idOf.set(s, id);
    const drawOf = new Map(model.units.map((u) => [u.id, u]));
    const out: OclUnit[] = [];
    for (let y = 0; y < model.height; y++) {
      for (const child of this.rows.row(y).units.children) {
        const id = idOf.get(child);
        const u = id === undefined ? undefined : drawOf.get(id);
        if (id === undefined || u === undefined) continue;
        const body = bodyNodes(child).find((n) => n.label === BODY_LABEL);
        if (body === undefined) continue;
        out.push({ id, u, order: out.length, feet: { x: child.x + body.x, y: child.y + body.y }, body: bareBodyOf(u), tilted: body.rotation !== 0 });
      }
    }
    return out;
  }

  /** 擺位改變（`draw(model)`）時算外框與舊剪影。要在全部單位畫完、`rows` 排好之後呼叫。 */
  protected drawOcclusion(model: DrawModel): void {
    const t0 = performance.now();
    this.outlineOf.clear();
    this.outlinePlan.clear();
    const units = this.occlusionUnits(model);
    const plan = planOcclusion(units, this.outlineWas, this.oclSource, { off: !this.outlinesEnabled, measure: this.outlineMeasure, memo: this.oclMemo });
    for (const e of units) {
      const p = plan.get(e.id);
      if (p?.drawn === true && p.layers !== undefined) this.addOutline(e, p.layers);
    }
    // 遲滯狀態：這一輪有沒有畫；不在場上的刪掉
    const ids = new Set(model.units.map((u) => u.id));
    for (const id of [...this.outlineWas.keys()]) if (!ids.has(id)) this.outlineWas.delete(id);
    for (const u of model.units) this.outlineWas.set(u.id, plan.get(u.id)?.drawn === true);
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
    };
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
    s.tint = outlineColor(unit.u);
    s.alpha = OUTLINE_ALPHA;
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
    return this.oclStats;
  }
}
