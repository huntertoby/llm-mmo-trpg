// PNL-3：任務與線頭面板（docs/art/資訊面板-移植需求.md 3.3「任務與線頭」、4.1 #24～#28、#40、#42）＋
// 共用小修：說明字裡數字不和前面名詞分開（PNL-1b 美術驗收可修 1，`PanelKit` 的 `KeepNum`）＋
// 重閃清單空的時候改成虛線空狀態（PNL-2 美術驗收可修 1）。vitest 沒有 DOM：分頁列、量高度由瀏覽器實測（報告第 4 節）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import type { WorldQuestLog, WorldThread, WorldView } from "../api/types";
import { clearPanelIconCache } from "../render/panelIcon";
import { setQCanvasFactory } from "../render/qIcon/core";
import { reflashEmptyText } from "../run/CampfireSkillCare";
import { fakeCanvasFactory, type FakeCanvasLog } from "../test/fakeCanvas";
import { readFile, readStyleFiles, SRC_DIR, stripCssComments, stripTsComments } from "../test/sourceScan";
import { glueNumbers, KeepNum, wordBeforeNumber } from "../ui/PanelKit";
import { pickTab } from "../ui/panelTabRules";
import { QuestCard, QuestLog, questTabs, StepTimeline, ThreadsPane } from "./QuestLog";
import { NO_QUEST_ZH, NO_THREAD_ZH, questsBadge, stepParts, stepState, THREAD_RULE_ZH, threadLeftText, threadsBadge } from "./questPanel";

const html = (el: Parameters<typeof renderToStaticMarkup>[0]) => renderToStaticMarkup(el);
const css = readStyleFiles()
  .map(([, t]) => stripCssComments(t))
  .join("\n");

const log: FakeCanvasLog = { calls: [] } as unknown as FakeCanvasLog;
beforeAll(() => setQCanvasFactory(fakeCanvasFactory(log)));
afterAll(() => {
  setQCanvasFactory(null);
  clearPanelIconCache();
});

type Step = WorldQuestLog["steps"][number];
const step = (text: string, done: boolean, current: boolean, place: string | null, task: string | null): Step => ({ text_zh: text, done, current, place_zh: place, task_zh: task });

const ferry = (over: Partial<WorldQuestLog> = {}): WorldQuestLog => ({
  id: "starter_ferry",
  name_zh: "霧渡新手路",
  kind_zh: "新手",
  summary_zh: "渡婆婆要你先把渡口到梯田這一路走通。",
  giver_zh: "渡婆婆",
  giver_portrait: null,
  giver_region: "cloud_ridge",
  steps: [
    step("渡口石階：趕走搶渡船的盜賊", true, false, "渡口石階", "趕走搶渡船的盜賊"),
    step("竹林小徑：突破雨裡包圍的霧狼", false, true, "竹林小徑", "突破雨裡包圍的霧狼"),
    step("在餘燼集打聽斷崖幫的運輸隊", false, false, null, "在餘燼集打聽斷崖幫的運輸隊"),
  ],
  done: false,
  route_zh: "往北邊的出口 → 竹林小徑",
  advice_zh: null,
  ...over,
});

const thread = (id: string, text: string, over: Partial<WorldThread> = {}): WorldThread => ({
  id,
  text_zh: text,
  scope: "personal",
  scope_zh: "個人",
  expires_zh: "2 天 23 小時後到期",
  left_zh: "剩 2 天 23 小時",
  npc_zh: null,
  location_zh: null,
  ...over,
});

const view = (quests: WorldQuestLog[], threads: WorldThread[]): WorldView => ({ quests, threads }) as unknown as WorldView;

describe("分頁與記號（#27、#40、#42）", () => {
  it("任務日誌｜線頭，短名「任務」「線頭」；細框條數，0 條不掛", () => {
    const tabs = questTabs(view([ferry(), ferry({ id: "b", done: true })], [thread("a", "商人欠你人情"), thread("b", "狼群是被趕下山的")]));
    expect(tabs.map((t) => [t.id, t.label, t.short])).toEqual([
      ["quests", "任務日誌", "任務"],
      ["threads", "線頭", "線頭"],
    ]);
    expect(tabs[0]!.badge).toEqual({ kind: "p", value: 1, hint: "進行中 1" });
    expect(tabs[1]!.badge).toEqual({ kind: "p", value: 2, hint: "線頭 2 條" });
    expect(questsBadge(view([], []))).toBeNull();
    expect(threadsBadge(view([], []))).toBeNull();
    expect(pickTab(tabs)).toBe("quests");
  });

  it("面板：標題「任務與線頭」＋回到地點圖、分頁列；頁內不再寫「進行中 N」", () => {
    const out = html(createElement(QuestLog, { view: view([ferry()], [thread("a", "商人欠你人情")]), onClose: () => undefined }));
    expect(out).toContain("任務與線頭");
    expect(out).toContain('data-testid="pnl-back"');
    expect(out).toContain('data-testid="world-quest-tabs-tabs"');
    expect(out).not.toContain("進行中 1</");
    expect(out).toContain('data-testid="world-quest-log"');
  });
});

