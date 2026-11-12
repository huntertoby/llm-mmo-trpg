// 數值工坊（NW-2b B2、B3）：技能表單。頁首：預算比例條（合格區間 70～100% 的底色、超出紅字與「我確定」勾選、變奏與
// 複合兩段分列、`violations` 紅字）、R2 唯讀提示（升階重算）與使用這招的單位；下面依區塊分組的欄位
// （消耗與冷卻／形狀與射程／效果 1、2…／第二段／變奏）。欄位一律由後端給。
import type { TuningBudgetResult, TuningCheckResult, TuningFieldView, TuningObjectDetail, TuningSkillUser } from "../api/types";
import { FieldRow } from "./FieldForm";
import { fieldErrorsOf, type Edits } from "./model";
import { budgetGeometry, budgetNeedsConfirm, ratioText, skillSections, verdictClass } from "./skillModel";
import { WEAPON_REQ_ZH } from "./SkillIdsEditor";

interface BarProps {
  budget: TuningBudgetResult | null;
  loading: boolean;
  /** 已勾「我確定」。 */
  confirmed: boolean;
  onConfirm(on: boolean): void;
}

/** 預算比例條（即時；停止輸入 0.3 秒後問後端，數字同 `trpg skills budget`）。 */
export function BudgetBar({ budget, loading, confirmed, onConfirm }: BarProps) {
  if (budget === null) return <div className="panel tn-budget muted">{loading ? "預算計算中……" : "預算：—"}</div>;
  const g = budgetGeometry(budget.ratio_permille, budget.min_ratio_permille, budget.max_ratio_permille);
  const needs = budgetNeedsConfirm(budget);
  const cls = verdictClass(budget.verdict);
  return (
    <section className={`panel tn-budget ${cls}`} aria-label="預算比例" data-testid="budget-bar" data-verdict={budget.verdict}>
      <div className="tn-budget-head">
        <span className="section-title">預算比例</span>
        <b className={`tn-budget-ratio ${cls}`}>{budget.ratio_text}</b>
        <span className={cls}>{budget.verdict_zh}</span>
        <span className="muted small">
          合格區間 {ratioText(budget.min_ratio_permille)}～{ratioText(budget.max_ratio_permille)}
        </span>
        {loading && <span className="muted small">（重算中）</span>}
        {budget.known_exception && <span className="tn-tag">已在例外清單</span>}
      </div>
      <div className="tn-budget-track" aria-hidden="true">
        <span className="tn-budget-band" style={{ left: `${g.bandLeft}%`, width: `${g.bandWidth}%` }} />
        {budget.ratio_permille !== null && <span className={`tn-budget-mark ${cls}`} style={{ left: `${g.at}%` }} />}
      </div>
      <div className="tn-budget-scale muted small" aria-hidden="true">
        <span>0%</span>
        <span>50%</span>
        <span>100%</span>
        <span>150%{g.clipped ? "＋" : ""}</span>
      </div>
      {budget.error_zh != null && <div className="tn-error">{budget.error_zh}</div>}
      {(budget.variants ?? []).length > 0 && (
        <ul className="tn-budget-list" aria-label="變奏的預算">
          {(budget.variants ?? []).map((v) => (
            <li key={v.id}>
              變奏「{v.name_zh}」：<b className={verdictClass(v.verdict)}>{v.ratio_text}</b> {v.verdict === "ok" ? "合格" : v.verdict === "over" ? "超出預算（變奏不能用「我確定」例外，驗證會擋）" : "過弱（驗證會擋）"}
            </li>
          ))}
        </ul>
      )}
      {(budget.segments ?? []).length > 0 && (
        <ul className="tn-budget-list" aria-label="複合技能兩段">
          {(budget.segments ?? []).map((s) => (
            <li key={s.label}>
              {s.label}：{s.points} 點
            </li>
          ))}
        </ul>
      )}
      {needs && (
        <div className="tn-budget-confirm" role="alert">
          <div className="tn-error">
            這招的預算 {budget.ratio_text} {budget.verdict === "over" ? "超出" : "低於"}合格區間（{ratioText(budget.min_ratio_permille)}～{ratioText(budget.max_ratio_permille)}）。預設不能寫回；確定要這樣，請勾下面的「我確定」，寫回時會自動把它登記進
            skill_budget.yaml 的例外清單。
          </div>
          <label className="tn-confirm-check">
            <input type="checkbox" checked={confirmed} onChange={(e) => onConfirm(e.target.checked)} data-testid="confirm-budget" />
            我確定（這招超出預算也要寫回）
          </label>
        </div>
      )}
      {budget.known_exception && budget.verdict === "ok" && <div className="muted small">回到合格區間：寫回時會自動從例外清單移除。</div>}
    </section>
  );
}

