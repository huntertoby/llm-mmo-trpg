// 技能列與目標選取（純函式）：合法動作 → 「模式」（技能、攻擊、推擊……）→ 每個模式的合法目標。
import type { Action, BattleView, Direction, InteractOption, Pending, Pos, SkillCard, UnitView } from "../api/types";
import { buildComposite, compositePrompt, firstKeyAt, firstPos, secondAt, secondTiles, soleCenter, type CompositeSet } from "./composite";
import { posKey, samePos } from "./geometry";
import { activeReason } from "./activations";
import { grantedRemaining } from "./granted";
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
  /**
   * 兩段選取（投擲物件、傳送他人、任意兩者互換）：第 1 段選的 ID（物件或單位）→（第 2 段 → 動作）。
   * 投擲與傳送的第 2 段是落點 "x,y"；互換的第 2 段是另一個單位的 ID（兩個方向都登記）。
   */
  hurls: Map<string, Map<string, Action>>;
  /** 兩段選取的種類（沒有兩段選取時 `null`）。 */
  pairKind: PairKind | null;
  /** 複合技能（位移 → 動作，Phase 3F-3b）的兩段選取；`hurls` 以同樣的鍵登記，讓「兩段選取」的流程共用。 */
  composite: CompositeSet | null;
}

export type PairKind = "hurl" | "teleport" | "swap" | "shadowstep" | "composite";

export type ModeKind = "skill" | "attack" | "shove" | "trip" | "interact" | "shove_aside" | "defend" | "end_stance" | "stand";

export interface ActionMode {
  /** 選取用的鍵：技能為 `skill:<id>`，其他為類型。 */
  key: string;
  kind: ModeKind;
  label: string;
  skillId: string | null;
  actions: Action[];
  targets: TargetSet;
  /**
   * 推動物件（Phase 3-10）：相鄰物件推不動的原因（物件 ID → 完整說明）；選取模式中點到時顯示。
   * 沒有不合法的物件時省略。
   */
  blockedObjects?: ReadonlyMap<string, string>;
  /** 全部都不合法時的原因：按鈕灰色，滑過或點擊顯示（有值 ＝ 不能選取）。 */
  blockedReason?: string;
}

export function emptyTargets(): TargetSet {
  return {
    self: null,
    units: new Map(),
    objects: new Map(),
    tiles: new Map(),
    directions: new Map(),
    hurls: new Map(),
    pairKind: null,
    composite: null,
  };
}

function setOnce<K>(map: Map<K, Action>, key: K, action: Action): void {
  if (!map.has(key)) map.set(key, action);
}

function addPair(t: TargetSet, kind: PairKind, first: string, second: string, action: Action): void {
  t.pairKind = kind;
  let seconds = t.hurls.get(first);
  if (seconds === undefined) {
    seconds = new Map();
    t.hurls.set(first, seconds);
  }
  setOnce(seconds, second, action);
}

/** 兩段選取的動作登記到它的第 1 段與第 2 段；不是兩段選取時回傳 `false`。 */
function addTwoStage(t: TargetSet, action: Extract<Action, { type: "use_skill" }>): boolean {
  if (action.target_object_id != null && action.target_pos != null) {
    addPair(t, "hurl", action.target_object_id, posKey(action.target_pos), action); // 投擲物件：物件 → 落點
    return true;
  }
  if (action.target_id != null && action.second_target_id != null) {
    // 任意兩者互換：伺服器每組只列一次，兩個方向都登記，玩家先點哪一個都行
    addPair(t, "swap", action.target_id, action.second_target_id, action);
    addPair(t, "swap", action.second_target_id, action.target_id, action);
    return true;
  }
  if (action.target_id != null && action.target_pos != null) {
    addPair(t, "teleport", action.target_id, posKey(action.target_pos), action); // 傳送他人：單位 → 落點
    return true;
  }
  return false;
}

