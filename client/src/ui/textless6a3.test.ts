// Phase 6A-3（去文字化④）：HP／法力／護盾說明句、釘選小卡精簡版、戰鬥紀錄浮動提示與釘選、操作說明句只出現前 3 次。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Action } from "../api/types";
import type { LogLine } from "../battle/log";
import { liveToasts, nextToastChange, stampArrivals, TOAST_FADE_MS, TOAST_MAX, TOAST_TTL_MS } from "../battle/logToasts";
import {
  bumpOpHint,
  opHintCount,
  opHintFullOnce,
  OP_HINT_LIMIT,
  OP_HINTS_KEY,
  readOpHintCounts,
  resetOpHints,
  showOpHint,
  type HintStore,
} from "../battle/opHints";
import { actionHintKind } from "../battle/skillTray";
import { emptyTargets, type ActionMode } from "../battle/targeting";
import { smallView, unit } from "../battle/testFixtures";
import type { UnitNames } from "../battle/units";
import { ModePanel, modeHintKind } from "./ActionPanel";
import { BattleLogDockView } from "./BattleLogDock";
import { Hud } from "./Hud";
import { OpHintReset } from "./LayoutPanel";
import { OpHint, OpHintView } from "./OpHint";
import { UnitInfo } from "./UnitInfo";
import { barData, pinnedCompact, PIN_COMPACT_WIDTH, RESOURCE_TEXT, unitChips } from "./statusCard";

const names: UnitNames = { name: (id) => id, marker: (id) => id.slice(-1) } as UnitNames;

const hero = unit("unit_0001", "ally", 0, 2, {
  name_zh: "主角",
  hp: 41,
  max_hp: 50,
  shield: 5,
  mana: 18,
  max_mana: 30,
  stamina: 6,
  max_stamina: 8,
});
const foe = unit("unit_0002", "enemy", 1, 1, {
  name_zh: "斷崖幫刀手",
  hp: 30,
  max_hp: 42,
  stamina: 6,
  max_stamina: 8,
  mana: 4,
  max_mana: 10,
  shield: 3,
  weapon_name_zh: "鬼頭刀",
  tags: ["elite"],
  traits_zh: ["精英詞綴「狂暴」：HP 低於一半時傷害 +2。"],
});

describe("HP、法力、護盾的說明句（玩法 PM 給的文字，一字不改）", () => {
  it("三句原文", () => {
    expect(RESOURCE_TEXT.hp).toBe("生命值，歸零就會倒下；靠治療、藥水或營火回復。");
    expect(RESOURCE_TEXT.mana).toBe("施放法術要花法力，戰鬥中不會自然回復；在營火或城鎮回滿。");
    expect(RESOURCE_TEXT.shield).toBe("受到傷害時先扣護盾、再扣生命值；時間到就消失，重複獲得只保留較大的一層。");
  });
  it("主角卡：HP 條（有護盾時加護盾句）、法力條", () => {
    expect(barData("hp", hero).hint.split("\n")).toEqual(["HP 41 / 50", RESOURCE_TEXT.hp, "護盾 5", RESOURCE_TEXT.shield]);
    expect(barData("hp", { ...hero, shield: 0 }).hint.split("\n")).toEqual(["HP 41 / 50", RESOURCE_TEXT.hp]);
    expect(barData("mana", hero).hint.split("\n")).toEqual(["法力 18 / 30", RESOURCE_TEXT.mana]);
    const html = renderToStaticMarkup(createElement(Hud, { view: { ...smallView(), units: [hero] }, hero, skills: {} }));
    expect(html).toContain('aria-label="HP 41 / 50"');
  });
  it("單位小卡共用同一份文字：HP 條、護盾與法力圖示", () => {
    expect(barData("hp", foe).hint).toContain(RESOURCE_TEXT.hp);
    const chips = unitChips(foe);
    expect(chips.find((c) => c.key === "shield")?.hint).toBe(`護盾 3\n${RESOURCE_TEXT.shield}`);
    expect(chips.find((c) => c.key === "mana")?.hint).toBe(`法力 4 / 10\n${RESOURCE_TEXT.mana}`);
  });
});

