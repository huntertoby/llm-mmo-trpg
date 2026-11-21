// 一輪 roguelite 的說明句（HC-6b）：場數、標準隊友人數、營火的源力照伺服器（`/api/glossary` 的 `rules`，
// `roguelite.yaml`），前端不寫死。目前的值組出來和改前的字逐字相同。
import { gameRules } from "../battle/glossary";

/** 「5 場戰鬥加頭目」。 */
export function runLengthText(battles: number = gameRules().roguelite_battles): string {
  return `${battles} 場戰鬥加頭目`;
}

/** 開新一輪的副標。 */
export function runNewSubText(): string {
  return `roguelite：${runLengthText()}，一路帶著同一個主角`;
}

/** 開新一輪表單下的「共 5 場戰鬥加頭目；」。 */
export function runTotalText(): string {
  return `共 ${runLengthText()}；`;
}

/** 開新一輪表單下的「隊友為 2 名標準隊友。」。 */
export function runCompanionsText(companions: number = gameRules().roguelite_companions): string {
  return `隊友為 ${companions} 名標準隊友。`;
}

/** 一輪畫面下一場的隊友說明（後面接伺服器的資源規則句）。 */
export function runCompanionsLine(companions: number = gameRules().roguelite_companions): string {
  return `隊友：標準隊友 ${companions} 名（滿狀態）；`;
}

/** 開發選單「roguelite 一輪」那格的說明。 */
export function runStartBlurb(): string {
  return `${runLengthText()}：打贏升級、營火回滿，一路帶著同一個主角。`;
}

/** 營火畫面的回滿說明。 */
export function campfireRestText(source: number = gameRules().campfire_source): string {
  return `HP、法力與耐力已回滿，源力 +${source}。`;
}
