// PNL-4 順手項（開發 PM 追加：QI-7、PNL-3 美術驗收可修；需求 3.1、3.3 更正）：
// 1. 任務日誌已完成的任務收進「已完成（N）」摺疊（預設摺起、卡片淡化、不掛「已完成」標籤、0 個不畫）；
// 2. 公告板與成長的 L2／L3 說明段落套 KeepNum；3. 任務類別標籤細框中性；4. dev/itemLegacy.tsx 已刪。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import type { WorldQuestLog, WorldView } from "../api/types";
import { clearPanelIconCache } from "../render/panelIcon";
import { setQCanvasFactory } from "../render/qIcon/core";
import { reflashNoteText } from "../run/CampfireSkillCare";
import { fakeCanvasFactory, type FakeCanvasLog } from "../test/fakeCanvas";
import { readFile, readSources, SRC_DIR, stripTsComments } from "../test/sourceScan";
import { glueNumbers } from "../ui/PanelKit";
import { trackedQuests, trackHint } from "./hud";
import { QuestCard, QuestsPane, questTabs } from "./QuestLog";
import { QUEST_DONE_FOLD, questDoneFoldText } from "./questPanel";

const log: FakeCanvasLog = { calls: [] } as unknown as FakeCanvasLog;
beforeAll(() => setQCanvasFactory(fakeCanvasFactory(log)));
afterAll(() => {
  setQCanvasFactory(null);
  clearPanelIconCache();
});

const quest = (id: string, done: boolean, kind = "支線"): WorldQuestLog => ({
  id,
  name_zh: `任務${id}`,
  kind_zh: kind,
  summary_zh: "",
  giver_zh: null,
  giver_portrait: null,
  giver_region: null,
  steps: [{ text_zh: "做事", done, current: !done, place_zh: null, task_zh: "做事" }],
  done,
  route_zh: null,
  advice_zh: null,
});
const html = (quests: WorldQuestLog[]) => renderToStaticMarkup(createElement(QuestsPane, { quests }));

describe("已完成的任務收進摺疊（PNL-3 美術驗收可修 2）", () => {
  it("進行中在前；已完成在最後的「已完成（N）」摺疊裡，預設摺起來", () => {
    const out = html([quest("b", true), quest("a", false), quest("c", true)]);
    expect(questDoneFoldText(2)).toBe("已完成（2）");
    const fold = out.indexOf('data-testid="world-quest-done"');
    expect(fold).toBeGreaterThan(out.indexOf('data-quest="a"'));
    expect(out.indexOf('data-quest="b"')).toBeGreaterThan(fold);
    expect(out.indexOf('data-quest="c"')).toBeGreaterThan(fold);
    expect(out).toMatch(/<details class="pnl-fold" name="quest-done"[^>]*data-fold="done"/);
    expect(out).not.toMatch(/<details[^>]*\sopen=""[^>]*data-fold="done"/);
    expect(out).toContain("已完成（2）");
  });
  it("卡片淡化保留、卡上不掛「已完成」標籤", () => {
    const out = renderToStaticMarkup(createElement(QuestCard, { quest: quest("b", true) }));
    expect(out).toContain('class="pnl-quest done"');
    expect(out).not.toContain("已完成");
  });
  it("沒有已完成的任務：不畫摺疊，量高度也不多一種樣子", () => {
    expect(html([quest("a", false)])).not.toContain("world-quest-done");
    const v = (qs: WorldQuestLog[]) => ({ quests: qs, threads: [] }) as unknown as WorldView;
    expect(questTabs(v([quest("a", false)]))[0]!.folds).toBeUndefined();
    expect(questTabs(v([quest("a", false), quest("b", true)]))[0]!.folds).toEqual([QUEST_DONE_FOLD]);
  });
  it("只有已完成的任務：只有摺疊，沒有空狀態", () => {
    const out = html([quest("b", true)]);
    expect(out).toContain("已完成（1）");
    expect(out).not.toContain("world-quest-empty");
  });
});

describe("任務類別標籤：細框中性（PNL-3 美術驗收可修 1）", () => {
  it("「新手」「主線」「支線」都是不帶色調的 pnl-tag", () => {
    for (const kind of ["新手", "主線", "支線"]) {
      const out = renderToStaticMarkup(createElement(QuestCard, { quest: quest("a", false, kind) }));
      expect(out).toContain(`<span class="pnl-tag">${kind}</span>`);
    }
  });
});

