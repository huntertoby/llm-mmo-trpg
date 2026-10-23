// Phase 3-41b：動作說明浮動卡的文字來自名詞對照表（後端依 core.yaml 產生），前端不寫死規則數字。
import { describe, expect, it } from "vitest";
import { actionCardText, actionHint, actionSummary, moreActionsSummary } from "./actionInfo";
import { objectiveRules } from "./objective";
import { BASIC_MODES, MORE_KINDS } from "./targeting";

const ui = import.meta.glob("../ui/TurnControls.tsx", { query: "?raw", import: "default", eager: true }) as Record<string, string>;

describe("動作說明", () => {
  it("常駐按鈕與「更多動作」的每一項都有浮動卡文字", () => {
    for (const kind of [...MORE_KINDS, "attack", "run", "defend", "move", "end_turn"]) {
      const text = actionCardText(kind);
      expect(text, kind).not.toBeNull();
      expect(text!.split("\n").length, kind).toBeGreaterThan(1);
    }
    // 基本動作表裡的每個種類（除了技能、充能）都有說明
    for (const m of BASIC_MODES) expect(actionSummary(m.kind), m.kind).not.toBeNull();
  });

  it("跑步與守護的數字來自對照表", () => {
    expect(actionSummary("run")).toContain("+3 格");
    expect(actionSummary("defend")).toContain("25%");
    expect(actionHint("run", "不能跑步：定身")).toMatch(/^不能跑步：定身\n・/);
  });

  it("「更多動作」鈕的說明列出對照表裡的動作名稱", () => {
    expect(moreActionsSummary(MORE_KINDS)).toContain("推擊、絆倒、推動物件");
  });

  it("UI 原始碼沒有寫死規則數字（跑步 +3 格、守護 +25%）", () => {
    const src = Object.values(ui).join("");
    expect(src.length).toBeGreaterThan(100);
    expect(src).not.toMatch(/\+3 格|\+25%|花 1 AP/);
  });

  it("勝利條件的規則列補上限時輪數、寫出召喚物與判定時機", () => {
    const lines = objectiveRules({ kind: "defend", rounds: 6 }).join("\n");
    expect(lines).toContain("守住守點 6 輪");
    expect(lines).toContain("每輪結束時");
    expect(lines).toContain("召喚物");
    expect(objectiveRules({ kind: "escape", rounds: 5 }).join("\n")).toContain("倒下的隊友不用撤");
  });
});
