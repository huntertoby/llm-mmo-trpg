import { describe, expect, it } from "vitest";
import type { Action } from "../api/types";
import { actionLabel } from "./actions";
import {
  actionAtTile,
  basicModes,
  BASIC_ACTION_KINDS,
  BASIC_ACTION_LIMIT,
  BASIC_MODES,
  emptyTargets,
  fallbackActions,
  moreModes,
  MORE_KINDS,
  RESIDENT_KINDS,
  targetTiles,
  TRAY_KINDS,
  vaultMarks,
  type ActionMode,
} from "./targeting";
import { smallView, unit } from "./testFixtures";

const H = "unit_0001";
const ALLY = "unit_0002";
const FOE = "unit_0003";
const hero = unit(H, "ally", 1, 1, {});
const view = smallView({ units: [hero, unit(ALLY, "ally", 2, 1), unit(FOE, "enemy", 3, 3)] });

const guardSelf = { type: "defend", unit_id: H, target_id: null } as Action;
const guardAlly = { type: "defend", unit_id: H, target_id: ALLY } as Action;
const swap = { type: "swap", unit_id: H, target_id: ALLY } as Action;
const aim = { type: "aim", unit_id: H } as Action;
const attack = { type: "attack", unit_id: H, target_id: FOE } as Action;
const shove = { type: "shove", unit_id: H, target_id: FOE } as Action;
const trip = { type: "trip", unit_id: H, target_id: FOE } as Action;
const climb = { type: "vault", unit_id: H, dest: { x: 1, y: 2 } } as Action;
const jump = { type: "vault", unit_id: H, dest: { x: 3, y: 1 } } as Action;
const run = { type: "run", unit_id: H } as Action;

function modeOf(legal: Action[], kind: string): ActionMode {
  const mode = basicModes(legal).find((m) => m.kind === kind);
  if (mode === undefined) throw new Error(`no mode ${kind}`);
  return mode;
}

describe("guard, swap and aim (Phase 3-21a)", () => {
  it("makes guard one resident mode: yourself, or an adjacent ally by clicking him", () => {
    const guard = modeOf([guardSelf, guardAlly, swap, aim], "defend");
    expect(guard.label).toBe("守護");
    expect(guard.targets.self).toBe(guardSelf);
    expect(guard.targets.units.get(ALLY)).toBe(guardAlly);
    // 點自己 ＝ 守護自己；點隊友 ＝ 守護他
    expect(actionAtTile(guard, view, hero, { x: 1, y: 1 })).toBe(guardSelf);
    expect(actionAtTile(guard, view, hero, { x: 2, y: 1 })).toBe(guardAlly);
    expect(targetTiles(guard, view, hero).targets).toEqual(
      expect.arrayContaining([
        { x: 1, y: 1 },
        { x: 2, y: 1 },
      ]),
    );
  });

  it("guards yourself instantly when no ally is adjacent", () => {
    const guard = modeOf([guardSelf], "defend");
    expect(guard.targets.units.size).toBe(0);
    expect(guard.targets.self).toBe(guardSelf);
  });

  it("has nothing left for the fallback list", () => {
    expect(fallbackActions([guardSelf, guardAlly, swap, aim, climb, shove, trip, run, attack], hero)).toEqual([]);
  });

  it("labels them in Chinese", () => {
    expect(actionLabel(guardSelf, view, {})).toBe("守護自己");
    expect(actionLabel(guardAlly, view, {})).toContain("守護：");
    expect(actionLabel(swap, view, {})).toContain("換位：");
    expect(actionLabel(aim, view, {})).toBe("瞄準");
    expect(actionLabel(climb, view, {})).toContain("攀跳到");
  });
});

describe("more-actions menu (Phase 3-21b)", () => {
  const labels = (legal: Action[]) => moreModes(basicModes(legal)).map((m) => m.label);

  it("lists only the currently legal extra actions, in a fixed order", () => {
    expect(labels([attack, run, guardSelf])).toEqual([]); // 常駐動作不進選單
    expect(labels([guardSelf, swap, aim])).toEqual(["換位", "瞄準"]);
    expect(labels([climb, aim, shove, trip])).toEqual(["推擊", "絆倒", "瞄準", "攀跳"]);
  });

  it("shows swap only when an ally is adjacent, and vault only with a legal landing", () => {
    expect(moreModes(basicModes([guardSelf])).map((m) => m.kind)).toEqual([]);
    expect(moreModes(basicModes([guardSelf, swap])).map((m) => m.kind)).toEqual(["swap"]);
    expect(moreModes(basicModes([guardSelf, climb])).map((m) => m.kind)).toEqual(["vault"]);
  });

  it("does not list a blocked (illegal) mode", () => {
    const blocked: ActionMode = {
      key: "interact",
      kind: "interact",
      label: "推動物件",
      skillId: null,
      actions: [],
      targets: emptyTargets(),
      blockedReason: "推不動",
    };
    expect(moreModes([blocked])).toEqual([]);
  });

  it("swap picks an ally by clicking him", () => {
    const mode = modeOf([swap], "swap");
    expect(actionAtTile(mode, view, hero, { x: 2, y: 1 })).toBe(swap);
    expect(actionAtTile(mode, view, hero, { x: 3, y: 3 })).toBeNull();
  });

  it("aim is a self-only instant action", () => {
    expect(modeOf([aim], "aim").targets.self).toBe(aim);
  });

  it("splits the resident, menu and tray buttons without overlap", () => {
    const all = [...RESIDENT_KINDS, ...MORE_KINDS, ...TRAY_KINDS];
    expect(new Set(all).size).toBe(all.length);
    expect(BASIC_MODES.map((m) => m.kind).sort()).toEqual([...all].sort());
  });

  it("keeps the number of basic actions within the limit of 10", () => {
    expect(BASIC_ACTION_KINDS.length).toBeLessThanOrEqual(BASIC_ACTION_LIMIT);
    expect(new Set(BASIC_ACTION_KINDS).size).toBe(BASIC_ACTION_KINDS.length);
  });
});

describe("vault (Phase 3-21b)", () => {
  it("picks the landing by clicking the tile", () => {
    const mode = modeOf([climb, jump], "vault");
    expect(actionAtTile(mode, view, hero, { x: 1, y: 2 })).toBe(climb);
    expect(actionAtTile(mode, view, hero, { x: 3, y: 1 })).toBe(jump);
    expect(actionAtTile(mode, view, hero, { x: 0, y: 0 })).toBeNull();
  });

  it("marks climb (adjacent) and jump (two tiles away) landings separately", () => {
    const mode = modeOf([climb, jump], "vault");
    expect(vaultMarks(mode, hero)).toEqual([
      { pos: { x: 1, y: 2 }, kind: "climb" },
      { pos: { x: 3, y: 1 }, kind: "jump" },
    ]);
    expect(vaultMarks(null, hero)).toEqual([]);
    expect(vaultMarks(modeOf([attack], "attack"), hero)).toEqual([]);
  });
});
