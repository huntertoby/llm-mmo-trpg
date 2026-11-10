// PERF-4b：找 `client/src` 非測試模組的執行期 import 環。
// 用專案既有的 typescript 剖析器（sourceScan 也用它），註解與字串裡的 import 字樣不會被誤認。
import ts from "typescript";

/** 一個檔案的執行期相依：`eager` 是載入時就要跑的靜態 import／re-export，`lazy` 是 `import("…")`。 */
export interface RuntimeImports {
  eager: string[];
  lazy: string[];
}

/**
 * 列出會留到執行期的 import 來源。`import type`、`export type` 編譯後消失，不算。
 * `import { type A } from "x"` 要算：專案開 verbatimModuleSyntax，這種寫法編譯後會留下 `import {} from "x"`，模組照樣被載入。
 */
export function runtimeImports(text: string, fileName: string): RuntimeImports {
  const kind = fileName.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS;
  const sf = ts.createSourceFile(fileName, text, ts.ScriptTarget.Latest, true, kind);
  const eager: string[] = [];
  const lazy: string[] = [];
  const visit = (node: ts.Node): void => {
    if (ts.isImportDeclaration(node) && ts.isStringLiteral(node.moduleSpecifier)) {
      if (node.importClause?.isTypeOnly !== true) eager.push(node.moduleSpecifier.text);
    } else if (ts.isExportDeclaration(node) && node.moduleSpecifier !== undefined && ts.isStringLiteral(node.moduleSpecifier)) {
      if (!node.isTypeOnly) eager.push(node.moduleSpecifier.text);
    } else if (ts.isCallExpression(node) && node.expression.kind === ts.SyntaxKind.ImportKeyword) {
      const arg = node.arguments[0];
      if (arg !== undefined && ts.isStringLiteralLike(arg)) lazy.push(arg.text);
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return { eager, lazy };
}

/** 把相對 import 解析成 `files` 裡的路徑；套件、資源檔（css、json…）回傳 undefined。 */
export function resolveImport(from: string, spec: string, files: ReadonlySet<string>): string | undefined {
  if (!spec.startsWith(".")) return undefined;
  const parts = from.split("/").slice(0, -1);
  for (const seg of spec.split("/")) {
    if (seg === "..") parts.pop();
    else if (seg !== ".") parts.push(seg);
  }
  const base = parts.join("/");
  return [base, `${base}.ts`, `${base}.tsx`, `${base}/index.ts`, `${base}/index.tsx`].find((p) => files.has(p));
}

/** 由 `[相對路徑, 原文]` 建相依圖（鍵與相依都排序過）。 */
export function buildGraph(sources: readonly (readonly [string, string])[], pick: (r: RuntimeImports) => readonly string[]): Map<string, string[]> {
  const files = new Set(sources.map(([p]) => p));
  const graph = new Map<string, string[]>();
  for (const [path, text] of [...sources].sort((a, b) => (a[0] < b[0] ? -1 : 1))) {
    const deps = new Set<string>();
    for (const spec of pick(runtimeImports(text, path))) {
      const dep = resolveImport(path, spec, files);
      if (dep !== undefined) deps.add(dep);
    }
    graph.set(path, [...deps].sort());
  }
  return graph;
}

/** 回傳圖裡所有的環（Tarjan 強連通分量：兩個以上互通的模組，或自己 import 自己）。 */
export function findCycles(graph: ReadonlyMap<string, readonly string[]>): string[][] {
  const index = new Map<string, number>();
  const low = new Map<string, number>();
  const onStack = new Set<string>();
  const stack: string[] = [];
  const out: string[][] = [];
  const connect = (v: string): void => {
    index.set(v, index.size);
    low.set(v, index.get(v)!);
    stack.push(v);
    onStack.add(v);
    for (const w of graph.get(v) ?? []) {
      if (!index.has(w)) {
        connect(w);
        low.set(v, Math.min(low.get(v)!, low.get(w)!));
      } else if (onStack.has(w)) {
        low.set(v, Math.min(low.get(v)!, index.get(w)!));
      }
    }
    if (low.get(v) !== index.get(v)) return;
    const scc: string[] = [];
    for (;;) {
      const w = stack.pop()!;
      onStack.delete(w);
      scc.push(w);
      if (w === v) break;
    }
    if (scc.length > 1 || (graph.get(v) ?? []).includes(v)) out.push(scc.sort());
  };
  for (const v of [...graph.keys()].sort()) if (!index.has(v)) connect(v);
  return out.sort((a, b) => (a[0]! < b[0]! ? -1 : 1));
}
