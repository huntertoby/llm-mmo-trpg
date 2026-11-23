// 開發用：E6-b2 招牌效果的驗收畫面（`client/dev/e6b2-gallery.html`，網址加 `?mute=1`；不屬於正式 build）。
// 規格 docs/phases/PhaseE6-b2計畫.md；美術移植需求 docs/art/E6-招牌-移植需求.md 第 4 節（每項都要截圖）。
// 現有內容沒有標招牌的詞條，這裡把資料直接塞進正式元件拍（字照 08 8.27、8.30 第 4 點；名字與說明照樣張 e6Signature.js 的假資料）。
// 畫好後 `document.body.dataset.ready = "1"`。
//   ?part=cards                 裝備卡：五種招牌、傳說、標灰兩種（超過 3 個、改寫規則衝突）
//   ?part=icons[&zoom=6]        類型小圖示 18／16／14 加標灰：真 1 倍，另外加最近鄰放大（zoom 倍）
//   ?part=offer                 一輪的三選一（有招牌和沒招牌的卡並排；剛打開時播一次強調）
//   ?part=offer&t=0.4           同上，強調動畫停在第 t 秒（關鍵影格）
//   ?part=fx                    一次性強調的關鍵影格 0.4、0.7、1.4 秒並排
//   ?part=world                 大世界背包畫面：背包滿時的列（「招牌」小標）、穿戴中的招牌勾選、背包詳情（第一次打開播強調）
//   ?part=panel                 一輪的角色面板：4 個勾 3 個、改寫規則衝突（點沒勾的那列看已滿提示）
import { createRoot } from "react-dom/client";
import { flushSync } from "react-dom";
import type { CSSProperties } from "react";
import type { GameRules, GearCandidate, GearItemInfo, Glossary, HeroGearSlot, RunHero, SignaturePanel, SignatureRow, WorldBagItem, WorldInventory, WorldView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { setGameRules, setGlossary } from "../battle/glossary";
import { waitForFonts } from "../render/fontLoad";
import { isSignatureKind, signatureGlyph, type SignatureKind } from "../render/qIcon/signature";
import { RunHeroPanel } from "../run/RunHeroPanel";
import campfire from "../run/fixtures/run_campfire.json";
import { RunGearOffer } from "../screens/RunGearOffer";
import { GearCardView } from "../ui/gear/GearCardView";
import { WorldBagScreen } from "../world/BagScreen";
import "../styles/index.css";

setGlossary(glossary as unknown as Glossary);
setGameRules((glossary as unknown as { rules: GameRules }).rules);
await waitForFonts();

const params = new URLSearchParams(location.search);
const part = params.get("part") ?? "cards";
const ZOOM = Number(params.get("zoom") ?? 1);
const T = params.get("t");

const LONG = "身上已經有 3 個招牌效果生效，這個沒有效果，可以在角色面板換選";
const SHORT = "已經有 3 個生效，這個沒有效果";
const RULE_OFF = (slot: string): string => `和${slot}的改寫規則衝突，沒有效果`;
const KIND_ZH: Record<SignatureKind, string> = { action: "新動作", reaction: "新反應", terrain: "地形規則", behavior: "行為改寫", rule: "改寫規則" };
const RARITY_ZH: Record<string, string> = { common: "普通", uncommon: "優良", rare: "稀有", epic: "史詩", legendary: "傳說" };

interface Sig {
  kind: SignatureKind;
  name: string;
  text: string;
  off?: string;
}
interface Demo {
  id: string;
  name: string;
  slot: string;
  slotZh: string;
  slotType: string;
  rarity: string;
  lv: number;
  look: Record<string, unknown>;
  lines: string[];
  sig?: Sig;
  legendary?: boolean;
  weaponZh?: string;
}

const W = (kind: string, form: string, material: string, rarity: string) => ({ kind, form, material, rarity, dye: null, style: null, keywords: [] });
const A = (kind: string, form: string, material: string, rarity: string, dye: string | null = null) => ({ kind, form, material, rarity, dye, style: null, keywords: [] });

const D: Record<string, Demo> = {
  hook: { id: "demo_hook", name: "勾魂鐮", slot: "main_hand", slotZh: "主手", slotType: "weapon", rarity: "rare", lv: 12, look: W("scythe", "hook", "steel", "rare"), weaponZh: "鉤鐮", lines: ["力量 +3", "流血傷害 +12%"], sig: { kind: "action", name: "鉤爪拉近", text: "1 AP，射程 4：把一個敵人拉到你身旁。冷卻 3 回合。" } },
  vest: { id: "demo_vest", name: "巡林者獵裝", slot: "body", slotZh: "身體", slotType: "body", rarity: "epic", lv: 14, look: A("leather", "hunter", "leather", "epic"), lines: ["敏捷 +3", "閃避 +3%"], sig: { kind: "reaction", name: "回身一刺", text: "敵人離開你身旁時，用主手打他一下。和其他反應共用每輪 1 次。" } },
  frost: { id: "demo_frost", name: "霜行長靴", slot: "feet", slotZh: "腳", slotType: "feet", rarity: "rare", lv: 12, look: A("boots", "tall", "leather", "rare"), lines: ["基礎加成：防禦值 +1%"], sig: { kind: "terrain", name: "霜行", text: "你走過的格子結 1 回合冰；你自己踩不會滑倒。" } },
  cleave: { id: "demo_cleave", name: "裂地大劍", slot: "main_hand", slotZh: "主手", slotType: "weapon", rarity: "epic", lv: 15, look: W("greatsword", "twohand", "steel", "epic"), weaponZh: "雙手劍・雙手", lines: ["力量 +4", "暴擊傷害 +15%", "技能強化：「橫掃」範圍 +1"], sig: { kind: "behavior", name: "劈出直線", text: "普攻改成往前打 2 格直線，只打敵人；傷害照形狀係數降低。" } },
  ember: { id: "demo_ember", name: "餘燼墜飾", slot: "neck", slotZh: "項鍊", slotType: "neck", rarity: "epic", lv: 14, look: A("pendant", "pendant", "gold", "epic"), lines: ["智力 +3", "火焰傷害 +10%"], sig: { kind: "rule", name: "慈焰", text: "你的火焰傷害打到隊友時，改成治療他。" } },
  mountain: { id: "demo_mountain", name: "移山者之盾", slot: "off_hand", slotZh: "副手", slotType: "offhand", rarity: "legendary", lv: 16, look: W("round_shield", "banded", "steel", "legendary"), legendary: true, lines: ["體質 +4", "格擋 +8%"], sig: { kind: "rule", name: "移山", text: "你可以推動任何物件，連巨石、石柱也推得動。" } },
  lava: { id: "demo_lava", name: "熔岩踏靴", slot: "feet", slotZh: "腳", slotType: "feet", rarity: "rare", lv: 13, look: A("iron_boots", "sabaton", "iron", "rare"), lines: ["基礎加成：防禦值 +3%", "火焰抗性 +10%"], sig: { kind: "terrain", name: "火行", text: "火表面不傷你，你站在火上也不會被點燃。", off: LONG } },
  blood: { id: "demo_blood", name: "血痕皮甲", slot: "body", slotZh: "身體", slotType: "body", rarity: "rare", lv: 13, look: A("leather", "vest", "leather", "rare", "red"), lines: ["基礎加成：防禦值 +3%", "敏捷 +2"], sig: { kind: "rule", name: "血痕", text: "你穿過敵人身旁的格子時，讓他流血 2 回合。", off: RULE_OFF("項鍊") } },
  gloves: { id: "demo_gloves", name: "獵人皮手套", slot: "hands", slotZh: "手", slotType: "hands", rarity: "uncommon", lv: 12, look: A("leather_gloves", "short", "leather", "uncommon"), lines: ["敏捷 +2", "命中 +4%"] },
};

function info(d: Demo): GearItemInfo {
  const sig = d.sig;
  const head = d.legendary === true ? "獨特效果" : "招牌";
  const affixes = [
    ...(sig === undefined
      ? []
      : [
          {
            affix_id: `affix_demo_${d.id}`,
            text_zh: sig.text,
            signature: sig.kind,
            signature_zh: `${head}・${KIND_ZH[sig.kind]}`,
            signature_name_zh: sig.name,
            off_zh: sig.off ?? null,
          },
        ]),
    ...d.lines.map((t, i) => ({ affix_id: `affix_demo_${d.id}_${i}`, text_zh: t })),
  ];
  return {
    id: d.id,
    name_zh: d.name,
    slot_type: d.slotType,
    weapon: null,
    weapon_name_zh: d.weaponZh ?? null,
    offhand: null,
    offhand_name_zh: null,
    offhand_traits_zh: [],
    two_handed: false,
    paired: false,
    tags: [],
    legendary: d.legendary === true,
    affixes,
    appearance: d.look,
    rarity: d.rarity,
    rarity_zh: RARITY_ZH[d.rarity] ?? null,
    item_level: d.lv,
    base_bonus_zh: null,
    points: 40,
  } as unknown as GearItemInfo;
}

function cand(d: Demo, now: Demo | null = null): GearCandidate {
  return { item: info(d), slot: d.slot, slot_zh: d.slotZh, current: now === null ? null : info(now), notes_zh: [], weapon_swap_zh: null } as unknown as GearCandidate;
}

const root = document.getElementById("root") ?? document.body.appendChild(document.createElement("div"));
const mount = (node: JSX.Element): void => {
  flushSync(() => createRoot(root).render(node));
};
const cap = (text: string, node: JSX.Element): JSX.Element => (
  <div>
    <div className="cap">{text}</div>
    {node}
  </div>
);

function cards(): void {
  mount(
    <div className="grid">
      {cap("新動作（稀有・主手）", <GearCardView cand={cand(D.hook!)} />)}
      {cap("新反應（史詩・身體）", <GearCardView cand={cand(D.vest!)} />)}
      {cap("地形規則（稀有・腳）", <GearCardView cand={cand(D.frost!)} />)}
      {cap("行為改寫（史詩・主手）", <GearCardView cand={cand(D.cleave!)} />)}
      {cap("改寫規則（史詩・項鍊）", <GearCardView cand={cand(D.ember!)} />)}
      {cap("傳說的獨特效果（副手）", <GearCardView cand={cand(D.mountain!)} />)}
      {cap("標灰：穿上後是第 4 個", <GearCardView cand={cand(D.lava!, D.frost!)} />)}
      {cap("標灰：改寫規則衝突", <GearCardView cand={cand(D.blood!, D.vest!)} />)}
    </div>,
  );
}

/** 真 1 倍：res 1 的畫布（灰階＝同一張圖畫上 grayscale＋50% 不透明，和 CSS 的標灰相同）。 */
function iconCanvas(kind: SignatureKind, box: number, grey: boolean, zoom: number): HTMLCanvasElement {
  const src = signatureGlyph(kind, box, 1);
  const c = document.createElement("canvas");
  c.width = box * zoom;
  c.height = box * zoom;
  c.className = "px";
  c.style.width = `${box * zoom}px`;
  c.style.height = `${box * zoom}px`;
  const x = c.getContext("2d");
  if (x !== null && src !== null) {
    x.imageSmoothingEnabled = false;
    if (grey) {
      x.filter = "grayscale(1)";
      x.globalAlpha = 0.5;
    }
    x.drawImage(src, 0, 0, src.width, src.height, 0, 0, box * zoom, box * zoom);
  }
  return c;
}

function icons(): void {
  const host = document.createElement("div");
  host.className = "icons";
  for (const [grey, zoom] of [[false, 1], [true, 1], [false, ZOOM], [true, ZOOM]] as const) {
    if (zoom === ZOOM && ZOOM === 1) continue;
    const title = document.createElement("h3");
    title.textContent = `${grey ? "標灰（灰階＋50%）" : "一般"}・${zoom === 1 ? "真 1 倍" : `最近鄰 ×${zoom}`}`;
    host.append(title);
    for (const box of [18, 16, 14]) {
      const line = document.createElement("div");
      line.className = "line";
      const label = document.createElement("span");
      label.className = "cap";
      label.textContent = `${box} px`;
      line.append(label);
      for (const kind of ["action", "reaction", "terrain", "behavior", "rule"] as const) {
        if (!isSignatureKind(kind)) continue;
        const cell = document.createElement("div");
        cell.className = "cell";
        const name = document.createElement("span");
        name.className = "cap";
        name.textContent = KIND_ZH[kind];
        cell.append(iconCanvas(kind, box, grey, zoom), name);
        line.append(cell);
      }
      host.append(line);
    }
  }
  root.append(host);
}

function offer(): void {
  if (T !== null) document.body.style.setProperty("--t", `${T}s`);
  document.body.classList.toggle("freeze", T !== null);
  const view = { screen: "gear_offer" as const, afterBattle: 3, candidates: [cand(D.hook!, null), cand(D.gloves!, null), cand(D.ember!, null)] };
  mount(<RunGearOffer seed={1} view={view} busy={false} onChoose={() => Promise.resolve(null)} />);
}

function row(d: Demo, over: Partial<SignatureRow> = {}): SignatureRow {
  const sig = d.sig!;
  return {
    key: `${d.slot}:affix_demo_${d.id}`,
    slot: d.slot,
    slot_zh: d.slotZh,
    item_name_zh: d.name,
    rarity: d.rarity,
    affix_id: `affix_demo_${d.id}`,
    kind: sig.kind,
    kind_zh: KIND_ZH[sig.kind],
    name_zh: sig.name,
    text_zh: sig.text,
    counted: true,
    rule: sig.kind === "rule",
    active: true,
    off_zh: null,
    ...over,
  };
}

/** 穿戴中：主手勾魂鐮（新動作）、身體血痕皮甲（改寫規則，和項鍊衝突）、腳熔岩踏靴（地形規則，第 4 個沒勾）、項鍊餘燼墜飾（改寫規則）、副手（新反應）。 */
const WORN: Demo[] = [D.hook!, { ...D.vest!, slot: "off_hand", slotZh: "副手", slotType: "offhand" }, D.blood!, D.lava!, D.ember!];
const PANEL: SignaturePanel = {
  rows: [
    row(D.hook!),
    row({ ...D.vest!, slot: "off_hand", slotZh: "副手" }),
    row(D.blood!, { active: false, off_zh: RULE_OFF("項鍊") }),
    row(D.lava!, { active: false, off_zh: SHORT }),
    row(D.ember!),
  ],
  active: 3,
  cap: 3,
  rules: 1,
  rule_cap: 1,
  has_rule: true,
  count_zh: "生效 3／3・改寫規則 1／1",
  full_zh: "已經有 3 個生效，先取消勾選一個，再勾這個。",
  chosen: [],
  problem_zh: null,
} as SignaturePanel;

function equipment(): HeroGearSlot[] {
  return WORN.map((d) => {
    const it = info({ ...d, sig: d.sig === undefined ? undefined : { ...d.sig, off: d.id === "demo_lava" ? LONG : d.id === "demo_blood" ? RULE_OFF("項鍊") : undefined } });
    return { slot: d.slot, slot_zh: d.slotZh, item: it } as unknown as HeroGearSlot;
  });
}

function panel(): void {
  const hero = { ...(campfire as unknown as { hero: RunHero }).hero, equipment: equipment(), signatures: PANEL } as RunHero;
  mount(
    <div className="panel-host">
      <RunHeroPanel hero={hero} busy={false} onChoose={() => Promise.resolve(null)} />
    </div>,
  );
}

function bagRow(d: Demo, sig: boolean): WorldBagItem {
  return { item: d.id, name_zh: `${d.name}（${d.lv} 級）`, kind_zh: "裝備", count: 1, description_zh: "", sell_price: 10, sellable: true, tradable: false, field_usable: false, gear: true, can_equip: true, signature: sig ? (d.sig?.kind ?? null) : null } as WorldBagItem;
}

function world(): void {
  const bag = [bagRow(D.frost!, true), bagRow(D.gloves!, false)];
  const inventory = {
    bag,
    slots_used: 30,
    slots_max: 30,
    pouch: [],
    pouch_count: 0,
    pouch_max: 3,
    can_pouch: true,
    pouch_problem_zh: null,
    consumables: [],
    equipped_zh: [],
    resonance_zh: [],
    equipment: equipment(),
    gear_cards: [cand(D.frost!, D.lava!), cand(D.gloves!, null)],
    signatures: PANEL,
  } as unknown as WorldInventory;
  const pending = { items: [bagRow(D.cleave!, true), bagRow(D.vest!, true), bagRow(D.gloves!, false)].map((r, i) => ({ ...r, item: `${r.item}_new${i}` })), over_slots: 2, hint_zh: "背包滿了：勾選要丟的，剩下的收進背包。" };
  const view = { inventory, wallet: null, pending_loot: pending, encounter: null, battle_id: null } as unknown as WorldView;
  mount(
    <div className="world-host" style={{ "--bag-cell": "48px" } as CSSProperties}>
      <WorldBagScreen view={view} busy={false} onAct={() => undefined} onClose={() => undefined} initialPick={`bag:${D.frost!.id}`} />
    </div>,
  );
}

/** 一次性強調的三個關鍵影格並排（各自停在 0.4、0.7、1.4 秒；物品 ID 不同，所以每張都播）。 */
function fx(): void {
  const frames = [0.4, 0.7, 1.4];
  mount(
    <div className="line">
      {frames.map((t) => (
        <div key={t} className="freeze" style={{ "--t": `${t}s`, width: 300 } as CSSProperties}>
          <div className="cap">{t} 秒</div>
          <GearCardView cand={cand({ ...D.hook!, id: `demo_hook_${t}` })} fx />
        </div>
      ))}
    </div>,
  );
}

const PARTS: Record<string, () => void> = { cards, icons, offer, fx, panel, world };
(PARTS[part] ?? cards)();
requestAnimationFrame(() => {
  document.body.dataset.ready = "1";
});
