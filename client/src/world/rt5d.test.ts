// Phase RT-5d：主城開場第三次驗收修正（docs/art/RT-5c檢查.md）。半坐起的手撐在地上、醒來時不握武器。
import { describe, expect, it } from "vitest";
import type { DollSpec } from "../render/appearance";
import { AWAKEN_HERO, AWAKEN_SIT_POSE, awakenHeroSpec, drawAwakenArt } from "../render/eventArtAwaken";
import { heroDoll } from "./opening";

type M = [number, number, number, number, number, number];
const mul = (m: M, n: M): M => [m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1], m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3], m[0] * n[4] + m[2] * n[5] + m[4], m[1] * n[4] + m[3] * n[5] + m[5]];
const apply = (m: M, x: number, y: number): [number, number] => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];

/** 追蹤畫布變換的假 context：記下近側手（`translate(4.6,-24)` 之後的原點）與遠側手（半徑 1.7 的點）在插圖座標的位置。 */
function trace(draw: (ctx: CanvasRenderingContext2D) => void): { near: [number, number][]; far: [number, number][]; calls: string[] } {
  let m: M = [1, 0, 0, 1, 0, 0];
  const stack: M[] = [];
  const near: [number, number][] = [];
  const far: [number, number][] = [];
  const calls: string[] = [];
  const target: Record<string, unknown> = {};
  const fns: Record<string, (...a: number[]) => void> = {
    save: () => stack.push(m),
    restore: () => {
      m = stack.pop() ?? m;
    },
    translate: (x, y) => {
      m = mul(m, [1, 0, 0, 1, x, y]);
      if (Math.abs(x - 4.6) < 1e-9 && Math.abs(y + 24) < 1e-9) near.push(apply(m, 0, 0));
    },
    rotate: (a) => {
      m = mul(m, [Math.cos(a), Math.sin(a), -Math.sin(a), Math.cos(a), 0, 0]);
    },
    scale: (x, y) => {
      m = mul(m, [x, 0, 0, y, 0, 0]);
    },
    ellipse: (x, y, rx, ry) => {
      if (Math.abs(x - 5.6) < 1e-9 && Math.abs(y + 27) < 1e-9 && rx === 1.7 && ry === 1.7) far.push(apply(m, x, y));
    },
  };
  const ctx = new Proxy(target, {
    get(t, k) {
      if (typeof k === "symbol") return undefined;
      if (k in t) return t[k];
      if (k === "createLinearGradient" || k === "createRadialGradient" || k === "createPattern") return () => ({ addColorStop: () => undefined });
      if (k === "measureText") return () => ({ width: 10 });
      return (...args: number[]) => {
        calls.push(String(k));
        fns[k]?.(...args);
      };
    },
    set(t, k, v) {
      if (typeof k === "string") t[k] = v;
      return true;
    },
  });
  draw(ctx as unknown as CanvasRenderingContext2D);
  return { near, far, calls };
}

const armed = (): DollSpec => {
  const hero = heroDoll(null);
  return { ...hero, gear: { ...hero.gear, main_hand: { kind: "sword" }, off_hand: { kind: "shield_round" } } };
};

describe("RT-5d 必修 1：半坐起是兩手在髖後撐地", () => {
  it("醒來時先把武器收起來：主手、副手都不畫（躺著、坐起兩格都是）", () => {
    const spec = awakenHeroSpec(armed());
    expect(spec.gear.main_hand).toBeUndefined();
    expect(spec.gear.off_hand).toBeUndefined();
    // 其他裝備不動
    expect(spec.look).toEqual(armed().look);
    // 實際畫出來：有武器的主角和空手的主角，兩格的指令流都一樣（武器沒有畫）
    const gear = { ...armed().gear };
    delete gear.main_hand;
    delete gear.off_hand;
    const bare: DollSpec = { ...armed(), gear };
    for (const pose of [0, 1] as const) expect(trace((c) => drawAwakenArt(c, armed(), pose, [], "")).calls).toEqual(trace((c) => drawAwakenArt(c, bare, pose, [], "")).calls);
  });

  it("上半身往後仰 30～35°", () => {
    const deg = (-(AWAKEN_SIT_POSE.lean ?? 0) * 180) / Math.PI;
    expect(deg).toBeGreaterThanOrEqual(30);
    expect(deg).toBeLessThanOrEqual(35);
  });

  it("兩手都在髖部後方，手掌（手的下緣）落在地面線上（容差 1.5）；手臂打直（手肘不彎）", () => {
    const sit = AWAKEN_HERO[1];
    const { near, far } = trace((c) => drawAwakenArt(c, heroDoll(null), 1, [], ""));
    expect(near).toHaveLength(1);
    expect(far).toHaveLength(1);
    const ground = sit.y; // 坐著時原點＝髖部正下方的地面
    const palm = 1.8 * 1.05; // 手的半徑（紙娃娃 1.8，插圖放大 1.05）
    for (const [x, y] of [near[0]!, far[0]!]) {
      expect(x).toBeLessThan(sit.x - 4); // 髖部後方（主角面向東，後方＝西）
      expect(Math.abs(y + palm - ground)).toBeLessThanOrEqual(1.5);
    }
    expect(AWAKEN_SIT_POSE.elbow ?? 0).toBe(0);
    expect(AWAKEN_SIT_POSE.elbowF ?? 0).toBe(0);
    // 遠側的手在更後面一點（從近側的手後面露出來）
    expect(far[0]![0]).toBeLessThan(near[0]![0]);
  });
});
