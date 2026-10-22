// 紙娃娃的外觀解析（Phase 3-16b；3E-2e 起外觀資料來自後端，前端不再寫死 ID 對照表）。
// 外觀只由資料欄位決定：主手 ← 武器外觀（`/api/glossary` 的 `weapon_looks`，內容檔 `weapons.yaml` 的 `look`）；
// 頭、身、手、腳、披風、副手、膚色、髮型 ← 單位視圖的 `doll_look`（內容檔單位範本的 `doll`）。
// 新內容沒有外觀資料時一律有預設，不得出錯：依陣營預設、召喚物用骷髏、武器依大類、不認得的 kind 只跳過該欄位。
// 純資料與純函式（不碰 Canvas），可以用 vitest 檢查。
import type { DollLook } from "../api/types";
import { weaponLookEntry } from "../battle/glossary";
import { ELEMENT_VFX } from "../battle/vfxPalette";
import { numToHex } from "./artPalette";
import { dollGear, isTwoHandedPart, type DollEquipment } from "./dollGear";

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
  head: ["hood", "helmet", "horned_helm", "wizard_hat", "bandana", "crown", "wide_hat", "cap", "greathelm"],
  body: ["shirt", "leather", "mail", "plate", "robe", "ribs", "coat"],
  hands: ["gloves", "gauntlets", "bracers"],
  feet: ["boots", "greaves", "shoes", "iron_boots"],
  cloak: ["cape"],
  main_hand: ["sword", "greatsword", "dagger", "axe", "hammer", "spear", "bow", "crossbow", "longgun", "staff", "pistol", "shotgun", "fist", "scythe", "whip"],
  off_hand: ["shield_round", "shield_kite", "tome", "orb"],
};

