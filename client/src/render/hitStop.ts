// 命中時的停頓（Phase 6N-5，選項 B：特效加停頓，不做慢動作）：繪製器的效果時鐘走到停頓那一刻就停住，
// 用掉停頓的時間再往下走。純函式（時間 → 時間），只吃 ticker 給的每幀時間，不讀時鐘。
// 停住的時候所有效果（身體片段、特效、浮動數字）都停在同一格；按住空白鍵加速時 ticker 的每幀時間變長，停頓一起變短。
// 6H-1：最後一擊放慢（`slows`：效果時鐘在範圍內以 0.4 倍走，前後漸變；`battle/impact.ts` 的 `slowRate`）。
import { slowRate, type SlowSpan } from "../battle/impact";

export interface Freeze {
  /** 效果時鐘上停住的那一刻（毫秒）。 */
  at: number;
  /** 還要停多久（毫秒）。 */
  left: number;
}

/**
 * 效果時鐘從 `clock` 往前走 `delta` 毫秒：碰到停頓時停在 `at`，先用掉停頓的時間；停頓用完就從 `freezes` 移除
 * （原地修改，`freezes` 依時間排序）。回傳新的時鐘。
 */
export function advanceClock(clock: number, delta: number, freezes: Freeze[], slows: readonly SlowSpan[] = []): number {
  if (slows.length > 0) return advanceSlowed(clock, delta, freezes, slows);
  let c = clock;
  let d = delta;
  while (d > 0) {
    const f = freezes[0];
    if (f === undefined || c + d < f.at) return c + d;
    if (f.at > c) {
      d -= f.at - c;
      c = f.at;
    }
    const use = Math.min(d, f.left);
    f.left -= use;
    d -= use;
    if (f.left <= 0) freezes.shift();
  }
  return c;
}

/** 放慢時每一小步的實際時間（毫秒）：倍速在這一小步內當作不變。 */
const SLOW_STEP_MS = 1;

/** 效果時鐘在 `c` 的倍速（好幾段重疊時取最慢的）。 */
export function rateAt(c: number, slows: readonly SlowSpan[]): number {
  let r = 1;
  for (const s of slows) r = Math.min(r, slowRate(c, s));
  return r;
}

/**
 * 有放慢時（6H-1 最後一擊）：一小步一小步走，每一步照目前的倍速前進；碰到停頓照舊停住、用掉停頓的時間。
 * 純函式（同樣的每幀時間得到同樣的時鐘）。
 */
function advanceSlowed(clock: number, delta: number, freezes: Freeze[], slows: readonly SlowSpan[]): number {
  let c = clock;
  let d = delta;
  while (d > 1e-9) {
    const f = freezes[0];
    if (f !== undefined && c >= f.at) {
      const use = Math.min(d, f.left);
      f.left -= use;
      d -= use;
      if (f.left <= 0) freezes.shift();
      continue;
    }
    const step = Math.min(d, SLOW_STEP_MS);
    const r = rateAt(c, slows);
    const next = c + step * r;
    if (f !== undefined && next >= f.at) {
      d -= (f.at - c) / r;
      c = f.at;
      continue;
    }
    c = next;
    d -= step;
  }
  return c;
}

/** 加一個停頓（同一刻已有時取長的；保持依時間排序）。比 `clock` 早的、長度 0 的不加。 */
export function addFreeze(freezes: Freeze[], at: number, ms: number, clock: number): void {
  if (ms <= 0 || at < clock) return;
  const same = freezes.find((f) => f.at === at);
  if (same !== undefined) {
    same.left = Math.max(same.left, ms);
    return;
  }
  freezes.push({ at, left: ms });
  freezes.sort((a, b) => a.at - b.at);
}
