// Phase 6A-2（去文字化③）：主角狀態卡與單位小卡——三條同粗寫字、耐力徽章拿掉、說明卡內容、詞綴徽章、釘選。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { BattleView, StatusView } from "../api/types";
import { actionCardText } from "../battle/actionInfo";
import { smallView, tile, unit } from "../battle/testFixtures";
import type { UnitNames } from "../battle/units";
import { Hud } from "./Hud";
import { UnitInfo } from "./UnitInfo";
import {
  affixBadges,
  barData,
  barFill,
  heroChips,
  pinnedUnitOf,
  reactionChip,
  sourceChip,
  statusCorner,
  togglePin,
  unitChips,
} from "./statusCard";

// 沒有 @types/node：同 render/fontLoad.test.ts，用變數名載入 node:fs（CSS 的 ?raw 在 vitest 是空字串）。
const nodeFs = "node:fs";
const { readFileSync } = (await import(/* @vite-ignore */ nodeFs)) as { readFileSync: (p: string, enc: string) => string };

const status = (over: Partial<StatusView> = {}): StatusView =>
  ({ status_id: "burning", remaining: 2, amount: null, source_id: null, cost_status: false, ...over }) as StatusView;

const hero = unit("unit_0001", "ally", 0, 2, {
  name_zh: "主角",
  hp: 41,
  max_hp: 50,
  shield: 5,
  mana: 18,
  max_mana: 30,
  stamina: 6,
  max_stamina: 8,
  ap: 3,
  move_points: 3,
  source: 1,
  source_max: 3,
  statuses: [status()],
  stacks: { static_charge: 2 },
  cooldowns: { skill_x: 1 },
});

const ELITE_LINE = "精英詞綴「狂暴」：HP 低於一半時傷害 +2。";
const elite = unit("unit_0002", "enemy", 1, 1, {
  name_zh: "狂暴的斷崖幫刀手",
  hp: 30,
  max_hp: 42,
  stamina: 6,
  max_stamina: 8,
  mana: 4,
  max_mana: 10,
  shield: 5,
  weapon_name_zh: "鬼頭刀",
  weapon_traits_zh: ["斬擊", "雙手"],
  tags: ["elite"],
  traits_zh: [ELITE_LINE, "被動「刀勢」：連續攻擊同一目標時傷害 +1。"],
  statuses: [status({ remaining: 1 })],
});

const view = (): BattleView => {
  const v = smallView();
  return { ...v, units: [hero, elite] };
};
const names: UnitNames = { name: (id) => id, marker: (id) => id.slice(-1) } as UnitNames;

const bars = (html: string) => [...html.matchAll(/class="stat-bar (\w+)"[^>]*aria-label="([^"]+)"/g)].map((m) => [m[1], m[2]]);

