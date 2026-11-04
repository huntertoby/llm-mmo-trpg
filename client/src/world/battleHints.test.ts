// 戰鬥短提示（6F-2，#99）：觸發條件、每種只出一次、全部關掉。
import { describe, expect, it } from "vitest";
import type { BattleHint, BattleView } from "../api/types";
import { hintFires, nextHint, readHintsOff, readSeen, seenKey, writeHintsOff, writeSeen } from "./battleHints";

const HERO = "u_hero";

function hint(id: string, trigger: BattleHint["trigger"], terrains: string[] = []): BattleHint {
  return { id, trigger, text_zh: id, terrains };
}

interface Opts {
  foeSurface?: string;
  surfaces?: string[];
  terrains?: string[];
  traps?: number;
  reactions?: number;
}

function view(o: Opts = {}): BattleView {
  const tiles = [
    { x: 1, y: 1, terrain: "stone", surface: "none" },
    { x: 2, y: 1, terrain: "stone", surface: o.foeSurface ?? "none" },
    ...(o.surfaces ?? []).map((surface, i) => ({ x: 5 + i, y: 5, terrain: "stone", surface })),
    ...(o.terrains ?? []).map((terrain, i) => ({ x: 5 + i, y: 6, terrain, surface: "none" })),
  ];
  return {
    units: [
      { id: HERO, pos: { x: 1, y: 1 }, team: "ally", hp: 20, downed: false, reaction_rules: Array.from({ length: o.reactions ?? 0 }, () => ({ reaction: "r" })) },
      { id: "u_mate", pos: { x: 0, y: 1 }, team: "ally", hp: 20, downed: false, reaction_rules: [] },
      { id: "u_foe", pos: { x: 2, y: 1 }, team: "enemy", hp: 20, downed: false, reaction_rules: [] },
    ],
    tiles,
    traps: Array.from({ length: o.traps ?? 0 }, () => ({})),
  } as unknown as BattleView;
}

class MemStore {
  data = new Map<string, string>();
  getItem(k: string) {
    return this.data.get(k) ?? null;
  }
  setItem(k: string, v: string) {
    this.data.set(k, v);
  }
}

describe("hint triggers follow the battle state", () => {
  it("battle start always fires", () => {
    expect(hintFires(hint("a", "battle_start"), view(), HERO, [])).toBe(true);
  });
  it("enemy on water: only when an enemy stands on a water tile", () => {
    const h = hint("w", "enemy_on_water");
    expect(hintFires(h, view(), HERO, [])).toBe(false);
    expect(hintFires(h, view({ surfaces: ["water"] }), HERO, [])).toBe(false);
    expect(hintFires(h, view({ foeSurface: "water" }), HERO, [])).toBe(true);
  });
  it("water and ice present", () => {
    expect(hintFires(hint("f", "water_present"), view({ surfaces: ["water"] }), HERO, [])).toBe(true);
    expect(hintFires(hint("f", "water_present"), view({ surfaces: ["ice"] }), HERO, [])).toBe(false);
    expect(hintFires(hint("i", "ice_present"), view({ surfaces: ["ice"] }), HERO, [])).toBe(true);
  });
  it("traps and lethal terrain (terrain ids come from the server)", () => {
    expect(hintFires(hint("t", "trap_present"), view({ traps: 1 }), HERO, [])).toBe(true);
    expect(hintFires(hint("t", "trap_present"), view(), HERO, [])).toBe(false);
    const lethal = hint("l", "lethal_terrain", ["chasm", "lava"]);
    expect(hintFires(lethal, view({ terrains: ["lava"] }), HERO, [])).toBe(true);
    expect(hintFires(lethal, view({ terrains: ["grass"] }), HERO, [])).toBe(false);
  });
  it("reaction: the hero has reaction rules, or someone's reaction triggered", () => {
    const h = hint("r", "reaction");
    expect(hintFires(h, view(), HERO, [])).toBe(false);
    expect(hintFires(h, view({ reactions: 1 }), HERO, [])).toBe(true);
    expect(hintFires(h, view(), HERO, [{ type: "reaction_triggered" }])).toBe(true);
  });
  it("pushed: a forced move of our side (not the enemy)", () => {
    const h = hint("p", "pushed");
    expect(hintFires(h, view(), HERO, [{ type: "unit_moved", unit_id: "u_foe", mode: "forced" }])).toBe(false);
    expect(hintFires(h, view(), HERO, [{ type: "unit_moved", unit_id: "u_mate", mode: "walk" }])).toBe(false);
    expect(hintFires(h, view(), HERO, [{ type: "unit_moved", unit_id: "u_mate", mode: "forced" }])).toBe(true);
  });
});

describe("one hint at a time, each once per character", () => {
  const hints = [hint("move_attack", "battle_start"), hint("water_lightning", "enemy_on_water")];
  it("picks the first that fires and has not been seen; nothing when switched off", () => {
    expect(nextHint(hints, view({ foeSurface: "water" }), HERO, [], new Set(), false)?.id).toBe("move_attack");
    expect(nextHint(hints, view({ foeSurface: "water" }), HERO, [], new Set(["move_attack"]), false)?.id).toBe("water_lightning");
    expect(nextHint(hints, view(), HERO, [], new Set(["move_attack"]), false)).toBeNull();
    expect(nextHint(hints, view(), HERO, [], new Set(), true)).toBeNull();
  });
  it("seen ids and the off switch are stored per browser; seen ids are per character", () => {
    const store = new MemStore();
    writeSeen("c1", new Set(["b", "a"]), store);
    expect(store.getItem(seenKey("c1"))).toBe('["a","b"]');
    expect([...readSeen("c1", store)].sort()).toEqual(["a", "b"]);
    expect(readSeen("c2", store).size).toBe(0);
    expect(readHintsOff(store)).toBe(false);
    writeHintsOff(true, store);
    expect(readHintsOff(store)).toBe(true);
    store.setItem(seenKey("c3"), "not json");
    expect(readSeen("c3", store).size).toBe(0);
  });
});
