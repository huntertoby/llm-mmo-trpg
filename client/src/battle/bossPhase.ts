// Boss 階段（Phase 5F-2）：單位卡的階段行與階段轉換的提示文字（純函式）。
import type { BattleResponse, UnitView } from "../api/types";

/** 單位卡的「階段」：「2/3 鎖霧（HP 30% 以下進入「歸一」）」；沒有階段時 `null`。 */
export function phaseText(unit: UnitView): string | null {
  const phase = unit.boss_phase;
  if (phase == null) return null;
  const head = `${phase.index}/${phase.total} ${phase.name_zh}`;
  if (phase.next_name_zh == null || phase.next_permille == null) return `${head}（最後階段）`;
  return `${head}（HP ${Math.floor(phase.next_permille / 10)}% 以下進入「${phase.next_name_zh}」）`;
}

/** 這次推進中 Boss 進入新階段的戰鬥紀錄文字（依序；沒有時空陣列）。 */
export function phaseNotices(res: Pick<BattleResponse, "steps">): string[] {
  const found: string[] = [];
  for (const step of res.steps) {
    for (const e of step.events) {
      if (e["type"] === "boss_phase_changed" && typeof e["text"] === "string") found.push(e["text"].trim());
    }
  }
  return found;
}
