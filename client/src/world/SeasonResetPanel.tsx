// 季末重置的管理者介面（Phase 5F-5）：填開賽日 → 預覽（dry-run：會清什麼、留什麼、編年史文字）→
// 輸入目前季 ID 確認後執行。權限由伺服器檢查（管理者，或開發模式沒登入）。
import { useState } from "react";
import { api } from "../api/client";
import type { SeasonResetReport } from "../api/types";
import { canExecute, resetBody, resetLineText, startDateProblem } from "./season";

interface Props {
  onDone(): void;
}

export function SeasonResetPanel({ onDone }: Props) {
  const [date, setDate] = useState("");
  const [force, setForce] = useState(false);
  const [confirm, setConfirm] = useState("");
  const [preview, setPreview] = useState<SeasonResetReport | null>(null);
  const [previewedFor, setPreviewedFor] = useState<string | null>(null);
  const [done, setDone] = useState<SeasonResetReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const problem = startDateProblem(date);
  const key = `${date.trim()}|${force ? 1 : 0}`;

  async function run(execute: boolean) {
    setBusy(true);
    setError(null);
    try {
      const report = await api.seasonReset(resetBody(date, force, execute ? confirm : null));
      if (execute) {
        setDone(report);
        setPreview(null);
        setConfirm("");
        onDone();
      } else {
        setPreview(report);
        setPreviewedFor(key);
        setDone(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const shown = done ?? preview;
  return (
    <div className="panel" data-testid="season-reset">
      <div className="section-title">季末重置（管理者）</div>
      <div className="muted small">先預覽：只列出會清掉與保留的東西，不寫任何檔。執行前會把整個存檔資料夾備份起來。</div>
      <div className="run-actions">
        <label>
          新一季開賽日
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            disabled={busy}
            data-testid="season-reset-date"
          />
        </label>
        <label className="small">
          <input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} disabled={busy} />
          賽季還沒結束也重置
        </label>
        <button type="button" onClick={() => void run(false)} disabled={busy || problem !== null} data-testid="season-reset-preview">
          預覽
        </button>
      </div>
      {date !== "" && problem !== null && <div className="error-text small">{problem}</div>}
      {error !== null && (
        <div className="error-text small" data-testid="season-reset-error">
          {error}
        </div>
      )}
      {shown !== null && (
        <div className="small" data-testid="season-reset-report">
          <div>
            <b>{shown.dry_run ? "預覽" : "已重置"}</b>：{shown.old_season} → {shown.new_season}（{shown.new_season_name_zh}）
          </div>
          {shown.warnings.map((w) => (
            <div key={w} className="error-text">
              已略過：{w}
            </div>
          ))}
          <div>{shown.dry_run ? "會清掉" : "清掉了"}：</div>
          <ul>
            {shown.cleared.map((l) => (
              <li key={l.label_zh}>{resetLineText(l)}</li>
            ))}
          </ul>
          <div>保留：</div>
          <ul>
            {shown.kept.map((l) => (
              <li key={l.label_zh}>{resetLineText(l)}</li>
            ))}
          </ul>
          {shown.chronicle.length > 0 && (
            <>
              <div>寫進編年史：</div>
              <ul>
                {shown.chronicle.map((t, i) => (
                  <li key={`c${i}`}>{t}</li>
                ))}
              </ul>
            </>
          )}
          {shown.backup !== null && shown.backup !== undefined && <div className="muted">備份：{shown.backup}</div>}
          {shown.archive !== null && shown.archive !== undefined && (
            <div className="muted" data-testid="season-reset-archive">唯讀封存：{shown.archive}</div>
          )}
        </div>
      )}
      {preview !== null && (
        <div className="run-actions">
          <label>
            輸入目前的季 ID（{preview.old_season}）確認
            <input value={confirm} onChange={(e) => setConfirm(e.target.value)} disabled={busy} data-testid="season-reset-confirm" />
          </label>
          <button
            type="button"
            className="primary"
            onClick={() => void run(true)}
            disabled={busy || !canExecute(preview, previewedFor, key, confirm)}
            data-testid="season-reset-execute"
          >
            {busy ? "執行中……" : "執行季末重置"}
          </button>
          {previewedFor !== key && <span className="error-text small">條件改了，請重新預覽</span>}
        </div>
      )}
    </div>
  );
}
