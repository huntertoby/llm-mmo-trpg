// Phase 6V-4b：主城裝飾搬進地圖檔（`look.decor`）、站著的裝飾和人物照 y 排序、噴水調大、後牆掛件最多 2 個。
// - 讀資料畫出來的結果和搬家前（6V-4 寫死在前端的 CAPITAL_DECOR）一模一樣：畫法呼叫的確定性雜湊鎖住；
// - 站著的（堆箱、晾衣繩）放所在排的物件層：北邊的人先畫（被擋住）、同排與南邊的人後畫（蓋住它）；地面的在人物下面；
// - 噴水：SPRAY_RISE 14（原 10，加 40%）、水珠直徑 12（原 8，半徑 ×1.5）；減少動態時靜止。
import { Container, Texture } from "pixi.js";
import { describe, expect, it } from "vitest";
import { type FieldView } from "../api/types";
import { TILE_SIZE } from "../battle/geometry";
import { type DrawModel } from "../battle/drawModel";
import { fountainSpray, SPRAY_RISE } from "../render/ambientAnim";
import { AmbientLayer, drawDrop, SPRAY_DROP } from "../render/ambientLayer";
import { HANGING_SETS, MAX_HANGINGS, wallDecor, wallHangings, type RoomKind } from "../render/interiorArt";
import { DECOR_DRAW, DECOR_ROWS, drawPavingRow, PAVING_RINGS, pavingJoints } from "../render/plazaDecor";
import { RowStack } from "../render/rowLayers";
import { decorLayerOf, SceneryLayer, type SceneryHost } from "../render/sceneryLayer";
import { capitalField, capitalDoc as doc } from "../test/capitalField";
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

function fnv(s: string): string {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h.toString(16).padStart(8, "0");
}

/** 搬家前（6V-4 的 CAPITAL_DECOR、源晶燈推算的鋪法；6V-4b 開工前在 71eb8352 上算的）的雜湊。 */
const BEFORE_ITEMS = "1f9081ed";
const BEFORE_PAVING = "92eb21cb";

describe("裝飾搬進地圖檔（6V-4b）", () => {
  it("讀資料畫出來的結果和搬家前一樣：14 件的種類、位置、圖層、畫布高與畫法呼叫；鋪法的範圍、圓心與每一列", () => {
    const scene = fieldScenery(capitalField(), ["cloud_ridge"]);
    const items = (scene.decor ?? []).map((d) => ({ kind: d.kind, x: d.x, y: d.y, w: d.w, layer: d.layer, rows: DECOR_ROWS[d.kind], calls: calls((c) => DECOR_DRAW[d.kind](c, d.x, d.y)) }));
    expect(items).toHaveLength(14);
    expect(fnv(JSON.stringify(items))).toBe(BEFORE_ITEMS);
    const p = scene.paving!;
    const paving = { x0: p.x0, y0: p.y0, w: p.w, h: p.h, cx: p.cx, cy: p.cy, cells: p.cells, rows: Array.from({ length: p.h }, (_, k) => calls((c) => drawPavingRow(c, p, k))) };
    expect(fnv(JSON.stringify(paving))).toBe(BEFORE_PAVING);
    // 傳送陣照舊
    expect(scene.plaza).toEqual({ x: 15, y: 11, open: ["cloud_ridge"] });
  });

  it("伺服器沒給 decor（或給了不認得的種類）就不畫那些；其他地圖可以照資料放", () => {
    expect(fieldScenery(capitalField(false), []).decor ?? []).toEqual([]);
    const odd = { ...capitalField(), decor: [{ kind: "fountain_jet", layer: "ground", x: 7, y: 14, width: 1, height: 1 }] } as unknown as FieldView;
    expect(fieldScenery(odd, []).decor ?? []).toEqual([]);
    const other = { ...capitalField(), map_id: "mist_ferry", region: "cloud_ridge" } as FieldView;
    const scene = fieldScenery(other, []);
    expect(scene.plaza ?? null).toBeNull();
    expect(scene.decor).toHaveLength(14);
  });
});

/** 測試用的 host：貼圖一律空白、`place` 只設位置。 */
function fakeHost(rows: RowStack): SceneryHost {
  return {
    art: { canvas: () => Texture.EMPTY } as unknown as SceneryHost["art"],
    rows,
    place: (node, _p, x, y) => node.position.set(x, y),
  };
}

/** 整棵圖層樹的畫的順序（先畫的在前）。 */
function drawOrder(root: Container): Container[] {
  const out: Container[] = [];
  const walk = (c: Container) => {
    out.push(c);
    for (const ch of c.children) walk(ch as Container);
  };
  walk(root);
  return out;
}

