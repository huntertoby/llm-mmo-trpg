// HC-6b：說明文字裡的規則數字改從伺服器資料組字。用目前的值（vitest 載入的 `/api/glossary` 快照）組出來的字，
// 要和改前寫死的字串逐字相同；另外驗換了值以後字跟著變、元件真的改用這些函式。
import { describe, expect, it } from "vitest";
import { gameRules } from "../battle/glossary";
import {
  completeIntro,
  inheritRuleText,
  inheritStepText,
  majorNoteText,
  openMixText,
  transformHint,
  transformHintTip,
} from "../run/flash";
import {
  campfireRestText,
  runCompanionsLine,
  runCompanionsText,
  runNewSubText,
  runStartBlurb,
  runTotalText,
} from "../run/runRulesText";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { budgetExceptionTitle, draftNameRuleText, movesExceptionTitle } from "../tuning/DraftPanel";
import { smallSampleNote } from "../tuning/model";
import { ratioWorkNote } from "../tuning/ratioModel";
import { openingLevelTag } from "../world/growthPanel";
import { flashLessonText } from "../world/OpeningDialog";
import { pregenDefaultNote } from "../world/pregen";
import { noThreadText, threadRuleText } from "../world/questPanel";
import { WISH_ZH } from "../world/wish";
import { leagueHintText } from "../world/WorldPanel";
import { opHintResetText } from "./LayoutPanel";
import { aboutDurationText, budgetWindowText } from "./rulesText";
import { AP_PIP_TEXT } from "./statusCard";
import { spreadNote } from "./StatusCardParts";
import { tryoutAddText, tryoutNeedsText } from "./workshop/TryoutPanel";

describe("HC-6b 一輪 roguelite（RunNewScreen、RunScreen、StartScreen、RunCampfire）", () => {
  it("目前的值組出來和改前逐字相同", () => {
    expect(runNewSubText()).toBe("roguelite：5 場戰鬥加頭目，一路帶著同一個主角");
    expect(runTotalText()).toBe("共 5 場戰鬥加頭目；");
    expect(runCompanionsText()).toBe("隊友為 2 名標準隊友。");
    expect(runCompanionsLine()).toBe("隊友：標準隊友 2 名（滿狀態）；");
    expect(runStartBlurb()).toBe("5 場戰鬥加頭目：打贏升級、營火回滿，一路帶著同一個主角。");
    expect(campfireRestText()).toBe("HP、法力與耐力已回滿，源力 +1。");
  });
  it("值換了字跟著變", () => {
    expect(runCompanionsText(3)).toBe("隊友為 3 名標準隊友。");
    expect(campfireRestText(2)).toBe("HP、法力與耐力已回滿，源力 +2。");
  });
  it("畫面改用這些函式", () => {
    expect(readFile(SRC_DIR, "screens/RunNewScreen.tsx")).toContain("sub={runNewSubText()}");
    expect(readFile(SRC_DIR, "screens/RunNewScreen.tsx")).toContain("{runCompanionsText()}");
    expect(readFile(SRC_DIR, "screens/RunScreen.tsx")).toContain("{runCompanionsLine()}");
    expect(readFile(SRC_DIR, "screens/StartScreen.tsx")).toContain("{runStartBlurb()}");
    expect(readFile(SRC_DIR, "screens/RunCampfire.tsx")).toContain("{campfireRestText()}");
  });
});

