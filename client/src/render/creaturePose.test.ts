// Phase 6M-2：異形 4 個通用片段（走、撲、受擊、倒下）。
// 1. 沒給姿勢時，drawCreature 的畫布指令流和加片段之前相同（快照在改 drawCreature 之前產生）。
// 2. 片段是時間的純函式：同一個時間點兩次結果相同；撲、受擊播完回到原樣；倒下停在塌扁、變淡；走路循環頭尾相接。
// 3. 影子不跟著姿勢動；身體跟著伸縮、傾斜、位移。
import { describe, expect, it } from "vitest";
import { AFFIX, BODY_IDS, BODY_VARIANTS, MATERIALS, TRAITS, drawCreature, resolveCreature, type CreatureLookDraw } from "./inkCreature";
import { CREATURE_CLIP_IDS, CREATURE_CLIPS, applyCreaturePose, cp, creaturePoseAt, type CreaturePose } from "./creaturePose";

// 數字固定 6 位小數再雜湊，讓 arm64／x64 的快照一致（MAC-1）：浮點數最後幾位在不同平台會不同。
function fmt(a: unknown): string {
  if (typeof a === "number") {
    if (Number.isInteger(a)) return Object.is(a, -0) ? "-0" : String(a);
    const fixed = a.toFixed(6);
    return fixed === "-0.000000" ? "0.000000" : fixed;
  }
  if (typeof a === "string") return JSON.stringify(a);
  if (Array.isArray(a)) return `[${a.map(fmt).join(",")}]`;
  return typeof a;
}

/** 畫布指令紀錄（含屬性設定；數字取 6 位小數）→ FNV-1a 雜湊與指令數（同 inkDollSnapshot.test.ts）。 */
function streamHash(draw: (ctx: CanvasRenderingContext2D) => void): string {
  let h = 2166136261;
  let n = 0;
  const push = (s: string): void => {
    n++;
    for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
    h = Math.imul(h ^ 10, 16777619);
  };
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        push(`${prop}(${args.map(fmt).join(",")})`);
        return undefined;
      };
    },
    set(target, prop: string, value) {
      target[prop] = value;
      push(`${prop}=${fmt(value)}`);
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  draw(ctx);
  return `${(h >>> 0).toString(16).padStart(8, "0")}:${n}`;
}

const looks = (): Array<[string, CreatureLookDraw, string[]]> => {
  const out: Array<[string, CreatureLookDraw, string[]]> = [];
  for (const body of BODY_IDS) for (const variant of BODY_VARIANTS[body] ?? [undefined]) for (const material of MATERIALS) out.push([`${body}/${variant ?? ""}/${material}`, { body, variant, material }, []]);
  out.push(["traits", { body: "hound", traits: Object.keys(TRAITS).sort(), element: "fire" }, []]);
  out.push(["affixes", { body: "golem", material: "stone" }, Object.keys(AFFIX).sort().concat(["mirror"])]);
  return out;
};

