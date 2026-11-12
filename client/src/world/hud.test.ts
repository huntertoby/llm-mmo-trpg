// Phase 6B-5：網遊式 HUD 版面 A（docs/archive/art/HUD移植需求.md）：23 項對照表、單一面板開關、快捷鍵、窄視窗收合、
// 浮動提示淡出、時間天氣、小地圖、四角版面的排版煙霧檢查（1040×624、800×600）、出口附近變半透明。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { FieldView, WorldView } from "../api/types";
import { TOAST_TTL_MS } from "../battle/logToasts";
import {
  addToasts,
  buttonBadge,
  buttonState,
  dayPart,
  evaluateHudLayout,
  HUD_TOUCH_ZH,
  hudButtonCard,
  exitRects,
  fadedBlocks,
  fieldFitScale,
  HUD_BLOCKS,
  HUD_BUTTONS,
  hudKey,
  hudLayout,
  isNarrow,
  liveHudToasts,
  mateCards,
  minimapModel,
  nextHudToastChange,
  panelAvailable,
  popupBox,
  readTrackerCollapsed,
  RESERVED_KEYS,
  restrictions,
  shownPanel,
  togglePanel,
  trackedQuests,
  TRACKER_KEY,
  weatherMark,
  weatherPhaseText,
  writeTrackerCollapsed,
  type HudLayout,
  type LiveToast,
} from "./hud";
import { BAR_ICON_ID } from "../render/hudIcon";
import { ICON as HUD_Q_ICON } from "../render/qIcon/hud";
import { HUD_BAR_ORDER, HudBarIcon, type HudBarKey } from "./HudBarIcons";
import { HudBarCard, WorldHud, type WorldHudProps } from "./WorldHud";
import { trackerFoldDot } from "./range";

/** 24×18（霧渡鎮的大小）：東邊、北邊、西南各一個出口。 */
function field(over: Partial<FieldView> = {}): FieldView {
  const W = 24;
  const H = 18;
  const tiles = Array.from({ length: W * H }, (_, i) => ({
    x: i % W,
    y: Math.floor(i / W),
    height: 0,
    terrain: i % W === 5 && Math.floor(i / W) === 5 ? "wall" : "stone",
    surface: Math.floor(i / W) >= 16 ? "water" : "none",
    walkable: !(i % W === 5 && Math.floor(i / W) === 5),
  }));
  return {
    map_id: "mist_ferry",
    name_zh: "霧渡鎮",
    region: "cloud_ridge",
    location: "mist_ferry",
    interior: false,
    width: W,
    height: H,
    tiles,
    objects: [],
    exits: [
      { id: "to_hunter_hut", cells: [[11, 0], [12, 0]], to: "hunter_hut", to_name_zh: "獵戶小屋" },
      { id: "to_ferry_steps", cells: [[23, 8], [23, 9]], to: "ferry_steps", to_name_zh: "渡口石階" },
      { id: "to_ashen_ferry", cells: [[3, 17], [4, 17]], to: "ashen_ferry", to_name_zh: "往灰燼荒原的渡口" },
    ],
    doors: [],
    stones: [{ id: "stone_mist_ferry", x: 12, y: 8, unlocked: true }],
    npcs: [{ id: "granny_du", name_zh: "渡婆婆", x: 11, y: 13 }],
    facilities: [
      { kind: "shop", x: 15, y: 11 },
      { kind: "tavern", x: 3, y: 6 },
    ],
    me: { x: 12, y: 10, facing: "s" },
    max_climb: 1,
    hero: null,
    stone_targets: [],
    ...over,
  } as FieldView;
}

type Over = { atService?: boolean; reports?: number; insight?: number; quests?: number; pending?: boolean; mates?: number };

