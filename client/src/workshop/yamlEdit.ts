// 「進階：直接編輯 YAML」：草稿 ⇄ 文字。JSON 也是合法的 YAML，所以貼 JSON 也可以。
import { parse, stringify } from "yaml";
import { isJson, type Json } from "./draft";

export function draftToYaml(draft: Json): string {
  if (Object.keys(draft).length === 0) return "";
  return stringify(draft, { lineWidth: 0 });
}

export type ParseResult = { ok: true; draft: Json } | { ok: false; error: string };

/** 文字 → 草稿。空白視為空草稿；不是 YAML 物件時回傳中文錯誤（含行號）。 */
export function parseDraftText(text: string): ParseResult {
  if (text.trim() === "") return { ok: true, draft: {} };
  let value: unknown;
  try {
    value = parse(text);
  } catch (e) {
    const err = e as { linePos?: { line: number; col: number }[] };
    const where = err.linePos?.[0];
    const head = where === undefined ? "" : `第 ${where.line} 行第 ${where.col} 欄附近，`;
    return { ok: false, error: `YAML 格式有誤：${head}請檢查括號、冒號、引號與縮排` };
  }
  if (!isJson(value)) return { ok: false, error: "技能必須寫成「欄位: 值」的形式（YAML 物件），不能只是一個值或清單" };
  return { ok: true, draft: value };
}

/** 兩個草稿內容是否相同（忽略欄位順序）。 */
export function sameDraft(a: Json, b: Json): boolean {
  return canonical(a) === canonical(b);
}

function canonical(v: unknown): string {
  if (Array.isArray(v)) return `[${v.map(canonical).join(",")}]`;
  if (isJson(v)) {
    return `{${Object.keys(v)
      .sort()
      .map((k) => `${JSON.stringify(k)}:${canonical(v[k])}`)
      .join(",")}}`;
  }
  return JSON.stringify(v) ?? "null";
}
