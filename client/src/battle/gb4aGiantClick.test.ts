// GB-4a：點巨型頭目的某一格（05 5.12.4 第 3 點、T12；docs/phases/PhaseGB計畫.md 8.1 第 3 點）。
// 9 格 × 選取模式的點擊表：由那一格推出部位、不跳選單；前殼、已破、未露出＝本體；打不到的部位格只提示原因。
// 人形頭目（1 格）的選單照段 1（pb1cPartClick.test.ts 原表不改）。
import { describe, expect, it } from "vitest";
import type { Action, BattleView, PartActionOptions, PartOption, PartView, Pos, UnitView } from "../api/types";
import { classifyActions } from "./actions";
import { giantAimLine } from "./footprint";
import { smallView, unit } from "./testFixtures";
import { decideTileClick, giantAimAt, hoverActionAt, type TileClickState } from "./tileClick";
import { skillMode, targetTiles, type ActionMode } from "./targeting";

const H = "unit_0001";
const HEART = "unit_0002";
const p = (x: number, y: number): Pos => ({ x, y });
const tilesOf = (cx: number, cy: number): Pos[] => [-1, 0, 1].flatMap((dy) => [-1, 0, 1].map((dx) => p(cx + dx, cy + dy)));

function part(id: string, name: string, tiles: Pos[], over: Partial<PartView> = {}): PartView {
  return { id, name_zh: name, hp: 32, max_hp: 32, broken: false, exposed: true, reach: "any", break_lines_zh: [], tiles, ...over };
}

function heart(parts: PartView[]): UnitView {
  return unit(HEART, "enemy", 5, 3, { footprint: 3, tiles: tilesOf(5, 3), parts });
}

const SHELL_PHASE = [
  part("core", "核心", [p(5, 3)], { exposed: false }),
  part("shell_seam", "殼縫", [p(4, 3), p(6, 3)]),
  part("vent", "熔岩噴口", [p(4, 2), p(5, 2), p(6, 2)], { reach: "ranged" }),
];
const MELEE_OPTS: PartOption[] = [
  { part_id: "core", name_zh: "核心", ok: false, reason_zh: "呼吸階段才露出" },
  { part_id: "shell_seam", name_zh: "殼縫", ok: true, reason_zh: null },
  { part_id: "vent", name_zh: "熔岩噴口", ok: false, reason_zh: "只有遠程才打得到" },
];

const hero: UnitView = unit(H, "ally", 3, 3);
const attack: Action = { type: "attack", unit_id: H, target_id: HEART };
const skill = (id: string, extra: Record<string, unknown>): Action => ({ type: "use_skill", unit_id: H, skill_id: id, ...extra }) as Action;
const modeOf = (actions: Action[], id: string): ActionMode =>
  skillMode({ skillId: id, name: "技能", costs: [], cooldown: 0, actions, disabledReason: null });
const bolt = skill("bolt", { target_id: HEART });
const singleMode = modeOf([bolt], "bolt");
const blastAt = skill("blast", { target_pos: p(5, 4) });
const areaMode = modeOf([blastAt], "blast");

function stateFor(parts: PartView[], opts: PartOption[]): TileClickState {
  const view: BattleView = smallView({ width: 12, height: 12, units: [hero, heart(parts)] });
  const classified = classifyActions([attack], view, {});
  const partActions: PartActionOptions[] = [
    { type: "attack", skill_id: null, target_id: HEART, options: opts },
    { type: "use_skill", skill_id: "bolt", target_id: HEART, options: opts },
  ];
  return { shift: false, pinned: false, view, hero, canAct: true, copying: false, canOrder: true, orderPick: null, command: null, mode: null, hurlPick: null, classified, partActions };
}

const BASE = stateFor(SHELL_PHASE, MELEE_OPTS);
const withPart = (a: Action, part: string): Action => ({ ...a, target_part: part }) as Action;

