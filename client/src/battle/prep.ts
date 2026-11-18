// 戰前佈置（SK-3，06 6.38 第 11 點）：開戰前（雙方都還沒行動）在我方起始區免費放 1 個自己的
// 陷阱、刻印或表面。伺服器在 `awaiting === "prep"` 時給 `prep`（可放的技能與每招放得下的格子）；
// 選了一招後，那招的格子當成一個選取模式（同複合技能第二段），點格子就送 `/prep`。
import type { Action, PrepOut } from "../api/types";
import { buildTargets, type ActionMode } from "./targeting";

export type PrepAction = Extract<Action, { type: "prepare" }>;

export const PREP_KIND_ZH: Readonly<Record<string, string>> = { trap: "陷阱", rune: "刻印", surface: "表面" };

/** 選好的那一招：每個放得下的格子一個 `prepare` 動作。 */
export function prepActions(prep: PrepOut, skillId: string): PrepAction[] {
  const option = prep.options.find((o) => o.skill_id === skillId);
  if (option === undefined) return [];
  return option.tiles.map(([x, y]) => ({ type: "prepare", unit_id: prep.unit_id, skill_id: skillId, target_pos: { x, y } }));
}

export function prepMode(prep: PrepOut, skillId: string, skillName: string): ActionMode | null {
  const actions = prepActions(prep, skillId);
  if (actions.length === 0) return null;
  return {
    key: `prep:${skillId}`,
    kind: "skill",
    label: `${skillName}（戰前佈置）`,
    skillId,
    actions,
    targets: buildTargets(actions),
  };
}

export function prepPromptText(prep: PrepOut, picked: string | null, skillName: string): string {
  if (prep.options.length === 0) return "目前沒有可以佈置的技能，直接開戰。";
  if (picked === null)
    return "開戰前可以在我方起始區免費放 1 個自己的陷阱、刻印或表面（每場 1 個；放了那招會照常進冷卻）。先選一招，或直接開戰。";
  const option = prep.options.find((o) => o.skill_id === picked);
  const what = option === undefined ? "" : (PREP_KIND_ZH[option.kind] ?? option.kind);
  return `「${skillName}」：在高亮的起始區格子點一下放${what}（共 ${option?.tiles.length ?? 0} 格可放）；按 Esc 換一招。`;
}
