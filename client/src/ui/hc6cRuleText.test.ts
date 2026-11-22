// HC-6c：前端剩下的說明文字改從資料組字。目前的值組出來要和改前逐字相同；換了值字跟著變；元件真的改用這些函式。
import { describe, expect, it } from "vitest";
import { gameRules } from "../battle/glossary";
import { INFUSE_HINT, modeHints } from "../battle/summonControl";
import { battleAlliesText } from "../screens/StartScreen";
import { pouchUseText } from "../world/bagView";
import { citeHint, clueHint } from "../world/EventCard";
import { hireHintText } from "../world/PartyPanel";
import { reselectBadgeHint } from "../world/range";
import { sourceRuleText } from "./statusCard";
import { summonTipText } from "./SummonPanel";

// 沒有 @types/node：同 statusCard.test.ts，用變數名載入 node:fs。
const nodeFs = "node:fs";
const { readFileSync } = (await import(/* @vite-ignore */ nodeFs)) as { readFileSync: (p: string, enc: string) => string };

const OLD_TIP = `集火：打你指定的敵人；目標倒下或離場後退回「跟隨」。
守護我：待在你 2 格內，優先打威脅你的敵人。
跟隨：靠近你行動，但會主動攻擊附近的敵人。
待命：原地不動，只打相鄰的敵人。
切換模式不花 AP、可以隨時換；指揮要花 1 AP，讓這隻召喚物立刻走到你指定的格子（用牠自己的移動力）並攻擊，不佔牠自己的回合；每隻每輪最多指揮 1 次。
灌注要花 1 AP：${INFUSE_HINT}`;

describe("HC-6c：目前的值組出來和改前逐字相同", () => {
  it("伺服器規則的現值（名詞表夾具）", () => {
    const r = gameRules();
    expect([r.summon_guard_radius, r.source_min_at_start, r.battle_team_size, r.item_skill_ap_cost, r.situation_care_max, r.start_keywords]).toEqual([2, 1, 3, 1, 2, 2]);
  });
  it("召喚物：守護 2 格、指揮與灌注 1 AP", () => {
    expect(modeHints().guard).toBe("待在你 2 格內，優先打威脅你的敵人。");
    expect(summonTipText({ summon_command_ap_cost: 1, summon_infuse_ap_cost: 1 })).toBe(OLD_TIP);
  });
  it("單場戰鬥補到 3 人、源力每場至少 1 點、腰包 1 AP", () => {
    expect(battleAlliesText()).toBe("隊友由 AI 控制（標準隊友補到 3 人）；你操控主角。");
    expect(sourceRuleText()).toBe("傳說技能的代價（跨戰鬥保留，每場至少 1 點；走上地圖上的「源」格 +1）");
    expect(pouchUseText()).toBe("戰鬥中 1 AP 使用");
  });
  it("線索最多 +2、重選 2 個關鍵字、雇用 0～2 名", () => {
    expect(clueHint(3)).toBe("線索：你持有的線索與往來 3 筆（點開來引用；回答裡要提到它，遊戲核對得到才 +1，最多 +2）");
    expect(citeHint({ item_zh: "線頭", text_zh: "灰燼的線索" })).toBe("線頭：引用時會把「灰燼的線索」寫進回答；回答裡要提到它，遊戲核對得到才 +1（最多 +2）");
    expect(reselectBadgeHint({ place_zh: "回霧渡鎮找葛蘭" } as never)).toBe("回霧渡鎮找葛蘭。可以換武器與 2 個關鍵字，但只有這一次。");
    expect(hireHintText(2)).toBe("免費帶 0～2 名隊友：系統傭兵或朋友的影子（出城前選好，野外不能換；不帶＝獨行）");
  });
});

describe("HC-6c：換了值字跟著變", () => {
  it("每個欄位", () => {
    expect(modeHints(3).guard).toContain("待在你 3 格內");
    expect(summonTipText({ summon_command_ap_cost: 2, summon_infuse_ap_cost: 3 }, 4)).toMatch(/待在你 4 格內[\s\S]*指揮要花 2 AP[\s\S]*灌注要花 3 AP/u);
    expect(battleAlliesText(4)).toContain("補到 4 人");
    expect(sourceRuleText(2)).toContain("每場至少 2 點");
    expect(pouchUseText(2)).toBe("戰鬥中 2 AP 使用");
    expect(clueHint(1, 1)).toContain("最多 +1）");
    expect(citeHint({ item_zh: "a", text_zh: "b" }, 3)).toContain("（最多 +3）");
    expect(reselectBadgeHint({ place_zh: "" } as never, 3)).toBe("可以換武器與 3 個關鍵字，但只有這一次。");
    expect(hireHintText(3)).toContain("0～3 名隊友");
  });
});

describe("HC-6c：元件改用這些函式", () => {
  const src = (p: string): string => readFileSync(p, "utf8");
  it("呼叫處", () => {
    expect(src("src/ui/SummonPanel.tsx")).toContain("practiceWording(summonTipText(view), view.practice)");
    expect(src("src/screens/StartScreen.tsx")).toContain("{battleAlliesText()}");
    expect(src("src/ui/statusCard.ts")).toContain("sourceRuleText()");
    expect(src("src/world/BagScreen.tsx")).toContain("{pouchUseText()}");
    expect(src("src/world/EconomyPanel.tsx")).toContain("{pouchUseText()}");
    expect(src("src/world/WorldPanel.tsx")).toContain("hireHintText(view.party.max_hired)");
    for (const p of ["src/battle/summonControl.ts", "src/ui/SummonPanel.tsx", "src/screens/StartScreen.tsx", "src/world/BagScreen.tsx", "src/world/EconomyPanel.tsx", "src/world/WorldPanel.tsx", "src/world/range.ts"]) {
      expect(src(p), p).not.toMatch(/待在你 2 格內|要花 1 AP|補到 3 人|戰鬥中 1 AP|0～2 名隊友|可以換武器與 2 個關鍵字/u);
    }
  });
});
