// 大世界事件與任務畫面的純函式（Phase 5B-5）。
import { describe, expect, it } from "vitest";
import type { WorldDialogLine, WorldEventSolution, WorldQuestLog, WorldView } from "../api/types";
import { leftPane } from "./growth";
import {
  affinityLine,
  appendChat,
  canSendChat,
  canSubmitAnswer,
  checkFormula,
  CITE_MAX,
  dialogByNpc,
  dialogEntries,
  lengthLabel,
  PLAYER_TEXT_MAX,
  questBadge,
  solutionClick,
  solutionHint,
  solutionLabel,
  waiveLabel,
  sortQuests,
  stepMark,
  insertCite,
  narratorResting,
  toggleCite,
} from "./story";

function solution(over: Partial<WorldEventSolution> = {}): WorldEventSolution {
  return {
    index: 1,
    kind: "situation",
    kind_zh: "情境判定",
    note_zh: "找安全路",
    hint_zh: "",
    attributes_zh: "感知、力量",
    template: "peddler_safe_path",
    available: true,
    unavailable_zh: null,
    cost_supplies: 0,
    can_pay: true,
    waive_thread: null,
    waive_zh: null,
    ...over,
  };
}

function quest(id: string, done: boolean, steps: Array<[boolean, boolean]> = []): WorldQuestLog {
  return {
    id,
    name_zh: id,
    kind_zh: "新手",
    summary_zh: "",
    giver_zh: null,
    steps: steps.map(([d, c]) => ({ text_zh: "步", done: d, current: c })),
    done,
  };
}

describe("引用線索", () => {
  it("點一下引用、再點取消，最多 4 筆", () => {
    expect(toggleCite([], "thread:a")).toEqual(["thread:a"]);
    expect(toggleCite(["thread:a"], "thread:a")).toEqual([]);
    const full = ["a", "b", "c", "d"];
    expect(full.length).toBe(CITE_MAX);
    expect(toggleCite(full, "e")).toEqual(full);
  });

  it("引用時把關鍵詞插進回答（已有、沒有、太長都不動）", () => {
    expect(insertCite("", "補給")).toBe("補給");
    expect(insertCite("我想交換 ", "補給")).toBe("我想交換，補給");
    expect(insertCite("拿補給換", "補給")).toBe("拿補給換");
    expect(insertCite("繞路", null)).toBe("繞路");
    const long = "字".repeat(PLAYER_TEXT_MAX - 1);
    expect(insertCite(long, "補給")).toBe(long);
  });
});

describe("說書人休息中", () => {
  it("開關開著、模型不可用才顯示", () => {
    expect(narratorResting(null)).toBe(false);
    expect(narratorResting({ enabled: true, model_available: false })).toBe(true);
    expect(narratorResting({ enabled: true, model_available: true })).toBe(false);
    expect(narratorResting({ enabled: true, model_available: null })).toBe(false);
    expect(narratorResting({ enabled: false, model_available: false })).toBe(false);
  });
});

describe("文字長度", () => {
  it("字數與上限", () => {
    expect(lengthLabel("你好")).toBe(`2／${PLAYER_TEXT_MAX}`);
    expect(lengthLabel("字".repeat(PLAYER_TEXT_MAX + 1))).toContain("太長");
  });

  it("回答可以空白，聊天不行；忙碌時都不能送", () => {
    expect(canSubmitAnswer("", false)).toBe(true);
    expect(canSubmitAnswer("x", true)).toBe(false);
    expect(canSubmitAnswer("字".repeat(PLAYER_TEXT_MAX + 1), false)).toBe(false);
    expect(canSendChat("  ", false)).toBe(false);
    expect(canSendChat("你好", false)).toBe(true);
    expect(canSendChat("你好", true)).toBe(false);
  });
});