/** 測試只用到的欄位（其他欄位不讀）。 */
function view({ atService = true, reports = 0, insight = 2, quests = 2, pending = false, mates = 2 }: Over = {}): WorldView {
  const members = [
    { name_zh: "阿青", title_zh: "主角", level: 4 },
    { name_zh: "傭兵・青鋒", title_zh: "劍客・攻擊", level: 4, mercenary: "merc_qing" },
    { name_zh: "傭兵・岳山", title_zh: "盾衛・守護", level: 4, mercenary: "merc_yue" },
  ].slice(0, 1 + mates);
  return {
    character: {
      character_id: "c1",
      name: "阿青",
      level: 4,
      xp: 45,
      xp_next: 100,
      hp: 41,
      max_hp: 50,
      mana: 18,
      max_mana: 30,
      supplies: 6,
      max_supplies: 10,
      fatigued: false,
      attribute_points: 0,
      weapon_name_zh: "長劍",
      race_name_zh: null,
      skills: [],
      bench: [],
      slots_zh: "",
      insight,
      skill_tier: 2,
    },
    here: { location: "mist_ferry", name_zh: "霧渡鎮", kind_zh: "城鎮", camp_problem_zh: atService ? null : "附近有敵人", can_rest: atService },
    encounter: null,
    battle_id: null,
    clock: { time_zh: "13:20", day_phase: "day", day_phase_zh: "白天", weather_zh: "濃霧" },
    growth: { at_service: atService, insight, skill_tier: 2 },
    pending_flash: pending ? { skill_id: "a", nth: 1, slot: null } : null,
    pending_offer: null,
    wallet: { gold: 1240, quest_coins: 35 },
    inventory: { bag: [] },
    shop: null,
    crafting: null,
    party: { members, max_hired: 2, can_hire: true, hire_problem_zh: null },
    my_shadow: { saved: true, reports_zh: Array.from({ length: reports }, (_, i) => `戰報 ${i}`) },
    quests: Array.from({ length: quests }, (_, i) => ({
      id: `q${i}`,
      name_zh: ["盜賊擋渡船", "懸賞：霧狼"][i % 2],
      kind_zh: "主線",
      summary_zh: "",
      giver_zh: null,
      steps: [
        { text_zh: "到渡口石階", done: i === 1, current: i === 0 },
        { text_zh: "打倒盜賊", done: false, current: i === 1 },
      ],
      done: false,
    })),
    threads: [{ id: "t1", text_zh: "古碑上的字", expires_zh: "還有 2 天", scope_zh: "", npc_zh: null, location_zh: null }],
    field: field(),
  } as unknown as WorldView;
}

const toasts: LiveToast[] = [
  { toast: { seq: 0, text: "賣出 3 件雜物，+45", warn: false, at: 0 }, fading: false },
  { toast: { seq: 1, text: "渡船：晚上不開", warn: true, at: 0 }, fading: false },
];

function props(v: WorldView, layout: HudLayout, over: Partial<WorldHudProps> = {}): WorldHudProps {
  return {
    view: v,
    layout,
    faded: [],
    toasts,
    trackerCollapsed: false,
    onTracker: () => undefined,
    onButton: () => undefined,
    onMap: () => undefined,
    onPlace: () => undefined,
    openPanel: null,
    panel: null,
    onClosePanel: () => undefined,
    ...over,
  };
}

const html = (p: WorldHudProps) => renderToStaticMarkup(createElement(WorldHud, p));
const count = (markup: string, item: string) => markup.split(`data-hud="${item}"`).length - 1;

describe("23 項對照表都找得到（HUD版面.md 第 2 節）", () => {
  const layout = hudLayout(1040, 624, { mates: 2, narrow: false, collapsed: false });
  const markup = html(props(view({ atService: false, reports: 1 }), layout));
  // 對照表的順序：Lv、經驗、HP、法力、補給、金幣、任務幣、階級、靈感點、技能、地點、時間、天氣、背包、隊伍、影子、
  // 地點卡的地點名、任務追蹤、限制提示、成長、潛行（原趕路）、留言、最近發生的事
  const items: Array<[string, string]> = [
    ["Lv", "lv"],
    ["經驗", "xp"],
    ["HP", "hp"],
    ["法力", "mana"],
    ["補給", "supplies"],
    ["金幣", "gold"],
    ["任務幣", "quest-coins"],
    ["階級", "rank"],
    ["靈感點", "insight"],
    ["技能", "btn-skills"],
    ["地點", "place"],
    ["時間", "time"],
    ["天氣", "weather"],
    ["背包", "btn-bag"],
    ["隊伍", "party"],
    ["我的影子", "shadow"],
    ["地點卡：地點名", "place"],
    ["地點卡：任務與線頭", "tracker"],
    ["地點卡：限制提示", "limits"],
    ["地點卡：成長與技能", "btn-growth"],
    ["地點卡：趕路勾選→潛行", "btn-sneak"],
    ["地點留言", "btn-notes"],
    ["最近發生的事", "toasts"],
  ];
  it.each(items)("%s", (_name, item) => {
    expect(count(markup, item)).toBeGreaterThan(0);
  });

  it("共 23 項", () => {
    expect(items).toHaveLength(23);
  });

  it("圖示＋數字的只有數字：HP、法力、補給、靈感、錢", () => {
    expect(markup).toContain(">41 / 50<");
    expect(markup).toContain(">18 / 30<");
    expect(markup).toContain(">1,240<");
    expect(markup).toContain(">35<");
    expect(markup).not.toContain("HP 41");
    expect(markup).not.toContain("金幣 1240<");
  });

  it("時間天氣是圖示＋一個字", () => {
    expect(markup).toMatch(/data-hud="time"[^>]*>.*?<span>午<\/span>/);
    expect(markup).toMatch(/data-hud="weather"[^>]*>.*?<span>霧<\/span>/);
  });

  it("功能列 7 個鈕＋地圖鈕，右下寫快捷鍵", () => {
    for (const b of HUD_BUTTONS) expect(count(markup, `btn-${b.id}`)).toBe(1);
    expect(count(markup, "map")).toBe(1);
    expect(markup).toContain('<span class="key">M</span>');
    for (const k of ["I", "K", "G", "J", "Y", "N", "R"]) expect(markup).toContain(`<span class="key">${k}</span>`);
  });

  it("面板平常看不到（收進面板的點了才出現）", () => {
    expect(markup).not.toContain("world-hud-panel");
    expect(markup).not.toContain("world-hud-backdrop");
  });

  it("隊友 2 人、任務追蹤 2 條、提示紅框", () => {
    expect(count(markup, "mate")).toBe(2);
    expect(count(markup, "tracked")).toBe(2);
    expect(markup).toContain("world-hud-toast warn");
  });

  it("影子有戰報時加紫點、成長有靈感點時加紅點", () => {
    expect(markup).toContain("world-hud-dot purple");
    expect(markup).toContain("world-hud-dot red");
  });
});

