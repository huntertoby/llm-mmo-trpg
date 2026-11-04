// 待機動畫的驅動（Phase 6M-4）：每幀把 idleClips 的呼吸、小動作套到站著的人身上（戰場與探索共用 BattleRenderer）。
// - 呼吸只改小人貼圖的垂直縮放（以腳底為軸），不換貼圖；小動作才換骨架姿勢的貼圖（量化 4 級，同裝備同朝向共用）。
// - 正在走、受擊、進出門的人（`hold`）、倒地、冰凍（不呼吸，動畫方案 2.7）不套用。
// - 不影響「沒設姿勢」的畫法：站好的貼圖照舊是 `art.figure(..., null)`，快照路徑不變。
// - 時鐘是 ticker 累加的毫秒（只影響畫面）；`enabled = false` 時一律站好（截圖、測試用）。
import type { Container, Sprite } from "pixi.js";
import type { UnitDraw } from "../battle/drawModel";
import { idleFrame, type IdleFrame } from "./idleClips";
import { isFrozenLook, isRootedLook, lockLegs } from "./statusAnim";
import type { InkPose } from "./inkPose";
import { bodyNodes, hasSkeleton, isProne } from "./unitSprite";

/** 冰凍：骨架停在當下的姿勢、不呼吸。 */
export const NO_IDLE_STATUS = "frozen";

export function idles(u: UnitDraw): boolean {
  return !u.downed && !isProne(u) && !isFrozenLook(u.statusIds ?? []);
}

/** 定身（6N-9）：小動作只動上半身，腳不動。 */
export function idleFrameFor(u: UnitDraw, ms: number): IdleFrame {
  const f = idleFrame(u.id, ms);
  if (f.pose === null || !isRootedLook(u.statusIds ?? [])) return f;
  return { ...f, pose: lockLegs(f.pose), key: `${f.key}|rooted` };
}

export class IdleMotion {
  clock = 0;
  enabled = true;
  private readonly busy = new Map<string, number>();
  /** 目前畫上去的小動作（單位 ID → 姿勢鍵；"" ＝ 站好）。 */
  private readonly shown = new Map<string, string>();
  private readonly baseY = new WeakMap<Sprite, number>();

  /** 重畫場景後（小人都重建了）：忘掉已套用的姿勢。 */
  reset(): void {
    this.shown.clear();
  }

  /** 這個人開始播別的動畫：停止待機，縮放回到原本。 */
  hold(unitId: string, sprite: Container | undefined): void {
    this.busy.set(unitId, (this.busy.get(unitId) ?? 0) + 1);
    this.shown.delete(unitId);
    if (sprite !== undefined && !sprite.destroyed) this.restore(sprite);
  }

  /** 和 `hold` 成對呼叫（同一個人可以同時有好幾段動畫，全部放開才恢復待機）。 */
  release(unitId: string): void {
    const n = (this.busy.get(unitId) ?? 0) - 1;
    if (n > 0) this.busy.set(unitId, n);
    else this.busy.delete(unitId);
  }

  isHeld(unitId: string): boolean {
    return this.busy.has(unitId);
  }

  private restore(sprite: Container): void {
    for (const node of bodyNodes(sprite)) {
      const base = this.baseY.get(node);
      if (base !== undefined) node.scale.y = base;
    }
  }

  /**
   * 推進 `dt` 毫秒並套用到所有站著的人。`setPose(id, sprite, pose)`：換成小動作的貼圖（`null` ＝ 站好的貼圖）。
   * 回傳這一幀換了幾次貼圖（效能量測用）。
   */
  tick(
    dt: number,
    units: ReadonlyMap<string, Container>,
    draws: ReadonlyMap<string, UnitDraw>,
    setPose: (unitId: string, sprite: Container, pose: InkPose | null) => void,
  ): number {
    this.clock += dt;
    let swaps = 0;
    for (const [id, sprite] of units) {
      if (sprite.destroyed || this.busy.has(id)) continue;
      const draw = draws.get(id);
      if (draw === undefined) continue;
      const on = this.enabled && idles(draw);
      const f = on ? idleFrameFor(draw, this.clock) : { scaleY: 1, pose: null, key: "" };
      for (const node of bodyNodes(sprite)) {
        let base = this.baseY.get(node);
        if (base === undefined) {
          base = node.scale.y;
          this.baseY.set(node, base);
        }
        node.scale.y = base * f.scaleY;
      }
      if (!hasSkeleton(draw)) continue;
      const was = this.shown.get(id) ?? "";
      if (was === f.key) continue;
      this.shown.set(id, f.key);
      setPose(id, sprite, f.key === "" ? null : f.pose);
      swaps += 1;
    }
    return swaps;
  }
}
