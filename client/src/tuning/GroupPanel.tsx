// 數值工坊（NW-2b B4）：分組改。選招（左欄技能清單的篩選或手動勾選；最多 100 招，不提供「全部技能」、不給全域倍率）
// → 選欄位與改法 → 預覽表（逐招列前後值、前後預算比例、跳過原因；POST /skills/group-preview）→「放進草稿」
// （草稿與差異頁仍逐招逐欄）。
import type { TuningGroupIn, TuningGroupOp, TuningGroupPreview, TuningGroupTarget } from "../api/types";
import { valueText } from "./model";
import { filterEmpty, GROUP_OPS, GROUP_TARGETS, groupProblem, MAX_GROUP, ratioText, verdictClass, verdictText, type SkillFilter } from "./skillModel";

export interface GroupForm {
  /** true ＝ 用左欄的篩選；false ＝ 用手動勾選。 */
  useFilter: boolean;
  target: TuningGroupTarget;
  op: TuningGroupOp["kind"];
  valueText: string;
}

export const DEFAULT_GROUP_FORM: GroupForm = { useFilter: true, target: "damage_base", op: "ladder", valueText: "1" };

/** 預覽要送的 body（篩選或手動勾選擇一）。 */
export function groupRequest(form: GroupForm, filter: SkillFilter, manual: readonly string[]): TuningGroupIn {
  const op = { kind: form.op, value: Number(form.valueText.trim()) };
  return form.useFilter ? { filter: { ...filter }, target: form.target, op } : { skills: [...manual], target: form.target, op };
}

interface Props {
  form: GroupForm;
  filter: SkillFilter;
  filterLabel: string;
  filterCount: number;
  manual: readonly string[];
  preview: TuningGroupPreview | null;
  error: string | null;
  busy: boolean;
  onForm(next: GroupForm): void;
  onPreview(): void;
  onAdd(): void;
}

export function GroupPanel({ form, filter, filterLabel, filterCount, manual, preview, error, busy, onForm, onPreview, onAdd }: Props) {
  const problem = groupProblem(form.useFilter, filter, manual, filterCount, form.valueText);
  const opHint = GROUP_OPS.find((o) => o.key === form.op)?.hint ?? "";
  const usable = preview?.rows.filter((r) => r.verdict !== "skipped").length ?? 0;
  return (
    <section className="panel tn-form tn-group-panel" aria-label="分組改" data-testid="group-panel">
      <div className="tn-form-head">
        <h2>分組改</h2>
        <span className="muted small">一次對一組技能套同一個改動（最多 {MAX_GROUP} 招；不提供「全部技能」，也沒有全域倍率）。</span>
      </div>
      <fieldset className="tn-group-pick">
        <legend>1. 選招</legend>
        <label className="tn-build">
          <input type="radio" checked={form.useFilter} onChange={() => onForm({ ...form, useFilter: true })} />
          用左邊技能清單的篩選：{filterEmpty(filter) ? "（還沒選篩選條件）" : `${filterLabel}，${filterCount} 招`}
        </label>
        <label className="tn-build">
          <input type="radio" checked={!form.useFilter} onChange={() => onForm({ ...form, useFilter: false })} />
          用左邊手動勾選的：{manual.length} 招
        </label>
      </fieldset>
      <fieldset className="tn-group-pick">
        <legend>2. 改哪個欄位、怎麼改</legend>
        <label>
          欄位
          <select value={form.target} aria-label="分組改的欄位" onChange={(e) => onForm({ ...form, target: e.target.value as TuningGroupTarget })}>
            {GROUP_TARGETS.map((t) => (
              <option key={t.key} value={t.key}>
                {t.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          改法
          <select value={form.op} aria-label="分組改的改法" onChange={(e) => onForm({ ...form, op: e.target.value as TuningGroupOp["kind"] })}>
            {GROUP_OPS.map((o) => (
              <option key={o.key} value={o.key}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          N
          <input value={form.valueText} inputMode="numeric" aria-label="分組改的 N" onChange={(e) => onForm({ ...form, valueText: e.target.value })} />
        </label>
        <div className="muted small">{opHint}</div>
      </fieldset>
      {problem !== null && <div className="tn-error">{problem}</div>}
      {error !== null && (
        <div className="tn-error" role="alert">
          {error}
        </div>
      )}
      <div className="tn-draft-row">
        <button type="button" className="primary" disabled={busy || problem !== null} onClick={onPreview} data-testid="group-preview">
          3. 預覽
        </button>
        <button type="button" disabled={busy || preview === null || usable === 0} onClick={onAdd} data-testid="group-add">
          4. 放進草稿（{usable} 招）
        </button>
      </div>
      {preview !== null && <GroupPreviewTable preview={preview} />}
    </section>
  );
}

export function GroupPreviewTable({ preview }: { preview: TuningGroupPreview }) {
  return (
    <div className="tn-group-preview" data-testid="group-preview-table">
      <div className="muted small">
        選到 {preview.count} 招（上限 {preview.max_skills}）；跳過 {preview.rows.filter((r) => r.verdict === "skipped").length} 招。預算比例是改前 → 改後（1 階）。
      </div>
      <div className="tn-table-wrap">
        <table className="tn-table">
          <thead>
            <tr>
              <th>技能</th>
              <th>改動</th>
              <th>預算比例</th>
              <th>判定</th>
            </tr>
          </thead>
          <tbody>
            {preview.rows.map((r) => (
              <tr key={r.skill_id} data-skill={r.skill_id} className={r.verdict === "skipped" ? "tn-skipped" : ""}>
                <td>
                  {r.name_zh} <span className="tn-object-id">{r.skill_id}</span>
                </td>
                <td>
                  {r.verdict === "skipped"
                    ? `跳過：${r.skipped_reason_zh ?? "原因不明"}`
                    : r.changes.map((c) => (
                        <div key={c.path}>
                          <code>{c.path}</code> {valueText(c.old)} → <b>{valueText(c.new)}</b>
                        </div>
                      ))}
                </td>
                <td className="tn-num">
                  {ratioText(r.before_ratio_permille)} → {ratioText(r.after_ratio_permille)}
                </td>
                <td className={verdictClass(r.verdict)}>{verdictText(r.verdict)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="muted small">超出預算的招放進草稿後，寫回前要在那一招的表單或寫回確認視窗勾「我確定」。</div>
    </div>
  );
}
