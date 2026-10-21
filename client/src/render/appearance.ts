// 紙娃娃的外觀表（Phase 3-16b；來源：美術 PM 的 docs/art/移植需求.md 第 4 節與樣張 paperdoll.js 的 TEMPLATES）。
// 外觀只由資料欄位決定：主手 ← `weapon_id`（武器外觀表）；頭、身、手、腳、披風、副手、膚色、髮型 ← `template_id`（外觀表）。
// 新內容沒有對照時一律有預設，不得出錯：未知範本依陣營預設、召喚物用骷髏、不認得的 kind 只跳過該欄位。
// 純資料與純函式（不碰 Canvas），可以用 vitest 檢查。
import { ELEMENT_VFX } from "../battle/vfxPalette";
import { numToHex } from "./artPalette";

export interface GearItem {
  kind: string;
  material?: string;
  color?: string;
  element?: string;
  trim?: string;
  hilt?: string;
  /** 形制（同一種 `kind` 的不同畫法，例如杖的 `scepter` 權杖、`totem` 圖騰杖）；不認得時畫預設形制。 */
  form?: string;
}

export interface Look {
  skin: string;
  hair?: "short" | "long" | "none";
  hairColor?: string;
  pants?: string;
  trim?: string;
  skull?: boolean;
  eyes?: string;
}

export type GearSlot = "head" | "body" | "hands" | "feet" | "cloak" | "main_hand" | "off_hand";

export type Gear = Partial<Record<GearSlot, GearItem>>;

export interface DollSpec {
  look: Look;
  gear: Gear;
  rarity?: "epic" | "legendary";
  /** 圖騰：不畫小人，畫一根圖騰柱。 */
  totem?: boolean;
}

/** 每個欄位認得的 `kind`；不在清單內的該欄位不畫。 */
export const KNOWN_KINDS: Readonly<Record<GearSlot, readonly string[]>> = {
  head: ["hood", "helmet", "horned_helm", "wizard_hat", "bandana", "crown"],
  body: ["shirt", "leather", "mail", "plate", "robe", "ribs"],
  hands: ["gloves", "gauntlets"],
  feet: ["boots", "greaves"],
  cloak: ["cape"],
  main_hand: ["sword", "greatsword", "dagger", "axe", "hammer", "spear", "bow", "staff"],
  off_hand: ["shield_round", "shield_kite", "tome"],
};

/** 材質 → [主色, 暗色]；不認得的材質用布料色。 */
export const MATERIAL: Readonly<Record<string, readonly [string, string]>> = {
  cloth: ["#8a8f99", "#5d6168"],
  leather: ["#8a5a32", "#5e3b1f"],
  iron: ["#8d969f", "#5a6169"],
  steel: ["#c3ccd6", "#7d8794"],
  gold: ["#e8bb48", "#9c7420"],
  wood: ["#a06a36", "#6a4420"],
  bone: ["#e9e3cf", "#a8a08a"],
};

export const RARITY_GLOW: Readonly<Record<string, string>> = { epic: "#b06cff", legendary: "#ffbf3a" };

/** 元素 → 色（沿用技能特效的 `ELEMENT_VFX` 主色）；物理與不認得的元素回傳 `undefined`（不套元素色）。 */
export function elementTint(element: string | undefined): string | undefined {
  if (element === undefined || element === "physical") return undefined;
  const v = ELEMENT_VFX[element];
  return v === undefined ? undefined : numToHex(v.primary);
}

function known(slot: GearSlot, item: GearItem | undefined): GearItem | undefined {
  return item !== undefined && KNOWN_KINDS[slot].includes(item.kind) ? item : undefined;
}

// ---- 武器外觀表（`weapons.yaml` 的 id → 主手 kind；元素取自武器本身）----

interface WeaponLook {
  kind: string;
  material: string;
  element?: string;
  form?: string;
  twoHanded: boolean;
}

