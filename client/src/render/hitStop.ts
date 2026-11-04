// 命中時的停頓（Phase 6N-5，選項 B：特效加停頓，不做慢動作）：繪製器的效果時鐘走到停頓那一刻就停住，
// 用掉停頓的時間再往下走。純函式（時間 → 時間），只吃 ticker 給的每幀時間，不讀時鐘。
// 停住的時候所有效果（身體片段、特效、浮動數字）都停在同一格；按住空白鍵加速時 ticker 的每幀時間變長，停頓一起變短。

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
export function advanceClock(clock: number, delta: number, freezes: Freeze[]): number {
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
