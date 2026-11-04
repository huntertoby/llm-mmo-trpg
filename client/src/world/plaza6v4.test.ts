// Phase 6V-4：主城廣場的只畫裝飾（花壇、攤布、晾衣繩、堆箱、放射狀鋪法）。版面照主城地圖的空格放：
// 不疊在物件、人、設施、門、建築、水上；格子與規則不變（只是 FieldScenery 的外觀資料）；畫法確定。
// 6V-4b：版面從前端的 `CAPITAL_DECOR` 搬到地圖檔 `look.decor`（API `FieldView.decor`）。
import { describe, expect, it } from "vitest";
import type { FieldView } from "../api/types";
import { DECOR_DRAW, drawPavingRow, PAVING_RINGS, pavingJoints } from "../render/plazaDecor";
import { capitalDoc as doc, capitalField } from "../test/capitalField";
import { fieldScenery, plazaDecorOf } from "./fieldScenery";

function calls(fn: (ctx: CanvasRenderingContext2D) => void): string[] {
  const out: string[] = [];
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(t, p: string) {
      if (p in t) return t[p];
      return (...a: unknown[]) => {
        out.push(`${p}(${a.map((v) => (typeof v === "number" ? v.toFixed(3) : typeof v)).join(",")})`);
        if (p === "createLinearGradient" || p === "createRadialGradient") return { addColorStop: () => undefined };
        return undefined;
      };
    },
    set(t, p: string, v) {
      t[p] = v;
      out.push(`${p}=${String(v)}`);
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  fn(ctx);
  return out;
}

const ITEMS = 14;

describe("主城廣場裝飾（6V-4）", () => {
  const field = capitalField();

  it("版面上 14 件都放得下（格子空著），種類齊全：花壇、攤布、晾衣繩、堆箱", () => {
    const decor = plazaDecorOf(field);
    expect(decor).toHaveLength(ITEMS);
    expect(new Set(decor.map((d) => d.kind))).toEqual(new Set(["flower_bed", "stall_cloth", "clothesline", "crate_stack"]));
  });

  it("不疊在物件、設施、情境物件、門、傳送石、建築、水上；只放在石地、草地、泥地", () => {
    const taken = new Set([
      ...doc.objects.map((o) => `${o.at[0]},${o.at[1]}`),
      ...doc.facilities.map((o) => `${o.at[0]},${o.at[1]}`),
      ...doc.situation_objects.map((o) => `${o.at[0]},${o.at[1]}`),
      ...doc.doors.map((o) => `${o.at[0]},${o.at[1]}`),
      ...doc.teleport_stones.map((o) => `${o.at[0]},${o.at[1]}`),
      ...doc.surfaces.map((o) => `${o.at[0]},${o.at[1]}`),
    ]);
    for (const b of doc.buildings) for (let y = b.at[1]; y < b.at[1] + b.size[1]; y++) for (let x = b.at[0]; x < b.at[0] + b.size[0]; x++) taken.add(`${x},${y}`);
    const terrain = new Map(field.tiles.map((t) => [`${t.x},${t.y}`, t.terrain]));
    for (const d of plazaDecorOf(field)) {
      for (let i = 0; i < d.w; i++) {
        const k = `${d.x + i},${d.y}`;
        expect(taken.has(k), `${d.kind}@${k}`).toBe(false);
        expect(["stone", "grass", "dirt"]).toContain(terrain.get(k));
      }
    }
    // 從傳送石到三扇門的直線上沒有裝飾（主要的路留空）
    const cells = new Set(plazaDecorOf(field).flatMap((d) => Array.from({ length: d.w }, (_, i) => `${d.x + i},${d.y}`)));
    for (let y = 5; y <= 11; y++) expect(cells.has(`15,${y}`)).toBe(false);
    for (let x = 6; x <= 24; x++) expect(cells.has(`${x},11`)).toBe(false);
  });

  it("格子被佔了（例：有人站上去、內容多了物件）那一件就不畫；沒有 decor 的地圖沒有裝飾", () => {
    const first = plazaDecorOf(field)[0]!;
    const busy = { ...field, objects: [...field.objects, { id: "x", kind: "crate", x: first.x, y: first.y, look: null }] } as FieldView;
    expect(plazaDecorOf(busy)).toHaveLength(ITEMS - 1);
    expect(plazaDecorOf({ ...field, decor: [] } as FieldView)).toEqual([]);
    expect(fieldScenery({ ...field, decor: [] } as FieldView, []).paving ?? null).toBeNull();
  });

  it("放射狀鋪法：地圖檔的範圍（11～20, 9～14），圓心在傳送石；只是外觀資料", () => {
    const scene = fieldScenery(field, []);
    expect(scene.paving).toMatchObject({ x0: 11, y0: 9, w: 10, h: 6, cx: 15.5, cy: 11.5 });
    expect(scene.paving!.cells.length).toBe(60);
    expect(scene.decor).toHaveLength(ITEMS);
    // 規則資料沒動：tiles 與 objects 原封不動
    expect(field.tiles.every((t) => t.walkable)).toBe(true);
  });

  it("畫法確定：同一件畫兩次一樣、不同位置不一樣；鋪法有同心接縫、放射接縫與一道金色嵌線", () => {
    for (const kind of ["flower_bed", "stall_cloth", "clothesline", "crate_stack"] as const) {
      const a = calls((c) => DECOR_DRAW[kind](c, 4, 7));
      expect(a, kind).toEqual(calls((c) => DECOR_DRAW[kind](c, 4, 7)));
      expect(a, kind).not.toEqual(calls((c) => DECOR_DRAW[kind](c, 9, 2)));
    }
    const p = fieldScenery(field, []).paving!;
    const row = calls((c) => drawPavingRow(c, p, 2));
    expect(row).toEqual(calls((c) => drawPavingRow(c, p, 2)));
    expect(row).toContain("strokeStyle=rgba(232,187,72,0.5)");
    const joints = PAVING_RINGS.slice(0, -1).reduce((n, r, i) => n + pavingJoints(r, PAVING_RINGS[i + 1]!), 0);
    expect(row.filter((x) => x.startsWith("lineTo(")).length).toBe(joints);
    expect(row.filter((x) => x.startsWith("rect(")).length).toBe(10);
  });
});
