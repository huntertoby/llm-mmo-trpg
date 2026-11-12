// 數值工坊的 1 階比值（Phase NW-2c C3）：技能表單的比值區（目前值、參考線、上次量測）、模擬面板的「比值」情境表單
// 與改前改後並排的結果表。比值和預算比例是兩把尺（實戰木樁傷害 ÷ 普攻 vs 點數模型），畫面各自標來源。
import type { ChangeEvent } from "react";
import type { TuningRatioSimResult, TuningRatioSummary, TuningSkillRatio } from "../api/types";
import { cellChanged, lineClass, lineText, RATIO_CELLS, ratioResultNotes, ratioSkillsOf, type RatioForm } from "./ratioModel";

function Lines({ summary }: { summary: TuningRatioSummary }) {
  if (summary.lines.length === 0) return <div className="muted small">{summary.category_zh}：不套參考線（只看單體傷害招）。</div>;
  return (
    <ul className="tn-ratio-lines" aria-label="參考線">
      {summary.lines.map((line) => (
        <li key={line.key} className={lineClass(line)} data-line={line.key} data-ok={line.ok == null ? "none" : String(line.ok)}>
          {lineText(line)}
          {line.tentative && <span className="tn-tag">建議，未定案</span>}
        </li>
      ))}
    </ul>
  );
}

