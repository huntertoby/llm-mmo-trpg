// 武器專屬待機接上戰場（QK-7）：IdleMotion 每幀問這裡「這個人現在是哪一格」，並把疊加層（光、法球）畫在小人上面。
// - 只在 Q 版畫法、戰場（沒有實地場景）、沒輪到行動、有骨架、沒在播小動作時才晃（其他條件照 6M-4 的 idles／hold）。
// - 貼圖的姿勢：量化後的 8 格動作（不含 glow、orbY；法球待機加 glowLayer 讓貼圖不畫法球），鍵用 poseKey，同裝備同朝向同一格共用。
// - 疊加層：Graphics，放在小人節點正上方，位置與縮放每幀跟著小人（含 6M-4 的呼吸縮放）。
import { Graphics, type Container, type Sprite } from "pixi.js";
import type { UnitDraw } from "../battle/drawModel";
import type { Facing } from "../api/types";
import type { Ctx } from "./artDraw";
import { poseKey } from "./motionClips";
import type { InkPose } from "./inkPose";
import { dollSkin } from "./inkStyle";
import { DOLL_H, DOLL_W } from "./paperdoll";
import type { QPose, QUnit, QView } from "./qCore";
import { GAME_HOOKS, qUnitOf } from "./qSpec";
import { canStamp } from "./qStamp";
import { lockLegs } from "./statusAnim";
import { BODY_LABEL, specOfUnit } from "./unitSprite";
import { weaponIdleFrame, weaponIdleKindOf, type WeaponIdleKind } from "./idleWeapons";
import { glowKindOf, glowShapes, probeGlowAnchor, type GlowAnchor, type GlowKind } from "./weaponGlow";

/** 疊加層節點的名稱。 */
export const WEAPON_GLOW_LABEL = "weapon-glow";

export interface WeaponIdleNow {
  /** 貼圖的姿勢（`null` ＝ 站好的貼圖：例如正面的劍沒有可套的鍵）。 */
  pose: InkPose | null;
  /** 貼圖鍵（"" ＝ 站好）。 */
  key: string;
  glow: number;
  orbY: number;
  glowKind: GlowKind | null;
  view: QView;
  west: boolean;
}

export const viewOf = (f: Facing): QView => (f === "north" ? "back" : f === "south" ? "front" : "side");

/** 拿掉疊加層的鍵（glow、orbY），其他照抄；法球有疊加層時加 glowLayer。 */
export function texturePose(p: QPose, glowKind: GlowKind | null, overlay: boolean): InkPose {
  const out: Record<string, number> = {};
  for (const [k, v] of Object.entries(p)) if (k !== "glow" && k !== "orbY" && typeof v === "number") out[k] = v;
  if (overlay && glowKind === "orb") out["glowLayer"] = 1;
  return out as InkPose;
}

export class WeaponIdleLayer {
  /** 能畫疊加層（有 DOM）；沒有時法球照貼圖畫、光不脈動。 */
  overlay = canStamp();
  private readonly units = new WeakMap<UnitDraw, { unit: QUnit; kind: WeaponIdleKind | null }>();
  private readonly anchors = new WeakMap<UnitDraw, Map<string, GlowAnchor | null>>();
  private readonly nodes = new WeakMap<Container, Graphics>();
  private probeCtx: Ctx | null = null;

  private unitOf(draw: UnitDraw): { unit: QUnit; kind: WeaponIdleKind | null } {
    let u = this.units.get(draw);
    if (u === undefined) {
      const unit = qUnitOf(specOfUnit(draw));
      u = { unit, kind: weaponIdleKindOf(unit) };
      this.units.set(draw, u);
    }
    return u;
  }

  /** 這個人現在的武器待機（沒有武器待機的人 → null，照 6M-4）。`rooted`：定身，腳不動。 */
  frame(draw: UnitDraw, ms: number, rooted: boolean): WeaponIdleNow | null {
    if (dollSkin() !== "q" || draw.active) return null;
    const { kind } = this.unitOf(draw);
    if (kind === null) return null;
    const view = viewOf(draw.facing);
    const f = weaponIdleFrame(kind, draw.id, ms, { breath: false, view });
    const glowKind = this.overlay ? glowKindOf(kind, view) : null;
    let pose = texturePose(f.pose, glowKind, this.overlay);
    if (rooted) pose = lockLegs(pose);
    const key = poseKey(pose);
    return { pose: key === "" ? null : pose, key, glow: f.pose.glow ?? 0, orbY: f.pose.orbY ?? 0, glowKind, view, west: draw.facing === "west" };
  }

  private anchorOf(draw: UnitDraw, now: WeaponIdleNow): GlowAnchor | null {
    if (now.glowKind === null) return null;
    let m = this.anchors.get(draw);
    if (m === undefined) {
      m = new Map();
      this.anchors.set(draw, m);
    }
    const key = `${draw.facing}|${now.key}`;
    if (m.has(key)) return m.get(key) ?? null;
    const ctx = this.ctx();
    const a = ctx === null ? null : probeGlowAnchor(ctx, this.unitOf(draw).unit, now.view, now.west, GAME_HOOKS, (now.pose ?? {}) as QPose, now.glowKind);
    m.set(key, a);
    return a;
  }

  private ctx(): Ctx | null {
    if (this.probeCtx === null && typeof document !== "undefined") {
      const c = document.createElement("canvas");
      c.width = 1;
      c.height = 1;
      this.probeCtx = c.getContext("2d");
    }
    return this.probeCtx;
  }

  /** 畫（或藏起）這個人的疊加層；`now` 為 null 或沒有疊加層時藏起來。 */
  paint(sprite: Container, draw: UnitDraw, now: WeaponIdleNow | null): void {
    const a = now === null ? null : this.anchorOf(draw, now);
    let g = this.nodes.get(sprite);
    if (a === null || now === null) {
      if (g !== undefined && !g.destroyed) g.visible = false;
      return;
    }
    const body = sprite.children.find((n): n is Sprite => n.label === BODY_LABEL && "texture" in n);
    if (body === undefined) return;
    if (g === undefined || g.destroyed) {
      g = new Graphics();
      g.label = WEAPON_GLOW_LABEL;
      g.eventMode = "none";
      sprite.addChildAt(g, sprite.getChildIndex(body) + 1);
      this.nodes.set(sprite, g);
    }
    g.visible = true;
    g.position.copyFrom(body.position);
    g.rotation = body.rotation;
    g.scale.set((Math.sign(body.scale.x) || 1) * (body.width / DOLL_W), body.height / DOLL_H);
    g.alpha = body.alpha;
    g.clear();
    for (const s of glowShapes(a, now.glow, now.orbY)) {
      if (s.circle) g.circle(s.circle[0], s.circle[1], s.circle[2]).fill({ color: s.color, alpha: s.alpha });
      else if (s.poly) g.poly([...s.poly]).fill({ color: s.color, alpha: s.alpha });
    }
  }

  /** 藏起疊加層（開始播別的動畫時）。 */
  hide(sprite: Container | undefined): void {
    const g = sprite === undefined ? undefined : this.nodes.get(sprite);
    if (g !== undefined && !g.destroyed) g.visible = false;
  }
}