describe("單一浮動面板", () => {
  it("再按一次關、按別的換", () => {
    expect(togglePanel(null, "bag")).toBe("bag");
    expect(togglePanel("bag", "bag")).toBeNull();
    expect(togglePanel("bag", "skills")).toBe("skills");
  });

  it("閃現待選時固定顯示、不能換；沒有資料的面板開不了", () => {
    expect(shownPanel(view({ pending: true }), "bag")).toBe("pending");
    expect(shownPanel(view(), "bag")).toBe("bag");
    expect(shownPanel(view(), "shop")).toBeNull();
    expect(panelAvailable(view(), "shop")).toBe(false);
    expect(shownPanel(view(), null)).toBeNull();
  });

  it("開著面板時有背景遮罩與關閉鈕（點空白處關）；鎖住時沒有關閉鈕", () => {
    const layout = hudLayout(1040, 624, { mates: 2, narrow: false, collapsed: false });
    const open = html(props(view(), layout, { panel: createElement("div", null, "背包內容"), openPanel: "bag" }));
    expect(open).toContain('data-testid="world-hud-backdrop"');
    expect(open).toContain('data-testid="world-hud-panel-close"');
    expect(open).toContain("背包內容");
    expect(open).toMatch(/data-hud="btn-bag"/);
    expect(open).toMatch(/aria-pressed="true"[^>]*data-hud="btn-bag"/);
    const locked = html(props(view(), layout, { panel: createElement("div", null, "閃現"), openPanel: "pending", panelLocked: true }));
    expect(locked).not.toContain("world-hud-panel-close");
  });
});

describe("快捷鍵", () => {
  it("I K G J Y N R M 對到功能，Esc 關面板", () => {
    expect(hudKey({ key: "i" })).toEqual({ kind: "button", id: "bag" });
    expect(hudKey({ key: "K" })).toEqual({ kind: "button", id: "skills" });
    expect(hudKey({ key: "g" })).toEqual({ kind: "button", id: "growth" });
    expect(hudKey({ key: "j" })).toEqual({ kind: "button", id: "quests" });
    expect(hudKey({ key: "y" })).toEqual({ kind: "button", id: "shadow" });
    expect(hudKey({ key: "n" })).toEqual({ kind: "button", id: "notes" });
    expect(hudKey({ key: "r" })).toEqual({ kind: "button", id: "sneak" });
    expect(hudKey({ key: "m" })).toEqual({ kind: "map" });
    expect(hudKey({ key: "Escape" })).toEqual({ kind: "escape" });
  });

  it("有修飾鍵、在輸入框打字、別的鍵都不算", () => {
    expect(hudKey({ key: "i", ctrlKey: true })).toBeNull();
    expect(hudKey({ key: "i", metaKey: true })).toBeNull();
    expect(hudKey({ key: "i" }, true)).toBeNull();
    expect(hudKey({ key: "q" })).toBeNull();
    expect(hudKey({ key: "e" })).toBeNull();
    expect(hudKey({ key: "M", shiftKey: true })).toBeNull(); // AU-1：Shift＋M 是全部靜音
  });

  it("不和戰鬥、走路的鍵衝突，彼此也不重複", () => {
    const keys = [...HUD_BUTTONS.map((b) => b.key), "m"];
    expect(new Set(keys).size).toBe(keys.length);
    for (const k of keys) expect(RESERVED_KEYS).not.toContain(k);
  });
});

