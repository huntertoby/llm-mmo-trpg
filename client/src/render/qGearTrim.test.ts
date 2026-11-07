// QK-8 小修 1、2（QK-5 做）：長袍邊色讀長袍自己的 trim；念珠照樣張深褐色。
import { describe, expect, it } from "vitest";
import type { QUnit, QView } from "./qCore";
import { drawQ } from "./qDoll";
import { BEAD_COLOR } from "./qGear";
import { SAMPLE_HOOKS } from "./qSample";
import { qUnitOf } from "./qSpec";
import { resolveDollT } from "./testDolls";

function fills(u: QUnit, view: QView): string[] {
  const out: string[] = [];
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(t, p: string) {
      if (p in t) return t[p];
      if (p === "getTransform") return () => ({ a: 1, b: 0, c: 0, d: 1, e: 0, f: 0 });
      return () => undefined;
    },
    set(t, p: string, v) {
      t[p] = v;
      if (p === "fillStyle" || p === "strokeStyle") out.push(String(v).toLowerCase());
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  drawQ(ctx, u, view, SAMPLE_HOOKS, null);
  return out;
}

describe("QK-8 小修 1、2", () => {
  it("長袍的 trim（霧鎖真人金邊、小蓮竹青邊）畫在前襟與下擺；外觀 look.trim 優先；都沒有不畫成 trim 色", () => {
    const robe = (trim?: string, look?: string): QUnit => ({ look: { skin: "#f1c9a5", hair: "long", ...(look ? { trim: look } : {}) }, gear: { body: { kind: "robe", color: "#e8ecea", ...(trim ? { trim } : {}) } } });
    for (const v of ["front", "side", "back"] as const) expect(fills(robe("#6aa84a"), v), v).toContain("#6aa84a");
    expect(fills(robe("#e8bb48"), "front")).toContain("#e8bb48");
    expect(fills(robe("#6aa84a", "#123456"), "front")).toContain("#123456");
    expect(fills(robe("#6aa84a", "#123456"), "front")).not.toContain("#6aa84a");
    expect(fills(robe(), "front")).not.toContain("#6aa84a");
  });

  it("霧鎖真人（content 的長袍 trim 金色）傳到 Q 版畫成金邊", () => {
    const u = qUnitOf(resolveDollT({ template: "sect_mist_lock_master", team: "enemy", summon: false, weaponId: "one_handed_sword" }));
    expect(u.gear.body?.trim).toBe("#e8bb48");
    expect(fills(u, "front")).toContain("#e8bb48");
  });

  it("念珠沒指定顏色：深褐 #6a3a22（樣張 qNpc.js 護法武僧），四方向", () => {
    const u = qUnitOf(resolveDollT({ template: "sect_warrior_monk", team: "enemy", summon: false, weaponId: "fist" }));
    expect(u.gear.neck?.kind).toBe("beads");
    for (const v of ["front", "side", "back"] as const) expect(fills(u, v), v).toContain(BEAD_COLOR);
    const colored: QUnit = { look: { skin: "#c08050" }, gear: { neck: { kind: "beads", color: "#aa0000" } } };
    expect(fills(colored, "front")).toContain("#aa0000");
  });
});
