// E4b（docs/phases/PhaseE4b計畫.md）：E4 的兩個觸發時機換成美術的圖（docs/art/E4-觸發圖示-美術.md 第 1、6 節；樣張 docs/art/sample/e4Triggers.js）。
import { afterEach, describe, expect, it } from "vitest";
import glossary from "../battle/fixtures/glossary.json";
import { fakeCanvasFactory, type FakeCanvasLog } from "../test/fakeCanvas";
import { setQCanvasFactory, type Ctx, type QOpts } from "./qIcon/core";
import * as QP from "./qIcon/parts";

afterEach(() => setQCanvasFactory(null));

/** 用假畫布畫一次，回傳呼叫紀錄（`halo` 另建的畫布記在同一份）。 */
function calls(draw: (c: Ctx) => void): string[] {
  const log: FakeCanvasLog = { calls: [] };
  const make = fakeCanvasFactory(log);
  setQCanvasFactory((w, h) => make(w, h));
  const cv = make(48, 48);
  draw(cv.getContext("2d") as Ctx);
  return log.calls ?? [];
}
/** 圖樣本身 `cpx` px 的選項（同 `core.render`）。 */
const opts = (cpx: number): QOpts => ({ small: cpx <= 24, tiny: cpx <= 14, owPx: 0, badge: false, u: 48 / (cpx * QP.BOX) });
const draw = (id: string, cpx: number): string => calls((c) => QP.entry("trigger", id).d(c, opts(cpx))).join(";");

describe("E4b 觸發「格擋時」「你讓別人位移時」", () => {
  it("TRIG 有專屬圖、加在最後；TRIG_ALIAS 沒有這兩個；zh 照名詞表", () => {
    expect(Object.keys(QP.TRIG).slice(-2)).toEqual(["on_block", "on_displace"]);
    for (const id of ["on_block", "on_displace"]) {
      expect(QP.TRIG_ALIAS[id], id).toBeUndefined();
      const g = glossary.triggers.find((t) => t.id === id);
      expect(QP.TRIG[id]?.zh, id).toBe(g?.name_zh);
    }
  });
  it("格擋時：一般有劍（劍柄色），tiny 沒有劍、只留盾＋撞擊星；不再畫成被近戰命中時", () => {
    const big = draw("on_block", 19.7);
    const tiny = draw("on_block", 11.8);
    expect(big).toContain("#a8703e");
    expect(tiny).not.toContain("#a8703e");
    for (const s of [big, tiny]) expect(s).toContain("#ffd23f");
    expect(big).not.toEqual(draw("hit_by_melee", 19.7));
  });
  it("你讓別人位移時：紅人形＋米白影子圈；tiny 與一般的呼叫紀錄不同；不再畫成造成撞擊後", () => {
    const big = draw("on_displace", 19.7);
    const tiny = draw("on_displace", 11.8);
    for (const s of [big, tiny]) { expect(s).toContain("#ff5a5a"); expect(s).toContain("#f2e6c8"); }
    expect(tiny).not.toEqual(big);
    expect(big).not.toEqual(draw("on_collision", 19.7));
  });
});
