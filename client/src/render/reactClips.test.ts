// 6N-4：受擊與結果的片段（純函式、確定性）。
import { describe, expect, it } from "vitest";
import { humanHit } from "./motionClips";
import { creatureReact, DOWNED_OFFSET, DOWNED_ROTATION, dodgeSide, downedCreaturePose, guardOf, REACT_CLIPS, REACT_MS, reactFrame, sideOffset } from "./reactClips";
import type { GearItem } from "./appearance";

const item = (kind: string): GearItem => ({ kind }) as GearItem;
const SAMPLES = [0, 0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9, 1];

describe("react clips (6N-4)", () => {
  it("has the six clips with prototype lengths; a whole move stays far under 1.8 s", () => {
    expect([...REACT_CLIPS]).toEqual(["hit", "heavy", "dodge", "block", "down", "trapped"]);
    for (const c of REACT_CLIPS) {
      expect(REACT_MS[c]).toBeGreaterThanOrEqual(200);
      expect(REACT_MS[c]).toBeLessThanOrEqual(1800);
    }
    expect(REACT_MS.trapped).toBe(400); // 陷阱停頓 0.4 秒（6A-4d）
  });

  it("is deterministic and quantized (same t → same frame)", () => {
    for (const c of REACT_CLIPS) for (const t of SAMPLES) expect(reactFrame(c, t, { side: -1, guard: "shield" })).toEqual(reactFrame(c, t, { side: -1, guard: "shield" }));
    expect(reactFrame("hit", 0.333)).toEqual(reactFrame("hit", 0.334));
  });

  it("hit is the 6M-4 hit (white flash on the silhouette, lean back, step back and return)", () => {
    const h = humanHit(0);
    expect(reactFrame("hit", 0).flash).toBe(h.flash);
    expect(reactFrame("hit", 0).flash).toBeGreaterThan(0.8);
    expect(reactFrame("hit", 0.3).back).toBeGreaterThan(3);
    expect(reactFrame("hit", 1).back).toBeCloseTo(0, 1);
  });

  it("a heavy hit shakes more: steps back further and shudders", () => {
    const peak = (c: "hit" | "heavy") => Math.max(...SAMPLES.map((t) => reactFrame(c, t).back));
    expect(peak("heavy")).toBeGreaterThan(peak("hit"));
    const backs = Array.from({ length: 25 }, (_, i) => reactFrame("heavy", i / 24).back);
    const turns = backs.slice(1, -1).filter((b, i) => (b - backs[i]!) * (backs[i + 2]! - b) < 0).length;
    expect(turns).toBeGreaterThan(2); // 抖動：位移來回好幾次
  });

  it("dodge hops to the side, leaves a fading afterimage and lands back; no white flash", () => {
    const mid = reactFrame("dodge", 0.4, { side: 1 });
    expect(mid.side).toBeGreaterThan(8);
    expect(mid.air).toBeGreaterThan(0);
    expect(reactFrame("dodge", 0.4, { side: -1 }).side).toBeLessThan(-8);
    expect(reactFrame("dodge", 0.3).ghost).toBeGreaterThan(0.2);
    expect(reactFrame("dodge", 1).side).toBeCloseTo(0, 5);
    expect(reactFrame("dodge", 1).ghost).toBe(0);
    for (const t of SAMPLES) expect(reactFrame("dodge", t).flash).toBe(0);
  });

  it("dodge side is picked from the battle key, seq and unit (same input → same side; both sides occur)", () => {
    expect(dodgeSide("plain", 12, "u1")).toBe(dodgeSide("plain", 12, "u1"));
    const sides = new Set(Array.from({ length: 20 }, (_, i) => dodgeSide("plain", i, "u1")));
    expect(sides).toEqual(new Set([1, -1]));
  });

  it("block raises a shield, a weapon or the arms, sparks and takes a small step back", () => {
    expect(guardOf(item("sword"), item("shield_round"))).toBe("shield");
    expect(guardOf(undefined, item("shield_kite"))).toBe("shield");
    expect(guardOf(item("spear"), undefined)).toBe("weapon");
    expect(guardOf(undefined, undefined)).toBe("arm");
    expect(guardOf(item("talisman"), undefined)).toBe("arm");
    expect(guardOf(undefined, item("orb"))).toBe("arm");
    const shield = reactFrame("block", 0.3, { guard: "shield" }).pose;
    const weapon = reactFrame("block", 0.3, { guard: "weapon" }).pose;
    const arm = reactFrame("block", 0.3, { guard: "arm" }).pose;
    expect(shield.armF).toBeLessThan(-1);
    expect(weapon.arm).toBeLessThan(-1);
    expect(weapon.wpn).toBeUndefined(); // 照預設握法，不會從 0 度跳過去
    expect(arm.arm).toBeLessThan(-1);
    expect(arm.armF).toBeLessThan(-1);
    expect(reactFrame("block", 0.3).spark).toBeGreaterThan(0);
    expect(reactFrame("block", 0.9).spark).toBe(0);
    const back = Math.max(...SAMPLES.map((t) => reactFrame("block", t).back));
    expect(back).toBeGreaterThan(1);
    expect(back).toBeLessThan(reactFrame("hit", 0.3).back); // 退一小步（比受擊小）
    expect(reactFrame("block", 1).pose).toEqual({});
  });

  it("down: flash → knees buckle → falls sideways; the last frame is the downed icon's transform with no pose", () => {
    expect(reactFrame("down", 0).flash).toBeGreaterThan(0.8);
    const buckled = reactFrame("down", 0.5);
    expect(buckled.pose.kneeN).toBeGreaterThan(1);
    expect(buckled.fall).toBe(0);
    const end = reactFrame("down", 1);
    expect(end.fall).toBe(1);
    expect(end.rotation).toBeCloseTo(DOWNED_ROTATION, 2);
    expect(end.dx).toBe(DOWNED_OFFSET.x);
    expect(end.dy).toBe(DOWNED_OFFSET.y);
    expect(end.pose).toEqual({});
    expect(end.back).toBe(0);
    // 側倒是單調的（不會倒一半又站起來）
    const falls = SAMPLES.map((t) => reactFrame("down", t).fall);
    for (let i = 1; i < falls.length; i++) expect(falls[i]!).toBeGreaterThanOrEqual(falls[i - 1]!);
  });

  it("trapped: the flash comes when the jaws close (0.25), the body cringes, then stands straight", () => {
    expect(reactFrame("trapped", 0.1).flash).toBe(0);
    expect(reactFrame("trapped", 0.26).flash).toBeGreaterThan(0.5);
    expect(reactFrame("trapped", 0.5).pose.kneeN).toBeGreaterThan(0.3);
    expect(reactFrame("trapped", 1).pose).toEqual({});
  });

  it("side offset follows the facing (south-north has perspective)", () => {
    expect(sideOffset("east", 10)).toEqual({ x: 0, y: 8 });
    expect(sideOffset("west", 10)).toEqual({ x: 0, y: -8 });
    expect(sideOffset("south", 10)).toEqual({ x: -10, y: 0 });
    expect(sideOffset("north", 10)).toEqual({ x: 10, y: 0 });
  });

  it("creatures: hit and down use the shared clips; dodge and block are a lighter hit without flash", () => {
    expect(creatureReact("hit", 0).flash).toBeGreaterThan(0.8);
    // QK-4：受擊是 Q 版分部件片段（clip），閃避、格擋是整隻往後讓的輕版（不換片段、沒有白閃）
    expect(creatureReact("hit", 0.3).clip).toBe("hit");
    expect(creatureReact("dodge", 0.3).clip).toBeUndefined();
    expect(creatureReact("dodge", 0.3).dx ?? 0).toBeLessThan(0);
    expect(Math.abs(creatureReact("dodge", 0.3).dx ?? 0)).toBeLessThan(6);
    expect(creatureReact("dodge", 0).flash).toBeUndefined();
    expect(creatureReact("block", 0.3).flash).toBeUndefined();
    // 倒下的最後一格＝重畫後的倒地樣子（不會跳回站著）；不變淡（透明度交給倒地外觀）
    expect(creatureReact("down", 1)).toEqual(downedCreaturePose());
    expect(downedCreaturePose().alpha).toBe(1);
    expect(downedCreaturePose()).toMatchObject({ clip: "death", u: 1 }); // QK-4：倒下片段的最後一格
  });
});
