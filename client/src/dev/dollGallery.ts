// 開發用：紙娃娃一覽（Phase 3G-G5b）。開 `client/doll-gallery.html`（pnpm dev 後 /doll-gallery.html）。
// 不屬於正式 build；供美術 PM 驗收與截圖：6 套整套穿上 × 4 朝向、各欄位換裝對照、成對武器、不認得的值退回預設。
import type { Facing } from "../api/types";
import type { DollSpec, GearItem } from "../render/appearance";
import { resolveDollT } from "../render/testDolls";
import { raceLookToLook } from "../render/inkRace";
import raceLooks from "../render/fixtures/raceLooks.json";
import type { DollEquipment } from "../render/dollGear";
import { DOLL_FOOT_Y, DOLL_H, DOLL_W, drawFigurePose } from "../render/paperdoll";

const SCALE = 3;

function figure(equipment: DollEquipment[], template: string, facing: Facing, label: string, downed = false): HTMLElement {
  return figureOf(resolveDollT({ team: "ally", summon: false, template, weaponId: "", equipment }), facing, label, downed);
}

function figureOf(spec: DollSpec, facing: Facing, label: string, downed = false): HTMLElement {
  const box = document.createElement("div");
  box.className = "cell";
  const c = document.createElement("canvas");
  c.width = DOLL_W * SCALE;
  c.height = DOLL_H * SCALE;
  const ctx = c.getContext("2d");
  if (ctx !== null) {
    ctx.fillStyle = "#2b2f38";
    ctx.fillRect(0, 0, c.width, c.height);
    ctx.scale(SCALE, SCALE);
    ctx.translate(DOLL_W / 2, DOLL_FOOT_Y);
    drawFigurePose(ctx, spec, facing, downed);
  }
  box.appendChild(c);
  const t = document.createElement("div");
  t.textContent = label;
  box.appendChild(t);
  return box;
}

const ONLY = decodeURIComponent(location.hash.slice(1)); // 例：#② 只顯示該段（截圖用）

function section(title: string, cells: HTMLElement[]): void {
  if (ONLY !== "" && !title.startsWith(ONLY)) return;
  const h = document.createElement("h2");
  h.textContent = title;
  const row = document.createElement("div");
  row.className = "row";
  for (const c of cells) row.appendChild(c);
  document.body.append(h, row);
}

type L = Record<string, unknown>;
const e = (slot: string, look: L): DollEquipment => ({ slot, appearance: look as DollEquipment["appearance"] });
const FACINGS: Facing[] = ["south", "north", "east", "west"];

// 樣張 gear-all.html 的 6 套（關鍵字 id 換成正式 id：impact→collision、hidden→concealed、mark→marked、shock→charged）
const SETS: Array<[string, string, DollEquipment[]]> = [
  ["鐵壁騎士", "hero_fighter", [e("main_hand", { kind: "sword", form: "broad", material: "steel", rarity: "rare", keywords: ["collision"] }), e("off_hand", { kind: "kite_shield", form: "tower", material: "steel" }), e("head", { kind: "helmet", form: "greathelm", rarity: "rare" }), e("body", { kind: "plate", form: "full", rarity: "epic" }), e("hands", { kind: "gauntlets", form: "plate" }), e("feet", { kind: "greaves", form: "knee" })]],
  ["烈焰法師", "hero_mage", [e("main_hand", { kind: "staff", form: "long", rarity: "epic", keywords: ["ignite"] }), e("head", { kind: "hat", form: "wizard", dye: "red" }), e("body", { kind: "robe", form: "long", dye: "red", keywords: ["ignite"] }), e("hands", { kind: "cloth_gloves", form: "fingerless", dye: "black" }), e("feet", { kind: "shoes", form: "slipper", dye: "brown" })]],
  ["影刃", "hero_archer", [e("main_hand", { kind: "dual_dagger", form: "kris", material: "steel", rarity: "epic" }), e("head", { kind: "hood", form: "cowl", dye: "black" }), e("body", { kind: "leather", form: "vest", dye: "black" }), e("hands", { kind: "leather_gloves", form: "long", dye: "black" }), e("feet", { kind: "boots", form: "tall", dye: "black" })]],
  ["鷹眼槍手", "hero_archer", [e("main_hand", { kind: "longgun", form: "sniper", rarity: "rare", keywords: ["marked"] }), e("head", { kind: "hat", form: "wide", dye: "brown" }), e("body", { kind: "coat", form: "cape", dye: "brown" }), e("hands", { kind: "leather_gloves", form: "short" }), e("feet", { kind: "boots", form: "short" })]],
  ["撼地者", "hero_fighter", [e("main_hand", { kind: "hammer", form: "warhammer", material: "iron", rarity: "epic" }), e("head", { kind: "helmet", form: "horned" }), e("body", { kind: "mail", form: "scale", material: "copper" }), e("hands", { kind: "bracers", form: "ring" }), e("feet", { kind: "iron_boots", form: "sabaton" })]],
  ["潮雷念動", "hero_mage", [e("main_hand", { kind: "whip", form: "chain", material: "silver", keywords: ["charged"] }), e("off_hand", { kind: "orb", form: "floating", rarity: "epic", keywords: ["wet"] }), e("head", { kind: "circlet", form: "crown", material: "silver" }), e("body", { kind: "robe", form: "short", dye: "blue" }), e("hands", { kind: "bracers", form: "leather" }), e("feet", { kind: "shoes", form: "wrapped", dye: "white" })]],
];

