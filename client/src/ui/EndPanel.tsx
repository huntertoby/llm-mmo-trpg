// 戰鬥結束：勝負、戰後結算（大世界：經驗、戰利品、任務進度，6F-1）、再來一場、下載戰鬥紀錄。
// 重播指令只在開發模式（`?dev=1`）顯示。
import { useEffect } from "react";
import { logUrl } from "../api/client";
import { play } from "../audio";
import type { BattleResponse } from "../api/types";
import { END_REASONS } from "../battle/glossary";
import { endDetail } from "../battle/objective";
import { isDevMode } from "../run/startFlow";

/** 戰後結算（大世界，6F-1）：`null` ＝ 還在讀（顯示「結算中」），`lines` 是伺服器給的句子。 */
export interface EndSummary {
  lines: readonly string[];
  /** 最後一行的說明（例如「HP 要到城鎮或營火才會回」）；沒有為 `null`。 */
  note: string | null;
}

interface Props {
  response: BattleResponse;
  onRestart(): void;
  /** 主按鈕文字；省略為「再來一場」。 */
  restartLabel?: string;
  /** 取代「勝利！／敗北……」的中性勝負文字（循環賽重播「某某 勝」，5F-4b）；省略照我方視角。 */
  heading?: string;
  /** 戰後結算（6F-1）：`undefined` ＝ 不顯示（一輪、單場戰鬥）；`null` ＝ 結算中。 */
  summary?: EndSummary | null;
  /** 開發模式（顯示重播指令）；省略時看網址的 `?dev=1`。 */
  dev?: boolean;
}

function SummaryBlock({ summary }: { summary: EndSummary | null }) {
  if (summary === null) {
    return (
      <div className="end-summary muted small" data-testid="end-summary">
        結算中……
      </div>
    );
  }
  // 說明（HP 不會自動回）放在捲動區外，句子再多也看得到
  return (
    <>
      {summary.lines.length > 0 && (
        <div className="end-summary small" data-testid="end-summary">
          <ul>
            {summary.lines.map((line, i) => (
              <li key={`${i}-${line}`}>{line}</li>
            ))}
          </ul>
        </div>
      )}
      {summary.note !== null && (
        <div className="end-summary-note small" data-testid="end-summary-note">
          {summary.note}
        </div>
      )}
    </>
  );
}

export function outcomeText(response: BattleResponse, title?: string): string {
  if (response.awaiting === "stalled") return "戰鬥中止（自動推進超過上限）";
  const o = response.outcome;
  if (o === null) return title ?? "戰鬥結束";
  let head = "平手";
  if (o.winner === "ally") head = "勝利！";
  else if (o.winner === "enemy") head = "敗北……";
  if (title !== undefined) head = title;
  const reason = o.end_reason === null ? "" : `（${END_REASONS[o.end_reason] ?? o.end_reason}）`;
  return `${head}${reason}・第 ${o.round} 輪`;
}

export function EndPanel({ response, onRestart, restartLabel = "再來一場", heading, summary, dev }: Props) {
  const detail = endDetail(response.outcome?.end_reason ?? null);
  const showDev = dev ?? (typeof window !== "undefined" && isDevMode(window.location.search));
  // AU-3：勝利短樂句（合成鐘琴暫代）接在結算畫面出現的那一刻
  const won = response.outcome?.winner === "ally";
  useEffect(() => {
    if (won) play("res_victory");
  }, [won, response.battle_id]);
  return (
    <div className="panel end-panel">
      <div className="end-title">{outcomeText(response, heading)}</div>
      {detail !== null && <div className="end-detail">{detail}</div>}
      {summary !== undefined && <SummaryBlock summary={summary} />}
      <div className="end-buttons">
        <button type="button" className="primary" onClick={onRestart}>
          {restartLabel}
        </button>
        <a
          className="button"
          href={logUrl(response.battle_id)}
          download={`battle-${response.battle_id}.json`}
        >
          下載戰鬥紀錄
        </a>
      </div>
      {showDev && (
        <div className="muted small" data-testid="end-dev-replay">
          紀錄可用 <code>uv run trpg battle replay 檔案</code> 重播驗證。
        </div>
      )}
    </div>
  );
}
