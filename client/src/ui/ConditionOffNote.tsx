// 說明卡第一行「本場不成立：…」（LW-2；`battle/conditionOff.ts`）。技能列的浮動卡（主動技與被動小圖示）共用；
// 之後別的地方要畫同一句（BS-2 的武器條件）也用這個，不要各自拼字。
import { conditionOffLine, type ConditionOffMark } from "../battle/conditionOff";

export function ConditionOffNote({ mark }: { mark: ConditionOffMark | null | undefined }) {
  if (mark == null) return null;
  return (
    <div className="skill-card-reason cond-off-note" data-testid="cond-off-note">
      {conditionOffLine(mark)}
    </div>
  );
}
