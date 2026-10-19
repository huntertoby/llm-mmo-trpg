// 技能列與目標選取（純函式）：合法動作 → 「模式」（技能、攻擊、推擊……）→ 每個模式的合法目標。
import type { Action, BattleView, Direction, InteractOption, Pos, SkillCard, UnitView } from "../api/types";
import { posKey, samePos } from "./geometry";
import { objectStyle } from "./glossary";

function posText(p: Pos): string {
  return `(${p.x}, ${p.y})`;
}

/** 方向 → 格子位移（與引擎相同：北 = y − 1）。 */
export const DIRECTION_DELTA: Readonly<Record<Direction, { dx: number; dy: number }>> = {
  north: { dx: 0, dy: -1 },
  east: { dx: 1, dy: 0 },
  south: { dx: 0, dy: 1 },
  west: { dx: -1, dy: 0 },
};

export const DIRECTION_ARROWS: Readonly<Record<Direction, string>> = {
  north: "↑",
  east: "→",
  south: "↓",
  west: "←",
};

export const DIRECTION_ORDER: readonly Direction[] = ["north", "east", "south", "west"];

export interface TargetSet {
  /** 不需要目標的動作（自身型、防禦、結束姿態、起身）。 */
  self: Action | null;
  /** 目標單位 ID → 動作。 */
  units: Map<string, Action>;
  /** 目標物件 ID → 動作。 */
  objects: Map<string, Action>;
  /** 目標格（"x,y"）→ 動作。 */
  tiles: Map<string, Action>;
  /** 方向 → 動作。 */
  directions: Map<Direction, Action>;
}

export type ModeKind = "skill" | "attack" | "shove" | "trip" | "interact" | "shove_aside" | "defend" | "end_stance" | "stand";

export interface ActionMode {
  /** 選取用的鍵：技能為 `skill:<id>`，其他為類型。 */
  key: string;
  kind: ModeKind;
  label: string;
  skillId: string | null;
  actions: Action[];
  targets: TargetSet;
}

function emptyTargets(): TargetSet {
  return { self: null, units: new Map(), objects: new Map(), tiles: new Map(), directions: new Map() };
}

function setOnce<K>(map: Map<K, Action>, key: K, action: Action): void {
  if (!map.has(key)) map.set(key, action);
}

/** 把一個動作登記到它的目標（單位 > 物件 > 格子 > 方向 > 自身；同一目標取第一個）。 */
function addTarget(t: TargetSet, action: Action): void {
  switch (action.type) {
    case "use_skill":
    case "attack": {
      if (action.target_id != null) setOnce(t.units, action.target_id, action);
      else if (action.target_object_id != null) setOnce(t.objects, action.target_object_id, action);
      else if (action.type === "use_skill" && action.target_pos != null)
        setOnce(t.tiles, posKey(action.target_pos), action);
      else if (action.type === "use_skill" && action.direction != null)
        setOnce(t.directions, action.direction, action);
      else t.self ??= action;
      return;
    }
    case "shove":
    case "trip":
      setOnce(t.units, action.target_id, action);
      return;
    case "interact":
      setOnce(t.objects, action.object_id, action);
      return;
    default:
      t.self ??= action;
  }
}

export function buildTargets(actions: readonly Action[]): TargetSet {
  const t = emptyTargets();
  for (const a of actions) addTarget(t, a);
  return t;
}

function pickableCount(t: TargetSet): number {
  return t.units.size + t.objects.size + t.tiles.size + t.directions.size;
}

/** 這個模式只有「自身」可選（不需要選目標）。 */
export function isSelfOnly(t: TargetSet): boolean {
  return t.self !== null && pickableCount(t) === 0;
}

// ---- 技能列 ---------------------------------------------------------------

export interface SkillButton {
  skillId: string;
  name: string;
  /** 代價各段文字（含 AP、法力、冷卻……，來自技能卡片）；卡片還沒取得時為空。 */
  costs: string[];
  /** 剩餘冷卻回合（0 = 沒有冷卻）。 */
  cooldown: number;
  actions: Action[];
  /** 停用原因（中文）；可用時 `null`。 */
  disabledReason: string | null;
}