for (const [name, tpl, eq] of SETS) section(`① ${name}（四個朝向）`, FACINGS.map((f) => figure(eq, tpl, f, `${name}・${f}`)));

// ② 各欄位換裝對照：同一個基底（hero_fighter）逐欄位換
const SLOT_VARIANTS: Array<[string, string, L[]]> = [
  ["head", "頭", [{ kind: "hood", form: "cowl" }, { kind: "hat", form: "wide" }, { kind: "cap", form: "fur" }, { kind: "cap", form: "leather" }, { kind: "helmet", form: "greathelm" }, { kind: "circlet", form: "crown" }]],
  ["body", "身", [{ kind: "coat", form: "cape" }, { kind: "robe", form: "short" }, { kind: "mail", form: "scale" }, { kind: "plate", form: "half" }, { kind: "leather", form: "hunter" }]],
  ["hands", "手", [{ kind: "bracers", form: "leather" }, { kind: "cloth_gloves", form: "fingerless" }, { kind: "leather_gloves", form: "long" }, { kind: "gauntlets", form: "mail" }]],
  ["feet", "腳", [{ kind: "shoes", form: "wrapped" }, { kind: "boots", form: "tall" }, { kind: "iron_boots", form: "sabaton" }, { kind: "greaves", form: "knee" }]],
  ["main_hand", "主手", [{ kind: "hammer", form: "mace" }, { kind: "spear", form: "trident" }, { kind: "spear", form: "halberd" }, { kind: "crossbow", form: "heavy" }, { kind: "pistol", form: "revolver" }, { kind: "shotgun", form: "double" }, { kind: "fist", form: "katar" }, { kind: "scythe", form: "long" }, { kind: "whip", form: "bladed" }, { kind: "sword", form: "arcane", material: "steel" }, { kind: "sword", form: "arcane", material: "steel", element: "fire" }]],
  ["off_hand", "副手", [{ kind: "kite_shield", form: "tower" }, { kind: "tome", form: "book" }, { kind: "orb", form: "ball", keywords: ["frozen"] }]],
];
for (const [slot, zh, variants] of SLOT_VARIANTS) {
  section(`② ${zh}（基底 hero_fighter；第一格＝沒穿，沿用範本）`, [
    figure([], "hero_fighter", "south", "沒穿"),
    ...variants.flatMap((v) => [figure([e(slot, v)], "hero_fighter", "south", `${String(v.kind)}・${String(v.form)}`), figure([e(slot, v)], "hero_fighter", "north", "背面")]),
  ]);
}

