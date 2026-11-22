// E4 第 6 項（KD-1 驗收小修 1）：「倒地」的說明框一條規則一行、前面加「・」，不再接狀態說明。
import { describe, expect, it } from "vitest";
import glossary from "../battle/fixtures/glossary.json";
import type { GlossaryEntry } from "../api/types";
import { entryTipParts } from "./tipParts";
import { statusTile } from "../render/skillIcon";

const statuses = (glossary as unknown as { statuses: GlossaryEntry[] }).statuses;
const prone = statuses.find((s) => s.id === "prone")!;

const LINES = [
  "不能使用反應（格擋、藉機攻擊、反擊）。",
  "倒地後的第一個自己回合少 1 AP。",
  "近戰攻擊你有優勢，遠程攻擊你有劣勢。",
  "不能衝鋒、跳躍、瞬步、攀跳。",
  "花一半移動點數站起來，或讓相鄰隊友扶起。",
  "站起來後會「站穩」，到下一個自己回合結束前不會再倒地。",
];

describe("E4：倒地的說明框", () => {
  it("名詞表的倒地只列規則、6 行一字不差", () => {
    expect(prone.rules_only).toBe(true);
    expect(prone.rules_zh).toEqual(LINES);
  });
  it("說明卡一條規則一段、前面加「・」，不接說明", () => {
    const parts = entryTipParts(prone, "狀態");
    expect(parts.map((p) => p.text)).toEqual(LINES.map((l) => `・${l}`));
    expect(parts.every((p) => !p.secondary)).toBe(true);
  });
  it("其他狀態照舊（說明＋規則接成一段）", () => {
    const burning = statuses.find((s) => s.id === "burning")!;
    expect(burning.rules_only).toBeUndefined();
    expect(entryTipParts(burning, "狀態")[0]!.text.startsWith(burning.description_zh ?? "")).toBe(true);
  });
  it("部件圓片的 tip 也一條一行", () => {
    expect(statusTile("prone").tip).toBe(LINES.map((l) => `・${l}`).join("\n"));
  });
});
