// RG-3（#162）戰場標記的圖層：被瞄準的準星、瞄準線（照排切段、往目標流動；被擋時斷點短槓＋灰點線）、
// 盾兵擋住的小盾與連結（只在選目標預覽有盾兵掩護時）、可疑痕跡（陷阱層）；看一眼在 `FeedbackLayer`（浮字那一層）。
// 規格 `docs/art/RG樣張.md` 第 2、3、8 節；幾何與時間是 `battle/rgMarks.ts` 的純函式，畫法是 `render/rgArt.ts`。
// 圖層（樣張第 3 節）：可疑痕跡＝每排 `traps`；瞄準線＝每排 `aims`（紅框之上、單位之下）；準星、斷點短槓、盾兵連結、小盾＝
// 頭頂標記層 `headMarks`（所有排與 `hudTop` 之上、浮字與特效之下）。
// 頭頂＝量身體貼圖的實際上緣（含頭飾，只量中心左右 ±9 模型 px；第 8 節第 1 條），只給準星、小盾、看一眼；浮字照舊 `unitTopY`。
import { Container, Graphics, Sprite, Texture, type Ticker } from "pixi.js";
import type { Pos } from "../../api/types";
import { tileLift } from "../../battle/elevation";
import { TILE_SIZE } from "../../battle/geometry";
import {
  AIM_BLOCKED_COLOR,
  AIM_COLOR,
  BADGE_AVOID,
  blinkPhase,
  CHEST_DY,
  chipCenter,
  dashes,
  flowOffset,
  lineGeom,
  linkDots,
  pointAt,
  reticleDraws,
  reticleY,
  RG_INK,
  RG_MIN,
  splitRows,
  type AimDraw,
  type GuardDraw,
  type LineGeom,
} from "../../battle/rgMarks";
import type { DrawModel } from "../../battle/drawModel";
import { minMarkScale } from "../minMark";
import { drawReticle, drawShieldChip, drawTraceGround, drawTraceQuestion, QUESTION_AT, rgCanvas } from "../rgArt";
import { bareBodyOf, BODY_LABEL, bodyNodes, creatureOf, HUMAN_TOP_Y, unitMarkTopY, unitTopY, type BareBody } from "../unitSprite";
import type { Highlights } from "./highlightLayer";
import { OcclusionLayer } from "./occlusionLayer";

const T = TILE_SIZE;
/** 量頭頂用的遮罩解析度（每虛擬像素 2 個畫布像素）與 alpha 門檻。 */
const HEAD_RES = 2;
const HEAD_ALPHA = 128;
/** 只量單位中心左右 ±9 模型 px（避開法杖頭、舉起的武器）。 */
const HEAD_HALF = 9;

/** 一條瞄準線在畫面上的狀態（每一幀重畫虛線）。 */
interface LineState {
  geom: LineGeom;
  /** 兩端未抬高的 y（照排切段用）。 */
  ya: number;
  yb: number;
  k: number;
  /** 每一排一個 Graphics（在那一排的 `aims`）。 */
  pens: Map<number, Graphics>;
}

interface ReticleState {
  sprite: Sprite;
  blocked: boolean;
  phase: 0 | 1;
  k: number;
  res: number;
}

export abstract class RgMarkLayer extends OcclusionLayer {
  /** 頭頂標記層（準星、斷點短槓、盾兵連結、小盾）；`BattleRenderer.init` 放在 `hudTop`、`hover` 之上、特效之下。 */
  protected readonly headMarks = new Container();
  private rgAims: readonly AimDraw[] = [];
  private rgGuard: GuardDraw | null = null;
  private rgLines: LineState[] = [];
  private rgReticles: ReticleState[] = [];
  private rgTraceNodes: Container[] = [];
  /** RG 標記自己的時鐘（毫秒；準星閃爍、虛線流動）。 */
  private rgClock = 0;
  private rgTicking: ((t: Ticker) => void) | null = null;
  private readonly rgTex = new Map<string, Texture>();
  /** 身體鍵 → 頭頂相對腳底（模型 px，往上為負）；量不到為 null。外觀或朝向變了鍵就變（第 8 節：變了才重量）。 */
  private readonly headTopMemo = new Map<string, number | null>();

  setHighlights(all: Highlights): void {
    super.setHighlights(all);
    if (!this.ready) return;
    this.rgAims = all.aims ?? [];
    this.rgGuard = all.guard ?? null;
    this.drawRgOverlay();
  }

  /** 畫面上的反向放大倍率（`minMark`）。 */
  private rgK(spec: { base: number; min: number }): number {
    return minMarkScale(spec.base, spec.min, this.scale);
  }