section("③ 成對武器（正面、背面、側面）", [
  ...FACINGS.map((f) => figure([e("main_hand", { kind: "dual_dagger", form: "short" })], "hero_archer", f, `雙匕首・${f}`)),
  ...(["south", "east"] as const).map((f) => figure([e("main_hand", { kind: "dual_pistol", form: "revolver" })], "hero_archer", f, `雙手槍・${f}`)),
]);
section("④ 拳套兩手都畫", FACINGS.map((f) => figure([e("main_hand", { kind: "fist", form: "knuckle" })], "hero_mage", f, `拳套・${f}`)));
section("⑤ 不認得的值退回預設、倒地、元素與材質", [
  figure([e("head", { kind: "???" }), e("body", { kind: "plate", form: "x", material: "unobtainium", dye: "pink", keywords: ["nope"] }), e("main_hand", { kind: "dagger", material: "???" })], "hero_fighter", "south", "不認得"),
  figure([e("body", { kind: "mail", material: "gold" }), e("main_hand", { kind: "sword", keywords: ["ignite"] }), e("neck", { kind: "pendant" }), e("ring_1", { kind: "ring" })], "hero_fighter", "south", "金鎖甲＋火劍＋項鍊戒指不畫"),
  figure([e("main_hand", { kind: "sword", keywords: ["frozen"] }), e("body", { kind: "mail", material: "crystal", keywords: ["frozen"] })], "hero_fighter", "south", "冰＋晶石"),
  figure(SETS[0]![2], "hero_fighter", "south", "倒地", true),
]);

// ⑥ 真側面（Phase 3S-2）：頭部裝備全部 kind（朝東、朝西）、盾／書／珠、披風（披風沒有對應的裝備類別，直接指定部件）
const BASE = resolveDollT({ team: "ally", summon: false, template: "hero_fighter", weaponId: "one_handed_sword" });
const withGear = (g: DollSpec["gear"]): DollSpec => ({ ...BASE, gear: { ...BASE.gear, ...g } });
const HEADS: GearItem[] = [{ kind: "helmet", material: "steel" }, { kind: "horned_helm", material: "steel" }, { kind: "greathelm", material: "steel" }, { kind: "hood", material: "cloth" }, { kind: "wizard_hat", material: "cloth", color: "#8a2f3a" }, { kind: "wide_hat", material: "leather" }, { kind: "cap", material: "leather" }, { kind: "cap", form: "fur", material: "leather" }, { kind: "crown", material: "gold" }, { kind: "bandana", material: "cloth", color: "#3a6aa8" }];
for (const f of ["east", "west"] as const) section(`⑥ 側面・頭部裝備（${f}）`, HEADS.map((h) => figureOf(withGear({ head: h }), f, `${h.kind}${h.form !== undefined ? `・${h.form}` : ""}`)));
const CAPE: GearItem = { kind: "cape", material: "cloth", color: "#7a2a3a" };
const OFFS: Array<[string, GearItem]> = [["圓盾", { kind: "shield_round", material: "iron" }], ["塔盾", { kind: "shield_kite", form: "tower", material: "steel" }], ["鳶盾", { kind: "shield_kite", material: "steel" }], ["法書", { kind: "tome", material: "leather" }], ["法器珠", { kind: "orb", form: "ball", element: "ice", material: "silver" }]];
section("⑥ 側面・盾、書、珠、披風", [...OFFS.map(([n, it]) => figureOf(withGear({ off_hand: it }), "east", n)), figureOf(withGear({ cloak: CAPE }), "east", "披風"), figureOf(withGear({ cloak: CAPE, off_hand: OFFS[1]![1], head: HEADS[1]! }), "east", "披風＋塔盾＋角盔"), figureOf(withGear({ cloak: CAPE, off_hand: OFFS[0]![1], head: HEADS[4]! }), "west", "披風＋圓盾＋巫師帽（西）")]);

