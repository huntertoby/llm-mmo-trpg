// X10-3b：數值工坊的一次性換算提示（關掉後記在瀏覽器；儲存壞掉時照樣顯示）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { readFile, SRC_DIR, stripTsComments } from "../test/sourceScan";
import { dismissScaleNotice, SCALE_NOTICE_KEY, SCALE_NOTICE_ZH, ScaleNotice, scaleNoticeDismissed, type StorageLike } from "./ScaleNotice";

function memory(): StorageLike & { data: Map<string, string> } {
  const data = new Map<string, string>();
  return { data, getItem: (k) => data.get(k) ?? null, setItem: (k, v) => void data.set(k, v) };
}

const broken: StorageLike = {
  getItem: () => {
    throw new Error("blocked");
  },
  setItem: () => {
    throw new Error("blocked");
  },
};

describe("數值工坊換算提示", () => {
  it("字照計畫", () => {
    expect(SCALE_NOTICE_ZH).toBe("數值已整體放大 10 倍（2026-11-20）；舊的 5 現在是 50。");
  });

  it("沒關過時顯示；關掉後記住、不再顯示", () => {
    const store = memory();
    expect(scaleNoticeDismissed(store)).toBe(false);
    expect(renderToStaticMarkup(createElement(ScaleNotice, { storage: store }))).toContain(SCALE_NOTICE_ZH);
    dismissScaleNotice(store);
    expect(store.data.get(SCALE_NOTICE_KEY)).toBe("1");
    expect(scaleNoticeDismissed(store)).toBe(true);
    expect(renderToStaticMarkup(createElement(ScaleNotice, { storage: store }))).toBe("");
  });

  it("儲存壞掉或沒有儲存時照樣顯示，關掉也不會丟錯", () => {
    expect(scaleNoticeDismissed(broken)).toBe(false);
    expect(() => dismissScaleNotice(broken)).not.toThrow();
    expect(renderToStaticMarkup(createElement(ScaleNotice, { storage: broken }))).toContain(SCALE_NOTICE_ZH);
    expect(renderToStaticMarkup(createElement(ScaleNotice, { storage: null }))).toContain(SCALE_NOTICE_ZH);
  });

  it("數值工坊頁面放了提示", () => {
    const screen = stripTsComments(readFile(SRC_DIR, "screens/TuningScreen.tsx"));
    expect(screen).toContain("<ScaleNotice />");
  });
});
