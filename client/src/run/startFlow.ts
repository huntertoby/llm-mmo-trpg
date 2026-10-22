// 新開局（Phase 3-24b2，06 6.27.3）的純函式：選關鍵字、能不能開始、三選一卡片的「加深／橋接／新方向」標示、開發者模式。
// 遊戲不定義流派：這裡沒有任何流派名稱；開發者起始包的名稱只在 ?dev=1 的開發者選單出現。
import type { OfferTag, StartKeywordOption } from "../api/types";

/** 點一個關鍵字：已選就取消；未選且還沒滿就加到最後（順序＝給招的順序）；滿了就不變。 */
export function toggleKeyword(selected: readonly string[], id: string, limit: number): string[] {
  if (selected.includes(id)) return selected.filter((k) => k !== id);
  if (selected.length >= limit) return [...selected];
  return [...selected, id];
}

/** 這個關鍵字能不能選：這把武器湊得到起始技能（預覽有技能）。 */
export function keywordAvailable(option: StartKeywordOption): boolean {
  return option.skill !== null && option.skill !== undefined;
}

/** 換武器後，把湊不到起始技能的已選關鍵字拿掉。 */
export function keepAvailable(selected: readonly string[], options: readonly StartKeywordOption[]): string[] {
  const ok = new Set(options.filter(keywordAvailable).map((o) => o.keyword.id));
  return selected.filter((k) => ok.has(k));
}

/** 可以開始：選了武器、剛好 `count` 個關鍵字，且每個都湊得到起始技能。 */
export function canStart(
  weapon: string,
  selected: readonly string[],
  count: number,
  options: readonly StartKeywordOption[],
): boolean {
  if (weapon === "" || selected.length !== count) return false;
  return selected.every((k) => options.some((o) => o.keyword.id === k && keywordAvailable(o)));
}

/** 三選一卡片的標示文字：「加深：點燃」「橋接：點燃＋標記」「新方向：撞擊」。 */
export function offerTagText(tag: OfferTag): string {
  const names = tag.keywords.map((k) => k.name_zh).join("＋");
  return names === "" ? tag.label_zh : `${tag.label_zh}：${names}`;
}

/** 標示的補充說明（退回時說明原因）。 */
export function offerTagHint(tag: OfferTag): string {
  if (!tag.fallback) {
    if (tag.kind === "deepen") return "帶你持有最多的關鍵字";
    if (tag.kind === "bridge") return "同時接上你已持有的兩個關鍵字";
    return "你還沒有的關鍵字";
  }
  if (tag.kind === "bridge") return "找不到同時接上兩個已持有關鍵字的技能：從持有的接到新的關鍵字";
  if (tag.kind === "deepen") return "還沒有可加深的關鍵字：改給新的方向";
  return "所有關鍵字都有了：改給持有最少的";
}

/** 開發者模式：網址帶 `?dev=1`（或 `dev=true`）才顯示開發者起始包選單。 */
export function isDevMode(search: string): boolean {
  const value = new URLSearchParams(search).get("dev");
  return value === "1" || value === "true";
}
