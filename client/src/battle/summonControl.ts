// 召喚物操控（Phase 3-33c，docs/design/06-技能.md 6.29.2）的純函式：
// 0 AP 模式切換（集火／守護我／跟隨／待命）與 1 AP 指揮（指定移動＋普攻）。
// 模式與已指揮的狀態來自 UnitView（summon_mode／summon_target_id／commanded）；
// 指揮的終點與目標由伺服器的 command-options 提供。
// 灌注技能（Phase 3-33d，6.29.3）：1 AP 把主角的一招主動技能借給召喚物，牠在下一個自己的回合開始時
// 從自己的位置施放；技能選單（含不能灌注的中文原因）由伺服器的 infuse-options 提供。
import type { Action, BattleView, CommandOption, CommandOptions, InfuseOptions, InfusionPreview, Pos, UnitView } from "../api/types";
import { samePos } from "./geometry";
import { isAlive, type UnitNames } from "./units";

/** 進行中的灌注：哪隻、伺服器給的技能選單。 */
export interface InfuseSession {
  summonId: string;
  options: InfuseOptions;
}

/** 進行中的指揮：哪隻、伺服器給的選項、目前選的終點（`null` ＝ 還沒選）。 */
export interface CommandSession {
  summonId: string;
  options: CommandOptions;
  dest: Pos | null;
}

export type SummonMode = NonNullable<UnitView["summon_mode"]>;

/** 模式的顯示順序。 */
export const MODE_ORDER: readonly SummonMode[] = ["focus", "guard", "follow", "hold"];

export const MODE_LABELS: Readonly<Record<SummonMode, string>> = {
  focus: "集火",
  guard: "守護我",
  follow: "跟隨",
  hold: "待命",
};

export const MODE_HINTS: Readonly<Record<SummonMode, string>> = {
  focus: "打你指定的敵人；目標倒下或離場後退回「跟隨」。",
  guard: "待在你 2 格內，優先打威脅你的敵人。",
  follow: "靠近你行動，但會主動攻擊附近的敵人。",
  hold: "原地不動，只打相鄰的敵人。",
};

function byId(a: UnitView, b: UnitView): number {
  return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
}

/** 主角目前在場上、能被操控的召喚物（圖騰沒有模式），依單位 ID 排序。 */
export function controllableSummons(view: BattleView, heroId: string): UnitView[] {
  return view.units.filter((u) => u.owner_id === heroId && u.summon_mode != null && isAlive(u)).sort(byId);
}

/** 「集火 → 盜賊1」「守護我」。 */
export function modeText(summon: UnitView, names: UnitNames): string {
  if (summon.summon_mode == null) return "";
  const label = MODE_LABELS[summon.summon_mode];
  return summon.summon_mode === "focus" && summon.summon_target_id != null
    ? `${label} → ${names.name(summon.summon_target_id)}`
    : label;
}

/** 可以指定的集火目標：場上的敵方單位（含敵方召喚物），依單位 ID 排序。 */
export function focusTargets(view: BattleView): UnitView[] {
  return view.units.filter((u) => u.team !== view.team && isAlive(u)).sort(byId);
}

export interface ModeButton {
  mode: SummonMode;
  label: string;
  hint: string;
  /** 目前就是這個模式。 */
  current: boolean;
  /** 集火要再選目標。 */
  needsTarget: boolean;
  /** 不能按（沒輪到、已經是這個模式、集火卻沒有敵人）。集火已是目前模式時仍可按來換目標。 */
  disabled: boolean;
}

/** 四個 0 AP 模式按鈕，`current` 標示目前模式。 */
export function modeButtons(summon: UnitView, canAct: boolean, view: BattleView): ModeButton[] {
  const hasFoes = focusTargets(view).length > 0;
  return MODE_ORDER.map((mode) => ({
    mode,
    label: MODE_LABELS[mode],
    hint: MODE_HINTS[mode],
    current: summon.summon_mode === mode,
    needsTarget: mode === "focus",
    disabled: !canAct || (mode === "focus" ? !hasFoes : summon.summon_mode === mode),
  }));
}

export function setModeAction(heroId: string, summonId: string, mode: SummonMode, targetId?: string): Action {
  return targetId === undefined
    ? { type: "set_summon_mode", unit_id: heroId, summon_id: summonId, mode }
    : { type: "set_summon_mode", unit_id: heroId, summon_id: summonId, mode, target_id: targetId };
}

/** 指揮鈕不能用的原因；可以用時 `null`（伺服器還會檢查暈眩等）。 */
export function commandBlocked(view: BattleView, hero: UnitView, summon: UnitView, canAct: boolean): string | null {
  if (!canAct) return "現在不是你的回合";
  if (summon.commanded) return "本輪已經指揮過了（每隻每輪 1 次）";
  if (hero.ap < view.summon_command_ap_cost) return `AP 不足：指揮需要 ${view.summon_command_ap_cost} AP`;
  return null;
}

