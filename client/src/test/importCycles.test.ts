// PERF-4b：`client/src` 非測試模組不得有執行期 import 環；工具本身也要驗，免得規則空跑。
import { describe, expect, it } from "vitest";
import { buildGraph, findCycles, resolveImport, runtimeImports } from "./importCycles";
import { readSources } from "./sourceScan";

const graphOf = (edges: Record<string, string[]>): Map<string, string[]> => new Map(Object.entries(edges));

describe("client/src 的執行期 import", () => {
  const sources = readSources().filter(([p]) => !p.startsWith("test/"));

  it("靜態 import 沒有環", () => {
    expect(findCycles(buildGraph(sources, (r) => r.eager))).toEqual([]);
  });

  it("算上動態 import() 也沒有環", () => {
    expect(findCycles(buildGraph(sources, (r) => [...r.eager, ...r.lazy]))).toEqual([]);
  });

  it("確實掃到真實的相依圖（防空跑）", () => {
    const graph = buildGraph(sources, (r) => r.eager);
    expect(graph.size).toBeGreaterThan(200);
    expect(graph.get("render/portrait.ts")).toContain("render/qSpec.ts");
    expect(graph.get("render/qSpec.ts")).toContain("render/itemColors.ts");
    expect(graph.get("render/paperdoll.ts")).toContain("render/qSpec.ts");
    expect(graph.get("render/itemColors.ts")).not.toContain("render/paperdoll.ts");
  });
});

describe("runtimeImports", () => {
  it("import type、export type 不算；一般 import、re-export、副作用 import 算", () => {
    const text = [
      'import type { A } from "./typeOnly";',
      'export type { B } from "./typeExport";',
      'import { c } from "./value";',
      'import { d, type D } from "./mixed";',
      'import "./effect";',
      'export { e } from "./reexport";',
      'export * from "./star";',
    ].join("\n");
    expect(runtimeImports(text, "a.ts").eager).toEqual(["./value", "./mixed", "./effect", "./reexport", "./star"]);
  });

  it("verbatimModuleSyntax 下全是 inline type 的 import 仍會載入模組，要算", () => {
    expect(runtimeImports('import { type A } from "./kept";', "a.ts").eager).toEqual(["./kept"]);
  });

  it("註解、字串裡的 import 字樣不算", () => {
    const text = ['// import { a } from "./comment";', 'const s = "import { b } from \'./string\'";', "export { s };"].join("\n");
    expect(runtimeImports(text, "a.ts")).toEqual({ eager: [], lazy: [] });
  });

  it("動態 import() 另外列；型別位置的 import(\"x\") 不算", () => {
    const text = 'type T = import("./typePos").T;\nexport const f = (): Promise<unknown> => import("./lazy");';
    expect(runtimeImports(text, "a.ts")).toEqual({ eager: [], lazy: ["./lazy"] });
  });

  it("tsx 也能解析", () => {
    expect(runtimeImports('import { X } from "./x";\nexport const y = <X />;', "a.tsx").eager).toEqual(["./x"]);
  });
});

describe("resolveImport", () => {
  const files = new Set(["render/a.ts", "render/b.tsx", "render/sub/index.ts", "ui/c.ts"]);

  it("解析相對路徑、副檔名與 index", () => {
    expect(resolveImport("render/x.ts", "./a", files)).toBe("render/a.ts");
    expect(resolveImport("render/x.ts", "./b", files)).toBe("render/b.tsx");
    expect(resolveImport("render/x.ts", "./sub", files)).toBe("render/sub/index.ts");
    expect(resolveImport("render/x.ts", "../ui/c", files)).toBe("ui/c.ts");
  });

  it("套件與不在清單內的資源不算", () => {
    expect(resolveImport("render/x.ts", "pixi.js", files)).toBeUndefined();
    expect(resolveImport("render/x.ts", "./style.css", files)).toBeUndefined();
  });
});

describe("findCycles", () => {
  it("找得到兩個、三個模組的環與自我 import", () => {
    expect(findCycles(graphOf({ a: ["b"], b: ["a"] }))).toEqual([["a", "b"]]);
    expect(findCycles(graphOf({ a: ["b"], b: ["c"], c: ["a"], d: ["a"] }))).toEqual([["a", "b", "c"]]);
    expect(findCycles(graphOf({ a: ["a"] }))).toEqual([["a"]]);
  });

  it("多個環分開回報", () => {
    expect(findCycles(graphOf({ a: ["b"], b: ["a"], c: ["d"], d: ["c"] }))).toEqual([["a", "b"], ["c", "d"]]);
  });

  it("菱形相依不是環", () => {
    expect(findCycles(graphOf({ a: ["b", "c"], b: ["d"], c: ["d"], d: [] }))).toEqual([]);
  });

  it("buildGraph 接起來能抓到環（原始碼 → 環）", () => {
    const sources = [
      ["a.ts", 'import { b } from "./b"; export const a = b;'],
      ["b.ts", 'import { a } from "./a"; export const b = a;'],
      ["c.ts", 'import type { D } from "./d"; export type C = D;'],
      ["d.ts", 'import type { C } from "./c"; export type D = C;'],
    ] as const;
    expect(findCycles(buildGraph(sources, (r) => r.eager))).toEqual([["a.ts", "b.ts"]]);
  });
});
