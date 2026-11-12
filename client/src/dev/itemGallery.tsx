// 開發用：物品的 Q 版小圖示（第⑥批），Phase QI-7。開 `client/dev/item-gallery.html`（自己的 vite 後 /dev/item-gallery.html?mute=1）。不屬於正式 build。
// 需求 docs/art/Q版小圖示-物品移植需求.md 第 7 節（截圖）、「指紋比對」節（37 行）。圖示走遊戲端 `qIcon/items.ts` 的 `canvas`（和 `ui/ItemIcon` 同一張畫布）；
// 清單、背包、信件、飛行停格用正式元件（`ShopPanel`、`LootChoicePanel`、`PouchEditor`、`SmithyPanel`、`BagContents`、`MailPanel`、`GainFlyIcon`）＋正式樣式畫，資料是假的。
// 參數：
//   ?set=<名稱,…>     逗號接多段：
//        a        總表（預設）：每列 每個大小 × `&res=`（最近鄰 ×`&zoom=`）；`&grp=` 只列這幾組、`&px=` 只列這幾個大小
//        fly      飛進背包 28 的飛行圓：37 個 × `&res=`（PNL-4 起拿掉現行對照，`dev/itemLegacy.tsx` 已刪）
//        list     清單列（正式元件）：商店買、賣（含一列裝備）、整理腰包、背包滿了（物品與裝備混排）、鐵匠特色材料；右邊最近鄰 ×3 的一列裁切
//        scene    背包 6×5＋腰包（物品與裝備混排）、信件附件、飛行停格（物品｜沒外觀的裝備｜有外觀的裝備）
//        missing  `content/world/items.yaml` 裡有、圖示表裡沒有的 id（應為 0）
//        hash     指紋（和樣張 `qicons_shots.py --hash items` 同一個 FNV 算法、同一個行格式，37 行），結果放 `body.dataset.hash`
//   &res=<1|2,…>      內部解析度（預設 1,2；1＝真 1 倍：畫布寬高＝CSS px）
//   &zoom=<k>         放大 k 倍顯示（預設 4）；截圖用裝置像素比 1 拍
//   &grp=<組,…>        set=a 只列這幾組（potion、throw、supply、mat、cloud、ashen、dye、gain）
//   &px=<大小,…>       set=a 只列這幾個大小（預設每個圖示用到的全部）
//   &label=0          不顯示名稱
// 畫好後 `body.dataset.ready = "1"`；另外掛 `window.__qiItemDev`（canvas、hash、missing）。
import { useEffect, useState, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { parse } from "yaml";
import itemsYaml from "../../../content/world/items.yaml?raw";
import type { MailApi } from "../world/MailPanel";
import type { MailView, WorldBagItem, WorldCrafting, WorldInventory, WorldPendingLoot, WorldShop } from "../api/types";
import { waitForFonts } from "../render/fontLoad";
import * as QI from "../render/qIcon/items";
import { BagContents } from "../world/BagScreen";
import { PouchEditor, ShopPanel } from "../world/EconomyPanel";
import { GainFlyIcon } from "../world/GainEffects";
import { LootChoicePanel } from "../world/LootChoicePanel";
import { MailPanel } from "../world/MailPanel";
import { SmithyPanel } from "../world/SmithyPanel";
import "../styles/index.css";

const q = new URLSearchParams(location.search);
const list = (k: string, d: string): string[] => (q.get(k) ?? d).split(",").filter((s) => s !== "");
const SETS = list("set", "a");
const RESS = list("res", "1,2").map(Number);
const ZOOM = Number(q.get("zoom") ?? 4);
/** 32 以上的大小另給：`&bigres=` 內部解析度、`&bigzoom=` 放大倍數（預設同 `&res=`、`&zoom=`；截圖第 1、2 張用 `bigres=1`）。 */
const BIG_RESS = list("bigres", RESS.join(",")).map(Number);
const BIG_ZOOM = Number(q.get("bigzoom") ?? ZOOM);
const zoomOf = (px: number): number => (px >= 32 ? BIG_ZOOM : ZOOM);
const ressOf = (px: number): number[] => (px >= 32 ? BIG_RESS : RESS);
const GRPS = list("grp", Object.keys(QI.GRP_ZH).join(",")) as QI.ItemGroup[];
const PXS = list("px", "").map(Number);
const LABEL = q.get("label") !== "0";

// ---------------- content（items.yaml）：名字、種類、染料色、稀有 ----------------
interface ContentItem { id: string; name_zh: string; kind: string; color?: string; rare?: boolean }
const CONTENT: ContentItem[] = ((parse(itemsYaml) as { items: ContentItem[] }).items ?? []).map((i) => ({ id: i.id, name_zh: i.name_zh, kind: i.kind, ...(i.color !== undefined ? { color: i.color } : {}), ...(i.rare !== undefined ? { rare: i.rare } : {}) }));
const BY_ID = new Map(CONTENT.map((i) => [i.id, i]));
const KIND_ZH: Record<string, string> = { consumable: "消耗品", material: "材料", dye: "染料", supply: "補給" };
/** 內容裡有、圖示表裡沒有的 id（染料有 color 時照樣有圖，不算）。 */
const missing = (): string[] => CONTENT.filter((i) => !QI.hasItemIcon(i.id, i.color)).map((i) => i.id);

// ---------------- 小工具 ----------------
const uniq = <T,>(a: readonly T[]): T[] => [...new Set(a)];
const sizesOf = (e: QI.ItemIconEntry): number[] => uniq(e.sizes).sort((a, b) => a - b);
/** 圖示畫布複製一份，CSS 顯示寬 px × zoom（最近鄰）。 */
function Zoomed({ cv, px, zoom = ZOOM }: { cv: HTMLCanvasElement; px: number; zoom?: number }) {
  const [el, setEl] = useState<HTMLCanvasElement | null>(null);
  useEffect(() => { if (el === null) return; el.width = cv.width; el.height = cv.height; el.getContext("2d")!.drawImage(cv, 0, 0); }, [el, cv]);
  return <canvas ref={setEl} style={{ width: px * zoom, height: px * zoom, imageRendering: "pixelated", display: "block", flex: "none" }} />;
}
const Label = ({ text }: { text: string }) => (LABEL ? <div className="lab">{text}</div> : null);

function SetA() {
  return (
    <>
      {GRPS.map((g) => (
        <section key={g}>
          <h2>
            {QI.GRP_ZH[g]}　每個大小：{RESS.map((r) => (r === 1 ? "真 1 倍" : `DPR ${r}`)).join("｜")}（最近鄰 ×{ZOOM}）
            {(BIG_ZOOM !== ZOOM || BIG_RESS.join() !== RESS.join()) && `；32 以上：${BIG_RESS.map((r) => (r === 1 ? "真 1 倍" : `DPR ${r}`)).join("｜")}（×${BIG_ZOOM}）`}
          </h2>
          <div className="row">
            {QI.list(g).map(({ id, entry: e }) => (
              <div key={id} className="cell">
                <div className="icons">
                  {(PXS.length > 0 ? sizesOf(e).filter((p) => PXS.includes(p)) : sizesOf(e)).map((px) => (
                    <div key={px} className="one">
                      {ressOf(px).map((res) => <Zoomed key={res} cv={QI.canvas(id, px, res)} px={px} zoom={zoomOf(px)} />)}
                    </div>
                  ))}
                </div>
                <Label text={`${e.zh} ${id.replace("item_", "")}｜${(PXS.length > 0 ? sizesOf(e).filter((p) => PXS.includes(p)) : sizesOf(e)).join("/")}`} />
              </div>
            ))}
          </div>
        </section>
      ))}
    </>
  );
}

function SetFly() {
  return (
    <section>
      <h2>飛進背包（28，深底圓金邊；直徑 26、金邊壓在圓上）　每格：{RESS.map((r) => (r === 1 ? "真 1 倍" : `DPR ${r}`)).join("｜")}（最近鄰 ×{ZOOM}）</h2>
      <div className="row">
        {QI.list().map(({ id, entry: e }) => (
          <div key={id} className="cell">
            <div className="icons">
              <div className="one">
                {RESS.map((res) => <Zoomed key={res} cv={QI.canvas(id, 28, res, { frame: "fly" })} px={28} />)}
              </div>
            </div>
            <Label text={`${e.zh} ${id.replace("item_", "")}`} />
          </div>
        ))}
      </div>
    </section>
  );
}

// ---------------- 假資料 ----------------
function bag(id: string, count = 1, over: Partial<WorldBagItem> = {}): WorldBagItem {
  const c = BY_ID.get(id);
  return {
    item: id, name_zh: c?.name_zh ?? id, kind_zh: KIND_ZH[c?.kind ?? ""] ?? "", count, description_zh: "說明", sell_price: 3, sellable: c?.kind !== "material", field_usable: false, gear: false, can_equip: false, tradable: true,
    ...(c?.color !== undefined ? { color: c.color } : {}), ...(c?.kind === "material" ? { rare: c.rare === true } : {}), ...over,
  } as WorldBagItem;
}
const gearRow = (id: string, name: string): WorldBagItem => ({ item: id, name_zh: name, kind_zh: "裝備", count: 1, description_zh: "武器・稀有", sell_price: 12, sellable: true, field_usable: false, gear: true, can_equip: true, tradable: true });
const LOOK_SWORD = { kind: "sword", material: "steel", rarity: "rare" };
const LOOK_ROBE = { kind: "robe", material: "cloth", rarity: "epic" };
const GEAR_CARDS = [
  { item: { id: "g_sword", name_zh: "稀有長劍（3 級）", slot_type: "weapon", affixes: [], tags: [], appearance: LOOK_SWORD }, slot: "main_hand", slot_zh: "主手", current: null, notes_zh: [] },
  { item: { id: "g_robe", name_zh: "史詩布袍（5 級）", slot_type: "body", affixes: [], tags: [], appearance: LOOK_ROBE }, slot: "body", slot_zh: "身體", current: null, notes_zh: [] },
];
const BAG_ROWS: WorldBagItem[] = [
  gearRow("g_sword", "稀有長劍（3 級）"), bag("item_hp_potion_small", 3), bag("item_hp_potion_medium", 2), bag("item_mana_potion", 2), bag("item_antidote_herb", 4), bag("item_fire_flask", 2),
  bag("item_water_flask"), bag("item_coarse_material", 5), bag("item_fine_material", 3), bag("item_superior_material"), bag("item_essence", 2), gearRow("g_robe", "史詩布袍（5 級）"),
  bag("item_scorched_iron", 6), bag("item_mist_crystal", 2), bag("item_summit_mist_crystal"), bag("item_living_bone"), bag("item_molten_heart"), bag("item_obsidian_shard", 3),
  bag("item_dye_indigo"), bag("item_dye_cinnabar"), bag("item_dye_snow", 2), bag("item_wolf_fang", 4), bag("item_unknown_thing", 2, { name_zh: "沒圖的東西", kind_zh: "材料" }),
];
const POUCH_ROWS: WorldBagItem[] = [bag("item_hp_potion_small", 2), bag("item_oil_flask"), bag("item_frost_flask")];
const INVENTORY = {
  bag: BAG_ROWS, slots_used: BAG_ROWS.length, slots_max: 30, pouch: POUCH_ROWS, pouch_count: 4, pouch_max: 3, can_pouch: true, pouch_problem_zh: null,
  consumables: [bag("item_hp_potion_small", 5), bag("item_mana_potion", 2), bag("item_oil_flask", 1), bag("item_frost_flask", 2), bag("item_mist_flask", 1)],
  equipped_zh: [], resonance_zh: [], equipment: [], gear_cards: GEAR_CARDS,
} as unknown as WorldInventory;
const shopItem = (id: string, price: number, over: Record<string, unknown> = {}) => ({ item: id, name_zh: BY_ID.get(id)?.name_zh ?? id, kind_zh: KIND_ZH[BY_ID.get(id)?.kind ?? ""] ?? "", description_zh: "說明", price, weekly: false, stock_zh: null, locked: false, lock_zh: null, can_buy: true, problem_zh: null, ...(BY_ID.get(id)?.color !== undefined ? { color: BY_ID.get(id)!.color } : {}), ...over });
const SHOP = {
  shop: "shop_mist", name_zh: "柳記雜貨", npc: "npc_liu", npc_name_zh: "柳掌櫃", rank_zh: "普通", affinity_zh: null, can_trade: true, trade_problem_zh: null, price_notes_zh: [],
  items: [shopItem("item_hp_potion_small", 20), shopItem("item_antidote_herb", 25), shopItem("item_water_flask", 15), shopItem("item_supplies", 10), shopItem("item_mist_flask", 30, { locked: true, lock_zh: "柳掌櫃好感度到友善才賣", can_buy: false, problem_zh: "好感度不夠" }), shopItem("item_green_bamboo", 18, { weekly: true, stock_zh: "本週剩 3 個", rare: false }), shopItem("item_dye_jade", 40)],
} as unknown as WorldShop;
const SELL_INV = { ...INVENTORY, bag: [gearRow("g_sword", "稀有長劍（3 級）"), bag("item_hp_potion_small", 3), bag("item_fire_flask", 2), bag("item_dye_cinnabar")] } as WorldInventory;
const PENDING = { items: [bag("item_wolf_fang", 2), gearRow("g_new", "稀有短刀（2 級）"), bag("item_thunder_feather")], over_slots: 2, hint_zh: "全部收下還差 2 格：丟掉一些再收。" } as unknown as WorldPendingLoot;
const LOOT_INV = { ...INVENTORY, bag: [bag("item_coarse_material", 5), gearRow("g_sword", "稀有長劍（3 級）"), bag("item_hp_potion_small", 3), bag("item_unknown_thing", 1, { name_zh: "沒圖的東西" })] } as WorldInventory;
const mat = (id: string, count: number, grade: boolean, lean: string | null = null) => ({ item: id, name_zh: BY_ID.get(id)?.name_zh ?? id, count, grade, level_cap: grade ? 1 : null, leaning_zh: lean, resonance_zh: null });
const CRAFTING = {
  stations: [{ station: "smithy_mist_ferry", kind: "smithy", name_zh: "石記鐵鋪", npc_name_zh: "石師傅" }], smithy: "smithy_mist_ferry", enchanter: null, can_use: true, problem_zh: null,
  slots: [{ slot_type: "weapon", name_zh: "武器", grade_amount: 3, affixes: [{ id: "affix_a", text_zh: "攻擊 +1" }] }],
  rarities: [{ rarity: "rare", name_zh: "稀有", cost_zh: "金幣 10 × 物品等級" }],
  materials: [mat("item_coarse_material", 5, true), mat("item_mist_crystal", 2, false, "傾向：敏捷 +n"), mat("item_wolf_fang", 4, false, "傾向：力量 +n"), mat("item_living_bone", 1, false, "傾向：體質 +n"), mat("item_lava_core", 1, false, "傾向：點燃")],
  flavor_max: 3, recipes: [], gear: [], essence: 0, note_zh: "沒人試過的材料組合只看得到傾向",
} as unknown as WorldCrafting;
const NOOP = (): void => undefined;

function Panel({ caption, width, children }: { caption: string; width: number; children: ReactNode }) {
  return (
    <div className="panel" style={{ width }}>
      <div className="ptitle">{caption}</div>
      {children}
    </div>
  );
}

function SetList() {
  return (
    <section>
      <h2>清單列（正式元件、正式樣式；圖示 24、裝備列與沒圖的物品留 24 空位）　右：一列真 1 倍最近鄰 ×3</h2>
      <div className="row">
        <Panel caption="商店：買（ShopPanel 第一張）＋賣東西（第二張，含一列裝備）" width={460}>
          <div data-crop="shop"><ShopPanel shop={SHOP} inventory={SELL_INV} busy={false} onAct={NOOP} /></div>
        </Panel>
        <Panel caption="背包滿了：選要丟哪件（LootChoicePanel）" width={460}>
          <div data-crop="loot"><LootChoicePanel pending={PENDING} inventory={LOOT_INV} busy={false} onAct={NOOP} /></div>
        </Panel>
        <Panel caption="整理腰包（PouchEditor）" width={400}>
          <PouchEditor inventory={INVENTORY} busy={false} onAct={NOOP} onDone={NOOP} />
        </Panel>
        <Panel caption="鐵匠：特色材料（SmithyPanel 打造；圖示在 checkbox 和名字之間）" width={460}>
          <SmithyPanel crafting={CRAFTING} busy={false} onAct={NOOP} initialTab="craft" />
        </Panel>
        <Crops />
      </div>
    </section>
  );
}

/** 把頁上真的畫出來的清單列（含圖示）做最近鄰放大：讀列裡的 `canvas.item-icon` 與位置，畫到一張畫布上（文字不畫，只看圖示與對齊）。 */
function Crops() {
  const [rows, setRows] = useState<{ key: string; cvs: HTMLCanvasElement[]; top: number[] }[]>([]);
  useEffect(() => {
    const t = window.setTimeout(() => {
      const out: { key: string; cvs: HTMLCanvasElement[]; top: number[] }[] = [];
      document.querySelectorAll<HTMLElement>(".world-shop-list li, .world-craft-material").forEach((li, i) => {
        const cvs = [...li.querySelectorAll<HTMLCanvasElement>("canvas.item-icon")];
        if (cvs.length === 0 || i > 40) return;
        out.push({ key: String(i), cvs, top: cvs.map((c) => c.getBoundingClientRect().top) });
      });
      setRows(out.slice(0, 6));
    }, 300);
    return () => window.clearTimeout(t);
  }, []);
  return (
    <Panel caption="清單列的 24 圖示：真 1 倍（DPR 1 拍）的左上角位置與最近鄰 ×3" width={300}>
      {rows.map((r) => (
        <div key={r.key} className="one">
          {r.cvs.map((c, j) => <Zoomed key={j} cv={c} px={24} zoom={3} />)}
          <span className="lab">y = {r.top.map((v) => v.toFixed(2)).join(", ")}</span>
        </div>
      ))}
    </Panel>
  );
}

const LETTER = (id: string, items: { item: string; count: number }[], gold = 0) => ({
  id, sender: "c_bob", sender_name: "老鐵", recipient: "c_me", recipient_name: "阿霧", from_zh: "灰燼荒原・餘燼集", sent_at: 0, expires_at: 0, days_left: 2, note: "焦鐵給你打鞋。",
  items: items.map((x) => ({ item: x.item, name_zh: BY_ID.get(x.item)?.name_zh ?? x.item, count: x.count, ...(BY_ID.get(x.item)?.color !== undefined ? { color: BY_ID.get(x.item)!.color } : {}), ...(BY_ID.get(x.item)?.kind === "material" ? { rare: BY_ID.get(x.item)!.rare === true } : {}) })),
  gear: [], gold, tax: 0, status_zh: "可以領", action: "claim", can_act: true, can_refuse: true,
});
const MAIL = {
  postman: { id: "postman_axin", name_zh: "阿信", race_zh: "人類", role_zh: "霧渡鎮的郵差", region: "cloud_ridge", location: "mist_ferry", place_zh: "雲嶺・霧渡鎮", portrait: null },
  here: true, line_zh: "「有你的信啦，快來拿！」",
  inbox: [LETTER("mail_1", [{ item: "item_scorched_iron", count: 3 }, { item: "item_dye_jade", count: 1 }, { item: "item_hp_potion_medium", count: 2 }]), LETTER("mail_2", [{ item: "item_molten_heart", count: 1 }, { item: "item_unknown_thing", count: 1 }], 270)],
  returned: [], outgoing: [], sendable: [bag("item_hp_potion_small", 3), bag("item_wolf_fang", 5), bag("item_dye_indigo")],
  gold: 120, mailbox_count: 2, mailbox_max: 20, max_attachments: 3, note_max: 40, tax_permille: 100, min_level: 3, level_ok: true, return_days: 3,
  footer_zh: "信只能在城鎮的郵差這裡領；3 天沒領會自動退回寄件人，季末清掉。", send_note_zh: "3 天內沒人領，會自動退回給你。",
} as unknown as MailView;
const NEVER = (): Promise<never> => new Promise(() => undefined);
const MAIL_API: MailApi = { mail: async () => MAIL, recipients: NEVER, quote: NEVER, send: NEVER, claim: NEVER, refuse: NEVER };

function SetScene() {
  return (
    <section>
      <h2>背包 6×5＋腰包（BagContents，物品 42 與裝備 42 混排、個數照現行；「沒圖的東西」退回名字小牌）</h2>
      <div className="row">
        <Panel caption="背包" width={700}>
          <div className="world-bag-screen" data-crop="bag"><BagContents inventory={INVENTORY} busy={false} onAct={NOOP} canUse /></div>
        </Panel>
        <Panel caption="信件附件（收件匣；物品 32、小牌高 32）" width={720}>
          <div data-crop="mail"><MailPanel mailApi={MAIL_API} inventory={INVENTORY} tab="inbox" initial={{ mail: MAIL }} /></div>
        </Panel>
        <Panel caption="拿到物品飛進背包：停住那一格（.item-fly.still）物品｜沒外觀的裝備｜有外觀的裝備；最近鄰 ×4" width={520}>
          <div className="flyrow" data-crop="fly">
            {[
              { kind: "item", item: "item_living_bone", color: null, rare: true },
              { kind: "item", item: "item_dye_jade", color: "#3E8E6A", rare: null },
              { kind: "generic", gear: false },
              { kind: "generic", gear: true },
              { kind: "gear", look: LOOK_SWORD, slot: "main_hand" },
            ].map((c, i) => (
              <div key={i} className="item-fly still" style={{ position: "relative", margin: 0, animation: "none", transform: "none" }}>
                <GainFlyIcon choice={c as never} />
              </div>
            ))}
          </div>
          <div className="flyrow big">
            {[
              { kind: "item", item: "item_living_bone", color: null, rare: true },
              { kind: "generic", gear: false },
              { kind: "generic", gear: true },
              { kind: "gear", look: LOOK_SWORD, slot: "main_hand" },
            ].map((c, i) => (
              <div key={i} style={{ zoom: 4 }}>
                <div className="item-fly still" style={{ position: "relative", margin: 0, animation: "none", transform: "none", filter: "none" }}>
                  <GainFlyIcon choice={c as never} />
                </div>
              </div>
            ))}
          </div>
          <div className="lab">物品與通用圖示：28 格裡直徑 26 的圓（金邊壓在圓上）；有外觀的裝備：直徑 32、金邊畫在圓外（6Q-1）。開發 PM 定第 5 節第 8 點選 (a)：維持，物品比裝備小一圈是預期。</div>
        </Panel>
      </div>
    </section>
  );
}

function SetMissing() {
  const m = missing();
  return (
    <section>
      <h2>content/world/items.yaml 裡有、圖示表裡沒有的 id：{m.length} 個（內容 {CONTENT.length} 個，表 {QI.list().length} 個含通用 2）</h2>
      <pre className="out" id="missing">{m.length === 0 ? "（無）" : m.join("\n")}</pre>
    </section>
  );
}

/** 樣張 q-icons-items.html ?part=hash 的 fp()。 */
function fp(c: HTMLCanvasElement): string { const d = c.getContext("2d")!.getImageData(0, 0, c.width, c.height).data; let a = 2166136261; for (let i = 0; i < d.length; i++) { a ^= d[i]!; a = Math.imul(a, 16777619) >>> 0; } return a.toString(16).padStart(8, "0"); }
/** 樣張的行格式：`id | 24:2倍/1倍 28:… 32:… 42:…`（每個用到的大小；28＝飛行圓，照 frameOf）。 */
const hashLines = (): string[] => QI.list().map(({ id, entry: e }) => `${id} | ${sizesOf(e).map((px) => `${px}:${fp(QI.canvas(id, px, 2))}/${fp(QI.canvas(id, px, 1))}`).join(" ")}`);
function SetHash() {
  const L = hashLines();
  useEffect(() => { document.body.dataset.hash = L.join("\n"); }, [L]);
  return <pre className="out" id="hash">{L.join("\n")}</pre>;
}

function App() {
  return (
    <>
      {SETS.map((s) => (s === "a" ? <SetA key={s} /> : s === "fly" ? <SetFly key={s} /> : s === "list" ? <SetList key={s} /> : s === "scene" ? <SetScene key={s} /> : s === "missing" ? <SetMissing key={s} /> : s === "hash" ? <SetHash key={s} /> : null))}
    </>
  );
}

(window as unknown as Record<string, unknown>)["__qiItemDev"] = { canvas: QI.canvas, hash: hashLines, missing };
void waitForFonts().then(() => {
  createRoot(document.getElementById("root")!).render(<App />);
  window.setTimeout(() => { document.body.dataset.ready = "1"; }, 600);
});
