// 單位圖層（R1e 自 `BattleRenderer.ts` 拆出，純搬移）：畫單位與剪影、HUD 掛載（`hudTop`、朝南三角形）、連心虛線、
// 換姿勢（`poseBody`／`restBody`）、待機、轉身。
import { Container, Graphics, RenderLayer, Sprite, type Texture } from "pixi.js";
import type { DrawModel, UnitDraw } from "../../battle/drawModel";
import { TILE_SIZE } from "../../battle/geometry";
import { heightAt, occluded } from "../../battle/elevation";
import { RING } from "../artPalette";
import { silhouette } from "../heightArt";
import { southArrowPlace } from "../rowLayers";
import { SOUTH_ARROW_LABEL } from "../minMark";
import { neighborFaces } from "../badgeLayout";
import { mapEdgeOf, NO_EDGE } from "../rowLayout";
import { BODY_LABEL, bodyNodes, bodyTexture, buildUnitSprite, isLinked, isProne, placeCreatureBody, PRONE, ringScale, type BodyFrame } from "../unitSprite";
import { roofCovers } from "../sceneryModel";
import type { InkPose } from "../inkPose";
import { LINK_COLOR } from "../inkCreature";
import { linkPairs } from "../linkLines";
import { knockOffset, proneBody } from "../motionClips";
import { FEET } from "../unitSprite";
import type { ClipFrame } from "../skillClips";
import type { Facing } from "../../api/types";
import { HighlightLayer } from "./highlightLayer";
import { DOLL_PX } from "./rendererBase";

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
    return occluded(model, u) || roofCovers(model.scenery, u) ? this.hudTop : null;
  }

  protected resetSouthArrow(sprite: Container): void {
    const arrow = sprite.children.find((n) => n.label === SOUTH_ARROW_LABEL);
    if (arrow !== undefined) arrow.y = 0;
  }

  /** 一個單位：畫在所在排；被南邊高格擋住時另在最上層畫剪影。 */
  protected drawUnit(model: DrawModel, u: UnitDraw): void {
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

  // ---- 待機、進出門（6M-4）----------------------------------------------------

  /** 每幀推進待機：站著的人呼吸、偶爾換小動作的貼圖。 */
  protected tickIdle(dt: number): void {
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
    old.destroy({ children: true });
    this.unitSprites.set(unitId, fresh);
    this.unitDrawOf.set(unitId, next);
    return fresh;
  }
}
