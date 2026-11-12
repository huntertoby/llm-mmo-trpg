// 受擊與結果的播放（Phase 6N-4）：把 `battle/vfx.ts` 的反應（受擊、重擊、格擋、閃避、倒下）在命中點那一刻
// 套到受擊者身上。姿勢由 reactClips.ts 的純函式給；這裡只負責「每幀照單位 ID 找目前的小人、換貼圖、移位置」，
// 和 6M-4 的受擊一樣：重畫場景後換成新的節點也跟得上，結束時回到站好（倒下＝倒地圖示）的樣子。
// - 有骨架的人形：五種片段；閃避另畫殘影、格擋另畫火花；
// - 異形：受擊、重擊、倒下用 6M-2 的通用片段，閃避、格擋是受擊的輕版；
// - 形態、召喚物、倒地狀態的人：沒有骨架，受擊類疊白色剪影閃白（6C-8），閃避不閃。
import { Container, Graphics, Sprite, type Texture } from "pixi.js";
import type { UnitDraw } from "../battle/drawModel";
import { TILE_SIZE } from "../battle/geometry";
import type { ReactKind, VfxReaction } from "../battle/vfx";
import type { ArtTextures } from "./artTextures";
import { knockOffset } from "./motionClips";
import { creatureReact, guardOf, REACT_MS, reactFrame, sideOffset, type ReactClip, type ReactFrame, type ReactOpts } from "./reactClips";
import { clearFlash, overlayFlash } from "./silhouetteFlash";
import { downedLook } from "./unitLook";
import { BODY_LABEL, bodyNodes, bodyTexture, creatureOf, dollPx, FEET, flashTexture, gripOf, hasSkeleton, isProne, overlayFlashKind, placeCreatureBody, uprightTexture, type BodyFrame } from "./unitSprite";
import type { Effect } from "./vfxEffects";
import { dummyFlashAlpha, dummyFlashMs, isTrainingDummy } from "./trainingDummy";

const T = TILE_SIZE;

/** 繪製器提供的操作（BattleRenderer 實作）。 */
export interface ReactHost {
  readonly art: ArtTextures;
  sprite(unitId: string): Container | null;
  draw(unitId: string): UnitDraw | undefined;
  /** 鎖住待機、狀態的身體動作（`IdleMotion.hold`）。 */
  hold(unitId: string, sprite: Container): void;
  release(unitId: string): void;
  /** 換小人的貼圖（同時把這張貼圖釘在 LRU 裡）。 */
  setTexture(unitId: string, node: Sprite, tex: Texture): void;
  /** 回到站好（倒地狀態＝躺著、倒下＝倒地圖示）的貼圖與位置。 */
  restBody(unitId: string, sprite: Container): void;
}

/** 反應種類 → 片段。 */
export const CLIP_OF: Readonly<Record<Exclude<ReactKind, "rise">, ReactClip>> = { hit: "hit", heavy: "heavy", block: "block", dodge: "dodge", down: "down" };

/** 片段長度（毫秒，已乘播放速度；最短 160，同 6M-4）。 */
export function reactMs(kind: Exclude<ReactKind, "rise">, scale: number): number {
  return Math.max(160, Math.round(REACT_MS[CLIP_OF[kind]] * scale));
}

/** 一個反應的所有效果（身體片段＋殘影或火花）。`startMs` 是效果時鐘上的命中點，`scale` 是播放速度的時間倍率。 */
export function reactEffects(host: ReactHost, r: VfxReaction, startMs: number, scale: number): Effect[] {
  const draw = host.draw(r.unitId);
  if (draw === undefined || r.kind === "rise") return []; // 復活（6N-5）在 resultEffects.ts
  if (isTrainingDummy(draw)) return r.kind === "dodge" ? [] : [dummyFlashEffect(host, r.unitId, startMs, scale)]; // PR-2c：木樁只閃白
  const ms = reactMs(r.kind, scale);
  const clip = CLIP_OF[r.kind];
  if (creatureOf(draw) !== null) return [bodyEffect(host, r.unitId, startMs, ms, (s, t) => poseCreature(host, r.unitId, s, clip, t))];
  if (hasSkeleton(draw) && !isProne(draw)) {
    const g = gripOf(draw);
    const opts: ReactOpts = { side: r.side ?? 1, guard: g === null ? "arm" : guardOf(g.main, g.off), variant: r.variant ?? 0 };
    if (clip === "down") return [downEffect(host, r.unitId, startMs, ms)];
    const out = [bodyEffect(host, r.unitId, startMs, ms, (s, t) => poseDoll(host, r.unitId, s, reactFrame(clip, t, opts)))];
    if (clip === "dodge") out.push(ghostEffect(host, r.unitId, startMs, ms, opts));
    if (clip === "block") out.push(sparkEffect(host, r.unitId, startMs, ms));
    return out;
  }
  if (r.kind === "dodge" || overlayFlashKind(draw) === null) return [];
  return [overlayEffect(host, r.unitId, startMs, ms, r.kind === "block" ? 0.4 : 1)];
}