describe("解法按鈕", () => {
  it("可用與不可用的文字", () => {
    expect(solutionLabel(solution())).toBe("情境判定：找安全路（感知、力量）");
    expect(solutionHint(solution())).toContain("送出前可以換");
    const later = solution({ kind: "combat", kind_zh: "戰鬥", note_zh: "", attributes_zh: "", template: null, available: false, unavailable_zh: "之後開放" });
    expect(solutionLabel(later)).toBe("戰鬥");
    expect(solutionHint(later)).toBe("之後開放");
    const parley = solution({ kind: "parley", kind_zh: "交涉", note_zh: "付錢", attributes_zh: "", template: null, cost_supplies: 2 });
    expect(solutionLabel(parley)).toBe("交涉：付錢（付出 2 補給）");
    expect(solutionHint(parley)).toContain("一定成功");
    expect(solutionHint(solution({ kind: "combat", template: null }))).toContain("一般戰鬥");
    expect(solutionHint(solution({ kind: "abandon", template: null }))).toContain("不留懲罰");
  });

  it("補充說明只在說明卡（TXT-1）", () => {
    const fox = solution({ kind: "situation", note_zh: "說服", hint_zh: "獸耳族主角有專屬的對話", attributes_zh: "意志" });
    expect(solutionLabel(fox)).toBe("情境判定：說服（意志）");
    expect(solutionHint(fox).split("\n")).toEqual(["獸耳族主角有專屬的對話", "看看處境，再寫你打算怎麼做（送出前可以換別的解法）"]);
    expect(solutionHint({ ...fox, available: false, unavailable_zh: "戰鬥中" })).toBe("戰鬥中");
  });

  it("解法按鈕送什麼、用線頭抵的按鈕", () => {
    expect(solutionClick(solution())).toEqual({ kind: "open", template: "peddler_safe_path" });
    expect(solutionClick(solution({ kind: "parley", index: 2, template: null }))).toEqual({ kind: "solve", solution: 2 });
    expect(solutionClick(solution({ kind: "combat", index: 0, template: null }))).toEqual({ kind: "solve", solution: 0 });
    expect(solutionClick(solution({ kind: "abandon", index: 3, template: null }))).toEqual({ kind: "solve", solution: 3 });
    expect(solutionClick(solution({ kind: "opportunity", index: 0, template: null }))).toEqual({ kind: "solve", solution: 0 });
    expect(solutionHint(solution({ kind: "opportunity", template: null }))).toContain("機遇技能三選一");
    expect(waiveLabel(solution())).toBeNull();
    expect(waiveLabel(solution({ kind: "parley", waive_thread: "peddler_owes_you", waive_zh: "商人欠你人情" }))).toBe("用〔商人欠你人情〕抵");
  });
});

describe("好感度與任務", () => {
  it("好感度一行帶級距與目前值", () => {
    expect(affinityLine({ range_zh: "中立（−9～19）", affinity: 0 })).toBe("中立（−9～19）・目前 0");
    expect(affinityLine({ range_zh: "冷淡（−49～−10）", affinity: -12 })).toBe("冷淡（−49～−10）・目前 −12");
  });

  it("步驟記號與排序（進行中在前）", () => {
    expect(stepMark({ text_zh: "", done: true, current: false })).toBe("✔");
    expect(stepMark({ text_zh: "", done: false, current: true })).toBe("▶");
    expect(stepMark({ text_zh: "", done: false, current: false })).toBe("・");
    expect(sortQuests([quest("a", true), quest("b", false)]).map((q) => q.id)).toEqual(["b", "a"]);
  });

  it("任務與線頭按鈕的小字", () => {
    const view = { quests: [quest("a", false), quest("b", true)], threads: [{ id: "t" }] } as unknown as WorldView;
    expect(questBadge(view)).toBe("任務 1・線頭 1");
    expect(questBadge({ quests: [], threads: [] } as unknown as WorldView)).toBe("");
  });
});

describe("對話紀錄", () => {
  const lines: WorldDialogLine[] = [
    { npc: "granny_du", speaker_zh: "渡婆婆", kind: "rumor", text_zh: "北坡最近不太平。", more_zh: "", source: null },
    { npc: "granny_du", speaker_zh: "渡婆婆", kind: "chat", text_zh: "孩子，先去渡口看看。", more_zh: "那裡有人搶船。", source: "fallback" },
  ];

  it("依 NPC 分組、傳聞加標籤", () => {
    const grouped = dialogByNpc(lines);
    expect(Object.keys(grouped)).toEqual(["granny_du"]);
    const entries = dialogEntries(grouped["granny_du"]!);
    expect(entries[0]!.text).toBe("〔傳聞〕北坡最近不太平。");
    expect(entries[1]!.more).toBe("那裡有人搶船。");
  });

  it("紀錄接在後面並保留上限", () => {
    let log = appendChat({}, "a", [{ speaker: "你", text: "1", mine: true }]);
    log = appendChat(log, "a", [{ speaker: "甲", text: "2", mine: false }], 1);
    expect(log["a"]!.map((e) => e.text)).toEqual(["2"]);
  });
});

describe("判定算式", () => {
  it("帶模式、修正與 DC 調整", () => {
    const text = checkFormula({ roll: 12, mode_zh: "一般", attribute_mod: 1, care_bonus: 1, race_bonus: 0, total: 14, dc: 12, base_dc: 13, dc_shift: -1 });
    expect(text).toBe("d20 12（一般）＋1屬性＋1用心＋0種族 ＝ 14 vs DC 12（基準 13，−1）");
  });
});

describe("左欄：三選一與任務日誌", () => {
  const base = { pending_flash: null, pending_offer: null } as unknown as WorldView;
  it("閃現優先、其次三選一，否則照玩家切換", () => {
    expect(leftPane({ ...base, pending_offer: {} } as unknown as WorldView, "quests")).toBe("offer");
    expect(leftPane({ ...base, pending_flash: {}, pending_offer: {} } as unknown as WorldView, "map")).toBe("pending");
    expect(leftPane(base, "quests")).toBe("quests");
    expect(leftPane(base, true)).toBe("growth");
  });
});
