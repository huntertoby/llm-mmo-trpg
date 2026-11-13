// 技能特效、受擊與結果（R1e 自 `BattleRenderer.ts` 拆出，純搬移）：命中閃白與受擊片段、反應、特殊結果、勝利、地形升降。
import { Container } from "pixi.js";
import type { Pos } from "../../api/types";
import { TILE_SIZE } from "../../battle/geometry";
import { heightAt, liftedOrigin, tileLift, type HeightShift } from "../../battle/elevation";
import { VFX_TIMING, type StepVfx } from "../../battle/vfx";
import { dummyFlashEffect, reactEffects, type ReactHost } from "../reactEffects";
import { isTrainingDummy } from "../trainingDummy";
import { riseEffects, specialEffects, victoryEffects, type ResultHost } from "../resultEffects";
import { addFreeze } from "../hitStop";
import type { FrameVictory } from "../../battle/playback";
import { blastEffect, castEffects, hitEffects, impactShakeEffect, shakeEffect, type Effect } from "../vfxEffects";
import { LIFT_SHAKE_PX } from "../../battle/impact";
import { liftEffects } from "../heightArt";
import { BODY_LABEL, bodyNodes, bodyTexture, creatureOf, flashTexture, hasSkeleton, isProne, overlayFlashKind } from "../unitSprite";
import { clearFlash, overlayFlash } from "../silhouetteFlash";
import { CREATURE_CLIPS, CREATURE_HIT_FLASH, quantizeCreaturePose } from "../creaturePose";
import { HUMAN_HIT_FLASH, humanHit, knockOffset, quantizeFlash } from "../motionClips";
import { FEET } from "../unitSprite";
import { reduceVfx, REDUCED_FLASH_MS } from "../reducedMotion";
import { SkillLayer } from "./skillLayer";
import { DOLL_PX, type LiftState } from "./rendererBase";

const T = TILE_SIZE;
/** 減少動態時的白閃（6H-1）：開頭的強度（人形、異形、疊層都一樣），之後線性淡掉。 */
export const REDUCED_FLASH_PEAK = 0.85;

export abstract class VfxLayer extends SkillLayer {
  /** 受擊與結果（6N-4，`reactEffects.ts`）用的操作。 */
  private readonly reactHost: ReactHost = {
    art: this.art,
    sprite: (id) => {
      const s = this.unitSprites.get(id) ?? this.downedSprites.get(id);
      return s === undefined || s.destroyed ? null : s;
    },
    draw: (id) => this.unitDrawOf.get(id) ?? this.downedDrawOf.get(id),
    hold: (id, s) => this.idle.hold(id, s),
    release: (id) => this.idle.release(id),
    setTexture: (id, node, tex) => this.setBodyTexture(id, node, tex),
    restBody: (id, s) => {
      if (this.unitDrawOf.has(id)) {
        this.restBody(id, s);
        return;
      }
      // 倒下的人：回到倒地圖示（重畫時 `unitSprite` 畫的樣子）
      const draw = this.downedDrawOf.get(id);
      if (draw === undefined || s.destroyed) return;
      for (const node of bodyNodes(s)) {
        node.position.set(0, FEET);
        node.rotation = 0;
        if (node.label !== BODY_LABEL) continue;
        const tex = bodyTexture(this.art, draw, {});
        if (tex !== null) this.setBodyTexture(id, node, tex);
      }
    },
    // OCL-1b：受擊閃白交給被遮擋外框（k ＝ 白閃 ÷ 呼叫點傳的峰值）、倒下片段藏外框
    outline: { flash: (id, flash, peak) => this.flashOutline(id, flash, peak), hide: (id) => this.hideOutline(id) },
  };

  /** 特殊結果、復活、勝利（6N-5，`resultEffects.ts`）用的操作：受擊的操作再加地圖大小。 */
  private readonly resultHost: ResultHost = {
    ...this.reactHost,
    bounds: () => ({ w: (this.model?.width ?? 0) * T, h: (this.model?.height ?? 0) * T }),
  };

