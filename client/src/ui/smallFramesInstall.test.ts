// HID-1b（四角飾件的舊 FAIL）：戰鬥主角卡（`data-rt-compact`）的小框標記不能只靠 ResizeObserver 的回呼：
// 背景分頁、隱藏的預覽窗不跑算繪幀，回呼不來，卡片就一直是大飾件＋原內距，左下飾件壓到第一個小圖示。
import { describe, expect, it } from "vitest";
import { installSmallFrames } from "./smallFrames";

class FakeEl {
  readonly classList = { contains: (name: string) => name === "rt-frame" };
  readonly style = { paddingLeft: "", paddingRight: "" };
  constructor(
    readonly dataset: Record<string, string | undefined>,
    readonly offsetHeight: number,
  ) {}
  querySelectorAll(): FakeEl[] {
    return [];
  }
}

/** 回呼永遠不來的 ResizeObserver（背景分頁的行為）。 */
class SilentResizeObserver {
  observe(): void {}
}
class NoopMutationObserver {
  observe(): void {}
}

function install(el: FakeEl): void {
  const win = {
    ResizeObserver: SilentResizeObserver,
    MutationObserver: NoopMutationObserver,
    Element: FakeEl,
    HTMLElement: FakeEl,
    getComputedStyle: () => ({ paddingLeft: "10px", paddingRight: "10px" }),
  };
  const doc = { defaultView: win, body: {}, querySelectorAll: () => [el] };
  installSmallFrames(doc as unknown as Document);
}

describe("HID-1b：小框標記不等 ResizeObserver 回呼", () => {
  it("資訊塊本身是小框（戰鬥主角卡）：一看到就標好、內距讓出飾件，就算回呼永遠不來", () => {
    const card = new FakeEl({ rtCompact: "true" }, 148);
    install(card);
    expect(card.dataset.rtSmall).toBe("true");
    expect(card.style.paddingLeft).toBe("16px");
    expect(card.style.paddingRight).toBe("16px");
  });

  it("一般的高框不會被標成小框", () => {
    const tall = new FakeEl({}, 148);
    install(tall);
    expect(tall.dataset.rtSmall).toBeUndefined();
    expect(tall.style.paddingLeft).toBe("");
  });

  it("還沒排版（高度 0）的一般框不動，留給之後的回呼", () => {
    const empty = new FakeEl({}, 0);
    install(empty);
    expect(empty.dataset.rtSmall).toBeUndefined();
  });
});