describe("任務卡（#24、#25）", () => {
  it("名字＋實心類別標籤＋委託人小頭像與名字；摘要；藍色路線膠囊（地圖圖示）", () => {
    const out = html(createElement(QuestCard, { quest: ferry() }));
    expect(out).toContain('<span class="name">霧渡新手路</span>');
    expect(out).toContain('<span class="pnl-tag open">新手</span>');
    expect(out).toMatch(/data-testid="world-quest-giver"><span class="story-portrait"[^>]*><\/span>渡婆婆<\/span>/);
    expect(out).toContain("渡婆婆要你先把渡口到梯田這一路走通。");
    expect(out).toMatch(/<span class="pnl-route" data-testid="world-quest-route"><canvas[^>]*data-icon="bar_M"[^>]*><\/canvas>往北邊的出口 → 竹林小徑<\/span>/);
  });

  it("建議照現行色在路線膠囊上面一行；完成的任務掛「已完成」", () => {
    const out = html(createElement(QuestCard, { quest: ferry({ advice_zh: "建議先完成霧渡新手路" }) }));
    expect(out.indexOf("world-quest-advice")).toBeLessThan(out.indexOf("pnl-route"));
    const done = html(createElement(QuestCard, { quest: ferry({ done: true, route_zh: null }) }));
    expect(done).toContain('class="pnl-quest done"');
    expect(done).toContain('<span class="pnl-tag mine">已完成</span>');
  });

  it("沒有任務：虛線空狀態（字不變）", () => {
    const tabs = questTabs(view([], []));
    expect(html(createElement("div", null, tabs[0]!.render()))).toContain(`<div class="pnl-empty" data-testid="world-quest-empty">${NO_QUEST_ZH}</div>`);
  });
});

