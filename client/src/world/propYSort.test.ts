// 6F-6：鐵匠鋪的鐵砧照 y 排序（巡檢 bug 16，同 6V-4b）、灰渡口半沉渡船的木箱加水線（美術 PM 6V-2b 檢查第 3 節第 1 點）。
import { Container, Texture } from "pixi.js";
import { parse } from "yaml";
import { describe, expect, it } from "vitest";
import smithyYaml from "../../../content/world/fields/cloud_ridge/interiors/mist_ferry_smithy.yaml?raw";
import ashFerryYaml from "../../../content/world/fields/ashen_waste/ash_ferry.yaml?raw";
import type { ObjectDraw } from "../battle/drawModel";
import { TILE_SIZE } from "../battle/geometry";
import { FURNITURE_ROWS } from "../render/interiorArt";
import { RowStack } from "../render/rowLayers";
import { objectLayerOf, SceneryLayer, type SceneryHost } from "../render/sceneryLayer";
import type { FieldScenery } from "../render/sceneryModel";
import { isSubmerged, SUBMERGED_ALPHA, waterline, WATERLINE } from "../render/submerged";

type XY = [number, number];
interface FieldDoc {
  size: XY;
  terrain: string;
  legend: Record<string, string>;
  objects: Array<{ at: XY; kind: string; look?: string }>;
  look?: Record<string, string>;
}

const T = TILE_SIZE;

function fakeHost(rows: RowStack): SceneryHost {
  return { art: { canvas: () => Texture.EMPTY } as unknown as SceneryHost["art"], rows, place: (node, _p, x, y) => node.position.set(x, y) };
}

function drawOrder(root: Container): Container[] {
  const out: Container[] = [];
  const walk = (c: Container) => {
    out.push(c);
    for (const ch of c.children) walk(ch as Container);
  };
  walk(root);
  return out;
}

describe("6F-6 the smithy anvil is y-sorted like standing decor (6V-4b)", () => {
  const doc = parse(smithyYaml) as FieldDoc;
  const anvil = doc.objects.find((o) => o.look === "anvil")!;
  const [ax, ay] = anvil.at;

  it("the anvil sits at (4,2) in 石記鐵鋪; its node is two tiles tall and goes in its own row's object layer", () => {
    expect([ax, ay]).toEqual([4, 2]);
    const rows = new RowStack();
    rows.reset(doc.size[1]);
    const layer = new SceneryLayer();
    const scenery: FieldScenery = { buildings: [], doors: [], interior: null, furniture: { [`${ax},${ay}`]: { look: "anvil", joinW: false, joinE: false } } };
    layer.draw(fakeHost(rows), { width: doc.size[0], height: doc.size[1] } as never, scenery);
    const look = layer.objectNode(fakeHost(rows), { x: ax, y: ay } as ObjectDraw)!;
    expect(look.dy).toBe(-(FURNITURE_ROWS - 1) * T);
    expect(look.node.height).toBe(FURNITURE_ROWS * T);
    expect(objectLayerOf(rows, { y: ay })).toBe(rows.row(ay).objects);
  });

  it("standing south of the anvil (4,3) draws over it; north (4,1) is covered by it; beside it (5,2) draws over it", () => {
    const rows = new RowStack();
    rows.reset(doc.size[1]);
    const anvilNode = new Container();
    objectLayerOf(rows, { y: ay }).addChild(anvilNode);
    const south = new Container();
    const north = new Container();
    const beside = new Container();
    rows.row(ay + 1).units.addChild(south);
    rows.row(ay - 1).units.addChild(north);
    rows.row(ay).units.addChild(beside);
    const order = drawOrder(rows.root);
    const at = (c: Container) => order.indexOf(c);
    expect(at(south)).toBeGreaterThan(at(anvilNode));
    expect(at(beside)).toBeGreaterThan(at(anvilNode));
    expect(at(north)).toBeLessThan(at(anvilNode));
  });
});

describe("6F-6 the half-sunk ferry crates at 灰渡口 get a waterline", () => {
  const doc = parse(ashFerryYaml) as FieldDoc;
  const lines = doc.terrain.trim().split("\n");
  const tiles = lines.flatMap((row) => [...row].map((ch) => ({ terrain: doc.legend[ch] ?? "?" })));
  const look = Object.entries(doc.look ?? {})
    .filter(([, v]) => typeof v === "string")
    .map(([k, v]) => `${k}=${v}`)
    .join(",");
  const model = { width: doc.size[0], look, tiles };

  it("both crates (2,7) and (3,7) stand on deep water; the scrap heap on the bank does not", () => {
    const crates = doc.objects.filter((o) => o.kind === "crate").map((o) => o.at);
    expect(crates).toEqual([
      [2, 7],
      [3, 7],
    ]);
    for (const [x, y] of crates) expect(isSubmerged(model, { x, y })).toBe(true);
    const rubble = doc.objects.find((o) => o.kind === "rubble")!;
    expect(isSubmerged(model, { x: rubble.at[0], y: rubble.at[1] })).toBe(false);
  });

  it("only maps whose chasm is drawn as deep water: the same tile on a default chasm map is not submerged", () => {
    expect(isSubmerged({ ...model, look: "" }, { x: 2, y: 7 })).toBe(false);
    expect(isSubmerged({ ...model, look: "chasm_style=default" }, { x: 2, y: 7 })).toBe(false);
  });

  it("the waterline sits in the lower half of the cell, inside the cell edges; below it the crate is see-through", () => {
    const w = waterline(T);
    expect(w.y).toBe(Math.round(T * WATERLINE));
    expect(w.y).toBeGreaterThan(T / 2);
    expect(w.y).toBeLessThan(T);
    expect(w.x0).toBeGreaterThan(0);
    expect(w.x1).toBeLessThan(T);
    for (const r of w.ripples) expect(r.x - r.r >= w.x0 && r.x + r.r <= w.x1).toBe(true);
    expect(SUBMERGED_ALPHA).toBeGreaterThan(0);
    expect(SUBMERGED_ALPHA).toBeLessThan(1);
  });
});