describe("釘選小卡：視窗不到 1000 寬收成精簡版", () => {
  it("門檻 1000；滑過（展開）時不收", () => {
    expect(PIN_COMPACT_WIDTH).toBe(1000);
    expect(pinnedCompact(800, false)).toBe(true);
    expect(pinnedCompact(999, false)).toBe(true);
    expect(pinnedCompact(1000, false)).toBe(false);
    expect(pinnedCompact(1600, false)).toBe(false);
    expect(pinnedCompact(800, true)).toBe(false);
  });
  const props = { unit: foe, names, heroId: "unit_0001", skills: {}, view: { ...smallView(), units: [hero, foe] }, pinned: true, onTogglePin: () => {} };
  it("精簡版只留名稱、HP 條、耐力條（與圖釘）", () => {
    const html = renderToStaticMarkup(createElement(UnitInfo, { ...props, compact: true }));
    expect(html).toContain("斷崖幫刀手");
    expect([...html.matchAll(/class="stat-bar (\w+)"/g)].map((m) => m[1])).toEqual(["hp", "stamina"]);
    expect(html).toContain("unit-pin");
    expect(html).not.toContain("hud-icons");
    expect(html).not.toContain("unit-details");
    expect(html).not.toContain("affix-badge");
    expect(html).not.toContain("鬼頭刀");
  });
  it("完整版照舊有圖示、詞綴徽章與「詳細」", () => {
    const html = renderToStaticMarkup(createElement(UnitInfo, { ...props, compact: false }));
    expect(html).toContain("hud-icons");
    expect(html).toContain("unit-details");
    expect(html).toContain("affix-badge");
  });
});

const line = (seq: number, over: Partial<LogLine> = {}): LogLine => ({
  seq,
  round: 1,
  text: `第 ${seq} 行（擲骰 d20=12）`,
  summary: `第 ${seq} 行`,
  type: "damage_dealt",
  unitIds: [],
  tiles: [],
  ...over,
});

describe("戰鬥紀錄：預設收成左下 2～3 條浮動提示，舊的淡出", () => {
  const lines = [line(1), line(2), line(3), line(4), line(5)];
  it("最多 3 條，取最新的，舊的在上；顯示精簡文字", () => {
    const arrivals = stampArrivals(new Map(), lines, 1000);
    const toasts = liveToasts(lines, arrivals, 1000);
    expect(TOAST_MAX).toBe(3);
    expect(toasts.map((t) => t.seq)).toEqual([3, 4, 5]);
    expect(toasts.every((t) => !t.fading)).toBe(true);
  });
  it("約 6 秒淡出：最後 1 秒標 fading，過了就不畫；下一次變化的時間", () => {
    expect(TOAST_TTL_MS).toBe(6000);
    const a = stampArrivals(new Map(), [line(1)], 0);
    const b = stampArrivals(a, [line(1), line(2)], 3000);
    expect(liveToasts([line(1), line(2)], b, 5200).map((t) => [t.seq, t.fading])).toEqual([
      [1, true],
      [2, false],
    ]);
    expect(nextToastChange(liveToasts([line(1), line(2)], b, 5200), b, 5200)).toBe(800);
    expect(liveToasts([line(1), line(2)], b, 6000).map((t) => t.seq)).toEqual([2]);
    expect(liveToasts([line(1), line(2)], b, 9000 + TOAST_FADE_MS)).toEqual([]);
  });
  it("剛進戰鬥已有的紀錄、補在前面的舊紀錄不冒提示；回合分隔不算提示", () => {
    const old = stampArrivals(new Map(), [line(1), line(2)], 0, true);
    expect(liveToasts([line(1), line(2)], old, 10)).toEqual([]);
    const later = stampArrivals(old, [line(0), line(1), line(2), line(3)], 100);
    expect(liveToasts([line(0), line(1), line(2), line(3)], later, 200).map((t) => t.seq)).toEqual([3]);
    const turn = [line(4), line(5, { type: "turn_started", text: "—— 主角的回合" })];
    expect(liveToasts(turn, stampArrivals(new Map(), turn, 0), 0).map((t) => t.seq)).toEqual([4]);
  });
  const toasts = liveToasts(lines, stampArrivals(new Map(), lines, 0), 0);
  const view = (open: boolean, pinned: boolean) =>
    renderToStaticMarkup(
      createElement(BattleLogDockView, {
        toasts,
        open,
        pinned,
        onToggleOpen: () => {},
        onTogglePin: () => {},
        log: (actions) => createElement("div", { className: "full-log" }, "完整紀錄", actions),
      }),
    );
  it("收起時：浮動提示＋紀錄圖示，沒有完整清單", () => {
    const html = view(false, false);
    expect(html.match(/data-testid="log-toast"/g)?.length).toBe(3);
    expect(html).toContain("第 5 行");
    expect(html).not.toContain("擲骰 d20");
    expect(html).toContain('class="log-dock-icon"');
    expect(html).toContain('aria-expanded="false"');
    expect(html).not.toContain("full-log");
  });
  it("點圖示展開：完整清單與圖釘，浮動提示不畫", () => {
    const html = view(true, false);
    expect(html).toContain("full-log");
    expect(html).not.toContain("log-toast");
    expect(html).toContain('aria-expanded="true"');
    expect(html).toMatch(/class="log-pin"[^>]*aria-pressed="false"/);
  });
  it("釘住：一直顯示完整清單，圖釘亮", () => {
    const html = view(true, true);
    expect(html).toContain("log-dock open pinned");
    expect(html).toMatch(/class="log-pin on"[^>]*aria-pressed="true"/);
  });
});

