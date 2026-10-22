import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CLOSE_GRACE_MS, FloatController, OPEN_DELAY_MS, resetFloatRegistry } from "./floatCard";
import { gearFoldLabel } from "./gearFold";
import { TileCardController, cardMaxHeight } from "./hoverCard";

const A = { x: 1, y: 1 };
const B = { x: 2, y: 1 };
const C = { x: 3, y: 1 };

beforeEach(() => {
  vi.useFakeTimers();
  resetFloatRegistry();
});
afterEach(() => vi.useRealTimers());

describe("單位資訊卡：滑過格子", () => {
  it("滑過有內容的格子立即顯示；離開後 250ms 寬限才換成新格子", () => {
    const c = new TileCardController();
    c.setHover(A);
    expect(c.visible).toBe(true);
    expect(c.shown).toEqual(A);
    c.setHover(B);
    vi.advanceTimersByTime(CLOSE_GRACE_MS - 1);
    expect(c.shown).toEqual(A);
    vi.advanceTimersByTime(1);
    expect(c.shown).toEqual(B);
  });

  it("滑向卡片途中經過其他格子，寬限期內保持原卡；進入卡片後不換", () => {
    const c = new TileCardController();
    c.setHover(A);
    c.setHover(B);
    c.setHover(C);
    vi.advanceTimersByTime(100);
    expect(c.shown).toEqual(A);
    c.cardEnter();
    vi.advanceTimersByTime(5000);
    expect(c.shown).toEqual(A);
    expect(c.visible).toBe(true);
  });

  it("離開卡片後有寬限，之後換成滑鼠所在的格子；離開戰場則關閉", () => {
    const c = new TileCardController();
    c.setHover(A);
    c.cardEnter();
    c.setHover(null);
    c.cardLeave();
    vi.advanceTimersByTime(CLOSE_GRACE_MS - 1);
    expect(c.visible).toBe(true);
    vi.advanceTimersByTime(1);
    expect(c.shown).toBeNull();
    expect(c.visible).toBe(false);
  });

  it("寬限期內又滑回原格子就保持原卡", () => {
    const c = new TileCardController();
    c.setHover(A);
    c.setHover(B);
    vi.advanceTimersByTime(100);
    c.setHover(A);
    vi.advanceTimersByTime(1000);
    expect(c.shown).toEqual(A);
  });

  it("沒有內容的格子不顯示卡片", () => {
    const c = new TileCardController();
    c.hasContent = (t) => t.x === 1;
    c.setHover(B);
    expect(c.visible).toBe(false);
    c.setHover(A);
    expect(c.visible).toBe(true);
  });
});

describe("單位資訊卡：釘住與關閉", () => {
  it("點卡片釘住後滑鼠移開、換格子都不關閉，也不換卡", () => {
    const c = new TileCardController();
    c.setHover(A);
    c.pin();
    c.cardLeave();
    c.setHover(B);
    c.setHover(null);
    vi.advanceTimersByTime(5000);
    expect(c.pinned).toBe(true);
    expect(c.shown).toEqual(A);
  });

  it("Esc／點外面（dismiss）關閉並取消釘住；滑鼠換到別的格子才再出現", () => {
    const c = new TileCardController();
    c.setHover(A);
    c.pin();
    c.dismiss();
    expect(c.visible).toBe(false);
    expect(c.pinned).toBe(false);
    c.setHover(B);
    expect(c.shown).toEqual(B);
  });

  it("dismiss 後滑鼠仍在同一格，不會自己跳出來", () => {
    const c = new TileCardController();
    c.setHover(A);
    c.dismiss();
    vi.advanceTimersByTime(5000);
    expect(c.visible).toBe(false);
  });

  it("卡片裡的說明框開著（hold）時不換卡，關掉後才開始計時", () => {
    const c = new TileCardController();
    c.setHover(A);
    c.setHover(B);
    c.hold(1);
    vi.advanceTimersByTime(5000);
    expect(c.shown).toEqual(A);
    c.hold(-1);
    vi.advanceTimersByTime(CLOSE_GRACE_MS);
    expect(c.shown).toEqual(B);
  });

  it("同時只開一張：技能卡開啟會關掉資訊卡，反之亦然", () => {
    const tile = new TileCardController();
    const skill = new FloatController();
    tile.setHover(A);
    skill.triggerEnter();
    vi.advanceTimersByTime(OPEN_DELAY_MS);
    expect(skill.visible).toBe(true);
    expect(tile.visible).toBe(false);
    tile.setHover(B);
    expect(tile.visible).toBe(true);
    expect(skill.visible).toBe(false);
  });
});

describe("最大高度與裝備加成摺疊", () => {
  it("最大高度不超出戰場區與視窗（上下各留 8px），太小時有下限", () => {
    expect(cardMaxHeight(900, 600)).toBe(584);
    expect(cardMaxHeight(400, 900)).toBe(400);
    expect(cardMaxHeight(50, 100)).toBe(120);
  });

  it("裝備加成標題顯示條數與展開狀態", () => {
    expect(gearFoldLabel(5, false)).toBe("▸ 裝備加成（5 條）");
    expect(gearFoldLabel(5, true)).toBe("▾ 裝備加成（5 條）");
  });
});
