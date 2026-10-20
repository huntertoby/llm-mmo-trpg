// 戰鬥紀錄彙總（純函式）：事件的中文 `text` 逐行列出；同一單位連續的步行（`unit_moved`、
// `mode == "walk"`，伺服器不給 `text`）合併成一行「X 從 (a) 移動到 (b)」。
import { asEvent, isUnitMoved, type Pos, type StepOut } from "../api/types";
import { samePos } from "./geometry";
import type { UnitNames } from "./units";

export interface LogLine {
  /** 第一個事件的 `seq`（React key 用；彙總的步行取第一步）。 */
  seq: number;
  round: number;
  text: string;
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
    if (run !== null) lines.push({ seq: run.seq, round: run.round, text: walkText(run, names) });
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
      lines.push({ seq: event.seq, round: event.round, text: event.text.trim() });
    }
  }
  flush();
  return lines;
}
