// Phase 3-24a2：裝填（武器動作）——只在空膛時出現在「更多動作」選單，不算進基本動作的 10 個上限；彈匣顯示。
import { describe, expect, it } from "vitest";
import type { Action } from "../api/types";
import { actionLabel } from "./actions";
import { ammoPips, ammoText, hasMagazine } from "./ammo";
import {
  basicModes,
  BASIC_ACTION_KINDS,
  BASIC_ACTION_LIMIT,
  BASIC_MODES,
  moreModes,
  MORE_KINDS,
  RESIDENT_KINDS,
  TRAY_KINDS,
  WEAPON_ACTION_KINDS,
} from "./targeting";
import { smallView, unit } from "./testFixtures";

const H = "unit_0001";
const FOE = "unit_0003";
const hero = unit(H, "ally", 1, 1, { weapon_id: "longgun", weapon_class: "ranged", ammo: 0, magazine: 1 });
const view = smallView({ units: [hero, unit(FOE, "enemy", 5, 1)] });
const reload = { type: "reload", unit_id: H } as Action;
const aim = { type: "aim", unit_id: H } as Action;

describe("裝填（Phase 3-24a2）", () => {
  it("空膛時裝填出現在「更多動作」，標籤是「裝填」，是不需要目標的即時動作", () => {
    const modes = basicModes([reload]);
    const more = moreModes(modes);
    expect(more.map((m) => m.kind)).toEqual(["reload"]);
    expect(more[0]!.label).toBe("裝填");
    expect(more[0]!.targets.self).toBe(reload);
    expect(actionLabel(reload, view, {})).toBe("裝填");
  });

  it("滿膛（伺服器沒有列出裝填）時選單裡沒有它", () => {
    expect(moreModes(basicModes([aim])).map((m) => m.kind)).toEqual(["aim"]);
    expect(moreModes(basicModes([]))).toEqual([]);
  });

  it("裝填是武器動作：不在基本動作的清單裡，基本動作仍不超過 10 個", () => {
    expect(WEAPON_ACTION_KINDS).toEqual(["reload"]);
    expect(BASIC_ACTION_KINDS).not.toContain("reload");
    expect(BASIC_ACTION_KINDS.length).toBeLessThanOrEqual(BASIC_ACTION_LIMIT);
    expect(BASIC_ACTION_KINDS.length + WEAPON_ACTION_KINDS.length).toBeLessThanOrEqual(BASIC_ACTION_LIMIT + 1);
  });

  it("常駐、選單、技能列的按鈕分配沒有重疊，而且涵蓋所有模式（含裝填）", () => {
    const all = [...RESIDENT_KINDS, ...MORE_KINDS, ...TRAY_KINDS];
    expect(new Set(all).size).toBe(all.length);
    expect(all).toContain("reload");
    expect(BASIC_MODES.map((m) => m.kind).sort()).toEqual([...all].sort());
  });
});

describe("彈匣顯示", () => {
  it("有彈匣才顯示；格數＝容量、裝著子彈的格子在前", () => {
    expect(hasMagazine(hero)).toBe(true);
    expect(hasMagazine(unit("u", "ally", 0, 0))).toBe(false);
    expect(ammoPips(1, 1)).toEqual([true]);
    expect(ammoPips(0, 1)).toEqual([false]);
    expect(ammoPips(1, 2)).toEqual([true, false]);
    expect(ammoPips(5, 2)).toEqual([true, true]);
    expect(ammoPips(0, 0)).toEqual([]);
  });

  it("文字：滿膛顯示 1/1，空膛提示要裝填", () => {
    expect(ammoText({ ammo: 1, magazine: 1 })).toBe("彈匣 1/1");
    expect(ammoText({ ammo: 0, magazine: 1 })).toBe("彈匣 0/1（空膛，需要裝填）");
  });
});
