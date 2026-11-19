// AR-AP2（docs/phases/PhaseAR-AP2計畫.md）：預支三樣暫借換成美術的圖（docs/art/AP-2-美術.md 第 1 節、5.1、5.2；樣張 docs/art/sample/ap2Borrow.js）。
import { afterEach, describe, expect, it } from "vitest";
import { fakeCanvasFactory, type FakeCanvasLog } from "../test/fakeCanvas";
import { setQCanvasFactory, type Ctx, type QOpts } from "./qIcon/core";
import * as QP from "./qIcon/parts";
import * as QT from "./qIcon/status";

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
/** 圖樣本身 `cpx` px 的選項（同 `core.render`：u＝48 ÷ 圖樣格邊長＝48 ÷ (cpx × BOX)）。 */
const opts = (cpx: number): QOpts => ({ small: cpx <= 24, tiny: cpx <= 14, owPx: 0, badge: false, u: 48 / (cpx * QP.BOX) });

describe("1. 狀態「預支」borrowed_ap", () => {
  it("和效果「預支」同一個函式（borrowArt）；不再畫透支的黃閃電", () => {
    const d = QT.NEW.borrowed_ap!.d;
    for (const cpx of [20, 12.4, 10.4, 6.4]) {
      const o = opts(cpx);
      expect(calls((c) => d(c, o))).toEqual(calls((c) => QP.borrowArt(c, o)));
    }
    expect(calls((c) => d(c, opts(12.4))).join(";")).not.toContain("#ffd23a");
  });
  it("頭頂 11（圖樣本身 <8 px）只留菱形、中間挖一個深色小菱形；狀態卡 20、說明行 16 是菱形＋右下那格", () => {
    const head = calls((c) => QP.borrowArt(c, opts(6.4))).join(";");
    expect(head).toContain("#ff9a3a");
    expect(head).toContain("#16121a");
    expect(head).not.toContain("#b3a994"); /* 沒有那格的灰框 */
    const card = calls((c) => QP.borrowArt(c, opts(12.4))).join(";");
    expect(card).toContain("#b3a994");
    expect(card).toContain("#ff4a5a");
  });
  it("色：亮面、桌面、那格的框照混色算（#ffc793、#ffac5d、#b3a994）", () => {
    expect(QP.BORROW.hi).toBe("#ffc793");
    expect(QP.SLOT_ICON.ring).toBe("#b3a994");
    expect(calls((c) => QP.gem(c, { tiny: false }, 0, 0, 10)).join(";")).toContain("#ffac5d");
  });
});
