// NPC 的外觀（Phase 6C-7；`docs/art/NPC頭像.md` 第 4 節第 5 項）：地圖上的紙娃娃直接用頭像的 `portrait.look`、`portrait.gear`，
// 地圖上和對話框裡才會是同一個人；不另開外觀欄位。只畫在頭像上的配件（`extras`）照表換成頭部裝備或不畫；
// `gear.head` 已經有值的以它為準。白狐霜音（`fox`）不用紙娃娃，用異形「犬」的骨架、白色。純函式，可用 vitest 檢查。
import type { DollLook, FieldFigure, FieldView, NpcPortrait } from "../api/types";

type FieldLook = NonNullable<FieldView["hero"]>;
type DollGearOut = NonNullable<DollLook["gear"]>[string];

/**
 * 頭像配件 → 地圖紙娃娃的頭部裝備（表上「不畫」的配件不在這裡）。QK-8（照 qNpc.js 的 prep）：斗笠 wide_hat 畫成草編斗笠 douli、
 * 頭帶 headband、護目鏡 goggles、額上護目鏡 goggles_up 都是 Q 版的頭部部件；沒戴帽時才換（已經有頭部裝備時見 `HEAD_FORM`）。
 */
export const EXTRA_HEAD: Readonly<Record<string, DollGearOut>> = {
  cap: { kind: "cap", material: "leather", color: "#3a2a1a" }, // QK-8：同樣張 qNpc.prep（深色皮帽）
  wide_hat: { kind: "douli", material: "cloth" },
  bandana: { kind: "bandana", material: "cloth", color: "#a83a2a" },
  headband: { kind: "headband", material: "cloth" },
  goggles: { kind: "goggles", material: "iron" },
  goggles_up: { kind: "goggles_up", material: "iron" },
};
/** 已經戴帽時，護目鏡改成帽子的 `form`（qNpc 照樣戴在眼睛上；額上護目鏡架在帽沿上）。 */
export const HEAD_FORM: ReadonlySet<string> = new Set(["goggles", "goggles_up"]);

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
      ...((g as { element?: string | null }).element != null ? { element: (g as { element?: string }).element } : {}),
    };
  }
  if (mapExtras) {
    // 照配件順序（樣張 qNpc.prep）：沒戴帽時換成頭部部件；已經戴帽時護目鏡改成帽子的形制；毛領是頸飾
    for (const e of p.extras ?? []) {
      const head = out["head"];
      if (head === undefined && EXTRA_HEAD[e] !== undefined) out["head"] = { ...EXTRA_HEAD[e] };
      else if (head !== undefined && HEAD_FORM.has(e) && (head as { form?: string | null }).form == null) out["head"] = { ...head, form: e };
      else if (e === "fur_collar" && out["neck"] === undefined) out["neck"] = { kind: "fur_collar", material: "fur" };
    }
  }
  return out;
}

/** 頭像 → 紙娃娃的 `doll_look`（白狐是異形犬）。 */
export function portraitDollLook(p: NpcPortrait, mapExtras: boolean): DollLook {
  if (isFox(p)) {
    return { skin: FOX_WHITE, skull: false, beard: false, affixes: [], traits: [], creature: { body: "hound", material: "fur", tint: FOX_WHITE, traits: [] } } as unknown as DollLook;
  }
  const l = p.look;
  const gear = portraitGear(p, mapExtras);
  // QK-8：頭像的手持物（main_hand）→ 紙娃娃主手的造型覆寫（同 figure.held）；主手不在紙娃娃的外觀格裡
  const main = gear["main_hand"];
  delete gear["main_hand"];
  const held = main === undefined ? {} : { main_kind: main.kind, main_material: main.material, ...(main.color != null ? { main_color: main.color } : {}), ...((main as { element?: string }).element != null ? { main_element: (main as { element?: string }).element } : {}) };
  return {
    skin: l?.skin ?? "#f1c9a5",
    skull: false,
    beard: l?.beard === true,
    affixes: [],
    // QK-8：霧鎖真人的霧氣（頭像配件 mist）在地圖全身上照頭目一樣繞身
    traits: mapExtras && (p.extras ?? []).includes("mist") ? ["mist"] : [],
    gear,
    ...held,
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

/**
 * 地圖上的 NPC 外觀：伺服器有 `look` 就用；沒有時照頭像換算；都沒有為 `null`（用預設外觀）。
 * 6V-3（美術 PM 6V-1 檢查待決 3）：照頭像換算的 NPC 武器欄是空的 → 空手。和情境物件上的人一樣把主手設成
 * `FIGURE_EMPTY_HAND`（紙娃娃不認得的造型＝不畫主手），不讓空手的武器 id 退回近戰預設的劍。只改資料，不改紙娃娃畫法。
 */
export function npcFieldLook(n: { id: string; look?: FieldLook | null; portrait?: NpcPortrait | null }): FieldLook | null {
  if (n.look != null) return n.look;
  const p = n.portrait;
  if (p == null) return null;
  const doll = portraitDollLook(p, true);
  const emptyHand = isFox(p) || (p.gear ?? {})["main_hand"] != null ? {} : { main_kind: FIGURE_EMPTY_HAND };
  return {
    template_id: `npc_${n.id}`,
    doll_look: { ...doll, ...emptyHand } as DollLook,
    weapon_id: "unarmed",
    weapon_class: "melee",
    race_look: portraitRaceLook(p) as FieldLook["race_look"],
    equipment: [],
  };
}

/** 站在情境物件上的人在渲染器裡的單位 ID（6V-1；和 NPC 的 `npc_` 分開，免得同名撞在一起）。 */
export const figureUnitId = (id: string): string => `figure_${id}`;
/** 站在設施格上的人的單位 ID（6V-3：主城的殿主、酒館老闆、鐵匠、附魔師、傭兵管事）。 */
export const facilityFigureId = (kind: string): string => figureUnitId(`facility_${kind}`);

/**
 * 站在情境物件上的人（Phase 6V-1）：主城功能型 NPC（守印人、守池人、工坊師傅、書記）的地圖紙娃娃。
 * 外觀照 `figure.portrait` 換算（同 NPC 的 6C-7 規則）；`figure.held` 是主手拿的東西（晶杖、錘子），
 * 用紙娃娃的 `main_kind`／`main_material` 覆寫主手（同 5A-ART3 的拂塵、符紙）。沒拿東西＝主手空著
 * （`FIGURE_EMPTY_HAND` 不是認得的造型，紙娃娃不畫主手；不然空手的武器 id 會退回成一把劍）。
 */
export const FIGURE_EMPTY_HAND = "none";

export function figureFieldLook(id: string, figure: FieldFigure): FieldLook {
  const held = figure.held;
  const doll = portraitDollLook(figure.portrait, true) as DollLook & { main_kind?: string; main_material?: string; main_color?: string };
  return {
    template_id: figureUnitId(id),
    doll_look: {
      ...doll,
      main_kind: held?.kind ?? FIGURE_EMPTY_HAND,
      ...(held?.material != null ? { main_material: held.material } : {}),
      ...(held?.color != null ? { main_color: held.color } : {}),
    } as DollLook,
    weapon_id: "unarmed",
    weapon_class: "melee",
    race_look: portraitRaceLook(figure.portrait) as FieldLook["race_look"],
    equipment: [],
  };
}