export type SkillCards = Readonly<Record<string, SkillCard | undefined>>;

export function skillButtons(hero: UnitView, legal: readonly Action[], cards: SkillCards): SkillButton[] {
  return hero.skills.map((skillId) => {
    const actions = legal.filter((a) => a.type === "use_skill" && a.skill_id === skillId);
    const cooldown = hero.cooldowns[skillId] ?? 0;
    const card = cards[skillId];
    const source = card?.source_cost ?? null;
    let disabledReason: string | null = null;
    if (cooldown > 0) disabledReason = `冷卻中（剩 ${cooldown} 回合）`;
    else if (source !== null && hero.source < source) disabledReason = `源力不足：需要 ${source}，目前 ${hero.source}`;
    else if (actions.length === 0) disabledReason = "目前沒有合法目標（或資源不足）";
    return {
      skillId,
      name: card?.name_zh ?? skillId,
      costs: card === undefined ? [] : card.ap_cost === null ? ["被動／反應", ...card.cost] : [...card.cost],
      cooldown,
      actions,
      disabledReason,
    };
  });
}

// ---- 動作模式 -------------------------------------------------------------

const BASIC_MODES: readonly { kind: Exclude<ModeKind, "skill">; label: string }[] = [
  { kind: "attack", label: "攻擊" },
  { kind: "shove", label: "推擊" },
  { kind: "trip", label: "絆倒" },
  { kind: "interact", label: "推動物件" },
  { kind: "shove_aside", label: "撥開物件" },
  { kind: "defend", label: "防禦" },
  { kind: "end_stance", label: "結束姿態" },
  { kind: "stand", label: "起身" },
];

function modeKindOf(a: Action): ModeKind | null {
  switch (a.type) {
    case "attack":
    case "shove":
    case "trip":
    case "defend":
    case "end_stance":
      return a.type;
    case "interact":
      return a.mode === "shove_aside" ? "shove_aside" : "interact";
    case "move":
      return a.path.length <= 1 ? "stand" : null;
    default:
      return null;
  }
}

/** 基本動作（不含技能）的模式：攻擊、推擊、絆倒、推動物件、防禦、結束姿態、起身。 */
export function basicModes(legal: readonly Action[]): ActionMode[] {
  return BASIC_MODES.flatMap(({ kind, label }) => {
    const actions = legal.filter((a) => modeKindOf(a) === kind);
    if (actions.length === 0) return [];
    // 撥開要選方向（面板上的按鈕），不能靠點物件，所以沒有可點的目標
    const targets = kind === "shove_aside" ? emptyTargets() : buildTargets(actions);
    return [{ key: kind, kind, label, skillId: null, actions, targets }];
  });
}

export function skillMode(button: SkillButton): ActionMode {
  return {
    key: `skill:${button.skillId}`,
    kind: "skill",
    label: button.name,
    skillId: button.skillId,
    actions: button.actions,
    targets: buildTargets(button.actions),
  };
}

// ---- 撥開 -----------------------------------------------------------------

export interface AsideChoice {
  side: "left" | "right";
  /** 例：「往左撥 ←」（箭頭是畫面上物件會移動的方向）。 */
  label: string;
  /** 合法時的動作；不合法時 `null`。 */
  action: Action | null;
  /** 不合法的原因（中文）；合法時 `null`。 */
  reason: string | null;
}

export interface AsideRow {
  objectId: string;
  name: string;
  choices: AsideChoice[];
}

function arrowFor(from: Pos, to: Pos): string {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  if (Math.abs(dx) >= Math.abs(dy)) return dx >= 0 ? DIRECTION_ARROWS.east : DIRECTION_ARROWS.west;
  return dy >= 0 ? DIRECTION_ARROWS.south : DIRECTION_ARROWS.north;
}

