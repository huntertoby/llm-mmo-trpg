// 待機動畫的驅動（Phase 6M-4）：每幀把 idleClips 的呼吸、小動作套到站著的人身上（戰場與探索共用 BattleRenderer）。
// - 呼吸只改小人貼圖的垂直縮放（以腳底為軸），不換貼圖；小動作才換骨架姿勢的貼圖（量化 4 級，同裝備同朝向共用）。
// - 正在走、受擊、進出門的人（`hold`）、倒地、冰凍（不呼吸，動畫方案 2.7）不套用。
// - 不影響「沒設姿勢」的畫法：站好的貼圖照舊是 `art.figure(..., null)`，快照路徑不變。
// - 時鐘是 ticker 累加的毫秒（只影響畫面）；`enabled = false` 時一律站好（截圖、測試用）。
// - QK-7：戰場上沒輪到行動的人另播武器專屬待機（weaponIdleLayer.ts；8 格量化換貼圖＋光、法球的疊加層）；播小動作時暫停。
import type { Container, Sprite } from "pixi.js";
import type { UnitDraw } from "../battle/drawModel";
import type { AmbientScene } from "./ambientModel";
import { idleFrame, type IdleFrame } from "./idleClips";
import { npcIdleFrame, type NpcIdleFrame } from "./npcFidgets";
import type { Facing } from "../api/types";
import { isFrozenLook, isRootedLook, lockLegs } from "./statusAnim";
import type { InkPose } from "./inkPose";
import { bodyNodes, creatureOf, hasSkeleton, isProne } from "./unitSprite";
import { creatureIdlePose } from "./inkCreature";
import type { CreaturePose } from "./creaturePose";
import { WeaponIdleLayer, type WeaponIdleNow } from "./weaponIdleLayer";

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
  /** 系統設定減少動態（6N-10）：呼吸、小動作都不跑，一律站好。 */
  reduced = false;
  /** 實地地圖的場景（6N-10）：有身分的 NPC 改用 `npcFidgets` 的 3～4 種小動作（挑法用場景鍵）；`null` ＝ 照 6M-4。 */
  scene: AmbientScene | null = null;
  /** 武器專屬待機（QK-7）。 */
  readonly weapons = new WeaponIdleLayer();
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
    this.weapons.hide(sprite);
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

  /**
   * 這個人現在的待機畫面：有身分的 NPC 照 `npcFidgets`（職業動作時轉成側面，6Q-1），其他照 6M-4；定身時再鎖住腳（6N-9）。
   */
  private frameOf(u: UnitDraw): NpcIdleFrame {
    const id = u.id;
    const scene = this.scene;
    const role = scene !== null && Object.hasOwn(scene.roles, id) ? scene.roles[id] : undefined;
    const toward = scene !== null && scene.sides !== undefined && Object.hasOwn(scene.sides, id) ? scene.sides[id] : undefined;
    const f: NpcIdleFrame = scene !== null && role !== undefined ? npcIdleFrame(scene.key, id, role, this.clock, u.facing, toward) : idleFrame(id, this.clock);
    if (f.pose === null || !isRootedLook(u.statusIds ?? [])) return f;
    return { ...f, pose: lockLegs(f.pose), key: `${f.key}|rooted` };
  }

  private restore(sprite: Container): void {
    for (const node of bodyNodes(sprite)) {
      const base = this.baseY.get(node);
      if (base !== undefined) node.scale.y = base;
    }
  }

  /**
   * 推進 `dt` 毫秒並套用到所有站著的人。`setPose(id, sprite, pose, facing)`：換成小動作的貼圖（`null` ＝ 站好的貼圖）；
   * `facing` 是畫這張貼圖用的朝向（NPC 職業動作時的側面，6Q-1；`undefined` ＝ 原本的朝向）。
   * 回傳這一幀換了幾次貼圖（效能量測用）。
   */
  tick(
    dt: number,
    units: ReadonlyMap<string, Container>,
    draws: ReadonlyMap<string, UnitDraw>,
    setPose: (unitId: string, sprite: Container, pose: InkPose | null, facing?: Facing) => void,
    setCreature?: (unitId: string, sprite: Container, pose: CreaturePose | null) => void,
  ): number {
    this.clock += dt;
    let swaps = 0;
    for (const [id, sprite] of units) {
      if (sprite.destroyed || this.busy.has(id)) continue;
      const draw = draws.get(id);
      if (draw === undefined) continue;
      const on = this.enabled && !this.reduced && idles(draw);
      // QK-4：異形、頭目的待機是分部件片段（8 格量化、相位用 id 雜湊；頭目 16 格），不另外縮放呼吸
      const cr = setCreature === undefined ? null : creatureOf(draw);
      if (cr !== null && setCreature !== undefined) {
        const pose = on ? creatureIdlePose(cr, this.clock, id) : null;
        const key = pose === null ? "" : `ci:${pose.u ?? 0}`;
        if ((this.shown.get(id) ?? "") !== key) {
          this.shown.set(id, key);
          setCreature(id, sprite, pose);
          swaps += 1;
        }
        continue;
      }
      let f: NpcIdleFrame = on ? this.frameOf(draw) : { scaleY: 1, pose: null, key: "" };
      // QK-7：戰場上（沒有實地場景）、沒在播小動作時，換成武器專屬待機的這一格
      const skel = hasSkeleton(draw);
      const w: WeaponIdleNow | null = on && skel && f.pose === null && this.scene === null ? this.weapons.frame(draw, this.clock, isRootedLook(draw.statusIds ?? [])) : null;
      if (w !== null) f = { ...f, pose: w.pose, key: w.key === "" ? "" : `wi:${w.key}` };
      for (const node of bodyNodes(sprite)) {
        let base = this.baseY.get(node);
        if (base === undefined) {
          base = node.scale.y;
          this.baseY.set(node, base);
        }
        node.scale.y = base * f.scaleY;
      }
      if (!skel) continue;
      const was = this.shown.get(id) ?? "";
      if (was !== f.key) {
        this.shown.set(id, f.key);
        setPose(id, sprite, f.key === "" ? null : f.pose, f.key === "" ? undefined : f.facing);
        swaps += 1;
      }
      this.weapons.paint(sprite, draw, w);
    }
    return swaps;
  }
}
