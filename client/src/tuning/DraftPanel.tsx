// 數值工坊（NW-1b B3、B5、B6；NW-2b B7）：草稿列（存、換、丟掉）、改動清單與驗證狀態、差異（含附帶改動）、
// 寫回（確認視窗：列附帶改動、預算例外與 #149 例外的「我確定」）、寫回紀錄與還原。
import { useState, type ReactNode } from "react";
import type { TuningApplyResult, TuningCheckResult, TuningDiff, TuningHistoryEntry, TuningSideChange, TuningStatus } from "../api/types";
import { DialogFrame } from "../ui/DialogFrame";
import { DRAFT_NAME_RE, newText, valueText, type Edit } from "./model";
import { confirmBlock } from "./skillModel";

interface DraftBarProps {
  status: TuningStatus;
  name: string;
  edits: readonly Edit[];
  unsaved: boolean;
  busy: boolean;
  onSave(): void;
  onSwitch(name: string): void;
  onDiscard(): void;
  onOpen(objectId: string): void;
}

/** 草稿列：目前草稿、換草稿（含新名稱）、存、丟掉；下面是改動清單。 */
export function DraftBar({ status, name, edits, unsaved, busy, onSave, onSwitch, onDiscard, onOpen }: DraftBarProps) {
  const [newName, setNewName] = useState("");
  const [askDiscard, setAskDiscard] = useState(false);
  const names = [...new Set([status.draft_default, ...status.drafts, name])].sort();
  const nameOk = DRAFT_NAME_RE.test(newName);
  return (
    <section className="panel tn-draft" aria-label="草稿">
      <div className="section-title">草稿</div>
      <div className="tn-draft-row">
        <label>
          目前的草稿
          <select value={name} disabled={busy} onChange={(e) => onSwitch(e.target.value)}>
            {names.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="primary" disabled={busy || !unsaved} onClick={onSave}>
          {unsaved ? "存草稿" : "已存"}
        </button>
        {askDiscard ? (
          <>
            <button type="button" className="danger" disabled={busy} onClick={() => (setAskDiscard(false), onDiscard())}>
              確定丟掉
            </button>
            <button type="button" data-sfx="ui_cancel" onClick={() => setAskDiscard(false)}>
              取消
            </button>
          </>
        ) : (
          <button type="button" disabled={busy || (edits.length === 0 && !status.drafts.includes(name))} onClick={() => setAskDiscard(true)}>
            丟掉草稿
          </button>
        )}
      </div>
      {askDiscard && <div className="muted small">丟掉「{name}」的全部改動？（只丟草稿，已寫回的數值不受影響）</div>}
      <div className="tn-draft-row">
        <label>
          另開一份草稿
          <input value={newName} placeholder="英文小寫，例 boss_try" aria-invalid={newName !== "" && !nameOk} onChange={(e) => setNewName(e.target.value)} />
        </label>
        <button
          type="button"
          disabled={busy || !nameOk || names.includes(newName)}
          onClick={() => {
            onSwitch(newName);
            setNewName("");
          }}
        >
          開新草稿
        </button>
      </div>
      {newName !== "" && !nameOk && <div className="tn-error">名稱只能用英文小寫、數字、底線、減號（最多 40 字）</div>}
      <div className="muted small">換草稿前會先把目前這份存起來。草稿存在伺服器的存檔資料夾，不會進 git。</div>
      <ChangeList edits={edits} onOpen={onOpen} />
    </section>
  );
}

function ChangeList({ edits, onOpen }: { edits: readonly Edit[]; onOpen(objectId: string): void }) {
  if (edits.length === 0) return <div className="muted">還沒有改動。從左邊選一個敵人或頭目開始改。</div>;
  return (
    <ul className="tn-changes" aria-label="改動清單">
      {edits.map((e) => (
        <li key={`${e.file}|${e.path}`}>
          <button type="button" className="link-button" onClick={() => onOpen(e.object_id)}>
            {e.object_id}
          </button>{" "}
          {e.label_zh}：{valueText(e.old)} → <b>{newText(e)}</b>
        </li>
      ))}
    </ul>
  );
}

/** 驗證狀態一行（停止輸入 0.5 秒後送；`trpg content check` 同一套）。 */
export function CheckLine({ check, checking, count }: { check: TuningCheckResult | null; checking: boolean; count: number }) {
  if (count === 0) return null;
  if (checking || check === null) return <div className="tn-check muted">驗證中……</div>;
  if (check.ok) return <div className="tn-check ok">驗證通過（{check.seconds} 秒；和 `trpg content check` 同一套檢查）</div>;
  const n = (check.field_errors?.length ?? 0) + (check.page_errors?.length ?? 0);
  return <div className="tn-check bad">有 {n} 個問題，請看紅字</div>;
}

/** 附帶改動（寫回時後端自動做：例外清單登記／移除；使用者不能直接改）。 */
export function SideChanges({ items }: { items: readonly TuningSideChange[] }) {
  if (items.length === 0) return null;
  return (
    <div className="tn-side-changes" data-testid="side-changes">
      <div className="section-title">附帶改動（寫回時自動做，不能直接改）</div>
      <ul>
        {items.map((c) => (
          <li key={`${c.action}|${c.skill_id}`} data-action={c.action}>
            <span className={`tn-tag${c.action === "exception_add" ? " enemy" : ""}`}>{c.action === "exception_add" ? "登記例外" : "移除例外"}</span> {c.text_zh}{" "}
            <span className="muted small">（{c.file}）</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** 差異表：對象、欄位、舊值 → 新值；附帶改動；下面可展開看 YAML 文字差異。 */
export function DiffView({ diff }: { diff: TuningDiff }) {
  if (diff.rows.length === 0) return <div className="muted">草稿沒有改動。</div>;
  return (
    <div className="tn-diff" data-testid="tuning-diff">
      <div className="tn-table-wrap">
        <table className="tn-table">
          <thead>
            <tr>
              <th>對象</th>
              <th>欄位</th>
              <th>現在</th>
              <th>改成</th>
            </tr>
          </thead>
          <tbody>
            {diff.rows.map((r) => (
              <tr key={`${r.file}|${r.path}`}>
                <td>{r.object_name_zh}</td>
                <td>{r.label_zh}</td>
                <td>{valueText(r.old)}</td>
                <td>
                  <b>{valueText(r.new)}</b>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <SideChanges items={diff.side_changes ?? []} />
      {(diff.errors ?? []).map((e) => (
        <div key={`${e.file}|${e.path}`} className="tn-error">
          {e.file} {e.path}：{e.message_zh}
        </div>
      ))}
      <details className="tn-diff-text">
        <summary>看檔案的文字差異（給 PM 看的）</summary>
        <pre>{diff.text}</pre>
      </details>
    </div>
  );
}

interface ApplyProps {
  status: TuningStatus;
  count: number;
  check: TuningCheckResult | null;
  checking: boolean;
  busy: boolean;
  diff: TuningDiff | null;
  applied: TuningApplyResult | null;
  simRunning?: boolean;
  /** 還沒勾「我確定」的原因（NW-2b；`null` ＝ 不需要或都勾了）。 */
  confirm?: string | null;
  /** 要勾「我確定」的例外清單（NW-2b；放在寫回按鈕下面）。 */
  exceptions?: ReactNode;
  onDiff(): void;
  onApply(): void;
}

/** 寫回按鈕停用的原因（`null` ＝ 可以按）。`confirm`：預算或 #149 例外還沒勾「我確定」的原因。 */
export function applyBlock(status: TuningStatus, count: number, check: TuningCheckResult | null, checking: boolean, simRunning = false, confirm: string | null = null): string | null {
  if (!status.can_write) return `現在不能寫回：${status.reason_zh ?? "原因不明"}（還是可以改、驗證、模擬）`;
  if (count === 0) return "草稿沒有改動";
  if (checking || check === null) return "等驗證跑完";
  if (!check.ok) return "草稿有錯，修正後才能寫回";
  if (confirm !== null) return confirm;
  if (simRunning) return "模擬跑完（或取消）再寫回";
  return null;
}

/** 寫回成功的提示：commit、檔案、備份、要重開伺服器。 */
export function AppliedNote({ applied }: { applied: TuningApplyResult }) {
  return (
    <div className="tn-applied" role="status" data-testid="tuning-applied">
      <div>
        <b>已寫回</b>並自動 commit：<code>{applied.commit.slice(0, 10)}</code> {applied.message.split("\n")[0]}
      </div>
      <div className="small">改到的檔：{applied.files.join("、")}</div>
      <div className="small muted">原檔備份在：{applied.backup}</div>
      <div className="tn-restart">{applied.restart_note_zh}</div>
    </div>
  );
}

export function ApplyPanel({ status, count, check, checking, busy, diff, applied, simRunning = false, confirm = null, exceptions = null, onDiff, onApply }: ApplyProps) {
  const block = applyBlock(status, count, check, checking, simRunning, confirm);
  return (
    <section className="panel tn-apply" aria-label="差異與寫回">
      <div className="section-title">差異與寫回</div>
      <div className="tn-draft-row">
        <button type="button" disabled={busy || count === 0} onClick={onDiff}>
          看差異
        </button>
        <button type="button" className="primary" disabled={busy || block !== null} onClick={onApply} data-testid="tuning-apply">
          寫回遊戲…
        </button>
      </div>
      {block !== null && <div className={`tn-apply-block small${block === confirm ? " tn-error" : " muted"}`}>{block}</div>}
      {exceptions}
      <div className="muted small">寫回＝把草稿寫進 content/ 的檔案並自動 commit 一筆「tune:」紀錄；按下後會先給你看清單再確認。</div>
      {applied !== null && <AppliedNote applied={applied} />}
      {diff !== null && <DiffView diff={diff} />}
    </section>
  );
}

interface DialogProps {
  diff: TuningDiff;
  busy: boolean;
  error: string | null;
  onConfirm(): void;
  onCancel(): void;
  /** NW-2b：最新的驗證結果（要勾「我確定」的預算例外與 #149 例外）。 */
  check?: TuningCheckResult | null;
  budgetOk?: ReadonlySet<string>;
  movesOk?: ReadonlySet<string>;
  onBudget?(skillId: string, on: boolean): void;
  onMoves?(unitId: string, on: boolean): void;
}

const NONE: ReadonlySet<string> = new Set();

/** 要勾「我確定」的例外（預算超出合格區間、招式組低於 #149 下限）。 */
export function ExceptionChecks({ check, budgetOk, movesOk, onBudget, onMoves }: Required<Pick<DialogProps, "budgetOk" | "movesOk">> & Pick<DialogProps, "check" | "onBudget" | "onMoves">) {
  const budget = check?.needs_confirm_budget ?? [];
  const moves = check?.needs_confirm_min_moves ?? [];
  if (budget.length === 0 && moves.length === 0) return null;
  return (
    <div className="tn-exceptions" data-testid="apply-exceptions">
      {budget.length > 0 && (
        <>
          <div className="section-title">預算例外（超出合格區間 70～100%；寫回時自動登記進例外清單）</div>
          {budget.map((f) => (
            <label key={f.skill_id} className="tn-confirm-check">
              <input type="checkbox" checked={budgetOk.has(f.skill_id)} onChange={(e) => onBudget?.(f.skill_id, e.target.checked)} />
              我確定：{f.message_zh}
            </label>
          ))}
        </>
      )}
      {moves.length > 0 && (
        <>
          <div className="section-title">#149 例外（招數低於下限：一般 2 招、精英 3 招、頭目每階段 3 招；commit 內文會記「#149 例外」）</div>
          {moves.map((f) => (
            <label key={f.unit_id} className="tn-confirm-check">
              <input type="checkbox" checked={movesOk.has(f.unit_id)} onChange={(e) => onMoves?.(f.unit_id, e.target.checked)} />
              我確定：{f.message_zh}
            </label>
          ))}
        </>
      )}
    </div>
  );
}

/** 寫回確認（共用的詢問視窗 `DialogFrame`）：列改動、附帶改動、要勾的例外、會 commit、要重開伺服器、進行中的一輪會從頭開始。 */
export function ApplyDialog({ diff, busy, error, onConfirm, onCancel, check = null, budgetOk = NONE, movesOk = NONE, onBudget, onMoves }: DialogProps) {
  const pending = confirmBlock(check, budgetOk, movesOk);
  return (
    <DialogFrame label="確認寫回" title="確認寫回遊戲的數值">
      <div className="tn-confirm">
        <DiffView diff={diff} />
        <ExceptionChecks check={check} budgetOk={budgetOk} movesOk={movesOk} onBudget={onBudget} onMoves={onMoves} />
        <ul className="tn-confirm-notes">
          <li>會改 content/ 裡的檔案，並自動 commit 一筆「tune:」紀錄（之後可以從「寫回紀錄」還原）。</li>
          <li>
            <b>要重開伺服器</b>遊戲才會用新數值（模擬不用重開）。
          </li>
          <li>重開後，進行中的 roguelite 一輪會從頭開始；舊的世界紀錄不能重播（和平常改內容一樣）。</li>
          <li>寫回前會先備份原檔；任何一步失敗都會自動還原。</li>
        </ul>
        {error !== null && (
          <div className="tn-error" role="alert">
            {error}
          </div>
        )}
        {pending !== null && <div className="tn-error">{pending}</div>}
        <div className="tn-draft-row">
          <button type="button" className="primary" disabled={busy || diff.rows.length === 0 || pending !== null} onClick={onConfirm}>
            {busy ? "寫回中……" : "確定寫回"}
          </button>
          <button type="button" data-sfx="ui_cancel" disabled={busy} onClick={onCancel}>
            取消
          </button>
        </div>
      </div>
    </DialogFrame>
  );
}

/** 寫回紀錄（最近 20 筆 `tune:`）：選一筆 → 產生反向改動放進草稿（不直接寫回）。 */
export function HistoryList({ history, busy, onRevert }: { history: readonly TuningHistoryEntry[]; busy: boolean; onRevert(commit: string): void }) {
  return (
    <section className="panel tn-history" aria-label="寫回紀錄">
      <div className="section-title">寫回紀錄與還原</div>
      {history.length === 0 ? (
        <div className="muted small">還沒有寫回過。</div>
      ) : (
        <ul className="tn-history-list">
          {history.map((h) => (
            <li key={h.commit}>
              <span className="small">
                <code>{h.commit.slice(0, 8)}</code> {h.date.slice(0, 16).replace("T", " ")}
              </span>
              <span className="tn-history-summary">{h.summary}</span>
              <button type="button" className="small-button" disabled={busy} onClick={() => onRevert(h.commit)}>
                還原這次
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="muted small">「還原這次」會把反向的改動放進目前的草稿；確認差異後再按「寫回遊戲」才會真的改回去。</div>
    </section>
  );
}
