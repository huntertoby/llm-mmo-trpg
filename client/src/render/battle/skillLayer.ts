// 技能的身體片段（R1e 自 `BattleRenderer.ts` 拆出，純搬移）：施放者轉向、起手到收勢的時間軸、作用端位置、片段特效提示。
import { Container, Sprite } from "pixi.js";
import { TILE_SIZE } from "../../battle/geometry";
import type { Effect } from "../vfxEffects";
import { bodyNodes, creatureFieldScale, creatureOf, creatureOffsetPx, creatureSide, hasSkeleton, isProne } from "../unitSprite";
import type { InkPose } from "../inkPose";
import type { Facing, Pos } from "../../api/types";
import { CREATURE_CLIPS, creatureAttackTypeOf, creatureStrikePose, perchRowPose, quantizeCreaturePose, type CreaturePose } from "../creaturePose";
import { CREATURE_FX_BOX, creatureMouth } from "../inkCreature";
import { creatureFxAnchorPx, creatureFxTurnOf } from "../creatureFxTurn";
import { DOLL_SCALE } from "../paperdoll";
import { EGG_FROM_U, EGG_START, eggColors } from "../qCreatureAnim";
import { creatureFacingTo, facingOf } from "../../battle/walkAnim";
import { HUMAN_HIT_MS, humanHit, knockOffset, proneBody } from "../motionClips";
import { FEET, gripOf } from "../unitSprite";
import type { SkillRow } from "../../battle/skillSequence";
import { dollSkin } from "../inkStyle";
import { qWeaponLen } from "../qSpec";
import { fbFrameAt, fbKindIndex, fbKindOfIndex, fbTimeOf, fbTip, qKeyAttackPose } from "../qAnimFB";
import type { QItem } from "../qCore";
import { anchorPoint, clipDef, clipFrame, clipHitFrame, recoverFrame, weaponClassOf, type Anchor, type ClipFrame, type FxCue, type WeaponClass } from "../skillClips";
import { attackFamilyOf, type AttackFamily } from "../attackVariants";
import { cueEffect } from "../skillFx";
import { weaponFrame } from "../inkWeaponFrame";
import { eggArcEffect, eggArcPlan } from "../eggArc";
import { MotionLayer } from "./motionLayer";
import { DOLL_PX } from "./rendererBase";
import { battleTrace } from "./devTrace";

const T = TILE_SIZE;

export abstract class SkillLayer extends MotionLayer {
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

  /** QK-4b：異形的出手點（嘴；頭目＝灰燼之心的核心、碎晶之主的手晶）在畫面上的位置；不是異形 → null。 */
  private creatureMouthWorld(unitId: string): { x: number; y: number } | null {
    const sprite = this.unitSprites.get(unitId);
    const draw = this.unitDrawOf.get(unitId);
    if (sprite === undefined || sprite.destroyed || draw === undefined) return null;
    const cr = creatureOf(draw);
    if (cr === null) return null;
    const [mx, my] = creatureMouth(cr);
    const o = creatureOffsetPx(draw, cr, { dx: mx, dy: my });
    return { x: sprite.x + o.x, y: sprite.y + FEET + o.y };
  }

  /** CB-2c：蛋從產卵片段拿出來，照拋物線飛到孵化格（`hitMs` 落地，同一刻畫面更新出幼體）；不是異形 → null。 */
  private eggEffect(r: SkillRow, to: Pos, hitMs: number, now: number): Effect | null {
    const sprite = this.unitSprites.get(r.unitId);
    const draw = this.unitDrawOf.get(r.unitId);
    if (sprite === undefined || sprite.destroyed || draw === undefined) return null;
    const cr = creatureOf(draw);
    if (cr === null) return null;
    const side = { ...draw, facing: creatureFacingTo({ x: draw.x, y: draw.y }, to, draw.facing) }; // CB-3：正南、正北不翻面，蛋從實際畫出來的那一面的身後出發
    const unit = creatureOffsetPx(side, cr, { dy: 1 }).y; // 異形座標 → 模型像素
    const start = creatureOffsetPx(side, cr, { dx: EGG_START[0], dy: EGG_START[1] });
    const land = this.center(to);
    const plan = eggArcPlan({ from: { x: sprite.x + start.x, y: sprite.y + FEET + start.y }, to: { x: land.x, y: land.y + FEET }, startMs: now + r.startMs + r.ms * EGG_FROM_U, landMs: now + hitMs, endMs: now + r.startMs + r.ms, unit });
    return eggArcEffect(plan, eggColors(cr.element));
  }

