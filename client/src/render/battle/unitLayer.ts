// 單位圖層（R1e 自 `BattleRenderer.ts` 拆出，純搬移）：畫單位與剪影、HUD 掛載（`hudTop`、朝南三角形）、連心虛線、
// 換姿勢（`poseBody`／`restBody`）、待機、轉身。
import { Container, Graphics, RenderLayer, Sprite, type Texture } from "pixi.js";
import type { DrawModel, UnitDraw } from "../../battle/drawModel";
import { TILE_SIZE } from "../../battle/geometry";
import { heightAt, occluded } from "../../battle/elevation";
import { RING } from "../artPalette";
import { silhouette } from "../heightArt";
import { southArrowPlace } from "../rowLayers";
import { CHARGE_BADGE_LABEL, HP_BAR_LABEL, PART_STRIP_LABEL, SOUTH_ARROW_LABEL, STATUS_ROW_LABEL } from "../minMark";
import { neighborFaces } from "../badgeLayout";
import { mapEdgeOf, NO_EDGE } from "../rowLayout";
import { BODY_LABEL, bodyNodes, bodyTexture, buildUnitSprite, creatureOf, dollPx, isLinked, isProne, PART_DEBRIS_LABEL, placeCreatureBody, PRONE, ringScale, specOfUnit, type BodyFrame } from "../unitSprite";
import { dollKey } from "../appearance";
import { partGlowCanvas } from "../bossPartArt";
import { DOLL_FOOT_Y, DOLL_H, DOLL_W } from "../paperdoll";
import type { PartFx } from "../../battle/partStrip";
import { roofCovers } from "../sceneryModel";
import type { InkPose } from "../inkPose";
import { creaturePerches, LINK_COLOR } from "../inkCreature";
import { linkPairs } from "../linkLines";
import { knockOffset, proneBody } from "../motionClips";
import { FEET } from "../unitSprite";
import type { ClipFrame } from "../skillClips";
import type { Facing } from "../../api/types";
import { HighlightLayer } from "./highlightLayer";
import { DOLL_PX } from "./rendererBase";

/** CB-3：鳥留在空中等攻擊的最長時間（效果時鐘毫秒；正常是走完到下一步出招之間的停頓，遠小於這個數）。 */
const ALOFT_MAX_MS = 4000;
/** PB-1e：選單打開時頭目的狀態列與蓄力徽章的透明度（美術移植需求 3.5）。 */
export const PART_MENU_DIM = 0.4;
/** PB-1e：選單滑過部位時的亮起節點。 */
export const PART_GLOW_LABEL = "part-glow";

const T = TILE_SIZE;

