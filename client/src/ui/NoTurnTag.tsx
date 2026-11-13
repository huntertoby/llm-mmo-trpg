// 「背刺・無聲（不會轉身）」「隱蔽出手（不會轉身）」的小標籤（BS-2；字在 `battle/noTurn.ts`）。
// 戰鬥紀錄的精簡行與浮動提示用；`hint` 為真時滑過看說明卡（浮動提示不互動，不掛說明卡）。
import { NO_TURN_HINT_ZH, noTurnLabel, type NoTurnKind } from "../battle/noTurn";
import { Hint } from "./Hint";

export function NoTurnTag({ kind, backstab, hint = true }: { kind: NoTurnKind; backstab: boolean; hint?: boolean }) {
  const tag = (
    <span className="no-turn-tag log-no-turn" data-no-turn={kind} data-testid="no-turn-tag" tabIndex={hint ? 0 : undefined}>
      {noTurnLabel(kind, backstab)}
    </span>
  );
  return hint ? <Hint text={NO_TURN_HINT_ZH[kind]}>{tag}</Hint> : tag;
}
