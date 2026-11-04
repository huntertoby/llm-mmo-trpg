// 減少動態（prefers-reduced-motion，6R-F；前端審查第 4 點）：戰場的效果在放進效果迴圈前先照類別處理。
// - `flash`（全畫面閃白）、`shake`（震動）、`dim`（Boss 四周變暗）：不播；
// - `fx`（弧光、殘影、火花、片段的特效提示）：不畫；
// - `body`（技能、受擊、閃避、倒下、勝利、復活的身體片段）：一開始就直接跳到最後一格（結果姿勢），播到時間照舊收尾；
// - 沒標的（飛行物、爆發、受擊的白圈、傷害數字、字樣）：照舊。
// 另外 `reduceVfx` 拿掉命中時的停頓與 6N-8 技能變體的特效層（軌跡、爆發形狀、粒子分布照基本樣子）。
// 純函式，不改規則與數值；遊戲內自己的「減少動態」開關不在這一段（待 PM 決定）。
import type { StepVfx, VfxCast } from "../battle/vfx";
import type { Effect, MotionTag } from "./vfxEffects";

/** 減少動態時不播的類別。 */
export const REDUCED_DROP: ReadonlySet<MotionTag> = new Set<MotionTag>(["flash", "shake", "dim", "fx"]);

/** 身體片段：第一次更新就畫最後一格，之後不再動（結束時照舊回到站好）。 */
function jumpToEnd(e: Effect): Effect {
  let done = false;
  return {
    ...e,
    update: () => {
      if (done) return;
      done = true;
      e.update(1);
    },
  };
}

/** 一組效果照減少動態處理；`reduced` 為假時原樣回傳。拿掉的效果馬上收尾（`end`）並銷毀節點。 */
export function reduceEffects(effects: readonly Effect[], reduced: boolean): Effect[] {
  if (!reduced) return [...effects];
  const out: Effect[] = [];
  for (const e of effects) {
    if (e.motion !== undefined && REDUCED_DROP.has(e.motion)) {
      e.end?.();
      e.node.destroy({ children: true });
      continue;
    }
    out.push(e.motion === "body" ? jumpToEnd(e) : e);
  }
  return out;
}

function plainCast(c: VfxCast): VfxCast {
  if (c.look === undefined) return c;
  const { look: _look, ...rest } = c;
  return rest;
}

/** 特效描述照減少動態處理：沒有停頓、技能變體的特效層照基本樣子。`reduced` 為假時原樣回傳。 */
export function reduceVfx(vfx: StepVfx, reduced: boolean): StepVfx {
  if (!reduced) return vfx;
  const { stops: _stops, ...rest } = vfx;
  return { ...rest, casts: vfx.casts.map(plainCast) };
}
