// HC-B：技能預算表的欄位依 `group_zh` 分組，畫成可收合的區塊；分組多時預設收合，只展開有改動或錯誤的組。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { TuningFieldView, TuningObjectDetail } from "../api/types";
import { FieldForm } from "./FieldForm";
import { editKey, fieldBlocks, groupOpen, OPEN_GROUPS_MAX, type Edits } from "./model";

const FILE = "skill_budget.yaml";
const f = (path: string, group: string): TuningFieldView => ({ path, pattern: path, label_zh: path, kind: "int", value: 1, note_zh: "", group_zh: group });
const GROUPS = ["原語點數", "狀態", "表面", "形狀", "係數", "召喚"];
const FIELDS = GROUPS.flatMap((g, i) => [f(`a${i}`, g), f(`b${i}`, g)]);
const DETAIL: TuningObjectDetail = { kind: "budget", id: "skill_budget", name_zh: "技能預算表（全體共用）", category: "rules", file: FILE, fields: FIELDS };

describe("技能預算表的分組（HC-B）", () => {
  it("每組一個可收合的區塊，標題帶欄位數", () => {
    const out = renderToStaticMarkup(createElement(FieldForm, { detail: DETAIL, edits: {}, check: null, onEdit: () => undefined, onDrop: () => undefined }));
    expect(out.match(/<details/g)?.length).toBe(GROUPS.length);
    for (const g of GROUPS) expect(out).toContain(`data-group="${g}"`);
    expect(out).toContain("（2）");
    expect(out).not.toMatch(/<details[^>]* open=""/);
  });

  it("分組多時只展開有改動的組；分組少（頭目部位）全展開", () => {
    const blocks = fieldBlocks(FIELDS);
    const edits: Edits = { [editKey(FILE, "a3")]: { file: FILE, path: "a3", old: 1, text: "2", label_zh: "a3", object_id: "skill_budget" } };
    const open = blocks.map((b) => groupOpen(b, GROUPS.length, edits, FILE, new Map()));
    expect(open).toEqual([false, false, false, true, false, false]);
    const errors = new Map([["b0", ["太大"]]]);
    expect(groupOpen(blocks[0]!, GROUPS.length, {}, FILE, errors)).toBe(true);
    expect(blocks.every((b) => groupOpen(b, OPEN_GROUPS_MAX, {}, FILE, new Map()))).toBe(true);
    const out = renderToStaticMarkup(createElement(FieldForm, { detail: DETAIL, edits, check: null, onEdit: () => undefined, onDrop: () => undefined }));
    expect(out.match(/<details[^>]* open=""/g)?.length).toBe(1);
  });
});
