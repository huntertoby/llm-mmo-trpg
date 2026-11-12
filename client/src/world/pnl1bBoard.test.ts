// PNL-1b：公告板分頁版（docs/art/資訊面板-移植需求.md 3.3「公告板」、4.1 #1～#12、#37～#39、#42、#44）＋
// PNL-1a 美術驗收必修 1（切分頁時捲動歸零）。vitest 沒有 DOM：分頁列縮放、量高度、捲動由瀏覽器實測（報告第 4 節）；
// 這裡鎖純函式、靜態輸出、「分頁內容不打 API」（PanelTabs 量高度會多掛載一次，PNL-1a 裁定 5）與 CSS 規則。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { api } from "../api/client";
import type { BoardSeasonBossView, BoardWorldEventView, SeasonBoardView, WorldView } from "../api/types";
import { clearPanelIconCache } from "../render/panelIcon";
import { setQCanvasFactory } from "../render/qIcon/core";
import { fakeCanvasFactory, type FakeCanvasLog } from "../test/fakeCanvas";
import { readFile, readStyleFiles, SRC_DIR, stripCssComments, stripTsComments } from "../test/sourceScan";
import { FoldMeasureProvider } from "../ui/PanelKit";
import { cappedLock, paneVariants, resetScrollOnSwitch } from "../ui/PanelTabs";
import { pickTab } from "../ui/panelTabRules";
import { BoardPanel, BoardView } from "./BoardPanel";
import { boardTabs } from "./BoardPanes";
import {
  bossBadge,
  bountyBadge,
  bountyRefreshText,
  bountyTone,
  daysAwayText,
  eventsBadge,
  fullScheduleText,
  goalsBadge,
  nextMilestone,
  pinIcon,
  timelineLayout,
} from "./boardTabs";

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
afterEach(() => vi.restoreAllMocks());

const ev = (event: string, name: string, a: number, b: number, status: BoardWorldEventView["status"], region: string | null): BoardWorldEventView => ({
  event,
  name_zh: name,
  text_zh: `${name}的說明`,
  status,
  status_zh: { pending: "尚未開始", active: "進行中", succeeded: "成功", failed: "失敗" }[status],
  progress: 0,
  target: 30,
  permille: 0,
  days_zh: `第 ${a}～${b} 天`,
  start_day: a,
  end_day: b,
  region,
  target_note_zh: status === "active" ? "沒有前一天的上線紀錄，用原門檻" : null,
});

const boss: BoardSeasonBossView = {
  boss: "rift_shard_lord",
  name_zh: "碎晶之主",
  status: "sealed",
  status_zh: "封印中",
  note_zh: "11 月 10 日 06:00 解鎖",
  announce_at: 0,
  unlock_at: 0,
  close_at: 0,
  world_keys: 0,
  keys_target: null,
  my_keys: 0,
  keys_required: 1,
  attempts_left: 3,
  daily_attempts: 3,
  can_challenge: false,
  problem_zh: null,
  first_kill_zh: null,
  first_kill_titles: [],
  title_zh: "碎晶的終結者",
  board: [],
};

const ms = (id: string, day: number, name: string, kinds: ("story_skill" | "boss_unlock" | "league" | "other")[]) => ({ id, day, name_zh: name, kind: kinds[0]!, kinds });

