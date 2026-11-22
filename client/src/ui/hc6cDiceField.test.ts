// HC-6c（AR-X10 待決 5）：說明卡的骰子行改讀 /api/glossary 的結構化欄位 `rules_dice`，不再比對句型。
import { describe, expect, it } from "vitest";
import type { Glossary, GlossaryEntry } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { entryTipParts, tipParts } from "./tipParts";

const KINDS = ["terrain", "surfaces", "objects", "statuses", "stacks"] as const;
const entries = (): GlossaryEntry[] => KINDS.flatMap((k) => (glossary as unknown as Glossary)[k]);

describe("HC-6c：名詞表的骰子欄", () => {
  it("rules_dice 指到的行就是「擲 NdM，每點 ×K」，骰子數字和欄位相同", () => {
    let n = 0;
    for (const e of entries()) {
      for (const d of e.rules_dice) {
        const line = e.rules_zh[d.line];
        expect(line, `${e.id}#${d.line}`).toBe(d.scale === 1 ? `擲 ${d.count}d${d.sides}` : `擲 ${d.count}d${d.sides}，每點 ×${d.scale}`);
        n += 1;
      }
    }
    expect(n).toBeGreaterThan(0);
  });
  it("照欄位分段的結果和 AR-X10 的句型比對相同（字和排法都不變）", () => {
    const old = /^擲 \d+d\d+，每點 ×\d+$/u;
    for (const e of entries()) {
      const lines = [e.description_zh ?? "", ...e.rules_zh];
      const byPattern = tipParts(lines, new Set(lines.flatMap((l, i) => (old.test(l) ? [i] : []))));
      expect(entryTipParts(e, "x"), e.id).toEqual(byPattern.length === 0 ? [{ text: "x", secondary: false }] : byPattern);
    }
  });
  it("欄位說了算：同一句沒標成骰子行就照一般句接起來", () => {
    const e = { id: "t", name_zh: "t", description_zh: "說明", tags: [], rules_zh: ["受到 10–60 傷害", "擲 1d6，每點 ×10"], rules_dice: [] } as unknown as GlossaryEntry;
    expect(entryTipParts(e, "x")).toEqual([{ text: "說明 受到 10–60 傷害 擲 1d6，每點 ×10", secondary: false }]);
    const marked = { ...e, rules_dice: [{ line: 1, count: 1, sides: 6, scale: 10 }] } as GlossaryEntry;
    expect(entryTipParts(marked, "x")).toEqual([
      { text: "說明 受到 10–60 傷害", secondary: false },
      { text: "擲 1d6，每點 ×10", secondary: true },
    ]);
    expect(entryTipParts(undefined, "狀態")).toEqual([{ text: "狀態", secondary: false }]);
  });
});