describe("窄視窗（< 900px）", () => {
  it("判定", () => {
    expect(isNarrow(899)).toBe(true);
    expect(isNarrow(900)).toBe(false);
  });

  it("隊友卡只留頭像和血條", () => {
    const layout = hudLayout(800, 520, { mates: 2, narrow: true, collapsed: true });
    const markup = html(props(view(), layout, { trackerCollapsed: true }));
    expect(count(markup, "mate")).toBe(2);
    expect(count(markup, "mate-hp")).toBe(2);
    expect(markup).not.toContain('class="name">傭兵');
    expect(layout.blocks.mates.width / layout.scale).toBe(96);
  });

  it("任務追蹤收成一個圖示", () => {
    const layout = hudLayout(800, 520, { mates: 2, narrow: true, collapsed: true });
    const markup = html(props(view(), layout, { trackerCollapsed: true }));
    expect(count(markup, "tracker")).toBe(1);
    expect(count(markup, "tracked")).toBe(0);
    expect(layout.blocks.tracker.width / layout.scale).toBe(36);
  });

  it("提示減為 1 條", () => {
    const list = addToasts([], ["一", "二", "三"], false, 1000, 0);
    expect(liveHudToasts(list, 1000, 1).map((t) => t.toast.text)).toEqual(["三"]);
    expect(liveHudToasts(list, 1000).map((t) => t.toast.text)).toEqual(["一", "二", "三"]);
  });

  it("收合狀態記在本機；讀寫失敗不出錯", () => {
    const mem = new Map<string, string>();
    const store = { getItem: (k: string) => mem.get(k) ?? null, setItem: (k: string, v: string) => void mem.set(k, v) };
    expect(readTrackerCollapsed(store)).toBe(false);
    writeTrackerCollapsed(true, store);
    expect(mem.get(TRACKER_KEY)).toBe("1");
    expect(readTrackerCollapsed(store)).toBe(true);
    const broken = {
      getItem: () => {
        throw new Error("blocked");
      },
      setItem: () => {
        throw new Error("blocked");
      },
    };
    expect(readTrackerCollapsed(broken)).toBe(false);
    expect(() => writeTrackerCollapsed(true, broken)).not.toThrow();
    expect(readTrackerCollapsed(null)).toBe(false);
  });
});

describe("浮動提示淡出", () => {
  it("最多 3 條、新的在下；約 6 秒消失，最後 1 秒淡出", () => {
    let list = addToasts([], ["a", "b"], false, 0, 0);
    list = addToasts(list, ["c", "d"], true, 1000, 2);
    expect(liveHudToasts(list, 1000).map((t) => t.toast.text)).toEqual(["b", "c", "d"]);
    expect(liveHudToasts(list, 4999).every((t) => !t.fading)).toBe(true);
    const at5500 = liveHudToasts(list, 5500);
    expect(at5500.find((t) => t.toast.text === "b")?.fading).toBe(true);
    expect(liveHudToasts(list, TOAST_TTL_MS).map((t) => t.toast.text)).toEqual(["c", "d"]);
    expect(liveHudToasts(list, 1000 + TOAST_TTL_MS)).toEqual([]);
  });

  it("不會一直累積：加入時丟掉過期的", () => {
    let list = addToasts([], ["舊"], false, 0, 0);
    list = addToasts(list, ["新"], false, TOAST_TTL_MS + 1, 1);
    expect(list.map((t) => t.text)).toEqual(["新"]);
    const many = addToasts([], Array.from({ length: 30 }, (_, i) => String(i)), false, 0, 0);
    expect(many.length).toBeLessThanOrEqual(12);
  });

  it("下一次要重畫的時間", () => {
    const list = addToasts([], ["a"], false, 0, 0);
    expect(nextHudToastChange(liveHudToasts(list, 0), 0)).toBe(5000);
    expect(nextHudToastChange(liveHudToasts(list, 5200), 5200)).toBe(800);
    expect(nextHudToastChange([], 0)).toBeNull();
  });
});

