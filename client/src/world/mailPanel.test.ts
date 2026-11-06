// 6T-1d（docs/art/6T-1c檢查.md）：郵寄面板收尾（寄出黏在底部、捲動區上緣不透明、附件格說明卡往下開、青石郵筒的苔）
// 與全遊戲主要按鈕（滑過亮一階、只有停用才是深灰）。
import { describe, expect, it } from "vitest";
import { POSTBOX_MOSS, POSTBOX_MOSS_HI, POSTBOX_HEIGHT, POSTBOX_MATERIALS, postboxMaterial } from "../render/objectArt";
import { floatPlacement } from "../ui/floatCard";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { type FieldView, type GearCandidate, type NpcPortrait, type MailLetter, type MailQuote, type MailRecipient, type MailView, type WorldBagItem } from "../api/types";
import { drawFurniture, FURNITURE_LOOKS } from "../render/interiorArt";
import { CrossClassConfirm, CrossClassLines } from "./BagScreen";
import { FieldHeads } from "./FieldHeads";
import { FACILITY_ZH, facilityFigures, hoverText } from "./fieldModel";
import { headMarks, mailAlertZh } from "./fieldPeople";
import { panelAvailable } from "./hud";
import { MailPanel, type MailApi } from "./MailPanel";
import { addToDraft, countValue, EMPTY_DRAFT, firstTab, goldValue, letterSub, mailTabs, removeFromDraft, sendableState, sendBody, sendState, setDraftCount, slotsUsed, tabSay } from "./mailModel";

const nodeFs = "node:fs";
const { readFileSync } = (await import(/* @vite-ignore */ nodeFs)) as { readFileSync: (p: string, enc: string) => string };
const baseCss = readFileSync("src/styles/base.css", "utf-8");
const entryCss = readFileSync("src/styles/entry.css", "utf-8");
const mailCss = readFileSync("src/world/mail.css", "utf-8");
const panelSrc = readFileSync("src/world/MailPanel.tsx", "utf-8");

/** 選擇器（完全相同）對應的規則內容。 */
function rule(css: string, selector: string): string | null {
  const esc = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const m = new RegExp(`(?:^|\\n)${esc}\\s*\\{([^}]*)\\}`).exec(css);
  return m === null ? null : m[1]!;
}

const lum = (hex: string): number => {
  const n = parseInt(hex.slice(1), 16);
  return 0.2126 * ((n >> 16) & 255) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255);
};

describe("6T-1d 小修 7：全遊戲主要按鈕", () => {
  it("滑過時亮一階（不是共用 button:hover 的深灰）", () => {
    const hover = rule(baseCss, "button.primary:hover:not(:disabled)");
    expect(hover).not.toBeNull();
    expect(hover).toContain("background: #4d6cb3");
    expect(lum("#4d6cb3")).toBeGreaterThan(lum("#3d5a99"));
  });

  it("只有停用時才是深灰；建角畫面的主要按鈕停用也是灰底", () => {
    expect(rule(baseCss, "button.primary:disabled")).toContain("background: #36364a");
    expect(rule(baseCss, "button:disabled")).toContain("opacity: 0.45"); // 停用照舊半透明
    expect(rule(entryCss, ".entry-skin button.primary:disabled")).toContain("linear-gradient(180deg, #3a3c50, #2c2e40)");
  });

  it("郵寄面板不再自己蓋一條滑過規則（改由 base.css 全遊戲一起）", () => {
    expect(mailCss).not.toContain(".world-mail button.primary:hover");
  });
});

