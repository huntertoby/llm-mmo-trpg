// 種族技與環境被動（Phase 3R-2，設計文件 07 7.7）：純函式。
// 種族技不佔技能欄，在技能列另外一組按鈕；選取方式和技能相同（合法動作 `use_race_skill` 的欄位）。
import type { Action, RaceView, UnitView } from "../api/types";
import { buildTargets, type ActionMode } from "./targeting";

const CHOICE_ZH: Readonly<Record<string, string>> = { stamina: "耐力", mana: "法力" };

/** 種族技按鈕為什麼不能按（可以按時 `undefined`）：AP 不足、次數用完、或沒有合法的目標。 */
export function raceBlockedReason(hero: UnitView, race: RaceView, hasActions: boolean): string | undefined {
  if (hasActions) return undefined;
  if (race.skill_uses_left <= 0) return `${race.skill_name_zh}本場已用完（限用 ${race.skill_uses_max} 次）`;
  if (hero.ap < race.skill_ap) return `AP 不足：需要 ${race.skill_ap}，剩餘 ${hero.ap}`;
  return `${race.skill_name_zh}現在沒有合法的目標或條件不符`;
}

/** 按鈕上的標籤：「林隱」；有選項的種族技（過充）每個選項一顆：「過充（耐力）」。 */
export function raceLabel(race: RaceView, choice: string): string {
  return choice === "" ? race.skill_name_zh : `${race.skill_name_zh}（${CHOICE_ZH[choice] ?? choice}）`;
}

/** 按鈕上的小字：「剩 1／2 次」。 */
export function raceUsesText(race: RaceView): string {
  return `${race.skill_ap} AP・剩 ${race.skill_uses_left}／${race.skill_uses_max} 次`;
}

/**
 * 主角的種族技模式（沒有種族時空陣列）。選項（過充的耐力／法力）各自一個模式，鍵為 `race:<選項>`；
 * 沒有合法動作的模式帶 `blockedReason`（按鈕灰色，點了顯示原因）。
 */
export function raceModes(hero: UnitView | null, legal: readonly Action[]): ActionMode[] {
  const race = hero?.race ?? null;
  if (hero === null || race === null) return [];
  const mine = legal.filter((a): a is Extract<Action, { type: "use_race_skill" }> => a.type === "use_race_skill");
  const choices = race.skill_choices.length > 0 ? [...race.skill_choices] : [""];
  return choices.map((choice) => {
    const actions = mine.filter((a) => (a.choice ?? "") === choice);
    return {
      key: `race:${choice}`,
      kind: "race" as const,
      label: raceLabel(race, choice),
      skillId: null,
      actions,
      targets: buildTargets(actions),
      blockedReason: raceBlockedReason(hero, race, actions.length > 0),
    };
  });
}

/** 種族技卡片（浮動卡）的各行：說明、花費與次數、選取方式。 */
export function raceBattleCardLines(race: RaceView): string[] {
  const lines = [race.skill_description_zh, `花費 ${race.skill_ap} AP・本場限用 ${race.skill_uses_max} 次（剩 ${race.skill_uses_left} 次）・不佔技能欄`];
  const reach = race.skill_range > 0 ? `射程 ${race.skill_range} 格` : "";
  const how = SHAPE_HOW[race.skill_shape];
  if (how !== undefined) lines.push([how, reach].filter((s) => s !== "").join("・"));
  return lines;
}

const SHAPE_HOW: Readonly<Record<string, string>> = {
  self: "對自己使用",
  ground_tile: "選一個格子",
  square3: "選中心格（影響 3×3）",
  cone: "選一個方向（錐形）",
  single: "選一個目標",
  object_then_tile: "先選物件，再選落點",
};

/** 環境被動那一行：「被動・林間視野：……（作用中）」。 */
export function passiveLine(race: RaceView): string {
  return `被動・${race.passive_name_zh}：${race.passive_description_zh}${race.passive_active ? "（目前有作用）" : ""}`;
}

/** HUD 的一行種族文字：「種族：精靈｜林隱 剩 2／2 次｜被動：林間視野（目前有作用）」；沒有種族時 `null`。 */
export function raceHudText(hero: UnitView): string | null {
  const race = hero.race ?? null;
  if (race === null) return null;
  return `種族：${race.name_zh}｜${race.skill_name_zh} 剩 ${race.skill_uses_left}／${race.skill_uses_max} 次｜被動：${race.passive_name_zh}${race.passive_active ? "（目前有作用）" : ""}`;
}