/** 撥開面板：每個相鄰的可推動物件一列，左、右兩個選項（不合法的附原因）。 */
export function asideRows(
  options: readonly InteractOption[],
  legal: readonly Action[],
  view: BattleView,
): AsideRow[] {
  const rows = new Map<string, AsideRow>();
  for (const o of options) {
    if (o.mode !== "shove_aside" || (o.side !== "left" && o.side !== "right")) continue;
    const obj = view.objects.find((x) => x.id === o.object_id);
    if (obj === undefined) continue;
    let row = rows.get(o.object_id);
    if (row === undefined) {
      row = { objectId: o.object_id, name: `${objectStyle(obj.kind).name} ${posText(obj.pos)}`, choices: [] };
      rows.set(o.object_id, row);
    }
    const side = o.side;
    const action = legal.find(
      (a) => a.type === "interact" && a.mode === "shove_aside" && a.object_id === o.object_id && a.side === side,
    );
    row.choices.push({
      side,
      label: `往${side === "left" ? "左" : "右"}撥 ${arrowFor(obj.pos, o.to_pos)}`,
      action: o.legal && action !== undefined ? action : null,
      reason: o.legal ? null : (o.reason ?? "不能撥開"),
    });
  }
  return [...rows.values()].map((r) => ({
    ...r,
    choices: [...r.choices].sort((a, b) => (a.side === b.side ? 0 : a.side === "left" ? -1 : 1)),
  }));
}

/** 備援清單：技能與基本模式都沒涵蓋的動作（正常情況為空；不含移動與結束回合）。 */
export function fallbackActions(legal: readonly Action[], hero: UnitView): Action[] {
  return legal.filter((a) => {
    if (a.type === "end_turn" || a.type === "move") return false;
    if (a.type === "use_skill") return !hero.skills.includes(a.skill_id);
    return modeKindOf(a) === null;
  });
}

// ---- 點選 / 滑過 ----------------------------------------------------------

function unitIdsAt(view: BattleView, tile: Pos): string[] {
  const here = view.units.filter((u) => !u.escaped && samePos(u.pos, tile));
  return [...here.filter((u) => !u.downed), ...here.filter((u) => u.downed)].map((u) => u.id);
}

/** 模式下點選／滑過一格 → 對應的動作（單位 > 物件 > 格子 > 相鄰的方向格）。 */
export function actionAtTile(mode: ActionMode, view: BattleView, hero: UnitView, tile: Pos): Action | null {
  const t = mode.targets;
  for (const id of unitIdsAt(view, tile)) {
    const hit = t.units.get(id);
    if (hit !== undefined) return hit;
  }
  for (const o of view.objects) {
    if (!samePos(o.pos, tile)) continue;
    const hit = t.objects.get(o.id);
    if (hit !== undefined) return hit;
  }
  const byTile = t.tiles.get(posKey(tile));
  if (byTile !== undefined) return byTile;
  for (const dir of DIRECTION_ORDER) {
    const d = DIRECTION_DELTA[dir];
    if (hero.pos.x + d.dx === tile.x && hero.pos.y + d.dy === tile.y) {
      const hit = t.directions.get(dir);
      if (hit !== undefined) return hit;
    }
  }
  return null;
}

export interface TargetTiles {
  /** 單位、物件、格子目標的位置。 */
  targets: Pos[];
  /** 方向型：相鄰的方向格。 */
  directions: { pos: Pos; direction: Direction }[];
}

/** 模式的合法目標所在的格子（高亮用）。 */
export function targetTiles(mode: ActionMode, view: BattleView, hero: UnitView): TargetTiles {
  const t = mode.targets;
  const targets: Pos[] = [];
  for (const id of t.units.keys()) {
    const u = view.units.find((x) => x.id === id);
    if (u !== undefined) targets.push(u.pos);
  }
  for (const id of t.objects.keys()) {
    const o = view.objects.find((x) => x.id === id);
    if (o !== undefined) targets.push(o.pos);
  }
  for (const key of t.tiles.keys()) {
    const [x, y] = key.split(",").map(Number);
    if (x !== undefined && y !== undefined) targets.push({ x, y });
  }
  const directions = [...t.directions.keys()].map((direction) => {
    const d = DIRECTION_DELTA[direction];
    return { pos: { x: hero.pos.x + d.dx, y: hero.pos.y + d.dy }, direction };
  });
  return { targets, directions };
}