/** 把一個動作登記到它的目標（兩段選取（物件＋落點、單位＋落點、單位＋單位）> 單位 > 物件 > 格子 > 方向 > 自身；同一目標取第一個）。 */
function addTarget(t: TargetSet, action: Action): void {
  switch (action.type) {
    case "use_skill":
    case "attack": {
      if (action.type === "use_skill" && addTwoStage(t, action)) return;
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
  return t.units.size + t.objects.size + t.tiles.size + t.directions.size + t.hurls.size;
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
  /** 暫時獲得的技能（Phase 3D-8c）：剩餘輪數；裝備的技能為 `null`。 */
  grantedRemaining?: number | null;
  /** 效果原語的代碼（Phase 3D-8d；分辨一般瞬步與傳送他人）；卡片還沒取得時為空。 */
  effectIds?: readonly string[];
  /** 複合技能（位移 → 動作，Phase 3F-3b）：有第二段。 */
  composite?: boolean;
}

export type SkillCards = Readonly<Record<string, SkillCard | undefined>>;

/** 本地端猜不出原因時的通用說明；伺服器的 `skill-reasons` 有原因時會取代它（Phase 3-5c-2）。 */
export const GENERIC_REASON = "目前沒有合法目標（或資源不足）";

export function skillButtons(hero: UnitView, legal: readonly Action[], cards: SkillCards): SkillButton[] {
  const granted = (hero.granted_skills ?? []).map((g) => g.skill_id).filter((id) => !hero.skills.includes(id));
  return [...hero.skills, ...granted].map((skillId) => {
    const actions = legal.filter((a) => a.type === "use_skill" && a.skill_id === skillId);
    const cooldown = hero.cooldowns[skillId] ?? 0;
    const card = cards[skillId];
    const source = card?.source_cost ?? null;
    let disabledReason: string | null = null;
    const active = activeReason(hero, skillId);
    if (active !== null) disabledReason = active;
    else if (cooldown > 0) disabledReason = `冷卻中（剩 ${cooldown} 回合）`;
    else if (source !== null && hero.source < source) disabledReason = `源力不足：需要 ${source}，目前 ${hero.source}`;
    else if (actions.length === 0) disabledReason = GENERIC_REASON;
    return {
      skillId,
      name: card?.name_zh ?? skillId,
      costs:
        card === undefined
          ? []
          : card.ap_cost === null
            ? ["被動／反應", ...card.cost]
            : [...card.cost, ...((card.activation_id ?? null) === null ? [] : ["傳說啟動"])],
      cooldown,
      actions,
      disabledReason,
      grantedRemaining: grantedRemaining(hero, skillId),
      effectIds: card?.effect_ids ?? [],
      // 只有「位移 → 動作」用兩段選取（Phase 3F-3b）；其他種類（3F-4a／4b）照第一段選取，
      // 第二段在結算時暫停詢問或自動結算（延遲段：之後才釋放）
      composite: (card?.followup ?? null) !== null && (card?.followup_when ?? "after_move") === "after_move",
    };
  });
}

// ---- 動作模式 -------------------------------------------------------------

export const BASIC_MODES: readonly { kind: Exclude<ModeKind, "skill">; label: string }[] = [
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

/** 複合技能：位移段選取（落點格或目標單位）→ 動作段選取（方向、目標、或以落點為中心）。 */
function compositeTargets(actions: readonly Action[]): TargetSet {
  const t = emptyTargets();
  const set = buildComposite(actions);
  t.pairKind = "composite";
  t.composite = set;
  for (const [key, first] of set) {
    t.hurls.set(key, new Map(first.seconds.map((s) => [s.key, s.action])));
  }
  return t;
}

export function skillMode(button: SkillButton): ActionMode {
  if (button.composite === true) {
    return {
      key: `skill:${button.skillId}`,
      kind: "skill",
      label: button.name,
      skillId: button.skillId,
      actions: button.actions,
      targets: compositeTargets(button.actions),
    };
  }
  const targets = buildTargets(button.actions);
  // 一般瞬步（Phase 3D-8d）和傳送他人一樣是「單位 → 落點」，只是第 1 段是敵人、第 2 段是他身旁的格子
  if (targets.pairKind === "teleport" && (button.effectIds ?? []).includes("shadowstep")) {
    targets.pairKind = "shadowstep";
  }
  return {
    key: `skill:${button.skillId}`,
    kind: "skill",
    label: button.name,
    skillId: button.skillId,
    actions: button.actions,
    targets,
  };
}

// ---- 複製技能的第二段選取 ----------------------------------------------------

/** 這個詢問是不是複製技能（`copy_skill`）的選目標。 */
export function isCopyPending(pending: Pending | null): pending is Pending {
  return pending !== null && pending.kind === "copy_skill";
}

/**
 * 複製技能暫停時的第二段選取：伺服器給的 `copy_options`（複製技能目前所有合法的選取）當成一個
 * 模式，點到目標就把那個選取連同「接受」送回 `/decision`。
 */
export function copyMode(pending: Pending, options: readonly Action[], skillName: string): ActionMode {
  return {
    key: `copy:${pending.copy_skill_id ?? ""}`,
    kind: "skill",
    label: skillName,
    skillId: pending.copy_skill_id ?? null,
    actions: [...options],
    targets: buildTargets(options),
  };
}

/** 第二段選取的提示文字。 */
export function copyPromptText(skillName: string, optionCount: number): string {
  if (optionCount === 0) return `目前沒有「${skillName}」的合法目標，請放棄這次施放。`;
  return `要複製「${skillName}」：在戰場上點選高亮的目標（共 ${optionCount} 個可選），或放棄施放。`;
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

/** 物件會移動的方向箭頭；會被推出地圖邊緣（沒有目的格）時依「主角 → 物件」方向以外無從得知，回傳空字串。 */
function arrowFor(from: Pos, to: Pos | null): string {
  if (to === null) return "";
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
      label: `往${side === "left" ? "左" : "右"}撥 ${arrowFor(obj.pos, o.to_pos)}`.trimEnd(),
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
  const here = view.units.filter((u) => !u.escaped && !u.dismissed && samePos(u.pos, tile));
  return [...here.filter((u) => !u.downed), ...here.filter((u) => u.downed)].map((u) => u.id);
}

// ---- 兩段選取（投擲物件、傳送他人、任意兩者互換）-------------------------------------

/** 這個模式是兩段選取（先選物件或單位、再選落點或第二個單位）。 */
export function isHurlMode(mode: ActionMode): boolean {
  return mode.targets.hurls.size > 0;
}

/** 第一段：`tile` 上可以選的物件或單位 ID（沒有時 `null`）。 */
export function hurlObjectAt(mode: ActionMode, view: BattleView, tile: Pos): string | null {
  const set = mode.targets.composite;
  if (set !== null) {
    const key = firstKeyAt(set, view, tile);
    const first = key === null ? undefined : set.get(key);
    return first !== undefined && soleCenter(first) === null ? first.key : null; // 只有「以落點為中心」的直接施放，不用選
  }
  for (const o of view.objects) {
    if (samePos(o.pos, tile) && mode.targets.hurls.has(o.id)) return o.id;
  }
  for (const id of unitIdsAt(view, tile)) {
    if (mode.targets.hurls.has(id)) return id;
  }
  return null;
}

/**
 * 第二段：選了 `pick` 之後，`tile` 對應的動作（不是合法的第二段時 `null`）。
 * 互換的第二段是另一個單位，要用 `view` 找出 `tile` 上的單位。
 */
export function hurlActionAt(mode: ActionMode, pick: string | null, tile: Pos, view?: BattleView): Action | null {
  const set = mode.targets.composite;
  if (set !== null) {
    if (pick === null) {
      // 只有「以落點為中心」的複合技能：滑過／點落點就是施放（view 用來找目標單位）
      const key = view === undefined ? null : firstKeyAt(set, view, tile);
      const only = key === null ? undefined : set.get(key);
      return (only === undefined ? null : soleCenter(only))?.action ?? null;
    }
    const first = set.get(pick);
    if (first === undefined || view === undefined) return null;
    return secondAt(first, view, tile)?.action ?? null;
  }
  if (pick === null) return null;
  const seconds = mode.targets.hurls.get(pick);
  if (seconds === undefined) return null;
  if (mode.targets.pairKind !== "swap") return seconds.get(posKey(tile)) ?? null;
  if (view === undefined) return null;
  for (const id of unitIdsAt(view, tile)) {
    const hit = seconds.get(id);
    if (hit !== undefined) return hit;
  }
  return null;
}

/** 第二段的合法格子（依伺服器列出的順序）；互換是另一個單位所在的格子。 */
export function hurlLandings(mode: ActionMode, pick: string | null, view?: BattleView): Pos[] {
  if (pick === null) return [];
  const set = mode.targets.composite;
  if (set !== null) {
    const first = set.get(pick);
    if (first === undefined || view === undefined) return [];
    const tiles = secondTiles(first, view);
    return [...tiles.targets, ...tiles.directions.map((d) => d.pos)];
  }
  const keys = [...(mode.targets.hurls.get(pick)?.keys() ?? [])];
  if (mode.targets.pairKind === "swap") {
    return keys.flatMap((id) => {
      const u = view?.units.find((x) => x.id === id);
      return u === undefined ? [] : [u.pos];
    });
  }
  return keys.map((key) => {
    const [x, y] = key.split(",").map(Number);
    return { x: x as number, y: y as number };
  });
}

/** 兩段選取的提示文字。 */
export function hurlPromptText(
  pickName: string | null,
  secondCount: number,
  firstCount: number,
  kind: PairKind = "hurl",
): string {
  const first = {
    hurl: "要舉起的物件",
    teleport: "要傳送的單位",
    swap: "要互換的第一個單位",
    shadowstep: "要瞬步過去的敵人",
    composite: "位移的落點或目標",
  }[kind];
  const second = {
    hurl: "落點",
    teleport: "落點（致命地形的成功率極低，Boss 不能選）",
    swap: "第二個單位",
    shadowstep: "要落在他身旁哪一格（落在他背後可以背刺）",
    composite: "動作段的方向或目標",
  }[kind];
  const verb = { hurl: "已舉起", teleport: "已選定", swap: "已選定", shadowstep: "已鎖定", composite: "已選定" }[kind];
  if (pickName === null) return `第 1 段：點選${first}（紅框 ${firstCount} 個）。Esc／右鍵取消。`;
  const redo = kind === "swap" ? "點同一個單位或按「重選單位」可以改選" : "再點其他目標可改選，點同一個取消";
  return `第 2 段：${verb}${pickName}，點選${second}（紅框 ${secondCount} 個）；${redo}。`;
}

/**
 * 模式下點選／滑過一格 → 對應的動作（單位 > 物件 > 格子 > 相鄰的方向格）。
 * 投擲物件的模式要先選物件（`hurlPick`），選好之前沒有動作；選好之後只有合法落點有動作。
 */
export function actionAtTile(
  mode: ActionMode,
  view: BattleView,
  hero: UnitView,
  tile: Pos,
  hurlPick: string | null = null,
): Action | null {
  const t = mode.targets;
  if (t.hurls.size > 0) return hurlActionAt(mode, hurlPick, tile, view);
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

/** 模式的合法目標所在的格子（高亮用）；兩段選取第一段是可選的物件或單位、第二段是合法落點或單位。 */
export function targetTiles(
  mode: ActionMode,
  view: BattleView,
  hero: UnitView,
  hurlPick: string | null = null,
): TargetTiles {
  const t = mode.targets;
  const targets: Pos[] = [];
  if (t.hurls.size > 0) {
    if (t.composite !== null) {
      const picked = hurlPick === null ? undefined : t.composite.get(hurlPick);
      if (picked !== undefined) return secondTiles(picked, view);
      for (const first of t.composite.values()) {
        const at = firstPos(first, view);
        if (at !== null) targets.push(at);
      }
      return { targets, directions: [] };
    }
    if (hurlPick !== null) return { targets: hurlLandings(mode, hurlPick, view), directions: [] };
    for (const id of t.hurls.keys()) {
      const at = view.objects.find((x) => x.id === id)?.pos ?? view.units.find((x) => x.id === id)?.pos;
      if (at !== undefined) targets.push(at);
    }
    return { targets, directions: [] };
  }
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

/** 兩段選取第一段已選好的物件或單位（或複合技能的落點）所在格（青色粗框）。 */
export function hurlPickPos(mode: ActionMode, view: BattleView, pick: string | null): Pos | undefined {
  if (pick === null) return undefined;
  const first = mode.targets.composite?.get(pick);
  if (first !== undefined) return firstPos(first, view) ?? undefined;
  return view.objects.find((o) => o.id === pick)?.pos ?? view.units.find((u) => u.id === pick)?.pos;
}

/** 複合技能兩段選取的提示（第 1 段：選落點或目標；第 2 段：選方向或目標）。 */
export function compositePromptFor(mode: ActionMode, pick: string | null): string {
  const set = mode.targets.composite;
  return compositePrompt(pick === null ? null : (set?.get(pick) ?? null), set?.size ?? 0);
}