/** 某個終點的選項（`options[0]` 是原地不動）。 */
export function optionAt(options: CommandOptions, tile: Pos): CommandOption | undefined {
  return options.options.find((o) => samePos(o.dest, tile));
}

/** 地圖上要標示的可到達格子（不含原地）。 */
export function commandMoveTiles(options: CommandOptions): Pos[] {
  return options.options.filter((o) => o.path.length > 1).map((o) => o.dest);
}

/** 選定終點後，打得到的敵人所在格（紅框）。 */
export function commandTargetTiles(option: CommandOption | undefined, view: BattleView): Pos[] {
  if (option === undefined) return [];
  const ids = new Set(option.targets);
  return view.units.filter((u) => ids.has(u.id)).map((u) => u.pos);
}

/** 指揮動作：`option.path` 只有起點（原地）時不帶 path。至少要有移動或攻擊目標，否則 `null`。 */
export function commandAction(
  heroId: string,
  summonId: string,
  option: CommandOption,
  targetId?: string,
): Action | null {
  const moves = option.path.length > 1;
  if (!moves && targetId === undefined) return null;
  return {
    type: "command_summon",
    unit_id: heroId,
    summon_id: summonId,
    path: moves ? [...option.path] : [],
    ...(targetId === undefined ? {} : { target_id: targetId }),
  };
}

/** 終點在下拉清單中的文字：「(4, 3)・可打 盜賊1」「原地・可打 …」。 */
export function optionLabel(option: CommandOption, names: UnitNames): string {
  const here = option.path.length <= 1 ? "原地" : `(${option.dest.x}, ${option.dest.y})`;
  const foes = option.targets.length === 0 ? "" : `・可打 ${option.targets.map((id) => names.name(id)).join("、")}`;
  return `${here}${foes}`;
}

// ---- 灌注技能（Phase 3-33d）----

export const INFUSE_HINT =
  "把你的一招主動技能借給牠：法力與冷卻現在由你付，牠在下一個自己的回合開始時從自己的位置施放（目標依目前模式選）；每隻每輪 1 次。牠在施放前倒下或消失，法力與冷卻不退。";

/** 灌注鈕不能用的原因；可以用時 `null`（技能本身能不能灌注看選單；伺服器還會檢查暈眩、到期等）。 */
export function infuseBlocked(view: BattleView, hero: UnitView, summon: UnitView, canAct: boolean): string | null {
  if (!canAct) return "現在不是你的回合";
  if (summon.infused_skill_id != null) return `身上已經有待施放的「${summon.infused_skill_name_zh ?? summon.infused_skill_id}」`;
  if (summon.infused) return "本輪已經灌注過了（每隻每輪 1 次）";
  const cost = view.summon_infuse_ap_cost;
  if (hero.ap < cost) return `AP 不足：灌注需要 ${cost} AP`;
  return null;
}

export function infuseAction(heroId: string, summonId: string, skillId: string): Action {
  return { type: "infuse_skill", unit_id: heroId, summon_id: summonId, skill_id: skillId };
}

export interface InfuseRow {
  skillId: string;
  name: string;
  /** 不能灌注的中文原因（技能本身的原因優先，其次是召喚物或 AP 的問題）；可以時 `null`。 */
  reason: string | null;
}

/** 灌注選單的每一列（照伺服器給的順序）。 */
export function infuseRows(options: InfuseOptions): InfuseRow[] {
  return options.skills.map((s) => ({ skillId: s.skill_id, name: s.name_zh, reason: s.problem ?? options.problem ?? null }));
}

/** 召喚物列上的「待施放」文字；沒有時 `null`。 */
export function pendingInfusionText(summon: UnitView): string | null {
  if (summon.infused_skill_id == null) return null;
  return `待施放：${summon.infused_skill_name_zh ?? summon.infused_skill_id}（下回合開始時）`;
}

/** 灌注預覽中召喚物會選的目標單位所在格（紅框）；沒有單位目標時空。 */
export function infusionTargetTiles(info: InfusionPreview, view: BattleView): Pos[] {
  const ids = new Set(info.units);
  if (info.target_id != null) ids.add(info.target_id);
  return view.units.filter((u) => ids.has(u.id) && u.team !== view.team).map((u) => u.pos);
}

/** 灌注預覽的一行說明：「從 (2, 3) 施放 → 盜賊1」「選不到目標：下回合會放棄（法力與冷卻不退）」。 */
export function infusionPreviewText(info: InfusionPreview, names: UnitNames): string {
  if (info.no_target) return "以牠目前的位置與模式選不到目標：下回合開始時會放棄（法力與冷卻不退）。";
  const at = `從 (${info.origin[0]}, ${info.origin[1]}) 施放`;
  if (info.target_id != null) return `${at} → ${names.name(info.target_id)}`;
  if (info.target_pos != null) return `${at} → (${info.target_pos[0]}, ${info.target_pos[1]})`;
  return `${at}，影響 ${info.tiles.length} 格`;
}