const board: SeasonBoardView = {
  season: {
    day: 1,
    days: 14,
    status: "running",
    status_zh: "賽季第 1 天／共 14 天",
    phase_zh: "霧中裂痕：主線第 1～2 章、雲嶺；世界事件「霧潮入侵」",
    phase: { id: "act1", name_zh: "霧中裂痕", text_zh: "主線第 1～2 章、雲嶺；世界事件「霧潮入侵」", start_day: 1, end_day: 3 },
    phases: [
      { id: "act1", name_zh: "霧中裂痕", text_zh: "a", start_day: 1, end_day: 3 },
      { id: "act2", name_zh: "灰燼之心", text_zh: "b", start_day: 4, end_day: 7 },
      { id: "act3", name_zh: "封印", text_zh: "c", start_day: 8, end_day: 10 },
      { id: "race", name_zh: "頭目競賽", text_zh: "d", start_day: 11, end_day: 13 },
      { id: "finale", name_zh: "季末", text_zh: "e", start_day: 14, end_day: 14 },
    ],
    upcoming: [],
    milestones: [
      ms("story_skill_1", 2, "主線第 1 章的劇情技能", ["story_skill"]),
      ms("story_skill_2", 6, "主線第 2 章的劇情技能", ["story_skill"]),
      ms("boss_earliest", 8, "賽季頭目最早解鎖", ["boss_unlock"]),
      ms("boss_forced", 10, "賽季頭目強制解鎖；主線第 3 章的劇情技能", ["boss_unlock", "story_skill"]),
      ms("league_signup_close", 13, "影子循環賽截止報名", ["league"]),
      ms("league", 14, "影子循環賽", ["league"]),
    ],
    next_refresh_at: 0,
    next_refresh_zh: "每天 06:00 刷新",
    refresh_time_zh: "06:00",
  },
  goals: [
    { goal: "starter_steps", text_zh: "完成新手任務 2 步", progress: 0, count: 2, done: false, coins: 1 },
    { goal: "reveal_hidden", text_zh: "發現 1 個隱藏地點", progress: 1, count: 1, done: true, coins: 1 },
    { goal: "elite_once", text_zh: "打倒 1 隻精英", progress: 0, count: 1, done: false, coins: 1 },
  ],
  goals_note_zh: "新手期：教學目標",
  bounties: [
    { bounty: "north_wolf_king", name_zh: "北坡狼王", location_zh: "北坡獵場", level: 5, coins: 3, open: true, claimed_by: null, status_zh: "懸賞中", status_note_zh: null },
    { bounty: "mist_swordsman", name_zh: "霧中劍客", location_zh: "劍冢", level: 5, coins: 3, open: true, claimed_by: null, status_zh: "懸賞中", status_note_zh: null },
    { bounty: "scarface", name_zh: "斷崖幫二當家「疤面」", location_zh: "斷崖幫寨", level: 4, coins: 3, open: false, claimed_by: "小美", status_zh: "已被 小美 搶下", status_note_zh: "今天第一次交手打倒仍有小獎：任務幣 1" },
  ],
  world_events: [ev("mist_tide", "霧潮入侵", 1, 3, "active", "cloud_ridge"), ev("lava_breach", "熔岩潰堤", 4, 7, "pending", "ashen_waste"), ev("seal_resonance", "封印共鳴", 7, 10, "pending", null)],
  cleared: [{ location_zh: "斷崖哨站", respawn_at: 0 }],
  level_bonus_zh: ["灰燼荒原：建議等級 +1"],
  season_boss: boss,
};

const keeperView = {
  field: {
    region: "capital",
    situation_objects: [{ id: "seal_keeper", name_zh: "守印人", panel: "board", figure: { portrait: null, line_zh: "封印和懸賞的消息，都貼在板上了。" } }],
  },
} as unknown as WorldView;

const noop = () => undefined;

describe("分頁記號與新字（#3、#5～#12、#37～#39、#42）", () => {
  it("今日目標細框「完成／總條數」、懸賞金底「還能搶的條數」、世界事件綠點、頭目封印中金鎖", () => {
    expect(goalsBadge(board.goals)).toEqual({ kind: "p", value: "1／3", hint: "今日目標完成 1／3" });
    expect(goalsBadge([])).toBeNull();
    expect(bountyBadge(board.bounties)).toEqual({ kind: "n", value: 2, hint: "懸賞中 2" });
    expect(bountyBadge([])).toBeNull();
    expect(eventsBadge(board.world_events)).toEqual({ kind: "live", hint: "霧潮入侵 進行中" });
    expect(eventsBadge([board.world_events[1]!])).toBeNull();
    expect(bossBadge(boss)).toEqual({ kind: "lock", hint: "封印中" });
    expect(bossBadge({ ...boss, status: "open", status_zh: "開放中" })).toBeNull();
  });
  it("五個分頁的順序、短名；預設開今日目標；沒有賽季頭目時只有四頁", () => {
    const tabs = boardTabs(board, { busy: false, onClose: noop });
    expect(tabs.map((t) => [t.id, t.label, t.short])).toEqual([
      ["goals", "今日目標", "目標"],
      ["bounty", "懸賞板", "懸賞"],
      ["sched", "賽季時程", "時程"],
      ["events", "世界事件", "事件"],
      ["boss", "賽季頭目", "頭目"],
    ]);
    expect(pickTab(tabs)).toBe("goals");
    expect(tabs.find((t) => t.id === "sched")?.badge ?? null).toBeNull(); // 時程：純資訊不掛
    expect(boardTabs({ ...board, season_boss: null }, { busy: false, onClose: noop }).map((t) => t.id)).toEqual(["goals", "bounty", "sched", "events"]);
  });
  it("下一個、（明天）／（N 天後）、完整日程標題、懸賞換一批", () => {
    expect(nextMilestone(board.season)).toEqual({ day: 2, names: ["主線第 1 章的劇情技能"] });
    expect(nextMilestone({ ...board.season, day: 14 })).toBeNull();
    expect(daysAwayText(2, 1)).toBe("（明天）");
    expect(daysAwayText(6, 1)).toBe("（5 天後）");
    expect(daysAwayText(1, 1)).toBe("");
    expect(fullScheduleText(board.season)).toBe("完整日程（6 個時間點、5 個階段）");
    expect(bountyRefreshText(board.season)).toBe("每天 06:00 換一批");
    expect(bountyTone(board.bounties[0]!)).toBe("open");
    expect(bountyTone(board.bounties[2]!)).toBe("dim");
    expect(bountyTone({ open: false, claimed_by: "阿霧", status_zh: "你搶下了" })).toBe("mine");
  });
});

