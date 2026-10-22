import { describe, expect, it } from "vitest";
import { HIGHLIGHT } from "../battle/glossary";
import { downedLook, GRAVE_GRAY, LOST_RING, pulseAlpha, statusBadges, summonBadgeOffset, SUMMON_BADGE_RADIUS, SUMMON_BADGE_FONT } from "./unitLook";
import { statusColor } from "./skillParts";

describe("downedLook（倒地圖示，不含文字）", () => {
  it("站著：沒有徽章、虛線圈，小人不透明", () => {
    const look = downedLook(false, true); // revivable 對站著的單位沒有意義
    expect(look).toMatchObject({ state: "up", dollAlpha: 1, grayscale: false, ring: null, badge: null, dashed: null });
  });

  it("可復活：綠愛心徽章、綠色虛線橢圓閃動、小人原色透明度 0.6、底圈沿用隊伍色", () => {
    const look = downedLook(true, true);
    expect(look.state).toBe("revivable");
    expect(look.badge).toEqual({ kind: "heart", edge: HIGHLIGHT.revive, glyph: HIGHLIGHT.revive });
    expect(look.dollAlpha).toBe(0.6);
    expect(look.grayscale).toBe(false);
    expect(look.ring).toBeNull();
    expect(look.dashed).toMatchObject({ color: HIGHLIGHT.revive, minAlpha: 0.4, maxAlpha: 1, periodMs: 1500 });
  });

  it("救不回：灰墓碑徽章、小人去色透明度 0.45、灰底圈、沒有虛線圈", () => {
    const look = downedLook(true, false);
    expect(look.state).toBe("lost");
    expect(look.badge).toEqual({ kind: "grave", edge: GRAVE_GRAY, glyph: GRAVE_GRAY });
    expect(look.dollAlpha).toBe(0.45);
    expect(look.grayscale).toBe(true);
    expect(look.ring).toEqual(LOST_RING);
    expect(look.dashed).toBeNull();
  });

  it("繪製資料裡沒有任何字串欄位帶文字（沒有紅叉、「倒」、「倒·復」）", () => {
    for (const look of [downedLook(true, true), downedLook(true, false)]) {
      const json = JSON.stringify(look);
      expect(json).not.toMatch(/倒|復|叉/);
    }
  });

  it("虛線圈的透明度在 0.4 與 1 之間以 1.5 秒為週期往返", () => {
    const dashed = downedLook(true, true).dashed!;
    expect(pulseAlpha(dashed, 0)).toBeCloseTo(0.4);
    expect(pulseAlpha(dashed, 750)).toBeCloseTo(1);
    expect(pulseAlpha(dashed, 1500)).toBeCloseTo(0.4);
    for (let ms = 0; ms < 3000; ms += 100) {
      const a = pulseAlpha(dashed, ms);
      expect(a).toBeGreaterThanOrEqual(0.4 - 1e-9);
      expect(a).toBeLessThanOrEqual(1 + 1e-9);
    }
  });
});

describe("statusBadges（戰場狀態徽章對應部件庫）", () => {
  it("沒有炸彈或蓄力就沒有徽章", () => {
    expect(statusBadges({ bomb: null })).toEqual([]);
    expect(statusBadges({ bomb: null, charge: null })).toEqual([]);
  });

  it("定時炸彈用 time_bomb、蓄力用 charging，數字是剩餘次數", () => {
    const badges = statusBadges({ bomb: 2, charge: 1 });
    expect(badges.map((b) => [b.statusId, b.count])).toEqual([
      ["time_bomb", 2],
      ["charging", 1],
    ]);
  });

  it("徽章用的狀態都是部件庫認得的狀態（有專屬顏色）", () => {
    for (const b of statusBadges({ bomb: 1, charge: 1 })) expect(statusColor(b.statusId)).not.toBe("#d8d8e0");
  });
});

describe("召喚物徽章位置（3-33h2）", () => {
  it("在右下（T×0.36, T×0.14），半徑 7、字級 10；有炸彈徽章時往左 16px", () => {
    expect(summonBadgeOffset({ bomb: null }, 50).y).toBeCloseTo(7);
    expect(summonBadgeOffset({ bomb: null }, 50).x).toBeCloseTo(18);
    expect(summonBadgeOffset({ bomb: 2 }, 50).x).toBeCloseTo(2);
    expect(SUMMON_BADGE_RADIUS).toBe(7);
    expect(SUMMON_BADGE_FONT).toBe(10);
  });
});
