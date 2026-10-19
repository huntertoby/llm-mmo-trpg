// 戰鬥結束：勝負、再來一場、下載戰鬥紀錄。
import { logUrl } from "../api/client";
import type { BattleResponse } from "../api/types";
import { END_REASONS } from "../battle/glossary";

interface Props {
  response: BattleResponse;
  onRestart(): void;
}

export function outcomeText(response: BattleResponse): string {
  if (response.awaiting === "stalled") return "戰鬥中止（自動推進超過上限）";
  const o = response.outcome;
  if (o === null) return "戰鬥結束";
  let head = "平手";
  if (o.winner === "ally") head = "勝利！";
  else if (o.winner === "enemy") head = "敗北……";
  const reason = o.end_reason === null ? "" : `（${END_REASONS[o.end_reason] ?? o.end_reason}）`;
  return `${head}${reason}・第 ${o.round} 輪`;
}

export function EndPanel({ response, onRestart }: Props) {
  return (
    <div className="panel end-panel">
      <div className="end-title">{outcomeText(response)}</div>
      <div className="end-buttons">
        <button type="button" className="primary" onClick={onRestart}>
          再來一場
        </button>
        <a
          className="button"
          href={logUrl(response.battle_id)}
          download={`battle-${response.battle_id}.json`}
        >
          下載戰鬥紀錄
        </a>
      </div>
      <div className="muted small">
        紀錄可用 <code>uv run trpg battle replay 檔案</code> 重播驗證。
      </div>
    </div>
  );
}