describe("賽季時間軸（SeasonTimeline）", () => {
  it("釘：每天一個、同一天的種類合併；下一個加亮金圈；已過的淡；圖示對照（第 5 節第 7 點）", () => {
    const t = timelineLayout({ ...board.season, day: 3 }, board.world_events);
    expect(t.days).toBe(14);
    expect(t.today).toBe(3);
    expect(t.pins.map((p) => [p.day, p.kinds.join("+"), p.next, p.past])).toEqual([
      [2, "story_skill", false, true],
      [6, "story_skill", true, false],
      [8, "boss_unlock", false, false],
      [10, "boss_unlock+story_skill", false, false],
      [13, "league", false, false],
      [14, "league", false, false],
    ]);
    expect(["story_skill", "boss_unlock", "league", "other"].map((k) => pinIcon(k as never))).toEqual(["narrator", "lock", "shadow", "hourglass"]);
  });
  it("階段：今天所在段金色；世界事件：重疊的排第二列、進行中看伺服器狀態", () => {
    const t = timelineLayout(board.season, board.world_events);
    expect(t.segs.filter((s) => s.now).map((s) => s.phase.id)).toEqual(["act1"]);
    expect(t.events.map((e) => [e.event.event, e.lane, e.now])).toEqual([
      ["mist_tide", 0, true],
      ["lava_breach", 0, false],
      ["seal_resonance", 1, false], // 第 7 天和熔岩潰堤重疊
    ]);
    expect(t.lanes).toBe(2);
  });
  it("開賽前：沒有今天、沒有下一個、沒有金色段", () => {
    const t = timelineLayout({ ...board.season, status: "upcoming", day: 0 }, board.world_events);
    expect(t.today).toBeNull();
    expect(t.pins.some((p) => p.next)).toBe(false);
    expect(t.segs.some((s) => s.now)).toBe(false);
  });
});