export const WEAPON_LOOKS: Readonly<Record<string, WeaponLook>> = {
  one_handed_sword: { kind: "sword", material: "steel", twoHanded: false },
  greatsword: { kind: "greatsword", material: "steel", twoHanded: true },
  dagger: { kind: "dagger", material: "iron", twoHanded: false },
  bow: { kind: "bow", material: "wood", twoHanded: true },
  fire_staff: { kind: "staff", material: "wood", element: "fire", twoHanded: true },
  lightning_staff: { kind: "staff", material: "wood", element: "lightning", twoHanded: true },
  frost_staff: { kind: "staff", material: "wood", element: "ice", twoHanded: true },
  // Phase 3-24a1：武器擴充第一批（斧、錘、矛已有畫法；權杖、圖騰杖是杖的形制）
  axe: { kind: "axe", material: "iron", twoHanded: false },
  hammer: { kind: "hammer", material: "iron", twoHanded: true },
  spear: { kind: "spear", material: "iron", twoHanded: true },
  scepter: { kind: "staff", material: "wood", form: "scepter", twoHanded: false },
  totem_staff: { kind: "staff", material: "wood", form: "totem", twoHanded: true },
};

/** 武器大類 → 主手 kind（`weapon_id` 不認得時的退回）。 */
export const WEAPON_CLASS_KIND: Readonly<Record<string, string>> = { melee: "sword", ranged: "bow", focus: "staff" };

const MATERIAL_OF_KIND: Readonly<Record<string, string>> = { sword: "steel", bow: "wood", staff: "wood" };

/** 主手外觀：依 `weapon_id`；未知依 `weapon_class`；都沒有畫劍。 */
export function weaponLook(weaponId: string | null | undefined, weaponClass?: string | null): WeaponLook {
  const hit = weaponId === null || weaponId === undefined ? undefined : WEAPON_LOOKS[weaponId];
  if (hit !== undefined) return hit;
  const kind = (weaponClass !== null && weaponClass !== undefined ? WEAPON_CLASS_KIND[weaponClass] : undefined) ?? "sword";
  return { kind, material: MATERIAL_OF_KIND[kind] ?? "steel", twoHanded: false };
}

// ---- 外觀表（鍵 template_id）----

const I = (kind: string, material: string, extra: Partial<GearItem> = {}): GearItem => ({ kind, material, ...extra });

const ITEMS = {
  tunic: I("shirt", "cloth", { color: "#4f7fbf" }),
  plain_shirt: I("shirt", "cloth"),
  leather_vest: I("leather", "leather"),
  green_leather: I("leather", "leather", { color: "#4f7a3a" }),
  chain_mail: I("mail", "iron"),
  plate_armor: I("plate", "steel"),
  mage_robe: I("robe", "cloth", { color: "#5a3fa0" }),
  boots: I("boots", "leather"),
  greaves: I("greaves", "steel"),
  gloves: I("gloves", "leather"),
  gauntlets: I("gauntlets", "steel"),
  hood_green: I("hood", "cloth", { color: "#3f6a32" }),
  hood_brown: I("hood", "cloth", { color: "#6a4a2e" }),
  iron_helmet: I("helmet", "iron"),
  horned_helm: I("horned_helm", "iron"),
  wizard_hat: I("wizard_hat", "cloth", { color: "#5a3fa0" }),
  bandana_red: I("bandana", "cloth", { color: "#b33a3a" }),
  round_shield: I("shield_round", "wood", { color: "#2f5fae" }),
  kite_shield: I("shield_kite", "wood", { color: "#8a5a32" }),
  tome: I("tome", "leather", { color: "#7a2a3a" }),
  red_cape: I("cape", "cloth", { color: "#a32a2a" }),
  blue_cape: I("cape", "cloth", { color: "#2c4f8a" }),
  dark_cape: I("cape", "cloth", { color: "#3a2a4a" }),
  storm_robe: I("robe", "cloth", { color: "#2c4f8a" }),
  storm_hat: I("wizard_hat", "cloth", { color: "#2c4f8a" }),
  ribs: I("ribs", "bone"),
} as const satisfies Record<string, GearItem>;

