// NPC 的外觀（Phase 6C-7；`docs/art/NPC頭像.md` 第 4 節第 5 項）：地圖上的紙娃娃直接用頭像的 `portrait.look`、`portrait.gear`，
// 地圖上和對話框裡才會是同一個人；不另開外觀欄位。只畫在頭像上的配件（`extras`）照表換成頭部裝備或不畫；
// `gear.head` 已經有值的以它為準。白狐霜音（`fox`）不用紙娃娃，用異形「犬」的骨架、白色。純函式，可用 vitest 檢查。
import type { DollLook, FieldView, NpcPortrait } from "../api/types";

type FieldLook = NonNullable<FieldView["hero"]>;
type DollGearOut = NonNullable<DollLook["gear"]>[string];

/** 頭像配件 → 地圖紙娃娃的頭部裝備（表上「不畫」的配件不在這裡）。 */
export const EXTRA_HEAD: Readonly<Record<string, DollGearOut>> = {
  cap: { kind: "cap", material: "leather" },
  wide_hat: { kind: "wide_hat", material: "leather" },
  bandana: { kind: "bandana", material: "cloth", color: "#a83a2a" },
  // 紙娃娃沒有頭帶，用頭巾代替
  headband: { kind: "bandana", material: "cloth", color: "#b8432f" },
};

/** 白狐的白色。 */
export const FOX_WHITE = "#f4f0e8";

/** `gear` 沒寫材質時的預設（顏色有寫時只影響暗面）。 */
const MATERIAL_OF: Readonly<Record<string, string>> = {
  leather: "leather",
  plate: "steel",
  mail: "steel",
  helmet: "steel",
  greathelm: "steel",
  cap: "leather",
  wide_hat: "leather",
};

export const isFox = (p: NpcPortrait | null | undefined): boolean => (p?.extras ?? []).includes("fox");

/** 頭像的 `gear` → 紙娃娃的 `gear`（補材質）。`mapExtras`：地圖上把配件換成頭部裝備（頭像自己畫配件時不換）。 */
export function portraitGear(p: NpcPortrait, mapExtras: boolean): Record<string, DollGearOut> {
  const out: Record<string, DollGearOut> = {};
  for (const [slot, g] of Object.entries(p.gear ?? {})) {
    out[slot] = {
      kind: g.kind,
      material: g.material ?? MATERIAL_OF[g.kind] ?? "cloth",
      ...(g.color != null ? { color: g.color } : {}),
      ...(g.trim != null ? { trim: g.trim } : {}),
    };
  }
  if (mapExtras && out["head"] === undefined) {
    const extra = (p.extras ?? []).find((e) => EXTRA_HEAD[e] !== undefined);
    if (extra !== undefined) out["head"] = { ...EXTRA_HEAD[extra]! };
  }
  return out;
}

/** 頭像 → 紙娃娃的 `doll_look`（白狐是異形犬）。 */
export function portraitDollLook(p: NpcPortrait, mapExtras: boolean): DollLook {
  if (isFox(p)) {
    return { skin: FOX_WHITE, skull: false, beard: false, affixes: [], traits: [], creature: { body: "hound", material: "fur", tint: FOX_WHITE, traits: [] } } as unknown as DollLook;
  }
  const l = p.look;
  return {
    skin: l?.skin ?? "#f1c9a5",
    skull: false,
    beard: l?.beard === true,
    affixes: [],
    traits: [],
    gear: portraitGear(p, mapExtras),
    ...(l?.hair != null ? { hair: l.hair } : {}),
    ...(l?.hair_color != null ? { hair_color: l.hair_color } : {}),
    ...(l?.bun_band != null ? { bun_band: l.bun_band } : {}),
    ...(l?.build != null ? { build: l.build } : {}),
  } as unknown as DollLook;
}

/** 種族部件（耳、角、臉部紋路）：紙娃娃本來就支援，照搬；沒有為 `null`。 */
export function portraitRaceLook(p: NpcPortrait): Record<string, unknown> | null {
  const l = p.look;
  if (l == null || isFox(p)) return null;
  const out: Record<string, unknown> = {};
  if (l.ears != null) out["ears"] = l.ears;
  if (l.horns != null) out["horns"] = l.horns;
  if (l.horn_color != null) out["horn_color"] = l.horn_color;
  if (l.pattern != null) out["pattern"] = l.pattern;
  if (l.mark_color != null) out["mark_color"] = l.mark_color;
  if (l.tusks === true) out["tusks"] = true; // RT-4：獸人獠牙（鏽牙）
  return Object.keys(out).length === 0 ? null : out;
}

/** 地圖上的 NPC 外觀：伺服器有 `look` 就用；沒有時照頭像換算；都沒有為 `null`（用預設外觀）。 */
export function npcFieldLook(n: { id: string; look?: FieldLook | null; portrait?: NpcPortrait | null }): FieldLook | null {
  if (n.look != null) return n.look;
  const p = n.portrait;
  if (p == null) return null;
  return {
    template_id: `npc_${n.id}`,
    doll_look: portraitDollLook(p, true),
    weapon_id: "unarmed",
    weapon_class: "melee",
    race_look: portraitRaceLook(p) as FieldLook["race_look"],
    equipment: [],
  };
}
