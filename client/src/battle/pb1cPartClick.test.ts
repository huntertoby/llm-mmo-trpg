// PB-1c：點有部位的頭目（05 5.12.3、R1 普攻也算單體、R6 本體預設、再點＝本體）。
// 規格 docs/phases/PhasePB-1計畫.md 第 7 節第 2、8 點：有部位／沒部位 × 瞄準單體／範圍／普攻；Enter、再點＝本體；Esc 只關選單。
import { describe, expect, it } from "vitest";
import type { Action, BattleView, PartActionOptions, PartOption, Pos, UnitView } from "../api/types";
import { classifyActions } from "./actions";
import { smallView, unit } from "./testFixtures";
import { decideTileClick, partOptionsFor, type TileClickState } from "./tileClick";
import { skillMode, type ActionMode } from "./targeting";
import { readFile, SRC_DIR } from "../test/sourceScan";

const H = "unit_0001";
const BOSS = "unit_0003";
const FOE = "unit_0004";
const p = (x: number, y: number): Pos => ({ x, y });
const hero: UnitView = unit(H, "ally", 0, 0);
const view: BattleView = smallView({
  units: [hero, unit("unit_0002", "ally", 1, 1), unit(BOSS, "enemy", 2, 1), unit(FOE, "enemy", 3, 3)],
});

const move = (x: number, y: number): Action => ({ type: "move", unit_id: H, path: [p(0, 0), p(x, y)] });
const attackBoss: Action = { type: "attack", unit_id: H, target_id: BOSS };
const attackFoe: Action = { type: "attack", unit_id: H, target_id: FOE };
const classified = classifyActions([move(0, 1), attackBoss, attackFoe], view, {});

const skill = (id: string, extra: Record<string, unknown>): Action => ({ type: "use_skill", unit_id: H, skill_id: id, ...extra }) as Action;
const modeOf = (actions: Action[], id: string): ActionMode =>
  skillMode({ skillId: id, name: "技能", costs: [], cooldown: 0, actions, disabledReason: null });
const boltBoss = skill("bolt", { target_id: BOSS });
const boltFoe = skill("bolt", { target_id: FOE });
const singleMode = modeOf([boltBoss, boltFoe], "bolt");
const blastAt = skill("blast", { target_pos: p(2, 1) });
const areaMode = modeOf([blastAt], "blast");

const OPTS: PartOption[] = [
  { part_id: "dantian", name_zh: "氣海", ok: false, reason_zh: "要從背後近戰才打得到" },
  { part_id: "whisk", name_zh: "拂塵", ok: true, reason_zh: null },
];
const PARTS: PartActionOptions[] = [
  { type: "attack", skill_id: null, target_id: BOSS, options: OPTS },
  { type: "use_skill", skill_id: "bolt", target_id: BOSS, options: OPTS },
];

const BASE: TileClickState = {
  shift: false,
  pinned: false,
  view,
  hero,
  canAct: true,
  copying: false,
  canOrder: true,
  orderPick: null,
  command: null,
  mode: null,
  hurlPick: null,
  classified,
};
const at = (over: Partial<TileClickState>, tile: Pos) => decideTileClick({ ...BASE, ...over }, tile);

