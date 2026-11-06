// Phase 6A-4e（戰鬥 D 版⑤：戰鬥版 HUD 版面 A）：字母標記的顯示條件、右上地名的來源、HUD 排版檢查的純函式。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { WorldView } from "../api/types";
import { BATTLE_DRAW, buildDrawModel } from "../battle/drawModel";
import { HUD_BOTTOM_FALLBACK, hudInsetStyle, hudLayoutIssues, type HudBox } from "../battle/hudLayout";
import { battlePlaceName, worldPlaceName } from "../battle/placeName";
import { smallView } from "../battle/testFixtures";
import { unitNames } from "../battle/units";
import { BattleStatusBox, roundHint } from "./BattleStatusBox";
import { TurnBar } from "./TurnBar";
import { UnitInfo } from "./UnitInfo";

const HERO = "unit_0001";

describe("字母標記只在滑過單位與行動順序列顯示", () => {
  it("戰鬥畫面的繪製模型不畫字母（BATTLE_DRAW），預設照舊有字母", () => {
    const view = smallView();
    const plain = buildDrawModel(view, HERO);
    expect(plain.units.map((u) => u.marker).every((m) => m !== "")).toBe(true);
    const battle = buildDrawModel(view, HERO, undefined, undefined, BATTLE_DRAW);
    expect(battle.units.length).toBe(plain.units.length);
    expect(battle.units.every((u) => u.marker === "")).toBe(true);
  });

  it("行動順序列每顆小章都有字母", () => {
    const view = smallView();
    const names = unitNames(view);
    const html = renderToStaticMarkup(createElement(TurnBar, { view, names }));
    for (const id of view.turn_order) expect(html).toContain(`<span class="turn-chip-marker">${names.marker(id)}</span>`);
    // 回合、地名不在行動順序列（移到右上）
    expect(html).not.toContain("測試地圖");
    expect(html).not.toContain("第 1");
  });

  it("滑過單位的資訊卡有字母", () => {
    const view = smallView();
    const names = unitNames(view);
    const enemy = view.units.find((u) => u.id === "unit_0003");
    if (enemy === undefined) throw new Error("fixture");
    const html = renderToStaticMarkup(
      createElement(UnitInfo, { unit: enemy, names, heroId: HERO, skills: {}, cards: {}, view, pinned: false, onTogglePin: () => undefined }),
    );
    expect(html).toContain(`>${names.marker(enemy.id)}</span>`);
  });
});

describe("右上地名：大世界用地點名，一輪用地圖名", () => {
  const world = (fieldName: string | null, here = "灰渡口") =>
    ({ field: fieldName === null ? null : { name_zh: fieldName }, here: { name_zh: here } }) as unknown as Pick<WorldView, "field" | "here">;

  it("世界畫面：實地地圖名優先，沒有實地用地點名，沒有世界畫面為 null", () => {
    expect(worldPlaceName(world("枯木林"))).toBe("枯木林");
    expect(worldPlaceName(world(null, "枯木林"))).toBe("枯木林");
    expect(worldPlaceName(null)).toBeNull();
    expect(worldPlaceName(world("  "))).toBeNull();
  });

  it("有地點名蓋過戰場地圖名（荒原的枯木林不寫成竹林）；沒有就用地圖名", () => {
    const view = smallView({ map_name_zh: "竹林" });
    expect(battlePlaceName(view, "枯木林")).toBe("枯木林");
    expect(battlePlaceName(view, null)).toBe("竹林");
    expect(battlePlaceName(view, undefined)).toBe("竹林");
    expect(battlePlaceName(view, "")).toBe("竹林");
  });

  it("右上狀態框：大世界顯示枯木林、一輪顯示地圖名；回合數字、天氣與勝利條件圖示", () => {
    const view = smallView({ map_name_zh: "竹林", round: 2, weather_id: "rain", weather_name_zh: "下雨" });
    const world6 = renderToStaticMarkup(createElement(BattleStatusBox, { view, placeName: "枯木林" }));
    expect(world6).toContain("枯木林");
    expect(world6).not.toContain("竹林");
    expect(world6).toContain("<b>2</b>");
    expect(world6).toContain('data-icon="rain"');
    expect(world6).toContain('data-testid="battle-objective"');
    const run = renderToStaticMarkup(createElement(BattleStatusBox, { view }));
    expect(run).toContain("竹林");
    // 沒有天氣就不畫天氣圖示
    expect(renderToStaticMarkup(createElement(BattleStatusBox, { view: smallView() }))).not.toContain("battle-weather");
    expect(roundHint(view)).toBe("第 2 / 30 輪");
  });
});

describe("HUD 排版檢查（三種大小）", () => {
  const bx = (left: number, top: number, right: number, bottom: number): HudBox => ({ left, top, right, bottom });
  /** 三種大小下的實測排法（右上框寬 224、左上卡寬 252；800 寬時 210／230）。 */
  const layouts: Record<string, { w: number; h: number; blocks: Record<string, HudBox> }> = {
    "800x600": {
      w: 800,
      h: 600,
      blocks: {
        hero: bx(8, 8, 238, 112),
        order: bx(300, 8, 520, 46),
        status: bx(582, 8, 792, 52),
        tools: bx(582, 56, 792, 92),
        skills: bx(8, 448, 564, 592),
        turn: bx(572, 432, 792, 592),
        log: bx(8, 390, 38, 418),
      },
    },
    "1040x624": {
      w: 1040,
      h: 624,
      blocks: {
        hero: bx(8, 8, 260, 112),
        order: bx(400, 8, 640, 46),
        status: bx(808, 8, 1032, 52),
        tools: bx(808, 56, 1032, 92),
        skills: bx(200, 470, 774, 616),
        turn: bx(782, 456, 1032, 616),
        log: bx(8, 410, 38, 440),
      },
    },
    "1600x900": {
      w: 1600,
      h: 900,
      blocks: {
        hero: bx(8, 8, 260, 112),
        order: bx(680, 8, 920, 46),
        status: bx(1368, 8, 1592, 52),
        tools: bx(1368, 56, 1592, 92),
        skills: bx(480, 746, 1334, 892),
        turn: bx(1342, 732, 1592, 892),
        log: bx(8, 690, 38, 720),
      },
    },
  };

  for (const [name, l] of Object.entries(layouts)) {
    it(`${name}：每塊都在畫面內、互不重疊`, () => {
      expect(hudLayoutIssues(l.blocks, l.w, l.h)).toEqual([]);
    });
  }

  it("出畫面、重疊、缺塊都會列出來", () => {
    const l = layouts["800x600"];
    if (l === undefined) throw new Error("fixture");
    expect(hudLayoutIssues({ ...l.blocks, turn: bx(572, 432, 820, 592) }, l.w, l.h)).toEqual(["turn 出畫面"]);
    expect(hudLayoutIssues({ ...l.blocks, order: bx(200, 8, 520, 46) }, l.w, l.h)).toEqual(["hero 與 order 重疊"]);
    const { log: _log, ...noLog } = l.blocks;
    expect(hudLayoutIssues(noLog, l.w, l.h)).toEqual(["找不到 log"]);
  });

  it("底部列高度的 CSS 變數：量到前用預設值", () => {
    expect(hudInsetStyle(null)).toEqual({ "--hud-bottom": `${HUD_BOTTOM_FALLBACK}px` });
    expect(hudInsetStyle(0)).toEqual({ "--hud-bottom": `${HUD_BOTTOM_FALLBACK}px` });
    expect(hudInsetStyle(171.2)).toEqual({ "--hud-bottom": "172px" });
  });
});