  /** 片段起點在畫面上的位置（紙娃娃座標 → 模型像素；作用端照武器的長度）。 */
  private anchorWorld(unitId: string, f: ClipFrame, anchor: Anchor): { x: number; y: number } | null {
    const sprite = this.unitSprites.get(unitId);
    const draw = this.unitDrawOf.get(unitId);
    if (sprite === undefined || sprite.destroyed || draw === undefined) return null;
    const grip = gripOf(draw);
    const main = grip?.main;
    const len = anchor === "tip" && main !== undefined ? (dollSkin() === "q" ? qWeaponLen(main) : (weaponFrame(main, { side: draw.facing === "east" || draw.facing === "west" })?.len ?? 0)) : 0;
    const fbk = fbKindOfIndex(f.pose.fbk ?? 0);
    const view = draw.facing === "south" ? "front" : "back";
    const a =
      fbk !== null && (draw.facing === "south" || draw.facing === "north")
        ? (() => {
            // QK-5：正面、背面五類出招的作用端（槍尖、杖頭、劍尖、拳頭；弓從胸前／頭頂上方放出）
            const fr = fbFrameAt(fbk, view, f.pose.fbt ?? 0);
            const p = fbTip(fbk, view, fr, main as QItem | undefined);
            return { x: p[0], y: p[1] + (fr.bob ?? 0) };
          })()
        : anchorPoint(f.pose, anchor, draw.facing, len);
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
    this.landAloft(new Set(rows.map((r) => r.unitId))); // CB-3：在空中等的鳥不在這一招裡 → 落地
    const turned = new Set<string>();
    for (const r of rows) {
      if (turned.has(r.unitId) || r.clip === "knocked_down" || r.target === null) continue;
      turned.add(r.unitId);
      const draw = this.unitDrawOf.get(r.unitId);
      const sprite = this.unitSprites.get(r.unitId);
      if (draw === undefined || sprite === undefined || (draw.x === r.target.x && draw.y === r.target.y)) continue;
      // CB-3：異形只有左右兩面：目標在正南、正北時出招期間維持原本的左右面（不轉向南北，免得敵方異形被畫成朝西又翻回來）
      const facing = creatureOf(draw) !== null ? creatureFacingTo({ x: draw.x, y: draw.y }, r.target, draw.facing) : facingOf({ x: draw.x, y: draw.y }, r.target, draw.facing);
      if (facing !== draw.facing) this.turn(r.unitId, sprite, facing);
    }
    const effects: Effect[] = [];
    for (const r of rows) {
      // CB-3b：開發用紀錄（這一招排了哪些片段）
      battleTrace(() => ({ kind: "row", clock: now, unit: r.unitId, template: this.unitDrawOf.get(r.unitId)?.template ?? "", pos: ((d) => (d === undefined ? null : { x: d.x, y: d.y }))(this.unitDrawOf.get(r.unitId)), target: r.target, clip: r.clip, startMs: r.startMs, ms: r.ms, hitMs: r.hitMs, strike: r.strike, recover: r.recover, action: r.creature?.action ?? null, frames: r.creature?.frames ?? null, perch: r.perch ?? null }));
      if (!r.still) effects.push(this.rowEffect(r, now));
      if (!r.recover) effects.push(...this.rowCues(r, now));
      if (r.eggTo !== undefined && r.hitMs !== null) {
        const egg = this.eggEffect(r, r.eggTo, r.hitMs, now);
        if (egg !== null) effects.push(egg);
      }
      if (r.strike && r.hitMs !== null) {
        // QK-4b：異形、頭目的飛行物、射線從嘴（頭目：核心、手晶）發出
        const mouth = this.creatureMouthWorld(r.unitId);
        if (mouth !== null) {
          origins.set(r.cast, mouth);
          continue;
        }
        const def = clipDef(r.clip);
        const hf = clipHitFrame(r.clip);
        const fbHit = this.fbPoseOf(r, r.fb?.hitAt ?? 0.5);
        const o = this.anchorWorld(r.unitId, fbHit === null ? hf : { ...hf, pose: fbHit }, def.anchor);
        if (o !== null) origins.set(r.cast, o);
      }
    }
    this.launch(effects);
    return origins;
  }