describe("主角狀態卡：三條一樣粗、條上寫字", () => {
  const html = renderToStaticMarkup(createElement(Hud, { view: view(), hero, skills: {} }));
  it("HP、法力、耐力三條，條上寫「名稱 現值 / 上限」", () => {
    expect(bars(html)).toEqual([
      ["hp", "HP 41 / 50"],
      ["mana", "法力 18 / 30"],
      ["stamina", "耐力 6 / 8"],
    ]);
    expect(html).toContain(">HP 41 / 50<");
    expect(html).toContain(">耐力 6 / 8<");
  });
  it("三條用同一個高度（CSS 只在 .stat-bar 設高度，各色沒有另設）", () => {
    const css = readFileSync("src/styles/status-card.css", "utf-8");
    const heights = [...css.matchAll(/([^{}]+)\{[^}]*\bheight:\s*16px/g)].map((m) => (m[1] ?? "").trim());
    expect(heights).toContain(".stat-bar");
    for (const kind of ["hp", "mana", "stamina"]) {
      const rule = new RegExp(`\\.stat-bar\\.${kind}[^{]*\\{([^}]*)\\}`, "g");
      for (const m of css.matchAll(rule)) expect(m[1]).not.toMatch(/\bheight/);
    }
    expect(css).toContain("#e04a3a");
    expect(css).toContain("#4a8ae0");
    expect(css).toContain("#c8a030");
  });
  it("原本的耐力徽章（hud-chip、「耐力」字樣的晶片）拿掉了；冷卻不重複列", () => {
    expect(html).not.toContain("hud-chip");
    expect(html).not.toContain("hud-bar-value");
    expect(html).not.toContain("冷卻");
  });
  it("護盾疊在 HP 條上（淺藍一段），數字只在說明卡", () => {
    expect(html).toContain("stat-bar-shield");
    expect(html).not.toContain("護盾 5");
    expect(barData("hp", hero).hint).toBe("HP 41 / 50\n護盾 5");
    expect(barFill(41, 50, 5)).toEqual({ fill: 0.82, shieldLeft: 0.82, shieldWidth: 0.1 });
    expect(barFill(48, 50, 5).shieldLeft).toBeCloseTo(0.9);
  });
  it("下面一排：AP 圓點、移動、反應、源力 3 點、狀態（右下角回合）、層數、腳下表面", () => {
    expect(heroChips(hero).map((c) => c.key)).toEqual(["ap", "move", "reaction", "source"]);
    expect(heroChips(hero)[0]?.pips).toEqual([true, true, true]);
    expect(sourceChip(hero).pips).toEqual([true, false, false]);
    expect(html).toContain('class="part-tip stat-badge status-badge"');
    expect(html).toContain('<b class="stat-corner">2</b>');
    expect(html).toContain('data-stack="static_charge"');
    expect(html).toContain("surface-badge");
  });
  it("反應用過變灰", () => {
    expect(reactionChip(hero).dim).toBe(false);
    expect(reactionChip({ ...hero, reaction_available: false })).toMatchObject({ dim: true, hint: "反應 已用\n本輪還能反應嗎" });
  });
  it("窄螢幕也是條＋圖示（不再是一行字）", () => {
    const compact = renderToStaticMarkup(createElement(Hud, { view: view(), hero, skills: {}, compact: true }));
    expect(bars(compact)).toHaveLength(3);
    expect(compact).toContain("hud-icons");
  });
});

describe("說明卡：名稱、現值、一句說明（用現有文字）", () => {
  it("耐力條：「耐力 6 / 8」＋耐力的動作說明", () => {
    const hint = barData("stamina", hero).hint;
    expect(hint.split("\n")[0]).toBe("耐力 6 / 8");
    expect(hint).toContain(actionCardText("stamina") ?? "?");
  });
  it("AP、移動、源力用 HUD 原本的提示句與移動的動作說明", () => {
    const [ap, move] = heroChips(hero);
    expect(ap?.hint).toBe("AP 3\n剩餘行動點數（自己的回合已含上回合保留的 AP）");
    expect(move?.hint).toContain("移動 3\n剩餘移動點數");
    expect(move?.hint).toContain(actionCardText("move") ?? "?");
    expect(sourceChip(hero).hint).toContain("源力 1/3：傳說技能的代價");
  });
  it("武器：名稱＋武器特性", () => {
    expect(unitChips(elite).find((c) => c.key === "weapon")?.hint).toBe("武器 鬼頭刀\n斬擊\n雙手");
  });
  it("狀態右下角：剩餘回合；沒有回合寫數值；都沒有不寫", () => {
    expect(statusCorner(status({ remaining: 3 }))).toBe("3");
    expect(statusCorner(status({ remaining: null, amount: 4 }))).toBe("4");
    expect(statusCorner(status({ remaining: null, amount: null }))).toBe("");
  });
});

