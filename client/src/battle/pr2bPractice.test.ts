// PR-2b（#147 靶場測試模式前端）行為一致測試 B 組：`BattleView.practice` 的每個分支。
// 實戰（`practice=false`）的輸出要和改前逐字相同（改前的句子直接寫在表裡）；測試模式才換字、拿掉冷卻與「結束回合」。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { WorldView } from "../api/types";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { BattleStatusBox } from "../ui/BattleStatusBox";
import { practicePreviewRows } from "../ui/ActionPanel";
import { costParts } from "../ui/SkillBar";
import { PracticeBar } from "../ui/TurnBar";
import { TurnControls } from "../ui/TurnControls";
import { WORKSHOP_NEW_TAG, WorkshopPanel, practiceRow, type WorkshopData } from "../world/WorkshopPanel";
import { panelAvailable } from "../world/hud";
import { objectHud } from "../world/atlasModel";
import {
  PRACTICE_EXIT_LABEL,
  SANDBOX_NOTE,
  TRIAL_EXIT_LABEL,
  rangeExitLabel,
  rangeFightNotes,
  rangeFightPlace,
  rangePlaceName,
} from "../world/range";
import type { LogLine } from "./log";
import { groupLog, practiceRoundLines, practiceRoundText } from "./logGroups";
import { PRACTICE_BAR_ZH, PRACTICE_SANDBOX_TAG_ZH, PRACTICE_SURE_NOTE_ZH, actionHintText, practiceWording } from "./skillTray";
import { smallView } from "./testFixtures";

const noop = () => undefined;

describe("B1 提示句：實戰逐字不變，測試模式「敵人」→「木樁」、「目標」不動", () => {
  const base = { copying: false, canAct: true, ended: false, moveCount: 45, attackCount: 3 };
  // 改前（PR-2b 之前）`actionHintText` 的原字
  const BEFORE: [Parameters<typeof actionHintText>[0], string][] = [
    [base, "點選藍色格子移動（45 格），點選紅框敵人攻擊（3 個）；右鍵或 Esc 取消選取。"],
    [{ ...base, ended: true }, "戰鬥結束。"],
    [{ ...base, copying: true }, "請為複製的技能或複合技能的第二段選擇目標（點高亮格子或左上角的方向鈕），或按 Esc 放棄。"],
    [{ ...base, canAct: false }, "等待中……"],
    [{ ...base, summonIdle: true }, "行動點數用完了，但還能調整召喚物的模式（0 AP）；準備好後按「結束回合」。"],
    [{ ...base, picked: "「普攻」（武器射程）：點選紅框目標（3 個）；右鍵或 Esc 取消選取。" }, "「普攻」（武器射程）：點選紅框目標（3 個）；右鍵或 Esc 取消選取。"],
  ];

  it.each(BEFORE)("實戰：%# 和改前逐字相同", (state, before) => {
    expect(actionHintText(state)).toBe(before);
    expect(practiceWording(actionHintText(state), false)).toBe(before);
  });

  it("測試模式：移動模式那句寫木樁（定稿原字）；寫「目標」的句子不動", () => {
    expect(practiceWording(actionHintText(base), true)).toBe("點選藍色格子移動（45 格），點選紅框木樁攻擊（3 個）；右鍵或 Esc 取消選取。");
    const target = "「普攻」（武器射程）：點選紅框目標（3 個）；右鍵或 Esc 取消選取。";
    expect(practiceWording(target, true)).toBe(target);
    expect(practiceWording("點一個敵人，隊友優先攻擊它。", true)).toBe("點一個木樁，隊友優先攻擊它。");
    expect(practiceWording("點一個敵人，隊友優先攻擊它。", false)).toBe("點一個敵人，隊友優先攻擊它。");
  });

  it("接線：技能列上方那行與選取面板的提示都經過 practiceWording（以 view.practice 分支）", () => {
    expect(readFile(SRC_DIR, "screens/battle/BattleBottomBar.tsx")).toContain("hint={practiceWording(actionHintText(hintState), practice)}");
    const panel = readFile(SRC_DIR, "ui/ActionPanel.tsx");
    expect(panel).toContain("practiceWording(modeHint(mode), props.view.practice)");
    expect(panel).toContain("practiceWording(hurlPromptText(");
    expect(panel).toContain("practiceWording(compositePromptFor(");
  });
});