  private rowFrame(r: SkillRow, t: number): ClipFrame {
    const base = r.recover ? recoverFrame(r.clip, t) : clipFrame(r.clip, t);
    const fb = this.fbPoseOf(r, t) ?? this.keyPoseOf(r, t, base.pose);
    return fb === null ? base : { ...base, pose: fb };
  }

  /** QK-5：朝南、朝北的 Q 版人形，五類出招改播正面、背面的關鍵幀（qAnimFB）；其他照片段。 */
  private fbPoseOf(r: SkillRow, t: number): InkPose | null {
    if (r.fb === undefined || r.fb.kind === null || dollSkin() !== "q") return null;
    const draw = this.unitDrawOf.get(r.unitId);
    if (draw === undefined || !hasSkeleton(draw) || (draw.facing !== "south" && draw.facing !== "north")) return null;
    const fbt = fbTimeOf(r.fb, t);
    return fbt === null ? null : { fbk: fbKindIndex(r.fb.kind), fbt };
  }

  /** QK-5：側面的雙手劍、長柄、弩、火槍出招接 Q 版關鍵姿勢 atk，弓接 bowAim（qDoll 的 KEY）；其他照片段。 */
  private keyPoseOf(r: SkillRow, t: number, base: InkPose): InkPose | null {
    if (r.fb === undefined || dollSkin() !== "q") return null;
    const draw = this.unitDrawOf.get(r.unitId);
    if (draw === undefined || !hasSkeleton(draw) || (draw.facing !== "east" && draw.facing !== "west")) return null;
    const main = gripOf(draw)?.main;
    return qKeyAttackPose(main?.kind, r.fb, t, base);
  }