/** 每幀照單位 ID 找目前的小人、鎖住待機；結束時回到站好。 */
export function bodyEffect(host: ReactHost, unitId: string, startMs: number, ms: number, pose: (s: Container, t: number) => void): Effect {
  let held = false;
  return {
    node: new Container(),
    startMs,
    endMs: startMs + ms,
    update: (t) => {
      const s = host.sprite(unitId);
      if (s === null) return;
      if (!held) {
        held = true;
        host.hold(unitId, s);
      }
      pose(s, t);
    },
    end: () => {
      const s = host.sprite(unitId);
      if (s !== null) host.restBody(unitId, s);
      if (held) host.release(unitId);
      held = false;
    },
    motion: "body",
  };
}

export function setBody(host: ReactHost, unitId: string, s: Container, frame: BodyFrame, upright: false | "ground" | "bare" = false): void {
  const draw = host.draw(unitId);
  if (draw === undefined) return;
  for (const node of bodyNodes(s)) {
    if (node.label !== BODY_LABEL) continue;
    const tex = upright === false ? bodyTexture(host.art, draw, frame) : uprightTexture(host.art, draw, frame, upright === "bare");
    if (tex !== null && node.texture !== tex) host.setTexture(unitId, node, tex);
  }
  // 6R-F：異形的位移改移節點（貼圖鍵不含 dx、dy），影子留在腳底；紙娃娃不動
  if (upright === false) placeCreatureBody(host.art, unitId, s, draw, frame, { x: 0, y: FEET });
}

/** 異形的一格（6R-F）：跟著的特效回到腳底，身體由 `setBody` 照姿勢的位移放好。 */
export function setCreatureBody(host: ReactHost, unitId: string, s: Container, pose: BodyFrame["creature"]): void {
  if (s.destroyed) return;
  for (const node of bodyNodes(s)) node.position.set(0, FEET);
  setBody(host, unitId, s, { creature: pose });
}

/** 紙娃娃：姿勢＋往後退、往側邊、離地、旋轉（南北向有透視，只走一半）。 */
export function poseDoll(host: ReactHost, unitId: string, s: Container, f: ReactFrame): void {
  const draw = host.draw(unitId);
  if (draw === undefined || s.destroyed) return;
  setBody(host, unitId, s, { pose: f.pose, flash: f.flash });
  const px = dollPx(draw);
  const back = knockOffset(draw.facing, f.back * px);
  const side = sideOffset(draw.facing, f.side * px);
  for (const node of bodyNodes(s)) {
    node.position.set(back.x + side.x, FEET + back.y + side.y - f.air * px);
    node.rotation = f.rotation;
  }
}

function poseCreature(host: ReactHost, unitId: string, s: Container, clip: ReactClip, t: number): void {
  setCreatureBody(host, unitId, s, creatureReact(clip, t));
}

/**
 * 倒下：白閃 → 膝蓋一軟 → 側倒。畫的是站著的紙娃娃（重畫成倒下之後也一樣），側倒時換成不含影子的版本，
 * 透明度、灰階慢慢變成倒地的外觀；最後一格（`fall` ＝ 1）直接換回倒地圖示的貼圖（位置、旋轉歸零），所以沒有跳一下。
 */
function downEffect(host: ReactHost, unitId: string, startMs: number, ms: number): Effect {
  const saved = new Map<Sprite, Sprite["filters"]>();
  const restoreFilters = () => {
    for (const [node, f] of saved) if (!node.destroyed) node.filters = f === null || f === undefined ? null : [...f];
    saved.clear();
  };
  const inner = bodyEffect(host, unitId, startMs, ms, (s, t) => {
    const draw = host.draw(unitId);
    if (draw === undefined || s.destroyed) return;
    const f = reactFrame("down", t);
    const look = downedLook(draw.downed, draw.revivable);
    if (f.fall >= 1 && draw.downed) {
      restoreFilters();
      host.restBody(unitId, s);
      for (const node of bodyNodes(s)) node.alpha = look.dollAlpha;
      return;
    }
    setBody(host, unitId, s, { pose: f.pose, flash: f.flash }, f.fall > 0 ? "bare" : "ground");
    const px = dollPx(draw);
    const back = knockOffset(draw.facing, f.back * px);
    for (const node of bodyNodes(s)) {
      node.position.set(back.x + f.dx * px, FEET + back.y + f.dy * px);
      node.rotation = f.rotation;
      node.alpha = 1 + (look.dollAlpha - 1) * f.fall;
      if (node.filters !== null && node.filters !== undefined && (node.filters as unknown[]).length > 0 && !saved.has(node)) {
        saved.set(node, node.filters); // 灰階等倒地的外觀先拿掉，躺平時再放回去
        node.filters = null;
      }
    }
  });
  const end = inner.end;
  inner.end = () => {
    restoreFilters();
    end?.();
    const s = host.sprite(unitId);
    const draw = host.draw(unitId);
    if (s !== null && draw?.downed === true) for (const node of bodyNodes(s)) node.alpha = downedLook(true, draw.revivable).dollAlpha;
  };
  return inner;
}

