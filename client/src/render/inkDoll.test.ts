// Phase C-1a：C 畫風骨架與四方向 — 確定性、圖層順序、背面對調、體型、倒地、不認得的值、快取鍵、無剪影外框。
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Facing } from "../api/types";
import type { DollSpec } from "./appearance";
import { buildScale } from "./inkDoll";
import { DOLL_FOOT_Y, DOLL_H, DOLL_SCALE, DOLL_W, drawFigure, drawFigurePose, renderFigureCanvas, SUMMON_H, SUMMON_W } from "./paperdoll";
import { resolveDollT } from "./testDolls";

function recorder(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map((a) => (typeof a === "number" ? a.toFixed(3) : typeof a)).join(",")})`);
        return undefined;
      };
    },
    set(target, prop: string, value) {
      target[prop] = value;
      calls.push(`${prop}=${String(value)}`);
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  return { ctx, calls };
}

const FACINGS: Facing[] = ["south", "north", "east", "west"];
const hero = (extra: Partial<DollSpec["look"]> = {}): DollSpec => {
  const s = resolveDollT({ team: "ally", summon: false, template: "hero_fighter", weaponId: "one_handed_sword" });
  return { ...s, look: { ...s.look, ...extra } };
};
const run = (spec: DollSpec, f: Facing): string[] => {
  const { ctx, calls } = recorder();
  drawFigure(ctx, spec, f);
  return calls;
};
const fills = (calls: string[]): string[] => calls.filter((c) => c.startsWith("fillStyle=#")).map((c) => c.slice(10));

afterEach(() => vi.restoreAllMocks());

describe("C 畫風骨架（C-1a）", () => {
  it("四方向 × 各體型 × 有／沒有髮型，重畫完全相同（同一隻小人不閃）；全程不呼叫 Math.random", () => {
    const rnd = vi.spyOn(Math, "random");
    for (const f of FACINGS) {
      for (const look of [{}, { build: "stout" as const }, { build: "tall" as const }, { hair: "long" as const }, { hair: "none" as const }]) {
        expect(run(hero(look), f)).toEqual(run(hero(look), f));
      }
    }
    expect(rnd).not.toHaveBeenCalled();
  });

  it("不同方向畫出不同的東西（不同 key）", () => {
    const sets = FACINGS.map((f) => run(hero(), f).join("|"));
    expect(new Set(sets).size).toBeGreaterThanOrEqual(3); // 西是東的鏡像，指令多一個 scale(-1)；南、北、東皆不同
    expect(run(hero(), "west")).not.toEqual(run(hero(), "east"));
  });

  it("西 ＝ 東的左右鏡像（整張 scale(-1,1)），東不鏡像", () => {
    const east = run(hero(), "east");
    const west = run(hero(), "west");
    expect(west.indexOf("scale(-1.000,1.000)")).toBeGreaterThanOrEqual(0);
    expect(west.indexOf("scale(-1.000,1.000)")).toBeLessThan(5);
    expect(west.filter((c) => c !== "scale(-1.000,1.000)")).toEqual(east.filter((c) => c !== "scale(-1.000,1.000)"));
    expect(east.slice(0, 5)).not.toContain("scale(-1.000,1.000)");
  });

  it("背面：先左右對調（scale(-1,1)），影子之後才是武器、腿、身體；背面沒有眼睛與臉紅", () => {
    const back = run(hero(), "north");
    const front = run(hero(), "south");
    expect(back.indexOf("scale(-1.000,1.000)")).toBeGreaterThan(0);
    expect(front).not.toContain("scale(-1.000,1.000)");
    // 正面畫臉（眼睛 ellipse 半徑 0.9×1.3、臉紅 rgba(220,90,80,0.32)），背面不畫
    expect(front).toContain("fillStyle=rgba(220,90,80,0.32)");
    expect(back).not.toContain("fillStyle=rgba(220,90,80,0.32)");
  });

  it("背面戴帽時後腦頭髮仍在（帽子只蓋頭頂）：頭髮色在背面照畫，正面被帽子蓋住就不畫", () => {
    const hairColor = "#123456";
    const capped: DollSpec = { ...hero({ hair: "short", hairColor }), gear: { ...hero().gear, head: { kind: "helmet", material: "steel" } } };
    expect(fills(run(capped, "north"))).toContain(hairColor);
    expect(fills(run(capped, "south"))).not.toContain(hairColor);
    expect(fills(run({ ...capped, gear: { ...capped.gear, head: undefined } }, "south"))).toContain(hairColor);
  });

  it("體型：stout ×(1.12,0.88)、tall ×(0.96,1.1)，四方向都套用；不認得的值＝普通", () => {
    expect(buildScale({ skin: "#fff", build: "stout" })).toEqual([1.12, 0.88]);
    expect(buildScale({ skin: "#fff", build: "tall" })).toEqual([0.96, 1.1]);
    expect(buildScale({ skin: "#fff" })).toEqual([1, 1]);
    expect(buildScale({ skin: "#fff", build: "weird" as never })).toEqual([1, 1]);
    for (const f of FACINGS) {
      expect(run(hero({ build: "stout" }), f)).toContain("scale(1.120,0.880)");
      expect(run(hero({ build: "tall" }), f)).toContain("scale(0.960,1.100)");
      expect(run(hero(), f)).not.toContain("scale(1.120,0.880)");
    }
  });

  it("地面影子：有影子（短斜線）；倒地姿勢不畫影子，且身體整個旋轉 90 度", () => {
    const up = recorder();
    drawFigurePose(up.ctx, hero(), "south", false);
    const down = recorder();
    drawFigurePose(down.ctx, hero(), "south", true);
    const lines = (c: string[]): number => c.filter((x) => x.startsWith("moveTo")).length;
    expect(down.calls).toContain(`rotate(${(Math.PI / 2).toFixed(3)})`);
    expect(up.calls).not.toContain(`rotate(${(Math.PI / 2).toFixed(3)})`);
    expect(lines(up.calls)).toBeGreaterThan(lines(down.calls)); // 少了影子那一排 moveTo
  });

  it("沒有黑色剪影外框：renderFigureCanvas 在沒有 DOM 的環境回傳 null，且貼圖不再用 source-in 偏移 8 方向描邊", () => {
    expect(renderFigureCanvas(hero(), "south", false, 1)).toBeNull();
    for (const f of FACINGS) expect(run(hero(), f)).not.toContain("fillStyle=#16121a");
  });

  it("不認得的值（kind、材質、顏色、形制、元素）一律退回預設，不出錯", () => {
    const weird: DollSpec = {
      look: { skin: "#ffffff", hair: "weird" as never, build: "huge" as never, pants: "not-a-color" },
      gear: {
        head: { kind: "???", material: "nope", color: "red" },
        body: { kind: "???", material: "unobtainium", color: "pink", form: "x", element: "nope" },
        feet: { kind: "???" },
        cloak: { kind: "???" },
        main_hand: { kind: "???", form: "x" },
        off_hand: { kind: "???" },
        hands: { kind: "???" },
      },
    };
    for (const f of FACINGS) for (const downed of [false, true]) expect(() => drawFigurePose(recorder().ctx, weird, f, downed)).not.toThrow();
  });

  it("圖騰仍畫圖騰柱；骷髏（skull ＋ ribs）四方向可畫", () => {
    for (const f of FACINGS) {
      expect(() => drawFigure(recorder().ctx, resolveDollT({ team: "ally", summon: true, template: "summon_war_totem", totem: true }), f)).not.toThrow();
      expect(() => drawFigure(recorder().ctx, resolveDollT({ team: "ally", summon: true, template: "summon_skeleton_warrior", weaponId: "one_handed_sword" }), f)).not.toThrow();
    }
  });
});

describe("畫布與縮放（C-1a）", () => {
  it("畫布高度留夠尖帽（-70）：腳底以上 ≥ 76；寬度容得下尾巴、披風、斜持武器", () => {
    expect(DOLL_FOOT_Y).toBeGreaterThanOrEqual(76);
    expect(DOLL_H).toBeGreaterThan(DOLL_FOOT_Y);
    expect(DOLL_W).toBe(64);
  });

  it("52px 格縮放約 0.74，人（頭頂約 -52）約 40px 高", () => {
    expect(DOLL_SCALE).toBe(0.74);
    expect(52 * DOLL_SCALE).toBeGreaterThan(36);
    expect(52 * DOLL_SCALE).toBeLessThan(42);
  });

  it("非人形召喚物沿用舊的 64×64 畫布（不隨 C 骨架改）", () => {
    expect([SUMMON_W, SUMMON_H]).toEqual([64, 64]);
  });
});