describe("時間、天氣、限制、任務追蹤、隊友", () => {
  it("時刻換算早午晚夜", () => {
    expect(dayPart({ time_zh: "06:00", day_phase: "day" })).toEqual({ char: "早", icon: "sun" });
    expect(dayPart({ time_zh: "13:20", day_phase: "day" })).toEqual({ char: "午", icon: "sun" });
    expect(dayPart({ time_zh: "18:05", day_phase: "night" })).toEqual({ char: "晚", icon: "moon" });
    expect(dayPart({ time_zh: "23:59", day_phase: "night" })).toEqual({ char: "夜", icon: "moon" });
    expect(dayPart({ time_zh: "04:59", day_phase: "night" }).char).toBe("夜");
    expect(dayPart({ time_zh: "??", day_phase: "day" }).char).toBe("午");
    expect(dayPart({ time_zh: "??", day_phase: "night" }).char).toBe("夜");
  });

  it("白天／夜晚照伺服器的 day_phase，不自己用時刻判斷（6F-1：HUD「晚」對遇敵卡「白天」）", () => {
    expect(dayPart({ time_zh: "17:40", day_phase: "day" })).toEqual({ char: "午", icon: "sun" });
    expect(dayPart({ time_zh: "18:00", day_phase: "night" })).toEqual({ char: "晚", icon: "moon" });
    expect(dayPart({ time_zh: "05:30", day_phase: "night" })).toEqual({ char: "夜", icon: "moon" });
    expect(dayPart({ time_zh: "05:12", day_phase: "night" }).char).not.toBe("早"); // 巡檢 bug 4
  });

  it("「夜晚」天氣不和時段重複（巡檢 bug 4：天氣欄「夜」、遇敵卡「夜晚・夜晚」）", () => {
    expect(weatherMark("夜晚")).toEqual({ char: "晴", icon: "night" });
    expect(weatherPhaseText("夜晚", "夜晚")).toBe("晴朗・夜晚");
    expect(weatherPhaseText("下雨", "夜晚")).toBe("下雨・夜晚");
    expect(weatherPhaseText("晴朗", "白天")).toBe("晴朗・白天");
  });

  it("天氣一個字", () => {
    expect(weatherMark("晴朗").char).toBe("晴");
    expect(weatherMark("下雨")).toEqual({ char: "雨", icon: "rain" });
    expect(weatherMark("濃霧")).toEqual({ char: "霧", icon: "fog" });
  });

  it("限制提示：不在城鎮與營火時", () => {
    expect(restrictions(view())).toEqual([]);
    const limits = restrictions(view({ atService: false }));
    expect(limits[0]).toContain("不能閃現");
    expect(limits[1]).toBe("紮營：附近有敵人");
  });

  it("任務追蹤最多 2 條，任務優先、再補線頭", () => {
    expect(trackedQuests(view()).map((t) => t.name)).toEqual(["盜賊擋渡船", "懸賞：霧狼"]);
    expect(trackedQuests(view())[0]!.line).toBe("到渡口石階（0/2）");
    expect(trackedQuests(view({ quests: 1 })).map((t) => t.kind)).toEqual(["quest", "thread"]);
  });

  it("隊友卡不含主角，最多 2 人，血條滿", () => {
    expect(mateCards(view()).map((m) => m.short)).toEqual(["傭兵・", "傭兵・"]);
    expect(mateCards(view({ mates: 0 }))).toEqual([]);
    expect(mateCards(view()).every((m) => m.hp === 1)).toBe(true);
  });

  it("功能列的數字與點", () => {
    expect(buttonBadge(view(), "quests")).toEqual({ text: "2", tone: "count" });
    expect(buttonBadge(view({ insight: 0 }), "growth")).toBeNull();
    expect(buttonBadge(view({ reports: 0 }), "shadow")).toBeNull();
    expect(buttonBadge(view(), "sneak")).toBeNull();
  });
});

describe("小地圖", () => {
  const map = minimapModel(field());
  it("出口箭頭朝外、NPC、休息點、傳送石、自己", () => {
    expect(map.exits.map((e) => [e.label, e.dir])).toEqual([
      ["獵戶小屋", "up"],
      ["渡口石階", "right"],
      ["往灰燼荒原的渡口", "down"],
    ]);
    expect(map.dots.map((d) => d.kind)).toEqual(["npc", "rest", "stone", "me"]);
    expect(map.dots.at(-1)).toMatchObject({ x: 12, y: 10 });
  });

  it("地形顏色、水、牆；沒有走過的資料＝不蓋霧", () => {
    expect(map.colors).toHaveLength(24 * 18);
    expect(map.colors[5 * 24 + 5]).not.toBe(map.colors[0]);
    expect(map.colors[17 * 24]).not.toBe(map.colors[0]);
    expect(map.fog.every((f) => !f)).toBe(true);
  });
});

