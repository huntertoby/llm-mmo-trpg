// 6N-3：貼圖快取的 LRU 上限（600 張）。
import { describe, expect, it } from "vitest";
import { TEXTURE_CAP, TextureLru } from "./textureLru";

class Fake {
  destroyed = false;
  constructor(readonly id: string) {}
  destroy(): void {
    this.destroyed = true;
  }
}

describe("texture LRU", () => {
  it("caps at 600 by default", () => {
    expect(TEXTURE_CAP).toBe(600);
    const lru = new TextureLru<Fake>();
    for (let i = 0; i < 700; i++) lru.set(`k${i}`, new Fake(`k${i}`));
    expect(lru.size).toBe(600);
    expect(lru.has("k99")).toBe(false);
    expect(lru.has("k100")).toBe(true);
  });

  it("evicts the least recently used and destroys it", () => {
    const lru = new TextureLru<Fake>(3);
    const a = new Fake("a");
    lru.set("a", a);
    lru.set("b", new Fake("b"));
    lru.set("c", new Fake("c"));
    lru.get("a"); // a 變成最近用過
    expect(lru.set("d", new Fake("d"))).toEqual(["b"]);
    expect(lru.keys()).toEqual(["c", "a", "d"]);
    expect(a.destroyed).toBe(false);
  });

  it("never evicts pinned keys (the scene drawn this round) nor the one just added", () => {
    const lru = new TextureLru<Fake>(2);
    const tile = new Fake("tile");
    lru.set("tile", tile);
    lru.pin("tile");
    lru.set("p1", new Fake("p1"));
    const p2 = new Fake("p2");
    expect(lru.set("p2", p2)).toEqual(["p1"]);
    expect(tile.destroyed).toBe(false);
    // 全部釘住時暫時超過上限，也不銷毀剛放進去的
    lru.pin("p2");
    const p3 = new Fake("p3");
    expect(lru.set("p3", p3)).toEqual([]);
    expect(lru.size).toBe(3);
    expect(p3.destroyed).toBe(false);
    // 下一輪重畫解除釘選後，再放就照順序淘汰
    lru.unpinAll();
    expect(lru.set("p4", new Fake("p4"))).toEqual(["tile", "p2"]);
    expect(tile.destroyed).toBe(true);
  });

  it("a re-request after eviction makes a fresh entry (nothing points at a destroyed one)", () => {
    const lru = new TextureLru<Fake>(2);
    lru.set("a", new Fake("a1"));
    lru.set("b", new Fake("b"));
    lru.set("c", new Fake("c"));
    expect(lru.get("a")).toBeUndefined();
    lru.set("a", new Fake("a2"));
    expect(lru.get("a")?.id).toBe("a2");
    expect(lru.get("a")?.destroyed).toBe(false);
    for (const [, v] of lru.entries()) expect(v.destroyed).toBe(false);
  });

  it("clear destroys everything", () => {
    const lru = new TextureLru<Fake>(5);
    const x = new Fake("x");
    lru.set("x", x);
    lru.clear();
    expect(lru.size).toBe(0);
    expect(x.destroyed).toBe(true);
  });
});
