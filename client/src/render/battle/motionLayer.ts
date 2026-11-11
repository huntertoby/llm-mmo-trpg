// 移動動畫（R1e 自 `BattleRenderer.ts` 拆出，純搬移）：位移與身體片段、逐格走路與停頓、進出門、鏡頭跟隨、補間。
import { Container, Sprite, type Ticker } from "pixi.js";
import type { Pos } from "../../api/types";
import { lerpPos, rowDuringMove, type MoveAnim, type MoveStyle } from "../../battle/animation";
import { TILE_SIZE } from "../../battle/geometry";
import { tileLift } from "../../battle/elevation";
import { warpPlan } from "../../battle/vfx";
import { creatureReact, reactFrame } from "../reactClips";
import { warpEffects, type Effect } from "../vfxEffects";
import { BODY_LABEL, bodyNodes, creatureOf, hasSkeleton } from "../unitSprite";
import { arriveFrame, doorOpenness, leaveFrame, type DoorMotion, type TransitFrame, type TransitKind } from "../doorClips";
import { creatureStrikePose, perchAt, PERCH_MS } from "../creaturePose";
import { cameraNudge, facingOf, type Gait, type WalkAnim, type WalkBeat } from "../../battle/walkAnim";
import { DUST_FROM, gaitPose, knockOffset, leapAirScale, legFrame, proneBody, skidBody, stumbleTilt, tilePhase } from "../motionClips";
import { beatEffects, landingDust } from "../walkFx";
import { FEET } from "../unitSprite";
import { clipDef, clipFrame } from "../skillClips";
import { leapShape, routeOffset, ZIGZAG_CORNERS } from "../skillVariants";
import { cueEffect } from "../skillFx";
import type { Facing } from "../../api/types";
import { FeedbackLayer } from "./feedbackLayer";
import { DOLL_PX } from "./rendererBase";

const T = TILE_SIZE;

export abstract class MotionLayer extends FeedbackLayer {
  /**
   * 依序播放移動動畫；`skip()` 為真時剩下的移動直接跳到終點。
   * 6M-3：步行（探索的主角、NPC 逐格走）用走路片段、衝鋒（`dash`）用跑步片段，腳步隨格子高低差走上去或跳上去；
   * 水平照舊等速（探索的鏡頭用同樣的時間等速平移）。其他位移照舊整個小人滑動或淡出淡入。
   */
  async animate(plan: readonly MoveAnim[], skip: () => boolean): Promise<void> {
    if (!this.ready) return;
    this.landAloft();
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
      if (!s.destroyed && s.parent !== units) {
        units.addChild(s);
        this.rows.attachMarks(s);
        this.resetSouthArrow(s); // 6F-21b：移動途中照 6F-21（南邊一排的 under、不抬高），停下重畫時再算
      }
    };
    if (m.durationMs <= 0 || skip()) {
      sprite.position.set(to.x, to.y);
      toRow(sprite)(1);
      return;
    }
    if (m.creatureBlink === true && !this.reduced) {
      await this.creatureBlinkMove(m, sprite, skip, toRow);
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

  /** CB-2b：異形的傳送播閃現片段：前半在原地淡出、片段完全透明的中段換格、後半在新格淡入（和傳送特效同一個時間軸，落地後不再多閃一次）。 */
  private async creatureBlinkMove(m: MoveAnim, sprite: Container, skip: () => boolean, toRow: (s: Container) => (t: number) => void): Promise<void> {
    const from = this.center(m.from);
    const to = this.center(m.to);
    this.launch(warpEffects(warpPlan(m), this.effectClock, (p) => this.center(p)));
    const frame = (t: number) => {
      if (sprite.destroyed) return;
      const there = t >= 0.5;
      sprite.position.set(there ? to.x : from.x, there ? to.y : from.y);
      toRow(sprite)(there ? 1 : 0);
      this.poseBody(m.unitId, sprite, { creature: creatureStrikePose("blink", t) });
    };
    frame(0);
    await this.during(m.durationMs, skip, frame);
    if (sprite.destroyed) return;
    sprite.position.set(to.x, to.y);
    toRow(sprite)(1);
    this.restBody(m.unitId, sprite);
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
      // 6R-1c：跳上、跳下高低差時，最高點從起點、落點中較高的一端往上量（沿用高低差跳躍的弧度）
      const lift = clip === "leap_air" ? leapAirScale(this.heightOf(m.from), this.heightOf(m.to), (clipDef(clip).air ?? 0) * DOLL_PX) : 1;
      const frame = (t: number) => {
        const raw = clipFrame(clip, t);
        const f = lift === 1 ? raw : { ...raw, air: raw.air * lift };
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
    opt: { gait: Gait; tile: number; linear?: boolean; onRow?: (t: number) => void; around?: { before: number; after: number } },
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
      // QK-4b：鳥起飛／落地過場（整段移動的開頭、結尾約 4 格；其他異形在 bodyTexture 忽略）
      const ar = opt.around ?? { before: 0, after: 0 };
      const perch = perchAt(ar.before + u * durationMs, ar.after + (1 - u) * durationMs);
      this.poseBody(unitId, sprite, { pose: f.pose, creature: perch > 0 ? { ...f.creature, perch } : f.creature }, f.air);
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

  /**
   * 一格一格走（6A-4d）：每格緩入緩出、轉彎時轉身；踩到特殊地表時在那一格停頓並播效果（冰花、滑倒、
   * 陷阱夾住、冒火、濺油），停頓結束才跳傷害數字與狀態圖示；倒在友軍格時短短滑回空格。鏡頭稍微跟著走路的人。
   * `skip()` 為真時直接跳到終點。6M-3：每格播走路（衝刺過的人播跑步）片段，照高低差走上去或跳上去；
   * 滑倒時只有小人倒下（底圈、血條不動），之後倒地狀態持續躺著（重畫時 `unitSprite` 照同一個姿勢畫）。
   */
  async animateWalk(walk: WalkAnim, skip: () => boolean): Promise<void> {
    if (!this.ready) return;
    this.landAloft();
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
      if (!s.destroyed && s.parent !== layer) {
        layer.addChild(s);
        this.rows.attachMarks(s);
        this.resetSouthArrow(s);
      }
      if (!s.destroyed) this.follow(s.position);
    };
    let last: Pos | null = null;
    let tile = 0;
    let legBefore = 0;
    let legAfter = walk.pieces.reduce((a, p) => a + (p.kind === "leg" ? p.durationMs : 0), 0);
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
          legAfter -= piece.durationMs;
          // CB-3：`aloft`＝走完不落地（結尾沒有落地過場）
          await this.stepLeg(walk.unitId, sprite, piece.from, piece.to, piece.durationMs, skip, { gait, tile, onRow: track(sprite, piece.from, piece.to), around: { before: legBefore, after: walk.aloft === true && !this.reduced ? PERCH_MS * 9 : legAfter } });
          legBefore += piece.durationMs;
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
      // CB-3：鳥走完緊接攻擊：留在空中（待機照舊停著），由下一步的出招列接手
      const stays = walk.aloft === true && !lying && !skip() && !this.reduced && this.keepAloft(walk.unitId, sprite);
      if (stays) {
        this.follow(null);
        return;
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
}
