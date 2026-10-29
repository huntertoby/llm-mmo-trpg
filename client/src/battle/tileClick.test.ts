// 點擊格子的規則（Phase 3T-7，抽自 BattleScreen 的 onTileClick）：每一列是一個「畫面狀態＋點的格子 → 要做的事」。
import { describe, expect, it } from "vitest";
import type { Action, BattleView, CommandOptions, Pos, UnitView } from "../api/types";
import { classifyActions } from "./actions";
import type { OrderKind } from "./orders";
import type { CommandSession } from "./summonControl";
import { smallView, unit } from "./testFixtures";
import { decideTileClick, type TileClickResult, type TileClickState } from "./tileClick";
import { skillMode, type ActionMode } from "./targeting";

const H = "unit_0001";
const p = (x: number, y: number): Pos => ({ x, y });
const hero: UnitView = unit(H, "ally", 0, 0);
// 隊友 (1,1)、敵人 (2,1)；物件 obj_0001 (2,2)、obj_0002 (1,2)（smallView 預設）。
const view: BattleView = smallView({
  units: [hero, unit("unit_0002", "ally", 1, 1), unit("unit_0003", "enemy", 2, 1)],
});

const move = (x: number, y: number): Action => ({ type: "move", unit_id: H, path: [p(0, 0), p(x, y)] });
const attack: Action = { type: "attack", unit_id: H, target_id: "unit_0003" };
const classified = classifyActions([move(0, 1), attack], view, {});

const skill = (extra: Record<string, unknown>): Action =>
  ({ type: "use_skill", unit_id: H, skill_id: "blast", ...extra }) as Action;
const modeOf = (actions: Action[], id = "blast"): ActionMode =>
  skillMode({ skillId: id, name: "技能", costs: [], cooldown: 0, actions, disabledReason: null });
const blast = skill({ target_pos: p(3, 2) });
const targetMode = modeOf([blast, skill({ target_id: "unit_0003" })]);

const hurlA = (obj: string, x: number, y: number): Action => skill({ target_object_id: obj, target_pos: p(x, y) });
const hurlActions = [hurlA("obj_0001", 2, 1), hurlA("obj_0001", 3, 2), hurlA("obj_0002", 0, 2)];
const hurlMode = modeOf(hurlActions, "hurl");

const options: CommandOptions = {
  summon_id: "unit_0006",
  ap_cost: 1,
  options: [
    { dest: p(1, 0), path: [p(1, 0)], targets: [] },
    { dest: p(2, 0), path: [p(1, 0), p(2, 0)], targets: ["unit_0003"] },
  ],
};
const command = (dest: Pos | null): CommandSession => ({ summonId: "unit_0006", options, dest });

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

interface Row {
  name: string;
  state: Partial<TileClickState>;
  tile: Pos;
  expected: TileClickResult;
}

const pin = (tile: Pos): TileClickResult => ({ kind: "pin", tile });
const IGNORE: TileClickResult = { kind: "ignore" };
const order = (kind: OrderKind): Partial<TileClickState> => ({ orderPick: kind });