describe("排版煙霧（四角版面）", () => {
  // 舞台＝視窗扣掉標頭（約 60px）與左右邊距；1040×624 與 800×600 兩種視窗
  const cases: Array<[string, number, number, boolean]> = [
    ["1040×624", 1008, 556, false],
    ["800×600", 768, 532, true],
  ];
  it.each(cases)("%s：每塊在畫面裡、不重疊、四角位置對、中間沒被擋", (_name, w, h, narrow) => {
    for (const collapsed of [false, true]) {
      const layout = hudLayout(w, h, { mates: 2, narrow, collapsed });
      const checks = evaluateHudLayout({ viewport: { width: w, height: h }, stage: { left: 0, top: 0, width: w, height: h }, blocks: layout.blocks });
      expect(checks.filter((c) => !c.pass)).toEqual([]);
    }
  });

  it("沒有隊友時影子鈕往上移，不和主角卡重疊", () => {
    const layout = hudLayout(1008, 556, { mates: 0, narrow: false, collapsed: false });
    const checks = evaluateHudLayout({ viewport: { width: 1008, height: 556 }, stage: { left: 0, top: 0, width: 1008, height: 556 }, blocks: layout.blocks });
    expect(checks.filter((c) => !c.pass)).toEqual([]);
    expect(layout.blocks.shadow.top).toBeLessThan(hudLayout(1008, 556, { mates: 2, narrow: false, collapsed: false }).blocks.shadow.top);
  });

  it("壞掉的版面會被抓到", () => {
    const layout = hudLayout(1008, 556, { mates: 2, narrow: false, collapsed: false });
    const blocks = { ...layout.blocks, tracker: { left: 400, top: 200, width: 200, height: 150 } };
    const failed = evaluateHudLayout({ viewport: { width: 1008, height: 556 }, stage: { left: 0, top: 0, width: 1008, height: 556 }, blocks }).filter((c) => !c.pass);
    expect(failed.map((c) => c.id)).toContain("center-free");
  });

  it("依視窗大小等比例縮放", () => {
    expect(hudLayout(1040, 624, { mates: 2, narrow: false, collapsed: false }).scale).toBe(1);
    expect(hudLayout(768, 532, { mates: 2, narrow: true, collapsed: false }).scale).toBeCloseTo(768 / 1040, 5);
  });
});

describe("地圖用滿舞台、出口附近的 HUD 變半透明", () => {
  it("霧渡鎮在 1040×624 的舞台上比 6B-3 的 0.54 倍大", () => {
    expect(fieldFitScale({ width: 1008, height: 556 }, field())).toBeGreaterThan(0.54);
  });

  it("出口格在舞台上的位置", () => {
    const stage = { width: 1008, height: 556 };
    const scale = fieldFitScale(stage, field());
    const rects = exitRects(field(), stage, scale);
    expect(rects).toHaveLength(6);
    const east = rects[2]!;
    expect(east.left + east.width).toBeLessThanOrEqual(stage.width + 1);
  });

  it("只有蓋到出口的塊變半透明", () => {
    const stage = { width: 1008, height: 556 };
    const layout = hudLayout(stage.width, stage.height, { mates: 2, narrow: false, collapsed: false });
    // 出口在右上角（小地圖底下）
    const corner = field({ exits: [{ id: "x", cells: [[23, 1]], to: "a", to_name_zh: "某處" }] });
    const faded = fadedBlocks(layout, exitRects(corner, stage, fieldFitScale(stage, corner)));
    // 6F-1 U16：右上整組（地名、小地圖、時間天氣、錢包）不變半透明，出口不畫在小地圖上面
    expect(faded).toEqual([]);
    // 正中間的出口：不擋任何一塊
    const middle = field({ exits: [{ id: "x", cells: [[12, 9]], to: "a", to_name_zh: "某處" }] });
    expect(fadedBlocks(layout, exitRects(middle, stage, fieldFitScale(stage, middle)))).toEqual([]);
    expect(HUD_BLOCKS).toHaveLength(10);
  });
});

/** 某顆鈕（`data-hud=item`）的開頭標籤到 `</button>` 之間的內容。 */
function buttonMarkup(markup: string, item: string): string {
  const at = markup.indexOf(`data-hud="${item}"`);
  if (at < 0) return "";
  const start = markup.lastIndexOf("<button", at);
  return markup.slice(start, markup.indexOf("</button>", at));
}