  /**
   * 我方勝利（6N-5）：站著的我方每人播舉手或收刀、地圖上方浮出「勝利」。不等待結束（呼叫端照 `v.ms` 等）。
   */
  playVictory(v: FrameVictory): void {
    if (!this.ready || v.ms <= 0) return;
    this.launch(victoryEffects(this.resultHost, v, this.effectClock));
  }

  /** 站在 `p` 的異形單位 ID；沒有為 `null`。 */
  private creatureAt(p: Pos): string | null {
    for (const [id, u] of this.unitDrawOf) if (u.x === p.x && u.y === p.y && creatureOf(u) !== null) return id;
    return null;
  }

  /**
   * 異形受擊（6M-2 的片段，6M-3 接上戰場）：`ms` 毫秒內播「受擊」片段——往後彈、仰、白閃只閃剪影（貼圖裡疊白色剪影）。
   * 每幀照單位 ID 找目前的小人（重畫場景後換成新的節點也跟得上）；結束時回到站好的貼圖。
   */
  private creatureHit(unitId: string, startMs: number, ms: number): Effect {
    const node = new Container();
    let held = false;
    const current = () => {
      const s = this.unitSprites.get(unitId);
      return s === undefined || s.destroyed ? null : s;
    };
    return {
      node,
      startMs,
      endMs: startMs + ms,
      motion: "body",
      update: (t) => {
        const s = current();
        if (s === null) return;
        if (!held) {
          held = true;
          this.idle.hold(unitId, s);
        }
        const pose = quantizeCreaturePose(CREATURE_CLIPS.hit.pose(t));
        this.poseBody(unitId, s, { creature: pose });
        this.flashOutline(unitId, pose.flash ?? 0, CREATURE_HIT_FLASH); // OCL-1b（Q6）：異形、頭目受擊的峰值 0.9
      },
      end: () => {
        const s = current();
        if (s !== null) this.restBody(unitId, s);
        this.flashOutline(unitId, 0, 1);
        if (held) this.idle.release(unitId);
        held = false;
      },
    };
  }

  /** 站在 `p`、有紙娃娃骨架、沒有倒地的人形單位 ID；沒有為 `null`。 */
  private dollAt(p: Pos): string | null {
    for (const [id, u] of this.unitDrawOf) if (u.x === p.x && u.y === p.y && hasSkeleton(u) && !isProne(u)) return id;
    return null;
  }

  /**
   * 人形受擊（6M-4）：`ms` 毫秒內播「受擊」片段——仰一下、往後彈、白閃只閃剪影（不含地上的影子、不整格變白）。
   * 和異形一樣每幀照單位 ID 找目前的小人；結束時回到站好的貼圖。
   */
  private dollHit(unitId: string, startMs: number, ms: number): Effect {
    let held = false;
    const current = () => {
      const s = this.unitSprites.get(unitId);
      return s === undefined || s.destroyed ? null : s;
    };
    return {
      node: new Container(),
      startMs,
      endMs: startMs + ms,
      motion: "body",
      update: (t) => {
        const s = current();
        if (s === null) return;
        if (!held) {
          held = true;
          this.idle.hold(unitId, s);
        }
        const h = humanHit(t);
        this.poseBody(unitId, s, { pose: h.pose, flash: h.flash });
        this.flashOutline(unitId, h.flash, HUMAN_HIT_FLASH); // OCL-1b（Q6）：人形受擊的峰值 0.85
        const off = knockOffset(this.unitDrawOf.get(unitId)?.facing ?? "south", h.knock * DOLL_PX);
        for (const node of bodyNodes(s)) node.position.set(off.x, FEET + off.y);
      },
      end: () => {
        const s = current();
        if (s !== null) this.restBody(unitId, s);
        this.flashOutline(unitId, 0, 1);
        if (held) this.idle.release(unitId);
        held = false;
      },
    };
  }