  /** 貼圖解析度：裝置像素比 × 地圖縮放 × 倍率，取 0.25 的倍數（至少 1）。 */
  private rgRes(k: number): number {
    const r = (typeof window === "undefined" ? 1 : window.devicePixelRatio || 1) * this.scale * k;
    return Math.max(1, Math.ceil(r * 4) / 4);
  }

  /** 畫布貼圖（自己的快取，鍵含解析度）。 */
  protected rgTexture(key: string, w: number, h: number, ox: number, oy: number, res: number, paint: (ctx: CanvasRenderingContext2D) => void): Texture | null {
    const full = `${key}|${res}`;
    const hit = this.rgTex.get(full);
    if (hit !== undefined && !hit.destroyed) return hit;
    const c = rgCanvas(w, h, ox, oy, res, paint);
    if (c === null) return null;
    const tex = Texture.from(c);
    this.rgTex.set(full, tex);
    return tex;
  }

  /** 世界座標的頭頂（含頭飾）：量身體貼圖的實際上緣；頭目照 `unitMarkTopY`（HUD 上緣）；量不到時 `unitTopY`。單位不在場上時 null。 */
  protected rgHeadTop(unitId: string): number | null {
    const sprite = this.unitSprites.get(unitId);
    const u = this.unitDrawOf.get(unitId);
    if (sprite === undefined || u === undefined || sprite.destroyed) return null;
    if (creatureOf(u)?.boss !== undefined) return sprite.y + unitMarkTopY(u);
    const body = bodyNodes(sprite).find((n) => n.label === BODY_LABEL);
    const rel = body === undefined ? null : this.measuredTop(bareBodyOf(u));
    return rel === null || body === undefined ? sprite.y + unitTopY(u) : sprite.y + body.y + rel;
  }

  /** 身體貼圖中心左右 ±9 模型 px 內第一列不透明像素，換成相對腳底的模型 px。 */
  private measuredTop(b: BareBody): number | null {
    const memo = this.headTopMemo.get(b.key);
    if (memo !== undefined) return memo;
    const img = this.art.alphaMask(`om|${HEAD_RES}|${b.key}`, () => b.draw(HEAD_RES));
    let out: number | null = null;
    if (img !== null) {
      const cx = img.w / 2;
      const half = (HEAD_HALF / b.k) * HEAD_RES;
      const x0 = Math.max(0, Math.floor(cx - half));
      const x1 = Math.min(img.w - 1, Math.ceil(cx + half));
      scan: for (let y = 0; y < img.h; y++) {
        for (let x = x0; x <= x1; x++) {
          if ((img.alpha[y * img.w + x] ?? 0) >= HEAD_ALPHA) {
            out = (y / HEAD_RES - b.box.foot) * b.k;
            break scan;
          }
        }
      }
    }
    this.headTopMemo.set(b.key, out);
    return out;
  }

  /** 縮放改變時重畫（反向放大倍率變了）。 */
  protected rgRescale(): void {
    if (this.model !== null) this.drawRgTraces(this.model);
    this.drawRgOverlay();
  }

  /** 可疑痕跡（`model.traces`）：畫在每排的陷阱層；「？」反向放大。 */
  protected drawRgTraces(model: DrawModel): void {
    for (const n of this.rgTraceNodes) if (!n.destroyed) n.destroy({ children: true });
    this.rgTraceNodes = [];
    const traces = model.traces ?? [];
    if (traces.length === 0) return;
    const qk = this.rgK(RG_MIN.question);
    const ground = this.rgTexture("rg-trace", T, T, 0, 0, this.rgRes(1), (ctx) => drawTraceGround(ctx, 0, 0, T));
    const q = this.rgTexture("rg-trace-q", 16, 16, 8, 8, this.rgRes(qk), (ctx) => drawTraceQuestion(ctx, 0, 0));
    for (const p of traces) {
      const node = new Container();
      if (ground !== null) {
        const s = new Sprite(ground);
        s.width = T;
        s.height = T;
        node.addChild(s);
      }
      if (q !== null) {
        const s = new Sprite(q);
        s.anchor.set(0.5);
        s.width = 16 * qk;
        s.height = 16 * qk;
        s.position.set(QUESTION_AT.x, QUESTION_AT.y);
        node.addChild(s);
      }
      node.label = "rg-trace";
      this.rows.row(p.y).traps.addChild(node);
      this.place(node, p, p.x * T, p.y * T);
      this.rgTraceNodes.push(node);
    }
  }