function memoryStore(): HintStore & { map: Map<string, string> } {
  const map = new Map<string, string>();
  return {
    map,
    getItem: (k) => map.get(k) ?? null,
    setItem: (k, v) => void map.set(k, v),
    removeItem: (k) => void map.delete(k),
  };
}

describe("操作說明句：每種只在前 3 次出現，次數記在本機", () => {
  it("前 3 次顯示，第 4 次起收進「?」；種類分開計數", () => {
    const s = memoryStore();
    expect(OP_HINT_LIMIT).toBe(3);
    for (let i = 0; i < 3; i += 1) {
      expect(showOpHint("target", s)).toBe(true);
      bumpOpHint("target", s);
    }
    expect(opHintCount("target", s)).toBe(3);
    expect(showOpHint("target", s)).toBe(false);
    expect(showOpHint("vault", s)).toBe(true);
    expect(JSON.parse(s.map.get(OP_HINTS_KEY) ?? "{}")).toEqual({ target: 3 });
  });
  it("讀寫失敗或格式不對時當作 0 次，照常顯示", () => {
    const broken: HintStore = {
      getItem: () => {
        throw new Error("blocked");
      },
      setItem: () => {
        throw new Error("blocked");
      },
      removeItem: () => {
        throw new Error("blocked");
      },
    };
    expect(showOpHint("target", broken)).toBe(true);
    expect(() => bumpOpHint("target", broken)).not.toThrow();
    expect(() => resetOpHints(broken)).not.toThrow();
    expect(showOpHint("target", null)).toBe(true);
    const bad = memoryStore();
    bad.map.set(OP_HINTS_KEY, "{not json");
    expect(readOpHintCounts(bad)).toEqual({});
    bad.map.set(OP_HINTS_KEY, JSON.stringify({ target: "x", vault: 5 }));
    expect(readOpHintCounts(bad)).toEqual({ vault: 5 });
  });
  it("「?」：完整句子不畫，滑過或點一下的說明卡（PartTip，可點）裡才有", () => {
    expect(renderToStaticMarkup(createElement(OpHintView, { full: true, label: "火焰爆", text: "點選格子上的目標。Esc／右鍵取消。" }))).toContain(
      "點選格子上的目標。Esc／右鍵取消。",
    );
    const q = renderToStaticMarkup(createElement(OpHintView, { full: false, label: "火焰爆", text: "點選格子上的目標。Esc／右鍵取消。" }));
    expect(q).toContain('data-testid="op-hint-q"');
    expect(q).toContain('role="button"');
    expect(q).toContain('aria-label="操作說明：火焰爆"');
    expect(q).not.toContain("Esc／右鍵取消");
  });
  it("設定裡的「重新顯示操作說明」清掉次數", () => {
    const s = memoryStore();
    for (let i = 0; i < 4; i += 1) bumpOpHint("order", s);
    expect(showOpHint("order", s)).toBe(false);
    resetOpHints(s);
    expect(showOpHint("order", s)).toBe(true);
    expect(renderToStaticMarkup(createElement(OpHintReset))).toContain("重新顯示操作說明");
  });
});

