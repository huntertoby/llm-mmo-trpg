// E6-b2 招牌效果的前端：灰字長短版用在哪裡、名額計數、已滿提示、一次性強調只播一次、減少動態時不播、背包滿時的小標。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it } from "vitest";
import type { GearCandidate, GearItemInfo, SignaturePanel, SignatureRow, WorldBagItem } from "../api/types";
import { itemLines, itemTipLines } from "../run/gearOffer";
import { GearCardView } from "../ui/gear/GearCardView";
import { SignaturePicker } from "../ui/gear/SignaturePicker";
import { resetMotionPrefMemo, saveMotionPref } from "../ui/motionPrefs";
import { LootChoicePanel } from "../world/LootChoicePanel";
import { clickRow, countText, markFxShown, overCap, resetFxShown, rowChecked, signatureLine } from "./signature";

const LONG = "身上已經有 3 個招牌效果生效，這個沒有效果，可以在角色面板換選";
const SHORT = "已經有 3 個生效，這個沒有效果";
const FULL = "已經有 3 個生效，先取消勾選一個，再勾這個。";

function item(over: Partial<GearItemInfo> = {}): GearItemInfo {
  return {
    id: "item_e6b2_hook",
    name_zh: "勾魂鐮",
    slot_type: "hands",
    affixes: [
      {
        affix_id: "affix_act_grapple",
        text_zh: "解鎖「鉤爪」：1 AP、冷卻 3，把 4 格內的目標拉近 3 格",
        signature: "action",
        signature_zh: "招牌・新動作",
        signature_name_zh: "鉤爪",
      },
      { affix_id: "affix_attr_str", text_zh: "力量 +3" },
    ],
    offhand_traits_zh: [],
    tags: [],
    two_handed: false,
    paired: false,
    legendary: false,
    rarity: "rare",
    rarity_zh: "稀有",
    item_level: 12,
    points: 24,
    ...over,
  } as unknown as GearItemInfo;
}

function cand(it: GearItemInfo): GearCandidate {
  return { item: it, slot: "hands", slot_zh: "手", current: null, notes_zh: [] } as unknown as GearCandidate;
}

function greyed(): GearItemInfo {
  const base = item();
  const [sig, rest] = base.affixes;
  return item({ id: "item_e6b2_grey", affixes: [{ ...sig!, off_zh: LONG }, rest!] });
}

function row(slot: string, over: Partial<SignatureRow> = {}): SignatureRow {
  return {
    key: `${slot}:affix_${slot}`,
    slot,
    slot_zh: slot,
    item_name_zh: `${slot}的裝備`,
    rarity: "rare",
    affix_id: `affix_${slot}`,
    kind: "action",
    kind_zh: "新動作",
    name_zh: `${slot}招`,
    text_zh: `${slot}招的說明`,
    counted: true,
    rule: false,
    active: true,
    off_zh: null,
    ...over,
  };
}

/** 4 個招牌勾 3 個（項鍊沒勾，短版灰字）＋2 條改寫規則（身體生效、腳衝突）。 */
const PANEL: SignaturePanel = {
  rows: [
    row("head"),
    row("body", { kind: "rule", kind_zh: "改寫規則", counted: false, rule: true }),
    row("hands"),
    row("feet", { kind: "rule", kind_zh: "改寫規則", counted: false, rule: true, active: false, off_zh: "和身體的改寫規則衝突，沒有效果" }),
    row("neck", { active: false, off_zh: SHORT }),
    row("ring_1"),
  ],
  active: 3,
  cap: 3,
  rules: 1,
  rule_cap: 1,
  has_rule: true,
  count_zh: "生效 3／3・改寫規則 1／1",
  full_zh: FULL,
  chosen: [],
};

const NONE: ReadonlySet<string> = new Set();
const html = (el: ReturnType<typeof createElement>): string => renderToStaticMarkup(el);

afterEach(() => {
  resetFxShown();
  saveMotionPref("system");
  resetMotionPrefMemo();
});

describe("裝備卡的招牌框", () => {
  it("招牌畫在詞條清單前面（第一行），清單不重複列招牌那一條", () => {
    const out = html(createElement(GearCardView, { cand: cand(item()) }));
    expect(out.indexOf("gear-card-signature")).toBeLessThan(out.indexOf("gear-card-lines"));
    expect(out).toContain("招牌・新動作");
    expect(out).toContain("鉤爪");
    const it1 = item();
    expect(itemLines(it1, signatureLine(it1))).toEqual(["力量 +3"]);
  });

  it("灰字：裝備卡用長版（不是短版）", () => {
    const out = html(createElement(GearCardView, { cand: cand(greyed()) }));
    expect(out).toContain(LONG);
    expect(out).not.toContain(SHORT + "<");
    expect(out).toContain("gear-sig off");
  });

  it("說明框（浮動卡）的行也用長版，招牌前面加類型牌的字", () => {
    const lines = itemTipLines(greyed(), "hands");
    expect(lines[0]).toEqual({ text: "招牌・新動作：解鎖「鉤爪」：1 AP、冷卻 3，把 4 格內的目標拉近 3 格", note: LONG });
    expect(lines[1]).toEqual({ text: "力量 +3", note: null });
  });

  it("沒有招牌的物品照舊（沒有框、行逐字相同）", () => {
    const plain = item({ affixes: [{ affix_id: "affix_attr_str", text_zh: "力量 +3" }] } as Partial<GearItemInfo>);
    expect(html(createElement(GearCardView, { cand: cand(plain) }))).not.toContain("gear-card-signature");
    expect(itemTipLines(plain, "hands")).toEqual([{ text: "力量 +3", note: null }]);
  });
});

