// Phase 6V-4：主城廣場的只畫裝飾（花壇、攤布、晾衣繩、堆箱、放射狀鋪法）。版面照主城地圖的空格放：
// 不疊在物件、人、設施、門、建築、水上；格子與規則不變（只是 FieldScenery 的外觀資料）；畫法確定。
import { describe, expect, it } from "vitest";
import { parse } from "yaml";
import capitalYaml from "../../../content/world/fields/capital/capital.yaml?raw";
import type { FieldView } from "../api/types";
import { CAPITAL_DECOR, DECOR_DRAW, drawPavingRow, PAVING_RINGS, pavingJoints } from "../render/plazaDecor";
import { fieldScenery, plazaDecorOf } from "./fieldScenery";

interface CapitalDoc {
  size: [number, number];
  terrain: string;
  legend: Record<string, string>;
  objects: Array<{ at: [number, number]; kind: string; look?: string }>;
  buildings: Array<{ kind: string; at: [number, number]; size: [number, number] }>;
  surfaces: Array<{ at: [number, number]; surface: string }>;
  doors: Array<{ id: string; at: [number, number] }>;
  teleport_stones: Array<{ id: string; at: [number, number] }>;
  facilities: Array<{ at: [number, number]; id: string }>;
  situation_objects: Array<{ at: [number, number]; id: string; name_zh?: string }>;
}

const doc = parse(capitalYaml) as CapitalDoc;

/** 照主城 yaml 組一張 FieldView（地形、物件、建築、表面、門、傳送石、設施、情境物件）。 */
function capitalField(): FieldView {
  const rows = doc.terrain.trim().split("\n");
  const surf = new Map(doc.surfaces.map((s) => [`${s.at[0]},${s.at[1]}`, s.surface]));
  const tiles = rows.flatMap((row, y) => [...row].map((ch, x) => ({ x, y, height: 0, terrain: doc.legend[ch]!, surface: surf.get(`${x},${y}`) ?? "none", walkable: true })));
  return {
    map_id: "capital",
    region: "capital",
    interior: false,
    width: doc.size[0],
    height: doc.size[1],
    tiles,
    objects: doc.objects.map((o, i) => ({ id: `o${i}`, kind: o.kind, x: o.at[0], y: o.at[1], look: o.look ?? null })),
    buildings: doc.buildings.map((b) => ({ kind: b.kind, x: b.at[0], y: b.at[1], width: b.size[0], height: b.size[1], sign: null })),
    doors: doc.doors.map((d) => ({ id: d.id, x: d.at[0], y: d.at[1] })),
    stones: doc.teleport_stones.map((s) => ({ id: s.id, x: s.at[0], y: s.at[1], unlocked: true })),
    facilities: doc.facilities.map((f) => ({ kind: f.id, x: f.at[0], y: f.at[1], figure: null })),
    situation_objects: doc.situation_objects.map((s) => ({ id: s.id, name_zh: s.name_zh ?? "", x: s.at[0], y: s.at[1] })),
    npcs: [],
    exits: [],
  } as unknown as FieldView;
}

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

describe("主城廣場裝飾（6V-4）", () => {
  const field = capitalField();

  it("版面上 14 件都放得下（格子空著），種類齊全：花壇、攤布、晾衣繩、堆箱", () => {
    const decor = plazaDecorOf(field);
    expect(decor).toHaveLength(CAPITAL_DECOR.length);
    expect(new Set(decor.map((d) => d.kind))).toEqual(new Set(["flower_bed", "stall", "clothesline", "crates"]));
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

  it("格子被佔了（例：有人站上去、內容多了物件）那一件就不畫；室內、其他地圖沒有裝飾", () => {
    const first = CAPITAL_DECOR[0]!;
    const busy = { ...field, objects: [...field.objects, { id: "x", kind: "crate", x: first.x, y: first.y, look: null }] } as FieldView;
    expect(plazaDecorOf(busy)).toHaveLength(CAPITAL_DECOR.length - 1);
    expect(plazaDecorOf({ ...field, interior: true } as FieldView)).toEqual([]);
    expect(plazaDecorOf({ ...field, map_id: "mist_ferry" } as FieldView)).toEqual([]);
  });

  it("放射狀鋪法：四盞源晶燈圍起來的範圍（11～20, 9～14），圓心在傳送石；只是外觀資料", () => {
    const plaza = fieldScenery(field, []).plaza!;
    expect(plaza.paving).toMatchObject({ x0: 11, y0: 9, w: 10, h: 6, cx: 15.5, cy: 11.5 });
    expect(plaza.paving!.cells.length).toBe(60);
    expect(plaza.decor).toHaveLength(CAPITAL_DECOR.length);
    // 規則資料沒動：tiles 與 objects 原封不動
    expect(field.tiles.every((t) => t.walkable)).toBe(true);
  });

  it("畫法確定：同一件畫兩次一樣、不同位置不一樣；鋪法有同心接縫、放射接縫與一道金色嵌線", () => {
    for (const kind of ["flower_bed", "stall", "clothesline", "crates"] as const) {
      const a = calls((c) => DECOR_DRAW[kind](c, 4, 7));
      expect(a, kind).toEqual(calls((c) => DECOR_DRAW[kind](c, 4, 7)));
      expect(a, kind).not.toEqual(calls((c) => DECOR_DRAW[kind](c, 9, 2)));
    }
    const p = fieldScenery(field, []).plaza!.paving!;
    const row = calls((c) => drawPavingRow(c, p, 2));
    expect(row).toEqual(calls((c) => drawPavingRow(c, p, 2)));
    expect(row).toContain("strokeStyle=rgba(232,187,72,0.5)");
    const joints = PAVING_RINGS.slice(0, -1).reduce((n, r, i) => n + pavingJoints(r, PAVING_RINGS[i + 1]!), 0);
    expect(row.filter((x) => x.startsWith("lineTo(")).length).toBe(joints);
    expect(row.filter((x) => x.startsWith("rect(")).length).toBe(10);
  });
});