describe("單位小卡", () => {
  const html = renderToStaticMarkup(
    createElement(UnitInfo, { unit: elite, names, heroId: hero.id, skills: {}, view: view(), onTogglePin: () => undefined }),
  );
  it("HP 條與耐力條，和主角卡同一個元件（一樣粗、寫字）", () => {
    expect(bars(html)).toEqual([
      ["hp", "HP 30 / 42"],
      ["stamina", "耐力 6 / 8"],
    ]);
  });
  it("圖示＋數字：護盾、法力、AP、移動、武器", () => {
    expect(unitChips(elite).map((c) => [c.key, c.label])).toEqual([
      ["shield", "5"],
      ["mana", "4"],
      ["ap", "2"],
      ["move", "4"],
      ["weapon", "鬼頭刀"],
    ]);
    expect(unitChips({ ...elite, shield: 0, max_mana: 0 }).map((c) => c.key)).toEqual(["ap", "move", "weapon"]);
  });
  it("精英詞綴的金色徽章，說明是特性欄那一句", () => {
    expect(affixBadges(elite)).toEqual([{ label: "狂暴", hint: ELITE_LINE }]);
    expect(html).toContain('data-testid="affix-badge"');
    expect(html).toContain("◆ 狂暴");
    expect(affixBadges({ ...elite, traits_zh: [] })).toEqual([{ label: "精英", hint: "精英" }]);
    expect(affixBadges(hero)).toEqual([]);
  });
  it("特性與詞綴說明收在「詳細」裡；朝向不寫字", () => {
    const details = html.slice(html.indexOf('<details class="unit-details"'));
    expect(details).toContain("<summary>詳細</summary>");
    expect(details).toContain("刀勢");
    expect(html.slice(0, html.indexOf("<details"))).not.toContain("刀勢");
    expect(html).not.toContain("朝向");
  });
  it("狀態圖示加回合數、腳下表面", () => {
    const onOil = { ...elite, pos: { x: 0, y: 2 } };
    const v = { ...view(), tiles: [...view().tiles.filter((t) => !(t.x === 0 && t.y === 2)), tile(0, 2, { surface: "oil", surface_remaining: 2 })] };
    const out = renderToStaticMarkup(createElement(UnitInfo, { unit: onOil, names, heroId: hero.id, skills: {}, view: v }));
    expect(out).toContain('<b class="stat-corner">1</b>');
    expect(out).toContain("surface-badge");
    expect(out).toContain('aria-label="腳下表面：油（2 輪）"');
  });
});

describe("釘選", () => {
  it("圖釘按鈕：沒釘「釘選」、釘住「取消釘選」；沒有 onTogglePin 時不畫", () => {
    const off = renderToStaticMarkup(createElement(UnitInfo, { unit: elite, names, heroId: hero.id, skills: {}, onTogglePin: () => undefined }));
    expect(off).toContain('aria-pressed="false"');
    expect(off).toContain('aria-label="釘選"');
    const on = renderToStaticMarkup(createElement(UnitInfo, { unit: elite, names, heroId: hero.id, skills: {}, pinned: true, onTogglePin: () => undefined }));
    expect(on).toContain('aria-pressed="true"');
    expect(on).toContain("unit-card pinned");
    const none = renderToStaticMarkup(createElement(UnitInfo, { unit: elite, names, heroId: hero.id, skills: {} }));
    expect(none).not.toContain("unit-pin");
  });
  it("點同一個取消、點別的改釘；同時一張", () => {
    expect(togglePin(null, "a")).toBe("a");
    expect(togglePin("a", "a")).toBeNull();
    expect(togglePin("a", "b")).toBe("b");
  });
  it("釘住的小卡跟著單位（不是格子）：單位移動、敵人回合播放中都用畫面上的視圖；不在戰場就不畫", () => {
    const moved = { ...view(), units: [hero, { ...elite, pos: { x: 2, y: 2 }, hp: 12 }] };
    expect(pinnedUnitOf(moved, elite.id)).toMatchObject({ pos: { x: 2, y: 2 }, hp: 12 });
    expect(pinnedUnitOf({ ...moved, units: [hero] }, elite.id)).toBeNull();
    expect(pinnedUnitOf(moved, null)).toBeNull();
  });
});
