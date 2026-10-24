// 開發用：紙娃娃一覽（Phase 3G-G5b）。開 `client/doll-gallery.html`（pnpm dev 後 /doll-gallery.html）。
// 不屬於正式 build；供美術 PM 驗收與截圖：6 套整套穿上 × 4 朝向、各欄位換裝對照、成對武器、不認得的值退回預設。
import type { Facing } from "../api/types";
import type { DollSpec, GearItem } from "../render/appearance";
import { resolveDollT } from "../render/testDolls";
import type { DollEquipment } from "../render/dollGear";
import { drawFigurePose } from "../render/paperdoll";

const SCALE = 3;

function figure(equipment: DollEquipment[], template: string, facing: Facing, label: string, downed = false): HTMLElement {
  return figureOf(resolveDollT({ team: "ally", summon: false, template, weaponId: "", equipment }), facing, label, downed);
}

function figureOf(spec: DollSpec, facing: Facing, label: string, downed = false): HTMLElement {
  const box = document.createElement("div");
  box.className = "cell";
  const c = document.createElement("canvas");
  c.width = 64 * SCALE;
  c.height = 64 * SCALE;
  const ctx = c.getContext("2d");
  if (ctx !== null) {
    ctx.fillStyle = "#2b2f38";
    ctx.fillRect(0, 0, c.width, c.height);
    ctx.scale(SCALE, SCALE);
    ctx.translate(32, 58);
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
