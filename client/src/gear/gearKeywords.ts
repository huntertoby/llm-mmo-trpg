// 裝備說明框的「關鍵字」行（Phase QI-4b，需求 docs/art/Q版小圖示-關鍵字移植需求.md 1.3 第 3 點；規格 docs/phases/PhaseQI-4計畫.md 第 0 節第 1～3 列）。
// 列的是圖示代表的那幾個：`resolveGear(look, slot).keywords`（認得的、最多 2 個、武器表元素換成的元素關鍵字在前），和圓章、點用同一份。
// 中文名來自 `gearAppearance.json` 的 `keywordNames`（後端 `skill_keywords.yaml` 匯出，不寫死在元件裡）；沒有名稱時寫 id。
// 物品若有第 3 個會產生關鍵字的詞條，後端已截掉（`derive_keywords(limit=2)`），這裡看不到（詞條行本身仍列出）。純函式。
import appearance from "../render/gearAppearance.json";
import { resolveGear, type GearLook } from "../render/gearResolve";
import type { TipLine } from "./affixStatus";

const NAMES: Readonly<Record<string, string | undefined>> = appearance.keywordNames;

/** 一個關鍵字的中文名（`keywordNames`；沒有時回 id）。 */
export const keywordName = (id: string): string => NAMES[id] ?? id;

/** 「關鍵字：點燃、潮濕」；沒有（認得的）關鍵字時回 `null`。 */
export function gearKeywordLine(look: GearLook | null | undefined, slot?: string): string | null {
  const kws = resolveGear(look, slot).keywords;
  return kws.length === 0 ? null : `關鍵字：${kws.map(keywordName).join("、")}`;
}

/** 說明卡的行後面接上「關鍵字」行（沒有關鍵字時原樣回傳同一個陣列）。 */
export function withKeywordLine(lines: TipLine[], look: GearLook | null | undefined, slot?: string): TipLine[] {
  const kw = gearKeywordLine(look, slot);
  return kw === null ? lines : [...lines, { text: kw, note: null }];
}
