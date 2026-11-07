// QK-5 追加（美術 PM 對 QK-8 的決定）：規則武器 fist ＝空手，畫成空手拳頭（赤膊武僧不戴拳套）；拳套只給 gauntlet。
import { describe, expect, it } from "vitest";
import type { QPose, QUnit, QView } from "./qCore";
import { drawQ } from "./qDoll";
import { SAMPLE_HOOKS } from "./qSample";
import { qUnitOf } from "./qSpec";
import { resolveDollT } from "./testDolls";

/** 畫一隻，回傳武器回報（probe）收到的武器種類與指令數。 */
function drawKinds(u: QUnit, view: QView, west = false): { kinds: string[]; calls: string[] } {
  const kinds: string[] = [];
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(t, p: string) {
      if (p in t) return t[p];
      if (p === "getTransform") return () => ({ a: 1, b: 0, c: 0, d: 1, e: 0, f: 0 });
      return (...a: unknown[]) => {
        calls.push(`${p}(${a.map((x) => (typeof x === "number" ? x.toFixed(3) : String(x))).join(",")})`);
        return undefined;
      };
    },
    set(t, p: string, v) {
      t[p] = v;
      calls.push(`${p}=${String(v)}`);
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  const pose: QPose = { probe: (k) => void kinds.push(k) };
  drawQ(ctx, u, view, SAMPLE_HOOKS, pose, west);
  return { kinds, calls };
}

const VIEWS: readonly [QView, boolean][] = [["front", false], ["back", false], ["side", false], ["side", true]];

describe("QK-5：fist 畫成空手、gauntlet 照畫拳套", () => {
  it("護法武僧（weapon: fist）四方向：Q 版小人沒有主手武器、不畫拳套", () => {
    const spec = resolveDollT({ template: "sect_warrior_monk", team: "enemy", summon: false, weaponId: "fist" });
    expect(spec.gear.main_hand?.kind).toBe("fist"); // 規則資料照舊
    const u = qUnitOf(spec);
    expect(u.gear.main_hand).toBeUndefined();
    expect(u.gear.off_hand).toBeUndefined();
    for (const [v, w] of VIEWS) expect(drawKinds(u, v, w).kinds, `${v} ${w}`).not.toContain("gauntlet");
  });

  it("fist 和空手畫出來相同；gauntlet 照畫拳套（和空手不同）", () => {
    const base: QUnit = { look: { skin: "#f1c9a5", hair: "short" }, gear: { body: { kind: "shirt", color: "#2f5a5a" } } };
    const fist = qUnitOf({ look: base.look, gear: { ...base.gear, main_hand: { kind: "fist", form: "knuckle", material: "iron" } } } as never);
    const gaunt: QUnit = { look: base.look, gear: { ...base.gear, main_hand: { kind: "gauntlet", material: "steel" } } };
    for (const [v, w] of VIEWS) {
      const bare = drawKinds(base, v, w).calls.join("\n");
      expect(drawKinds(fist, v, w).calls.join("\n"), `${v} ${w}`).toBe(bare);
      const g = drawKinds(gaunt, v, w);
      expect(g.kinds, `${v} ${w}`).toContain("gauntlet");
      expect(g.calls.join("\n")).not.toBe(bare);
    }
  });
});
