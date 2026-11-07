// 盜賊三套的區域外觀（QK-8；docs/design/18-雲嶺內容.md 18.5.1 第 1 條）：`content/ui/region_dolls.yaml` 在 build 時以 `?raw` 匯入、
// 用 `yaml` 解析（內容即資料；Python 端 `trpg.content.region_dolls` 驗證同一份檔）。
// 戰場在表上的區域時，表上範本的紙娃娃外觀換成表裡的；武器（主手造型覆寫）、詞綴、特徵、大小照範本。純函式。
import { parse } from "yaml";
import regionDollsYaml from "../../../content/ui/region_dolls.yaml?raw";
import type { DollLook } from "../api/types";

type Table = Readonly<Record<string, Readonly<Record<string, Partial<DollLook>>>>>;

function load(): Table {
  try {
    const d = parse(regionDollsYaml) as { regions?: unknown } | null;
    const r = d?.regions;
    return r !== null && typeof r === "object" ? (r as Table) : {};
  } catch {
    return {};
  }
}
export const REGION_DOLLS: Table = load();

/** 照範本留下的欄位（武器、詞綴、特徵、大小）。 */
const KEEP = ["main_kind", "main_material", "main_color", "main_tassel", "main_glow", "affixes", "traits", "scale"] as const;

/** 表上的範本：先找完全相同的 ID，再找最長的前綴（精英詞綴的範本 ID 是 `<範本>_<詞綴>`，例 `bandit_captain_heart_linked`）。 */
function rowOf(region: string, template: string): Partial<DollLook> | undefined {
  const table = REGION_DOLLS[region];
  if (table === undefined) return undefined;
  const parts = template.split("_");
  for (let n = parts.length; n > 0; n--) {
    const row = table[parts.slice(0, n).join("_")];
    if (row !== undefined) return row;
  }
  return undefined;
}

/** 這一區這個範本的外觀：表上有就換（保留範本的武器與詞綴）；沒有回傳原本的。 */
export function regionDollLook(region: string | null | undefined, template: string, doll: DollLook | null | undefined): DollLook | null {
  const o = region ? rowOf(region, template) : undefined;
  if (o === undefined || doll == null || doll.creature != null) return doll ?? null;
  const out: Record<string, unknown> = { ...doll, ...o };
  for (const k of KEEP) {
    const v = (doll as unknown as Record<string, unknown>)[k];
    if (v === undefined) delete out[k];
    else out[k] = v;
  }
  return out as unknown as DollLook;
}
