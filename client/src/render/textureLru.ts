// 貼圖快取的 LRU 上限（Phase 6N-3；美術 PM 6N-1 驗收第 3 節第 4 點：上限 600 張，約 6M-3 量測的 4 倍）。
// 用 Map 的插入順序當「最久沒用」的順序：每次用到就移到最後；超過上限時從最前面淘汰並銷毀。
// 「釘住」的鍵（這一輪重畫場景用到的地形、物件、站著的小人）不淘汰，畫面上正在用的貼圖不會被銷毀；
// 只淘汰重畫之間由動畫（走路、技能片段、待機）臨時要的姿勢貼圖。剛放進去的那一張也不淘汰。
// 6N-4（美術 PM 6N-3 驗收第 4 點）：每個小人「目前正在用」的貼圖也釘住（`hold(owner, key)`，一個 owner 一張，
// 換貼圖時換掉），長時間停在同一個姿勢的人不會被淘汰後閃一下。

export const TEXTURE_CAP = 600;

export interface Destroyable {
  destroy(options?: boolean): void;
}

export class TextureLru<V extends Destroyable> {
  private readonly map = new Map<string, V>();
  private pinned = new Set<string>();
  /** 小人 → 它目前正在用的鍵；鍵 → 有幾個小人在用。 */
  private readonly holdOf = new Map<string, string>();
  private readonly heldCount = new Map<string, number>();

  constructor(readonly cap: number = TEXTURE_CAP) {}

  get size(): number {
    return this.map.size;
  }

  /** 取用（算一次使用，移到最後）。 */
  get(key: string): V | undefined {
    const hit = this.map.get(key);
    if (hit !== undefined) {
      this.map.delete(key);
      this.map.set(key, hit);
    }
    return hit;
  }

  has(key: string): boolean {
    return this.map.has(key);
  }

  /** 放進去；超過上限時淘汰最久沒用、沒釘住的（不含這一張）。回傳被淘汰的鍵（測試用）。 */
  set(key: string, value: V): string[] {
    this.map.delete(key);
    this.map.set(key, value);
    const out: string[] = [];
    if (this.map.size <= this.cap) return out;
    for (const [k, v] of this.map) {
      if (this.map.size <= this.cap) break;
      if (k === key || this.pinned.has(k) || this.heldCount.has(k)) continue;
      v.destroy(true);
      this.map.delete(k);
      out.push(k);
    }
    return out;
  }

  /** 釘住一個鍵（這一輪重畫用到）。 */
  pin(key: string): void {
    this.pinned.add(key);
  }

  /** 重新開始一輪釘選（重畫場景前）。 */
  unpinAll(): void {
    this.pinned = new Set<string>();
  }

  /** `owner`（小人）目前正在用 `key`：釘住，直到它換成別張、`release` 或 `releaseAll`。 */
  hold(owner: string, key: string): void {
    const old = this.holdOf.get(owner);
    if (old === key) return;
    if (old !== undefined) this.unhold(old);
    this.holdOf.set(owner, key);
    this.heldCount.set(key, (this.heldCount.get(key) ?? 0) + 1);
  }

  release(owner: string): void {
    const old = this.holdOf.get(owner);
    if (old === undefined) return;
    this.holdOf.delete(owner);
    this.unhold(old);
  }

  /** 全部放開（重畫場景前：小人都重建了，重畫用到的貼圖改由這一輪的釘選保護）。 */
  releaseAll(): void {
    this.holdOf.clear();
    this.heldCount.clear();
  }

  /** 正被某個小人用著的鍵（測試用）。 */
  isHeld(key: string): boolean {
    return this.heldCount.has(key);
  }

  private unhold(key: string): void {
    const n = (this.heldCount.get(key) ?? 0) - 1;
    if (n > 0) this.heldCount.set(key, n);
    else this.heldCount.delete(key);
  }

  /** 刪掉一個並銷毀。 */
  drop(key: string): void {
    const v = this.map.get(key);
    if (v === undefined) return;
    v.destroy(true);
    this.map.delete(key);
  }

  keys(): string[] {
    return [...this.map.keys()];
  }

  entries(): IterableIterator<[string, V]> {
    return this.map.entries();
  }

  clear(): void {
    for (const v of this.map.values()) v.destroy(true);
    this.map.clear();
    this.pinned = new Set<string>();
    this.releaseAll();
  }
}
