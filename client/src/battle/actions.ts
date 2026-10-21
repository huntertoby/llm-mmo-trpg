// 合法動作分類（純函式）：可移動的格子、可攻擊的敵人、其他動作（附中文標籤）、結束回合。
import type { Action, AttackAction, BattleView, MoveAction, Pos } from "../api/types";
import { DIRECTIONS, objectStyle, reactionName } from "./glossary";
import { REACTION_MODE_LABELS } from "./reactions";
import { posKey, samePos } from "./geometry";
import { unitNames, type UnitNames } from "./units";

export interface LabeledAction {
  action: Action;
  label: string;
}

export interface ClassifiedActions {
  /** 目的地（`x,y`）→ 移動動作（同一格多條路徑取第一條）。 */
  moves: Map<string, MoveAction>;
  /** 敵方單位 ID → 對它的普攻（多個時取第一個）。 */
  attacks: Map<string, AttackAction>;
  /** 其他動作：技能、攻擊物件、推擊、絆倒、防禦、互動、結束姿態、原地起身……（依原順序）。 */
  others: LabeledAction[];
  endTurn: Action | null;
}

/** 技能 ID → 中文名（還沒取得時顯示 ID）。 */
export type SkillNames = Readonly<Record<string, string>>;

function posText(p: Pos): string {
  return `(${p.x}, ${p.y})`;
}

function objectLabel(view: BattleView, objectId: string): string {
  const obj = view.objects.find((o) => o.id === objectId);
  return obj === undefined ? objectId : `${objectStyle(obj.kind).name} ${posText(obj.pos)}`;
}

function skillTarget(a: Extract<Action, { type: "use_skill" }>, view: BattleView, names: UnitNames): string {
  if (a.target_id != null && a.second_target_id != null)
    return `${names.label(a.target_id)} ⇄ ${names.label(a.second_target_id)}`; // 任意兩者互換
  if (a.target_id != null && a.target_pos != null) return `${names.label(a.target_id)} → ${posText(a.target_pos)}`; // 傳送他人
  if (a.target_id != null) return names.label(a.target_id);
  if (a.target_object_id != null) return objectLabel(view, a.target_object_id);
  if (a.target_pos != null) return posText(a.target_pos);
  if (a.direction != null) return `向${DIRECTIONS[a.direction] ?? a.direction}`;
  return "";
}

/** 一個動作的中文標籤（「其他動作」清單用；也可用於任何動作）。 */
export function actionLabel(
  action: Action,
  view: BattleView,
  skills: SkillNames,
  names: UnitNames = unitNames(view),
): string {
  switch (action.type) {
    case "use_skill": {
      const target = skillTarget(action, view, names);
      const name = skills[action.skill_id] ?? action.skill_id;
      return target === "" ? `技能：${name}` : `技能：${name} → ${target}`;
    }
    case "attack":
      return action.target_id != null
        ? `攻擊：${names.label(action.target_id)}`
        : `攻擊：${objectLabel(view, action.target_object_id ?? "")}`;
    case "move": {
      const dest = action.path[action.path.length - 1];
      return action.path.length <= 1 || dest === undefined ? "起身" : `移動到 ${posText(dest)}`;
    }
    case "defend":
      return action.target_id != null ? `守護：${names.label(action.target_id)}` : "守護自己";
    case "swap":
      return `換位：${names.label(action.target_id)}`;
    case "aim":
      return "瞄準";
    case "run":
      return "跑步";
    case "shove":
      return `推擊：${names.label(action.target_id)}`;
    case "trip":
      return `絆倒：${names.label(action.target_id)}`;
    case "interact":
      if (action.mode === "shove_aside")
        return `撥開：${objectLabel(view, action.object_id)}（往${action.side === "right" ? "右" : "左"}）`;
      return `推動：${objectLabel(view, action.object_id)}`;
    case "end_stance":
      return "結束姿態";
    case "set_reaction_mode":
      return `反應設定：${reactionName(action.reaction)} → ${REACTION_MODE_LABELS[action.mode]}`;
    case "end_turn":
      return "結束回合";
  }
}

function enemyIds(view: BattleView): Set<string> {
  return new Set(view.units.filter((u) => u.team !== view.team).map((u) => u.id));
}

export function classifyActions(
  actions: readonly Action[],
  view: BattleView,
  skills: SkillNames,
): ClassifiedActions {
  const names = unitNames(view);
  const enemies = enemyIds(view);
  const result: ClassifiedActions = { moves: new Map(), attacks: new Map(), others: [], endTurn: null };
  for (const action of actions) {
    if (action.type === "end_turn") {
      result.endTurn ??= action;
      continue;
    }
    if (action.type === "move") {
      const start = action.path[0];
      const dest = action.path[action.path.length - 1];
      if (start !== undefined && dest !== undefined && !samePos(start, dest)) {
        const key = posKey(dest);
        if (!result.moves.has(key)) result.moves.set(key, action);
        continue;
      }
    }
    if (action.type === "attack" && action.target_id != null && enemies.has(action.target_id)) {
      if (!result.attacks.has(action.target_id)) result.attacks.set(action.target_id, action);
      continue;
    }
    result.others.push({ action, label: actionLabel(action, view, skills, names) });
  }
  return result;
}

/** 點選格子 → 要送出的動作：格上有可攻擊的敵人就攻擊，否則可移動就移動，否則 `null`。 */
export function actionForClick(classified: ClassifiedActions, view: BattleView, tile: Pos): Action | null {
  const target = view.units.find((u) => !u.downed && !u.escaped && !u.dismissed && samePos(u.pos, tile));
  if (target !== undefined) {
    const attack = classified.attacks.get(target.id);
    if (attack !== undefined) return attack;
  }
  return classified.moves.get(posKey(tile)) ?? null;
}

/** 技能 ID（取技能名用）：合法動作中出現的與我方單位裝備的。 */
export function skillIdsOf(actions: readonly Action[], view: BattleView): string[] {
  const ids = new Set<string>();
  for (const a of actions) if (a.type === "use_skill") ids.add(a.skill_id);
  for (const u of view.units) for (const s of u.skills) ids.add(s);
  return [...ids].sort();
}
