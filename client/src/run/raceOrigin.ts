// 開局的「種族與出身」（Phase 3R-3a，設計文件 07 7.7）：純函式。
// 開局順序：種族與出身 → 武器 → 2 關鍵字。種族技與環境被動都不給數值；出身不影響戰鬥。
import type { OriginOption, RaceOption, StartOptions } from "../api/types";

export interface RaceOriginChoice {
  race: string;
  origin: string;
}

/** 開局選項有沒有種族與出身（舊後端或沒有種族資料時沒有；沒有就不顯示這一步）。 */
export function hasRaceOrigin(options: StartOptions | null): boolean {
  return options !== null && (options.races ?? []).length > 0 && (options.origins ?? []).length > 0;
}

/** 種族與出身都選好了（沒有這一步的選項時視為好了）。 */
export function raceOriginDone(options: StartOptions | null, choice: RaceOriginChoice): boolean {
  if (!hasRaceOrigin(options)) return true;
  return choice.race !== "" && choice.origin !== "";
}

/** 送給 `POST /api/runs` 的欄位：沒選的不帶（舊流程＝無種族、無出身）。 */
export function raceOriginBody(choice: RaceOriginChoice): { race?: string; origin?: string } {
  return { ...(choice.race === "" ? {} : { race: choice.race }), ...(choice.origin === "" ? {} : { origin: choice.origin }) };
}

/** 種族卡浮動卡的各行：種族技（說明已含每場次數）、花費與環境被動。 */
export function raceCardLines(race: RaceOption): string[] {
  return [
    `種族技・${race.skill_name_zh}：${race.skill_description_zh}`,
    `花費 ${race.skill_ap} AP・不佔技能欄`,
    `環境被動・${race.passive_name_zh}：${race.passive_description_zh}`,
  ];
}

/** 種族卡上的一行小字：「林隱／林間視野」。 */
export function raceSummary(race: RaceOption): string {
  return `${race.skill_name_zh}／${race.passive_name_zh}`;
}

/** 出身卡浮動卡的各行：界域、簡介、不影響戰鬥的提醒。 */
export function originCardLines(origin: OriginOption): string[] {
  return [`界域：${origin.realm_name_zh}`, origin.description_zh, "出身只影響外觀與劇情，不影響戰鬥數值。"];
}

/** 已選種族與出身的一句話（開局畫面與一輪面板用）；都沒選時 `null`。 */
export function raceOriginText(raceName: string | null | undefined, originName: string | null | undefined): string | null {
  const parts = [raceName, originName].filter((s): s is string => s !== null && s !== undefined && s !== "");
  return parts.length === 0 ? null : parts.join("・");
}
