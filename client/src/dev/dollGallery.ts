// 開發用：紙娃娃一覽（Phase 3G-G5b）。開 `client/doll-gallery.html`（pnpm dev 後 /doll-gallery.html）。
// 不屬於正式 build；供美術 PM 驗收與截圖：6 套整套穿上 × 4 朝向、各欄位換裝對照、成對武器、不認得的值退回預設。
import type { Facing } from "../api/types";
import type { DollSpec, GearItem } from "../render/appearance";
import { resolveDollT } from "../render/testDolls";
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
