// 數值工坊（NW-1b B4）：頭目戰小模擬。情境（頭目、build 勾選、種子數）→「N 場、預估 X 秒」→ 開始／取消、進度 →
// 結果表（改前／改後／差值，每格附分子分母、分母 < 30 標「樣本小」）與勝負翻轉場數。
import type { TuningSimJob, TuningSimOptions, TuningSimResult } from "../api/types";
import { battleCount, estimateText, flipsText, scaleProblem, secondsText, SIM_SCALES, simRows, type SimCell } from "./model";

export interface SimForm {
  boss: string;
  builds: readonly string[];
  seedsText: string;
}

interface Props {
  options: TuningSimOptions;
  form: SimForm;
  job: TuningSimJob | null;
  /** 不能開始的原因（例如草稿驗證沒過）；`null` ＝ 可以。 */
  blocked: string | null;
  error: string | null;
  skillName(id: string): string;
  onForm(next: SimForm): void;
  onStart(): void;
  onCancel(): void;
}

function seedsOf(text: string): number {
  return /^\d+$/.test(text.trim()) ? Number(text.trim()) : NaN;
}

function Cell({ cell }: { cell: SimCell }) {
  return (
    <td>
      <span className="tn-num">{cell.text}</span> <span className="muted small">（{cell.frac}）</span>
      {cell.small && <span className="tn-small">樣本小</span>}
    </td>
  );
}

export function SimResultTable({ result, skillName, buildName }: { result: TuningSimResult; skillName(id: string): string; buildName(id: string): string }) {
  const rows = simRows(result, skillName, buildName);
  let lastGroup = "";
  return (
    <div className="tn-sim-result" data-testid="tuning-sim-result">
      <div className="tn-flips">{flipsText(result)}</div>
      {result.before_cached && <div className="muted small">改前結果用的是快取（同一份內容、同樣情境跑過）。</div>}
      <div className="tn-table-wrap">
        <table className="tn-table">
          <thead>
            <tr>
              <th>項目</th>
              <th>改前</th>
              <th>改後</th>
              <th>差值</th>
            </tr>
          </thead>
          <tbody>
            {rows.flatMap((r) => {
              const out = [];
              if (r.group !== lastGroup) {
                lastGroup = r.group;
                out.push(
                  <tr key={`g-${r.group}`} className="tn-group-row">
                    <th colSpan={4}>{r.group}</th>
                  </tr>,
                );
              }
              out.push(
                <tr key={`${r.group}-${r.label}`}>
                  <td>{r.label}</td>
                  <Cell cell={r.before} />
                  <Cell cell={r.after} />
                  <td className="tn-delta">{r.delta}</td>
                </tr>,
              );
              return out;
            })}
          </tbody>
        </table>
      </div>
      <div className="muted small">括號是分子／分母（場數或回合數）；分母小於 30 標「樣本小」，數字容易跳，想確定請改用「中」或加種子數再跑。</div>
    </div>
  );
}

function Progress({ job, onCancel }: { job: TuningSimJob; onCancel(): void }) {
  const pct = job.total > 0 ? Math.round((job.done / job.total) * 100) : 0;
  return (
    <div className="tn-progress" data-state={job.state}>
      <div className="tn-bar" role="progressbar" aria-valuemin={0} aria-valuemax={job.total} aria-valuenow={job.done} aria-label="模擬進度">
        <span style={{ width: `${pct}%` }} />
      </div>
      <span className="small">
        {job.done}/{job.total} 場・已過 {secondsText(job.elapsed_s)}・預估共 {secondsText(job.estimate_s)}
      </span>
      <button type="button" className="danger" onClick={onCancel}>
        取消模擬
      </button>
    </div>
  );
}

export function SimPanel({ options, form, job, blocked, error, skillName, onForm, onStart, onCancel }: Props) {
  const seeds = seedsOf(form.seedsText);
  const problem = scaleProblem(options, form.builds.length, seeds);
  const running = job?.state === "running";
  const buildName = (id: string) => options.builds.find((b) => b.id === id)?.name_zh ?? id;
  const toggle = (id: string) => {
    const has = form.builds.includes(id);
    const next = has ? form.builds.filter((b) => b !== id) : options.builds.map((b) => b.id).filter((b) => b === id || form.builds.includes(b));
    onForm({ ...form, builds: next });
  };
  return (
    <section className="panel tn-sim" aria-label="小模擬">
      <div className="section-title">小模擬：頭目戰（改前 vs 改後）</div>
      <div className="muted small">用目前的草稿（還沒寫回也可以）和現在的數值各打一次，同樣的種子配對比較。模擬不用重開伺服器。</div>
      <div className="tn-sim-form">
        <label>
          頭目
          <select value={form.boss} disabled={running} onChange={(e) => onForm({ ...form, boss: e.target.value })}>
            {options.bosses.map((b) => (
              <option key={b.key} value={b.key}>
                {b.name_zh}
              </option>
            ))}
          </select>
        </label>
        <div className="tn-scale" role="group" aria-label="規模">
          <span>規模</span>
          {SIM_SCALES.map((s) => (
            <button
              key={s.key}
              type="button"
              disabled={running}
              className={seeds === s.seeds ? "active" : ""}
              aria-pressed={seeds === s.seeds}
              onClick={() => onForm({ ...form, seedsText: String(s.seeds) })}
            >
              {s.label}（每個 build {s.seeds} 種子）
            </button>
          ))}
          <label className="tn-seeds">
            種子數
            <input value={form.seedsText} inputMode="numeric" disabled={running} onChange={(e) => onForm({ ...form, seedsText: e.target.value })} />
          </label>
        </div>
        <fieldset className="tn-builds" disabled={running}>
          <legend>
            我方 build（{form.builds.length}/{options.builds.length}）
            <button type="button" className="small-button" onClick={() => onForm({ ...form, builds: options.builds.map((b) => b.id) })}>
              全選
            </button>
          </legend>
          {options.builds.map((b) => (
            <label key={b.id} className="tn-build">
              <input type="checkbox" checked={form.builds.includes(b.id)} onChange={() => toggle(b.id)} />
              {b.name_zh}
            </label>
          ))}
        </fieldset>
      </div>
      <div className="tn-estimate" data-testid="tuning-sim-estimate">
        {problem ?? estimateText(options, battleCount(form.builds.length, seeds))}
      </div>
      <div className="muted small">同時用 {options.workers} 個程序跑；PM 跑全量測試時會比較慢。</div>
      {blocked !== null && !running && <div className="tn-error">{blocked}</div>}
      {error !== null && <div className="tn-error" role="alert">{error}</div>}
      {running ? (
        <Progress job={job} onCancel={onCancel} />
      ) : (
        <button type="button" className="primary" disabled={problem !== null || blocked !== null} onClick={onStart}>
          開始模擬
        </button>
      )}
      {job !== null && job.state === "cancelled" && <div className="muted">模擬已取消。</div>}
      {job !== null && job.state === "failed" && <div className="tn-error">模擬失敗：{job.error_zh ?? "原因不明"}</div>}
      {job !== null && job.state === "done" && job.result != null && <SimResultTable result={job.result} skillName={skillName} buildName={buildName} />}
    </section>
  );
}