describe("功能列定稿圖示與說明卡（6A-4f，HUD功能列圖示.md）", () => {
  const layout = hudLayout(1040, 624, { mates: 2, narrow: false, collapsed: false });
  const v = view({ reports: 1 });
  const markup = html(props(v, layout, { openPanel: "bag" }));
  const expected: Record<string, HudBarKey> = { bag: "I", skills: "K", growth: "G", quests: "J", shadow: "Y", notes: "N", sneak: "R" };

  it("7 顆鈕各畫自己的定稿圖示（QI-5：Q 版畫布，功能列鈕 35px × 2）；影子鈕、地圖鈕也用定稿", () => {
    for (const b of HUD_BUTTONS) expect(buttonMarkup(markup, `btn-${b.id}`)).toContain(`data-bar-icon="${expected[b.id]}"`);
    expect(buttonMarkup(markup, "shadow")).toContain('data-bar-icon="Y"');
    expect(buttonMarkup(markup, "map")).toContain('data-bar-icon="M"');
    expect(buttonMarkup(markup, "btn-bag")).toContain('<canvas class="hud-icon hud-bar-icon" width="70" height="70" style="width:35px;height:35px"');
    expect(markup).not.toContain('data-icon="boots"');
  });

  it("QI-5：8 顆對到第⑦批 Q 版圖示；背包＝風格樣張的後背包、潛行＝第④批「隱蔽」的兜帽（同題材直接呼叫）", () => {
    expect(BAR_ICON_ID).toEqual({ I: "bar_I", K: "bar_K", G: "bar_G", J: "bar_J", Y: "bar_Y", N: "bar_N", R: "bar_R", M: "bar_M" });
    for (const k of HUD_BAR_ORDER) expect(HUD_Q_ICON[BAR_ICON_ID[k]]?.grp, k).toBe("bar");
    expect(HUD_Q_ICON.bar_I?.src).toBe("style:hud.bag");
    expect(HUD_Q_ICON.bar_R?.src).toBe("b4:status.concealed");
    expect(buttonMarkup(markup, "btn-sneak")).toContain('data-bar-icon="R"');
  });

  it("按鈕狀態：開著的面板金底、沒有資料開不了的變灰", () => {
    expect(buttonMarkup(markup, "btn-bag")).toContain('data-state="open"');
    expect(buttonMarkup(markup, "btn-skills")).toContain('data-state="normal"');
    const bag = HUD_BUTTONS[0] as (typeof HUD_BUTTONS)[number];
    const empty = { ...v, inventory: null } as unknown as WorldView;
    expect(buttonState(empty, bag, null)).toBe("disabled");
    expect(buttonMarkup(html(props(empty, layout)), "btn-bag")).toContain("world-hud-btn disabled");
  });

  it("每顆都有說明卡：標題列（圖示、名稱、快捷鍵）、黃字狀態、說明一句、觸控小字", () => {
    for (const b of HUD_BUTTONS) {
      const k = expected[b.id] as HudBarKey;
      const card = hudButtonCard(v, b.id);
      expect(card.status).not.toBe("");
      expect(card.desc).not.toBe("");
      const out = renderToStaticMarkup(createElement(HudBarCard, { k, card }));
      expect(out).toContain(`data-hud-card="${k}"`);
      expect(out).toContain(`data-bar-icon="${k}"`);
      expect(out).toContain(`<span class="name">${b.name}</span>`);
      expect(out).toContain(`<span class="key">${k}</span>`);
      expect(out).toContain(card.status);
      expect(out).toContain(HUD_TOUCH_ZH);
    }
    expect(hudButtonCard(v, "quests").status).toBe("進行中 2 條");
    expect(hudButtonCard(v, "sneak").status).toBe("花 1 補給");
  });

  it("圖示的抖動由名字決定：畫兩次一樣", () => {
    const a = renderToStaticMarkup(createElement(HudBarIcon, { k: "I" }));
    const b = renderToStaticMarkup(createElement(HudBarIcon, { k: "I" }));
    expect(a.replace(/hudbar[^"-]*/g, "")).toBe(b.replace(/hudbar[^"-]*/g, ""));
    expect(HUD_BAR_ORDER).toEqual(["I", "K", "G", "J", "Y", "N", "R", "M"]);
  });
});

// ---------------- UI-E2／RT-1 ----------------

