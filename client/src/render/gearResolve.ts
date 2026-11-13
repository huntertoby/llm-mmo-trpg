// 裝備外觀的驗證＋補預設（QI-4b 從 `gearIcon.ts` 原樣搬出；`gearIcon.ts` re-export，舊的 import 照用）。
// 為什麼獨立一檔：`qIcon/skills.ts` 要 `resolveGear`，而 `gearIcon.ts` 從 QI-4b 起 import `qIcon/keywords.ts`（→ `skills.ts`），
// 留在 `gearIcon.ts` 會成執行期 import 環（`test/importCycles.test.ts` 會擋）。本檔不 import 任何 Q 版圖樣。
// 純函式：不認得的值一律退回預設、不丟例外；清單來自 content/equipment/appearance.yaml（匯出成 gearAppearance.json）。
import appearance from "./gearAppearance.json";
import { GEAR_DYE, GEAR_RARITY } from "./artPalette";
import { KEYWORD_COLOR, STACK_KEYWORDS } from "./palette";

/** 已驗證的外觀（`resolveGear` 的結果）。 */
export interface Resolved {
  kind: string;
  form: string;
  material: string;
  dye: string | null;
  keywords: string[];
  rarity: string;
  style: string;
}
/** 輸入的外觀欄位（來自 API 的 `appearance`；任何欄位都可以缺或不認得）。 */
export interface GearLook {
  kind?: string | null;
  form?: string | null;
  material?: string | null;
  dye?: string | null;
  style?: string | null;
  rarity?: string | null;
  keywords?: readonly string[] | null;
  /** 武器的元素（`weapons.yaml` 的 `look.element`）：火焰、冰霜、雷電、水會換成對應的元素關鍵字（混色）。 */
  element?: string | null;
}

interface KindEntry {
  id: string;
  slotType: string;
  zh: string;
  paired: boolean;
  forms: Array<{ id: string; zh: string; materials?: string[]; defaultMaterial?: string; offhands?: string[] }>;
  materials: string[];
  defaultMaterial: string;
}
const KINDS: Readonly<Record<string, KindEntry>> = Object.fromEntries((appearance.kinds as unknown as KindEntry[]).map((k) => [k.id, k]));
const FALLBACK_KIND = "sword";
const MAX_KEYWORDS = appearance.maxKeywords;

/** 沒有 `kind` 時，依欄位退回的造型（欄位名同裝備欄位）。 */
const SLOT_DEFAULT_KIND: Readonly<Record<string, string>> = {
  main_hand: "sword",
  off_hand: "round_shield",
  head: "helmet",
  body: "mail",
  hands: "leather_gloves",
  feet: "boots",
  neck: "pendant",
  ring_1: "ring",
  ring_2: "ring",
};

/** 造型清單（供預覽頁與測試用）。 */
export function gearKinds(): readonly KindEntry[] {
  return appearance.kinds as unknown as KindEntry[];
}

/**
 * 外觀形制名（RG-8，玩法 PM 交接 4.1.7 第 2 點：物品名維持「塔盾」，「雲紋碑盾」「熔殼塔盾」當外觀形制名，放圖示說明、物品卡副標）。
 * 只有限定副手特性的形制（`appearance.yaml` 的 `offhands`，目前就是這兩種大盾）回傳名字；其他形制、缺欄位、不認得的值回 `null`（畫面照原本）。
 * 直接比對 `kind`＋`form`，不走 `resolveGear` 的退回預設（退回的形制不是這件物品的形制名）。
 */
export function signatureFormZh(it: GearLook | null | undefined): string | null {
  if (it == null || it.kind == null || it.form == null) return null;
  const form = KINDS[it.kind]?.forms.find((f) => f.id === it.form);
  return form?.offhands !== undefined && form.offhands.length > 0 ? form.zh : null;
}

/** 沒寫（或不認得）`form` 時退回的形制（QI-1a D1：錘退戰錘，和人物、樣張 `NO_FORM` 一致）；其他種類退清單第一個。 */
const NO_FORM: Readonly<Record<string, string>> = { hammer: "warhammer" };

/** 武器元素 → 元素關鍵字（與 `dollGear.ELEMENT_OF_KEYWORD` 相反）；物理、神聖等沒有對應色的元素不套色。 */
const KEYWORD_OF_ELEMENT: Readonly<Record<string, string>> = { fire: "ignite", water: "wet", lightning: "charged", ice: "frozen" };

/** 驗證＋補預設：任何輸入都回傳畫得出來的外觀。`slot`：物品所在欄位，`kind` 缺漏時用來選預設造型。 */
export function resolveGear(it: GearLook | null | undefined, slot?: string): Resolved {
  const src = it ?? {};
  const wanted = src.kind ?? (slot !== undefined ? SLOT_DEFAULT_KIND[slot] : undefined);
  const kind = wanted !== undefined && wanted !== null && KINDS[wanted] !== undefined ? wanted : FALLBACK_KIND;
  const K = KINDS[kind] as KindEntry;
  const form = K.forms.find((f) => f.id === src.form) ?? K.forms.find((f) => f.id === NO_FORM[kind]) ?? (K.forms[0] as KindEntry["forms"][number]);
  const mats = form.materials ?? K.materials;
  const material = src.material != null && mats.includes(src.material) ? src.material : (form.defaultMaterial ?? K.defaultMaterial);
  const dye = (appearance.dyeMaterials as string[]).includes(material) && src.dye != null && GEAR_DYE[src.dye] !== undefined ? src.dye : null;
  const fromElement = src.element != null ? KEYWORD_OF_ELEMENT[src.element] : undefined;
  const given = (src.keywords ?? []).filter((k) => KEYWORD_COLOR[k] !== undefined && !STACK_KEYWORDS.has(k)); /* KW-3：層數關鍵字裝備不帶 */
  const keywords = (fromElement !== undefined && !given.includes(fromElement) ? [fromElement, ...given] : given).slice(0, MAX_KEYWORDS);
  const rarity = src.rarity != null && GEAR_RARITY[src.rarity] !== undefined ? src.rarity : "common";
  return { kind, form: form.id, material, dye, keywords, rarity, style: "common" };
}