  /** PR-2c：靶場木樁（受擊只閃白 0.1 秒，`dummyFlashEffect`）。 */
  private isDummy(unitId: string): boolean {
    return isTrainingDummy(this.unitDrawOf.get(unitId));
  }

  /** 站在 `p`、受擊時疊白色剪影閃白的單位（形態、召喚物、倒地的人；6C-8）ID；沒有為 `null`。 */
  private overlayFlashAt(p: Pos): string | null {
    for (const [id, u] of this.unitDrawOf) if (u.x === p.x && u.y === p.y && overlayFlashKind(u) !== null) return id;
    return null;
  }

  /**
   * 形態、召喚物、倒地的人受擊（6C-8）：沒有骨架，不換姿勢，只在小人上疊一層白色剪影（同一張圖不含地上影子、轉白），
   * 不透明度照人形受擊片段的白閃（開頭 0.85、播到 1/4 消失）；不畫整片白圓、不整格變白。結束時拿掉。
   */
  private overlayHit(unitId: string, startMs: number, ms: number): Effect {
    const current = () => {
      const s = this.unitSprites.get(unitId);
      return s === undefined || s.destroyed ? null : s;
    };
    const owner = this.art.uniqueOwner(`flash:${unitId}`); // 6R-F：白閃疊層的貼圖也釘住
    return {
      node: new Container(),
      startMs,
      endMs: startMs + ms,
      motion: "body",
      update: (t) => {
        const s = current();
        const draw = this.unitDrawOf.get(unitId);
        if (s === null || draw === undefined) return;
        const body = bodyNodes(s).find((n) => n.label === BODY_LABEL);
        const tex = flashTexture(this.art, draw);
        if (body === undefined || tex === null) return;
        this.art.holdFor(owner, tex);
        overlayFlash(body, tex, humanHit(t).flash);
        this.flashOutline(unitId, humanHit(t).flash, HUMAN_HIT_FLASH); // OCL-1b（Q6）：疊層照人形受擊，峰值 0.85
      },
      end: () => {
        const s = current();
        if (s !== null) clearFlash(s);
        this.flashOutline(unitId, 0, 1);
        this.art.holdFor(owner, null);
      },
    };
  }

