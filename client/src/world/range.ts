// 主城工坊靶場（Phase TR-1，#134；21 21.5、06 6.27.3）的畫面邏輯：武器架分組、「看示範」要送哪些關鍵字、選到一半的草稿。
// 規則全部在伺服器（`trpg.world.opening`）：這裡只決定畫面怎麼排、送什麼。
import type { StartWeaponOption } from "../api/types";

export const CLASS_LABELS: Record<string, string> = { melee: "近戰", ranged: "遠程", focus: "法器" };

export interface Rack {
  weaponClass: string;
  name: string;
  weapons: StartWeaponOption[];
}

/** 武器架：照伺服器給的大類順序（近戰、遠程、法器）把可選的武器分組；沒列到的大類接在最後。 */
export function groupRacks(weapons: readonly StartWeaponOption[], order: readonly string[]): Rack[] {
  const classes = [...order, ...weapons.map((w) => w.weapon_class).filter((c) => !order.includes(c))];
  const seen = new Set<string>();
  const out: Rack[] = [];
  for (const cls of classes) {
    if (seen.has(cls)) continue;
    seen.add(cls);
    const list = weapons.filter((w) => w.weapon_class === cls);
    if (list.length > 0) out.push({ weaponClass: cls, name: CLASS_LABELS[cls] ?? cls, weapons: list });
  }
  return out;
}

/** 「看示範」要送的關鍵字（依序給起始技能，伺服器最多收 `count` 個）：已選的就看已選的那組；沒選的接在已選的後面
 * （選滿了就換掉第 2 個），看到的招就是「改選它」時會拿到的那招。 */
export function demoKeywords(selected: readonly string[], keyword: string, count: number): string[] {
  if (selected.includes(keyword)) return [...selected];
  if (selected.length < count) return [...selected, keyword];
  return [...selected.slice(0, count - 1), keyword];
}

export interface RangeDraft {
  weapon: string;
  keywords: string[];
}

const DRAFT_PREFIX = "trpg.rangeDraft.";

/** 選到一半的武器與關鍵字（中途離開、去試打回來時接著選；只是本機的方便，伺服器不記）。讀不到時 `null`。 */
export function readDraft(characterId: string): RangeDraft | null {
  try {
    const raw = window.localStorage.getItem(DRAFT_PREFIX + characterId);
    if (raw === null) return null;
    const data: unknown = JSON.parse(raw);
    if (typeof data !== "object" || data === null) return null;
    const { weapon, keywords } = data as { weapon?: unknown; keywords?: unknown };
    if (typeof weapon !== "string" || !Array.isArray(keywords)) return null;
    return { weapon, keywords: keywords.filter((k): k is string => typeof k === "string") };
  } catch {
    return null;
  }
}

export function writeDraft(characterId: string, draft: RangeDraft | null): void {
  try {
    if (draft === null) window.localStorage.removeItem(DRAFT_PREFIX + characterId);
    else window.localStorage.setItem(DRAFT_PREFIX + characterId, JSON.stringify(draft));
  } catch {
    // 私密視窗或封鎖儲存：不記草稿，照樣能選
  }
}