describe("選取面板的說明句接上次數（localStorage）", () => {
  const mem = memoryStore();
  beforeEach(() => {
    mem.map.clear();
    vi.stubGlobal("localStorage", mem);
  });
  afterEach(() => vi.unstubAllGlobals());
  const target = { units: new Map([["unit_0002", { kind: "skill" } as unknown as Action]]) };
  const mode: ActionMode = {
    key: "skill:fire",
    kind: "skill",
    label: "火焰爆",
    skillId: "fire",
    actions: [],
    targets: { ...emptyTargets(), ...target },
  };
  const panel = () =>
    renderToStaticMarkup(
      createElement(ModePanel, {
        enabled: true,
        mode,
        hurlPick: null,
        onHurlReset: () => {},
        preview: null,
        view: smallView(),
        interactOptions: [],
        names,
        legend: [],
        orderHint: null,
        onProtectHero: null,
        cancellable: true,
        onCancel: () => {},
        onAction: () => {},
        onPreviewAction: () => {},
      }),
    );
  it("次數未滿 3：照常寫出句子；滿 3 次：只剩「?」", () => {
    expect(modeHintKind(mode)).toBe("target");
    expect(panel()).toContain("Esc／右鍵取消");
    mem.map.set(OP_HINTS_KEY, JSON.stringify({ target: 3 }));
    const html = panel();
    expect(html).not.toContain("Esc／右鍵取消");
    expect(html).toContain('data-testid="op-hint-q"');
    expect(html).toContain("火焰爆");
  });
  it("技能列上方的移動說明：同一輪只算一次，第 4 輪起收進「?」；狀態句不算", () => {
    const base = { copying: false, canAct: true, ended: false, moveCount: 5, attackCount: 1 };
    expect(actionHintKind(base)).toBe("move");
    expect(actionHintKind({ ...base, copying: true })).toBe("copy");
    expect(actionHintKind({ ...base, canAct: false })).toBeNull();
    expect(actionHintKind({ ...base, ended: true })).toBeNull();
    expect(actionHintKind({ ...base, summonIdle: true })).toBeNull();
    const s = memoryStore();
    resetOpHints(s);
    for (const round of [1, 1, 2, 2, 3]) expect(opHintFullOnce("move", `b1:${round}`, s)).toBe(true);
    expect(opHintCount("move", s)).toBe(3);
    expect(opHintFullOnce("move", "b1:4", s)).toBe(false);
    expect(opHintFullOnce("move", "b1:4", s)).toBe(false);
    expect(opHintCount("move", s)).toBe(3);
    resetOpHints(s);
    expect(opHintFullOnce("move", "b1:4", s)).toBe(true);
  });
  it("OpHint 元件直接用：別種說明句不受影響", () => {
    mem.map.set(OP_HINTS_KEY, JSON.stringify({ target: 3 }));
    const html = renderToStaticMarkup(createElement(OpHint, { kind: "vault", token: "vault", label: "攀跳", text: "點選紫色格子。" }));
    expect(html).toContain("點選紫色格子。");
  });
});