describe("站著的裝飾和人物照 y 排序（6V-4b）", () => {
  const field = capitalField();
  const scene = fieldScenery(field, []);
  const model = { width: field.width, height: field.height } as unknown as DrawModel;

  it("堆箱、晾衣繩放所在排的物件層；花壇、攤布放裝飾層", () => {
    const rows = new RowStack();
    rows.reset(field.height);
    for (const d of scene.decor ?? []) {
      const layer = decorLayerOf(rows, d);
      expect(layer, `${d.kind}@${d.x},${d.y}`).toBe(d.layer === "standing" ? rows.row(d.y).objects : rows.row(d.y).deco);
      expect(d.layer).toBe(d.kind === "crate_stack" || d.kind === "clothesline" ? "standing" : "ground");
    }
  });

  it("人站在堆箱後面（北邊一排）先畫＝被擋住；站在前面（南邊）或同一排後畫＝蓋住它；地面的花壇都在人物下面", () => {
    const rows = new RowStack();
    rows.reset(field.height);
    new SceneryLayer().draw(fakeHost(rows), model, scene);
    const crate = (scene.decor ?? []).find((d) => d.kind === "crate_stack" && d.x === 24 && d.y === 9)!;
    const crateNode = rows.row(crate.y).objects.children.find((c) => c.x === crate.x * TILE_SIZE && c.y === (crate.y - 1) * TILE_SIZE) as Container;
    expect(crateNode).toBeDefined();
    // 堆箱畫布兩格高：上面那一格蓋到北邊一排（站在後面的人的身體）
    expect(crateNode.height).toBe(DECOR_ROWS.crate_stack * TILE_SIZE);
    const behind = new Container();
    const front = new Container();
    const beside = new Container();
    rows.row(crate.y - 1).units.addChild(behind);
    rows.row(crate.y + 1).units.addChild(front);
    rows.row(crate.y).units.addChild(beside);
    const order = drawOrder(rows.root);
    const at = (c: Container) => order.indexOf(c);
    expect(at(behind)).toBeLessThan(at(crateNode));
    expect(at(front)).toBeGreaterThan(at(crateNode));
    expect(at(beside)).toBeGreaterThan(at(crateNode));
    // 晾衣繩同理（3 格寬）
    const line = (scene.decor ?? []).find((d) => d.kind === "clothesline")!;
    const lineNode = rows.row(line.y).objects.children.find((c) => c.x === line.x * TILE_SIZE) as Container;
    const back = new Container();
    rows.row(line.y - 1).units.addChild(back);
    expect(drawOrder(rows.root).indexOf(back)).toBeLessThan(drawOrder(rows.root).indexOf(lineNode));
    // 花壇在所在排的裝飾層：同一排的人畫在它上面
    const bed = (scene.decor ?? []).find((d) => d.kind === "flower_bed")!;
    const bedNode = rows.row(bed.y).deco.children.find((c) => c.x === bed.x * TILE_SIZE) as Container;
    const onBed = new Container();
    rows.row(bed.y).units.addChild(onBed);
    expect(drawOrder(rows.root).indexOf(onBed)).toBeGreaterThan(drawOrder(rows.root).indexOf(bedNode));
  });
});

describe("噴水調大（6V-4b）", () => {
  it("SPRAY_RISE 14（原 10 加 40%）；水珠直徑 12（原 8，半徑 ×1.5），貼圖的漸層半徑照著放大", () => {
    expect(SPRAY_RISE).toBe(14);
    expect(SPRAY_DROP).toBe(12);
    const got = calls((c) => drawDrop(c));
    expect(got[0]).toBe("createRadialGradient(4.500,4.500,0.500,6.000,6.000,6.000)");
    expect(got).toContain("fillRect(0.000,0.000,12.000,12.000)");
  });

  it("水弧的最高點照 SPRAY_RISE：drop＝0 時頂點在噴口上方 SPRAY_RISE", () => {
    const top = Math.min(...fountainSpray("s", 0, 30, 0).slice(0, 14).map((d) => d.y));
    expect(top).toBeGreaterThanOrEqual(-SPRAY_RISE - 1e-9);
    expect(top).toBeLessThan(-SPRAY_RISE * 0.9);
  });

  it("減少動態時靜止：時鐘停在 0，噴水停在第 0 毫秒的樣子", () => {
    const layer = new AmbientLayer();
    layer.reduced = true;
    for (let i = 0; i < 5; i++) layer.tick(333);
    expect(layer.clock).toBe(0);
    expect(fountainSpray("s", layer.clock, 30, 20)).toEqual(fountainSpray("s", 0, 30, 20));
  });
});

describe("後牆掛件最多 2 個、不疊在擺設上方（6V-4b）", () => {
  it("各種室內、各種寬度：最多 MAX_HANGINGS（2）個，不在擺設與緊貼後牆的物件那幾欄", () => {
    expect(MAX_HANGINGS).toBe(2);
    for (const kind of Object.keys(HANGING_SETS) as RoomKind[]) {
      for (let width = 6; width <= 16; width++) {
        for (const blocked of [[], [1], [5, 6, 7], [1, 2, 3, 6]]) {
          const decor = wallDecor(kind, width, blocked);
          const hang = wallHangings(kind, width, blocked, decor);
          expect(hang.length, `${kind} w${width}`).toBeLessThanOrEqual(2);
          const taken = new Set([...blocked, ...decor.flatMap((d) => Array.from({ length: d.w }, (_, i) => d.x + i))]);
          for (const h of hang) expect(taken.has(h.x), `${kind} w${width} @${h.x}`).toBe(false);
        }
      }
    }
    // 導師殿（空牆多）原本會掛到 3 個以上，現在 2 個
    expect(wallHangings("mentor", 16, [], wallDecor("mentor", 16, [])).map((h) => h.kind)).toEqual(HANGING_SETS.mentor.slice(0, 2));
  });
});

// --- 原 plaza6v4.test.ts ---
describe("原 plaza6v4.test.ts", () => {
// Phase 6V-4：主城廣場的只畫裝飾（花壇、攤布、晾衣繩、堆箱、放射狀鋪法）。版面照主城地圖的空格放：
// 不疊在物件、人、設施、門、建築、水上；格子與規則不變（只是 FieldScenery 的外觀資料）；畫法確定。
// 6V-4b：版面從前端的 `CAPITAL_DECOR` 搬到地圖檔 `look.decor`（API `FieldView.decor`）。

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
});