describe("6M-2：異形通用片段", () => {
  it("沒給姿勢時，drawCreature 的指令流不變（快照）", () => {
    const out: Record<string, string> = {};
    for (const [k, look, affixes] of looks()) out[k] = streamHash((ctx) => drawCreature(ctx, resolveCreature({ look, affixes })));
    expect(out).toMatchSnapshot();
  });

  it("片段是時間的純函式，數值都是有限數字", () => {
    for (const id of CREATURE_CLIP_IDS) {
      for (let ms = -100; ms <= CREATURE_CLIPS[id].dur + 200; ms += 17) {
        for (const hover of [false, true]) {
          const a = creaturePoseAt(id, ms, { hover });
          expect(creaturePoseAt(id, ms, { hover })).toEqual(a);
          for (const v of Object.values(a)) expect(Number.isFinite(v)).toBe(true);
          expect(cp(a, "alpha")).toBeGreaterThan(0.5);
          expect(cp(a, "sy")).toBeGreaterThan(0.4);
        }
      }
    }
  });

  it("撲、受擊播完回到原樣；倒下停在塌扁、往後倒、變淡；走路循環頭尾相接", () => {
    const rest = (p: CreaturePose): void => {
      expect(cp(p, "dx")).toBeCloseTo(0, 6);
      expect(cp(p, "dy")).toBeCloseTo(0, 6);
      expect(cp(p, "sx")).toBeCloseTo(1, 6);
      expect(cp(p, "sy")).toBeCloseTo(1, 6);
      expect(cp(p, "rot")).toBeCloseTo(0, 6);
    };
    for (const id of ["pounce", "hit"] as const) {
      rest(creaturePoseAt(id, 0));
      rest(creaturePoseAt(id, CREATURE_CLIPS[id].dur));
    }
    rest(creaturePoseAt("fall", 0));
    const end = creaturePoseAt("fall", 10_000);
    expect(cp(end, "sy")).toBeLessThan(0.5);
    expect(cp(end, "rot")).toBeLessThan(-0.3);
    expect(cp(end, "alpha")).toBeLessThan(0.6);
    expect(creaturePoseAt("walk", 900)).toEqual(creaturePoseAt("walk", 0));
    expect(creaturePoseAt("walk", 1234)).toEqual(creaturePoseAt("walk", 334));
  });

  it("撲：先往後縮、壓低，再往前上撲出（往前超過 10、離地）；受擊：往後彈、開頭白閃", () => {
    const xs = Array.from({ length: 53 }, (_, i) => creaturePoseAt("pounce", i * 10));
    expect(Math.min(...xs.slice(0, 18).map((p) => cp(p, "dx")))).toBeLessThan(-2);
    expect(cp(creaturePoseAt("pounce", 170), "sy")).toBeLessThan(0.9);
    expect(Math.max(...xs.map((p) => cp(p, "dx")))).toBeGreaterThan(10);
    expect(Math.min(...xs.map((p) => cp(p, "dy")))).toBeLessThan(-7);
    const hs = Array.from({ length: 37 }, (_, i) => creaturePoseAt("hit", i * 10));
    expect(Math.min(...hs.map((p) => cp(p, "dx")))).toBeLessThan(-5);
    expect(cp(hs[0]!, "flash")).toBeGreaterThan(0.8);
    expect(cp(hs[36]!, "flash")).toBe(0);
  });

  it("走路：不浮空的身形踩步（只往上、不陷進地）；浮空的上下飄", () => {
    for (let ms = 0; ms < 900; ms += 15) {
      expect(cp(creaturePoseAt("walk", ms), "dy")).toBeLessThanOrEqual(0);
      expect(cp(creaturePoseAt("walk", ms, { hover: true }), "dy")).toBeLessThan(0);
    }
  });

  it("有姿勢時影子不動、身體動；預設值不加指令", () => {
    const calls = (pose: CreaturePose | null): string[] => {
      const out: string[] = [];
      const ctx = new Proxy({} as Record<string, unknown>, {
        get: (t, p: string) => (p in t ? t[p] : (...a: unknown[]) => void out.push(`${p}(${a.map(fmt).join(",")})`)),
        set: (t, p: string, v) => ((t[p] = v), out.push(`${p}=${fmt(v)}`), true),
      }) as unknown as CanvasRenderingContext2D;
      drawCreature(ctx, resolveCreature({ look: { body: "hound" } }), pose);
      return out;
    };
    const a = calls(null);
    const b = calls({ dx: 3, sy: 0.8, rot: 0.1 });
    // 影子（第一個 stroke）之前的指令一樣，之後多了位移、傾斜、伸縮
    const firstEllipse = (xs: string[]): number => xs.findIndex((s) => s.startsWith("stroke("));
    expect(b.slice(0, firstEllipse(b) + 1)).toEqual(a.slice(0, firstEllipse(a) + 1));
    expect(b).toContain("translate(3,0)");
    expect(b).toContain("rotate(0.100000)"); // fmt 把非整數取 6 位小數（MAC-1）
    expect(b).toContain("scale(1,0.800000)");
    const none: string[] = [];
    const ctx = new Proxy({} as Record<string, unknown>, { get: () => (...a: unknown[]) => void none.push(String(a)), set: () => true }) as unknown as CanvasRenderingContext2D;
    applyCreaturePose(ctx, {});
    expect(none).toEqual([]);
  });
});
