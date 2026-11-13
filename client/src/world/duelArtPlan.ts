// 精英單挑插圖（RG-4，docs/art/RG樣張.md 9.8）的資料：大世界的 WorldView → 要畫什麼（純函式，node 測得到；畫在 `render/duelArt.ts`）。
// - 主角：玩家自己的紙娃娃（`character.hero_look`，沒有時 `field.hero`），武器＝主手。
// - 精英：遭遇陣容裡第一個精英（同 `duelEliteName`）的 `look`（FieldHeroView 格式；異形是 `doll_look.creature`）。
//   人形的武器＝它的主手；異形的武器＝獸爪（`beast_claw`）。
// - 區域：`map.region`；只有雲嶺、荒原有天色，其他區退回雲嶺。
// 鍛疤（forge_scar，base bandit_captain）不另寫特例：剪影從伺服器給的外觀自動產生，所以現在是借荒原隊長的剪影**暫代**，
// 外觀定案後插圖剪影自動跟著換（9.6 決定 4、9.8 第 6 條）。
import type { WorldView } from "../api/types";
import { resolveDoll, type DollInput, type DollSpec, type GearItem } from "../render/appearance";
import { CREATURE_ELITE_K, CREATURE_ELITE_K_DEFAULT, duelRegion, type DuelMain, type DuelRegion } from "../render/duelArt";
import type { GearLook } from "../render/gearResolve";
import { resolveCreature, rigKey, type ResolvedCreature } from "../render/inkCreature";
import { BEAST_CLAW } from "../render/qIcon/beastClaw";
import { weaponIconItem } from "../render/weaponIcon";

type Encounter = NonNullable<WorldView["encounter"]>;
type EnemyLook = NonNullable<Encounter["enemies"][number]["look"]>;
type HeroLook = NonNullable<WorldView["character"]["hero_look"]>;
/** 主角與精英共用的外觀欄位（FieldHeroView）。 */
type FieldLook = Pick<HeroLook, "template_id" | "doll_look" | "weapon_id" | "weapon_class" | "race_look" | "equipment">;

/** 交叉武器的來源：裝備外觀（`resolveGear` 吃的）、武器 id 推出來的那一件，或獸爪。 */
export type DuelWeaponPlan = { kind: "gear"; look: GearLook } | { kind: "item"; item: GearItem } | { kind: typeof BEAST_CLAW };

export type DuelElitePlan = { kind: "doll"; spec: DollSpec } | { kind: "creature"; creature: ResolvedCreature; k: number };

export interface DuelPlan {
  hero: DollSpec;
  heroWeapon: DuelWeaponPlan;
  elite: DuelElitePlan;
  eliteWeapon: DuelWeaponPlan;
  region: DuelRegion;
  /** 快取鍵（同一組外觀、區域畫一次）。 */
  key: string;
}

/** 提出單挑的精英：陣容裡第一個精英；沒有標精英時用第一名敵人（同 `duelEliteName`）。 */
export function duelElite(e: Encounter): Encounter["enemies"][number] | undefined {
  return e.enemies.find((x) => x.elite) ?? e.enemies[0];
}

function dollOf(look: FieldLook, team: "ally" | "enemy"): DollSpec {
  return resolveDoll({
    template: look.template_id,
    dollLook: look.doll_look ?? null,
    team,
    summon: false,
    weaponId: look.weapon_id,
    weaponClass: look.weapon_class,
    raceLook: (look.race_look ?? null) as Readonly<Record<string, unknown>> | null,
    equipment: (look.equipment ?? []).map((x) => ({ slot: x.slot, appearance: x.appearance ?? null })) as DollInput["equipment"],
  });
}

/** 主手武器：有主手裝備的外觀就用它，否則照武器 id／大類（同武器小圖示 `weaponIconItem`）。 */
export function mainWeaponOf(look: FieldLook): DuelWeaponPlan {
  const app = (look.equipment ?? []).find((x) => x.slot === "main_hand")?.appearance;
  if (app?.kind != null) return { kind: "gear", look: app as GearLook };
  return { kind: "item", item: weaponIconItem(look.weapon_id, look.weapon_class) };
}

/** 主手的 kind（＋形制、材質、元素；RG-6：插圖依 kind 分剪影組、交叉組，9.9.5 第 1 條）。獸爪、沒有 kind 時 null。 */
export function mainKindOf(w: DuelWeaponPlan): DuelMain | null {
  if (w.kind === BEAST_CLAW) return null;
  const it = w.kind === "gear" ? w.look : w.item;
  if (it.kind == null) return null;
  return { kind: it.kind, form: it.form ?? null, material: it.material ?? null, element: it.element ?? null };
}

/** 異形精英的插圖倍率（依身形；沒有給的身形用預設）。 */
export const creatureDuelK = (c: ResolvedCreature): number => CREATURE_ELITE_K[rigKey(c)] ?? CREATURE_ELITE_K_DEFAULT;

function eliteOf(look: EnemyLook, rank: string): DuelElitePlan {
  const doll = look.doll_look ?? null;
  if (doll?.creature != null) {
    // 大小查 SIZES（不是戰場的 FIELD_SIZES）＋精英 ×1.15，同樣張 QCreature.resolve
    const creature = resolveCreature({ look: doll.creature, elite: rank === "elite", affixes: doll.affixes ?? undefined, rarity: doll.rarity ?? null });
    return { kind: "creature", creature, k: creatureDuelK(creature) };
  }
  return { kind: "doll", spec: dollOf(look as FieldLook, "enemy") };
}

/** 有單挑邀請、主角與精英都有外觀時回傳要畫的東西；否則 null（不畫插圖）。 */
export function duelPlan(view: WorldView): DuelPlan | null {
  const e = view.encounter;
  if (e == null) return null;
  const elite = duelElite(e);
  const heroLook = (view.character?.hero_look ?? view.field?.hero ?? null) as FieldLook | null;
  if (elite?.look == null || heroLook === null) return null;
  const el = eliteOf(elite.look, elite.rank ?? "elite");
  const region = duelRegion(view.map?.region);
  return {
    hero: dollOf(heroLook, "ally"),
    heroWeapon: mainWeaponOf(heroLook),
    elite: el,
    eliteWeapon: el.kind === "creature" ? { kind: BEAST_CLAW } : mainWeaponOf(elite.look as FieldLook),
    region,
    key: JSON.stringify([heroLook, elite.look, elite.rank ?? null, region]),
  };
}
