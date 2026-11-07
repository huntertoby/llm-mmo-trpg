// Q 版樣張的資料（QK-1：dev 畫廊 `dev/doll-gallery.html?skin=q` 與自測用；正式畫面不用）。
// 照 docs/art/sample/paperdoll.js（材質色、ITEMS、TEMPLATES）、anim.js（unit、REST、出招片段命中格）、idleWeapons.js（武器待機），
// 讓畫廊能出和 docs/art/closeup/ 同一組格子、同一套顏色的 3 倍特寫，逐格對照。
import type { QHooks, QItem, QLook, QPose, QUnit } from "./qCore";
import { WEAPON_IDLE, WEAPON_IDLE_KINDS, weaponIdlePose } from "./idleWeapons";

const MATERIAL: Readonly<Record<string, readonly [string, string]>> = {
  cloth: ["#8a8f99", "#5d6168"],
  leather: ["#8a5a32", "#5e3b1f"],
  iron: ["#8d969f", "#5a6169"],
  steel: ["#c3ccd6", "#7d8794"],
  gold: ["#e8bb48", "#9c7420"],
  wood: ["#a06a36", "#6a4420"],
  bone: ["#e9e3cf", "#a8a08a"],
};
const ELEMENT_TINT: Readonly<Record<string, string>> = { fire: "#ff6a1a", water: "#4aa8ff", ice: "#8fe3ff", lightning: "#fff36b", poison: "#7ddc3a", wind: "#7fe0c0", earth: "#b0814a", holy: "#ffd75e", shadow: "#9a6ad8" };
function pdMix(a: string, b: string, t: number): string {
  const pa = parseInt(a.slice(1), 16);
  const pb = parseInt(b.slice(1), 16);
  const ch = (p: number, s: number): number => (p >> s) & 255;
  const m = (s: number): number => Math.round(ch(pa, s) * (1 - t) + ch(pb, s) * t);
  return `#${((m(16) << 16) | (m(8) << 8) | m(0)).toString(16).padStart(6, "0")}`;
}
/** 樣張的顏色（paperdoll.js 的 itemColors）。 */
export const SAMPLE_HOOKS: QHooks = {
  colors: (item) => {
    let [main, dark] = item.color ? [item.color, pdMix(item.color, "#000000", 1 - 0.68)] : (MATERIAL[item.material ?? ""] ?? MATERIAL["cloth"]!);
    const t = item.element ? ELEMENT_TINT[item.element] : undefined;
    if (t) {
      main = pdMix(main, t, 0.45);
      dark = pdMix(dark, t, 0.3);
    }
    return [main, dark];
  },
  tint: (e) => (e ? ELEMENT_TINT[e] : undefined),
};