// ⑦ 真側面・武器（Phase 3S-3）：每種 kind × 形制朝東；長柄、劍不蓋臉、槍口朝面向方向；成對武器（副手畫在遠側、較暗）；朝西幾個
const W = (kind: string, form?: string, extra: Partial<GearItem> = {}): GearItem => ({ kind, form, material: kind === "bow" || kind === "staff" ? "wood" : "steel", ...extra });
const wlabel = (w: GearItem): string => `${w.kind}${w.form !== undefined ? `・${w.form}` : ""}`;
const MELEE: GearItem[] = [W("sword"), W("sword", "arcane"), W("sword", "arcane", { element: "fire" }), W("greatsword"), W("dagger"), W("axe"), W("hammer", "mace"), W("hammer", "flail"), W("hammer", "warhammer"), W("scythe"), W("fist", "knuckle"), W("fist", "katar"), W("fist", "claw")];
const POLES: GearItem[] = [W("spear"), W("spear", "halberd"), W("spear", "trident"), W("staff"), W("staff", "totem"), W("staff", "scepter"), W("whip", "chain"), W("whip", "bladed"), W("bow"), W("crossbow", "light"), W("crossbow", "heavy"), W("crossbow", "repeater")];
const GUNS: GearItem[] = [W("longgun", "flintlock"), W("longgun", "hunting"), W("longgun", "sniper"), W("pistol", "flintlock"), W("pistol", "revolver"), W("pistol", "derringer"), W("shotgun", "blunderbuss"), W("shotgun", "double"), W("shotgun", "pump")];
const solo = (ws: GearItem[], f: Facing): HTMLElement[] => ws.map((w) => figureOf(withGear({ main_hand: w, off_hand: undefined }), f, wlabel(w)));
section("⑦ 側面・武器（近戰、拳套）", solo(MELEE, "east"));
section("⑦ 側面・武器（長柄、鞭、弓、弩）", solo(POLES, "east"));
section("⑦ 側面・武器（槍：槍口朝面向方向）", solo(GUNS, "east"));
const PAIRS: GearItem[] = [W("dagger"), W("sword"), W("pistol", "revolver"), W("axe"), W("whip", "chain")];
section("⑦ 側面・成對武器（副手畫在遠側、較暗）", [...PAIRS.map((w) => figureOf(withGear({ main_hand: w, off_hand: w }), "east", `${wlabel(w)}×2`)), figureOf(withGear({ main_hand: W("dagger"), off_hand: W("dagger") }), "west", "dagger×2（西）")]);
section("⑦ 側面・武器（朝西）", solo([W("sword"), W("greatsword"), W("staff"), W("spear"), W("longgun", "sniper"), W("pistol", "revolver"), W("bow")], "west"));

// ⑧ C 畫風・樣張畫過的裝備與武器（Phase C-1b）：頭、手持物、圓盾，各四朝向；對照 docs/art/story.png
const C_HEADS: GearItem[] = [{ kind: "helmet", material: "steel" }, { kind: "hood", material: "cloth", color: "#5a4a7a" }, { kind: "wizard_hat", material: "cloth", color: "#2c4f8a" }];
const C_WEAPONS: GearItem[] = [W("sword"), W("dagger"), W("axe"), W("staff"), W("staff", "long", { element: "fire" }), W("bow")];
const C_SHIELD: GearItem = { kind: "shield_round", material: "wood", color: "#2f5fae" };
const C_SETS: Array<[string, DollSpec["gear"]]> = [
  ["騎士", { head: C_HEADS[0]!, body: { kind: "plate", material: "steel" }, main_hand: W("sword"), off_hand: C_SHIELD }],
  ["法師", { head: C_HEADS[2]!, body: { kind: "robe", color: "#5a3a8a" }, main_hand: W("staff", "long", { element: "ice" }) }],
  ["弓手", { head: C_HEADS[1]!, body: { kind: "leather", material: "leather" }, main_hand: W("bow"), cloak: { kind: "cape", color: "#2f6a4a" } }],
  ["斧手", { body: { kind: "shirt", color: "#b8a888" }, main_hand: W("axe"), off_hand: W("axe") }],
];
section("⑧ C-1b・四方向（整套）", C_SETS.flatMap(([n, g]) => FACINGS.map((f) => figureOf(withGear({ ...g, ...(g.off_hand === undefined ? { off_hand: undefined } : {}) }), f, `${n}・${f}`))));
for (const f of FACINGS) {
  section(`⑧ C-1b・頭部裝備（${f}）`, C_HEADS.map((h) => figureOf(withGear({ head: h }), f, h.kind)));
  section(`⑧ C-1b・武器與圓盾（${f}）`, [
    ...C_WEAPONS.map((w) => figureOf(withGear({ main_hand: w, off_hand: undefined }), f, wlabel(w))),
    figureOf(withGear({ main_hand: W("sword"), off_hand: C_SHIELD }), f, "sword＋圓盾"),
    figureOf(withGear({ main_hand: W("dagger"), off_hand: W("dagger") }), f, "dagger×2"),
    figureOf(withGear({ main_hand: W("axe"), off_hand: W("axe") }), f, "axe×2"),
  ]);
}