/** 閃避的殘影：在原地留一張同樣的小人，從半透明淡掉（只在效果圖層，不動小人本身）。 */
function ghostEffect(host: ReactHost, unitId: string, startMs: number, ms: number, opts: ReactOpts): Effect {
  const node = new Container();
  let ghost: Sprite | null = null;
  const owner = host.art.uniqueOwner(`ghost:${unitId}`); // 6R-F：同一人一步內兩次閃避，殘影不互相頂掉
  return {
    node,
    startMs,
    endMs: startMs + ms,
    motion: "fx",
    update: (t) => {
      const s = host.sprite(unitId);
      const f = reactFrame("dodge", t, opts);
      if (s === null || s.destroyed) return;
      const body = bodyNodes(s).find((n) => n.label === BODY_LABEL);
      if (body === undefined) return;
      if (ghost === null) {
        ghost = new Sprite(body.texture);
        host.art.holdFor(owner, body.texture); // 殘影用的貼圖釘住（重畫場景時不被銷毀）
        ghost.anchor.copyFrom(body.anchor);
        ghost.scale.copyFrom(body.scale);
        ghost.tint = 0xcfe6ff;
        node.addChild(ghost);
      }
      ghost.position.set(s.x, s.y + FEET);
      ghost.alpha = f.ghost;
      ghost.visible = f.ghost > 0.01;
    },
    end: () => {
      ghost?.destroy();
      ghost = null;
      host.art.holdFor(owner, null);
    },
  };
}

/** 格擋的火花：擋住那一刻在身前迸出 7 道短光線（角度固定，確定性），往外散、淡掉。 */
function sparkEffect(host: ReactHost, unitId: string, startMs: number, ms: number): Effect {
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
      const f = reactFrame("block", t);
      if (f.spark <= 0) return;
      const front = knockOffset(draw.facing, -T * 0.16);
      const cx = s.x + front.x;
      const cy = s.y + FEET + front.y - T * 0.42;
      const k = 1 - f.spark; // 0 → 1：往外散
      g.circle(cx, cy, 2 + 3 * f.spark).fill({ color: 0xfff4c0, alpha: 0.9 * f.spark });
      for (let i = 0; i < 7; i++) {
        const a = -Math.PI / 2 + (i - 3) * 0.42;
        const r0 = 3 + 9 * k;
        const r1 = r0 + 5 * f.spark + 2;
        g.moveTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0)
          .lineTo(cx + Math.cos(a) * r1, cy + Math.sin(a) * r1)
          .stroke({ width: 1.6, color: i % 2 === 0 ? 0xffe27a : 0xffffff, alpha: f.spark });
      }
    },
  };
}

/** 沒有骨架的單位：疊白色剪影閃白（6C-8 的做法；格擋淡一點）。 */
function overlayEffect(host: ReactHost, unitId: string, startMs: number, ms: number, strength: number): Effect {
  const owner = host.art.uniqueOwner(`flash:${unitId}`); // 6R-F：白閃疊層的貼圖也釘住
  return {
    node: new Container(),
    startMs,
    endMs: startMs + ms,
    motion: "body",
    update: (t) => {
      const s = host.sprite(unitId);
      const draw = host.draw(unitId);
      if (s === null || draw === undefined) return;
      const body = bodyNodes(s).find((n) => n.label === BODY_LABEL);
      const tex = flashTexture(host.art, draw);
      if (body === undefined || tex === null) return;
      host.art.holdFor(owner, tex);
      overlayFlash(body, tex, reactFrame("hit", t).flash * strength);
    },
    end: () => {
      const s = host.sprite(unitId);
      if (s !== null) clearFlash(s);
      host.art.holdFor(owner, null);
    },
  };
}

/**
 * 靶場木樁被打中（PR-2c，`docs/art/靶場移植需求.md` 第 2 節）：不動、只在木樁上疊白色剪影 0.1 秒（`DUMMY_FLASH_MS` × 播放速度倍率），
 * 整段同一個強度。標成身體片段：減少動態時直接畫最後一格（同一張白閃停一下＝一格），結束時拿掉。
 */
export function dummyFlashEffect(host: ReactHost, unitId: string, startMs: number, scale: number): Effect {
  const owner = host.art.uniqueOwner(`flash:${unitId}`);
  return {
    node: new Container(),
    startMs,
    endMs: startMs + dummyFlashMs(scale),
    motion: "body",
    update: (t) => {
      const s = host.sprite(unitId);
      const draw = host.draw(unitId);
      if (s === null || draw === undefined) return;
      const body = bodyNodes(s).find((n) => n.label === BODY_LABEL);
      const tex = flashTexture(host.art, draw);
      if (body === undefined || tex === null) return;
      host.art.holdFor(owner, tex);
      overlayFlash(body, tex, dummyFlashAlpha(t));
    },
    end: () => {
      const s = host.sprite(unitId);
      if (s !== null) clearFlash(s);
      host.art.holdFor(owner, null);
    },
  };
}