function Cells({ summary }: { summary: TuningRatioSummary }) {
  return (
    <table className="tn-table tn-ratio-cells">
      <thead>
        <tr>
          {RATIO_CELLS.map((c) => (
            <th key={c.key}>{c.label}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        <tr>
          {RATIO_CELLS.map((c) => (
            <td key={c.key} className="tn-num">
              {summary[c.key]}
            </td>
          ))}
        </tr>
      </tbody>
    </table>
  );
}

/** 技能表單的比值區（NW-2c；資料來自 `GET /skills/{id}/ratio`）。 */
export function RatioBox({ ratio, loading }: { ratio: TuningSkillRatio | null; loading: boolean }) {
  return (
    <section className="panel tn-ratio" aria-label="1 階比值" data-testid="ratio-box">
      <div className="tn-budget-head">
        <span className="section-title">1 階比值（實戰木樁傷害 ÷ 普攻，每 AP）</span>
        {loading && <span className="muted small">（讀取中）</span>}
      </div>
      {ratio === null ? (
        <div className="muted small">{loading ? "讀取中……" : "比值：—"}</div>
      ) : ratio.current == null ? (
        <div className="muted small" data-testid="ratio-empty">
          {ratio.reason_zh ?? "還沒有比值"}
        </div>
      ) : (
        <>
          <div className={`small ${ratio.current.stale ? "tn-warn" : "muted"}`} data-testid="ratio-source">
            來源：{ratio.current.source_zh}；類別：{ratio.current.category_zh}
          </div>
          <Cells summary={ratio.current} />
          <Lines summary={ratio.current} />
          {ratio.previous != null && (
            <div className="muted small" data-testid="ratio-previous">
              上次（{ratio.previous.source_zh}）：直接 {ratio.previous.plain}、成立 直接 {ratio.previous.on} → 現在：直接 {ratio.current.plain}、成立 直接 {ratio.current.on}
            </div>
          )}
        </>
      )}
      <div className="muted small">參考線只當參考，不擋寫回；比值和上面的預算比例是兩把尺，改一個另一個不一定跟著到線。改完數值到右邊「小模擬」選「比值」重算。</div>
    </section>
  );
}

interface FormProps {
  form: RatioForm;
  running: boolean;
  edited: readonly string[];
  skillChoices: readonly { id: string; name_zh: string }[];
  skillName(id: string): string;
  baselineNote: string | null;
  onForm(next: RatioForm): void;
  onImport(text: string): void;
}

/** 模擬面板的「比值」情境：受測招、種子數、匯入基準。 */
export function RatioSimForm({ form, running, edited, skillChoices, skillName, baselineNote, onForm, onImport }: FormProps) {
  const skills = ratioSkillsOf(form, edited);
  const pickFile = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (file !== undefined) void file.text().then(onImport);
  };
  return (
    <div className="tn-sim-form">
      <fieldset className="tn-builds tn-probe" disabled={running}>
        <legend>要量的招（{form.skills === null ? "草稿改到的技能" : "自己選的"}；只量 1 階主動武器技）</legend>
        {skills.length === 0 && <span className="muted small">還沒有：草稿沒改到技能時，請從下面加一招。</span>}
        {skills.map((id) => (
          <span key={id} className="tn-tag">
            {skillName(id)}
            <button type="button" className="small-button" aria-label={`不量${skillName(id)}`} onClick={() => onForm({ ...form, skills: skills.filter((s) => s !== id) })}>
              ✕
            </button>
          </span>
        ))}
        <select value="" aria-label="加一招要量的" onChange={(e) => e.target.value !== "" && onForm({ ...form, skills: [...new Set([...skills, e.target.value])].sort() })}>
          <option value="">加一招…</option>
          {skillChoices
            .filter((s) => !skills.includes(s.id))
            .map((s) => (
              <option key={s.id} value={s.id}>
                {s.name_zh}（{s.id}）
              </option>
            ))}
        </select>
        {form.skills !== null && (
          <button type="button" className="small-button" onClick={() => onForm({ ...form, skills: null })}>
            改回草稿改到的
          </button>
        )}
      </fieldset>
      <div className="tn-scale" role="group" aria-label="比值規模">
        <span>規模</span>
        {[10, 50, 250].map((n) => (
          <button key={n} type="button" disabled={running} className={form.seedsText.trim() === String(n) ? "active" : ""} aria-pressed={form.seedsText.trim() === String(n)} onClick={() => onForm({ ...form, seedsText: String(n) })}>
            每組 {n} 種子{n === 50 ? "（預設）" : n === 250 ? "（BAL-21e）" : ""}
          </button>
        ))}
        <label className="tn-seeds">
          種子數
          <input value={form.seedsText} inputMode="numeric" disabled={running} aria-label="比值每組種子數" onChange={(e) => onForm({ ...form, seedsText: e.target.value })} />
        </label>
      </div>
      <fieldset className="tn-builds" disabled={running}>
        <legend>匯入基準（t1_skill_ratio.py run 的 JSON）</legend>
        <input type="file" accept=".json,application/json" aria-label="匯入比值基準 JSON" onChange={pickFile} />
        {baselineNote !== null && (
          <div className="muted small" data-testid="ratio-baseline-note">
            {baselineNote}
          </div>
        )}
      </fieldset>
      <div className="muted small">組＝招 × 可用武器 × 情境（無條件 1 個；有條件「成立／不成立」2 個；每個變奏多 1 個）。一次最多 40,000 組×種子。</div>
    </div>
  );
}

/** 比值的改前改後並排（逐招）。 */
export function RatioResultTable({ result, skillName }: { result: TuningRatioSimResult; skillName(id: string): string }) {
  return (
    <div className="tn-sim-result" data-testid="tuning-ratio-result">
      {ratioResultNotes(result).map((n) => (
        <div key={n} className="muted small">
          {n}
        </div>
      ))}
      <div className="tn-table-wrap">
        <table className="tn-table">
          <thead>
            <tr>
              <th>項目</th>
              <th>改前</th>
              <th>改後</th>
            </tr>
          </thead>
          <tbody>
            {result.skills.flatMap((row) => [
              <tr key={`g-${row.skill_id}`} className="tn-group-row">
                <th colSpan={3}>
                  {row.name_zh || skillName(row.skill_id)} <span className="tn-object-id">{row.skill_id}</span>
                </th>
              </tr>,
              ...RATIO_CELLS.map((c) => (
                <tr key={`${row.skill_id}-${c.key}`} data-cell={c.key}>
                  <td>{c.label}</td>
                  <td className="tn-num">{row.before?.[c.key] ?? "—"}</td>
                  <td className={`tn-num${cellChanged(row.before, row.after, c.key) ? " tn-changed-cell" : ""}`}>{row.after?.[c.key] ?? "—"}</td>
                </tr>
              )),
              ...(row.after?.lines ?? []).map((line, i) => {
                const before = row.before?.lines[i];
                return (
                  <tr key={`${row.skill_id}-line-${line.key}`} data-line={line.key}>
                    <td>
                      參考線 {line.label_zh} ≥ {line.threshold.toFixed(2)}
                      {line.tentative && <span className="tn-tag">建議，未定案</span>}
                    </td>
                    <td className={before === undefined ? "muted" : lineClass(before)}>{before === undefined ? "—" : before.ok == null ? "沒有值" : before.ok ? "達標" : "低於"}</td>
                    <td className={lineClass(line)}>{line.ok == null ? "沒有值" : line.ok ? "達標" : "低於"}</td>
                  </tr>
                );
              }),
            ])}
          </tbody>
        </table>
      </div>
      <div className="muted small">範圍是一般武器（不含雙匕首與綁定武器）的最低～最高；參考線比的是最高值（同 BAL-21e「低於 0.9」的判法），只當參考，不擋寫回。</div>
    </div>
  );
}
