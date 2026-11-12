// FL-1c（06 6.34「費用方向」第 7 點）：沒有任何閃現選項的招，閃現面板整列標灰、不能按，灰字「這招目前沒有可以閃的變化」。
// 伺服器事先算好（`SkillFlash.flash_available`；false 時 `can_flash` 也是 false、`flash_problem_zh` 同一句）。
// 一輪（`FlashSection`）與大世界成長面板（`WorldGrowth` 的靈感閃現分頁）都要。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { RunHero, RunResponse, WorldView } from "../api/types";
import campfire from "../run/fixtures/run_campfire.json";
import { FlashSection, flashRowState } from "../run/FlashSection";
import { NO_FLASH_OPTIONS_TEXT, noFlashOptions, showCanFlash } from "../run/flash";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { WorldGrowth } from "./WorldGrowth";

const CAMPFIRE = campfire as unknown as RunResponse;
const noop = async () => null;
const html = (el: ReturnType<typeof createElement>) => renderToStaticMarkup(el);

/** 營火 fixture 的主角，第 3 招（原本可以閃）改成伺服器算過「沒有選項」。 */
function heroWithNone(): { hero: RunHero; none: string; ok: string } {
  const base = CAMPFIRE.hero;
  const flash = base.flash ?? [];
  const none = flash[2]!.skill_id;
  const ok = flash[3]!.skill_id;
  const hero: RunHero = {
    ...base,
    insight: 3,
    flash: flash.map((f) => (f.skill_id === none ? { ...f, can_flash: false, flash_available: false, flash_problem_zh: NO_FLASH_OPTIONS_TEXT } : f)),
  };
  return { hero, none, ok };
}

function worldView(hero: RunHero): WorldView {
  return {
    character: { character_id: "c1", level: 5, attribute_points: 0, race: "human", look: {}, look_change_zh: null, free_race_change: false, free_race_change_zh: null, hero_look: null, origin_realm: null },
    field: null,
    hero,
    limits: {},
    growth: { insight: 3, skill_tier: 1, at_service: true, service_zh: "", can_allocate: false, can_spend: true, blocked_zh: null, pending: false, can_flash: true, flash_blocked_zh: null, starter_note_zh: null },
    oath: { available: false, unavailable_zh: "尚未開放", current: null, cooldown_until: 0, cooldown_zh: null, can_swear: false, swear_problem_zh: "尚未開放", can_release: false, templates: [] },
  } as unknown as WorldView;
}

/** 某一招那一列（`<li>`…`</li>`）。 */
function rowOf(markup: string, skillId: string): string {
  const at = markup.indexOf(`data-testid="flash-open-${skillId}"`);
  expect(at).toBeGreaterThan(-1);
  // 卡片內也有 <li>（效果清單），所以找列本身的 class 開頭
  const start = Math.max(markup.lastIndexOf('<li class="flash-skill-row', at), markup.lastIndexOf('<li class="pnl-row', at));
  expect(start).toBeGreaterThan(-1);
  return markup.slice(start, markup.indexOf("</li>", at));
}

describe("FL-1c：沒有可以閃的變化", () => {
  it("判斷照伺服器的 flash_available（缺欄位的舊回應當作有）", () => {
    expect(NO_FLASH_OPTIONS_TEXT).toBe("這招目前沒有可以閃的變化");
    expect(noFlashOptions(undefined)).toBe(false);
    expect(noFlashOptions({ flash_available: true } as never)).toBe(false);
    expect(noFlashOptions({} as never)).toBe(false);
    expect(noFlashOptions({ flash_available: false } as never)).toBe(true);
    const { hero, none } = heroWithNone();
    const f = hero.flash!.find((x) => x.skill_id === none);
    expect(showCanFlash(f)).toBe(false); // 不再顯示「可以閃現了」
    expect(flashRowState(f, 3, hero.flash_rules, null)).toEqual({ can: false, reason: NO_FLASH_OPTIONS_TEXT });
  });

  it("一輪的閃現區：那一列標灰（虛線框）、灰字、閃現鈕停用；其他列照舊", () => {
    const { hero, none, ok } = heroWithNone();
    const out = html(createElement(FlashSection, { runId: "r", hero, busy: false, onChoose: noop }));
    const row = rowOf(out, none);
    expect(row).toContain('class="flash-skill-row flash-none"');
    expect(row).toContain(`data-testid="flash-none-${none}"`);
    expect(row).toContain(NO_FLASH_OPTIONS_TEXT);
    expect(row).toMatch(/<button[^>]*disabled=""[^>]*data-testid="flash-open-/);
    const other = rowOf(out, ok);
    expect(other).not.toContain("flash-none");
    expect(other).not.toMatch(/<button[^>]*disabled=""/);
  });

  it("大世界成長面板的靈感閃現分頁：同樣標灰、灰字、停用", () => {
    const { hero, none, ok } = heroWithNone();
    const out = html(createElement(WorldGrowth, { view: worldView(hero), busy: false, onChoose: noop, onAct: noop, onClose: () => undefined, initialTab: "flash" }));
    const row = rowOf(out, none);
    expect(row).toContain("pnl-row pnl-skill flash-none");
    expect(row).toContain(NO_FLASH_OPTIONS_TEXT);
    expect(row).toMatch(/<button[^>]*disabled=""[^>]*data-testid="flash-open-/);
    expect(rowOf(out, ok)).not.toContain("flash-none");
  });

  it("樣式照 LW-2 標灰（3.7 第 1 條）：灰紫虛線框、圖示褪灰；字不淡（不設 opacity）", () => {
    const css = readFile(SRC_DIR, "styles/flash.css");
    const box = /\.flash-skill-row\.flash-none,\s*\.pnl-skill\.flash-none\s*\{([^}]*)\}/.exec(css)?.[1] ?? "";
    expect(box).toMatch(/border:\s*1px dashed #8a8398/);
    expect(box).not.toMatch(/opacity/);
    expect(css).toMatch(/\.pnl-skill\.flash-none > canvas\s*\{\s*filter:\s*grayscale\(1\) brightness\(0\.8\)/);
  });
});
