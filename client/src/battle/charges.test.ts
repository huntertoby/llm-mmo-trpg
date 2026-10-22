// Phase 3G-G3a：裝備充能——層數顯示、啟動按鈕只在伺服器列出（層數與 AP 足夠）時出現在「更多動作」。
import { describe, expect, it } from "vitest";
import type { Action, ChargeView } from "../api/types";
import { actionLabel } from "./actions";
import { chargePips, chargeText } from "./charges";
import { basicModes, chargeModes, fallbackActions, moreModes, MORE_KINDS, RESIDENT_KINDS, TRAY_KINDS } from "./targeting";
import { smallView, unit } from "./testFixtures";

const H = "unit_0001";
const FOE = "unit_0002";

const static_: ChargeView = {
  affix_id: "affix_charge_static",
  name_zh: "靜電終結",
  stack_id: "static_charge",
  stack_name_zh: "靜電",
  stacks: 3,
  max_stacks: 3,
  cost_stacks: 3,
  cost_ap: 1,
  needs_target: true,
  ready: true,
};
const fury: ChargeView = {
  affix_id: "affix_charge_fury",
  name_zh: "怒氣爆發",
  stack_id: "fury",
  stack_name_zh: "怒氣",
  stacks: 4,
  max_stacks: 4,
  cost_stacks: 4,
  cost_ap: 0,
  needs_target: false,
  ready: true,
};

const hero = unit(H, "ally", 1, 1, { charges: [static_, fury] });
const view = smallView({ units: [hero, unit(FOE, "enemy", 2, 1)] });
const staticAct = { type: "activate_charge", unit_id: H, affix_id: static_.affix_id, target_id: FOE } as Action;
const furyAct = { type: "activate_charge", unit_id: H, affix_id: fury.affix_id } as Action;
const aim = { type: "aim", unit_id: H } as Action;

describe("裝備充能的顯示", () => {
  it("層數格子依裝備版上限，已累積的在前", () => {
    expect(chargePips({ stacks: 2, max_stacks: 3 })).toEqual([true, true, false]);
    expect(chargePips({ stacks: 0, max_stacks: 0 })).toEqual([]);
  });

  it("文字說明層數與啟動花費；層數足夠時標示可啟動", () => {
    expect(chargeText({ ...static_, stacks: 2, ready: false })).toBe("靜電 2/3（啟動：3 層＋1 AP）");
    expect(chargeText(static_)).toBe("靜電 3/3（可啟動：3 層＋1 AP）");
    expect(chargeText(fury)).toBe("怒氣 4/4（可啟動：4 層）");
  });
});

describe("啟動按鈕", () => {
  it("每條充能詞條一個模式，放在「更多動作」最後；標籤含層數與 AP 花費", () => {
    const modes = basicModes([aim, staticAct, furyAct], hero.charges);
    const more = moreModes(modes);
    expect(more.map((m) => m.key)).toEqual(["aim", "charge:affix_charge_fury", "charge:affix_charge_static"]);
    expect(more.map((m) => m.label)).toEqual(["瞄準", "啟動怒氣（4 層）", "啟動靜電（3 層＋1 AP）"]);
  });

  it("需要目標的充能點敵人，作用在自己的是「自身」模式", () => {
    const [furyMode, staticMode] = chargeModes([staticAct, furyAct], hero.charges);
    expect(furyMode!.targets.self).toBe(furyAct);
    expect(staticMode!.targets.units.get(FOE)).toBe(staticAct);
    expect(staticMode!.targets.self).toBeNull();
  });

  it("伺服器沒有列出（層數或 AP 不足）時選單裡沒有它", () => {
    expect(moreModes(basicModes([aim], hero.charges)).map((m) => m.kind)).toEqual(["aim"]);
    expect(chargeModes([], hero.charges)).toEqual([]);
  });

  it("不是備援清單的動作；不佔常駐、選單、技能列的按鈕分配", () => {
    expect(fallbackActions([staticAct, furyAct], hero)).toEqual([]);
    const all = [...RESIDENT_KINDS, ...MORE_KINDS, ...TRAY_KINDS];
    expect(all).not.toContain("charge");
  });

  it("沒有詞條資料時退回通用標籤；動作標籤含目標", () => {
    expect(chargeModes([staticAct])[0]!.label).toBe("啟動充能 affix_charge_static");
    expect(actionLabel(staticAct, view, {})).toContain("啟動靜電（3 層＋1 AP）");
    expect(actionLabel(furyAct, view, {})).toBe("啟動怒氣（4 層）");
  });
});