  /**
   * 播放一步的技能特效（Phase 3-12）：蓄力、飛行物或光束、命中爆發、受擊閃白與震動。不等待結束；
   * 描述內的時間已依播放速度縮放，`impactMs` 是命中後爆發的時間。`shake` 為假時不震動（版面設定）。
   */
  playVfx(raw: StepVfx, impactMs: number, shake: boolean, origins: ReadonlyMap<number, { x: number; y: number }> = new Map()): void {
    if (!this.ready || impactMs <= 0) return;
    const vfx = reduceVfx(raw, this.reduced); // 6R-F：減少動態時沒有停頓、沒有技能變體的特效層
    const now = this.effectClock;
    const effects: Effect[] = [];
    const auraHits = vfx.casts.some((c) => c.kind === "aura");
    const at = (p: Pos) => this.center(p);
    vfx.casts.forEach((cast, i) => {
      // 6N-1：飛行物、光束、扇形從出招那一刻的作用端（杖頭、劍尖、槍口、弓弦）發出，不從格子中心
      const o = origins.get(i);
      const from = o !== undefined && (cast.kind === "projectile" || cast.kind === "beam" || cast.kind === "cone") ? o : null;
      const atCast = from === null ? at : (p: Pos) => (p.x === cast.from.x && p.y === cast.from.y ? from : at(p));
      effects.push(...castEffects(cast, now, impactMs, atCast));
    });
    // 6N-4：有反應資料時，受擊者的身體由反應決定（受擊、重擊、格擋、閃避、倒下；`reactEffects.ts`），在各自那一段的命中點開始
    const reactions = vfx.reactions;
    const scale = impactMs / VFX_TIMING.impact;
    if (reactions !== undefined) {
      // 6N-5：復活（從倒地站起、一圈綠光）在 resultEffects.ts
      for (const r of reactions) effects.push(...(r.kind === "rise" ? riseEffects(this.resultHost, r, now + r.atMs, scale) : reactEffects(this.reactHost, r, now + r.atMs, scale)));
    }
    // 6N-5：特殊結果（暴擊閃白、擊殺震動、大火花與彈開、多一層殘影、Boss 四周變暗）與命中時的停頓
    const stage = this.app.stage;
    effects.push(...specialEffects(this.resultHost, vfx, { now, impactMs, scale, shake, apply: (x, y) => stage.position.set(x, y) }));
    for (const s of vfx.stops ?? []) addFreeze(this.freezes, now + s.atMs, s.ms, this.effectClock);
    for (const hit of vfx.hits) {
      // 異形（6M-3）：受擊只閃角色的剪影（不畫整片白圓），身體往後彈一下
      // 有骨架的人形（6M-4，美術 PM 檢查）：同樣只閃剪影、往後彈；形態、召喚物、倒地的人（6C-8）疊白色剪影閃白、不畫白圓
      const foe = this.creatureAt(hit.pos);
      const doll = foe === null ? this.dollAt(hit.pos) : null;
      const flat = foe === null && doll === null ? this.overlayFlashAt(hit.pos) : null;
      effects.push(...hitEffects(hit, now, impactMs, auraHits, at, foe === null && doll === null && flat === null));
      if (reactions !== undefined) continue;
      if (foe !== null) effects.push(this.creatureHit(foe, now + hit.atMs, Math.max(160, impactMs)));
      if (doll !== null) effects.push(this.dollHit(doll, now + hit.atMs, Math.max(160, impactMs)));
      if (flat !== null) effects.push(this.isDummy(flat) ? dummyFlashEffect(this.reactHost, flat, now + hit.atMs, scale) : this.overlayHit(flat, now + hit.atMs, Math.max(160, impactMs)));
    }
    for (const blast of vfx.blasts) effects.push(blastEffect(blast, now, impactMs, at));
    // 6H-1：鏡頭微震只在重擊、爆炸、Boss 大招（`battle/impact.ts`）；版面設定關掉、減少動態時不震
    const quake = shake ? impactShakeEffect(vfx.shakes ?? [], now, (x, y) => stage.position.set(x / this.scale, y / this.scale)) : null; // 幅度是畫面像素：場景座標要除以縮放
    if (quake !== null) effects.push(quake);
    // 6H-1：最後一擊放慢（效果時鐘在命中點前後以 0.4 倍走）；減少動態時 `reduceVfx` 已拿掉
    if (vfx.slow !== undefined) this.slows.push({ fromMs: now + vfx.slow.fromMs, toMs: now + vfx.slow.toMs, rampMs: vfx.slow.rampMs, rate: vfx.slow.rate });
    // 6H-1：減少動態時，重擊、爆炸改成目標身上的白閃加長
    // （倒下、復活的人不閃：減少動態時他們直接是結果的姿勢，白閃會把姿勢換回站著）
    const lying = new Set((reactions ?? []).filter((r) => r.kind === "down" || r.kind === "rise").map((r) => r.unitId));
    if (this.reduced) for (const s of vfx.shakes ?? []) if (s.kind !== "boss") for (const p of s.targets) this.steadyFlashAt(p, now + s.atMs, Math.max(60, Math.round(REDUCED_FLASH_MS * scale)), effects, lying);
    this.launch(effects);
  }

