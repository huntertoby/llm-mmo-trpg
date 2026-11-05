// Phase 6T-1b：郵差與郵筒（實地地圖）、郵差頭上的「✉」、郵寄面板（三分頁）、別大類武器的卡片與換裝確認。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { FieldView, GearCandidate, NpcPortrait, MailLetter, MailQuote, MailRecipient, MailView, WorldBagItem } from "../api/types";
import { drawFurniture, FURNITURE_LOOKS } from "../render/interiorArt";
import { POSTBOX_HEIGHT, POSTBOX_MATERIALS, postboxMaterial } from "../render/objectArt";
import { CrossClassConfirm, CrossClassLines } from "./BagScreen";
import { FieldHeads } from "./FieldHeads";
import { FACILITY_ZH, facilityFigures, hoverText } from "./fieldModel";
import { headMarks, mailAlertZh } from "./fieldPeople";
import { panelAvailable } from "./hud";
import { MailPanel, type MailApi } from "./MailPanel";
import { addToDraft, EMPTY_DRAFT, firstTab, goldValue, letterSub, mailTabs, removeFromDraft, sendableState, sendBody, sendState, slotsUsed } from "./mailModel";

/** 畫布指令的紀錄（同 render/townArt.test.ts）。 */
function calls(draw: (c: CanvasRenderingContext2D) => void): string[] {
  const out: string[] = [];
  const ctx = new Proxy({} as Record<string, unknown>, {
    get(t, p: string) {
      if (p in t) return t[p];
      return (...a: unknown[]) => void out.push(`${p}(${a.map((x) => (typeof x === "number" ? x.toFixed(2) : String(x))).join(",")})`);
    },
    set(t, p: string, v) {
      t[p] = v;
      out.push(`${p}=${String(v)}`);
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  draw(ctx);
  return out;
}

const PORTRAIT = { look: { skin: "#f1c9a5", hair: "short", hair_color: "#2a1a10" }, gear: { body: { kind: "coat", material: "cloth", color: "#4a7a5a", trim: "#d9b24a" } }, extras: ["cap"] } as unknown as NpcPortrait;

function field(over: Partial<FieldView> = {}): FieldView {
  const tiles = Array.from({ length: 24 }, (_, i) => ({ x: i % 6, y: Math.floor(i / 6), height: 0, terrain: "stone", surface: "none", walkable: true }));
  return {
    map_id: "mist_ferry",
    name_zh: "霧渡鎮",
    region: "cloud_ridge",
    location: "mist_ferry",
    interior: false,
    width: 6,
    height: 4,
    tiles,
    tiles_hash: "",
    open_cells: [],
    objects: [{ x: 3, y: 1, kind: "low_wall", look: "postbox" }],
    exits: [],
    doors: [],
    stones: [],
    npcs: [],
    facilities: [
      { kind: "post", x: 3, y: 1 },
      { kind: "post", x: 4, y: 1, figure: { portrait: PORTRAIT, facing: "s", work: "town", line_zh: "" }, name_zh: "阿信", postman: "postman_axin" },
    ],
    me: { x: 2, y: 3, facing: "e" },
    max_climb: 1,
    walk_max_steps: 30,
    hero: { template_id: "hero_mage", weapon_id: "fire_staff", weapon_class: "focus", doll_look: null, race_look: null, equipment: [] },
    stone_targets: [],
    enemies: [],
    friends: [],
    campfires: [],
    situation_objects: [],
    sneaking: false,
    sneak_cost: 1,
    footprints: [],
    buildings: [],
    chasm_style: "default",
    decor: [],
    ...over,
  } as unknown as FieldView;
}

const BADGE = { postman: "postman_axin", region: "cloud_ridge", location: "mist_ferry", here: true, unread: 2, returned: 1, bubble: "✉" };

function bag(item: string, over: Partial<WorldBagItem> = {}): WorldBagItem {
  return { item, name_zh: item, kind_zh: "材料", count: 5, description_zh: "", sell_price: 0, sellable: false, field_usable: false, gear: false, can_equip: false, tradable: true, ...over };
}

function letter(id: string, over: Partial<MailLetter> = {}): MailLetter {
  return {
    id,
    sender: "c_bob",
    sender_name: "老鐵",
    recipient: "c_me",
    recipient_name: "阿霧",
    from_zh: "灰燼荒原・餘燼集",
    sent_at: 0,
    expires_at: 0,
    days_left: 2,
    note: "焦鐵給你打鞋。",
    items: [{ item: "item_scorched_iron", name_zh: "焦鐵", count: 3 }],
    gear: [],
    gold: 0,
    tax: 0,
    status_zh: "可以領",
    action: "claim",
    can_act: true,
    can_refuse: true,
    ...over,
  };
}

function mailView(over: Partial<MailView> = {}): MailView {
  return {
    postman: { id: "postman_axin", name_zh: "阿信", race_zh: "人類", role_zh: "霧渡鎮的郵差", region: "cloud_ridge", location: "mist_ferry", place_zh: "雲嶺・霧渡鎮", portrait: PORTRAIT },
    here: true,
    line_zh: "「有你的信啦，快來拿！」",
    inbox: [letter("mail_000001"), letter("mail_000002", { sender_name: "霜月", items: [], gold: 270, can_act: false, problem_zh: "背包放不下，先整理背包" })],
    returned: [letter("mail_000003", { status_zh: "過期退回", can_refuse: false, sender_name: "阿霧", recipient_name: "小魚" })],
    outgoing: [],
    sendable: [bag("item_hp_potion_small", { kind_zh: "消耗品", count: 3 }), bag("item_wolf_fang"), bag("item_gen_body_1", { gear: true, count: 1, tradable: false, bound_zh: "穿過" }), bag("item_dye_indigo", { kind_zh: "染料", tradable: false })],
    gold: 120,
    mailbox_count: 2,
    mailbox_max: 20,
    max_attachments: 3,
    note_max: 40,
    tax_permille: 100,
    min_level: 3,
    level_ok: true,
    return_days: 3,
    footer_zh: "信只能在城鎮的郵差這裡領；3 天沒領會自動退回寄件人，季末清掉。",
    send_note_zh: "3 天內沒人領，會自動退回給你（跑腿費不退）；季末沒領的信會清掉。",
    ...over,
  };
}

const NEVER: MailApi = {
  mail: () => new Promise(() => undefined),
  recipients: () => new Promise(() => undefined),
  quote: () => new Promise(() => undefined),
  send: () => new Promise(() => undefined),
  claim: () => new Promise(() => undefined),
  refuse: () => new Promise(() => undefined),
};

describe("郵差與郵筒（實地地圖）", () => {
  it("郵差站位畫成紙娃娃（名字照伺服器）；郵筒那格沒有人、說明寫「郵筒」", () => {
    const f = field();
    const figs = facilityFigures(f);
    expect(figs.map((x) => [x.name_zh, x.x, x.y])).toEqual([["阿信", 4, 1]]);
    expect(FACILITY_ZH.post).toBe("郵筒");
    expect(hoverText(f, { x: 4, y: 1 })).toBe("郵差 阿信");
    expect(hoverText(f, { x: 3, y: 1 })).toBe("郵筒");
  });

  it("有信時郵差頭上「✉」，沒有信時不畫", () => {
    const lit = headMarks(field(), new Map(), new Map(), { mail: BADGE });
    expect(lit.map((m) => [m.kind, m.alert, m.pos.x])).toEqual([["post", "mail", 4]]);
    expect(lit[0]!.alertZh).toBe("有信：收件匣 2 封、退件 1 封");
    expect(headMarks(field(), new Map(), new Map(), { mail: { ...BADGE, bubble: null, unread: 0, returned: 0 } })).toEqual([]);
    expect(headMarks(field(), new Map(), new Map(), {})).toEqual([]);
    const html = renderToStaticMarkup(createElement(FieldHeads, { marks: lit, grid: { width: 6, height: 4, tiles: [] } as never, scale: 1, onPick: () => undefined }));
    expect(html).toContain('data-alert="mail"');
    expect(html).toContain('data-testid="field-mail-glyph"');
    expect(html).not.toContain("！");
    expect(mailAlertZh({ unread: 0, returned: 0 })).toBe("郵寄");
  });

  it("郵筒三種材質依區域、確定性、不寫字；高度約紙娃娃的 0.6 倍", () => {
    expect(FURNITURE_LOOKS).toContain("postbox");
    expect(postboxMaterial("ashen_waste")).toBe("ashen_waste");
    expect(postboxMaterial("capital")).toBe("capital");
    expect(postboxMaterial("cloud_ridge")).toBe("cloud_ridge");
    expect(postboxMaterial("crystal_crown")).toBe("cloud_ridge");
    const draws = (["cloud_ridge", "ashen_waste", "capital"] as const).map((region) => calls((c) => drawFurniture(c, { look: "postbox", joinW: false, joinE: false, region })).join("|"));
    expect(new Set(draws).size).toBe(3);
    expect(calls((c) => drawFurniture(c, { look: "postbox", joinW: false, joinE: false, region: "capital" })).join("|")).toBe(draws[2]);
    expect(draws.every((d) => !d.includes("fillText"))).toBe(true);
    expect(new Set(Object.values(POSTBOX_MATERIALS).map((m) => m.body)).size).toBe(3);
    expect(POSTBOX_HEIGHT / 50).toBeGreaterThan(0.5);
    expect(POSTBOX_HEIGHT / 50).toBeLessThan(0.7);
  });

  it("郵寄面板只在世界畫面有郵寄資料時開", () => {
    expect(panelAvailable({ mail: BADGE } as never, "mail")).toBe(true);
    expect(panelAvailable({ mail: null } as never, "mail")).toBe(false);
  });
});

describe("郵寄面板的純函式", () => {
  it("分頁標籤寫封數；有信先開收件匣", () => {
    expect(mailTabs(mailView()).map((t) => t.label)).toEqual(["寄東西", "收件匣 2", "退件・過期 1"]);
    expect(mailTabs(mailView({ inbox: [], returned: [] })).map((t) => t.label)).toEqual(["寄東西", "收件匣", "退件・過期"]);
    expect(firstTab(mailView())).toBe("inbox");
    expect(firstTab(mailView({ inbox: [] }))).toBe("returned");
    expect(firstTab(mailView({ inbox: [], returned: [] }))).toBe("send");
  });

  it("綁定的灰掉並寫原因；點進附件最多 3 格、不超過持有數", () => {
    const v = mailView();
    const [potion, fang, worn, dye] = v.sendable as [WorldBagItem, WorldBagItem, WorldBagItem, WorldBagItem];
    expect(sendableState(worn)).toEqual({ ok: false, reason: "穿過" });
    expect(sendableState(dye)).toEqual({ ok: false, reason: "不能寄" });
    let d = addToDraft(EMPTY_DRAFT, worn, 3);
    expect(d).toBe(EMPTY_DRAFT);
    for (let i = 0; i < 5; i++) d = addToDraft(d, potion, 3);
    expect(d.items).toEqual({ item_hp_potion_small: 3 });
    d = addToDraft(d, fang, 3);
    d = addToDraft(d, bag("item_a"), 3);
    expect(slotsUsed(d)).toBe(3);
    expect(addToDraft(d, bag("item_b"), 3)).toBe(d);
    expect(slotsUsed(removeFromDraft(d, "item_wolf_fang"))).toBe(2);
    const g = addToDraft(EMPTY_DRAFT, bag("item_gear", { gear: true, count: 1 }), 3);
    expect(addToDraft(g, bag("item_gear", { gear: true, count: 1 }), 3)).toBe(g);
  });

  it("寄件請求與「寄出」的狀態：沒選人、檢查沒過都不亮", () => {
    expect(sendBody(EMPTY_DRAFT)).toBeNull();
    const d = { ...EMPTY_DRAFT, to: "c_fish", items: { item_wolf_fang: 2 }, gold: 500, note: "拿去" };
    expect(sendBody(d)).toEqual({ kind: "mail_send", to: "c_fish", items: { item_wolf_fang: 2 }, gear: [], gold: 500, note: "拿去" });
    expect(goldValue("5 00")).toBe(500);
    expect(goldValue("abc")).toBe(0);
    const bad: MailQuote = { ok: false, gold: 500, tax: 50, received: 450, value: 0, tax_zh: "跑腿費 10%：−50　對方實收 450", problems: [{ code: "bag_full", text_zh: "對方背包放不下（還差 1 格）" }] };
    expect(sendState(EMPTY_DRAFT, null, true, null)).toEqual({ ok: false, reason: "先選收件人" });
    expect(sendState(d, bad, true, null)).toEqual({ ok: false, reason: "對方背包放不下（還差 1 格）" });
    expect(sendState(d, { ...bad, ok: true, problems: [] }, true, null)).toEqual({ ok: true, reason: null });
    expect(sendState(d, { ...bad, ok: true, problems: [] }, false, "信只能在城鎮的郵差這裡寄、這裡領").ok).toBe(false);
  });

  it("信的第二行：收件匣寫剩幾天、退件寫原因", () => {
    expect(letterSub(letter("m"), false)).toBe("寄自 灰燼荒原・餘燼集・剩 2 天");
    expect(letterSub(letter("m", { status_zh: "過期退回" }), true)).toBe("過期退回・寄自 灰燼荒原・餘燼集");
  });
});

describe("郵寄面板（靜態輸出）", () => {
  const recipients: MailRecipient[] = [
    { character_id: "c_fish", name_zh: "小魚", level: 5, region: "cloud_ridge", place_zh: "雲嶺・霧渡鎮", can_receive: true },
    { character_id: "c_low", name_zh: "小石", level: 1, region: "cloud_ridge", place_zh: "雲嶺・霧渡鎮", can_receive: false, problem_zh: "還不到 3 級" },
  ];
  const quote: MailQuote = { ok: true, gold: 500, tax: 50, received: 450, value: 500, tax_zh: "跑腿費 10%：−50　對方實收 450", problems: [] };

  it("收件匣：背包放不下的那封「領取」灰掉並寫原因；底下的說明是過期自動退回", () => {
    const html = renderToStaticMarkup(createElement(MailPanel, { mailApi: NEVER, inventory: null, initial: { mail: mailView() } }));
    expect(html).toContain('data-tab="inbox"');
    expect(html).toMatch(/data-testid="mail-claim-mail_000002"[^>]*disabled|disabled=""[^>]*data-testid="mail-claim-mail_000002"/);
    expect(html).toContain("背包放不下，先整理背包");
    expect(html).toContain("自動退回寄件人");
    expect(html).toContain("阿信：「有你的信啦，快來拿！」");
    expect(html).toContain("收件匣 2");
  });

  it("退件・過期：過期的信照退件用「領取」，沒有「退回」", () => {
    const html = renderToStaticMarkup(createElement(MailPanel, { mailApi: NEVER, inventory: null, tab: "returned", initial: { mail: mailView() } }));
    expect(html).toContain('data-testid="mail-claim-mail_000003"');
    expect(html).not.toContain('data-testid="mail-refuse-mail_000003"');
    expect(html).toContain("過期退回・寄自");
  });

  it("寄東西：綁定的灰掉標「穿過」、稅與實收照伺服器、檢查通過才亮「寄出」", () => {
    const draft = { ...EMPTY_DRAFT, to: "c_fish", items: { item_wolf_fang: 5 }, gold: 500 };
    const html = renderToStaticMarkup(createElement(MailPanel, { mailApi: NEVER, inventory: null, tab: "send", draft, initial: { mail: mailView(), recipients, quote } }));
    expect(html).toContain('data-testid="mail-bound-tag">穿過');
    expect(html).toContain("跑腿費 10%：−50　對方實收 450");
    expect(html).toContain("還不到 3 級");
    expect(html).toContain("會自動退回給你");
    expect(html).not.toMatch(/data-testid="mail-send-btn"[^>]*disabled|disabled=""[^>]*data-testid="mail-send-btn"/);
    const blocked = renderToStaticMarkup(
      createElement(MailPanel, { mailApi: NEVER, inventory: null, tab: "send", draft, initial: { mail: mailView(), recipients, quote: { ...quote, ok: false, problems: [{ code: "too_strong", text_zh: "紫電長弓的物品等級高於對方等級 +2" }] } } }),
    );
    expect(blocked).toMatch(/disabled=""[^>]*data-testid="mail-send-btn"/);
    expect(blocked).toContain("✗ 紫電長弓的物品等級高於對方等級 +2");
  });
});

describe("別大類武器的卡片與換裝確認（08 8.13 #135）", () => {
  const row = bag("item_gen_weapon_1", { gear: true, count: 1, kind_zh: "裝備", cross_class_zh: "別大類：可交易・可分解・可賣", cross_class_lost_zh: "換上後不能用：戰歌、順風" });
  const cand = { item: { id: "item_gen_weapon_1", name_zh: "鐵劍" }, slot: "main_hand", slot_zh: "主手", notes_zh: [], weapon_swap_zh: null } as unknown as GearCandidate;

  it("卡片兩行字照伺服器", () => {
    const html = renderToStaticMarkup(createElement(CrossClassLines, { row }));
    expect(html).toContain("別大類：可交易・可分解・可賣");
    expect(html).toContain("換上後不能用：戰歌、順風");
    expect(renderToStaticMarkup(createElement(CrossClassLines, { row: { ...row, cross_class_zh: null } }))).toBe("");
  });

  it("確認框列出不能用的招、說明換回同大類就恢復", () => {
    const html = renderToStaticMarkup(createElement(CrossClassConfirm, { cand, row, busy: false, onConfirm: () => undefined, onCancel: () => undefined }));
    expect(html).toContain("「鐵劍」是別大類的武器。換上後不能用：戰歌、順風（換回同大類就恢復）。要換上嗎？");
    expect(html).toContain('data-testid="cross-class-yes"');
  });
});