describe("HC-6b 閃現（flash.ts、FlashChooser、CampfireSkillCare、SkillFlashInfo）", () => {
  it("目前的值組出來和改前逐字相同", () => {
    expect(transformHint()).toBe("可以重閃第 3 格轉型");
    expect(transformHintTip()).toBe("角色升階後，新的轉型選擇變多了；在營火重閃第 3 次的變化，可能出現轉型。");
    expect(inheritRuleText(gameRules().flash_max_carry)).toBe(
      "傳承：把另一招的小變化（最多 2 個）帶給這招，算已閃次數；舊技能會消失，花掉的靈感點不退。完整技能不能接受傳承。",
    );
    expect(inheritStepText(2)).toBe("1. 帶走哪些小變化（最多 2 個，依序成為新技能的第 1、2 次）");
    expect(openMixText()).toBe("混合各類變化，至少涵蓋 2 類");
    expect(majorNoteText()).toBe("第 3 次是大變化；指定類別時，轉型保底會另外列在最後並標「轉型」。");
    expect(completeIntro()[0]).toBe("完整技能是整招設計好的技能，強度視為已經閃現 3 次（預算 +12%）。");
  });
  it("值換了字跟著變", () => {
    expect(transformHint(4)).toBe("可以重閃第 4 格轉型");
    expect(inheritStepText(3)).toBe("1. 帶走哪些小變化（最多 3 個，依序成為新技能的第 1、2、3 次）");
    expect(completeIntro(120, 4)[0]).toContain("強度視為已經閃現 4 次");
  });
  it("元件改用這些函式", () => {
    expect(readFile(SRC_DIR, "run/FlashChooser.tsx")).toContain("{openMixText()}");
    expect(readFile(SRC_DIR, "run/FlashChooser.tsx")).toContain("{majorNoteText()}");
    expect(readFile(SRC_DIR, "run/CampfireSkillCare.tsx")).toContain("{inheritRuleText(limit)}");
    expect(readFile(SRC_DIR, "run/CampfireSkillCare.tsx")).toContain("{inheritStepText(limit)}");
    expect(readFile(SRC_DIR, "ui/SkillFlashInfo.tsx")).toContain("<Hint text={transformHintTip()}>");
  });
});

describe("HC-6b 數值工坊（DraftPanel、SimPanel、RatioView）與技能工坊（TryoutPanel）", () => {
  it("目前的值組出來和改前逐字相同", () => {
    expect(draftNameRuleText(40)).toBe("名稱只能用英文小寫、數字、底線、減號（最多 40 字）");
    expect(budgetExceptionTitle()).toBe("預算例外（超出合格區間 70～100%；寫回時自動登記進例外清單）");
    expect(movesExceptionTitle()).toBe("#149 例外（招數低於下限：一般 2 招、精英 3 招、頭目每階段 3 招；commit 內文會記「#149 例外」）");
    expect(smallSampleNote(30)).toBe("括號是分子／分母（場數或回合數）；分母小於 30 標「樣本小」，數字容易跳，想確定請改用「中」或加種子數再跑。");
    expect(ratioWorkNote(40000)).toBe("組＝招 × 可用武器 × 情境（無條件 1 個；有條件「成立／不成立」2 個；每個變奏多 1 個）。一次最多 40,000 組×種子。");
    expect(tryoutAddText()).toBe("不換（加在空格；主動技最多 6 個，滿了會被拒絕）");
    expect(tryoutNeedsText()).toBe("技能要先組完整、而且檢查合法（預算 70–100%、沒有違反規則）才能裝上試玩。");
  });
  it("值換了字跟著變", () => {
    const window = { budget_min_ratio_permille: 650, budget_max_ratio_permille: 1000 };
    expect(budgetWindowText("～", window)).toBe("65～100%");
    expect(budgetWindowText("–", { budget_min_ratio_permille: 725, budget_max_ratio_permille: 950 })).toBe("72.5–95%");
    expect(movesExceptionTitle({ min_moves_mob: 1, min_moves_elite: 2, min_moves_boss_phase: 4 })).toContain("一般 1 招、精英 2 招、頭目每階段 4 招");
    expect(tryoutAddText(5)).toBe("不換（加在空格；主動技最多 5 個，滿了會被拒絕）");
  });
  it("元件改用這些函式", () => {
    expect(readFile(SRC_DIR, "tuning/DraftPanel.tsx")).toContain("{draftNameRuleText(status.draft_name_max)}");
    expect(readFile(SRC_DIR, "tuning/SimPanel.tsx")).toContain("{smallSampleNote(smallSample)}");
    expect(readFile(SRC_DIR, "tuning/SimPanel.tsx")).toContain("maxWork={options.ratio_max_work}");
    expect(readFile(SRC_DIR, "tuning/RatioView.tsx")).toContain("{ratioWorkNote(maxWork)}");
  });
});

