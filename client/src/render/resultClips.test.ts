// 6N-5：格擋成功的攻擊者被彈開、復活、勝利的片段（純函式）；四周變暗的強度。
import { describe, expect, it } from "vitest";
import { creatureReact, creatureResult, DOWNED_OFFSET, DOWNED_ROTATION, reactFrame, RESULT_CLIPS, RESULT_MS, resultFrame, riseRing, victoryPose } from "./reactClips";
import { vignetteAlpha } from "./resultEffects";

const SAMPLES = [0, 0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9, 1];

describe("result clips (6N-5)", () => {
  it("lengths within 200–520 ms", () => {
    for (const c of RESULT_CLIPS) {
      expect(RESULT_MS[c]).toBeGreaterThanOrEqual(200);
      expect(RESULT_MS[c]).toBeLessThanOrEqual(520);
    }
  });

  it("deterministic: same t → same frame", () => {
    for (const c of RESULT_CLIPS) for (const t of SAMPLES) expect(resultFrame(c, t, "sheathe")).toEqual(resultFrame(c, t, "sheathe"));
    for (const c of RESULT_CLIPS) for (const t of SAMPLES) expect(creatureResult(c, t)).toEqual(creatureResult(c, t));
  });

  it("recoil: pushed back about half a step, no flash, back in place at the end", () => {
    const peak = Math.max(...SAMPLES.map((t) => resultFrame("recoil", t).back));
    expect(peak).toBeGreaterThanOrEqual(7);
    for (const t of SAMPLES) expect(resultFrame("recoil", t).flash).toBe(0);
    expect(resultFrame("recoil", 1)).toMatchObject({ back: 0, pose: {} });
  });

  it("rise: the first frame is the down clip's last frame (no jump from the downed icon); ends standing", () => {
    const first = resultFrame("rise", 0);
    const down = reactFrame("down", 1);
    expect(first.pose).toEqual(down.pose);
    expect(first.rotation).toBe(down.rotation);
    expect([first.dx, first.dy, first.fall]).toEqual([down.dx, down.dy, down.fall]);
    expect(first.rotation).toBeCloseTo(DOWNED_ROTATION, 1);
    expect([first.dx, first.dy]).toEqual([DOWNED_OFFSET.x, DOWNED_OFFSET.y]);
    const last = resultFrame("rise", 1);
    expect(last).toMatchObject({ pose: {}, rotation: 0, dx: 0, dy: 0, fall: 0 });
    // 單調站起來（不回倒）
    const falls = SAMPLES.map((t) => resultFrame("rise", t).fall);
    for (let i = 1; i < falls.length; i++) expect(falls[i]!).toBeLessThanOrEqual(falls[i - 1]!);
  });

  it("rise: the green ring shows in the middle and is gone at both ends", () => {
    expect(riseRing(0)).toBe(0);
    expect(riseRing(1)).toBe(0);
    expect(riseRing(0.55)).toBeGreaterThan(0.8);
  });

  it("creature rise starts on the downed creature pose", () => {
    expect(creatureResult("rise", 0)).toEqual(creatureReact("down", 1));
    expect(creatureResult("rise", 1)).toMatchObject({ dx: 0, rot: 0 });
  });

  it("victory: raise lifts the main arm high and hops; sheathe lowers it; both end standing", () => {
    expect(resultFrame("victory", 0.5, "raise").pose.arm!).toBeLessThan(-2);
    expect(Math.max(...SAMPLES.map((t) => resultFrame("victory", t, "raise").air))).toBeGreaterThan(2);
    expect(resultFrame("victory", 0.5, "sheathe").pose.arm!).toBeGreaterThan(0.3);
    expect(Math.max(...SAMPLES.map((t) => resultFrame("victory", t, "sheathe").air))).toBe(0);
    for (const k of ["raise", "sheathe"] as const) expect(resultFrame("victory", 1, k)).toMatchObject({ pose: {}, air: 0 });
  });

  it("victory pose is picked by the hash (battle key:seq:unit:victory); both show up", () => {
    expect(victoryPose("m1", 9, "u_a")).toBe(victoryPose("m1", 9, "u_a"));
    const seen = new Set(Array.from({ length: 24 }, (_, i) => victoryPose("m1", 9, `u_${i}`)));
    expect([...seen].sort()).toEqual(["raise", "sheathe"]);
  });

  it("boss vignette: darkens in, holds, lightens back within its 0.3 s", () => {
    expect(vignetteAlpha(0)).toBe(0);
    expect(vignetteAlpha(0.5)).toBe(1);
    expect(vignetteAlpha(1)).toBe(0);
  });
});