/** 材質 → [主色, 暗色]；不認得的材質用布料色。 */
export const MATERIAL: Readonly<Record<string, readonly [string, string]>> = {
  cloth: ["#8a8f99", "#5d6168"],
  leather: ["#8a5a32", "#5e3b1f"],
  iron: ["#7a828b", "#474c52"],
  steel: ["#a9b6c6", "#6d7a8a"],
  gold: ["#e8bb48", "#9c7420"],
  wood: ["#a06a36", "#6a4420"],
  bone: ["#e9e3cf", "#a8a08a"],
  // Phase 3G-G5b：裝備外觀新增的材質（色票同 artPalette 的 GEAR_MATERIAL）；原有 7 種不動，舊單位畫面不變
  copper: ["#b06a3c", "#6e3e20"],
  silver: ["#e8edf2", "#a8b0ba"],
  crystal: ["#b8a8ff", "#7a68c8"],
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

// ---- 武器外觀（後端 `weapons.yaml` 的 `look`，經 glossary 載入；沒有時依武器大類退回）----

interface WeaponLook {
  kind: string;
  material: string;
  element?: string;
  form?: string;
  twoHanded: boolean;
}

/** 武器大類 → 主手 kind（`weapon_id` 不認得時的退回）。 */
export const WEAPON_CLASS_KIND: Readonly<Record<string, string>> = { melee: "sword", ranged: "bow", focus: "staff" };

const MATERIAL_OF_KIND: Readonly<Record<string, string>> = { sword: "steel", bow: "wood", staff: "wood" };

/** 主手外觀：依 `weapon_id`（glossary 的武器外觀）；未知依 `weapon_class`；都沒有畫劍。 */
export function weaponLook(weaponId: string | null | undefined, weaponClass?: string | null): WeaponLook {
  const entry = weaponId === null || weaponId === undefined ? undefined : weaponLookEntry(weaponId);
  if (entry !== undefined) {
    const { kind, material, element, form } = entry.look;
    return { kind, material, ...(element != null ? { element } : {}), ...(form != null ? { form } : {}), twoHanded: entry.two_handed };
  }
  const kind = (weaponClass !== null && weaponClass !== undefined ? WEAPON_CLASS_KIND[weaponClass] : undefined) ?? "sword";
  return { kind, material: MATERIAL_OF_KIND[kind] ?? "steel", twoHanded: false };
}

// ---- 單位外觀（後端 `doll_look`；沒有時依陣營／召喚物退回）----

export const SKIN = ["#f1c9a5", "#d9a47a", "#a8724c", "#7a4e32"] as const;

export interface Appearance extends DollSpec {
  /** 主手的材質／顏色覆寫（例如生鏽的劍）；主手的種類仍由武器外觀決定。 */
  mainStyle?: Partial<GearItem>;
}

const GEAR_SLOTS: readonly GearSlot[] = ["head", "body", "hands", "feet", "cloak", "off_hand"];

/** 後端的單位外觀 → 內部外觀；欄位值是可選的（`null` 與缺漏同義）。 */
function fromDollLook(d: DollLook): Appearance {
  const look: Look = { skin: d.skin };
  if (d.hair != null) look.hair = d.hair;
  if (d.hair_color != null) look.hairColor = d.hair_color;
  if (d.pants != null) look.pants = d.pants;
  if (d.trim != null) look.trim = d.trim;
  if (d.eyes != null) look.eyes = d.eyes;
  if (d.skull) look.skull = true;
  const gear: Gear = {};
  for (const slot of GEAR_SLOTS) {
    const g = d.gear?.[slot];
    if (g !== undefined) gear[slot] = { kind: g.kind, material: g.material, ...(g.color != null ? { color: g.color } : {}) };
  }
  const mainStyle: Partial<GearItem> = {};
  if (d.main_material != null) mainStyle.material = d.main_material;
  if (d.main_color != null) mainStyle.color = d.main_color;
  return { look, gear, ...(d.rarity != null ? { rarity: d.rarity } : {}), ...(Object.keys(mainStyle).length > 0 ? { mainStyle } : {}) };
}

/** 骷髏身形：召喚物沒有外觀資料時用（生鏽的主手同範例骷髏戰士）。 */
function skeletonLook(): Appearance {
  return {
    look: { skin: "#e9e3cf", skull: true, pants: "#d9d2bd", eyes: "#2a1030" },
    gear: { body: { kind: "ribs", material: "bone" } },
    mainStyle: { material: "iron", color: "#9a8a76" },
  };
}

/** 陣營預設：我方 ＝ 布衣＋靴；敵方 ＝ 皮甲＋頭巾＋靴。 */
function factionDefault(team: string): Appearance {
  if (team === "enemy") {
    return {
      look: { skin: SKIN[2], hair: "short", hairColor: "#2a1c14" },
      gear: { body: { kind: "leather", material: "leather" }, feet: { kind: "boots", material: "leather" }, head: { kind: "bandana", material: "cloth", color: "#b33a3a" } },
    };
  }
  return {
    look: { skin: SKIN[0], hair: "short", hairColor: "#6a3d1e" },
    gear: { body: { kind: "shirt", material: "cloth" }, feet: { kind: "boots", material: "leather" } },
  };
}

export interface DollInput {
  /** 範本 ID（快取鍵與除錯用；外觀來自 `dollLook`）。 */
  template: string;
  /** 單位視圖的紙娃娃外觀（`UnitView.doll_look`）；沒有時依陣營或召喚物退回預設。 */
  dollLook?: DollLook | null | undefined;
  team: string;
  summon: boolean;
  totem?: boolean;
  weaponId?: string | null;
  weaponClass?: string | null;
  /** 身上穿的裝備（`UnitView.equipment`，Phase 3G-G5b）：有穿的欄位依外觀欄位畫，沒穿的沿用範本外觀。 */
  equipment?: readonly DollEquipment[] | undefined;
}

/** 單位 → 紙娃娃規格；永遠回傳畫得出來的規格（未知範本、武器、kind 都有退回）。 */
export function resolveDoll(input: DollInput): DollSpec {
  if (input.totem === true) return { look: { skin: "#a8a49a" }, gear: {}, totem: true };
  const app = input.dollLook != null ? fromDollLook(input.dollLook) : input.summon ? skeletonLook() : factionDefault(input.team);
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
  let twoHanded = weapon.twoHanded;
  const rarity = app.rarity; // 外光只來自範本（頭目記號）；裝備稀有度不影響小人
  if (input.equipment !== undefined && input.equipment.length > 0) {
    const worn = dollGear(input.equipment);
    for (const slot of ["head", "body", "hands", "feet", "main_hand", "off_hand"] as const) {
      const item = known(slot, worn.gear[slot]);
      if (item !== undefined) gear[slot] = item;
    }
    if (worn.paired && gear.main_hand !== undefined) gear.off_hand = { ...gear.main_hand }; // 成對武器：副手格是第二把武器
    // 雙手武器：優先看武器資料（外觀表），沒有對照的新武器才依造型判斷
    if (worn.gear.main_hand !== undefined) twoHanded = weaponLookEntry(input.weaponId ?? "")?.two_handed ?? isTwoHandedPart(worn.gear.main_hand);
    if (worn.paired) twoHanded = false; // 成對武器：副手格已經是第二把武器
  }
  if (twoHanded) delete gear.off_hand; // 雙手武器副手留空
  return { look: app.look, gear, ...(rarity !== undefined ? { rarity } : {}) };
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