describe("HC-6b 戰鬥與介面（LayoutPanel、StatusCardParts、statusCard）", () => {
  it("目前的值組出來和改前逐字相同", () => {
    expect(opHintResetText()).toBe("已重設，之後選取時會再顯示 3 次");
    expect(spreadNote()).toBe("會擴散：帶著這個狀態倒下時，以剩下的回合傳給身邊 1 格內的一名同伴；身上有好幾種時只傳一種，傳過去的仍會擴散。");
    expect(AP_PIP_TEXT.overdraftNext(1)).toBe("透支：下回合少 1 AP");
    expect(AP_PIP_TEXT.borrowNext(1)).toBe("預支：下回合少 1 AP");
  });
  it("值換了字跟著變", () => {
    expect(spreadNote(2)).toContain("身邊 2 格內");
    expect(opHintResetText(5)).toBe("已重設，之後選取時會再顯示 5 次");
  });
});

describe("HC-6b 大世界（questPanel、growthPanel、pregen、wish 等待、OpeningDialog、WorldPanel）", () => {
  it("目前的值組出來和改前逐字相同", () => {
    expect(threadRuleText()).toBe("事件的結果會留下線頭（每人約 5 條，約 3 天到期）。");
    expect(noThreadText()).toBe("還沒有線頭。事件的結果會留下線頭（每人約 5 條，約 3 天到期）。");
    expect(openingLevelTag()).toBe("4 級起");
    expect(pregenDefaultNote()).toBe("最多等 10 秒；來不及就改用一般的版本。");
    expect(WISH_ZH.timeout()).toBe("池子這次沒來得及回應（等了 10 秒），改從選單挑關鍵字吧（沒有扣任務幣）。");
    expect(WISH_ZH.waitNote()).toBe("最多等 10 秒；來不及就改從選單挑關鍵字（不扣任務幣）。");
    expect(WISH_ZH.tagTimeout()).toBe("池子這次沒來得及回應（等了 10 秒），改從清單點選標籤吧（沒有扣任務幣）。");
    expect(flashLessonText()).toBe("在成長面板（G）選一招、花 1 點靈感，看 4 個變化選 1 個。略過也沒關係，之後在城鎮或營火隨時能閃。");
    expect(leagueHintText()).toBe("影子循環賽：報名（每個帳號 1 個角色、第 13 天截止）、勝場排行榜、看每一場的重播");
  });
  it("值換了字跟著變（線頭到期：整天寫天、不整天寫小時）", () => {
    expect(threadRuleText(4, 2 * 86400)).toBe("事件的結果會留下線頭（每人約 4 條，約 2 天到期）。");
    expect(aboutDurationText(90000)).toBe("約 25 小時");
    expect(openingLevelTag(5)).toBe("5 級起");
    expect(pregenDefaultNote(8)).toBe("最多等 8 秒；來不及就改用一般的版本。");
  });
  it("元件改用這些函式", () => {
    expect(readFile(SRC_DIR, "world/QuestLog.tsx")).toContain("<InfoTip text={threadRuleText()} />");
    expect(readFile(SRC_DIR, "world/WorldGrowth.tsx")).toContain("<LockTag text={openingLevelTag()} ");
    expect(readFile(SRC_DIR, "world/OpeningDialog.tsx")).toContain("? flashLessonText()");
    expect(readFile(SRC_DIR, "world/WorldPanel.tsx")).toContain("<Hint text={leagueHintText()}>");
  });
});