describe("撿到時的一次性強調", () => {
  it("同一件只播一次：第一次有 fx，記下播過之後就沒有", () => {
    const first = html(createElement(GearCardView, { cand: cand(item()), fx: true }));
    expect(first).toContain("gear-sig fx");
    markFxShown("item_e6b2_hook"); // 掛上之後 useSignatureFx 的 effect 做的事
    const again = html(createElement(GearCardView, { cand: cand(item()), fx: true }));
    expect(again).not.toContain(" fx");
  });

  it("不是撿到的畫面（fx 沒開）不播", () => {
    expect(html(createElement(GearCardView, { cand: cand(item()) }))).not.toContain(" fx");
  });

  it("減少動態時不播", () => {
    saveMotionPref("on");
    expect(html(createElement(GearCardView, { cand: cand(item()), fx: true }))).not.toContain(" fx");
  });
});

describe("角色面板的勾選", () => {
  it("灰字：角色面板用短版（不是長版）", () => {
    const out = html(createElement(SignaturePicker, { panel: PANEL, equipment: [], busy: false, onPick: () => undefined }));
    expect(out).toContain(SHORT);
    expect(out).not.toContain(LONG);
    expect(out).toContain("和身體的改寫規則衝突，沒有效果");
  });

  it("名額計數：生效 N／3・改寫規則 N／1；沒有改寫規則時只寫生效", () => {
    expect(countText(PANEL, NONE)).toBe("生效 3／3・改寫規則 1／1");
    expect(countText({ ...PANEL, has_rule: false }, NONE)).toBe("生效 3／3");
    expect(countText(PANEL, new Set(["head:affix_head"]))).toBe("生效 2／3・改寫規則 1／1");
    const out = html(createElement(SignaturePicker, { panel: PANEL, equipment: [], busy: false, onPick: null }));
    expect(out).toContain("生效 3／3・改寫規則 1／1");
  });

  it("已滿時按沒勾的列：跳提示，不送出", () => {
    const neck = PANEL.rows.find((r) => r.slot === "neck")!;
    expect(clickRow(PANEL, NONE, neck)).toEqual({ kind: "full" });
    expect(PANEL.full_zh).toBe(FULL);
  });

  it("先取消一個再勾另一個：送出新的 3 個（含生效的改寫規則）", () => {
    const head = PANEL.rows.find((r) => r.slot === "head")!;
    const neck = PANEL.rows.find((r) => r.slot === "neck")!;
    expect(overCap(PANEL)).toBe(true);
    expect(clickRow(PANEL, NONE, head)).toEqual({ kind: "drop", key: head.key });
    const dropped = new Set([head.key]);
    expect(rowChecked(head, dropped)).toBe(false);
    expect(clickRow(PANEL, dropped, neck)).toEqual({ kind: "send", chosen: ["body:affix_body", "hands:affix_hands", "ring_1:affix_ring_1", neck.key] });
    expect(clickRow(PANEL, dropped, head)).toEqual({ kind: "undrop", key: head.key });
  });

  it("改寫規則是圓鈕：按另一條直接換過去", () => {
    const feet = PANEL.rows.find((r) => r.slot === "feet")!;
    expect(clickRow(PANEL, NONE, feet)).toEqual({ kind: "send", chosen: ["head:affix_head", "hands:affix_hands", "ring_1:affix_ring_1", feet.key] });
    const body = PANEL.rows.find((r) => r.slot === "body")!;
    expect(clickRow(PANEL, NONE, body)).toEqual({ kind: "none" });
  });

  it("沒有超過名額時不能取消（全部都生效）", () => {
    const three: SignaturePanel = { ...PANEL, rows: [row("head"), row("hands"), row("ring_1")], has_rule: false, rules: 0 };
    expect(clickRow(three, NONE, three.rows[0]!)).toEqual({ kind: "none" });
  });

  it("列的順序照後端（部位），方框與圓鈕", () => {
    const out = html(createElement(SignaturePicker, { panel: PANEL, equipment: [], busy: false, onPick: () => undefined }));
    const order = PANEL.rows.map((r) => out.indexOf(`signature-row-${r.slot}`));
    expect([...order].sort((a, b) => a - b)).toEqual(order);
    expect(out).toContain('role="radio"');
    expect(out).toContain('role="checkbox"');
  });
});

describe("大世界背包滿時的小標", () => {
  it("帶招牌的裝備名字後面加「招牌」與 14 px 圖示", () => {
    const gear = { item: "g1", name_zh: "稀有手套", kind_zh: "裝備", count: 1, description_zh: "", sell_price: 0, sellable: true, tradable: false, gear: true, can_equip: false, field_usable: false, signature: "action" } as WorldBagItem;
    const plain = { ...gear, item: "g2", signature: null } as WorldBagItem;
    const out = html(createElement(LootChoicePanel, { pending: { items: [gear, plain], over_slots: 1, hint_zh: "" }, inventory: null, busy: false, onAct: () => undefined }));
    expect(out).toContain("world-loot-signature-new:g1");
    expect(out).not.toContain("world-loot-signature-new:g2");
    expect(out).toContain('data-size="14"');
  });
});