describe("B2 costParts：測試模式不寫冷卻", () => {
  const b = { cooldown: 0, costs: ["AP 1", "耐力 6", "冷卻 2 回合"] };
  it("實戰照舊（有「冷卻 N 回合」、冷卻中只寫「冷卻 N」）", () => {
    expect(costParts(b)).toEqual(["AP 1", "耐力 6", "冷卻 2 回合"]);
    expect(costParts(b, false)).toEqual(["AP 1", "耐力 6", "冷卻 2 回合"]);
    expect(costParts({ ...b, cooldown: 2 })).toEqual(["冷卻 2"]);
    expect(costParts({ cooldown: 0, costs: [] })).toEqual(["…"]);
  });
  it("測試模式：拿掉冷卻，其他代價相同", () => {
    expect(costParts(b, true)).toEqual(["AP 1", "耐力 6"]);
    expect(costParts({ ...b, cooldown: 2 }, true)).toEqual(["AP 1", "耐力 6"]);
    expect(costParts({ cooldown: 0, costs: ["AP 2", "耐力 8"] }, true)).toEqual(["AP 2", "耐力 8"]);
    expect(costParts({ cooldown: 0, costs: ["冷卻 3 回合"] }, true)).toEqual(["…"]);
  });
});

describe("B3 回合操作：測試模式沒有「結束回合」，也不補別的按鈕", () => {
  const props = {
    enabled: true,
    endTurn: { type: "end_turn" } as never,
    attack: null,
    defend: null,
    run: null,
    runReason: null,
    moveCount: 3,
    moving: true,
    onMove: noop,
    onPreviewAction: noop,
    selectedKey: null,
    more: [],
    extra: [],
    onPickMode: noop,
    onAction: noop,
    speed: null,
  };
  const buttons = (html: string) => [...html.matchAll(/<button[^>]*>([^<]*)</g)].map((m) => m[1]);
  it("實戰有、測試模式沒有；其餘按鈕相同", () => {
    const live = renderToStaticMarkup(createElement(TurnControls, props));
    const test = renderToStaticMarkup(createElement(TurnControls, { ...props, practice: true }));
    expect(live).toContain("end-turn-button");
    expect(live).toContain("結束回合");
    expect(test).not.toContain("end-turn-button");
    expect(test).not.toContain("結束回合");
    expect(buttons(test)).toEqual(buttons(live).filter((t) => t !== "結束回合"));
    expect(renderToStaticMarkup(createElement(TurnControls, { ...props, practice: false }))).toBe(live);
  });
});

describe("B4 狀態盒與上方中央", () => {
  it("實戰：勝利條件圖示、沒有沙盒小牌；測試模式：沙盒小牌、輪數照舊", () => {
    const live = renderToStaticMarkup(createElement(BattleStatusBox, { view: smallView({ round: 3 }) }));
    const test = renderToStaticMarkup(createElement(BattleStatusBox, { view: smallView({ round: 3, practice: true, max_rounds: null }) }));
    expect(live).toContain('data-testid="battle-objective"');
    expect(live).not.toContain(PRACTICE_SANDBOX_TAG_ZH);
    expect(test).not.toContain('data-testid="battle-objective"');
    expect(test).toContain(PRACTICE_SANDBOX_TAG_ZH);
    expect(test).toContain("沙盒・不算勝負");
    expect(test).toMatch(/第 <b>3<\/b> 輪/);
  });
  it("提示條：「測試模式」徽章＋定稿句；BattleScreen 依 practice 二選一", () => {
    const bar = renderToStaticMarkup(createElement(PracticeBar));
    expect(bar).toContain("test-mode-badge");
    expect(bar).toContain(PRACTICE_BAR_ZH);
    expect(PRACTICE_BAR_ZH).toBe("每次出手後自動過一輪，資源立刻補滿，木樁不會倒");
    const screen = readFile(SRC_DIR, "screens/BattleScreen.tsx");
    expect(screen).toContain("{practice ? <PracticeBar /> : <TurnBar view={shown} names={data.names} acting={pb.acting} />}");
    expect(screen).toContain("const practice = shown.practice;");
  });
  it("預覽：測試模式三段各自不換行、多一行必中句；沒有命中率時不多那一行", () => {
    const { rows, sure } = practicePreviewRows(["命中 100%　暴擊 5%　傷害 3–10", "確定：木樁 不會倒"]);
    expect(rows[0]?.parts).toEqual(["命中 100%", "暴擊 5%", "傷害 3–10"]);
    expect(rows[1]?.parts).toBeNull();
    expect(sure).toBe(true);
    expect(practicePreviewRows(["治療 主角 3–5"]).sure).toBe(false);
    expect(PRACTICE_SURE_NOTE_ZH).toBe("靶場木樁必中，實戰會有失手");
    expect(readFile(SRC_DIR, "ui/ActionPanel.tsx")).toContain("<PreviewBox content={content} practice={view.practice} />");
  });
});