  /** 準星、瞄準線、斷點、盾兵連結與小盾（設定高亮、重畫場景、縮放改變時都重來）。 */
  protected drawRgOverlay(): void {
    for (const l of this.rgLines) for (const g of l.pens.values()) if (!g.destroyed) g.destroy();
    this.rgLines = [];
    this.rgReticles = [];
    for (const c of this.headMarks.removeChildren()) c.destroy({ children: true });
    if (this.model === null) return;
    this.drawAims();
    this.drawGuard();
    this.ensureRgTick();
  }

  private drawAims(): void {
    if (this.rgAims.length === 0) return;
    const rk = this.rgK(RG_MIN.reticle);
    const lk = this.rgK(RG_MIN.line);
    const tops = new Map<string, number>();
    const topOf = (id: string, p: Pos): number => {
      const hit = tops.get(id);
      if (hit !== undefined) return hit;
      const y = this.rgHeadTop(id) ?? this.center(p).y + HUMAN_TOP_Y;
      tops.set(id, y);
      return y;
    };
    const bars = new Graphics();
    for (const a of this.rgAims) {
      const c = this.center(a.caster);
      const t = this.center(a.target);
      const from = { x: c.x, y: c.y + CHEST_DY };
      const to = { x: t.x, y: reticleY(topOf(a.targetId, a.target), rk) };
      const badge = { x: c.x + BADGE_AVOID.dx, y: c.y + BADGE_AVOID.dy };
      const blocker = a.blocker === null ? null : (() => {
        const b = this.center(a.blocker);
        return { x: b.x, y: b.y + CHEST_DY };
      })();
      const geom = lineGeom(from, to, rk, badge, blocker);
      if (geom === null) continue;
      const ya = from.y + tileLift(this.heightOf(a.caster));
      const yb = to.y + tileLift(this.heightOf(a.target));
      this.rgLines.push({ geom, ya, yb, k: lk, pens: new Map() });
      if (geom.cut !== null) this.drawBreakBar(bars, geom, Math.min(lk, 1.3));
    }
    for (const l of this.rgLines) this.paintLine(l);
    for (const r of reticleDraws(this.rgAims)) {
      const p = this.center(r.pos);
      const res = this.rgRes(rk);
      const phase = blinkPhase(this.rgClock, this.reduced);
      const tex = this.reticleTex(phase, r.blocked, res);
      if (tex === null) continue;
      const s = new Sprite(tex);
      s.anchor.set(12 / 24, 12 / 26);
      s.width = 24 * rk;
      s.height = 26 * rk;
      s.position.set(p.x, reticleY(topOf(r.targetId, r.pos), rk));
      s.label = "rg-reticle";
      this.rgReticles.push({ sprite: s, blocked: r.blocked, phase, k: rk, res });
    }
    this.headMarks.addChild(bars, ...this.rgReticles.map((r) => r.sprite));
  }

  private reticleTex(phase: 0 | 1, blocked: boolean, res: number): Texture | null {
    return this.rgTexture(`rg-reticle|${blocked ? "b" : phase}`, 24, 26, 12, 12, res, (ctx) => drawReticle(ctx, 0, 0, phase, blocked));
  }

  /** 斷點：垂直於線的本色短槓（長 11、線 2.6＋外框）；800 寬最多放大 1.3。 */
  private drawBreakBar(g: Graphics, geom: LineGeom, k: number): void {
    const at = pointAt(geom, geom.cut ?? geom.start);
    const nx = -geom.uy;
    const ny = geom.ux;
    const h = 5.5 * k;
    const seg = () => g.moveTo(at.x - nx * h, at.y - ny * h).lineTo(at.x + nx * h, at.y + ny * h);
    seg().stroke({ width: 2.6 * k + 2, color: RG_INK, cap: "round" });
    seg().stroke({ width: 2.6 * k, color: AIM_COLOR, cap: "round" });
  }

