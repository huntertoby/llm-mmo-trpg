// 原型美術對照表（Phase 3-13）：地形 / 物件種類 / 單位範本 → Kenney CC0 素材圖（見 docs/phases/Phase3-13報告.md）。
// 純資料與純函式；沒有對照（或圖檔載入失敗）時回傳 `null`，繪圖端退回原本的色塊，不得出錯。
// 新內容沒有對照時：地形與物件用色塊，單位用陣營預設圖。

export type SpritePack = "tiny-dungeon" | "tiny-town";

export interface SpriteRef {
  pack: SpritePack;
  /** 檔名中的圖塊編號（`tile_NNNN.png`）。 */
  tile: string;
  /** 乘上的顏色（0xffffff ＝ 不變）；用來把同一張圖變成冰、土等變體。 */
  tint?: number;
}

const dungeon = (tile: string, tint?: number): SpriteRef => ({ pack: "tiny-dungeon", tile, ...(tint === undefined ? {} : { tint }) });
const town = (tile: string, tint?: number): SpriteRef => ({ pack: "tiny-town", tile, ...(tint === undefined ? {} : { tint }) });

/** 地形圖塊。 */
export const TERRAIN_SPRITES: Readonly<Record<string, SpriteRef>> = {
  stone: town("0109"),
  grass: town("0000"),
  dirt: town("0025"),
  wall: dungeon("0058"),
  // 素材包沒有岩漿、深淵、冰窟：用石地圖塊乘上顏色，保留紋理又一眼分得出來
  lava: town("0109", 0xff6a2a),
  chasm: town("0109", 0x2a2a3c),
  ice_hole: town("0109", 0x3a6aa8),
};

/** 物件圖（畫在地形圖塊之上，背景透明）。 */
export const OBJECT_SPRITES: Readonly<Record<string, SpriteRef>> = {
  wooden_bridge: dungeon("0080"),
  oil_barrel: town("0130"),
  thin_ice: town("0109", 0xaad8f0),
  stone_pillar: dungeon("0018"),
  grass: town("0006"),
  crate: dungeon("0089"),
  earth_wall: dungeon("0057", 0xc8a070),
  low_wall: dungeon("0077"),
  fallen_log: town("0106"),
  dead_tree: town("0003"),
  rubble: dungeon("0042"),
  ice_wall: dungeon("0067", 0x9fe0ff),
  thorn_wall: town("0007"),
};

/** 單位範本 → 圖（依武器／職業／階級挑選；召喚物與木樁各有圖）。 */
export const UNIT_SPRITES: Readonly<Record<string, SpriteRef>> = {
  hero_fighter: dungeon("0096"),
  hero_mage: dungeon("0084"),
  hero_archer: dungeon("0099"),
  hero_stormcaller: dungeon("0111"),
  bandit: dungeon("0085"),
  bandit_archer: dungeon("0112"),
  bandit_shieldbearer: dungeon("0097"),
  bandit_warlord: dungeon("0087"),
  bandit_boss: dungeon("0110"),
  std_enemy_t1: dungeon("0120"),
  std_enemy_t2: dungeon("0122"),
  std_enemy_t3: dungeon("0123"),
  std_enemy_t4: dungeon("0108"),
  std_enemy_t5: dungeon("0124"),
  sim_companion_archer: dungeon("0112"),
  sim_companion_fighter: dungeon("0096"),
  sim_duelist: dungeon("0100"),
  training_dummy: town("0095"),
  summon_afterimage: dungeon("0121"),
  summon_elemental_spirit: dungeon("0107"),
  summon_skeleton_warrior: dungeon("0098"),
  summon_war_totem: dungeon("0066"),
};

const DEFAULT_UNIT: Readonly<Record<"ally" | "enemy", SpriteRef>> = {
  ally: dungeon("0086"),
  enemy: dungeon("0121"),
};

export function terrainSprite(terrain: string): SpriteRef | null {
  return TERRAIN_SPRITES[terrain] ?? null;
}

export function objectSprite(kind: string): SpriteRef | null {
  return OBJECT_SPRITES[kind] ?? null;
}

/** 單位圖：範本沒有對照時用陣營預設圖（永遠有圖）。 */
export function unitSprite(templateId: string, team: "ally" | "enemy"): SpriteRef {
  return UNIT_SPRITES[templateId] ?? DEFAULT_UNIT[team];
}

export function spriteKey(ref: SpriteRef): string {
  return `${ref.pack}/tile_${ref.tile}`;
}

export function spriteUrl(ref: SpriteRef): string {
  return `/assets/kenney/${ref.pack}/tile_${ref.tile}.png`;
}

/** 所有用到的圖（去重、排序），供預先載入與測試檢查檔案存在。 */
export function allSpriteRefs(): SpriteRef[] {
  const map = new Map<string, SpriteRef>();
  const add = (r: SpriteRef) => map.set(spriteKey(r), r);
  for (const r of Object.values(TERRAIN_SPRITES)) add(r);
  for (const r of Object.values(OBJECT_SPRITES)) add(r);
  for (const r of Object.values(UNIT_SPRITES)) add(r);
  for (const r of Object.values(DEFAULT_UNIT)) add(r);
  return [...map.values()].sort((a, b) => (spriteKey(a) < spriteKey(b) ? -1 : 1));
}

/** 已載入的貼圖庫：鍵為 `spriteKey`。載入失敗的圖不在表內，查詢回傳 `undefined`。 */
export class SpriteBook<T> {
  private readonly textures = new Map<string, T>();
  set(ref: SpriteRef, texture: T): void {
    this.textures.set(spriteKey(ref), texture);
  }
  get(ref: SpriteRef | null): T | undefined {
    return ref === null ? undefined : this.textures.get(spriteKey(ref));
  }
}