describe("點擊表：有部位／沒部位 × 普攻／瞄準單體／範圍", () => {
  it("沒有 part_options 時，點頭目照舊普攻、瞄準照舊送出（和改前相同）", () => {
    expect(at({}, p(2, 1))).toEqual({ kind: "act", action: attackBoss, dismissPin: false });
    expect(at({ partActions: null }, p(2, 1))).toEqual({ kind: "act", action: attackBoss, dismissPin: false });
    expect(at({ mode: singleMode }, p(2, 1))).toEqual({ kind: "submit", action: boltBoss, dismissPin: false });
  });

  it("普攻點有部位的頭目（R1）：打開選單，動作是打本體", () => {
    expect(at({ partActions: PARTS, pinned: true }, p(2, 1))).toEqual({
      kind: "part_menu",
      targetId: BOSS,
      tile: p(2, 1),
      action: attackBoss,
      options: OPTS,
      submit: false,
      dismissPin: true,
    });
  });

  it("瞄準單體技能點有部位的頭目：打開選單（submit）", () => {
    const r = at({ partActions: PARTS, mode: singleMode }, p(2, 1));
    expect(r).toMatchObject({ kind: "part_menu", targetId: BOSS, action: boltBoss, submit: true });
  });

  it("範圍技能（target_pos）點頭目那一格：照舊送出，不開選單", () => {
    expect(at({ partActions: PARTS, mode: areaMode }, p(2, 1))).toEqual({ kind: "submit", action: blastAt, dismissPin: false });
  });

  it("沒有部位的單位：普攻、瞄準照舊", () => {
    expect(at({ partActions: PARTS }, p(3, 3))).toEqual({ kind: "act", action: attackFoe, dismissPin: false });
    expect(at({ partActions: PARTS, mode: singleMode }, p(3, 3))).toEqual({ kind: "submit", action: boltFoe, dismissPin: false });
  });

  it("移動、釘住等其他格子照舊", () => {
    expect(at({ partActions: PARTS }, p(0, 1))).toEqual({ kind: "act", action: move(0, 1), dismissPin: false });
    expect(at({ partActions: PARTS }, p(3, 0))).toEqual({ kind: "pin", tile: p(3, 0) });
  });
});

describe("選單開著時（R6）", () => {
  it("再點同一個頭目＝打本體（照原本送出）", () => {
    expect(at({ partActions: PARTS, partMenuTarget: BOSS }, p(2, 1))).toEqual({ kind: "act", action: attackBoss, dismissPin: false });
    expect(at({ partActions: PARTS, partMenuTarget: BOSS, mode: singleMode }, p(2, 1))).toEqual({ kind: "submit", action: boltBoss, dismissPin: false });
  });

  it("點別的地方只關選單（不移動、不攻擊別人、不釘卡）", () => {
    for (const tile of [p(0, 1), p(3, 3), p(3, 0)]) expect(at({ partActions: PARTS, partMenuTarget: BOSS }, tile)).toEqual({ kind: "ignore" });
  });

  it("Shift＋點照舊釘卡", () => {
    expect(at({ partActions: PARTS, partMenuTarget: BOSS, shift: true }, p(2, 1))).toEqual({ kind: "pin", tile: p(2, 1) });
  });
});

describe("`partOptionsFor`", () => {
  it("用動作種類＋技能＋目標對到選項", () => {
    expect(partOptionsFor(PARTS, attackBoss)?.type).toBe("attack");
    expect(partOptionsFor(PARTS, boltBoss)?.skill_id).toBe("bolt");
    expect(partOptionsFor(PARTS, skill("other", { target_id: BOSS }))).toBeNull();
    expect(partOptionsFor(PARTS, attackFoe)).toBeNull();
    expect(partOptionsFor(PARTS, move(0, 1))).toBeNull();
    expect(partOptionsFor(null, attackBoss)).toBeNull();
  });
});

describe("Esc 只關選單、不取消瞄準；Enter／點本體＝本體（PartMenu 接線）", () => {
  const menu = readFile(SRC_DIR, "ui/PartMenu.tsx");
  const hook = readFile(SRC_DIR, "ui/usePopupMenu.ts");
  it("選單用共用的 usePopupMenu（Esc 先關選單並 stopPropagation，BattleScreen 的 Esc 不會再取消瞄準）＋PopupFrame", () => {
    expect(menu).toMatch(/usePopupMenu\(/);
    expect(menu).toMatch(/<PopupFrame/);
    expect(menu).toMatch(/popup-menu/);
    expect(hook).toMatch(/e\.key !== "Escape"/);
    expect(hook).toMatch(/stopPropagation\(\)/);
  });
  it("按下滑鼠那一刻開著的選單目標交給點擊規則（再點＝本體）", () => {
    const tiles = readFile(SRC_DIR, "screens/battle/useTileInteraction.ts");
    expect(tiles).toMatch(/partMenuTarget/);
    expect(tiles).toMatch(/case "part_menu"/);
  });
});
