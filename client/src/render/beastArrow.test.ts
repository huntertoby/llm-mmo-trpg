// QK-3b（docs/art/QK-3檢查.md 第 3 節）：四足召喚物（戰狼）也要有面向箭頭；被頭蓋住就移到底圈前緣。
import { describe, expect, it } from "vitest";
import { arrowAboveBody, arrowRing, facingArrowPoly } from "./unitSprite";

const wolf = (facing: "north" | "south" | "east" | "west") => ({ facing, summon: true, summonLook: { body: "beast", variant: "wolf", size: "medium" }, dollLook: null }) as never;
const human = (facing: "north" | "south" | "east" | "west") => ({ facing, summon: false, summonLook: null, dollLook: null }) as never;

describe("四足召喚物的面向箭頭", () => {
  it("貼在召喚物放寬、往頭移的底圈前緣：朝東尖端比一般單位遠、朝西往負 x 遠", () => {
    const ring = arrowRing(wolf("east"));
    const base = arrowRing(human("east"));
    expect(ring.rx).toBeGreaterThan(base.rx);
    expect(ring.cx).toBeGreaterThan(0);
    expect(facingArrowPoly(wolf("east"))[0]!).toBeGreaterThan(facingArrowPoly(human("east"))[0]!);
    expect(facingArrowPoly(wolf("west"))[0]!).toBeLessThan(facingArrowPoly(human("west"))[0]!);
  });

  it("朝北時底圈後緣被身體蓋住：箭頭畫在身體上面；其他方向、人形照舊畫在地上", () => {
    expect(arrowAboveBody(wolf("north"))).toBe(true);
    for (const f of ["south", "east", "west"] as const) expect(arrowAboveBody(wolf(f))).toBe(false);
    expect(arrowAboveBody(human("north"))).toBe(false);
  });

  it("人形單位的箭頭位置不變", () => {
    expect(arrowRing(human("east"))).toMatchObject({ cx: 0 });
  });
});
