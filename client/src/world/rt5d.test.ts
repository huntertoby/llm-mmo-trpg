// Phase RT-5d：主城開場第三次驗收修正（docs/art/RT-5c檢查.md）。半坐起的手撐在地上、醒來時不握武器。
import { describe, expect, it } from "vitest";
import type { DollSpec } from "../render/appearance";
import { AWAKEN_HERO, AWAKEN_SIT_POSE, awakenHeroSpec, drawAwakenArt } from "../render/eventArtAwaken";
import { devCameraShift, shiftCamera } from "./devCamera";
import { captionShiftDecor, clearOfHud, NUDGE_FAR, NUDGE_MAX, nudgeCamera, type NudgeTarget } from "./hudAvoid";
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

describe("RT-5d 必修 2：開發用的鏡頭位移（拍 1600 寬的夾邊畫面）", () => {
  it("只在 `?dev=1` 時有效；格式不對或 0,0 時不位移", () => {
    expect(devCameraShift("?dev=1&devcam=0,260")).toEqual({ x: 0, y: 260 });
    expect(devCameraShift("?dev=1&devcam=-40,12.5")).toEqual({ x: -40, y: 12.5 });
    expect(devCameraShift("?devcam=0,260")).toBeNull();
    expect(devCameraShift("?dev=0&devcam=0,260")).toBeNull();
    expect(devCameraShift("?dev=1")).toBeNull();
    expect(devCameraShift("?dev=1&devcam=0,0")).toBeNull();
    expect(devCameraShift("?dev=1&devcam=abc")).toBeNull();
    expect(devCameraShift("?dev=1&devcam=1,2,3")).toBeNull();
  });

  it("位移加在鏡頭上；沒位移時原樣回傳", () => {
    const cam = { x: 134, y: 465, scale: 1 };
    expect(shiftCamera(cam, null)).toBe(cam);
    expect(shiftCamera(cam, { x: 0, y: 260 })).toEqual({ x: 134, y: 725, scale: 1 });
  });
});

// 1600×900 主角站在西邊（rt5c_7 那一幀）時實機量到的鏡頭微調輸入（舞台 1568×832）
const R = (l: number, t: number, w: number, h: number, weight?: number): NudgeTarget => ({ left: l, top: t, width: w, height: h, ...(weight === undefined ? {} : { weight }) });
const WEST = {
  cam: { x: 0, y: 284.75, scale: 1 },
  view: { width: 1568, height: 832 },
  content: { width: 1536, height: 1180 },
  insets: { top: 220, right: 222.5, bottom: 77.5, left: 0 },
  reach: { top: 12, right: 222.5, bottom: 127.5, left: 0 },
  avoid: [R(10, 10, 313, 93), R(10, 123, 188, 98), R(10, 228, 45, 45), R(1346, 10, 213, 30), R(1346, 45, 213, 130), R(1346, 180, 213, 38), R(1346, 223, 213, 30), R(1346, 458, 213, 188), R(548, 755, 473, 70), R(423, 715, 721, 30)],
  hero: R(96, 700, 48, 96),
};
const MAIN = [R(672, 556, 48, 96, 3)];
const STONES = [R(1422.5, 257, 105.5, 203), R(728, 1025, 100, 155), R(8, 655, 84.5, 189), R(440, 10, 153.5, 114), R(1374.5, 1025, 105.5, 155)];
const BODIES = [R(1448, 298, 32, 66, 3), R(776, 1066, 32, 66, 3), R(56, 682, 32, 66, 3), R(536, 58, 32, 66, 3), R(1400, 1066, 32, 66, 3)];
const ASH = BODIES[1]!;

describe("RT-5d 小修 3：碑身露出一部分、被下方 HUD 蓋住時，鏡頭優先往上推（可以超過 2 格）", () => {
  it("主角在西邊：荒原碑身整個露出來（不再被快捷列、說明列蓋住），主角也沒被蓋", () => {
    const cam = nudgeCamera({ ...WEST, targets: [...MAIN, ...STONES, ...BODIES.map((b) => ({ ...b, far: true }))] });
    expect(clearOfHud(ASH, cam, WEST.view, WEST.avoid)).toBe(true);
    expect(clearOfHud(WEST.hero, cam, WEST.view, WEST.avoid)).toBe(true);
    expect(cam.y - WEST.cam.y).toBeGreaterThan(NUDGE_MAX);
    expect(cam.y - WEST.cam.y).toBeLessThanOrEqual(NUDGE_FAR);
    expect(cam.x).toBe(WEST.cam.x);
  });

  it("沒標 `far` 的目標照舊最多 2 格（RT-5c 的行為：荒原碑身推不出來）", () => {
    const cam = nudgeCamera({ ...WEST, targets: [...MAIN, ...STONES, ...BODIES] });
    expect(Math.abs(cam.y - WEST.cam.y)).toBeLessThanOrEqual(NUDGE_MAX);
    expect(clearOfHud(ASH, cam, WEST.view, WEST.avoid)).toBe(false);
  });
});

describe("RT-5d 小修 4：說明列也盡量不壓源晶燈的柱身", () => {
  const cap = { left: 665, top: 725, width: 270, height: 21 };
  const hud = [R(548, 755, 473, 70), cap];
  const lamp = R(797, 680, 22, 68);
  it("壓到燈柱時挪開（挪得少的那邊），挪過去也不壓燈柱", () => {
    const dx = captionShiftDecor(cap, [], [lamp], hud, 1568);
    expect(dx).not.toBe(0);
    const moved = { ...cap, left: cap.left + dx };
    expect(moved.left + moved.width <= lamp.left || moved.left >= lamp.left + lamp.width).toBe(true);
    expect(Math.abs(dx)).toBeLessThan(170);
  });

  it("沒壓到東西就不挪；兩邊都讓不開燈柱時，退回只避開碑身", () => {
    expect(captionShiftDecor(cap, [], [R(100, 100, 20, 60)], hud, 1568)).toBe(0);
    // 一整排燈柱擋住說明列可以去的地方（讓不開），碑身也壓在說明列下面：只避開碑身
    const body = R(700, 700, 32, 66);
    const lamps = [R(4, 690, 1560, 68)];
    const dx = captionShiftDecor(cap, [body], lamps, hud, 1568);
    const moved = { ...cap, left: cap.left + dx };
    expect(dx).not.toBe(0);
    expect(moved.left + moved.width <= body.left || moved.left >= body.left + body.width).toBe(true);
  });
});
