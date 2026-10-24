// Phase 3S-3：側面武器的幾何斷言（追蹤座標變換，量出武器實際畫到的範圍）。
import { describe, expect, it } from "vitest";
import { KNOWN_KINDS, type GearItem } from "./appearance";
import { drawWeaponSide } from "./paperdoll";
import { GUN_KINDS, sideWeaponPose } from "./paperdollSideWeapon";

type M = [number, number, number, number, number, number]; // a b c d e f

/** 追蹤 translate／rotate／scale 的 ctx，記下所有路徑點（經矩陣轉到畫布座標）。 */
function trackingCtx(): { ctx: CanvasRenderingContext2D; pts: Array<[number, number]> } {
  const pts: Array<[number, number]> = [];
  let m: M = [1, 0, 0, 1, 0, 0];
  const stack: M[] = [];
  const mul = (a: M, b: M): M => [
    a[0] * b[0] + a[2] * b[1],
    a[1] * b[0] + a[3] * b[1],
    a[0] * b[2] + a[2] * b[3],
    a[1] * b[2] + a[3] * b[3],
    a[0] * b[4] + a[2] * b[5] + a[4],
    a[1] * b[4] + a[3] * b[5] + a[5],
  ];
  const pt = (x: number, y: number): void => {
    pts.push([m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]]);
  };
  const num = (v: unknown): number => (typeof v === "number" ? v : 0);
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(t, prop: string) {
      if (prop in t) return t[prop];
      switch (prop) {
        case "save":
          return () => stack.push([...m] as M);
        case "restore":
          return () => {
            m = stack.pop() ?? m;
          };
        case "translate":
          return (x: number, y: number) => {
            m = mul(m, [1, 0, 0, 1, x, y]);
          };
        case "scale":
          return (x: number, y: number) => {
            m = mul(m, [x, 0, 0, y, 0, 0]);
          };
        case "rotate":
          return (a: number) => {
            m = mul(m, [Math.cos(a), Math.sin(a), -Math.sin(a), Math.cos(a), 0, 0]);
          };
        case "moveTo":
        case "lineTo":
          return (x: number, y: number) => pt(x, y);
        case "quadraticCurveTo":
          return (_cx: number, _cy: number, x: number, y: number) => pt(x, y);
        case "bezierCurveTo":
          return (_a: number, _b: number, _c: number, _d: number, x: number, y: number) => pt(x, y);
        case "rect":
        case "fillRect":
        case "roundRect":
          return (x: number, y: number, w: number, h: number) => {
            for (const [px, py] of [[x, y], [x + w, y], [x, y + h], [x + w, y + h]] as const) pt(px, py);
          };
        case "arc":
        case "ellipse":
          return (x: number, y: number, r: number, r2?: unknown) => {
            const rx = prop === "ellipse" ? r : r;
            const ry = prop === "ellipse" ? num(r2) : r;
            for (const [px, py] of [[x - rx, y], [x + rx, y], [x, y - ry], [x, y + ry]] as const) pt(px, py);
          };
        default:
          return () => undefined;
      }
    },
    set(t, prop: string, value) {
      t[prop] = value;
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  return { ctx, pts };
}

const HAND = 4.6; // 近側手的 x
const NOSE_X = 10.2; // 鼻尖
const GUNS = [...GUN_KINDS];
const FORMS: Record<string, Array<string | undefined>> = {
  sword: [undefined, "arcane"],
  hammer: ["mace", "flail", "warhammer"],
  spear: [undefined, "halberd", "trident"],
  staff: [undefined, "totem", "scepter"],
  longgun: ["flintlock", "hunting", "sniper"],
  pistol: ["flintlock", "revolver", "derringer"],
  shotgun: ["blunderbuss", "double", "pump"],
  crossbow: ["light", "heavy", "repeater"],
};

function measure(it: GearItem, far = false): { minX: number; maxX: number; topX: number; minY: number } {
  const { ctx, pts } = trackingCtx();
  drawWeaponSide(ctx, it, HAND, far);
  const xs = pts.map((p) => p[0]);
  const top = pts.reduce((a, b) => (b[1] < a[1] ? b : a));
  return { minX: Math.min(...xs), maxX: Math.max(...xs), topX: top[0], minY: top[1] };
}

describe("側面武器角度（3S-3）", () => {
  it("槍（火槍、手槍、霰彈槍、弩）一律槍口朝面向方向：重心在手的前方，最遠點在前", () => {
    for (const kind of GUNS) {
      for (const form of FORMS[kind] ?? [undefined]) {
        for (const far of [false, true]) {
          const r = measure({ kind, form, material: "steel" }, far);
          expect(r.maxX - HAND).toBeGreaterThan(HAND - r.minX);
          expect(r.maxX).toBeGreaterThan(HAND + 4);
        }
      }
    }
  });

  it("長柄與劍：頂端在臉的前面（頂端 x 超過鼻尖），不蓋住臉", () => {
    for (const kind of ["sword", "greatsword", "dagger", "axe", "hammer", "spear", "scythe", "staff"]) {
      for (const form of FORMS[kind] ?? [undefined]) {
        const r = measure({ kind, form, material: "steel" });
        expect(r.topX, `${kind}/${String(form)}`).toBeGreaterThan(NOSE_X);
      }
    }
  });

  it("身體範圍內（臉的高度、x 在後腦到鼻尖之間）不會有長柄武器的頂端", () => {
    for (const kind of ["staff", "spear", "hammer", "scythe", "greatsword", "sword", "axe", "dagger"]) {
      const { ctx, pts } = trackingCtx();
      drawWeaponSide(ctx, { kind, material: "steel" }, HAND, false);
      // 只看頭部高度（-37 ~ -21）：武器在這個高度的部分都要在鼻尖前面
      const inFace = pts.filter(([x, y]) => y < -21 && y > -37 && x < NOSE_X - 1 && x > -8);
      expect(inFace.length, kind).toBe(0);
    }
  });

  it("鞭、弓往前；拳套刃往前", () => {
    expect(measure({ kind: "whip", material: "leather" }).maxX).toBeGreaterThan(HAND + 8);
    expect(measure({ kind: "bow", material: "wood" }).maxX).toBeGreaterThan(HAND + 6);
    expect(measure({ kind: "fist", form: "katar", material: "steel" }).maxX).toBeGreaterThan(HAND + 6);
  });

  it("每個已知主手 kind 都有側面姿勢；不認得的 kind 用保守退回；遠側比近側暗", () => {
    for (const kind of [...KNOWN_KINDS.main_hand, "weird_kind"]) {
      const near = sideWeaponPose({ kind, material: "steel" }, false);
      const far = sideWeaponPose({ kind, material: "steel" }, true);
      expect(Number.isFinite(near.angle)).toBe(true);
      expect(near.shade).toBe(0);
      expect(far.shade).toBeGreaterThan(0);
    }
    expect(() => measure({ kind: "orb", form: "ball", material: "steel" })).not.toThrow();
  });
});