function UsedBy({ users, tier }: { users: readonly TuningSkillUser[]; tier: number }) {
  if (users.length === 0) return <div className="muted small">目前沒有單位或模擬用 build 裝這招（地圖戰要量它，請用模擬面板的「裝到 build」）。</div>;
  return (
    <div className="tn-table-wrap">
      <table className="tn-table" aria-label="使用這招的單位">
        <thead>
          <tr>
            <th>誰</th>
            <th>哪裡</th>
            <th>實戰階級</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={`${u.kind}|${u.id}`}>
              <td>
                {u.name_zh} <span className="tn-object-id">{u.id}</span>
              </td>
              <td>{u.kind === "build" ? "模擬用 build 英雄" : u.where_zh.join("、")}</td>
              <td>{u.tier == null ? "—" : u.tier > tier ? <b className="tn-v-weak">{u.tier} 階（用升階版）</b> : `${u.tier} 階`}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface Props {
  detail: TuningObjectDetail;
  edits: Edits;
  check: TuningCheckResult | null;
  budget: TuningBudgetResult | null;
  budgetLoading: boolean;
  ladder: readonly string[] | null;
  confirmed: boolean;
  onConfirm(on: boolean): void;
  onEdit(field: TuningFieldView, text: string): void;
  onDrop(key: string): void;
}

const KIND_ZH: Readonly<Record<string, string>> = { active: "主動", passive: "被動", reaction: "反應", stance: "姿態", modifier: "修正" };
const CATEGORY_ZH: Readonly<Record<string, string>> = { weapon: "武器技", spell: "法術" };

export function SkillForm({ detail, edits, check, budget, budgetLoading, ladder, confirmed, onConfirm, onEdit, onDrop }: Props) {
  const errors = fieldErrorsOf(check, detail.file);
  const facets = detail.skill ?? null;
  const violations = budget?.violations ?? [];
  const budgetErrors = new Map<string, string[]>();
  for (const e of budget?.field_errors ?? []) if (e.file === detail.file) budgetErrors.set(e.path, [...(budgetErrors.get(e.path) ?? []), e.message_zh]);
  const [retier, ...userNotes] = detail.notes_zh ?? [];
  return (
    <section className="panel tn-form tn-skill-form" aria-label={`${detail.name_zh}的數值`} data-object={detail.id}>
      <div className="tn-form-head">
        <h2>{detail.name_zh}</h2>
        <span className="muted small">
          {facets !== null && `${facets.tier} 階・${CATEGORY_ZH[facets.category] ?? facets.category}・${WEAPON_REQ_ZH[facets.weapon_req] ?? facets.weapon_req}・${KIND_ZH[facets.kind] ?? facets.kind}${facets.ap_cost !== null ? `・${facets.ap_cost} AP` : ""}・`}
          {detail.file}
        </span>
        {facets?.enemy_only === true && <span className="tn-tag enemy">敵人專用</span>}
      </div>
      {violations.length > 0 && (
        <div className="tn-page-errors tn-violations" role="alert" data-testid="budget-violations">
          {violations.map((v) => (
            <div key={`${v.rule}|${v.message_zh}`} className="tn-error">
              {v.message_zh} <span className="muted small">（{v.rule}）</span>
            </div>
          ))}
        </div>
      )}
      <BudgetBar budget={budget} loading={budgetLoading} confirmed={confirmed} onConfirm={onConfirm} />
      {retier !== undefined && (
        <div className="tn-note tn-retier" data-testid="retier-note">
          <b>唯讀提示：</b>
          {retier}
          {userNotes.map((n) => (
            <div key={n} className="small">
              {n}
            </div>
          ))}
        </div>
      )}
      <details className="tn-used-by">
        <summary>使用這招的單位與 build（{(detail.used_by ?? []).length}）</summary>
        <UsedBy users={detail.used_by ?? []} tier={facets?.tier ?? 1} />
      </details>
      <div className="muted small">直接在「改成」欄填新值；空白＝不改。骰子可以打字（例 2d6）或按「−1 級／＋1 級」。滑過欄位名看說明。</div>
      {skillSections(detail.fields).map((sec) => (
        <div key={sec.key} className="tn-section" data-section={sec.key}>
          <div className="section-title tn-section-title">{sec.title}</div>
          <div className="tn-fields">
            {sec.fields.map(({ field, label }) => (
              <FieldRow
                key={field.path}
                detail={detail}
                field={field}
                label={label}
                edits={edits}
                errors={errors.get(field.path) ?? budgetErrors.get(field.path) ?? []}
                ladder={ladder}
                onEdit={onEdit}
                onDrop={onDrop}
              />
            ))}
          </div>
        </div>
      ))}
      {detail.fields.length === 0 && <div className="muted">這招沒有開放可改的數值。</div>}
    </section>
  );
}
