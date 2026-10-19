// 以真實的 API 回應（oil_depot、種子 3、build_fire 的建立戰鬥回應）檢查純邏輯能處理實際資料。
// 重新產生：見 docs/phases/Phase3-3報告.md（以 TestClient 建立戰鬥並存下回應）。
import { describe, expect, it } from "vitest";
import type { BattleResponse } from "../api/types";
import { classifyActions } from "./actions";
import { buildDrawModel } from "./drawModel";
import { OBJECTS, TERRAIN } from "./glossary";
import { logLines } from "./log";
import { telegraphMarks } from "./telegraph";
import { unitNames } from "./units";
import fixture from "./fixtures/oil_depot_seed3.json";

const response = fixture as unknown as BattleResponse;

describe("a real create-battle response", () => {
  it("is waiting for the hero", () => {
    expect(response.awaiting).toBe("action");
    expect(response.view.active_unit).toBe(response.hero_id);
  });

  it("draws every tile and only known terrain and objects", () => {
    const model = buildDrawModel(response.view, response.hero_id);
    expect(model.tiles).toHaveLength(response.view.width * response.view.height);
    for (const t of response.view.tiles) expect(TERRAIN[t.terrain], t.terrain).toBeDefined();
    for (const o of response.view.objects) expect(OBJECTS[o.kind], o.kind).toBeDefined();
    expect(model.units.filter((u) => u.hero)).toHaveLength(1);
  });

  it("classifies every legal action", () => {
    const c = classifyActions(response.legal_actions, response.view, {});
    const moves = response.legal_actions.filter((a) => a.type === "move");
    const distinct = new Set(moves.map((a) => (a.type === "move" ? JSON.stringify(a.path.at(-1)) : "")));
    expect(c.moves.size).toBe(distinct.size);
    expect(c.endTurn).not.toBeNull();
    const placed = moves.length + c.attacks.size + c.others.length + 1;
    expect(placed).toBe(response.legal_actions.length);
    for (const o of c.others) expect(o.label).not.toBe("");
  });

  it("turns the opening steps into Chinese log lines", () => {
    const lines = logLines(response.steps, unitNames(response.view));
    expect(lines[0]?.text).toMatch(/^戰鬥開始：/);
    expect(lines.some((l) => l.text.startsWith("先攻："))).toBe(true);
  });

  it("carries the hero's reaction rules, the telegraph and the orders", () => {
    const hero = response.view.units.find((u) => u.id === response.hero_id);
    expect(hero?.reaction_rules.length).toBeGreaterThan(0);
    expect(hero?.reaction_rules.every((r) => r.mode === "auto" && r.name_zh !== "")).toBe(true);
    const enemies = response.view.units.filter((u) => u.team === "enemy");
    expect(enemies.every((u) => u.reaction_rules.length === 0)).toBe(true);
    expect(response.telegraph.round).toBe(response.view.round);
    expect(telegraphMarks(response.telegraph, response.view).length).toBeLessThanOrEqual(response.telegraph.changes.length);
    expect(response.orders_ignored).toEqual([]);
  });
});
