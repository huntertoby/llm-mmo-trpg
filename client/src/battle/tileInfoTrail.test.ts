// E3b（08 8.29 E3 顯示）：霜行留下的表面的名詞說明。
import { describe, expect, it } from "vitest";
import type { BattleView, TileView } from "../api/types";
import { glossaryEntry, glossaryName } from "./glossary";
import { smallView } from "./testFixtures";
import { tileSections, trailSurfaceLine } from "./tileInfo";

function withTile(over: Partial<TileView>): BattleView {
  const v = smallView();
  return { ...v, tiles: v.tiles.map((t) => (t.x === 1 && t.y === 2 ? { ...t, ...over } : t)) };
}

const at = { x: 1, y: 2 };
const owner = () => smallView().units.find((u) => u.id === "unit_0001")?.name_zh as string;

describe("E3b 霜行冰的說明", () => {
  it("冰：誰留下的、剩幾回合、到期直接消失、自己踩不會滑倒", () => {
    const v = withTile({ surface: "ice", surface_remaining: 1, surface_creator: "unit_0001", surface_trail: "unit_0001" });
    const surface = tileSections(v, at, {}).find((s) => s.kind === "surface");
    const name = owner();
    expect(surface?.title).toBe("冰");
    expect(surface?.lines[0]).toBe(`${name}沿路留下的冰：剩 1 回合，到期直接消失，不會變成水。${name}自己踩不會滑倒，其他人照一般冰檢定。`);
    // 「持續 N 回合，之後變成水」那一行不列（不適用）；其餘照一般冰的說明
    expect(surface?.lines.some((l) => l.startsWith("由技能產生時持續"))).toBe(false);
    const general = (glossaryEntry("surfaces", "ice")?.rules_zh ?? []).filter((r) => !r.startsWith("由技能產生時持續"));
    expect(surface?.lines.slice(1)).toEqual(general);
  });

  it("不是冰：「滑倒」那句換成該表面原本的說明", () => {
    const v = withTile({ surface: "fire", surface_remaining: 2, surface_creator: "unit_0001", surface_trail: "unit_0001" });
    const surface = tileSections(v, at, {}).find((s) => s.kind === "surface");
    const name = owner();
    const fire = glossaryName("surfaces", "fire");
    expect(surface?.lines[0]).toBe(`${name}沿路留下的${fire}：剩 2 回合，到期直接消失。`); // 8.29 E3：不是冰不寫「不會變成水」
    expect(surface?.lines[0]).not.toContain("滑倒");
    const general = (glossaryEntry("surfaces", "fire")?.rules_zh ?? []).filter((r) => !r.startsWith("由技能產生時持續"));
    expect(general.length).toBeGreaterThan(0);
    expect(surface?.lines.slice(1)).toEqual(general);
  });

  it("一般的冰照舊", () => {
    const v = withTile({ surface: "ice", surface_remaining: 2, surface_creator: "unit_0003" });
    const surface = tileSections(v, at, {}).find((s) => s.kind === "surface");
    expect(surface?.title).toBe("冰・剩 2 回合");
    expect(surface?.lines.join("")).not.toContain("沿路留下");
  });

  it("持有者不在視圖裡時用單位 ID；沒有剩餘回合時不寫", () => {
    expect(trailSurfaceLine("unit_0009", "ice", null)).toBe("unit_0009沿路留下的冰：到期直接消失，不會變成水。unit_0009自己踩不會滑倒，其他人照一般冰檢定。");
    const fire = glossaryName("surfaces", "fire");
    expect(trailSurfaceLine("unit_0009", "fire", null)).toBe(`unit_0009沿路留下的${fire}：到期直接消失。`);
  });
});