// ⑨ C-2a・其餘防具與副手：身體、頭、手、腳、副手各形制，四朝向
const G = (kind: string, form?: string, extra: Partial<GearItem> = {}): GearItem => ({ kind, ...(form === undefined ? {} : { form }), ...extra });
const C2_ROWS: Array<[string, Array<[string, DollSpec["gear"]]>]> = [
  ["身體", [
    ["mail chain", { body: G("mail", "chain", { material: "steel" }) }],
    ["mail scale", { body: G("mail", "scale", { material: "iron" }) }],
    ["coat travel", { body: G("coat", "travel", { material: "leather" }) }],
    ["coat cape", { body: G("coat", "cape", { color: "#7a2f3a" }) }],
  ]],
  ["頭", [
    ["wide_hat", { head: G("wide_hat", "wide", { color: "#6a4a2a" }) }],
    ["cap leather", { head: G("cap", "leather", { material: "leather" }) }],
    ["cap fur", { head: G("cap", "fur", { material: "leather" }) }],
    ["bandana", { head: G("bandana", "bandana", { color: "#b03a3a" }) }],
    ["crown", { head: G("crown", "crown", { material: "gold" }) }],
    ["horned_helm", { head: G("horned_helm", "horned", { material: "steel" }) }],
    ["greathelm", { head: G("greathelm", "greathelm", { material: "steel" }) }],
  ]],
  ["手", [
    ["gloves plain", { hands: G("gloves", "plain", { color: "#c8c0a8" }), main_hand: undefined, off_hand: undefined }],
    ["gloves fingerless", { hands: G("gloves", "fingerless", { material: "leather" }), main_hand: undefined, off_hand: undefined }],
    ["gloves long", { hands: G("gloves", "long", { material: "leather" }), main_hand: undefined, off_hand: undefined }],
    ["gauntlets plate", { hands: G("gauntlets", "plate", { material: "steel" }), main_hand: undefined, off_hand: undefined }],
    ["gauntlets mail", { hands: G("gauntlets", "mail", { material: "iron" }), main_hand: undefined, off_hand: undefined }],
    ["bracers leather", { hands: G("bracers", "leather", { material: "leather" }), main_hand: undefined, off_hand: undefined }],
    ["bracers ring", { hands: G("bracers", "ring", { material: "copper" }), main_hand: undefined, off_hand: undefined }],
  ]],
  ["腳", [
    ["shoes slipper", { feet: G("shoes", "slipper", { color: "#6a5a8a" }) }],
    ["shoes wrapped", { feet: G("shoes", "wrapped", { material: "cloth" }) }],
    ["iron_boots", { feet: G("iron_boots", "plain", { material: "iron" }) }],
    ["sabaton", { feet: G("iron_boots", "sabaton", { material: "steel" }) }],
  ]],
  ["副手", [
    ["kite", { off_hand: G("shield_kite", "kite", { material: "iron" }), main_hand: W("sword") }],
    ["tower", { off_hand: G("shield_kite", "tower", { material: "wood" }), main_hand: W("sword") }],
    ["tome book", { off_hand: G("tome", "book", { material: "leather" }), main_hand: W("staff") }],
    ["tome scroll", { off_hand: G("tome", "scroll", { material: "cloth" }), main_hand: W("staff") }],
    ["orb ball", { off_hand: G("orb", "ball", { material: "crystal", element: "ice" }), main_hand: W("staff") }],
    ["orb floating", { off_hand: G("orb", "floating", { material: "crystal", element: "fire" }), main_hand: W("staff") }],
  ]],
];
for (const f of FACINGS) {
  for (const [row, items] of C2_ROWS) section(`⑨ C-2a・${row}（${f}）`, items.map(([n, g]) => figureOf(withGear(g), f, n)));
}

// ⑩ C-2a・整套代表（四方向）
const C2_KITS: Array<[string, DollSpec["gear"]]> = [
  ["重甲", { head: G("greathelm", "greathelm", { material: "steel" }), body: G("mail", "chain", { material: "steel" }), hands: G("gauntlets", "plate", { material: "steel" }), feet: G("iron_boots", "sabaton", { material: "steel" }), off_hand: G("shield_kite", "tower", { material: "iron" }), main_hand: W("axe") }],
  ["旅人", { head: G("wide_hat", "wide", { color: "#6a4a2a" }), body: G("coat", "cape", { color: "#7a2f3a" }), hands: G("gloves", "long", { material: "leather" }), feet: G("shoes", "wrapped", { material: "cloth" }), off_hand: G("tome", "book", { material: "leather" }), main_hand: W("dagger") }],
  ["術士", { head: G("crown", "crown", { material: "gold" }), body: G("robe", "long", { color: "#3a4a8a" }), hands: G("bracers", "ring", { material: "copper" }), feet: G("shoes", "slipper", { color: "#6a5a8a" }), off_hand: G("orb", "floating", { material: "crystal", element: "fire" }), main_hand: W("staff") }],
];
section("⑩ C-2a・整套代表（四方向）", C2_KITS.flatMap(([n, g]) => FACINGS.map((f) => figureOf(withGear(g), f, `${n}・${f}`))));

