// 特殊結果的強化、復活、勝利的播放（Phase 6N-5；需求 docs/art/動畫移植需求第二批.md 第 4、5 節）。
// 姿勢由 reactClips.ts 的純函式給（`resultFrame`、`creatureResult`）；這裡只負責每幀照單位 ID 找目前的小人、換貼圖、
// 畫畫面閃白、四周變暗、大火花、多一層殘影。命中時的停頓由繪製器的效果時鐘處理（`BattleRenderer.freezeAt`）。
// - 暴擊：畫面閃白一下（震動、金色弧光、放大的「暴擊」數字在原本的特效與回饋裡）；
// - 擊殺：多一次震動（版面設定關掉震動時不震）；
// - 格擋成功：大火花、攻擊者被彈開半步；
// - 閃避成功：殘影多一層（在原地和跳到的位置中間）；
// - Boss 大招：畫面四周變暗 0.3 秒；
// - 復活：從倒地圖示站起來、腳下一圈綠光；勝利：全隊舉手或收刀、浮出「勝利」。
// 異形用 6M-2 的通用片段（`creatureResult`）；形態、召喚物沒有骨架，只有綠光、字樣。
import { Container, Graphics, Sprite } from "pixi.js";
import type { FrameVictory } from "../battle/playback";
import { BOSS_DIM_MS } from "../battle/specials";
import { TILE_SIZE } from "../battle/geometry";
import type { StepVfx, VfxReaction, VfxSpecial } from "../battle/vfx";
import { label } from "./labels";
import { knockOffset } from "./motionClips";
import { creatureResult, reactFrame, resultFrame, RESULT_MS, riseRing, victoryPose, type ResultClip } from "./reactClips";
import { bodyEffect, poseDoll, setBody, setCreatureBody, type ReactHost } from "./reactEffects";
import { downedLook } from "./unitLook";
import { BODY_LABEL, bodyNodes, creatureOf, dollPx, FEET, hasSkeleton } from "./unitSprite";
import type { Effect } from "./vfxEffects";
import type { PartFx } from "../battle/partStrip";
import { partBreakEffect } from "./partBreakFx";

const T = TILE_SIZE;

/** 繪製器提供的操作：6N-4 的 `ReactHost` 再加地圖大小（畫面閃白、四周變暗用）。 */
export interface ResultHost extends ReactHost {
  bounds(): { w: number; h: number };
  /** PB-1e：頭目部位破壞演出換格時，人物、頭頂小格、掉落物照這一格畫（`null`＝回到伺服器給的樣子）。沒有的繪製器（測試）可以不給。 */
  partFx?(unitId: string, fx: PartFx | null): void;
}

/** 片段長度（毫秒，已乘播放速度；最短 160，同 6N-4）。 */
export function resultMs(clip: ResultClip, scale: number): number {
  return Math.max(160, Math.round(RESULT_MS[clip] * scale));
}

/** 這個單位站起來之後有沒有骨架（倒下的人 `hasSkeleton` 一律為假，所以照站著的樣子判斷）。 */
function standsWithSkeleton(host: ReactHost, unitId: string): boolean {
  const d = host.draw(unitId);
  return d !== undefined && hasSkeleton({ ...d, downed: false });
}

// ---- 復活 --------------------------------------------------------------------------

/** 復活（`unit_revived`）：身體從倒地站起＋一圈綠光。`startMs` 是效果時鐘上的命中點。 */
export function riseEffects(host: ReactHost, r: VfxReaction, startMs: number, scale: number): Effect[] {
  const draw = host.draw(r.unitId);
  if (draw === undefined) return [];
  const ms = resultMs("rise", scale);
  const out: Effect[] = [ringEffect(host, r.unitId, startMs, ms)];
  if (creatureOf(draw) !== null) {
    out.push(
      bodyEffect(host, r.unitId, startMs, ms, (s, t) => setCreatureBody(host, r.unitId, s, creatureResult("rise", t))),
    );
  } else if (standsWithSkeleton(host, r.unitId)) out.push(riseBody(host, r.unitId, startMs, ms));
  return out;
}

/**
 * 紙娃娃從倒地站起（倒下片段倒過來）：第一格＝倒地圖示的變換、透明度＝倒地的外觀（可復活 0.6），
 * 灰階等濾鏡先拿掉；最後一格回到站好。重畫場景前後都照單位 ID 找目前的小人。
 */
