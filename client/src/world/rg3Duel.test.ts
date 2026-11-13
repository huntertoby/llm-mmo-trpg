// RG-3（#162）：遇敵面板的單挑對話框（`EncounterView.duel`）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { WorldView } from "../api/types";
import { duelEliteName, EncounterPanel } from "./WorldPanel";

function view(duel: "offered" | "accepted" | "declined" | null, duelZh: string | null, inBattle = false): WorldView {
  return {
    encounter: {
      location: "north_slope",
      location_name_zh: "北坡",
      enemy_level: 3,
      map_name_zh: "雪坡",
      weather_zh: "晴",
      day_phase_zh: "白天",
      enemies: [
        { name_zh: "雪狼", elite: false, affix_zh: null },
        { name_zh: "狼王", elite: true, affix_zh: "迅捷" },
      ],
      retreat_to_zh: "霧渡鎮",
      fatigued: false,
      hero_hp: 60,
      in_battle: inBattle,
      reinforcements: 0,
      hero_statuses: [],
      opening_zh: [],
      allies_zh: "主角（開場 HP 60）",
      battlefield_fallback_zh: null,
      duel,
      duel_zh: duelZh,
    },
  } as unknown as WorldView;
}

const OFFERED = "狼王要求一對一：接受＝只有你和它，拒絕＝照原本全隊打；兩邊獎勵一樣。";
const html = (v: WorldView) => renderToStaticMarkup(createElement(EncounterPanel, { view: v, busy: false, onAct: () => undefined, onBattle: () => undefined }));

describe("duel dialog", () => {
  it("offered: a dialog titled after the elite, the server's text (rewards equal) and two equal buttons", () => {
    const out = html(view("offered", OFFERED));
    expect(out).toContain("狼王要求一對一");
    expect(out).toContain("兩邊獎勵一樣");
    expect(out).toContain('data-testid="world-duel-accept"');
    expect(out).toContain('data-testid="world-duel-decline"');
    expect(out).toContain('class="duel-choices"');
    expect(out).toContain('data-testid="world-fight"'); // 不選直接開戰＝拒絕（照舊能打）
  });

  it("chosen: no dialog, only the server's line; no duel: nothing", () => {
    const accepted = html(view("accepted", "接受了狼王的單挑：隊友與其他敵人都不上場，獎勵照整場算。"));
    expect(accepted).not.toContain("world-duel-accept");
    expect(accepted).toContain('data-testid="world-encounter-duel"');
    const none = html(view(null, null));
    expect(none).not.toContain("world-duel");
    expect(none).not.toContain("world-encounter-duel");
  });

  it("already fighting: no dialog", () => {
    expect(html(view("offered", OFFERED, true))).not.toContain("world-duel-accept");
  });

  it("names the first elite", () => {
    const e = view("offered", OFFERED).encounter;
    expect(e === null ? "" : duelEliteName(e)).toBe("狼王");
  });
});
