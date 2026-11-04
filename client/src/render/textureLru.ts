// 貼圖快取的 LRU 上限（Phase 6N-3；美術 PM 6N-1 驗收第 3 節第 4 點）。
// 用 Map 的插入順序當「最久沒用」的順序：每次用到就移到最後；超過上限時從最前面淘汰並銷毀。
// 「釘住」的鍵（這一輪重畫場景用到的地形、物件、站著的小人）不淘汰，畫面上正在用的貼圖不會被銷毀；
// 只淘汰重畫之間由動畫（走路、技能片段、待機）臨時要的姿勢貼圖。剛放進去的那一張也不淘汰。
// 6N-4（美術 PM 6N-3 驗收第 4 點）：每個小人「目前正在用」的貼圖也釘住（`hold(owner, key)`，一個 owner 一張，
// 換貼圖時換掉），長時間停在同一個姿勢的人不會被淘汰後閃一下。
// 6R-F（前端審查第 9 點）：上限從 600 張改成位元組預算（預設 256MB，每張 `w*h*4`）。大小由 `set` 的第三個參數或
// `sizeOf` 給；沒給 `sizeOf` 時每張算 1（預算就是張數，測試用）。

/** 貼圖快取的位元組預算（6R-F）：256MB。 */
export const TEXTURE_BUDGET_BYTES = 256 * 1024 * 1024;

/** 一張 RGBA 貼圖的位元組數（`w*h*4`）。 */
export function rgbaBytes(w: number, h: number): number {
  return Math.max(0, Math.round(w)) * Math.max(0, Math.round(h)) * 4;
}

export interface Destroyable {
  destroy(options?: boolean): void;
}

interface Grave<V> {
  v: V;
  bytes: number;
}

export class TextureLru<V extends Destroyable> {
  private readonly map = new Map<string, V>();
  /** 每個鍵的大小（`sizeOf` 的單位）。 */
  private readonly sizes = new Map<string, number>();
  private total = 0;
  private pinned = new Set<string>();
  /** 小人 → 它目前正在用的鍵；鍵 → 有幾個小人在用。 */
  private readonly holdOf = new Map<string, string>();
  private readonly heldCount = new Map<string, number>();

  /** 淘汰後先不銷毀（6N-4）：放進 `graveyard`，等 `flushEvicted`（重畫場景、舊的小人都拆掉之後）才銷毀。 */
  private graveyard: Grave<V>[] = [];
  private graveBytes = 0;

  /**
   * `deferDestroy`（6N-4，ArtTextures 用）：淘汰時只從快取拿掉，銷毀延到下一次重畫場景的 `flushEvicted`。
   * 兩次重畫之間畫面上的節點可能還拿著被淘汰的貼圖（例如這一幀才換掉的待機姿勢），馬上銷毀會讓 Pixi 畫到
   * 已銷毀的貼圖（`null.alphaMode`／`uid`）而重建繪製器。
   */
  constructor(
    /** 預算（`sizeOf` 的單位；ArtTextures 用位元組）。 */
    readonly budget: number = TEXTURE_BUDGET_BYTES,
    private readonly deferDestroy = false,
    private readonly sizeOf: (v: V) => number = () => 1,
  ) {}

  /** 淘汰了、還沒銷毀的數量（測試、量測用）。 */
  get pendingDestroy(): number {
    return this.graveyard.length;
  }

  /** 淘汰了、還沒銷毀的大小。 */
  get pendingBytes(): number {
    return this.graveBytes;
  }

  /** 快取裡的總大小（不含淘汰了還沒銷毀的）。 */
  get bytes(): number {
    return this.total;
  }

  /** 銷毀延後的貼圖（`keep(v)` 為真的跳過、留到下一次；例如畫面上還有活著的 Sprite 拿著它）。 */
  flushEvicted(keep: (v: V) => boolean = () => false): void {
    const rest: Grave<V>[] = [];
    let bytes = 0;
    for (const g of this.graveyard) {
      if (keep(g.v)) {
        rest.push(g);
        bytes += g.bytes;
      } else g.v.destroy(true);
    }
    this.graveyard = rest;
    this.graveBytes = bytes;
  }

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

  /** 看一眼（不算使用、不改順序）。 */
  peek(key: string): V | undefined {
    return this.map.get(key);
  }

  has(key: string): boolean {
    return this.map.has(key);
  }

  /** 放進去；超過預算時淘汰最久沒用、沒釘住的（不含這一張）。`bytes` 省略時用 `sizeOf`。回傳被淘汰的鍵（測試用）。 */
  set(key: string, value: V, bytes?: number): string[] {
    this.forget(key);
    const size = Math.max(0, bytes ?? this.sizeOf(value));
    this.map.set(key, value);
    this.sizes.set(key, size);
    this.total += size;
    const out: string[] = [];
    if (this.total <= this.budget) return out;
    for (const [k, v] of this.map) {
      if (this.total <= this.budget) break;
      if (k === key || this.pinned.has(k) || this.heldCount.has(k)) continue;
      const b = this.sizes.get(k) ?? 0;
      if (this.deferDestroy) {
        this.graveyard.push({ v, bytes: b });
        this.graveBytes += b;
      } else v.destroy(true);
      this.forget(k);
      out.push(k);
    }
    return out;
  }

  /** 從快取拿掉（不銷毀）。 */
  private forget(key: string): void {
    if (!this.map.has(key)) return;
    this.map.delete(key);
    this.total -= this.sizes.get(key) ?? 0;
    this.sizes.delete(key);
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

  /** 放開 `keep` 以外的 owner（6R-F：重畫場景後，這一輪沒畫到的小人、殘影都放開）。 */
  releaseExcept(keep: ReadonlySet<string>): void {
    for (const owner of [...this.holdOf.keys()]) if (!keep.has(owner)) this.release(owner);
  }

  /** 目前有 hold 的 owner 數（量測用）。 */
  get owners(): number {
    return this.holdOf.size;
  }

  /** 全部放開。 */
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
    this.forget(key);
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
    this.sizes.clear();
    this.total = 0;
    this.pinned = new Set<string>();
    this.releaseAll();
    this.flushEvicted();
  }
}