function riseBody(host: ReactHost, unitId: string, startMs: number, ms: number): Effect {
  const saved = new Map<Sprite, Sprite["filters"]>();
  const restore = () => {
    for (const [node, f] of saved) if (!node.destroyed && node.parent?.destroyed !== true) node.filters = f === null || f === undefined ? null : [...f];
    saved.clear();
  };
  const fallen = downedLook(true, true).dollAlpha;
  const inner = bodyEffect(host, unitId, startMs, ms, (s, t) => {
    const draw = host.draw(unitId);
    if (draw === undefined || s.destroyed) return;
    const f = resultFrame("rise", t);
    setBody(host, unitId, s, { pose: f.pose }, f.fall > 0 ? "bare" : "ground");
    const px = dollPx(draw);
    for (const node of bodyNodes(s)) {
      node.position.set(f.dx * px, FEET + f.dy * px);
      node.rotation = f.rotation;
      node.alpha = 1 + (fallen - 1) * f.fall;
      if (node.filters !== null && node.filters !== undefined && (node.filters as unknown[]).length > 0 && !saved.has(node)) {
        saved.set(node, node.filters);
        node.filters = null;
      }
    }
  });
  const end = inner.end;
  inner.end = () => {
    restore();
    end?.();
    const s = host.sprite(unitId);
    const draw = host.draw(unitId);
    if (s !== null && draw !== undefined && !draw.downed) for (const node of bodyNodes(s)) node.alpha = 1;
  };
  return inner;
}

/** 復活的綠光：腳下一圈橢圓往外擴開、淡掉，中間一道淡淡的光柱。 */
function ringEffect(host: ReactHost, unitId: string, startMs: number, ms: number): Effect {
  const g = new Graphics();
  return {
    node: g,
    startMs,
    endMs: startMs + ms,
    motion: "fx",
    update: (t) => {
      g.clear();
      const s = host.sprite(unitId);
      const a = riseRing(t);
      if (s === null || a <= 0) return;
      const cx = s.x;
      const cy = s.y + FEET;
      const r = T * (0.22 + 0.3 * t);
      g.ellipse(cx, cy, r, r * 0.42).stroke({ width: 3, color: 0x6fe08a, alpha: 0.9 * a });
      g.ellipse(cx, cy, r * 0.7, r * 0.3).stroke({ width: 1.5, color: 0xd8ffd8, alpha: 0.7 * a });
      g.rect(cx - T * 0.16, cy - T * 0.9, T * 0.32, T * 0.9).fill({ color: 0x8ff0a4, alpha: 0.16 * a });
    },
  };
}

// ---- 格擋成功：攻擊者被彈開半步 --------------------------------------------------------

function recoilEffect(host: ReactHost, unitId: string, startMs: number, scale: number): Effect | null {
  const draw = host.draw(unitId);
  if (draw === undefined) return null;
  const ms = resultMs("recoil", scale);
  if (creatureOf(draw) !== null) {
    return bodyEffect(host, unitId, startMs, ms, (s, t) => setCreatureBody(host, unitId, s, creatureResult("recoil", t)));
  }
  if (!hasSkeleton(draw)) return null;
  return bodyEffect(host, unitId, startMs, ms, (s, t) => poseDoll(host, unitId, s, resultFrame("recoil", t)));
}

/** 格擋成功的大火花：11 道、半徑大七成，和 6N-4 的火花同一刻迸出。 */
function bigSparkEffect(host: ReactHost, unitId: string, startMs: number, ms: number): Effect {
  const g = new Graphics();
  return {
    node: g,
    startMs,
    endMs: startMs + ms,
    motion: "fx",
    update: (t) => {
      g.clear();
      const s = host.sprite(unitId);
      const draw = host.draw(unitId);
      if (s === null || draw === undefined) return;
      const spark = reactFrame("block", t).spark;
      if (spark <= 0) return;
      const front = knockOffset(draw.facing, -T * 0.2);
      const cx = s.x + front.x;
      const cy = s.y + FEET + front.y - T * 0.42;
      const k = 1 - spark;
      g.circle(cx, cy, 4 + 6 * spark).fill({ color: 0xfff4c0, alpha: 0.75 * spark });
      for (let i = 0; i < 11; i++) {
        const a = -Math.PI / 2 + (i - 5) * 0.3;
        const r0 = 5 + 16 * k;
        const r1 = r0 + 9 * spark + 3;
        g.moveTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0)
          .lineTo(cx + Math.cos(a) * r1, cy + Math.sin(a) * r1)
          .stroke({ width: 2.2, color: i % 2 === 0 ? 0xffd24a : 0xffffff, alpha: spark });
      }
    },
  };
}