describe("9 格點擊表（第 1 階段，近戰站殼縫西側）", () => {
  // 每一格：普攻、瞄準單體技能各自的結果
  const table: [Pos, string, "body" | "part" | "hint", string?][] = [
    [p(4, 2), "噴口西", "hint", "打不到熔岩噴口：只有遠程才打得到"],
    [p(5, 2), "噴口中", "hint", "打不到熔岩噴口：只有遠程才打得到"],
    [p(6, 2), "噴口東", "hint", "打不到熔岩噴口：只有遠程才打得到"],
    [p(4, 3), "殼縫西", "part", "shell_seam"],
    [p(5, 3), "核心（未露出）", "body"],
    [p(6, 3), "殼縫東", "part", "shell_seam"],
    [p(4, 4), "前殼西", "body"],
    [p(5, 4), "前殼中", "body"],
    [p(6, 4), "前殼東", "body"],
  ];
  it.each(table)("普攻點 %o（%s）", (tile, _name, kind, extra) => {
    const r = decideTileClick(BASE, tile);
    if (kind === "hint") expect(r).toEqual({ kind: "hint", text: extra });
    else if (kind === "part") expect(r).toEqual({ kind: "act", action: withPart(attack, extra as string), dismissPin: false });
    else expect(r).toEqual({ kind: "act", action: attack, dismissPin: false });
  });
  it.each(table)("瞄準單體技能點 %o（%s）", (tile, _name, kind, extra) => {
    const r = decideTileClick({ ...BASE, mode: singleMode }, tile);
    if (kind === "hint") expect(r).toEqual({ kind: "hint", text: extra });
    else if (kind === "part") expect(r).toEqual({ kind: "submit", action: withPart(bolt, extra as string), dismissPin: false });
    else expect(r).toEqual({ kind: "submit", action: bolt, dismissPin: false });
  });
  it("巨型頭目不跳選單（任何一格都不回 part_menu）", () => {
    for (const t of tilesOf(5, 3)) {
      expect(decideTileClick(BASE, t).kind).not.toBe("part_menu");
      expect(decideTileClick({ ...BASE, mode: singleMode }, t).kind).not.toBe("part_menu");
    }
  });
  it("範圍技能（target_pos）點佔格：照舊送出，不推部位", () => {
    expect(decideTileClick({ ...BASE, mode: areaMode }, p(5, 4))).toEqual({ kind: "submit", action: blastAt, dismissPin: false });
  });
  it("釘住的卡：打部位時一併關掉（同一般攻擊）", () => {
    expect(decideTileClick({ ...BASE, pinned: true }, p(6, 3))).toEqual({ kind: "act", action: withPart(attack, "shell_seam"), dismissPin: true });
  });
});

describe("已破、露出後、遠程", () => {
  it("已破的殼縫格＝本體", () => {
    const parts = SHELL_PHASE.map((x) => (x.id === "shell_seam" ? { ...x, broken: true, hp: 0 } : x));
    const opts = MELEE_OPTS.map((o) => (o.part_id === "shell_seam" ? { ...o, ok: false, reason_zh: "已經破了" } : o));
    expect(decideTileClick(stateFor(parts, opts), p(4, 3))).toEqual({ kind: "act", action: attack, dismissPin: false });
  });
  it("第 2 階段核心露出：點中心格打核心", () => {
    const parts = SHELL_PHASE.map((x) => (x.id === "core" ? { ...x, exposed: true } : x));
    const opts = MELEE_OPTS.map((o) => (o.part_id === "core" ? { ...o, ok: true, reason_zh: null } : o));
    expect(decideTileClick(stateFor(parts, opts), p(5, 3))).toEqual({ kind: "act", action: withPart(attack, "core"), dismissPin: false });
  });
  it("遠程射程不夠：噴口格提示伺服器的原因", () => {
    const opts = MELEE_OPTS.map((o) => (o.part_id === "vent" ? { ...o, reason_zh: "那一格超出射程" } : o));
    expect(decideTileClick(stateFor(SHELL_PHASE, opts), p(5, 2))).toEqual({ kind: "hint", text: "打不到熔岩噴口：那一格超出射程" });
  });
});

describe("滑過：預覽的動作與資訊卡的一行", () => {
  const hoverAt = (tile: Pos, s: TileClickState = BASE) => giantAimAt(s.view, s.partActions, hoverActionAt(s, tile), tile);
  it("殼縫格預覽帶 target_part；噴口格不預覽並寫原因；前殼＝本體", () => {
    expect(hoverAt(p(6, 3))).toMatchObject({ kind: "part", action: withPart(attack, "shell_seam") });
    expect(hoverAt(p(5, 2))).toMatchObject({ kind: "blocked", reason: "只有遠程才打得到" });
    expect(hoverAt(p(5, 4))).toMatchObject({ kind: "body", action: attack, part: null });
  });
  it("資訊卡的字", () => {
    const line = (tile: Pos) => {
      const aim = hoverAt(tile);
      return aim === null ? null : giantAimLine(aim);
    };
    expect(line(p(4, 3))).toBe("部位：殼縫（點這一格打殼縫）");
    expect(line(p(4, 2))).toBe("部位：熔岩噴口・打不到：只有遠程才打得到");
    expect(line(p(5, 3))).toBe("部位：核心・呼吸階段才露出（點這一格＝打本體）");
    expect(line(p(5, 4))).toBe("前殼（本體）：點這一格打本體");
  });
  it("不在佔格、沒有部位選項、不能行動時沒有", () => {
    expect(hoverAt(p(3, 3))).toBeNull();
    expect(hoverAt(p(5, 2), { ...BASE, partActions: null })).toBeNull();
    expect(hoverAt(p(5, 2), { ...BASE, canAct: false })).toBeNull();
  });
});

describe("目標高亮蓋整個 3×3", () => {
  it("瞄準單體技能：targetTiles 列出 9 格", () => {
    const t = targetTiles(singleMode, BASE.view, hero);
    expect(t.targets).toEqual(tilesOf(5, 3));
  });
});
