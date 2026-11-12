// LW-2：隊伍與影子面板的獨狼出城前提示（06 6.37「提示與標灰」）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { WorldLoneWolf, WorldMyShadow, WorldPartyView, WorldView } from "../api/types";
import { PartyShadowPanel, partyShadowTabs } from "./PartyShadowPanel";
import { LONE_WOLF_ZH, loneWolfHint } from "./partyShadow";

const html = (el: Parameters<typeof renderToStaticMarkup>[0]) => renderToStaticMarkup(el);
const noop = () => undefined;

function party(n: number, lone: WorldLoneWolf | null): WorldPartyView {
  const members = [
    { name_zh: "AA", title_zh: "主角", level: 2, mercenary: null },
    { name_zh: "賽倫", title_zh: "盾衛・守護", level: 2, mercenary: "merc_tiebi", ai_zh: "預設（守衛）" },
  ].slice(0, n);
  return { members, max_hired: 2, can_hire: true, hire_problem_zh: null, mercenaries: [], shadows: [], ai_choices: [], ai: {}, season_boss_ok: true, free_slots: 2, lone_wolf: lone } as WorldPartyView;
}
const SHADOW = { saved: true, saved_zh: "霧渡鎮・Lv 3", ai_zh: "預設", can_set_ai: false, coins: 0, reports_zh: [] } as WorldMyShadow;
const view = (p: WorldPartyView) => ({ character: { hero_look: null, origin_realm: null }, field: null, party: p, my_shadow: SHADOW }) as unknown as WorldView;

const OFF: WorldLoneWolf = { ok: false, skills_zh: ["孤狼撲擊", "獨行者"], affixes_zh: ["皮甲的「獨行的」"] };
const ON: WorldLoneWolf = { ok: true, skills_zh: ["獨行者"], affixes_zh: [] };

describe("loneWolfHint", () => {
  it("沒帶獨狼技能或詞條＝沒有提示", () => {
    expect(loneWolfHint(null)).toBeNull();
    expect(loneWolfHint(undefined)).toBeNull();
    expect(loneWolfHint({ ok: true, skills_zh: [], affixes_zh: [] })).toBeNull();
  });
  it("帶隊友＝警告：技能與詞條都列出", () => {
    expect(loneWolfHint(OFF)).toEqual({ tone: "warn", text: LONE_WOLF_ZH.off, list: "用不出來：孤狼撲擊、獨行者、皮甲的「獨行的」", note: null });
  });
  it("獨行＝資訊：多一句護送／守點例外", () => {
    expect(loneWolfHint(ON)).toEqual({ tone: "info", text: LONE_WOLF_ZH.on, list: "會生效：獨行者", note: LONE_WOLF_ZH.escort });
  });
});

describe("隊伍分頁與我的影子分頁", () => {
  it("帶隊友：琥珀提示「帶隊友出城，獨狼技能不會生效」", () => {
    const out = html(createElement(PartyShadowPanel, { view: view(party(2, OFF)), busy: false, onAct: noop }));
    expect(out).toMatch(/pnl-callout warn"[^>]*data-testid="world-party-lone-wolf"[^]*<b>獨狼<\/b>：帶隊友出城，獨狼技能不會生效[^]*用不出來：孤狼撲擊、獨行者、皮甲的「獨行的」/);
  });
  it("獨行：青色資訊提示＋例外小字", () => {
    const out = html(createElement(PartyShadowPanel, { view: view(party(1, ON)), busy: false, onAct: noop }));
    expect(out).toMatch(/pnl-callout info"[^>]*data-testid="world-party-lone-wolf"[^]*只帶主角出城，獨狼技能會生效[^]*world-party-lone-note">（護送、守點戰開場就有 NPC 同行時不成立）/);
  });
  it("沒帶：不畫提示（舊回應沒有 lone_wolf 欄位也一樣）", () => {
    expect(html(createElement(PartyShadowPanel, { view: view(party(2, null)), busy: false, onAct: noop }))).not.toContain("world-party-lone-wolf");
    const old = { ...party(2, null) } as Partial<WorldPartyView>;
    delete old.lone_wolf;
    expect(html(createElement(PartyShadowPanel, { view: view(old as WorldPartyView), busy: false, onAct: noop }))).not.toContain("lone-wolf");
  });
  it("我的影子分頁：帶獨狼技能時提示「獨狼技能在影子裡用不出來」；沒帶不提示", () => {
    const pane = (p: WorldPartyView) => html(partyShadowTabs(view(p), false, noop).find((t) => t.id === "shadow")!.render() as Parameters<typeof renderToStaticMarkup>[0]);
    expect(pane(party(1, ON))).toMatch(/data-testid="world-shadow-lone-wolf"[^]*獨狼技能在影子裡用不出來/);
    expect(pane(party(1, null))).not.toContain("world-shadow-lone-wolf");
  });
});