type ItemId = keyof typeof ITEMS;

const SLOT_OF: Readonly<Record<ItemId, GearSlot>> = {
  tunic: "body",
  plain_shirt: "body",
  leather_vest: "body",
  green_leather: "body",
  chain_mail: "body",
  plate_armor: "body",
  mage_robe: "body",
  ribs: "body",
  boots: "feet",
  greaves: "feet",
  gloves: "hands",
  gauntlets: "hands",
  hood_green: "head",
  hood_brown: "head",
  iron_helmet: "head",
  horned_helm: "head",
  wizard_hat: "head",
  bandana_red: "head",
  round_shield: "off_hand",
  kite_shield: "off_hand",
  tome: "off_hand",
  red_cape: "cloak",
  blue_cape: "cloak",
  dark_cape: "cloak",
  storm_robe: "body",
  storm_hat: "head",
};

export const SKIN = ["#f1c9a5", "#d9a47a", "#a8724c", "#7a4e32"] as const;

export interface Appearance extends DollSpec {
  /** 主手的材質／顏色覆寫（例如生鏽的劍）；主手的種類仍由 `weapon_id` 決定。 */
  mainStyle?: Partial<GearItem>;
}

function build(look: Look, ids: readonly ItemId[], extra: Partial<Appearance> = {}): Appearance {
  const gear: Gear = {};
  for (const id of ids) gear[SLOT_OF[id]] = ITEMS[id];
  return { look, gear, ...extra };
}

const RUSTY: Partial<GearItem> = { material: "iron", color: "#9a8a76" };

/** 單位範本 → 外觀（鍵是 `template_id`；8 個來自樣張，其餘為內容庫既有範本的補充）。 */
export const APPEARANCES: Readonly<Record<string, Appearance>> = {
  hero_fighter: build({ skin: SKIN[0], hair: "short", hairColor: "#6a3d1e" }, ["plate_armor", "greaves", "gauntlets", "round_shield", "blue_cape"]),
  hero_mage: build({ skin: SKIN[1], hair: "long", hairColor: "#c8c0b0", trim: "#e8bb48" }, ["mage_robe", "boots", "wizard_hat", "tome"]),
  hero_archer: build({ skin: SKIN[0], hair: "long", hairColor: "#c27a2c", pants: "#3a3a2a" }, ["green_leather", "boots", "gloves", "hood_green"]),
  bandit: build({ skin: SKIN[2], hair: "short", hairColor: "#2a1c14" }, ["leather_vest", "boots", "bandana_red"]),
  bandit_archer: build({ skin: SKIN[1], hair: "short", hairColor: "#3a2a1c" }, ["leather_vest", "boots", "hood_brown"]),
  bandit_shieldbearer: build({ skin: SKIN[3], hair: "short", hairColor: "#1c1410" }, ["chain_mail", "boots", "iron_helmet", "kite_shield"], { mainStyle: RUSTY }),
  bandit_boss: build({ skin: SKIN[2], hair: "short", hairColor: "#1c1410" }, ["chain_mail", "greaves", "gauntlets", "horned_helm", "red_cape"], { rarity: "epic" }),
  summon_skeleton_warrior: build({ skin: "#e9e3cf", skull: true, pants: "#d9d2bd", eyes: "#2a1030" }, ["ribs"], { mainStyle: RUSTY }),
  // 補充（內容庫既有範本，樣張沒有）
  // 隊友（模擬用範本）要和同職業的主角分得出來（美術 PM 3-16b 檢查第 3 項）：戰士鎖甲＋鳶盾、不披披風；弓手皮背心、不戴兜帽
  sim_companion_fighter: build({ skin: SKIN[3], hair: "short", hairColor: "#2a1c14" }, ["chain_mail", "greaves", "gauntlets", "kite_shield"]),
  sim_companion_archer: build({ skin: SKIN[1], hair: "long", hairColor: "#c27a2c", pants: "#3a3a2a" }, ["leather_vest", "boots", "gloves"]),
  // 風暴法師：深藍法袍與帽子、飾邊用雷的黃色（和紫袍的 hero_mage 分開，檢查第 2 項）
  hero_stormcaller: build({ skin: SKIN[0], hair: "long", hairColor: "#8fb8e8", trim: "#fff36b" }, ["storm_robe", "boots", "storm_hat", "tome"]),
  // 軍閥：鐵盔＋板甲＋深紫披風，不加外光（外光留給 bandit_boss，檢查第 1 項）
  bandit_warlord: build({ skin: SKIN[3], hair: "short", hairColor: "#1c1410" }, ["plate_armor", "greaves", "gauntlets", "iron_helmet", "dark_cape"]),
};

