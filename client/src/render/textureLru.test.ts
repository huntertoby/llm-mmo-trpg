// 6N-3：貼圖快取的 LRU 上限（6R-F 起是位元組預算）。
import { describe, expect, it } from "vitest";
import { rgbaBytes, TEXTURE_BUDGET_BYTES, TextureLru } from "./textureLru";

class Fake {
  destroyed = false;
  constructor(readonly id: string) {}
  destroy(): void {
    this.destroyed = true;
  }
}

describe("texture LRU", () => {
  it("6R-F: the default budget is 256MB of w*h*4 bytes, not a count", () => {
    expect(TEXTURE_BUDGET_BYTES).toBe(256 * 1024 * 1024);
    expect(rgbaBytes(285, 285)).toBe(285 * 285 * 4);
    // 小人貼圖（約 1MB 一張）：256MB 放得下約 256 張，不是 600 張
    const mb = 1024 * 1024;
    const lru = new TextureLru<Fake>();
    for (let i = 0; i < 400; i++) lru.set(`k${i}`, new Fake(`k${i}`), mb);
    expect(lru.size).toBe(256);
    expect(lru.bytes).toBe(256 * mb);
    expect(lru.has("k143")).toBe(false);
    expect(lru.has("k144")).toBe(true);
  });

  it("6R-F: big textures evict more entries than small ones (budget, not count)", () => {
    const lru = new TextureLru<Fake>(100, false, () => 10);
    for (let i = 0; i < 10; i++) lru.set(`s${i}`, new Fake(`s${i}`)); // 10 × 10 = 100：剛好滿
    expect(lru.size).toBe(10);
    const big = new Fake("big");
    expect(lru.set("big", big, 45)).toEqual(["s0", "s1", "s2", "s3", "s4"]); // 要騰出 45：淘汰 5 張小的
    expect(lru.bytes).toBe(95);
    expect(big.destroyed).toBe(false);
  });

  it("6R-F: held and pinned keys are never evicted by the byte budget", () => {
    const lru = new TextureLru<Fake>(30, true);
    const held = new Fake("held");
    lru.set("held", held, 10);
    lru.hold("u1", "held");
    const pinned = new Fake("pinned");
    lru.set("pinned", pinned, 10);
    lru.pin("pinned");
    for (let i = 0; i < 50; i++) lru.set(`w${i}`, new Fake(`w${i}`), 10);
    lru.flushEvicted();
    expect(lru.has("held")).toBe(true);
    expect(lru.has("pinned")).toBe(true);
    expect(held.destroyed).toBe(false);
    expect(pinned.destroyed).toBe(false);
    expect(lru.bytes).toBe(30);
  });

  it("6R-F: releaseExcept frees owners that were not drawn this round", () => {
    const lru = new TextureLru<Fake>(10);
    lru.set("a", new Fake("a"));
    lru.set("b", new Fake("b"));
    lru.hold("alive", "a");
    lru.hold("dead", "b");
    lru.hold("ghost:x#1", "b");
    lru.releaseExcept(new Set(["alive"]));
    expect(lru.isHeld("a")).toBe(true);
    expect(lru.isHeld("b")).toBe(false);
    expect(lru.owners).toBe(1);
  });

  it("6R-F: pending bytes count evicted-but-not-destroyed textures; keep() leaves live ones", () => {
    const lru = new TextureLru<Fake>(10, true);
    const a = new Fake("a");
    lru.set("a", a, 6);
    lru.set("b", new Fake("b"), 6);
    expect(lru.pendingBytes).toBe(6);
    lru.flushEvicted((v) => v === a);
    expect(a.destroyed).toBe(false);
    expect(lru.pendingBytes).toBe(6);
    lru.flushEvicted();
    expect(a.destroyed).toBe(true);
    expect(lru.pendingBytes).toBe(0);
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

  it("never evicts the texture a unit is showing right now (6N-4; art PM 6N-3 check, point 4)", () => {
    const lru = new TextureLru<Fake>(3);
    const idle = new Fake("idle-pose");
    lru.set("idle-pose", idle);
    lru.hold("u1", "idle-pose"); // 一直停在同一個待機姿勢的人
    for (let i = 0; i < 20; i++) lru.set(`walk${i}`, new Fake(`walk${i}`)); // 別人走路要了很多新姿勢
    expect(lru.has("idle-pose")).toBe(true);
    expect(idle.destroyed).toBe(false);
    expect(lru.size).toBe(3);
  });

  it("a hold moves with the unit's current texture and is released on release / releaseAll", () => {
    const lru = new TextureLru<Fake>(2);
    lru.set("a", new Fake("a"));
    lru.hold("u1", "a");
    lru.set("b", new Fake("b"));
    lru.hold("u1", "b"); // 換貼圖：a 不再釘住
    expect(lru.isHeld("a")).toBe(false);
    expect(lru.isHeld("b")).toBe(true);
    lru.set("c", new Fake("c"));
    expect(lru.has("a")).toBe(false);
    expect(lru.has("b")).toBe(true);
    // 兩個人用同一張：一個放開還釘著
    lru.hold("u2", "b");
    lru.release("u1");
    expect(lru.isHeld("b")).toBe(true);
    lru.releaseAll();
    expect(lru.isHeld("b")).toBe(false);
    lru.set("d", new Fake("d"));
    lru.set("e", new Fake("e"));
    expect(lru.has("b")).toBe(false);
  });

  it("over the cap, every unit's current texture on screen survives (town idle bug; 6N-4)", () => {
    // 城鎮：20 個人（主角、NPC、朋友影子、敵群）各自停在某個待機姿勢；同時別人一直換新姿勢，遠超過上限
    const lru = new TextureLru<Fake>(50, true);
    const shown = new Map<string, Fake>();
    for (let u = 0; u < 20; u++) {
      const key = `idle:u${u}:0`;
      const tex = new Fake(key);
      lru.set(key, tex);
      lru.hold(`u${u}`, key);
      shown.set(`u${u}`, tex);
    }
    for (let i = 0; i < 2000; i++) {
      const u = i % 20;
      if (i % 7 === 0) {
        // 有人換到新的姿勢：放開舊的、釘住新的（舊的之後才可能被淘汰）
        const key = `idle:u${u}:${i}`;
        const tex = new Fake(key);
        lru.set(key, tex);
        lru.hold(`u${u}`, key);
        shown.set(`u${u}`, tex);
      } else lru.set(`walk:${i}`, new Fake(`walk:${i}`));
      if (i % 300 === 299) lru.flushEvicted(); // 偶爾重畫場景
    }
    lru.flushEvicted();
    for (const tex of shown.values()) expect(tex.destroyed).toBe(false);
    expect(lru.size).toBeLessThanOrEqual(50);
  });

  it("deferred destroy: evicted textures are destroyed only on flush (after the scene is rebuilt)", () => {
    const lru = new TextureLru<Fake>(1, true);
    const a = new Fake("a");
    lru.set("a", a);
    lru.set("b", new Fake("b"));
    expect(lru.has("a")).toBe(false);
    expect(a.destroyed).toBe(false);
    expect(lru.pendingDestroy).toBe(1);
    lru.flushEvicted((v) => v.id === "a");
    expect(a.destroyed).toBe(false);
    lru.flushEvicted();
    expect(a.destroyed).toBe(true);
    expect(lru.pendingDestroy).toBe(0);
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
