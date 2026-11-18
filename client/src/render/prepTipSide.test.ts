// SK-3b 第 14 項（美術 AR-SK3 驗收）：戰前佈置的「放在這裡」預設畫在格子右邊，會超出地圖右緣時翻到左邊。
import { describe, expect, it } from "vitest";

import { tipPlacement } from "./prepMarks";

describe("戰前佈置提示框的位置", () => {
  it("放得下就在格子右邊", () => {
    expect(tipPlacement(0, 1, 2, 10)).toEqual({ side: "right", x: 1 });
    expect(tipPlacement(7, 1, 2, 10)).toEqual({ side: "right", x: 8 }); // 剛好貼齊右緣
  });

  it("右邊會超出地圖就翻到左邊", () => {
    expect(tipPlacement(8, 1, 2, 10)).toEqual({ side: "left", x: 6 });
    expect(tipPlacement(9, 1, 2.5, 10)).toEqual({ side: "left", x: 6.5 });
  });

  it("不知道地圖寬時照舊放右邊", () => {
    expect(tipPlacement(99, 1, 2, Infinity)).toEqual({ side: "right", x: 100 });
  });
});
