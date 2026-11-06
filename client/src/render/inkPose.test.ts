// Phase 6M-1：骨架姿勢鉤子 — 工具函式、確定性、前傾時腳留在地上、髖膝、側面手肘與另一隻手、正面背面抬腳擺手。
// 用一個會追蹤變換矩陣的假畫布：每次 fill 記下填色與「目前路徑在畫布座標的外框」，用填色找部件。
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Facing } from "../api/types";
import type { DollSpec } from "./appearance";
import { darken } from "./color";
import { addPose, cleanPose, mixPose, POSE_KEYS, pz, REST_POSE, scalePose, type InkPose } from "./inkPose";
import { drawFigure } from "./paperdoll";
import { resolveDollT } from "./testDolls";
import { setDollSkin } from "./inkStyle";

// QK-1：這個檔案鎖 C 手繪墨線的畫法（C 的畫法留著給 QK-2～QK-4），畫面預設改成 Q 版之後在這裡指定 C。
setDollSkin("c");

type M = [number, number, number, number, number, number];
interface Fill {
  color: string;
  box: [number, number, number, number];
}

function tracker(): { ctx: CanvasRenderingContext2D; fills: Fill[] } {
  let m: M = [1, 0, 0, 1, 0, 0];
  const stack: M[] = [];
  let pts: Array<[number, number]> = [];
  const fills: Fill[] = [];
  const props: Record<string, unknown> = {};
  const mul = (n: M): void => {
    const [a, b, c, d, e, f] = m;
    m = [a * n[0] + c * n[1], b * n[0] + d * n[1], a * n[2] + c * n[3], b * n[2] + d * n[3], a * n[4] + c * n[5] + e, b * n[4] + d * n[5] + f];
  };
  const add = (x: number, y: number): void => {
    pts.push([m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]]);
  };
  const record = (): void => {
    if (pts.length === 0) return;
    const xs = pts.map((p) => p[0]);
    const ys = pts.map((p) => p[1]);
    fills.push({ color: String(props.fillStyle), box: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)] });
  };
  const api: Record<string, (...a: number[]) => void> = {
    save: () => void stack.push([...m]),
    restore: () => {
      m = stack.pop() ?? m;
    },
    translate: (x, y) => mul([1, 0, 0, 1, x, y]),
    rotate: (r) => mul([Math.cos(r), Math.sin(r), -Math.sin(r), Math.cos(r), 0, 0]),
    scale: (x, y) => mul([x, 0, 0, y, 0, 0]),
    beginPath: () => {
      pts = [];
    },
    moveTo: (x, y) => add(x, y),
    lineTo: (x, y) => add(x, y),
    quadraticCurveTo: (cx, cy, x, y) => {
      add(cx, cy);
      add(x, y);
    },
    bezierCurveTo: (a, b, c, d, x, y) => {
      add(a, b);
      add(c, d);
      add(x, y);
    },
    ellipse: (x, y, rx, ry) => {
      add(x - rx, y - ry);
      add(x + rx, y + ry);
    },
    arc: (x, y, r) => {
      add(x - r, y - r);
      add(x + r, y + r);
    },
    rect: (x, y, w, h) => {
      add(x, y);
      add(x + w, y + h);
    },
    fill: () => record(),
    fillRect: (x, y, w, h) => {
      pts = [];
      add(x, y);
      add(x + w, y + h);
      record();
      pts = [];
    },
  };
  const ctx = new Proxy(props, {
    get(target, prop: string) {
      if (prop in api) return api[prop];
      if (prop in target) return target[prop];
      return () => undefined;
    },
    set(target, prop: string, value) {
      target[prop] = value;
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  return { ctx, fills };
}

const PANTS = "#123456";
const SKIN = "#e0b090";
const BASE = resolveDollT({ team: "ally", summon: false, template: "hero_fighter", weaponId: "one_handed_sword" });
const SPEC: DollSpec = { ...BASE, look: { ...BASE.look, pants: PANTS, skin: SKIN }, gear: { ...BASE.gear, off_hand: undefined, body: { kind: "shirt", color: "#336699" } } };
const ARM = "#336699";

const draw = (f: Facing, pose: InkPose | null, spec: DollSpec = SPEC): Fill[] => {
  const { ctx, fills } = tracker();
  drawFigure(ctx, spec, f, true, pose);
  return fills;
};
const of = (fills: Fill[], color: string): Fill[] => fills.filter((x) => x.color === color);
const cx = (f: Fill): number => (f.box[0] + f.box[2]) / 2;
const cy = (f: Fill): number => (f.box[1] + f.box[3]) / 2;
const close = (a: Fill[], b: Fill[]): void => {
  expect(a.length).toBe(b.length);
  a.forEach((x, i) => x.box.forEach((v, j) => expect(v).toBeCloseTo(b[i]!.box[j]!, 6)));
};

afterEach(() => vi.restoreAllMocks());

describe("inkPose 工具", () => {
  it("pz：沒給、NaN、Infinity → 0", () => {
    expect(pz(null, "arm")).toBe(0);
    expect(pz({ arm: Number.NaN }, "arm")).toBe(0);
    expect(pz({ arm: Infinity }, "arm")).toBe(0);
    expect(pz({ arm: 0.5 }, "arm")).toBe(0.5);
  });
  it("cleanPose 只留認得的有限數字；mixPose、addPose、scalePose 的 wpn 兩邊都沒給時維持沒給", () => {
    expect(cleanPose({ arm: 1, nope: 2, hipN: "x", lean: Number.NaN })).toEqual({ arm: 1 });
    expect(mixPose({ arm: 0 }, { arm: 1, hipN: 2 }, 0.25)).toEqual({ arm: 0.25, hipN: 0.5 });
    expect("wpn" in mixPose({ arm: 0 }, { arm: 1 }, 0.5)).toBe(false);
    expect(addPose({ arm: 1, bob: -1 }, { arm: 0.5 }, { wpn: 0.2 })).toEqual({ arm: 1.5, bob: -1, wpn: 0.2 });
    expect(scalePose({ hipN: 0.5, bob: -2 }, 0.5)).toEqual({ hipN: 0.25, bob: -1 });
    expect(POSE_KEYS.length).toBe(new Set(POSE_KEYS).size);
  });
});

describe("6M-1 姿勢鉤子", () => {
  it("有姿勢時同一姿勢重畫完全相同，全程不呼叫 Math.random", () => {
    const rnd = vi.spyOn(Math, "random");
    const P: InkPose = { bob: -1, lean: 0.2, hipN: 0.4, hipF: -0.4, kneeN: 0.3, arm: -0.8, elbow: -0.6, armF: 0.5, elbowF: -0.4, liftL: 2, armR: 1, wpn: 0.3 };
    for (const f of ["south", "north", "east", "west"] as const) expect(draw(f, P)).toEqual(draw(f, P));
    expect(rnd).not.toHaveBeenCalled();
  });

  it("REST 姿勢的正面、背面：每個填色部件的位置都和沒姿勢相同", () => {
    for (const f of ["south", "north"] as const) {
      const key = (x: Fill): string => `${x.color}|${x.box.map((v) => v.toFixed(5)).join(",")}`;
      expect(draw(f, REST_POSE).map(key).sort()).toEqual(draw(f, null).map(key).sort());
    }
  });

  it("側面前傾：頭、身體跟著傾，腿與靴抵銷前傾、留在原地", () => {
    const a = draw("east", REST_POSE);
    const b = draw("east", { lean: 0.4 });
    close(of(b, PANTS), of(a, PANTS));
    close(of(b, darken(PANTS, 0.25)), of(a, darken(PANTS, 0.25)));
    const headA = of(a, SKIN)[0]!;
    const headB = of(b, SKIN)[0]!;
    expect(cx(headB) - cx(headA)).toBeGreaterThan(5); // 往面向方向（東、+x）傾
  });

  it("側面髖往前踢、膝往後彎；朝西鏡像", () => {
    const near = (fs: Fill[]): Fill => of(fs, PANTS)[0]!;
    const rest = near(draw("east", REST_POSE));
    expect(cx(near(draw("east", { hipN: 0.5 }))) - cx(rest)).toBeGreaterThan(1.5);
    expect(cx(near(draw("west", { hipN: 0.5 }))) - cx(near(draw("west", REST_POSE)))).toBeLessThan(-1.5);
    // 膝：小腿靴往後（-x）、大腿不動
    const boots = (fs: Fill[]): Fill[] => fs.filter((x) => x.box[3] > -1 && x.box[1] > -10 && x.color !== PANTS && x.color !== darken(PANTS, 0.25) && !x.color.startsWith("rgba"));
    const bA = boots(draw("east", REST_POSE));
    const bB = boots(draw("east", { kneeN: 0.7 }));
    expect(bA.length).toBeGreaterThan(0);
    expect(Math.min(...bB.map(cx))).toBeLessThan(Math.min(...bA.map(cx)) + 1e-9);
    close(of(draw("east", { kneeN: 0.7 }), PANTS), of(draw("east", REST_POSE), PANTS));
  });

  it("側面主手拆成上臂、前臂（手肘）；沒姿勢時仍是一塊", () => {
    const arms = (fs: Fill[]): Fill[] => of(fs, ARM).slice(1); // 第一塊同色的是身體
    expect(arms(draw("east", null)).length).toBe(1);
    const rest = arms(draw("east", REST_POSE));
    expect(rest.length).toBe(2);
    // 手肘彎：上臂不動、前臂動
    const bent = arms(draw("east", { elbow: -1.2 }));
    close([bent[0]!], [rest[0]!]);
    expect(cy(bent[1]!)).toBeLessThan(cy(rest[1]!) - 1); // 前臂往上收
    // 繞肩：舉手時上臂、前臂一起往上
    const up = arms(draw("east", { arm: -2 }));
    expect(cy(up[1]!)).toBeLessThan(cy(rest[1]!) - 5);
  });

  it("側面另一隻手：只在有姿勢時畫（較暗），繞肩可以伸出身體前方", () => {
    const FAR = darken(ARM, 0.25);
    expect(of(draw("east", null), FAR).length).toBe(0);
    const rest = of(draw("east", REST_POSE), FAR);
    expect(rest.length).toBe(2);
    const reach = of(draw("east", { armF: -0.8, elbowF: -0.3 }), FAR);
    expect(Math.max(...reach.map((x) => x.box[2]))).toBeGreaterThan(Math.max(...rest.map((x) => x.box[2])) + 1.5);
    // 成對武器的副手跟著另一隻手走
    const pair: DollSpec = { ...SPEC, gear: { ...SPEC.gear, main_hand: { kind: "dagger", material: "steel" }, off_hand: { kind: "dagger", material: "steel" } } };
    const handDot = darken(SKIN, 0.2);
    const h0 = of(draw("east", REST_POSE, pair), handDot);
    const h1 = of(draw("east", { armF: -1.4 }, pair), handDot);
    expect(h0.length).toBe(1);
    expect(Math.hypot(cx(h1[0]!) - cx(h0[0]!), cy(h1[0]!) - cy(h0[0]!))).toBeGreaterThan(3);
  });

  it("正面、背面抬腳：大腿抬 45%、靴抬 100%；擺手跟著 armL／armR 上下", () => {
    for (const f of ["south", "north"] as const) {
      const a = draw(f, REST_POSE);
      const b = draw(f, { liftL: 4 });
      const la = of(a, PANTS);
      const lb = of(b, PANTS);
      expect(la.length).toBe(2);
      expect(cy(lb[0]!) - cy(la[0]!)).toBeCloseTo(-1.8, 6); // sx = -1 那條腿
      expect(cy(lb[1]!) - cy(la[1]!)).toBeCloseTo(0, 6);
      const arms = (fs: Fill[]): Fill[] => of(fs, ARM).slice(1); // 第一塊同色的是身體
      const armsA = arms(a);
      const armsB = arms(draw(f, { armL: 1.5, armR: -1.5 }));
      expect(armsA.length).toBe(2);
      expect(armsB.map(cy).map((y, i) => Math.round((y - cy(armsA[i]!)) * 10) / 10).sort()).toEqual([-1.5, 1.5]);
    }
  });

  it("起伏 bob：整個人上下移", () => {
    const a = draw("south", REST_POSE);
    const b = draw("south", { bob: -2 });
    expect(cy(of(b, SKIN)[0]!) - cy(of(a, SKIN)[0]!)).toBeCloseTo(-2, 6);
    expect(cy(of(b, PANTS)[0]!) - cy(of(a, PANTS)[0]!)).toBeCloseTo(-2, 6);
  });

  it("wpn（6M-2）：主手武器相對手的角度；給預設握法的角度（劍側面 0.75）＝ 沒給", () => {
    const solo = (p: InkPose | null): string => JSON.stringify(draw("east", p).filter((x) => x.color !== ARM && x.color !== darken(ARM, 0.25)));
    expect(solo({ wpn: 0.75 })).toBe(solo(REST_POSE));
    expect(solo({ wpn: 0 })).not.toBe(solo(REST_POSE));
    expect(solo({ wpn: 0.8 })).not.toBe(solo(REST_POSE));
  });
});