  /**
   * 減少動態時的白閃（6H-1）：不換姿勢、不位移，只把目標的剪影閃白後淡掉（`ms` 已縮放）。
   * 人形、異形換成帶白閃的身體貼圖；形態、召喚物、倒地的人疊白色剪影。效果沒有動態標記，減少動態時照播。
   */
  private steadyFlashAt(p: Pos, startMs: number, ms: number, out: Effect[], skip: ReadonlySet<string>): void {
    const unitId = this.creatureAt(p) ?? this.dollAt(p) ?? this.overlayFlashAt(p);
    if (unitId === null || skip.has(unitId) || this.isDummy(unitId)) return; // PR-2c：木樁只有受擊那一下的白閃（一格）
    const current = () => {
      const s = this.unitSprites.get(unitId);
      return s === undefined || s.destroyed ? null : s;
    };
    const owner = this.art.uniqueOwner(`flash:${unitId}`);
    const kind = this.creatureAt(p) !== null ? "creature" : this.dollAt(p) !== null ? "doll" : "overlay";
    out.push({
      node: new Container(),
      startMs,
      endMs: startMs + ms,
      update: (t) => {
        const s = current();
        const draw = this.unitDrawOf.get(unitId);
        if (s === null || draw === undefined) return;
        const flash = REDUCED_FLASH_PEAK * (1 - t);
        this.flashOutline(unitId, flash, REDUCED_FLASH_PEAK); // OCL-1b（Q6）：減少動態的白閃一律 0.85（異形也是），峰值照它自己
        if (kind === "doll") this.poseBody(unitId, s, { flash: quantizeFlash(flash) });
        else if (kind === "creature") this.poseBody(unitId, s, { creature: quantizeCreaturePose({ flash }) });
        else {
          const body = bodyNodes(s).find((n) => n.label === BODY_LABEL);
          const tex = flashTexture(this.art, draw);
          if (body === undefined || tex === null) return;
          this.art.holdFor(owner, tex);
          overlayFlash(body, tex, flash);
        }
      },
      end: () => {
        this.flashOutline(unitId, 0, 1);
        const s = current();
        if (s === null) return;
        if (kind === "overlay") clearFlash(s);
        else this.restBody(unitId, s);
        this.art.holdFor(owner, null);
      },
    });
  }

  /**
   * 地形升降動畫（Phase 3-19）：呼叫前已用新的 `view` 重畫（以結果為準），這裡把變動的格子先放回舊高度，
   * 再以 ease-out 補間到新高度（格上的物件、單位一起移動）；升起時碎土＋輕微震動（`shake` 為假時不震），
   * 下降結束時一圈塵土。`durationMs` 已依播放速度縮放；`skip()` 為真時直接跳到結果。
   */
  playLift(shifts: readonly HeightShift[], durationMs: number, shake: boolean, skip: () => boolean): void {
    const model = this.model;
    if (!this.ready || model === null || durationMs <= 0 || shifts.length === 0 || skip()) return;
    const now = this.effectClock;
    const effects: Effect[] = [];
    for (const s of shifts) {
      const shift = { ...s, to: heightAt(model, s.pos) };
      const key = `${s.pos.x},${s.pos.y}`;
      const state: LiftState = { pos: shift.pos, h: shift.from, to: shift.to };
      this.lifting.set(key, state);
      const apply = (h: number) => {
        if (this.lifting.get(key) !== state) return; // 已被新的畫面或新的動畫取代
        state.h = h;
        this.rows.setLift(shift.pos, tileLift(h));
        if (h === shift.to) this.lifting.delete(key);
      };
      apply(shift.from);
      const origin = (h: number) => liftedOrigin(shift.pos, h);
      effects.push(...liftEffects({ shift, now, durationMs, origin, apply, skip, size: T }));
    }
    if (shake && shifts.some((s) => heightAt(model, s.pos) > s.from)) {
      const stage = this.app.stage;
      effects.push(shakeEffect(LIFT_SHAKE_PX, now, durationMs * 0.6, (x, y) => stage.position.set(x / this.scale, y / this.scale))); // 6H-1：降到 1 px
    }
    this.launch(effects);
  }
}