describe("畫面（靜態輸出）", () => {
  it("固定區：標題、回到地點圖、守印人（寬版對話泡＋窄版小頭像一行，滑過「守印人：全文」）、第 N 天大字、日程、下一個", () => {
    const out = html(createElement(BoardView, { board, view: keeperView, onClose: noop }));
    expect(out).toContain('class="pnl-fixed"');
    expect(out).toContain('data-testid="world-board-keeper"');
    expect(out).toContain('data-testid="world-board-keeper-mini"');
    expect(out).toContain("封印和懸賞的消息，都貼在板上了。");
    expect(out).toContain("公告板");
    expect(out).toContain("回到地點圖");
    expect(out).toMatch(/第<b>1<\/b>天<span class="of">／共 14 天<\/span>/);
    expect(out).toContain("霧中裂痕");
    expect(out).toContain("第 1～3 天");
    expect(out).toContain("下一個");
    expect(out).toContain("（明天）");
    // 預設分頁＝今日目標：資訊標籤、完成一條 +1、每條一列
    expect(out).toContain('data-tab="goals"');
    expect(out).toContain("新手期：教學目標");
    expect(out).toContain("完成一條");
    expect(out).toContain("完成（+1 任務幣）");
    expect(out).toContain("0／2");
  });
  it("其他城鎮（沒有守印人）不畫守印人；讀取中只畫固定區", () => {
    const plain = html(createElement(BoardView, { board: null, view: { field: { region: "cloud_ridge", situation_objects: [] } } as unknown as WorldView, onClose: noop }));
    expect(plain).not.toContain("world-board-keeper");
    expect(plain).toContain("讀取中");
  });
  it("懸賞：五欄（欄名列與每列共用 class）、Lv N、代幣、狀態標籤；括號說明進說明卡（不在畫面上）", () => {
    const out = html(createElement(BoardView, { board, view: keeperView, onClose: noop, initial: "bounty" }));
    expect(out).toContain('class="pnl-cols-head pnl-bounty-cols"');
    for (const h of ["目標・地點", "建議等級", "獎勵", "狀態", "先搶先贏", "每天 06:00 換一批"]) expect(out).toContain(h);
    expect(out.match(/class="pnl-row pnl-bounty pnl-bounty-cols/g)?.length).toBe(3);
    expect(out).toContain("Lv <b>5</b>");
    expect(out).toContain("已被 小美 搶下");
    expect(out).toContain('data-testid="world-board-bounty-note"');
    expect(out).not.toContain("今天第一次交手");
  });
  it("賽季時程：時間軸四種列名、完整日程摺疊列出全部時間點", () => {
    const out = html(createElement(BoardView, { board, view: keeperView, onClose: noop, initial: "sched" }));
    for (const h of ["時間點", "天", "階段", "世界事件", "完整日程（6 個時間點、5 個階段）"]) expect(out).toContain(h);
    expect(out).toContain('data-testid="world-board-timeline"');
    expect(out.match(/class="pnl-tl-day/g)?.length).toBe(14);
    expect(out).toContain('class="pnl-tl-day today"');
    expect(out).toContain('data-kinds="boss_unlock story_skill"');
    expect(out).toContain('data-lane="1"');
    expect(out.match(/<li[^>]*><span class="d">/g)?.length).toBe(6);
  });
  it("世界事件：全服一起推進、尚未開始虛線、門檻進 (i)、世界變化列在最後", () => {
    const out = html(createElement(BoardView, { board, view: keeperView, onClose: noop, initial: "events" }));
    expect(out).toContain("全服一起推進");
    expect(out).toContain('class="pnl-event pending"');
    expect(out).toContain("<b>0</b>／30");
    expect(out).toContain('aria-label="門檻：沒有前一天的上線紀錄，用原門檻"');
    expect(out).toContain('data-testid="world-board-shared"');
    expect(out).toContain("已清空");
    expect(out).toContain("灰燼荒原：建議等級 +1");
  });
  it("賽季頭目：狀態標籤、鑰匙、挑戰規則與評分榜摺疊（右邊「還沒有人打倒」或第 1 名）；挑戰鈕在摺疊外", () => {
    const out = html(createElement(BoardView, { board, view: keeperView, onClose: noop, initial: "boss" }));
    expect(out).toContain("碎晶之主");
    expect(out).toContain("封印中");
    expect(out).toContain("挑戰規則與評分榜");
    expect(out).toContain("還沒有人打倒");
    const open: SeasonBoardView = { ...board, season_boss: { ...boss, status: "open", status_zh: "開放中", can_challenge: true, board: [{ rank: 1, name: "小美", score: 1, rounds: 1, survivors: 1, allies: 1, no_down: false, location_zh: "霧渡鎮", mine: false, at: 0, titles: [] }] } };
    const o2 = html(createElement(BoardView, { board: open, view: keeperView, onClose: noop, onAct: noop, initial: "boss" }));
    expect(o2).toContain("第 1 名 小美");
    const btn = o2.indexOf('data-testid="world-board-boss-challenge"');
    const fold = o2.indexOf('data-testid="world-board-boss-fold"');
    expect(btn).toBeGreaterThan(-1);
    expect(btn).toBeLessThan(fold);
  });
  it("量高度時兩個摺疊各打開一次（時程、頭目的 folds）", () => {
    const tabs = boardTabs(board, { busy: false, onClose: noop });
    expect(tabs.flatMap((t) => paneVariants(t).map((v) => v.key))).toEqual(["goals", "bounty", "sched:full", "events", "boss:rules"]);
  });
});

describe("不重複打 API（PNL-1a 裁定 5：PanelTabs 量高度時分頁內容多掛載一次）", () => {
  it("每一頁的每種量測樣子各畫兩遍，api.worldBoard 一次都沒被呼叫", () => {
    const spy = vi.spyOn(api, "worldBoard").mockResolvedValue(board);
    const tabs = boardTabs(board, { busy: false, onClose: noop });
    for (let pass = 0; pass < 2; pass++) {
      for (const t of tabs) for (const v of paneVariants(t)) html(createElement(FoldMeasureProvider, { value: v.fold }, t.render()));
    }
    html(createElement(BoardView, { board, view: keeperView, onClose: noop }));
    expect(spy).not.toHaveBeenCalled();
  });
  it("讀公告板只在 BoardPanel（PanelTabs 外面）：分頁與時間軸的檔不匯入 API；整個 world/ 只有一處 api.worldBoard", () => {
    for (const f of ["world/BoardPanes.tsx", "world/SeasonTimeline.tsx", "world/boardTabs.ts"]) {
      const code = stripTsComments(readFile(SRC_DIR, f));
      expect(code, f).not.toMatch(/from "\.\.\/api\/client"/);
      expect(code, f).not.toMatch(/\bapi\./);
    }
    const panel = stripTsComments(readFile(SRC_DIR, "world/BoardPanel.tsx"));
    expect(panel.match(/api\s*\.\s*worldBoard\(/g)?.length).toBe(1);
    expect(panel.indexOf("useBoard(characterId, view)")).toBeGreaterThan(-1);
    expect(typeof BoardPanel).toBe("function");
  });
});

describe("PNL-1a 美術驗收：必修 1 切分頁時捲動歸零、可修 1 固定區下緣漸隱加長", () => {
  const host = (top: number) => {
    const body = { scrollTop: top };
    return { body, root: { closest: (sel: string) => (sel === ".ui-popup-body" ? body : null), parentElement: null } };
  };
  it("換頁時把捲動區 scrollTop 設回 0；同一頁、沒捲、沒有捲動區時不動", () => {
    const a = host(22);
    expect(resetScrollOnSwitch(a.root, "party", "shadow")).toBe(true);
    expect(a.body.scrollTop).toBe(0);
    const same = host(22);
    expect(resetScrollOnSwitch(same.root, "party", "party")).toBe(false);
    expect(same.body.scrollTop).toBe(22);
    expect(resetScrollOnSwitch(host(0).root, "a", "b")).toBe(false);
    expect(resetScrollOnSwitch(null, "a", "b")).toBe(false);
    const parentOnly = { scrollTop: 9 };
    expect(resetScrollOnSwitch({ closest: () => null, parentElement: parentOnly }, "a", "b")).toBe(true);
    expect(parentOnly.scrollTop).toBe(0);
  });
  it("鎖高度不超過捲動區（最高那一頁超出 maxHeight 時，短的頁不再多一段要捲的空白）", () => {
    expect(cappedLock(334, 334, 0)).toBe(334); // 放得下：照量到的
    expect(cappedLock(334, 334, 125)).toBe(209); // 800×600 公告板：超出 125 → 只鎖到放得下
    expect(cappedLock(200, 334, 40)).toBe(200); // 重量時舊的鎖高比較大：照實際分頁區高扣
    expect(cappedLock(50, 50, 400)).toBe(0);
  });
  it("PanelTabs 的分頁列點擊會呼叫歸零（原始碼）", () => {
    const code = stripTsComments(readFile(SRC_DIR, "ui/PanelTabs.tsx"));
    expect(code).toMatch(/onPick=\{\(id\) => \{\s*resetScrollOnSwitch\(root\.current, active\.id, id\);\s*setPicked\(id\);/);
  });
  it("漸隱 16px、上段實色", () => {
    const at = css.indexOf('.ui-popup-body[data-scrolled="1"] .pnl-fixed::after {');
    const block = css.slice(at, css.indexOf("}", at));
    expect(block).toContain("height: 16px;");
    expect(block).toMatch(/var\(--ui-navy\) 35%/);
  });
});

describe("CSS（3.3）", () => {
  const container = (() => {
    const all: string[] = [];
    let at = css.indexOf("@container world-panel (max-width: 559px)");
    while (at >= 0) {
      all.push(css.slice(at, css.indexOf("}\n}", at) + 3));
      at = css.indexOf("@container world-panel (max-width: 559px)", at + 1);
    }
    return all.join("\n");
  })();
  it("懸賞欄寬寫在 class；面板 < 560 收掉獎勵欄（欄名一起收）", () => {
    expect(css).toMatch(/\.pnl-bounty-cols \{[^}]*grid-template-columns: 28px minmax\(0, 1fr\) 64px 46px 96px;/);
    expect(container).toContain(".pnl-bounty .reward, .pnl-cols-head .reward-h { display: none; }");
  });
  it("面板 < 560：守印人對話泡收起、標題旁小頭像一行出現", () => {
    expect(container).toContain(".pnl-speaker { display: none; }");
    expect(container).toContain(".pnl-speaker-mini { display: flex; }");
    expect(css).toMatch(/\.pnl-speaker-mini \.line \{[^}]*text-overflow: ellipsis;[^}]*white-space: nowrap;/);
  });
  it("尚未開始的世界事件＝虛線框；今天＝亮金膠囊", () => {
    expect(css).toMatch(/\.pnl-event\.pending \{[^}]*border: 1px dashed/);
    expect(css).toMatch(/\.pnl-tl-day\.today::before \{[^}]*background: var\(--ui-gold-hi\)/);
  });
});