describe("UI-E2：主角卡、隊友小卡、彈窗、標題牌（大世界）", () => {
  const layout = hudLayout(1040, 624, { mates: 2, narrow: false, collapsed: false });

  it("主角卡是共用的 HeroCard：頭像＋HP、法力、耐力（細）、經驗；外框有區域四角飾件", () => {
    const markup = html(props(view(), layout));
    expect(markup).toMatch(/class="hero-card rt-frame hero-card-world world-hud-hero"[^>]*data-hero-card="world"/);
    expect(markup).toContain('class="hud-portrait"');
    for (const k of ["hp", "mana", "stamina", "xp"]) expect(count(markup, k)).toBe(1);
    expect(markup).toMatch(/world-hud-bar stamina[^"]*" style="height:5px"/);
  });

  it("隊友小卡改用 portrait.ts 的頭像（傭兵的外觀與出身區；沒有外觀＝剪影），不再是通用臉", () => {
    const v = view();
    const mercs = [
      { id: "merc_qing", portrait: { look: { skin: "fair" }, gear: {}, extras: [] }, origin: "cloud_ridge" },
      { id: "merc_yue", portrait: null, origin: "crystal_crown" },
    ];
    const withRoster = { ...v, party: { ...v.party, mercenaries: mercs } } as unknown as WorldView;
    const cards = mateCards(withRoster);
    expect(cards.map((m) => m.origin)).toEqual(["cloud_ridge", "crystal_crown"]);
    expect(cards[0]?.portrait).toEqual(mercs[0]?.portrait);
    expect(cards[1]?.portrait).toBeNull();
    const markup = html(props(withRoster, layout));
    const mates = markup.slice(markup.indexOf('data-hud="party"'), markup.indexOf('data-hud-block="shadow"'));
    expect(mates.split('class="story-portrait"').length - 1).toBe(2);
    expect(mates).toContain('data-portrait="doll"');
    expect(mates).toContain('data-portrait="silhouette"');
    expect(mates).not.toContain("hud-portrait");
    // 名冊裡找不到（舊存檔、影子）時也不會壞：剪影＋金框
    expect(mateCards(v).map((m) => [m.portrait, m.origin])).toEqual([
      [null, "merc"],
      [null, "merc"],
    ]);
  });

  it("面板是共用彈窗：位置照 6F-3（上緣在主角卡下、讓出左右欄），內容在 .ui-popup-body 裡捲", () => {
    const markup = html(props(view(), layout, { panel: createElement("div", null, "背包內容"), openPanel: "bag" }));
    const box = popupBox(layout, 720);
    expect(markup).toMatch(/class="ui-popup rt-frame ui-popup-hud world-hud-panel"/);
    expect(markup).toContain(`top:${box.top}px`);
    expect(markup).toContain(`max-height:${box.maxHeight}px`);
    expect(markup).toMatch(/<div class="ui-popup-body"><button[^>]*world-hud-panel-close/);
    expect(markup).toContain('data-panel="bag"');
  });

  it("地名是區域標題牌（材質、內框細線由 --rt-plaque-*、--rt-accent 決定）；小地圖、任務、功能列有四角飾件", () => {
    const markup = html(props(view(), layout));
    expect(markup).toContain('class="world-hud-place rt-plaque"');
    expect(markup).toContain('class="world-hud-minimap rt-frame"');
    expect(markup).toContain('class="world-hud-tracker rt-frame"');
    expect(markup).toContain('class="world-hud-funcs rt-frame"');
  });
});

describe("OB-6c 窄版任務欄收合時的重選提醒點", () => {
  const layout = hudLayout(800, 520, { mates: 2, narrow: true, collapsed: true });
  const withReselect = (windowOpen: boolean): WorldView =>
    ({ ...view(), opening: { reselect: { window_open: windowOpen, before_level: 4, place_zh: "回葛蘭所在的霧渡鎮" } } }) as unknown as WorldView;
  /** 收合鈕（`data-hud="tracker"` 那顆 button）的 HTML。 */
  const foldButton = (markup: string): string => {
    const m = /<button[^>]*data-hud="tracker"[^>]*>[\s\S]*?<\/button>/.exec(markup);
    return m === null ? "" : m[0];
  };

  it("有資格且收合：收合鈕右上有通知點（沿用功能列的 world-hud-dot red），滑過寫「4 級前可重選一次」", () => {
    const btn = foldButton(html(props(withReselect(true), layout, { trackerCollapsed: true })));
    expect(btn).toContain('class="world-hud-dot red"');
    expect(btn).toMatch(/aria-label="4 級前可重選一次。任務追蹤/);
    expect(trackerFoldDot({ window_open: true, before_level: 4 } as never, true)).toBe("4 級前可重選一次");
  });

  it("沒資格或展開：沒有點", () => {
    const closed = foldButton(html(props(withReselect(false), layout, { trackerCollapsed: true })));
    expect(closed).not.toBe("");
    expect(closed).not.toContain("world-hud-dot");
    expect(closed).not.toContain("可重選");
    const none = foldButton(html(props(view(), layout, { trackerCollapsed: true })));
    expect(none).not.toContain("world-hud-dot");
    const open = html(props(withReselect(true), layout, { trackerCollapsed: false }));
    expect(foldButton(open)).toBe("");
    expect(open).toContain('data-testid="world-hud-reselect"');
    expect(trackerFoldDot({ window_open: true, before_level: 4 } as never, false)).toBeNull();
    expect(trackerFoldDot({ window_open: false, before_level: 4 } as never, true)).toBeNull();
    expect(trackerFoldDot(null, true)).toBeNull();
  });
});