export abstract class UnitLayer extends HighlightLayer {
  /** 「連心的」精英到相鄰（曼哈頓 1）同陣營單位的青色虛線（Phase 5A-ART2），畫在腳邊、單位底下。 */
  protected drawLinks(model: DrawModel): void {
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

  /**
   * 6F-21b：朝南三角形的圖層與高度（`southArrowPlace`）：南邊那格是高台時把三角形往上移到那格的地面；
   * 回傳要掛的全域層（南邊那格沒人站），或 `null`（照 6F-21 掛南邊一排的 `under`；最南一排跟著單位畫）。
   */
  private southArrowTop(model: DrawModel, u: UnitDraw, sprite: Container): RenderLayer | null {
    const arrow = sprite.children.find((n) => n.label === SOUTH_ARROW_LABEL);
    if (arrow === undefined || u.y + 1 >= model.height) return null;
    const s = { x: u.x, y: u.y + 1 };
    const place = southArrowPlace(heightAt(model, u), heightAt(model, s), model.units.some((o) => o.x === s.x && o.y === s.y && !o.downed));
    arrow.y = -place.lift;
    return place.layer === "top" ? this.arrowTop : null;
  }

  /**
   * 6F-22（美術 PM 11-06）：被南邊高台擋住（`occluded`）的單位，HUD 改畫在高台之上（`hudTop`）；身體照舊被擋、畫剪影。
   * 6F-22b（美術 PM 6F-22 檢查第 2 節第 1 題）：屋頂蓋住屋後的人（`roofCovers`，同樣畫剪影）比照。
   */
  private hudLayerOf(model: DrawModel, u: UnitDraw): RenderLayer | null {
    // PB-1e（美術移植需求 3.4）：有部位的頭目南邊那格站著人時，整組 HUD 一起改掛最上層（部位小格才不被那個人的頭蓋住）
    if (u.partHudUp === true) return this.hudTop;
    return occluded(model, u) || roofCovers(model.scenery, u) ? this.hudTop : null;
  }

  /** PB-1e：頭目 HUD 改掛最上層時，朝南三角形（已縮小，`facingArrowPoly`）也一起；要在 `attachMarks`、`attachHud` 之後呼叫。 */
  private attachPartHud(u: UnitDraw, sprite: Container): void {
    if (u.partHudUp !== true) return;
    for (const n of sprite.children) if (n.label === SOUTH_ARROW_LABEL && n.parentRenderLayer !== this.hudTop) this.hudTop.attach(n);
  }

  protected resetSouthArrow(sprite: Container): void {
    const arrow = sprite.children.find((n) => n.label === SOUTH_ARROW_LABEL);
    if (arrow !== undefined) arrow.y = 0;
  }

  /** 一個單位：畫在所在排（剪影、外框在全部單位畫完後由 `OcclusionLayer.drawOcclusion` 決定）。 */
  protected drawUnit(model: DrawModel, u0: UnitDraw): void {
    const fx = this.partFxOf.get(u0.id); // PB-1e：破壞演出中重畫場景，照演出那一格畫
    const u = fx === undefined || u0.parts === undefined ? u0 : { ...u0, partFx: fx };
    const faces = neighborFaces({ x: u.x, y: u.y, height: heightAt(model, u) }, model.units.map((o) => ({ x: o.x, y: o.y, height: heightAt(model, o), downed: o.downed }))); // 6F-13
    this.facesOf.set(u.id, faces);
    const sprite = buildUnitSprite(this.art, this.pulses, u, faces, { edge: mapEdgeOf(model, u) }); // 6F-16：地圖邊緣
    this.scaleUnitMarks(sprite); // 6F-9、6F-11
    this.holdBody(u.id, sprite); // 6R-F：這一輪畫到的人；沒畫到的（死掉、離場、換地圖）在 endFrame 放開
    // QK-9：頭目的環放大後伸進左右格，頭目排在同一排最前面（先畫），左右鄰居的腳不被環蓋住
    if (ringScale(u) > 1) this.rows.row(u.y).units.addChildAt(sprite, 0);
    else this.rows.row(u.y).units.addChild(sprite);
    this.rows.attachMarks(sprite, this.southArrowTop(model, u, sprite)); // 6F-13：徽章畫在「▲N」之上；6F-21b：朝南三角形
    this.rows.attachHud(sprite, this.hudLayerOf(model, u)); // 6F-22：被高台擋住時 HUD 畫在高台之上
    this.attachPartHud(u, sprite);
    this.place(sprite, u, u.x * T + T / 2, u.y * T + T / 2);
    if (!u.downed) {
      this.unitSprites.set(u.id, sprite);
      this.unitDrawOf.set(u.id, u);
    } else {
      // 6N-4：倒下的人只給倒下片段找（命中那一刻重畫後，片段要接在倒地圖示的新節點上播完）；待機、狀態、走路照舊不碰
      this.downedSprites.set(u.id, sprite);
      this.downedDrawOf.set(u.id, u);
    }
  }

  /** 6F-22：被南邊高台擋住、或屋頂蓋住（6B-ART1）的單位（只看地形）。 */
  protected terrainOccluded(model: DrawModel, u: UnitDraw): boolean {
    return occluded(model, u) || roofCovers(model.scenery, u);
  }

  /** 6F-22 舊剪影（虛線人形）：OCL-1a 起在算完新外框之後才決定畫不畫（`legacySilhouetteWanted`，D5）。 */
  protected drawLegacySilhouette(u: UnitDraw): void {
    const c = this.center(u);
    const ring = u.summon ? RING.summon : RING[u.team];
    const outline = silhouette(c.x, c.y + T * 0.23, ring.stroke, T);
    this.silhouettes.addChild(outline);
    this.silhouetteOf.set(u.id, outline);
  }

  /** 一格片段畫面套到小人：骨架姿勢、離地高度、往面向方向的位移（南北向只走一半，有透視）。 */
  protected poseClip(unitId: string, sprite: Container, f: ClipFrame): void {
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
  protected spinBody(sprite: Container, angle: number): void {
    const h = 16 * DOLL_PX;
    for (const node of bodyNodes(sprite)) {
      node.rotation = angle;
      node.x += -h * Math.sin(angle);
      node.y += h * Math.cos(angle) - h;
    }
  }

  // ---- CB-3：鳥走完緊接攻擊時留在空中 ------------------------------------------
  /** 留在空中的鳥（一次最多一隻：走完的那一步到緊接的攻擊之間）；`until`＝效果時鐘的期限（保險：攻擊沒有來就落地）。 */
  private aloft: { unitId: string; until: number } | null = null;

  /** 飛行姿勢（移動片段的第 0 格，沒有落地內插）。 */
  private poseAloft(unitId: string, sprite: Container): void {
    this.poseBody(unitId, sprite, { creature: { clip: "move", u: 0 } });
  }

  /** 走完不落地：只有待機落地的鳥才留；待機停著（`hold` 不放），回傳有沒有留。 */
  protected keepAloft(unitId: string, sprite: Container): boolean {
    const draw = this.unitDrawOf.get(unitId);
    const cr = draw === undefined ? null : creatureOf(draw);
    if (cr === null || !creaturePerches(cr) || sprite.destroyed) return false;
    this.poseAloft(unitId, sprite);
    this.aloft = { unitId, until: this.effectClock + ALOFT_MAX_MS };
    return true;
  }

  /** 出招列開始接手這隻鳥：放掉留空時佔著的待機鎖（出招列自己另有一個）。 */
  protected takeOverAloft(unitId: string): void {
    if (this.aloft?.unitId !== unitId) return;
    this.aloft = null;
    this.idle.release(unitId);
  }

  /** 落地（回到站好）：別的動畫開始了、或等不到攻擊。`keep` 裡的單位不動（緊接的攻擊就是它的）。 */
  protected landAloft(keep?: ReadonlySet<string>): void {
    const a = this.aloft;
    if (a === null || keep?.has(a.unitId) === true) return;
    this.aloft = null;
    const sprite = this.unitSprites.get(a.unitId);
    if (sprite !== undefined && !sprite.destroyed) this.restBody(a.unitId, sprite);
    this.idle.release(a.unitId);
  }

  /** 重畫場景後（小人都重建了）：還在空中的鳥換回飛行姿勢；不在場上了就放掉。 */
  protected reposeAloft(): void {
    const a = this.aloft;
    if (a === null) return;
    const sprite = this.unitSprites.get(a.unitId);
    if (sprite === undefined || sprite.destroyed) {
      this.aloft = null;
      this.idle.release(a.unitId);
    } else this.poseAloft(a.unitId, sprite);
  }

  // ---- 待機、進出門（6M-4）----------------------------------------------------

  /** 每幀推進待機：站著的人呼吸、偶爾換小動作的貼圖。 */
  protected tickIdle(dt: number): void {
    if (this.aloft !== null && this.effectClock > this.aloft.until) this.landAloft();
    this.idle.tick(
      dt,
      this.unitSprites,
      this.unitDrawOf,
      (id, sprite, pose, facing) => this.idlePose(id, sprite, pose, facing),
      (id, sprite, pose) => (pose === null ? this.restBody(id, sprite) : this.poseBody(id, sprite, { creature: pose })), // QK-4：異形待機
    );
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
  protected setBodyTexture(unitId: string, node: Sprite, tex: Texture): void {
    node.texture = tex;
    this.art.holdFor(unitId, tex);
  }

  /** 小人換姿勢（6M-3）：紙娃娃、異形換成這一格的貼圖（形態、召喚物沒有骨架，不換）；`air` ＝ 跳躍離地高度（只抬小人，底圈不動）。 */
  protected poseBody(unitId: string, sprite: Container, frame: BodyFrame, air = 0): void {
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
  protected markProne(unitId: string): void {
    const draw = this.unitDrawOf.get(unitId);
    if (draw === undefined || isProne(draw)) return;
    this.unitDrawOf.set(unitId, { ...draw, statusIds: [...(draw.statusIds ?? []), PRONE] });
  }

  /** 走完：小人回到站好（倒地狀態＝躺著）的貼圖與位置（之後的 `view` 會再以結果重畫）。 */
  protected restBody(unitId: string, sprite: Container): void {
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

  /** 小人身體目前的貼圖釘在 LRU（owner ＝ 單位 ID；6R-F）。 */
  private holdBody(unitId: string, sprite: Container): void {
    const body = bodyNodes(sprite).find((n) => n.label === BODY_LABEL);
    this.art.holdFor(unitId, body?.texture ?? null);
  }

  /** 轉身：用新的朝向重建小人，放在原位與原圖層（重畫場景時再以 `view` 為準）。 */
  protected turn(unitId: string, old: Container, facing: Facing): Container {
    const draw = this.unitDrawOf.get(unitId);
    if (draw === undefined || old.destroyed) return old;
    const next = { ...draw, facing };
    const fresh = buildUnitSprite(this.art, this.pulses, next, this.facesOf.get(unitId) ?? [], { edge: this.model === null ? NO_EDGE : mapEdgeOf(this.model, next) });
    this.scaleUnitMarks(fresh); // 6F-9、6F-11
    this.holdBody(unitId, fresh); // 6R-F：兩次重畫之間新畫的朝向也要釘住，不然會被淘汰銷毀
    fresh.position.copyFrom(old.position);
    const parent = old.parent;
    if (parent !== null) parent.addChildAt(fresh, parent.getChildIndex(old));
    this.rows.attachMarks(fresh, this.model === null ? null : this.southArrowTop(this.model, next, fresh));
    this.rows.attachHud(fresh, this.model === null ? null : this.hudLayerOf(this.model, next));
    this.attachPartHud(next, fresh);
    old.destroy({ children: true });
    this.unitSprites.set(unitId, fresh);
    this.unitDrawOf.set(unitId, next);
    return fresh;
  }

  // ---- PB-1e：頭目部位（破壞演出蓋過的樣子、選單滑過的亮起與淡化）---------------------------

  /** 破壞演出中蓋過的樣子（單位 ID → 這一格）；重畫場景時 `drawUnit` 照它畫。 */
  protected readonly partFxOf = new Map<string, PartFx>();

  /**
   * 破壞演出換格（`resultEffects` 的 `part_break`）：人物（部位白閃、裂紋、斷了）、頭頂小格、地上的掉落物照這一格。
   * 有片段在播（受擊）時片段下一格自己換貼圖；沒有時直接換站好的貼圖。`null`＝回到伺服器給的樣子。
   */
  protected setPartFx(unitId: string, fx: PartFx | null): void {
    if (fx === null) this.partFxOf.delete(unitId);
    else this.partFxOf.set(unitId, fx);
    const draw = this.unitDrawOf.get(unitId);
    if (draw === undefined || draw.parts === undefined) return;
    const { partFx: _old, ...rest } = draw;
    const next: UnitDraw = fx === null ? rest : { ...rest, partFx: fx };
    this.unitDrawOf.set(unitId, next);
    const sprite = this.unitSprites.get(unitId);
    if (sprite === undefined || sprite.destroyed) return;
    this.rebuildPartNodes(sprite, next);
    if (!this.idle.isHeld(unitId)) this.restBody(unitId, sprite);
  }

  /** 頭頂部位小格、地上的掉落物換成 `u` 的樣子（同一個單位節點、同一層）。 */
  private rebuildPartNodes(sprite: Container, u: UnitDraw): void {
    const fresh = buildUnitSprite(this.art, this.pulses, u, this.facesOf.get(u.id) ?? [], { edge: this.model === null ? NO_EDGE : mapEdgeOf(this.model, u) });
    for (const label of [PART_STRIP_LABEL, PART_DEBRIS_LABEL]) {
      const old = sprite.children.find((n) => n.label === label);
      const now = fresh.children.find((n) => n.label === label);
      const layer = old?.parentRenderLayer ?? sprite.children.find((n) => n.label === HP_BAR_LABEL)?.parentRenderLayer ?? null;
      const body = sprite.children.findIndex((n) => n.label === BODY_LABEL);
      const at = old !== undefined ? sprite.getChildIndex(old) : label === PART_DEBRIS_LABEL ? Math.max(0, body) : sprite.children.length;
      if (old !== undefined) old.destroy({ children: true });
      if (now === undefined) continue;
      sprite.addChildAt(now, Math.min(at, sprite.children.length));
      if (label === PART_STRIP_LABEL) {
        if (layer !== null) layer.attach(now);
        this.scaleMark(now);
      }
    }
    fresh.destroy({ children: true });
  }

  /** 選部位小選單：哪個頭目、滑過哪個部位（`null`＝本體或沒滑過）。 */
  private partFocus: { unitId: string; part: string | null } | null = null;
  /** 目前畫上去的亮起與淡化（換焦點、重畫場景時先拿掉）。 */
  private focusNodes: { glow: Sprite | null; dimmed: Container[] } = { glow: null, dimmed: [] };

  /**
   * PB-1e（美術移植需求 3.5）：選單打開時頭目的狀態列（含「+N」）與蓄力徽章淡到 40%；滑過某個部位時那個部位亮起。
   * `unitId` ＝ `null` ＝選單關了。HP 條、護盾條、部位條不淡。
   */
  setPartFocus(unitId: string | null, part: string | null): void {
    this.partFocus = unitId === null ? null : { unitId, part };
    this.applyPartFocus();
  }

  /** 照目前的焦點畫亮起與淡化（重畫場景後 `BattleRenderer.draw` 再呼叫一次）。 */
  protected applyPartFocus(): void {
    const prev = this.focusNodes;
    if (prev.glow !== null && !prev.glow.destroyed) prev.glow.destroy();
    for (const n of prev.dimmed) if (!n.destroyed) n.alpha = 1;
    this.focusNodes = { glow: null, dimmed: [] };
    const f = this.partFocus;
    if (f === null) return;
    const sprite = this.unitSprites.get(f.unitId);
    const draw = this.unitDrawOf.get(f.unitId);
    if (sprite === undefined || sprite.destroyed || draw === undefined) return;
    const dimmed = sprite.children.filter((n) => n.label === STATUS_ROW_LABEL || n.label === CHARGE_BADGE_LABEL);
    for (const n of dimmed) n.alpha = PART_MENU_DIM;
    this.focusNodes = { glow: this.partGlow(sprite, draw, f.part), dimmed };
  }

  /** 滑過的部位亮起（貼在身體之上、同一個位置與大小）；本體、破了、畫不出來時不畫。 */
  private partGlow(sprite: Container, u: UnitDraw, part: string | null): Sprite | null {
    if (part === null || u.downed || !(u.parts ?? []).some((p) => p.id === part && !p.broken)) return null;
    const spec = specOfUnit(u);
    const k = dollPx(u);
    const res = this.art.figureRes(k);
    const tex = this.art.canvas(`pglow|${res}|${part}|${dollKey(spec, u.facing, false)}|${k.toFixed(3)}`, () => partGlowCanvas(spec, u.facing, part, res, k));
    if (tex === null) return null;
    const glow = new Sprite(tex);
    glow.label = PART_GLOW_LABEL;
    glow.anchor.set(0.5, DOLL_FOOT_Y / DOLL_H);
    glow.width = DOLL_W * k;
    glow.height = DOLL_H * k;
    glow.position.set(0, FEET);
    const body = sprite.children.findIndex((n) => n.label === BODY_LABEL);
    sprite.addChildAt(glow, body < 0 ? sprite.children.length : body + 1);
    return glow;
  }
}
