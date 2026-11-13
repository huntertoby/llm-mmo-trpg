// 說明卡第一行「本場不成立：…」（LW-2；`battle/conditionOff.ts`）。技能列的浮動卡（主動技與被動小圖示）共用；
// 之後別的地方要畫同一句（BS-2 的武器條件）也用這個，不要各自拼字。
import { conditionOffLine, type ConditionOffMark } from "../battle/conditionOff";

/** 說明卡第一行「現在不能用：…」（LW-2b，移植需求 3.7 第 2 條）：和「本場不成立」同一個深藍底，框改琥珀實線、
 *  「現在不能用」四個字琥珀粗體。同一張卡兩條都有時，這一條在上（呼叫端先放這個、再放 `ConditionOffNote`）。 */
export function NowOffNote({ reason }: { reason: string | null | undefined }) {
  if (reason == null) return null;
  return (
    <div className="skill-card-reason now-off-note" data-testid="now-off-note">
      <b>現在不能用</b>：{reason}
    </div>
  );
}

export function ConditionOffNote({ mark }: { mark: ConditionOffMark | null | undefined }) {
  if (mark == null) return null;
  return (
    <div className="skill-card-reason cond-off-note" data-testid="cond-off-note">
      {conditionOffLine(mark)}
    </div>
  );
}
