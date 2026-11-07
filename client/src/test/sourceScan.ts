// 掃原始碼的規則測試共用工具（6C-R1）：在執行時用 node 的 fs 讀檔，不用 `import.meta.glob`。
// 原因：vitest 的 fsModuleCache（node_modules/.vitest-cache）會快取測試檔的編譯結果，連 eager glob 掃到的檔案清單
// 一起凍結；測試檔本身沒改時，新加的原始碼不會被掃到，規則形同空跑。執行時讀目錄就不受快取影響。
// 去註解用 typescript 的剖析器（內部驅動 scanner），字串、樣板字串、正則與 JSX 文字裡的 `//`、`/*` 都不會被誤當註解。
// @ts-expect-error 測試在 node 執行；專案沒裝 @types/node，只為了讀檔
import { readFileSync, readdirSync } from "node:fs";
import ts from "typescript";

interface Dirent {
  name: string;
  isDirectory(): boolean;
  isFile(): boolean;
}
const readDir = readdirSync as (url: URL, opts: { withFileTypes: true }) => Dirent[];
const readText = readFileSync as (url: URL, enc: string) => string;

/** `client/src/` 目錄。 */
export const SRC_DIR = new URL("../", import.meta.url);

/** 遞迴列出 `dir` 底下符合 `keep` 的檔案（相對路徑、`/` 分隔、排序過）。 */
export function listFiles(dir: URL, keep: (path: string) => boolean): string[] {
  const out: string[] = [];
  const walk = (url: URL, prefix: string): void => {
    for (const ent of readDir(url, { withFileTypes: true })) {
      if (ent.isDirectory()) {
        if (ent.name === "node_modules") continue;
        walk(new URL(`${ent.name}/`, url), `${prefix}${ent.name}/`);
      } else if (ent.isFile() && keep(`${prefix}${ent.name}`)) {
        out.push(`${prefix}${ent.name}`);
      }
    }
  };
  walk(dir, "");
  return out.sort();
}

/** 讀 `dir` 底下的一個檔案（`path` 為 `listFiles` 回傳的相對路徑）。 */
export function readFile(dir: URL, path: string): string {
  return readText(new URL(path, dir), "utf8");
}

const isTestFile = (p: string): boolean => /\.test\.tsx?$/.test(p);

/** `client/src/**` 的 .ts／.tsx 原始碼（不含測試檔、.d.ts）→ `[相對路徑, 原文]`。 */
export function readSources(): (readonly [string, string])[] {
  return listFiles(SRC_DIR, (p) => /\.tsx?$/.test(p) && !p.endsWith(".d.ts") && !isTestFile(p)).map((p) => [p, readFile(SRC_DIR, p)] as const);
}

/** `client/src/**` 的 .css → `[相對路徑, 原文]`。 */
export function readStyleFiles(): (readonly [string, string])[] {
  return listFiles(SRC_DIR, (p) => p.endsWith(".css")).map((p) => [p, readFile(SRC_DIR, p)] as const);
}

const blank = (s: string): string => s.replace(/[^\n]/g, " ");

function blankRanges(text: string, ranges: readonly (readonly [number, number])[]): string {
  const sorted = [...ranges].sort((a, b) => a[0] - b[0]);
  let out = "";
  let at = 0;
  for (const [s, e] of sorted) {
    if (s < at) continue;
    out += text.slice(at, s) + blank(text.slice(s, e));
    at = e;
  }
  return out + text.slice(at);
}

const isJsDoc = (n: ts.Node): boolean => n.kind >= ts.SyntaxKind.FirstJSDocNode && n.kind <= ts.SyntaxKind.LastJSDocNode;

/**
 * 去掉 TS／TSX 的註解（換成空白、保留換行，行號與位置不變）。
 * 用剖析器取得每個語彙單元，只在單元之間的空白區（trivia）找註解，所以字串、樣板字串、正則與 JSX 文字不受影響。
 */
export function stripTsComments(text: string, fileName = "file.tsx"): string {
  const kind = fileName.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS;
  const sf = ts.createSourceFile(fileName, text, ts.ScriptTarget.Latest, true, kind);
  const ranges = new Map<number, number>();
  const visit = (node: ts.Node): void => {
    if (isJsDoc(node)) return;
    const children = node.getChildren(sf);
    if (children.length === 0) {
      // JSX 文字是一整個單元，裡面的 `//` 不是註解
      if (node.kind === ts.SyntaxKind.JsxText) return;
      // 同一行的註解算前一個單元的 trailing，換行後的算 leading；兩種都要
      for (const r of ts.getTrailingCommentRanges(text, node.pos) ?? []) ranges.set(r.pos, r.end);
      for (const r of ts.getLeadingCommentRanges(text, node.pos) ?? []) ranges.set(r.pos, r.end);
      return;
    }
    for (const c of children) visit(c);
  };
  visit(sf);
  return blankRanges(text, [...ranges.entries()]);
}

/** 去掉 CSS 註解（換成空白、保留換行）；字串裡的 `/*` 不算。 */
export function stripCssComments(text: string): string {
  const ranges: [number, number][] = [];
  let i = 0;
  while (i < text.length) {
    const ch = text[i];
    if (ch === '"' || ch === "'") {
      i += 1;
      while (i < text.length && text[i] !== ch && text[i] !== "\n") i += text[i] === "\\" ? 2 : 1;
      i += 1;
    } else if (ch === "/" && text[i + 1] === "*") {
      const end = text.indexOf("*/", i + 2);
      const stop = end === -1 ? text.length : end + 2;
      ranges.push([i, stop]);
      i = stop;
    } else {
      i += 1;
    }
  }
  return blankRanges(text, ranges);
}

/**
 * `BattleRenderer` 類別的原始碼檔（`readSources` 的相對路徑）：R1e 起依職責拆到 `render/battle/`，依繼承順序排；
 * 類別本體與生命週期留在 `render/BattleRenderer.ts`。
 */
export const BATTLE_RENDERER_FILES = [
  "render/battle/rendererBase.ts",
  "render/battle/terrainLayer.ts",
  "render/battle/highlightLayer.ts",
  "render/battle/unitLayer.ts",
  "render/battle/feedbackLayer.ts",
  "render/battle/motionLayer.ts",
  "render/battle/skillLayer.ts",
  "render/battle/vfxLayer.ts",
  "render/BattleRenderer.ts",
] as const;

/** `BattleRenderer` 類別各檔串成一段（R1e 拆檔前針對單一檔案的接線檢查照舊適用）；`sources` 沒有其中一檔時丟例外。 */
export function battleRendererSource(sources: Readonly<Record<string, string>>): string {
  return BATTLE_RENDERER_FILES.map((f) => {
    const text = sources[f];
    if (text === undefined) throw new Error(`找不到 ${f}`);
    return text;
  }).join("\n");
}
