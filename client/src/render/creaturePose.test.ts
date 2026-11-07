// Phase 6M-2 → QK-4：異形的片段。6M-2 的 4 個通用整隻片段（走、撲、受擊、倒下）在 QK-4 換成 Q 版分部件片段的引用
// （`clip`＋量化的 `u`，部件動作在 qCreatureAnim.ts，依身形）；這裡驗：
// 1. 沒給姿勢時，drawCreature 的指令流（快照，QK-4 重產）；
// 2. 片段是時間的純函式：同一個時間點兩次結果相同；受擊、攻擊播完回到原樣；倒下停在最後一格；走路循環頭尾相接；
// 3. 影子不跟著姿勢動；身體跟著伸縮、傾斜、位移（跳躍的整隻欄位仍可疊上去）。
import { describe, expect, it } from "vitest";
import { AFFIX, BODY_IDS, BODY_VARIANTS, MATERIALS, TRAITS, drawCreature, resolveCreature, type CreatureLookDraw } from "./inkCreature";
import { CREATURE_CLIP_IDS, CREATURE_CLIPS, applyCreaturePose, cp, creaturePoseAt, creaturePoseKey, creatureStrikePose, quantizeCreaturePose, type CreaturePose } from "./creaturePose";

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

describe("6M-2／QK-4：異形片段", () => {
  it("沒給姿勢時，drawCreature 的指令流不變（快照）", () => {
    const out: Record<string, string> = {};
    for (const [k, look, affixes] of looks()) out[k] = streamHash((ctx) => drawCreature(ctx, resolveCreature({ look, affixes })));
    expect(out).toMatchSnapshot();
  });

  it("片段是時間的純函式：引用 Q 版片段（clip）與量化過的格（u ∈ [0, 1]）", () => {
    const want: Record<string, string> = { walk: "move", pounce: "atk:@melee", hit: "hit", fall: "death" };
    for (const id of CREATURE_CLIP_IDS) {
      const us = new Set<number>();
      for (let ms = -100; ms <= CREATURE_CLIPS[id].dur + 200; ms += 17) {
        const a = creaturePoseAt(id, ms);
        expect(creaturePoseAt(id, ms)).toEqual(a);
        expect(a.clip).toBe(want[id]);
        expect(Number.isFinite(a.u)).toBe(true);
        expect(a.u!).toBeGreaterThanOrEqual(0);
        expect(a.u!).toBeLessThanOrEqual(1);
        us.add(a.u!);
      }
      expect(us.size).toBeGreaterThan(3); // 有格數（不是整段同一格）
      expect(us.size).toBeLessThanOrEqual(12); // 量化（貼圖快取有上限）
    }
  });

  it("受擊從第一格播到回原樣；倒下停在最後一格；走路循環頭尾相接", () => {
    expect(creaturePoseAt("hit", 0).u).toBe(0);
    expect(creaturePoseAt("hit", CREATURE_CLIPS.hit.dur).u).toBe(1);
    expect(creaturePoseAt("fall", 0).u).toBe(0);
    expect(creaturePoseAt("fall", 10_000)).toEqual(creaturePoseAt("fall", CREATURE_CLIPS.fall.dur));
    expect(creaturePoseAt("fall", 10_000).u).toBe(1);
    expect(creaturePoseAt("walk", 900)).toEqual(creaturePoseAt("walk", 0));
    expect(creaturePoseAt("walk", 1234)).toEqual(creaturePoseAt("walk", 334));
  });

  it("攻擊依動作類型（creatureStrikePose）；量化與快取鍵帶著片段與格", () => {
    const p = creatureStrikePose("breath", 0.5);
    expect(p.clip).toBe("atk:@breath");
    expect(quantizeCreaturePose(p)).toEqual(p);
    expect(creaturePoseKey(p)).toContain("atk:@breath@");
    expect(creaturePoseKey(creatureStrikePose("breath", 0.52))).toBe(creaturePoseKey(p)); // 同一格共用貼圖
    expect(creaturePoseKey(creatureStrikePose("breath", 0.7))).not.toBe(creaturePoseKey(p));
    expect(creaturePoseKey({})).toBe("");
    expect(cp(p, "flash")).toBe(0);
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
    // 影子（第一個 fill）之前的指令一樣，之後多了位移、傾斜、伸縮
    const firstEllipse = (xs: string[]): number => xs.findIndex((s) => s.startsWith("fill("));
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
