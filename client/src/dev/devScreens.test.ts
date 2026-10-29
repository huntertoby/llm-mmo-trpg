import { describe, expect, it } from "vitest";
import { DEV_SCREENS, devScreenParam } from "./devScreens";

describe("devScreenParam", () => {
  it("只在 ?dev=1 且 screen 合法時回傳畫面", () => {
    for (const s of DEV_SCREENS) expect(devScreenParam(`?dev=1&screen=${s}`)).toBe(s);
    expect(devScreenParam("?screen=level_up")).toBeNull();
    expect(devScreenParam("?dev=0&screen=level_up")).toBeNull();
    expect(devScreenParam("?dev=1&screen=nope")).toBeNull();
    expect(devScreenParam("?dev=1")).toBeNull();
  });
});