const I = (slot: string, kind: string, material: string, extra: Partial<QItem> = {}): QItem => ({ slot, kind, material, ...extra });
export const SAMPLE_ITEMS = {
  plate_armor: I("body", "plate", "steel"),
  mage_robe: I("body", "robe", "cloth", { color: "#5a3fa0" }),
  green_leather: I("body", "leather", "leather", { color: "#4f7a3a" }),
  leather_vest: I("body", "leather", "leather"),
  chain_mail: I("body", "mail", "iron"),
  boots: I("feet", "boots", "leather"),
  greaves: I("feet", "greaves", "steel"),
  gloves: I("hands", "gloves", "leather"),
  gauntlets: I("hands", "gauntlets", "steel"),
  hood_green: I("head", "hood", "cloth", { color: "#3f6a32" }),
  iron_helmet: I("head", "helmet", "iron"),
  horned_helm: I("head", "horned_helm", "iron"),
  wizard_hat: I("head", "wizard_hat", "cloth", { color: "#5a3fa0" }),
  bandana_red: I("head", "bandana", "cloth", { color: "#b33a3a" }),
  sword: I("main_hand", "sword", "steel"),
  rusty_sword: I("main_hand", "sword", "iron", { color: "#9a8a76" }),
  greatsword: I("main_hand", "greatsword", "steel"),
  dagger: I("main_hand", "dagger", "iron"),
  bow: I("main_hand", "bow", "wood"),
  fire_staff: I("main_hand", "staff", "wood", { element: "fire" }),
  round_shield: I("off_hand", "shield_round", "wood", { color: "#2f5fae" }),
  kite_shield: I("off_hand", "shield_kite", "wood", { color: "#8a5a32" }),
  holy_shield: I("off_hand", "shield_kite", "steel", { element: "holy" }),
  tome: I("off_hand", "tome", "leather", { color: "#7a2a3a" }),
  red_cape: I("cloak", "cape", "cloth", { color: "#a32a2a" }),
  blue_cape: I("cloak", "cape", "cloth", { color: "#2c4f8a" }),
} as const;
type ItemId = keyof typeof SAMPLE_ITEMS;
function build(look: QLook, ids: ItemId[]): QUnit {
  const gear: QUnit["gear"] = {};
  for (const id of ids) {
    const it = SAMPLE_ITEMS[id];
    gear[it.slot as keyof QUnit["gear"]] = it;
  }
  return { look, gear };
}
const SKIN = ["#f1c9a5", "#d9a47a", "#a8724c", "#7a4e32"] as const;
export const SAMPLE_TEMPLATES = {
  hero_fighter: build({ skin: SKIN[0], hair: "short", hairColor: "#6a3d1e" }, ["plate_armor", "greaves", "gauntlets", "sword", "round_shield", "blue_cape"]),
  hero_mage: build({ skin: SKIN[1], hair: "long", hairColor: "#c8c0b0", trim: "#e8bb48" }, ["mage_robe", "boots", "wizard_hat", "fire_staff", "tome"]),
  hero_archer: build({ skin: SKIN[0], hair: "long", hairColor: "#c27a2c", pants: "#3a3a2a" }, ["green_leather", "boots", "gloves", "hood_green", "bow"]),
  bandit: build({ skin: SKIN[2], hair: "short", hairColor: "#2a1c14" }, ["leather_vest", "boots", "bandana_red", "dagger"]),
  bandit_shieldbearer: build({ skin: SKIN[3], hair: "short", hairColor: "#1c1410" }, ["chain_mail", "boots", "iron_helmet", "rusty_sword", "kite_shield"]),
  bandit_boss: build({ skin: SKIN[2], hair: "short", hairColor: "#1c1410" }, ["chain_mail", "greaves", "gauntlets", "horned_helm", "greatsword", "red_cape"]),
} as const;

/** anim.js 的 unit(kind)：襯衫、皮靴、主手一件武器。 */
export const sampleUnit = (kind: string): QUnit => ({ look: { skin: "#f1c9a5", hair: "short", hairColor: "#3a2414" }, gear: { body: { kind: "shirt", color: "#2f5a5a" }, feet: { kind: "boots", material: "leather" }, main_hand: { kind } } });

/** anim.js 的 13 種武器（自測照這個順序）。 */
export const SAMPLE_WEAPONS = ["sword", "saber", "arcane_blade", "paired", "spear", "scythe", "whip", "gauntlet", "staff", "orb", "bow", "crossbow", "gun"] as const;
export const SAMPLE_WEAPON_ZH: Readonly<Record<string, string>> = { sword: "劍", saber: "刀", spear: "槍（長兵）", bow: "弓", crossbow: "弩", gun: "火槍", staff: "法杖", orb: "法球", gauntlet: "拳套", whip: "鞭", scythe: "鐮", paired: "成對武器", arcane_blade: "魔導劍", greatsword: "雙手劍" };

/** 出招片段的命中格（anim.js：揮砍 slash(1)、突刺 thrust(1)、射擊 release(1)、施法 cast(1)）。 */
const SLASH: QPose = { arm: 0.15, wpn: 1.85, lean: 0.18, hipN: 0.45, hipF: -0.3 };
const THRUST: QPose = { arm: -1.0, wpn: 2.57, lean: 0.2, hipN: 0.5, hipF: -0.35 };
const RELEASE: QPose = { arm: -1.3, wpn: 2.87, lean: 0 };
const CAST: QPose = { arm: -1.2, wpn: 2.4, lean: 0.12 };
const ATTACK_HIT: Readonly<Record<string, QPose>> = { spear: THRUST, gauntlet: THRUST, bow: RELEASE, crossbow: RELEASE, gun: RELEASE, staff: CAST, orb: CAST };
export const sampleHitPose = (kind: string): QPose => ({ ...(ATTACK_HIT[kind] ?? SLASH) });

// ---------- idleWeapons.js 的武器待機（closeups i 列用；QK-7 起表在 idleWeapons.ts）----------
export const SAMPLE_IDLE: Readonly<Record<string, { mid?: number; pose: (u: number) => QPose }>> = Object.fromEntries(
  WEAPON_IDLE_KINDS.map((k) => [k, { ...(WEAPON_IDLE[k].mid !== undefined ? { mid: WEAPON_IDLE[k].mid } : {}), pose: (u: number) => weaponIdlePose(k, u) }]),
);