  /** 一條線這一幀的虛線（前段本色流動；被擋時斷點後空 4、灰點線不流動），照排切開畫進每排的 `aims`。 */
  private paintLine(l: LineState): void {
    const { geom, k } = l;
    for (const g of l.pens.values()) g.clear();
    const pen = (row: number): Graphics => {
      let g = l.pens.get(row);
      if (g === undefined || g.destroyed) {
        g = new Graphics();
        g.label = "rg-aim";
        l.pens.set(row, g);
        this.rows.row(row).aims.addChild(g);
      }
      return g;
    };
    const rows = this.model?.height ?? 1;
    const cut = geom.cut ?? geom.end;
    const front = dashes(geom.start, cut, 4 * k, 7 * k, flowOffset(this.rgClock, k, this.reduced));
    const tailFrom = cut + 4;
    const tail = geom.cut === null || tailFrom >= geom.end ? [] : dashes(tailFrom, geom.end, 1.5 * k, 5 * k, -tailFrom);
    const pieces = (list: Array<[number, number]>) => list.flatMap(([s0, s1]) => splitRows(s0, s1, geom.len, l.ya, l.yb, rows));
    const fp = pieces(front);
    const tp = pieces(tail);
    const stroke = (list: typeof fp, width: number, color: number, alpha: number) => {
      const used = new Set<number>();
      for (const p of list) {
        const a = pointAt(geom, p.s0);
        const b = pointAt(geom, p.s1);
        pen(p.row).moveTo(a.x, a.y).lineTo(b.x, b.y);
        used.add(p.row);
      }
      for (const r of used) pen(r).stroke({ width, color, alpha, cap: "round" });
    };
    // 每一段自己包外框色（先描全部外框、再描全部本色），所以是一顆顆膠囊
    stroke(fp, 2 * k + 2, RG_INK, 0.85);
    stroke(tp, 2 * k + 1.5, RG_INK, 0.6);
    stroke(fp, 2 * k, AIM_COLOR, 1);
    stroke(tp, 2 * k, AIM_BLOCKED_COLOR, 1);
  }

  /** 盾兵連結（米白點線，盾兵 → 小盾的側邊）與小盾。 */
  private drawGuard(): void {
    const gd = this.rgGuard;
    if (gd === null) return;
    const ck = this.rgK(RG_MIN.chip);
    const w = this.center(gd.ward);
    const top = this.rgHeadTop(gd.wardId) ?? w.y + HUMAN_TOP_Y;
    const chip = chipCenter(gd.guard, gd.ward, w.x, top, ck);
    const dots = new Graphics();
    for (const d of linkDots(this.center(gd.guard), w, chip, ck)) {
      dots.circle(d.x, d.y, d.r + 0.8).fill({ color: RG_INK, alpha: 0.45 });
      dots.circle(d.x, d.y, d.r).fill({ color: 0xe8f0f8, alpha: 0.85 });
    }
    dots.label = "rg-guard-link";
    this.headMarks.addChild(dots);
    const tex = this.rgTexture("rg-chip", 16, 16, 8, 8, this.rgRes(ck), (ctx) => drawShieldChip(ctx, 0, 0));
    if (tex === null) return;
    const s = new Sprite(tex);
    s.anchor.set(0.5);
    s.width = 16 * ck;
    s.height = 16 * ck;
    s.position.set(chip.x, chip.y);
    s.label = "rg-guard-chip";
    this.headMarks.addChild(s);
  }

  /** 準星閃爍、虛線流動（有瞄準時才跑；減少動態時不動）。 */
  private ensureRgTick(): void {
    if (this.rgTicking !== null || !this.ready) return;
    const tick = (t: Ticker) =>
      this.guard(() => {
        if (this.rgLines.length === 0 && this.rgReticles.length === 0) return;
        this.rgClock += t.deltaMS;
        if (this.reduced) return;
        for (const l of this.rgLines) this.paintLine(l);
        const phase = blinkPhase(this.rgClock);
        for (const r of this.rgReticles) {
          if (r.blocked || r.phase === phase || r.sprite.destroyed) continue;
          const tex = this.reticleTex(phase, false, r.res);
          if (tex === null) continue;
          r.sprite.texture = tex;
          r.sprite.width = 24 * r.k;
          r.sprite.height = 26 * r.k;
          r.phase = phase;
        }
      });
    this.rgTicking = tick;
    this.app.ticker.add(tick);
  }

  /** 銷毀時釋放自己的貼圖。 */
  protected rgDestroy(): void {
    for (const t of this.rgTex.values()) if (!t.destroyed) t.destroy(true);
    this.rgTex.clear();
  }

  /** 測試、截圖用：目前畫了幾條線、幾個準星、有沒有小盾、幾個痕跡。 */
  rgStats(): { lines: number; blocked: number; reticles: number; grayReticles: number; guard: boolean; traces: number } {
    return {
      lines: this.rgLines.length,
      blocked: this.rgLines.filter((l) => l.geom.cut !== null).length,
      reticles: this.rgReticles.length,
      grayReticles: this.rgReticles.filter((r) => r.blocked).length,
      guard: this.rgGuard !== null && this.headMarks.children.some((c) => c.label === "rg-guard-chip"),
      traces: this.rgTraceNodes.filter((n) => !n.destroyed).length,
    };
  }
}
