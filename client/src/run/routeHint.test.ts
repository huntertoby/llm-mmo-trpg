import { describe, expect, it } from "vitest";
import type { RouteHint } from "../api/types";
import { baseAttributes } from "./flow";
import { routeHintText, topAttribute } from "./routeHint";

const BASE = baseAttributes(10);
const SPELL: RouteHint = {
  lean: "spell",
  fits: ["int"],
  text_zh: "你選的關鍵字多半是法術，建議配一些點到心智屬性（智力），或選有武器技的關鍵字",
};

describe("routeHint（BAL-19g 創角提示）", () => {
  it("最高屬性同分時取六屬性順序在前的", () => {
    expect(topAttribute(BASE, {})).toBe("str");
    expect(topAttribute(BASE, { int: 2, wil: 2 })).toBe("int");
    expect(topAttribute(BASE, { dex: 1, wil: 3 })).toBe("wil");
  });

  it("最高屬性對不上時顯示提示（力量最高卻選雷、暗）", () => {
    expect(routeHintText(SPELL, BASE, { str: 4 })).toBe(SPELL.text_zh);
  });

  it("最高屬性跟得上、還沒配點或沒有提示時不顯示", () => {
    expect(routeHintText(SPELL, BASE, { int: 4 })).toBeNull();
    expect(routeHintText(SPELL, BASE, {})).toBeNull();
    expect(routeHintText(null, BASE, { str: 4 })).toBeNull();
    expect(routeHintText(undefined, BASE, { str: 4 })).toBeNull();
  });
});
