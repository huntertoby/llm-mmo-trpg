// 狀態動作與地表動畫的接線（Phase 6N-9）：把 StatusAnimator、SurfaceAnimator 包成一個，讓 BattleRenderer 只加幾行。
// - prefers-reduced-motion：開著時兩者都停（狀態只剩靜態的身上特效，表面不動、不播轉場），設定改變時馬上跟著變；
// - 播放速度：轉場的時間乘上 `playback.SPEED_SCALE`（含開發用的 `?anim=`）；「略過」不播轉場。
import type { Container } from "pixi.js";
import type { DrawModel, UnitDraw } from "../battle/drawModel";
import { SPEED_SCALE } from "../battle/playback";
import { loadSpeed } from "../ui/SpeedControl";
import { prefersReducedMotion, subscribeReducedMotion } from "../world/frameLoop";
import { animTextureCount } from "./statusAnimArt";
import { StatusAnimator } from "./statusAnimLayer";
import { SurfaceAnimator, type SurfaceHost } from "./surfaceAnimLayer";

/** 轉場的時間倍率：「略過」→ `null`。 */
export function surfaceTimeScale(): number | null {
  const speed = loadSpeed();
  return speed === "skip" ? null : SPEED_SCALE[speed];
}

export class MotionAnims {
  readonly status = new StatusAnimator();
  readonly surface = new SurfaceAnimator();
  private unsubscribe: (() => void) | null = null;
  /** 開發頁、截圖用：強制開關（`null` ＝ 照 prefers-reduced-motion）。 */
  private forced: boolean | null = null;

  start(): void {
    this.sync();
    this.unsubscribe = subscribeReducedMotion(() => this.sync());
  }

  stop(): void {
    this.unsubscribe?.();
    this.unsubscribe = null;
  }

  private sync(): void {
    const on = this.forced ?? !prefersReducedMotion();
    this.status.setEnabled(on);
    this.surface.setEnabled(on);
  }

  /** 強制開關（`null` ＝ 照系統設定）。 */
  force(on: boolean | null): void {
    this.forced = on;
    this.sync();
  }

  /** 地形畫好之後：表面的轉場與動態。 */
  drawSurfaces(model: DrawModel, host: SurfaceHost): void {
    this.surface.draw(model, host, surfaceTimeScale());
  }

  /** 單位畫好之後：下一幀重新掛上狀態動作（站在水上的單位算潮濕）。 */
  drawUnits(model: DrawModel): void {
    const water = new Set(model.tiles.filter((t) => t.surface === "water").map((t) => `${t.x},${t.y}`));
    const wet = new Set(model.units.filter((u) => !u.downed && water.has(`${u.x},${u.y}`)).map((u) => u.id));
    this.status.reset(wet);
  }

  tick(dt: number, units: ReadonlyMap<string, Container>, draws: ReadonlyMap<string, UnitDraw>, held: (id: string) => boolean): void {
    this.surface.tick(dt);
    this.status.tick(dt, units, draws, held);
  }

  /** 兩個時鐘設成同一個值（截圖時固定相位用）。 */
  setClock(ms: number): void {
    this.status.clock = ms;
    this.surface.clock = ms;
  }

  stats(): { statusUnits: number; particleSprites: number; transitions: number; shimmerTiles: number; animTextures: number } {
    const s = this.status.stats();
    const f = this.surface.stats();
    return { statusUnits: s.units, particleSprites: s.sprites, transitions: f.transitions, shimmerTiles: f.shimmers, animTextures: animTextureCount() };
  }
}