describe("B5 戰鬥紀錄：測試模式每輪多一行「第 {n} 輪結束：木樁補滿」", () => {
  const line = (seq: number, round: number, text = `行 ${seq}`): LogLine => ({ seq, round, text, type: "attack", unitIds: [], tiles: [] });
  const lines = [line(1, 1), line(2, 1), line(3, 2), line(4, 4)];
  it("實戰：原樣回傳同一個陣列", () => {
    expect(practiceRoundLines(lines, false)).toBe(lines);
  });
  it("測試模式：輪數 +1 時插在新一輪前面，歸在剛結束的那一輪", () => {
    const out = practiceRoundLines(lines, true);
    expect(out.map((l) => l.text)).toEqual(["行 1", "行 2", "第 1 輪結束：木樁補滿", "行 3", "第 2 輪結束：木樁補滿", "第 3 輪結束：木樁補滿", "行 4"]);
    expect(new Set(out.map((l) => l.seq)).size).toBe(out.length);
    const items = groupLog(out).map((i) => (i.kind === "group" ? i.head.text : i.text));
    expect(items).toEqual(["第 1 輪", "行 1", "行 2", "第 1 輪結束：木樁補滿", "第 2 輪", "行 3", "第 2 輪結束：木樁補滿", "第 3 輪", "第 3 輪結束：木樁補滿", "第 4 輪", "行 4"]);
    expect(practiceRoundText(7)).toBe("第 7 輪結束：木樁補滿");
  });
});

const WORKSHOP: WorkshopData = {
  title_zh: "樞島工坊・靶場與改造",
  capital_zh: "樞島",
  speaker: { name_zh: "工坊師傅", portrait: null, region: "capital" },
  line: { speaker_zh: "工坊師傅", text_zh: "木樁隨你打，打壞了我再釘。試試你現在的本事。" },
  practice_zh: "靶場試玩",
  practice_note_zh: "用你現在的技能與裝備打木樁，不耗任何資源",
  rework_zh: "改造技能",
  rework_note_zh: "之後開放",
  footer_zh: "靶場裡技能沒有冷卻，每次出手後自動過一輪，資源立刻補滿。",
  practice_available: true,
  practice_blocked_zh: null,
  practice_new: true,
  seen_id: "range:practice",
};

