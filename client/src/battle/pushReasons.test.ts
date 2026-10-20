import { describe, expect, it } from "vitest";
import type { Action, InteractOption } from "../api/types";
import { blockedPushAt, pushBlockers, pushReasonText, withPushReasons } from "./pushReasons";
import { actionAtTile, basicModes } from "./targeting";
import { smallView, unit } from "./testFixtures";

const H = "unit_0001";
const hero = unit(H, "ally", 1, 1, {});
// 測試視圖：obj_0002（木箱）在 (1, 2)，也就是主角正南方；obj_0001（油桶）在 (2, 2)
const view = smallView({ units: [hero] });
const push = (id: string, legal: boolean, reason: string | null): InteractOption => ({
  object_id: id,
  mode: "push",
  side: null,
  legal,
  reason,
  to_pos: { x: 1, y: 3 },
});
const pushAction = (id: string): Action => ({ type: "interact", unit_id: H, object_id: id, mode: "push" }) as Action;
const defend = { type: "defend", unit_id: H } as Action;

describe("push reasons", () => {
  it("adds a greyed push button with the reason when nothing is legal", () => {
    const options = [push("obj_0002", false, "推不動：木箱後方有單位")];
    const modes = withPushReasons(basicModes([]), options, view);
    expect(modes.map((m) => m.kind)).toEqual(["interact"]);
    expect(modes[0]!.label).toBe("推動物件");
    expect(modes[0]!.blockedReason).toBe("推不動：木箱後方有單位");
    expect(modes[0]!.actions).toEqual([]);
  });

  it("prefixes reasons that do not say why it cannot be pushed (height, AP)", () => {
    const blockers = pushBlockers([
      push("obj_0002", false, "高度差過大：相差 3 層（上限 1 層）"),
      push("obj_0001", false, "AP 不足：需要 1，目前 0"),
    ]);
    expect(blockers.get("obj_0002")).toBe("推不動：高度差過大：相差 3 層（上限 1 層）");
    expect(blockers.get("obj_0001")).toBe("推不動：AP 不足：需要 1，目前 0");
    expect(pushReasonText(blockers, view)).toContain("；");
  });

  it("keeps the legal mode and attaches the blocked neighbours; clicking one yields its reason", () => {
    const legal = [pushAction("obj_0001")];
    const options = [push("obj_0001", true, null), push("obj_0002", false, "推不動：木箱後方有單位")];
    const modes = withPushReasons(basicModes(legal), options, view);
    const mode = modes.find((m) => m.kind === "interact")!;
    expect(mode.blockedReason).toBeUndefined();
    expect(actionAtTile(mode, view, hero, { x: 2, y: 2 })).toBe(legal[0]);
    expect(blockedPushAt(mode, view, { x: 1, y: 2 })).toContain("後方有單位");
    expect(blockedPushAt(mode, view, { x: 2, y: 2 })).toBeNull();
  });

  it("changes nothing when all pushes are legal, and keeps the button order", () => {
    const legal: Action[] = [defend, pushAction("obj_0001")];
    const modes = withPushReasons(basicModes(legal), [push("obj_0001", true, null)], view);
    expect(modes.map((m) => m.kind)).toEqual(["interact", "defend"]);
    expect(modes.every((m) => m.blockedReason === undefined && m.blockedObjects === undefined)).toBe(true);
    const blocked = withPushReasons(basicModes([defend]), [push("obj_0002", false, "x")], view);
    expect(blocked.map((m) => m.kind)).toEqual(["interact", "defend"]);
  });
});
