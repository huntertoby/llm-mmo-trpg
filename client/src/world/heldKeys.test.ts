import { describe, expect, it } from "vitest";
import { HeldKeys } from "./heldKeys";

const nodeFs = "node:fs";
const { readFileSync } = (await import(/* @vite-ignore */ nodeFs)) as { readFileSync: (p: string, enc: string) => string };

describe("WM-1 按住連走（HeldKeys）", () => {
  it("按住時每一格都拿得到方向，不必等作業系統的重複（第 1、2 步之間不停頓）", () => {
    const keys = new HeldKeys();
    expect(keys.press("right", false)).toBe(true);
    // 沒有任何 repeat 事件：走路迴圈每播完一格問一次，都還是 right
    expect([keys.take(), keys.take(), keys.take()]).toEqual(["right", "right", "right"]);
  });

  it("作業系統的重複（e.repeat）不算新的按下", () => {
    const keys = new HeldKeys();
    expect(keys.press("up", true)).toBe(false);
    expect(keys.take()).toBeNull();
  });

  it("放開後不會多走：放開之後下一次就停", () => {
    const keys = new HeldKeys();
    keys.press("left", false);
    expect(keys.take()).toBe("left"); // 正在播的那一格
    keys.release("left");
    expect(keys.take()).toBeNull();
  });

  it("按下馬上放開（點按）也走一格，而且只走一格", () => {
    const keys = new HeldKeys();
    keys.press("down", false);
    keys.release("down");
    expect(keys.take()).toBe("down");
    expect(keys.take()).toBeNull();
  });

  it("同時按兩個方向：最後按的優先，放開它就回到前一個", () => {
    const keys = new HeldKeys();
    keys.press("up", false);
    keys.press("right", false);
    expect(keys.take()).toBe("right");
    keys.release("right");
    expect(keys.take()).toBe("up");
  });

  it("視窗失焦（clear）時停止，連沒用掉的點按也丟掉", () => {
    const keys = new HeldKeys();
    keys.press("up", false);
    keys.clear();
    expect(keys.active).toBeNull();
    expect(keys.take()).toBeNull();
  });

  it("WorldField 聽 keyup、blur、visibilitychange，並濾掉 e.repeat", () => {
    const src = readFileSync("src/world/WorldField.tsx", "utf-8");
    expect(src).toContain('addEventListener("keyup"');
    expect(src).toContain('addEventListener("blur"');
    expect(src).toContain('addEventListener("visibilitychange"');
    expect(src).toContain("keys.current.press(dir, e.repeat)");
    expect(src).not.toContain("KEY_QUEUE_MAX");
  });
});
