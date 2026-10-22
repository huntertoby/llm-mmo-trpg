import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CLOSE_GRACE_MS, FloatController, OPEN_DELAY_MS, floatPlacement, resetFloatRegistry } from "./floatCard";

beforeEach(() => {
  vi.useFakeTimers();
  resetFloatRegistry();
});
afterEach(() => vi.useRealTimers());

describe("滑過的延遲與寬限", () => {
  it("滑過約 150ms 才顯示；太快滑過不顯示", () => {
    const c = new FloatController();
    c.triggerEnter();
    vi.advanceTimersByTime(OPEN_DELAY_MS - 1);
    expect(c.visible).toBe(false);
    vi.advanceTimersByTime(1);
    expect(c.visible).toBe(true);
    const d = new FloatController();
    d.triggerEnter();
    vi.advanceTimersByTime(OPEN_DELAY_MS - 50);
    d.triggerLeave();
    vi.advanceTimersByTime(1000);
    expect(d.visible).toBe(false);
  });

  it("離開按鈕後有 250ms 寬限，之後才關", () => {
    const c = new FloatController();
    c.triggerEnter();
    vi.advanceTimersByTime(OPEN_DELAY_MS);
    c.triggerLeave();
    vi.advanceTimersByTime(CLOSE_GRACE_MS - 1);
    expect(c.visible).toBe(true);
    vi.advanceTimersByTime(1);
    expect(c.visible).toBe(false);
  });

  it("寬限期間滑進卡片（橋接區也算卡片）就保持開著，離開卡片後才重新計時", () => {
    const c = new FloatController();
    c.triggerEnter();
    vi.advanceTimersByTime(OPEN_DELAY_MS);
    c.triggerLeave();
    vi.advanceTimersByTime(CLOSE_GRACE_MS - 10);
    c.cardEnter();
    vi.advanceTimersByTime(5000);
    expect(c.visible).toBe(true);
    c.cardLeave();
    vi.advanceTimersByTime(CLOSE_GRACE_MS);
    expect(c.visible).toBe(false);
  });

  it("寬限期間又滑回按鈕也保持開著", () => {
    const c = new FloatController();
    c.triggerEnter();
    vi.advanceTimersByTime(OPEN_DELAY_MS);
    c.triggerLeave();
    vi.advanceTimersByTime(100);
    c.triggerEnter();
    vi.advanceTimersByTime(5000);
    expect(c.visible).toBe(true);
  });

  it("卡片內的部件說明框開著時，卡片不關；說明框關了才開始計時", () => {
    const c = new FloatController();
    c.triggerEnter();
    vi.advanceTimersByTime(OPEN_DELAY_MS);
    c.triggerLeave();
    c.cardEnter();
    c.hold(1);
    c.cardLeave();
    vi.advanceTimersByTime(5000);
    expect(c.visible).toBe(true);
    c.hold(-1);
    vi.advanceTimersByTime(CLOSE_GRACE_MS);
    expect(c.visible).toBe(false);
  });
});

describe("釘住、Esc、點外面、焦點", () => {
  it("點一下釘住：移開滑鼠仍顯示；再點一下取消", () => {
    const c = new FloatController();
    c.triggerEnter();
    vi.advanceTimersByTime(OPEN_DELAY_MS);
    c.click(true);
    c.triggerLeave();
    vi.advanceTimersByTime(5000);
    expect(c.visible).toBe(true);
    c.click(true);
    expect(c.pinned).toBe(false);
  });

  it("觸控沒有滑過，點一下就顯示；點卡片只會釘住不會取消", () => {
    const c = new FloatController();
    c.click(true);
    expect(c.visible).toBe(true);
    c.click(false);
    expect(c.pinned).toBe(true);
  });

  it("dismiss（Esc、點外面）全部關掉，含釘住的", () => {
    const c = new FloatController();
    c.triggerEnter();
    vi.advanceTimersByTime(OPEN_DELAY_MS);
    c.click(true);
    c.dismiss();
    expect(c.visible).toBe(false);
  });

  it("取得焦點就顯示，失去焦點關閉", () => {
    const c = new FloatController();
    c.focusIn();
    expect(c.visible).toBe(true);
    c.focusOut();
    expect(c.visible).toBe(false);
  });
});

describe("同時只開一張", () => {
  it("新的取代舊的（含釘住的）", () => {
    const a = new FloatController();
    const b = new FloatController();
    a.click(true);
    expect(a.visible).toBe(true);
    b.triggerEnter();
    vi.advanceTimersByTime(OPEN_DELAY_MS);
    expect(b.visible).toBe(true);
    expect(a.visible).toBe(false);
  });

  it("卡片內的部件說明框（nested）不會取代外面的卡片", () => {
    const card = new FloatController();
    const part = new FloatController(true);
    card.click(true);
    part.triggerEnter();
    vi.advanceTimersByTime(OPEN_DELAY_MS);
    expect(part.visible).toBe(true);
    expect(card.visible).toBe(true);
  });
});

describe("位置", () => {
  const view = { width: 800, height: 600 };
  const size = { width: 380, height: 200 };

  it("預設貼在觸發元素上方、無空隙、左緣對齊", () => {
    const p = floatPlacement({ left: 100, top: 500, width: 60, height: 40 }, size, view);
    expect(p).toEqual({ left: 100, top: 300, side: "above" });
  });

  it("上方放不下就翻到下方", () => {
    const p = floatPlacement({ left: 100, top: 50, width: 60, height: 40 }, size, view);
    expect(p).toEqual({ left: 100, top: 90, side: "below" });
  });

  it("靠右邊時往內推，仍與觸發元素水平重疊（不會有空隙）", () => {
    const anchor = { left: 760, top: 500, width: 30, height: 30 };
    const p = floatPlacement(anchor, size, view);
    expect(p.left + size.width).toBeLessThanOrEqual(view.width - 4);
    expect(p.left).toBeLessThanOrEqual(anchor.left);
    expect(p.left + size.width).toBeGreaterThanOrEqual(anchor.left + anchor.width);
  });

  it("靠左邊不超出畫面；置中對齊也會被夾住", () => {
    expect(floatPlacement({ left: -20, top: 500, width: 30, height: 30 }, size, view).left).toBe(4);
    expect(floatPlacement({ left: 0, top: 500, width: 30, height: 30 }, size, view, "center").left).toBe(4);
  });

  it("兩邊都放不下就選空間大的一邊，且不超出視窗", () => {
    const tall = { width: 300, height: 500 };
    const p = floatPlacement({ left: 100, top: 250, width: 40, height: 40 }, tall, view);
    expect(p.top).toBeGreaterThanOrEqual(4);
    expect(p.top + tall.height).toBeLessThanOrEqual(view.height - 4);
  });
});
