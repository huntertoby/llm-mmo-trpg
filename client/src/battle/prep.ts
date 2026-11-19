// 戰前佈置（SK-3，06 6.38 第 11 點）：開戰前（雙方都還沒行動）在我方起始區免費放 1 個自己的
// 陷阱、刻印或表面。伺服器在 `awaiting === "prep"` 時給 `prep`（可放的技能與每招放得下的格子）；
// 選了一招後，那招的格子當成一個選取模式（同複合技能第二段），點格子就送 `/prep`。
import type { Action, Pos, PrepOut, SkillCard } from "../api/types";
import { posKey } from "./geometry";
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

/** 選目標模式是戰前佈置選格（`prepMode` 做的 key）。 */
export function isPrepModeKey(key: string): boolean {
  return key.startsWith("prep:");
}

/** AR-SK4：佈置選格時左上技能說明卡的字（玩法 PM 11-19 定案；不寫顏色）。`count`＝可放的格數。 */
export function prepModeHint(count: number): string {
  return `點框起來的起始區裡的一格放下（可選 ${count} 格）。Esc／右鍵取消。`;
}

/**
 * AR-SK4（AR-SK3 驗收第 10 件）：佈置選格時，滑過可放的格子不顯示格子資訊卡（「放在這裡」就是那一格最重要的資訊）；
 * 滑過其他格子照舊。
 */
export function prepHidesTileCard(mode: ActionMode | null, tile: Pos | null): boolean {
  return mode !== null && tile !== null && isPrepModeKey(mode.key) && mode.targets.tiles.has(posKey(tile));
}

export function prepPromptText(prep: PrepOut, picked: string | null, skillName: string): string {
  if (prep.options.length === 0) return "目前沒有可以佈置的技能，直接開戰。";
  if (picked === null)
    return "開戰前可以在我方起始區免費放 1 個自己的陷阱、刻印或表面（每場 1 個；放了那招會照常進冷卻）。先選一招，或直接開戰。";
  const option = prep.options.find((o) => o.skill_id === picked);
  const what = option === undefined ? "" : (PREP_KIND_ZH[option.kind] ?? option.kind);
  // AR-SK3：起始區格子換成金色框記號，字照玩法 PM 定案（「高亮的起始區」→「框起來的起始區」）
  return `「${skillName}」：在框起來的起始區格子點一下放${what}（共 ${option?.tiles.length ?? 0} 格可放）；按 Esc 換一招。`;
}

/**
 * AR-SK3：戰前佈置的格子記號（取代借來的選目標紅框；`render/prepMarks.ts` 畫）：
 * `cells`＝這一招放得下的格子（只畫這些，起始區其他格不畫）、`hover`＝指著的那一格（在 `cells` 裡才算）、
 * `kind`＝要放什麼（預覽用）、`surface`＝表面的種類（技能卡第一個 `create_surface` 的表面；沒有時 null）。
 */
export interface PrepMarksDraw {
  cells: readonly Pos[];
  hover: Pos | null;
  kind: "trap" | "rune" | "surface";
  surface: string | null;
}

export function prepMarksOf(prep: PrepOut, skillId: string, hover: Pos | null, card?: SkillCard): PrepMarksDraw | null {
  const option = prep.options.find((o) => o.skill_id === skillId);
  if (option === undefined || option.tiles.length === 0) return null;
  const cells = option.tiles.map(([x, y]): Pos => ({ x, y }));
  const on = hover !== null && cells.some((c) => c.x === hover.x && c.y === hover.y) ? hover : null;
  const effects = card?.icon?.segments?.flatMap((seg) => seg.effects ?? []) ?? [];
  const surface = effects.find((e) => e.type === "create_surface")?.surface ?? null;
  return { cells, hover: on, kind: option.kind, surface: option.kind === "surface" ? surface : null };
}