  private rowEffect(r: SkillRow, now: number): Effect {
    let held = false;
    let restoreFacing: Facing | null = null;
    const current = () => {
      const s = this.unitSprites.get(r.unitId);
      return s === undefined || s.destroyed ? null : s;
    };
    const fxNode = new Container(); // CB-3c：轉向後的片段特效（在效果圖層，蓋在目標之上；這一列結束時跟著移除）
    return {
      node: fxNode,
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
          this.takeOverAloft(r.unitId); // CB-3：還在空中的鳥由這一列接手（不先落地）
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
        else if ((r.strike || r.perch !== undefined) && creatureOf(draw) !== null) {
          // CB-2c：起飛、落地過場（減少動態時 `playbackPlan` 不排這兩列；這裡是保險）
          if (r.perch !== undefined && this.reduced) return;
          // CB-2b：命中時重畫會把朝向換回規則的朝向（施放技能不轉身）：片段播完前維持面向東西向的目標，噴口才不會翻到背後
          let body = s;
          const side = r.target === null ? draw.facing : creatureFacingTo({ x: draw.x, y: draw.y }, r.target, draw.facing);
          if (side !== draw.facing) {
            restoreFacing = draw.facing;
            body = this.turn(r.unitId, s, side);
          }
          // QK-4：依技能的動作類型挑這款身形的攻擊片段（普攻、衝鋒、吐息、遠程、範圍、召喚、位移）
          const dist = r.target === null ? null : Math.max(Math.abs(r.target.x - draw.x), Math.abs(r.target.y - draw.y));
          const action = r.creature?.action ?? creatureAttackTypeOf(r.clip, dist);
          const pose = r.perch !== undefined ? perchRowPose(r.perch, action, t) : creatureStrikePose(action, t, r.creature?.frames);
          // CB-3c：目標在正南／正北（同一欄）時，片段自帶的特效另畫在目標那一格（頭目照舊）
          const fxTurn = creatureOf(draw)?.boss === undefined && r.target !== null ? creatureFxTurnOf({ x: draw.x, y: draw.y }, r.target) : null;
          const full: CreaturePose = { ...pose, ...(r.ownFx === true ? { fxAll: true } : {}), ...(r.creature?.inPlace === true ? { inPlace: true } : {}), ...(fxTurn === null ? {} : { fxTurn }) };
          this.poseBody(r.unitId, body, { creature: full });
          this.placeTurnedFx(fxNode, r.unitId, full);
          // CB-3b：開發用紀錄（這一次重畫的格）
          battleTrace(() => ({ kind: "frame", clock: this.effectClock, unit: r.unitId, action, clip: pose.clip, u: pose.u, t, frame: r.creature?.frames === undefined ? null : Math.round((pose.u ?? 0) * (r.creature.frames.n - 1)) }));
        }
      },
      end: () => {
        let s = current();
        if (r.clip === "knocked_down") this.markProne(r.unitId);
        if (s !== null && restoreFacing !== null && this.unitDrawOf.get(r.unitId)?.facing !== restoreFacing) s = this.turn(r.unitId, s, restoreFacing);
        if (s !== null) this.restBody(r.unitId, s);
        if (held) this.idle.release(r.unitId);
        held = false;
        this.art.holdFor(`cfx:${r.unitId}`, null);
      },
    };
  }

  /**
   * CB-3c：同一欄（`pose.fxTurn`）時，片段這一格自帶的特效另畫一張，錨點（「相鄰目標」那一點）放在相鄰那一格的地面（跟著那一格抬高）；
   * 其他情況（東西向、斜向、頭目、這一格沒特效）藏起來，特效照舊畫在身體貼圖裡。
   */
  private placeTurnedFx(node: Container, unitId: string, pose: CreaturePose): void {
    let fx = node.children.find((n): n is Sprite => n instanceof Sprite);
    const draw = this.unitDrawOf.get(unitId);
    const sprite = this.unitSprites.get(unitId);
    const cr = draw === undefined ? null : creatureOf(draw);
    const turn = pose.fxTurn;
    const tex = turn === undefined || cr === null || draw === undefined || sprite === undefined ? null : this.art.creatureFx(cr, creatureSide(draw), pose);
    if (tex === null || turn === undefined || cr === null || draw === undefined || sprite === undefined) {
      if (fx !== undefined) fx.visible = false;
      return;
    }
    if (fx === undefined) {
      fx = new Sprite(tex);
      fx.anchor.set(0.5, CREATURE_FX_BOX.foot / CREATURE_FX_BOX.h);
      node.addChild(fx);
    } else if (fx.texture !== tex) fx.texture = tex;
    this.art.holdFor(`cfx:${unitId}`, tex);
    const field = creatureFieldScale(draw);
    const k = (T / 52) * DOLL_SCALE * field; // 同身體貼圖的縮放（unitSprite 的異形小人）
    fx.width = CREATURE_FX_BOX.w * k;
    fx.height = CREATURE_FX_BOX.h * k;
    fx.visible = true;
    const from = { x: draw.x, y: draw.y };
    const to = { x: draw.x, y: draw.y + turn };
    const a = creatureFxAnchorPx({ from, to, side: creatureSide(draw), size: cr.size, fieldScale: field, dollScale: DOLL_SCALE, tile: T });
    const lift = this.center(to).y - this.center(from).y - a.y; // 相鄰那一格比自己高或低時，跟著那一格抬高
    fx.position.set(sprite.x + a.x, sprite.y + FEET + a.y + lift);
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
}