describe("6T-1d 小修 3、4：寄出黏在底部、捲動區上緣不透明", () => {
  it("「寄出」那一列在兩欄格線外面、黏在捲動區底部、不透明底", () => {
    const wrap = panelSrc.indexOf('className="mail-send-wrap"');
    const grid = panelSrc.indexOf('className="mail-send" data-testid="mail-send"');
    const check = panelSrc.indexOf('data-testid="mail-check"');
    const actions = panelSrc.indexOf('className="mail-actions"');
    expect(wrap).toBeGreaterThan(-1);
    expect(grid).toBeGreaterThan(wrap);
    // 檢查框之後、mail-actions 之前要先關掉 mail-send-main 與 mail-send 兩層
    const between = panelSrc.slice(panelSrc.indexOf("</section>", check), actions);
    expect(between.match(/<\/div>/g)?.length).toBe(2);
    const css = rule(mailCss, ".mail-actions");
    expect(css).toContain("position: sticky");
    expect(css).toContain("bottom: 0");
    expect(css).toContain("background: var(--ui-navy)");
  });

  it("郵寄面板捲下去以後的上緣色塊是實色（沒有半透明的漸層）", () => {
    const top = rule(mailCss, '.world-hud-panel[data-panel="mail"] > .ui-popup-body::before');
    expect(top).toContain("background: var(--ui-navy);");
    expect(top).not.toContain("gradient");
  });
});

describe("6T-1d 小修 5：附件格的說明卡先往下開", () => {
  const view = { width: 1600, height: 900 };
  const size = { width: 80, height: 36 };
  it("prefer below：下方放得下就放下方，放不下才翻到上方", () => {
    expect(floatPlacement({ left: 100, top: 300, width: 24, height: 26 }, size, view, "center", 4, "below").side).toBe("below");
    expect(floatPlacement({ left: 100, top: 860, width: 24, height: 26 }, size, view, "center", 4, "below").side).toBe("above");
    expect(floatPlacement({ left: 100, top: 300, width: 24, height: 26 }, size, view, "center").side).toBe("above"); // 預設不變
  });

  it("附件格的 −／＋／×／裝備格的說明卡都 prefer below", () => {
    for (const t of ['"少寄 1 個"} prefer="below"', '"多寄 1 個"} prefer="below"', 'text="拿掉這一格" prefer="below"', 'text="點了拿掉" prefer="below"']) {
      expect(panelSrc).toContain(t);
    }
  });
});

describe("6T-1d 小修 6：青石郵筒的苔再加深一階", () => {
  it("苔斑比 6T-1c 的 #2a5e18 深、亮點比 #8ac850 亮", () => {
    expect(lum(POSTBOX_MOSS)).toBeLessThan(lum("#2a5e18"));
    expect(lum(POSTBOX_MOSS_HI)).toBeGreaterThan(lum("#8ac850"));
  });
});