// ---- 閃避成功：殘影多一層 --------------------------------------------------------------

/** 第二層殘影：在原地（6N-4 的殘影）和跳到的位置中間，跟著目前的姿勢、更淡。 */
function secondGhostEffect(host: ReactHost, unitId: string, startMs: number, ms: number, side: 1 | -1, variant: number): Effect {
  const node = new Container();
  let ghost: Sprite | null = null;
  const key = host.art.uniqueOwner(`ghost2:${unitId}`); // 6R-F：每個殘影自己一個 owner，不互相頂掉
  return {
    node,
    startMs,
    endMs: startMs + ms,
    motion: "fx",
    update: (t) => {
      const s = host.sprite(unitId);
      if (s === null || s.destroyed) return;
      const body = bodyNodes(s).find((n) => n.label === BODY_LABEL);
      if (body === undefined) return;
      const f = reactFrame("dodge", t, { side, variant });
      if (ghost === null) {
        ghost = new Sprite(body.texture);
        ghost.anchor.copyFrom(body.anchor);
        ghost.scale.copyFrom(body.scale);
        ghost.tint = 0xb8d8ff;
        node.addChild(ghost);
      }
      if (ghost.texture !== body.texture) ghost.texture = body.texture;
      host.art.holdFor(key, body.texture); // 殘影用的貼圖釘住（同 6N-4 的殘影）
      ghost.position.set(s.x + body.x / 2, s.y + (FEET + body.y) / 2);
      ghost.rotation = body.rotation / 2;
      ghost.alpha = f.ghost * 0.6;
      ghost.visible = f.ghost > 0.01;
    },
    end: () => {
      ghost?.destroy();
      ghost = null;
      host.art.holdFor(key, null);
    },
  };
}

// ---- 畫面閃白、四周變暗 ----------------------------------------------------------------

/** 暴擊：整張地圖閃白一下（停頓那一刻最亮，之後淡掉）。 */
function screenFlashEffect(host: ResultHost, startMs: number, ms: number): Effect {
  const g = new Graphics();
  return {
    node: g,
    startMs,
    endMs: startMs + ms,
    motion: "flash",
    update: (t) => {
      const { w, h } = host.bounds();
      g.clear();
      g.rect(-T, -T, w + T * 2, h + T * 2).fill({ color: 0xffffff, alpha: 0.32 * (1 - t) });
    },
  };
}

/** 四周變暗的強度（0～1）：前 20% 暗下來，最後 30% 亮回去。 */
export function vignetteAlpha(t: number): number {
  const k = t < 0 ? 0 : t > 1 ? 1 : t;
  return k < 0.2 ? k / 0.2 : k > 0.7 ? (1 - k) / 0.3 : 1;
}

/** Boss 大招：地圖四周一圈一圈往內變暗（中間不暗）。 */
function vignetteEffect(host: ResultHost, startMs: number, ms: number): Effect {
  const g = new Graphics();
  const bands = 8;
  return {
    node: g,
    startMs,
    endMs: startMs + ms,
    motion: "dim",
    update: (t) => {
      const { w, h } = host.bounds();
      const a = vignetteAlpha(t);
      g.clear();
      const band = Math.min(w, h) * 0.26;
      for (let i = 0; i < bands; i++) {
        const inset = (band * i) / bands - T * 0.5;
        g.rect(inset, inset, w - inset * 2, h - inset * 2).stroke({ width: band / bands + 1, color: 0x05040a, alpha: 0.6 * a * (1 - i / bands) });
      }
    },
  };
}