// ⑪ C-2b・其餘武器（四朝向）：巨劍、錘、矛、弩、火槍、霰彈槍、手槍、拳套、鐮刀、鞭、魔導劍、權杖、圖騰杖、成對武器、護膝
const C2B_A: GearItem[] = [W("sword", "curved"), W("sword", "arcane"), W("sword", "arcane", { element: "fire" }), W("greatsword"), W("greatsword", "zhanma"), W("greatsword", "serrated"), W("hammer", "mace"), W("hammer", "flail"), W("hammer", "warhammer"), W("scythe"), W("fist", "knuckle"), W("fist", "katar"), W("fist", "claw")];
const C2B_B: GearItem[] = [W("spear"), W("spear", "halberd"), W("spear", "trident"), W("staff", "scepter", { element: "ice" }), W("staff", "totem"), W("staff", "wand", { element: "fire" }), W("whip"), W("whip", "chain"), W("whip", "bladed"), W("crossbow", "light"), W("crossbow", "heavy"), W("crossbow", "repeater")];
const C2B_C: GearItem[] = [W("longgun", "flintlock"), W("longgun", "hunting"), W("longgun", "sniper"), W("pistol", "flintlock"), W("pistol", "revolver"), W("pistol", "derringer"), W("shotgun", "blunderbuss"), W("shotgun", "double"), W("shotgun", "pump")];
const C2B_PAIRS: GearItem[] = [W("dagger", "short"), W("dagger", "kris"), W("pistol", "revolver"), W("pistol", "flintlock"), W("hammer", "mace"), W("fist", "claw")];
for (const f of FACINGS) {
  section(`⑪ C-2b・近戰（${f}）`, C2B_A.map((w) => figureOf(withGear({ main_hand: w, off_hand: undefined }), f, wlabel(w))));
  section(`⑪ C-2b・長柄、杖、鞭、弩（${f}）`, C2B_B.map((w) => figureOf(withGear({ main_hand: w, off_hand: undefined }), f, wlabel(w))));
  section(`⑪ C-2b・槍（${f}）`, C2B_C.map((w) => figureOf(withGear({ main_hand: w, off_hand: undefined }), f, wlabel(w))));
  section(`⑪ C-2b・成對武器（${f}）`, C2B_PAIRS.map((w) => figureOf(withGear({ main_hand: w, off_hand: w }), f, `${wlabel(w)}×2`)));
  section(`⑪ C-2b・護膝與側面副手外移（${f}）`, [
    figureOf(withGear({ feet: G("greaves", "knee", { material: "steel" }) }), f, "greaves knee"),
    figureOf(withGear({ feet: G("greaves", "long", { material: "steel" }) }), f, "greaves"),
    figureOf(withGear({ main_hand: W("sword"), off_hand: C_SHIELD }), f, "sword＋圓盾"),
    figureOf(withGear({ main_hand: W("sword"), off_hand: G("shield_kite", "kite", { material: "iron" }) }), f, "sword＋鳶盾"),
    figureOf(withGear({ main_hand: W("sword"), off_hand: G("shield_kite", "tower", { material: "wood" }) }), f, "sword＋塔盾"),
    figureOf(withGear({ main_hand: W("staff"), off_hand: G("tome", "book", { material: "leather" }) }), f, "staff＋書"),
    figureOf(withGear({ main_hand: W("staff"), off_hand: G("orb", "ball", { material: "crystal", element: "ice" }) }), f, "staff＋法球"),
  ]);
}