// --- 原 mail6t1b.test.ts ---
describe("原 mail6t1b.test.ts", () => {
// Phase 6T-1b：郵差與郵筒（實地地圖）、郵差頭上的「✉」、郵寄面板（三分頁）、別大類武器的卡片與換裝確認。

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

// ---------------------------------------------------------------------------
// Phase 6T-1c：寄件填數量、照分頁換台詞、剪影不寫「?」、信件卡片的按鈕位置
// ---------------------------------------------------------------------------

const TAB_LINES = { send: "「要寄東西啦？」", inbox: "「有你的信啦，快來拿！」", inbox_empty: "「還沒有你的信啦。」", returned: "「對方一直沒來拿的，都退回來啦。」" };

describe("6T-1c 寄件填數量（玩法 PM acfc999f）", () => {
  const potion = bag("item_hp_potion_small", { count: 7 });

  it("數量夾在 1～背包裡的數量；裝備、不在附件裡的不動", () => {
    const d = addToDraft(EMPTY_DRAFT, potion, 3);
    expect(setDraftCount(d, potion, 5).items).toEqual({ item_hp_potion_small: 5 });
    expect(setDraftCount(d, potion, 99).items).toEqual({ item_hp_potion_small: 7 });
    expect(setDraftCount(d, potion, 0).items).toEqual({ item_hp_potion_small: 1 });
    expect(setDraftCount(d, potion, Number.NaN).items).toEqual({ item_hp_potion_small: 1 });
    expect(setDraftCount(EMPTY_DRAFT, potion, 3)).toBe(EMPTY_DRAFT);
    const gear = bag("item_gear", { gear: true, count: 1 });
    const g = addToDraft(EMPTY_DRAFT, gear, 3);
    expect(setDraftCount(g, gear, 3)).toBe(g);
    expect(countValue("1 2")).toBe(12);
    expect(Number.isNaN(countValue(""))).toBe(true);
    expect(sendBody({ ...setDraftCount(d, potion, 4), to: "c_fish" })?.items).toEqual({ item_hp_potion_small: 4 });
  });

  it("附件格：材料、消耗品有 ± 與數字框（上限寫在旁邊），裝備沒有", () => {
    const v = mailView({ sendable: [potion, bag("item_gen_body_1", { gear: true, count: 1 })] });
    const draft = { ...EMPTY_DRAFT, to: "c_fish", items: { item_hp_potion_small: 7 }, gear: ["item_gen_body_1"] };
    const html = renderToStaticMarkup(createElement(MailPanel, { mailApi: NEVER, inventory: null, tab: "send", draft, initial: { mail: v } }));
    expect(html).toContain('data-testid="mail-count-input-item_hp_potion_small"');
    expect(html).toContain('value="7"');
    expect(html).toContain("／7");
    expect(html).toMatch(/disabled=""[^>]*data-testid="mail-inc-item_hp_potion_small"/); // 已經是上限
    expect(html).not.toMatch(/disabled=""[^>]*data-testid="mail-dec-item_hp_potion_small"/);
    expect(html).not.toContain('data-testid="mail-count-item_gen_body_1"');
    expect(html).toContain('data-testid="mail-slot-item_gen_body_1"');
  });
});

describe("6T-1c 郵差照分頁換台詞", () => {
  it("寄東西／收件匣（有信、空的）／退件各一句；剛寄出的那句優先；等級不到照伺服器那句", () => {
    const v = mailView({ tab_lines: TAB_LINES });
    expect(tabSay(v, "send", null)).toBe("「要寄東西啦？」");
    expect(tabSay(v, "inbox", null)).toBe("「有你的信啦，快來拿！」");
    expect(tabSay({ ...v, inbox: [] }, "inbox", null)).toBe("「還沒有你的信啦。」");
    expect(tabSay(v, "returned", null)).toBe("「對方一直沒來拿的，都退回來啦。」");
    expect(tabSay(v, "send", "「送出去啦！」")).toBe("「送出去啦！」");
    expect(tabSay({ ...v, level_ok: false, line_zh: "「等你再強一點啦，3 級以後。」" }, "send", null)).toBe("「等你再強一點啦，3 級以後。」");
    expect(tabSay(mailView(), "send", null)).toBe("「有你的信啦，快來拿！」"); // 舊伺服器沒有 tab_lines：照 line_zh
  });

  it("面板上方照打開的分頁說話", () => {
    const render = (tab: "send" | "inbox" | "returned") => renderToStaticMarkup(createElement(MailPanel, { mailApi: NEVER, inventory: null, tab, initial: { mail: mailView({ tab_lines: TAB_LINES }) } }));
    expect(render("send")).toContain("阿信：「要寄東西啦？」");
    expect(render("returned")).toContain("阿信：「對方一直沒來拿的，都退回來啦。」");
    expect(render("inbox")).toContain("阿信：「有你的信啦，快來拿！」");
  });
});

describe("6T-1c 美術 PM 6T-1b 檢查的修正", () => {
  it("信件卡片：按鈕包在固定的一列裡，不能領的原因寫在按鈕下面", () => {
    const html = renderToStaticMarkup(createElement(MailPanel, { mailApi: NEVER, inventory: null, initial: { mail: mailView() } }));
    const card = html.slice(html.indexOf('data-testid="mail-letter-mail_000002"'));
    const btns = card.indexOf('class="mail-letter-btns"');
    expect(btns).toBeGreaterThan(0);
    expect(card.indexOf('data-testid="mail-claim-mail_000002"')).toBeGreaterThan(btns);
    expect(card.indexOf('data-testid="mail-problem-mail_000002"')).toBeGreaterThan(card.indexOf('data-testid="mail-refuse-mail_000002"'));
  });
});
});