export interface SpecialOpts {
  /** 效果時鐘上這一步的原點。 */
  now: number;
  /** 命中後爆發的時間（已縮放；`impactMs / VFX_TIMING.impact` ＝ 播放速度的倍率）。 */
  impactMs: number;
  scale: number;
  /** 版面設定的畫面震動（6H-1 起擊殺不另外震，這裡用不到；微震由繪製器的 `impactShakeEffect` 處理）。 */
  shake: boolean;
  /** 震動時移動舞台。 */
  apply: (x: number, y: number) => void;
}

function oneSpecial(host: ResultHost, s: VfxSpecial, o: SpecialOpts, vfx: StepVfx): Effect[] {
  const at = o.now + s.atMs;
  switch (s.kind) {
    case "crit":
      return [screenFlashEffect(host, at, Math.max(60, Math.round(140 * o.scale)))];
    case "kill":
      return []; // 6H-1：擊殺不另外震（微震只在重擊、爆炸、Boss 大招；停頓照 6N-5）
    case "block": {
      const out: Effect[] = s.unitId === null ? [] : [bigSparkEffect(host, s.unitId, at, Math.max(160, Math.round(340 * o.scale)))];
      const recoil = s.attackerId === undefined ? null : recoilEffect(host, s.attackerId, at, o.scale);
      if (recoil !== null) out.push(recoil);
      return out;
    }
    case "dodge": {
      if (s.unitId === null || !standsWithSkeleton(host, s.unitId)) return [];
      const r = vfx.reactions?.find((x) => x.unitId === s.unitId && x.kind === "dodge");
      return [secondGhostEffect(host, s.unitId, at, Math.max(160, Math.round(380 * o.scale)), r?.side ?? 1, r?.variant ?? 0)];
    }
    case "boss":
      return [vignetteEffect(host, at, Math.max(60, Math.round(BOSS_DIM_MS * o.scale)))];
    case "part_break": {
      // PB-1e：正式演出 5 格（部位白閃、裂紋、碎塊飛出＋「破」、落地）；重擊白閃與微震照 PB-1c（`specials.ts`、`impact.ts`）
      const e = partBreakEffect(host, s, at, o.scale);
      return e === null ? [] : [e];
    }
  }
}

/** 一步所有特殊結果的效果（停頓另外由繪製器處理）。 */
export function specialEffects(host: ResultHost, vfx: StepVfx, o: SpecialOpts): Effect[] {
  return (vfx.specials ?? []).flatMap((s) => oneSpecial(host, s, o, vfx));
}

// ---- 勝利 --------------------------------------------------------------------------

/** 勝利：站著的我方每人播舉手或收刀（照雜湊），地圖上方浮出「勝利」。 */
export function victoryEffects(host: ResultHost, v: FrameVictory, startMs: number): Effect[] {
  const out: Effect[] = [];
  for (const id of v.unitIds) {
    const draw = host.draw(id);
    if (draw === undefined) continue;
    if (creatureOf(draw) !== null) {
      out.push(
        bodyEffect(host, id, startMs, v.clipMs, (s, t) => setCreatureBody(host, id, s, creatureResult("victory", t))),
      );
    } else if (hasSkeleton(draw)) {
      const kind = victoryPose(v.battleKey, v.seq, id);
      out.push(bodyEffect(host, id, startMs, v.clipMs, (s, t) => poseDoll(host, id, s, resultFrame("victory", t, kind))));
    }
  }
  out.push(victoryWord(host, startMs, Math.max(v.ms, v.clipMs)));
  return out;
}

/** 「勝利」字樣（之後有圖示時可換掉）：地圖上方彈出、停住、最後淡掉。 */
function victoryWord(host: ResultHost, startMs: number, ms: number): Effect {
  const node = new Container();
  const text = label("勝利", 46, 0xffe27a, true);
  text.anchor.set(0.5);
  text.style.stroke = { color: 0x000000, width: 6 };
  node.addChild(text);
  node.alpha = 0;
  return {
    node,
    startMs,
    endMs: startMs + ms,
    update: (t) => {
      const { w, h } = host.bounds();
      const pop = t < 0.15 ? t / 0.15 : 1;
      node.position.set(w / 2, h * 0.32 - 12 * pop);
      node.scale.set(0.7 + 0.3 * pop + (t < 0.25 ? 0.12 * Math.sin((t / 0.25) * Math.PI) : 0));
      node.alpha = t > 0.85 ? (1 - t) / 0.15 : pop;
    },
  };
}