describe("公告板與成長的說明段落套 KeepNum（需求 3.1 更正）", () => {
  it("公告板：階段說明、下一個的天數、頭目說明、首殺、挑戰原因、挑戰規則", () => {
    const src = stripTsComments(readFile(SRC_DIR, "world/BoardPanes.tsx"));
    for (const t of [
      "<KeepNum text={daysAwayText(next.day, s.day)} />",
      "<KeepNum text={s.phase.text_zh} />",
      "<KeepNum text={boss.note_zh} />",
      "<KeepNum text={boss.first_kill_zh} />",
      "<KeepNum text={boss.problem_zh} />",
      "<KeepNum text={`${bossAttemptsLabel(boss)}；只准系統傭兵，失敗只扣次數。`} />",
      "<KeepNum text={e.text_zh} />",
    ])
      expect(src).toContain(t);
    expect(src).not.toMatch(/className="pnl-l[23]"[^>]*>\{(?!\/)[^}<]*_zh\}/);
  });
  it("成長：警告、鎖住、入門配點、已閃次數、空狀態、種族次行、重閃說明", () => {
    const src = stripTsComments(readFile(SRC_DIR, "world/WorldGrowth.tsx"));
    for (const t of ["<KeepNum text={warn} />", "<KeepNum text={FLASH_LOCK_ZH.tail} />", "<KeepNum text={starter} />", "<KeepNum text={flashCountText(flash, hero.flash_rules)} />", "<KeepNum text={ATTR_EMPTY_ZH} />"])
      expect(src).toContain(t);
    expect(stripTsComments(readFile(SRC_DIR, "world/GrowthLookRows.tsx"))).toContain("<KeepNum text={RACE_NOTE_ZH} />");
    expect(stripTsComments(readFile(SRC_DIR, "run/CampfireSkillCare.tsx"))).toContain("<KeepNum text={reflashNoteText(hero.flash_rules)} />");
  });
  it("重閃說明字不變；「點出 4 個」黏在一起", () => {
    const text = reflashNoteText(undefined as never);
    expect(text).toMatch(/^把一招以前某一次的變化換掉，價格和閃現相同（\d+ 點出 \d+ 個；指定類別 \d+ 點出 \d+ 個）。不需要先上場用過，也不增加閃現次數；新選項整招不會比現在弱；標 ▼ 的是換掉後變小的地方。$/);
    expect(glueNumbers(text).filter((p) => p.glue).length).toBeGreaterThanOrEqual(2);
  });
});

describe("物品圖示舊畫法（QI-7 留給開發頁對照）已刪", () => {
  it("dev/itemLegacy.tsx 不在了，開發頁也不再引用", () => {
    const files = readSources().map(([p]) => p);
    expect(files).toContain("dev/itemGallery.tsx");
    expect(files).not.toContain("dev/itemLegacy.tsx");
    expect(stripTsComments(readFile(SRC_DIR, "dev/itemGallery.tsx"))).not.toMatch(/itemLegacy|LegacyTile|LegacyGainIcon|現行｜/);
  });
});

describe("HUD 追蹤列的線頭到期改「剩 …」（玩法 PM 11-13 確認，需求 3.3）", () => {
  it("用伺服器的 left_zh；說明卡 trackHint 同一行；舊伺服器沒有 left_zh 時用原字", () => {
    const v = (threads: unknown[]) => ({ quests: [], threads, guide: null }) as unknown as WorldView;
    const t = { id: "t1", text_zh: "商人欠你人情", scope: "personal", scope_zh: "個人", expires_zh: "2 天 23 小時後到期", left_zh: "剩 2 天 23 小時", npc_zh: null, location_zh: null };
    const [line] = trackedQuests(v([t]));
    expect(line).toMatchObject({ kind: "thread", name: "商人欠你人情", line: "剩 2 天 23 小時" });
    expect(trackHint(line!)).toBe("線頭：商人欠你人情・剩 2 天 23 小時（點了打開任務面板）");
    expect(trackedQuests(v([{ ...t, left_zh: null }]))[0]!.line).toBe("2 天 23 小時後到期");
  });
});
