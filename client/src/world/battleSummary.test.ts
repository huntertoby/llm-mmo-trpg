// 6F-1：大世界戰後結算的句子（經驗、戰利品、任務進度、HP 說明）。
import { describe, expect, it } from "vitest";
import type { WorldView } from "../api/types";
import { battleSummary, HP_NOTE_ZH } from "./battleSummary";

function view(events: string[], loot: string | null = null, quests: unknown[] = []): WorldView {
  return {
    events,
    last_loot_zh: loot,
    quests,
    threads: [],
    character: { xp: 400, xp_next: 950, level: 1, hp: 6, max_hp: 40 },
  } as unknown as WorldView;
}

describe("battleSummary", () => {
  it("打贏：伺服器句子＋經驗進度＋HP 不會自動回", () => {
    const s = battleSummary(view(["打贏了（3 輪），獲得 100 經驗。", "掉落：焦鐵 ×1。", "任務「霧渡新手路」完成第 1 步（＋300 經驗）。"], "掉落：焦鐵 ×1。"));
    expect(s.lines).toContain("經驗 400／950（Lv 1）");
    expect(s.lines.some((l) => l.includes("沒有掉落"))).toBe(false);
    expect(s.note).toBe(`HP 6／40：${HP_NOTE_ZH}`);
  });

  it("打贏沒掉落：補一句；沒有任務句子時帶追蹤中的任務進度", () => {
    const quest = { id: "q", name_zh: "霧渡新手路", done: false, summary_zh: "", steps: [{ text_zh: "竹林小徑", current: true, done: false }] };
    const s = battleSummary(view(["打贏了（2 輪），獲得 50 經驗。"], null, [quest]));
    expect(s.lines).toContain("戰利品：這場沒有掉落。");
    expect(s.lines.some((l) => l.startsWith("任務「霧渡新手路」"))).toBe(true);
  });

  it("輸了：不寫 HP 說明（會被抬回城鎮）", () => {
    const s = battleSummary(view(["戰鬥失敗（全滅）。", "被抬回霧渡鎮，HP、法力回滿；下一場戰鬥帶「疲憊」。"]));
    expect(s.note).toBeNull();
    expect(s.lines.some((l) => l.includes("沒有掉落"))).toBe(false);
  });
});