describe("B6 工坊師傅選單", () => {
  const html = (w: WorkshopData, seen = false) => renderToStaticMarkup(createElement(WorkshopPanel, { workshop: w, busy: false, seen, onPractice: noop }));
  it("「新」小牌：practice_new 且本機還沒點過才有", () => {
    expect(html(WORKSHOP)).toContain(`data-testid="workshop-new">${WORKSHOP_NEW_TAG}<`);
    expect(html(WORKSHOP, true)).not.toContain('data-testid="workshop-new"');
    expect(html({ ...WORKSHOP, practice_new: false })).not.toContain('data-testid="workshop-new"');
  });
  it("標頭、台詞、兩列、面板下說明都照伺服器給的字", () => {
    const h = html(WORKSHOP);
    expect(h).toContain("mail-head");
    expect(h).toContain("樞島工坊・靶場與改造");
    expect(h).toContain("<b>工坊師傅</b>：木樁隨你打，打壞了我再釘。試試你現在的本事。");
    expect(h).toContain("用你現在的技能與裝備打木樁，不耗任何資源");
    expect(h).toContain("靶場裡技能沒有冷卻，每次出手後自動過一輪，資源立刻補滿。");
  });
  it("第 1 列可以按時有「›」、沒有原因；停用時 aria-disabled 並帶原因（Hint）", () => {
    expect(practiceRow(WORKSHOP, false)).toEqual({ enabled: true, reason: null, isNew: true });
    const blocked = { ...WORKSHOP, practice_available: false, practice_blocked_zh: "先處理眼前的事，再來打木樁" };
    expect(practiceRow(blocked, false)).toEqual({ enabled: false, reason: "先處理眼前的事，再來打木樁", isNew: true });
    const h = html(blocked);
    expect(h).toMatch(/class="workshop-menu-item is-disabled" aria-disabled="true"[^>]*data-testid="workshop-practice"/);
    expect(h.match(/workshop-menu-go/g)).toBeNull();
    expect(html(WORKSHOP).match(/workshop-menu-go/g)?.length).toBe(1);
    expect(readFile(SRC_DIR, "world/WorkshopPanel.tsx")).toContain("<Hint text={row.reason}>{practice}</Hint>");
  });
  it("第 2 列永遠停用、只寫一次「之後開放」", () => {
    for (const w of [WORKSHOP, { ...WORKSHOP, practice_available: false, practice_blocked_zh: "x" }]) {
      const h = html(w);
      expect(h).toMatch(/<button type="button" class="workshop-menu-item" disabled="" data-testid="workshop-rework">/);
      expect(h.match(/之後開放/g)?.length).toBe(1);
    }
  });
  it("面板接線：objectHud 的 workshop 開面板；沒有 WorldView.workshop 就開不了", () => {
    expect(objectHud({ panel: "workshop" })).toEqual({ panel: "workshop", who: null });
    expect(panelAvailable({ workshop: WORKSHOP } as unknown as WorldView, "workshop")).toBe(true);
    expect(panelAvailable({ workshop: null } as unknown as WorldView, "workshop")).toBe(false);
    const screen = readFile(SRC_DIR, "screens/WorldScreen.tsx");
    expect(screen).toContain("api.worldRangePractice(charId)");
    expect(screen).toContain("hintSeenAction([w.seen_id])");
    expect(screen).toContain("api.worldRangeTrialClose(charId)");
  });
});

describe("B7 地名、離開鈕、開場訊息", () => {
  it("rangePlaceName 吃 WorkshopView.capital_zh（靶場試玩）或 RangeView.capital_zh（開局試打）", () => {
    expect(rangeFightPlace("practice", { workshop: WORKSHOP, opening: null })).toBe("樞島・工坊靶場");
    expect(rangeFightPlace("trial", { opening: { capital_zh: "樞島" }, workshop: null })).toBe("樞島・工坊靶場");
    expect(rangeFightPlace("practice", null)).toBe(rangePlaceName(null));
  });
  it("離開鈕：師傅入口「離開靶場」、開局試打維持「回到靶場」", () => {
    expect(rangeExitLabel("practice")).toBe(PRACTICE_EXIT_LABEL);
    expect(PRACTICE_EXIT_LABEL).toBe("離開靶場");
    expect(rangeExitLabel("trial")).toBe(TRIAL_EXIT_LABEL);
    expect(TRIAL_EXIT_LABEL).toBe("回到靶場");
  });
  it("開場訊息：開局試打「靶場試打：{武器}＋{招 1}、{招 2}」，靶場試玩只寫標題；後面接沙盒說明", () => {
    expect(rangeFightNotes("trial", { title_zh: "靶場試打：弓", skills_zh: ["淬毒箭", "燧石飛刃"] })).toEqual(["靶場試打：弓＋淬毒箭、燧石飛刃", SANDBOX_NOTE]);
    expect(rangeFightNotes("trial", { title_zh: "看示範：弓", skills_zh: ["點燃箭"] })).toEqual(["看示範：弓＋點燃箭", SANDBOX_NOTE]);
    expect(rangeFightNotes("practice", { title_zh: "靶場試玩：弓", skills_zh: ["a", "b", "c"] })).toEqual(["靶場試玩：弓", SANDBOX_NOTE]);
  });
});
