// 戰鬥紀錄分組（純函式）：把扁平的 `LogLine` 依「行動」分組，每輪、每個單位回合之間加分隔。
//
// - 輪分隔：`round` 改變時插入「第 N 輪」。
// - 回合分隔：`turn_started`（單位回合）與 `environment_started`（環境回合）。
// - 行動：以「行動開始事件」（`LogLine.action`：技能、普攻、步行、衝刺、衝鋒）為標題，其後的結果
//   （擲骰、傷害、治療、狀態、反應……）歸在它底下，直到下一個標題、回合結束或下一個分隔。
// - 沒有標題可掛的行（回合開始時的狀態傷害、環境事件等）各自成一組、沒有子行。
import type { Pos, Team } from "../api/types";
import type { LogLine } from "./log";

export interface LogGroup {
  kind: "group";
  /** 標題行（行動開始事件，或沒有標題可掛的單獨一行）。 */
  head: LogLine;
  children: LogLine[];
  /** 整組牽涉的單位（標題與結果的聯集，去重，依出現順序）。 */
  unitIds: string[];
  tiles: Pos[];
  /** 標題行是否為真正的「行動」；否則只是一般的單獨一行。 */
  isAction: boolean;
}

export interface LogDivider {
  kind: "round" | "turn";
  round: number;
  /** 回合分隔的文字（去掉開頭的破折號）；輪分隔為「第 N 輪」。 */
  text: string;
  team?: Team;
  seq: number;
}

export type LogItem = LogDivider | LogGroup;

const TURN_TYPES = new Set(["turn_started", "environment_started"]);

function newGroup(head: LogLine, isAction: boolean): LogGroup {
  return { kind: "group", head, children: [], unitIds: [...head.unitIds], tiles: [...head.tiles], isAction };
}

function addTo(group: LogGroup, line: LogLine): void {
  group.children.push(line);
  for (const id of line.unitIds) if (!group.unitIds.includes(id)) group.unitIds.push(id);
  group.tiles.push(...line.tiles);
}

function turnText(line: LogLine): string {
  return line.text.replace(/^[—–-]+\s*/, "").replace(/^～\s*|\s*～$/g, "");
}

export function groupLog(lines: readonly LogLine[]): LogItem[] {
  const items: LogItem[] = [];
  let round = 0;
  let open: LogGroup | null = null;
  for (const line of lines) {
    if (line.round !== round) {
      round = line.round;
      open = null;
      items.push({ kind: "round", round, text: `第 ${round} 輪`, seq: line.seq });
    }
    if (TURN_TYPES.has(line.type)) {
      open = null;
      const turn: LogDivider = { kind: "turn", round, text: turnText(line), seq: line.seq };
      if (line.team !== undefined) turn.team = line.team;
      items.push(turn);
    } else if (line.action === true) {
      open = newGroup(line, true);
      items.push(open);
    } else if (open !== null && line.type !== "turn_ended") {
      addTo(open, line);
    } else {
      open = null;
      items.push(newGroup(line, false));
    }
  }
  return items;
}