// ⑫ 3R-3b・種族外觀（耳、角、尾、膚色）與頭部裝備衝突規則；種族外觀來自 fixtures/raceLooks.json（content/races.yaml 的 look）
const RACE_LOOKS = raceLooks as Readonly<Record<string, Readonly<Record<string, unknown>>>>;
const RACE_ZH: Record<string, string> = { human: "人類", elf: "精靈", fox: "狐族", dragonkin: "龍裔", dwarf: "矮人", cyborg: "晶能義體人", orc: "獸人", fiend: "角魔", scalefolk: "鱗族", seafolk: "海民" };
const RACE_ORDER = ["human", "elf", "fox", "dragonkin", "dwarf", "cyborg", "orc", "fiend", "scalefolk", "seafolk"];
const raceSpec = (race: string, g: DollSpec["gear"] = {}): DollSpec => {
  const d = withGear({ main_hand: W("sword"), off_hand: undefined, ...g });
  return { ...d, look: { ...d.look, ...raceLookToLook(RACE_LOOKS[race]) } };
};
const raceCell = (race: string, g: DollSpec["gear"], f: Facing, label: string): HTMLElement => figureOf(raceSpec(race, g), f, `${RACE_ZH[race] ?? race}${label}`);
for (const f of FACINGS) section(`⑫ 3R-3b・10 族（${f}）`, RACE_ORDER.map((r) => raceCell(r, {}, f, "")));
const HAT = (kind: string, c = "#7a5a3a"): GearItem => ({ kind, material: "cloth", color: c });
const HELM = (kind: string): GearItem => ({ kind, material: "steel" });
const CROWN: GearItem = { kind: "crown", material: "gold" };
const HOOD = HAT("hood", "#5a4a7a");
const WIZ = HAT("wizard_hat", "#2c4f8a");
const ROBE: GearItem = { kind: "robe", color: "#5a3a8a" };
const RED_CAPE: GearItem = { kind: "cape", color: "#a83030" };
const conflict = (title: string, cells: Array<[string, DollSpec["gear"]]>, race: string, facings: Facing[]): void => {
  for (const f of facings) section(`⑫ 3R-3b・衝突・${title}（${f}）`, cells.map(([n, g]) => raceCell(race, g, f, `＋${n}`)));
};
conflict("角魔＋帽子", [["沒戴", {}], ["寬帽", { head: HAT("wide_hat") }], ["巫師帽", { head: WIZ }], ["皮帽", { head: HAT("cap") }], ["頭巾", { head: HAT("bandana", "#a83030") }], ["角盔", { head: HELM("horned_helm") }], ["頭盔", { head: HELM("helmet") }], ["兜帽", { head: HOOD }], ["皇冠", { head: CROWN }]], "fiend", ["south", "east", "north"]);
conflict("狐族＋頭部裝備", [["沒戴", {}], ["兜帽", { head: HOOD }], ["頭盔", { head: HELM("helmet") }], ["皮帽", { head: HAT("cap") }], ["頭巾", { head: HAT("bandana", "#a83030") }], ["寬帽", { head: HAT("wide_hat") }], ["皇冠", { head: CROWN }]], "fox", ["south", "east", "north"]);
conflict("狐族＋長袍與披風（尾巴從下襬露出）", [["長袍", { body: ROBE }], ["短袍", { body: { ...ROBE, form: "short" } }], ["披風", { cloak: RED_CAPE }]], "fox", ["south", "east", "north"]);
conflict("角魔＋披風與長袍（背面尾巴在披風上）", [["披風", { cloak: RED_CAPE }], ["披風＋長袍", { cloak: RED_CAPE, body: ROBE }], ["沒披風", {}]], "fiend", ["north", "south", "east"]);
conflict("精靈＋頭部裝備（尖耳伸出）", [["沒戴", {}], ["頭盔", { head: HELM("helmet") }], ["兜帽", { head: HOOD }], ["寬帽", { head: HAT("wide_hat") }], ["皮帽", { head: HAT("cap") }]], "elf", ["south", "east", "north"]);
conflict("鱗族＋頭部裝備（鰭耳）", [["沒戴", {}], ["兜帽", { head: HOOD }], ["頭盔", { head: HELM("helmet") }], ["巫師帽", { head: WIZ }]], "scalefolk", ["south", "east", "north"]);
conflict("龍裔＋帽子、長袍（龍角、粗龍尾）", [["沒戴", {}], ["寬帽", { head: HAT("wide_hat") }], ["頭盔", { head: HELM("helmet") }], ["長袍", { body: ROBE }]], "dragonkin", ["south", "east", "north"]);
conflict("矮人＋板甲＋大盾（體型與鬍子屬 3R-3c，這裡只有膚色）", [["板甲＋塔盾", { body: { kind: "plate", material: "steel" }, off_hand: G("shield_kite", "tower", { material: "wood" }) }]], "dwarf", ["south", "east", "north"]);
