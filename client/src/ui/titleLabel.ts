// 帳號紀念稱號的文字（Phase 5F-3c）：例「「碎晶的終結者（s1）」」；多個稱號用頓號隔開。

/** 稱號清單 → 顯示文字（沒有稱號＝空字串）。 */
export function accountTitlesLabel(titles?: readonly string[] | null): string {
  const list = (titles ?? []).filter((t) => t !== "");
  return list.length === 0 ? "" : list.map((t) => `「${t}」`).join("、");
}
