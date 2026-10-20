// 戰鬥紀錄彙總（純函式）：事件的中文 `text` 逐行列出；同一單位連續的步行（`unit_moved`、
// `mode == "walk"`，伺服器不給 `text`）合併成一行「X 從 (a) 移動到 (b)」。
import { asEvent, isUnitMoved, type EventBase, type Pos, type StepOut, type Team } from "../api/types";
import { samePos } from "./geometry";
import type { UnitNames } from "./units";

/** 結果行的語意（決定符號與顏色）；沒有的為 `undefined`。 */
export type LogTone = "damage" | "heal" | "shield" | "status" | "down" | "hit" | "miss";

export interface LogLine {
  /** 第一個事件的 `seq`（React key 用；彙總的步行取第一步）。 */
  seq: number;
  round: number;
  /** 完整文字（現有的中文描述，完整保留）。 */
  text: string;
  /** 事件型別（步行彙總為 `unit_moved`）；分組用。 */
  type: string;
  /** 精簡版文字（擲骰與修正細節已拿掉）；沒有細節時為 `undefined`，顯示 `text`。 */
  summary?: string;
  tone?: LogTone;
  /** 是否為「行動開始」事件（技能、普攻、步行、衝刺、衝鋒）；分組時當標題。 */
  action?: true;
  /** 這一行主要說的單位的陣營（顏色用）；不明為 `undefined`。 */
  team?: Team;
  /** 事件牽涉的單位（滑過高亮用）。 */
  unitIds: string[];
  /** 事件直接指出的格子（滑過高亮用；單位目前所在格由畫面依單位補上）。 */
  tiles: Pos[];
}

// ---- 事件 → 行的中繼資料 ------------------------------------------------------------
const SUBJECT_KEYS = ["unit_id", "attacker_id", "source_id", "target_id"] as const;
const TARGET_FIRST_KEYS = ["target_id", "unit_id", "attacker_id", "source_id"] as const;
/** 這些事件說的是「被作用的單位」，顏色與主詞以目標為準。 */
const TARGET_FIRST = new Set([
  "damage_dealt",
  "healed",
  "status_applied",
  "status_removed",
  "status_resisted",
  "status_save_rolled",
  "status_converted",
]);
/** 擲骰類事件：精簡成「主詞 → 結果」，完整擲骰與修正放進細節。 */
const ROLL_TYPES = new Set(["attack_rolled", "status_save_rolled", "check_rolled", "maneuver_rolled"]);
const BRACKETS = /［[^］]*］|（[^）]*）/g;

function isPos(v: unknown): v is Pos {
  if (typeof v !== "object" || v === null) return false;
  const o = v as { x?: unknown; y?: unknown };
  return typeof o.x === "number" && typeof o.y === "number";
}

function eventTiles(event: EventBase): Pos[] {
  const tiles: Pos[] = [];
  for (const key of ["pos", "from_pos", "to_pos"]) {
    const v = event[key];
    if (isPos(v)) tiles.push(v);
  }
  const list = event["tiles"];
  if (Array.isArray(list)) tiles.push(...list.filter(isPos));
  return tiles;
}

function eventUnits(event: EventBase, names: UnitNames): string[] {
  const ids: string[] = [];
  for (const [key, v] of Object.entries(event)) {
    if (key.endsWith("_id") && typeof v === "string" && names.team(v) !== undefined && !ids.includes(v)) ids.push(v);
  }
  return ids;
}

function eventTeam(event: EventBase, names: UnitNames): Team | undefined {
  const keys = TARGET_FIRST.has(event.type) ? TARGET_FIRST_KEYS : SUBJECT_KEYS;
  for (const key of keys) {
    const v = event[key];
    const team = typeof v === "string" ? names.team(v) : undefined;
    if (team !== undefined) return team;
  }
  return undefined;
}

function eventTone(event: EventBase): LogTone | undefined {
  switch (event.type) {
    case "damage_dealt":
    case "object_damaged":
    case "bomb_exploded":
      return "damage";
    case "healed":
      return "heal";
    case "shield_gained":
    case "shield_absorbed":
      return "shield";
    case "status_applied":
      return "status";
    case "unit_downed":
      return "down";
    case "attack_rolled":
      return event["hit"] === true ? "hit" : "miss";
    default:
      return undefined;
  }
}

