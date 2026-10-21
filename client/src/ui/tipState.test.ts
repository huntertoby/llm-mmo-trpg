import { describe, expect, it } from "vitest";
import { tipPlacement, tipReduce, tipVisible, TIP_CLOSED, type TipEvent } from "./tipState";

const run = (...events: TipEvent[]) => events.reduce(tipReduce, TIP_CLOSED);

describe("部件說明框的開關", () => {
  it("滑過顯示、移開關閉", () => {
    expect(tipVisible(run("enter"))).toBe(true);
    expect(tipVisible(run("enter", "leave"))).toBe(false);
  });

  it("點一下釘住：移開滑鼠仍然顯示；再點一下取消", () => {
    const pinned = run("enter", "click", "leave");
    expect(pinned).toEqual({ hover: false, pinned: true });
    expect(tipVisible(pinned)).toBe(true);
    expect(tipVisible(run("enter", "click", "click", "leave"))).toBe(false);
  });

  it("觸控沒有滑過，點一下就顯示", () => {
    expect(tipVisible(run("click"))).toBe(true);
  });

  it("Esc 與點外面都會關閉（含釘住的）", () => {
    expect(run("enter", "click", "escape")).toEqual(TIP_CLOSED);
    expect(run("click", "outside")).toEqual(TIP_CLOSED);
  });
});

describe("說明框的位置", () => {
  const view = { width: 800, height: 600 };
  const size = { width: 200, height: 80 };

  it("優先放在部件上方並置中", () => {
    const p = tipPlacement({ left: 300, top: 300, width: 30, height: 30 }, size, view);
    expect(p).toEqual({ left: 215, top: 300 - 80 - 6 });
  });

  it("上方放不下就改放下方", () => {
    const p = tipPlacement({ left: 300, top: 20, width: 30, height: 30 }, size, view);
    expect(p.top).toBe(20 + 30 + 6);
  });

  it("不超出視窗的左右下緣", () => {
    const left = tipPlacement({ left: 0, top: 300, width: 30, height: 30 }, size, view);
    expect(left.left).toBe(4);
    const right = tipPlacement({ left: 790, top: 300, width: 30, height: 30 }, size, view);
    expect(right.left).toBe(800 - 200 - 4);
    const bottom = tipPlacement({ left: 300, top: 590, width: 30, height: 30 }, { width: 200, height: 300 }, view);
    expect(bottom.top + 300).toBeLessThanOrEqual(600);
    expect(bottom.top).toBeGreaterThanOrEqual(4);
  });
});