describe("步驟時間軸 StepTimeline（#24）", () => {
  it("綠勾＝完成、金圈＝目前、空圈數字＝未到；左欄地點、右欄要做的事；沒有「：」整句放右欄", () => {
    const out = html(createElement(StepTimeline, { steps: ferry().steps }));
    expect(out).toContain('<li class="done" data-step="done" data-testid="world-quest-step"><span class="dot" aria-label="完成">✓</span><span class="place">渡口石階</span><span class="what">趕走搶渡船的盜賊</span></li>');
    expect(out).toContain('<li class="current" data-step="current" data-testid="world-quest-step"><span class="dot" aria-label="目前"></span><span class="place">竹林小徑</span>');
    expect(out).toContain('<span class="dot" aria-label="第 3 步">3</span><span class="place"></span><span class="what">在餘燼集打聽斷崖幫的運輸隊</span>');
  });

  it("stepParts：後端分欄；舊資料沒有 task_zh 時整句放右欄", () => {
    expect(stepParts(step("渡口石階：趕走", false, false, "渡口石階", "趕走"))).toEqual({ place: "渡口石階", task: "趕走" });
    expect(stepParts({ text_zh: "渡口石階：趕走", done: false, current: false })).toEqual({ place: null, task: "渡口石階：趕走" });
    expect(stepState(step("x", true, false, null, "x"))).toBe("done");
    expect(stepState(step("x", false, true, null, "x"))).toBe("current");
    expect(stepState(step("x", false, false, null, "x"))).toBe("todo");
  });

  it("CSS：圈之間直線、完成段綠線、目前金圈＋亮金粗體；欄寬寫在 class", () => {
    expect(css).toMatch(/\.pnl-steps li::before\s*\{[^}]*width: 2px/);
    expect(css).toMatch(/\.pnl-steps li\.done::before\s*\{[^}]*rgb\(143 209 158/);
    expect(css).toMatch(/\.pnl-steps li\.current \.what\s*\{[^}]*color: var\(--ui-gold-hi\);[^}]*font-weight: 700/);
    expect(css).toMatch(/\.pnl-steps li\s*\{[^}]*grid-template-columns: 18px minmax\(64px, max-content\) minmax\(0, 1fr\)/);
    const src = stripTsComments(readFile(SRC_DIR, "world/QuestLog.tsx"));
    expect(src).not.toMatch(/style=\{\{/);
  });
});

describe("線頭列（#26、#28）", () => {
  it("線軸 18、粗體內容、範圍標籤、鐘＋「剩 …」、NPC 與指向地點標籤；規則句進第一行 (i)", () => {
    const out = html(createElement(ThreadsPane, { threads: [thread("a", "商人欠你人情", { npc_zh: "渡婆婆", location_zh: "渡口石階" })] }));
    expect(out).toMatch(/<li class="pnl-row pnl-thread" data-thread="a"><canvas[^>]*data-icon="thread"/);
    expect(out).toContain('<span class="name">商人欠你人情</span>');
    expect(out).toContain('<span class="pnl-tag">個人</span>');
    expect(out).toMatch(/<span class="pnl-tag"><canvas[^>]*data-icon="card:cooldown"[^>]*><\/canvas>剩 2 天 23 小時<\/span>/);
    expect(out).toContain('<span class="pnl-tag">渡婆婆</span>');
    expect(out).toContain('<span class="pnl-tag">指向渡口石階</span>');
    expect(out).toContain(`aria-label="${THREAD_RULE_ZH}"`);
    expect(out).not.toContain("後到期");
  });

  it("沒有線頭：虛線空狀態（字不變），不畫第一行 (i)", () => {
    const out = html(createElement(ThreadsPane, { threads: [] }));
    expect(out).toBe(`<div class="pnl-empty" data-testid="world-thread-empty">${NO_THREAD_ZH}</div>`);
  });

  it("舊伺服器沒有 left_zh 時用原字", () => {
    expect(threadLeftText({ expires_zh: "3 小時後到期" })).toBe("3 小時後到期");
    expect(threadLeftText({ left_zh: "剩 3 小時", expires_zh: "3 小時後到期" })).toBe("剩 3 小時");
  });

  it("分頁內容不打 API（PanelTabs 量高度會多掛載一次）", () => {
    const src = stripTsComments(readFile(SRC_DIR, "world/QuestLog.tsx"));
    expect(src).not.toMatch(/from "\.\.\/api\/client"/);
  });
});

describe("共用小修：說明字的數字不和前面的名詞分開（KeepNum）", () => {
  it("「封印鑰匙 +5」的詞和數字包成 .pnl-nowrap，其他照常斷行", () => {
    const parts = glueNumbers("成功則熔心坑提早開放、封印鑰匙 +5");
    const glued = parts.filter((p) => p.glue).map((p) => p.text);
    expect(glued).toHaveLength(1);
    expect(glued[0]).toMatch(/匙 \+5$/);
    expect(glued[0]!.length).toBeGreaterThanOrEqual(4); // 至少「鑰匙 +5」：不會只剩「匙 +5」
    expect(parts.map((p) => p.text).join("")).toBe("成功則熔心坑提早開放、封印鑰匙 +5");
  });

  it("沒有空白、負號、全形加號也黏；句首數字、前面是標點時不黏", () => {
    expect(glueNumbers("補給−3").some((p) => p.glue && p.text.endsWith("−3"))).toBe(true);
    expect(glueNumbers("鑰匙＋2").some((p) => p.glue && p.text.endsWith("＋2"))).toBe(true);
    expect(glueNumbers("5 條線頭")).toEqual([{ text: "5 條線頭", glue: false }]);
    expect(glueNumbers("（+5）")).toEqual([{ text: "（+5）", glue: false }]);
    expect(glueNumbers("沒有數字")).toEqual([{ text: "沒有數字", glue: false }]);
  });

  it("一個字的詞併進前一個詞；太長只取尾端 6 字", () => {
    expect([...wordBeforeNumber("封印鑰匙")].length).toBeGreaterThanOrEqual(2);
    expect([...wordBeforeNumber("abcdefghij")].length).toBeLessThanOrEqual(6);
    expect(wordBeforeNumber("、")).toBe("");
  });

  it("輸出：.pnl-nowrap 的 CSS 是 white-space: nowrap；公告板世界事件說明、任務摘要、步驟、線頭都經過 KeepNum", () => {
    const out = html(createElement(KeepNum, { text: "封印鑰匙 +5" }));
    expect(out).toMatch(/<span class="pnl-nowrap">[^<]*匙 \+5<\/span>/);
    expect(html(createElement(KeepNum, { text: "沒有數字" }))).toBe("沒有數字");
    expect(css).toMatch(/\.pnl-nowrap\s*\{\s*white-space: nowrap;\s*\}/);
    const board = stripTsComments(readFile(SRC_DIR, "world/BoardPanes.tsx"));
    expect(board).toMatch(/<div className="pnl-l2">\s*<KeepNum text=\{e\.text_zh\} \/>/);
    const quest = stripTsComments(readFile(SRC_DIR, "world/QuestLog.tsx"));
    for (const s of ["<KeepNum text={quest.summary_zh} />", "<KeepNum text={task} />", "<KeepNum text={t.text_zh} />"]) expect(quest).toContain(s);
  });
});

describe("重閃清單空的時候：虛線空狀態（PNL-2 美術驗收可修 1）", () => {
  it("成長面板（bare，右邊已有標籤）只寫原因；一輪營火照原句", () => {
    expect(reflashEmptyText(true)).toBe("要先閃現過，或有完整技能。");
    expect(reflashEmptyText(false)).toBe("還沒有可以重閃的技能（要先閃現過，或有完整技能）。");
    const src = stripTsComments(readFile(SRC_DIR, "run/CampfireSkillCare.tsx"));
    expect(src).toContain('{list.length === 0 && <EmptyNote testId="reflash-empty">{reflashEmptyText(bare)}</EmptyNote>}');
    expect(src).not.toContain('<div className="muted small">還沒有可以重閃的技能');
  });
});
