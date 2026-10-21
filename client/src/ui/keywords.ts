// 技能的關鍵字顯示（Phase 3-24b1，docs/design/06-技能.md 6.27.1）：「製造：點燃｜利用：倒地」。
// 關鍵字由伺服器依原語、條件、觸發自動推導（SkillCard.keywords、WorkshopCheck.keywords）；遊戲不定義流派，
// 這裡只顯示關鍵字本身。
import type { KeywordRef, SkillKeywords } from "../api/types";

/** 一側的文字：關鍵字名稱用「、」連接；沒有時寫「無」。 */
export function keywordSide(refs: readonly KeywordRef[]): string {
  return refs.length === 0 ? "無" : refs.map((k) => k.name_zh).join("、");
}

/** 完整一行，例如「製造：點燃｜利用：倒地」。 */
export function keywordSummary(keywords: SkillKeywords): string {
  return `製造：${keywordSide(keywords.makes)}｜利用：${keywordSide(keywords.uses)}`;
}

/** 製造與利用都沒有關鍵字（工坊草稿剛開始時）。 */
export function noKeywords(keywords: SkillKeywords): boolean {
  return keywords.makes.length === 0 && keywords.uses.length === 0;
}