const ROWS: Row[] = [
  // Shift＋左鍵
  { name: "shift pins any tile", state: { shift: true }, tile: p(2, 1), expected: pin(p(2, 1)) },
  { name: "shift wins over command", state: { shift: true, command: command(null) }, tile: p(1, 0), expected: pin(p(1, 0)) },
  { name: "shift wins over a mode", state: { shift: true, mode: targetMode }, tile: p(3, 2), expected: pin(p(3, 2)) },
  // 不是自己的回合
  { name: "not my turn pins", state: { canAct: false }, tile: p(2, 1), expected: pin(p(2, 1)) },
  { name: "no hero pins", state: { hero: null }, tile: p(2, 1), expected: pin(p(2, 1)) },
  { name: "not my turn ignores the mode", state: { canAct: false, mode: targetMode }, tile: p(3, 2), expected: pin(p(3, 2)) },
  // 沒有選取模式
  { name: "idle: enemy tile attacks", state: {}, tile: p(2, 1), expected: { kind: "act", action: attack, dismissPin: false } },
  { name: "idle: enemy tile attacks and dismisses a pinned card", state: { pinned: true }, tile: p(2, 1), expected: { kind: "act", action: attack, dismissPin: true } },
  { name: "idle: reachable tile moves", state: {}, tile: p(0, 1), expected: { kind: "act", action: move(0, 1), dismissPin: false } },
  { name: "idle: tile without action pins", state: {}, tile: p(3, 2), expected: pin(p(3, 2)) },
  // 有選取模式
  { name: "mode: target tile submits", state: { mode: targetMode }, tile: p(3, 2), expected: { kind: "submit", action: blast, dismissPin: false } },
  { name: "mode: pinned card is dismissed", state: { mode: targetMode, pinned: true }, tile: p(3, 2), expected: { kind: "submit", action: blast, dismissPin: true } },
  { name: "mode: copy pause also submits", state: { mode: targetMode, canAct: false, copying: true }, tile: p(3, 2), expected: { kind: "submit", action: blast, dismissPin: false } },
  { name: "mode: tile without action pins", state: { mode: targetMode }, tile: p(0, 1), expected: pin(p(0, 1)) },
  { name: "mode: copy pause with no action pins", state: { mode: targetMode, canAct: false, copying: true }, tile: p(0, 1), expected: pin(p(0, 1)) },
  { name: "mode: shove aside is ignored", state: { mode: { ...targetMode, kind: "shove_aside" } }, tile: p(3, 2), expected: IGNORE },
  {
    name: "mode: a blocked push shows its reason",
    state: { mode: { ...targetMode, blockedObjects: new Map([["obj_0001", "推不動：太重"]]) } },
    tile: p(2, 2),
    expected: { kind: "hint", text: "推不動：太重" },
  },
  // 投擲（兩段選取）
  { name: "hurl stage 1: click an object picks it", state: { mode: hurlMode }, tile: p(2, 2), expected: { kind: "hurl_pick", pick: "obj_0001" } },
  { name: "hurl stage 1: click a non-object is ignored", state: { mode: hurlMode }, tile: p(0, 1), expected: IGNORE },
  { name: "hurl stage 2: click the same object cancels the pick", state: { mode: hurlMode, hurlPick: "obj_0001" }, tile: p(2, 2), expected: { kind: "hurl_pick", pick: null } },
  { name: "hurl stage 2: click another object re-picks", state: { mode: hurlMode, hurlPick: "obj_0001" }, tile: p(1, 2), expected: { kind: "hurl_pick", pick: "obj_0002" } },
  { name: "hurl stage 2: landing submits (landing first)", state: { mode: hurlMode, hurlPick: "obj_0001" }, tile: p(3, 2), expected: { kind: "submit", action: hurlActions[1] as Action, dismissPin: false } },
  { name: "hurl stage 2: landing keeps a pinned card", state: { mode: hurlMode, hurlPick: "obj_0001", pinned: true }, tile: p(2, 1), expected: { kind: "submit", action: hurlActions[0] as Action, dismissPin: false } },
  { name: "hurl stage 2: click elsewhere is ignored", state: { mode: hurlMode, hurlPick: "obj_0001" }, tile: p(0, 1), expected: IGNORE },
  // 隊友指令
  { name: "order: protect an ally", state: order("protect"), tile: p(1, 1), expected: { kind: "order", order: { kind: "protect", ward: "unit_0002" } } },
  { name: "order: protect an enemy is ignored", state: order("protect"), tile: p(2, 1), expected: IGNORE },
  { name: "order: focus an enemy", state: order("focus_target"), tile: p(2, 1), expected: { kind: "order", order: { kind: "focus_target", target: "unit_0003" } } },
  { name: "order: hold position takes any tile", state: order("hold_position"), tile: p(3, 2), expected: { kind: "order", order: { kind: "hold_position", at: [3, 2], radius: 1 } } },
  { name: "order: retreat takes any tile", state: order("retreat_to"), tile: p(0, 2), expected: { kind: "order", order: { kind: "retreat_to", at: [0, 2] } } },
  { name: "order pick is skipped when orders are not allowed", state: { ...order("protect"), canOrder: false }, tile: p(2, 1), expected: { kind: "act", action: attack, dismissPin: false } },
  { name: "order pick beats a mode", state: { ...order("retreat_to"), mode: targetMode }, tile: p(3, 2), expected: { kind: "order", order: { kind: "retreat_to", at: [3, 2] } } },
  // 指揮召喚物
  { name: "command: pick a destination", state: { command: command(null) }, tile: p(1, 0), expected: { kind: "command_dest", dest: p(1, 0) } },
  { name: "command: change the destination", state: { command: command(p(1, 0)) }, tile: p(2, 0), expected: { kind: "command_dest", dest: p(2, 0) } },
  { name: "command: a non-option tile is ignored", state: { command: command(null) }, tile: p(3, 2), expected: IGNORE },
  {
    name: "command: foe of the chosen destination moves and attacks",
    state: { command: command(p(2, 0)) },
    tile: p(2, 1),
    expected: {
      kind: "act",
      action: {
        type: "command_summon",
        unit_id: H,
        summon_id: "unit_0006",
        path: [p(1, 0), p(2, 0)],
        target_id: "unit_0003",
      } as unknown as Action,
      dismissPin: false,
    },
  },
  { name: "command: foe that is not a target of the destination is ignored", state: { command: command(p(1, 0)) }, tile: p(2, 1), expected: IGNORE },
  { name: "command is ignored when not my turn", state: { command: command(null), canAct: false }, tile: p(1, 0), expected: pin(p(1, 0)) },
];

describe("decideTileClick", () => {
  it.each(ROWS)("$name", ({ state, tile, expected }) => {
    const got = decideTileClick({ ...BASE, ...state }, tile);
    expect(got).toEqual(expected);
  });

  it("never reads anything but its input (same input, same answer)", () => {
    const state: TileClickState = { ...BASE, mode: targetMode };
    expect(decideTileClick(state, p(3, 2))).toEqual(decideTileClick(state, p(3, 2)));
  });
});