/** 骷髏身形：召喚物不在外觀表內時用。 */
function skeletonLook(): Appearance {
  return build({ skin: "#e9e3cf", skull: true, pants: "#d9d2bd", eyes: "#2a1030" }, ["ribs"]);
}

/** 陣營預設：我方 ＝ 布衣＋靴；敵方 ＝ 皮甲＋頭巾＋靴。 */
function factionDefault(team: string): Appearance {
  if (team === "enemy") return build({ skin: SKIN[2], hair: "short", hairColor: "#2a1c14" }, ["leather_vest", "boots", "bandana_red"]);
  return build({ skin: SKIN[0], hair: "short", hairColor: "#6a3d1e" }, ["plain_shirt", "boots"]);
}

export interface DollInput {
  template: string;
  team: string;
  summon: boolean;
  totem?: boolean;
  weaponId?: string | null;
  weaponClass?: string | null;
}

/** 單位 → 紙娃娃規格；永遠回傳畫得出來的規格（未知範本、武器、kind 都有退回）。 */
export function resolveDoll(input: DollInput): DollSpec {
  if (input.totem === true) return { look: { skin: "#a8a49a" }, gear: {}, totem: true };
  const table = APPEARANCES[input.template];
  const app = table ?? (input.summon ? skeletonLook() : factionDefault(input.team));
  const weapon = weaponLook(input.weaponId, input.weaponClass);
  const main: GearItem = {
    kind: weapon.kind,
    material: weapon.material,
    ...(weapon.element !== undefined ? { element: weapon.element } : {}),
    ...(weapon.form !== undefined ? { form: weapon.form } : {}),
    ...app.mainStyle,
  };
  const gear: Gear = {};
  for (const slot of ["head", "body", "hands", "feet", "cloak", "off_hand"] as const) {
    const item = known(slot, app.gear[slot]);
    if (item !== undefined) gear[slot] = item;
  }
  const mainKnown = known("main_hand", main);
  if (mainKnown !== undefined) gear.main_hand = mainKnown;
  if (weapon.twoHanded) delete gear.off_hand; // 雙手武器副手留空
  return { look: app.look, gear, ...(app.rarity !== undefined ? { rarity: app.rarity } : {}) };
}

/** 穩定的快取鍵（物件鍵排序）：同一套裝備＋朝向＋姿勢共用一張貼圖。 */
export function dollKey(spec: DollSpec, facing: string, downed: boolean): string {
  const stable = (v: unknown): unknown => {
    if (Array.isArray(v)) return v.map(stable);
    if (v !== null && typeof v === "object") {
      return Object.fromEntries(Object.entries(v as Record<string, unknown>).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)).map(([k, x]) => [k, stable(x)]));
    }
    return v;
  };
  return `${facing}|${downed ? "down" : "up"}|${JSON.stringify(stable(spec))}`;
}