/** 擲骰與修正細節：精簡文字（完整文字另外保留）；沒有可拿掉的細節時回傳 `undefined`。 */
export function summarize(type: string, text: string): string | undefined {
  if (ROLL_TYPES.has(type)) {
    const colon = text.indexOf("：");
    if (colon < 0) return undefined;
    const head = text.slice(0, colon).replace(BRACKETS, "").trim();
    const verdict = /→\s*([^→]+)$/.exec(text)?.[1]?.trim();
    return verdict === undefined ? head : `${head} → ${verdict}`;
  }
  if (type === "initiative_rolled") {
    const m = /^(.*?)\s+d20=.*=\s*(-?\d+)$/.exec(text);
    return m === null ? undefined : `${m[1]} ${m[2]}`;
  }
  if (type === "damage_dealt" || type === "healed") {
    const short = text.replace(BRACKETS, "").replace(/\s+/g, " ").replace(/\s+，/g, "，").trim();
    return short === text ? undefined : short;
  }
  return undefined;
}

/** 行動開始事件：技能施放、普攻（沒有技能的命中判定）、衝刺、衝鋒。 */
function startsAction(event: EventBase): boolean {
  switch (event.type) {
    case "skill_used":
    case "unit_dashed":
    case "unit_charged":
      return true;
    case "attack_rolled":
      return event["skill_id"] === null || event["skill_id"] === undefined;
    default:
      return false;
  }
}

function makeLine(event: EventBase, text: string, names: UnitNames): LogLine {
  const summary = summarize(event.type, text);
  const line: LogLine = {
    seq: event.seq,
    round: event.round,
    text,
    type: event.type,
    unitIds: eventUnits(event, names),
    tiles: eventTiles(event),
  };
  if (summary !== undefined && summary !== text) line.summary = summary;
  if (startsAction(event)) line.action = true;
  const tone = eventTone(event);
  if (tone !== undefined) line.tone = tone;
  const team = eventTeam(event, names);
  if (team !== undefined) line.team = team;
  return line;
}

interface WalkRun {
  unitId: string;
  start: Pos;
  end: Pos;
  cost: number;
  seq: number;
  round: number;
}

function walkText(run: WalkRun, names: UnitNames): string {
  return (
    `${names.label(run.unitId)} 從 (${run.start.x}, ${run.start.y}) ` +
    `移動到 (${run.end.x}, ${run.end.y})（消耗 ${run.cost} 移動）`
  );
}

/** 戰鬥紀錄只需要每一步的事件（`/history` 沒有戰場視圖）。 */
export type LogStep = Pick<StepOut, "events">;

export function logLines(steps: readonly LogStep[], names: UnitNames): LogLine[] {
  const lines: LogLine[] = [];
  const pending: { walk: WalkRun | null } = { walk: null };
  const flush = () => {
    const run = pending.walk;
    if (run !== null) {
      const line: LogLine = {
        seq: run.seq,
        round: run.round,
        text: walkText(run, names),
        type: "unit_moved",
        action: true,
        unitIds: [run.unitId],
        tiles: [run.start, run.end],
      };
      const team = names.team(run.unitId);
      if (team !== undefined) line.team = team;
      lines.push(line);
    }
    pending.walk = null;
  };
  for (const step of steps) {
    for (const raw of step.events) {
      const event = asEvent(raw);
      if (isUnitMoved(event) && event.mode === "walk" && event.text === undefined) {
        const run = pending.walk;
        if (run !== null && run.unitId === event.unit_id && samePos(run.end, event.from_pos)) {
          run.end = event.to_pos;
          run.cost += event.cost;
        } else {
          flush();
          pending.walk = {
            unitId: event.unit_id,
            start: event.from_pos,
            end: event.to_pos,
            cost: event.cost,
            seq: event.seq,
            round: event.round,
          };
        }
        continue;
      }
      if (event.text === undefined) continue;
      flush();
      lines.push(makeLine(event, event.text.trim(), names));
    }
  }
  flush();
  return lines;
}
