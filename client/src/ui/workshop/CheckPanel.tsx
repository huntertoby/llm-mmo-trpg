// 即時檢查面板：預算條、違反的規則、最低稀有度、技能卡片預覽。
import type { WorkshopCheck } from "../../api/types";
import { budgetView, checkHeadline, missingStepNames, rarityName } from "../../workshop/state";
import { SkillCardView } from "../SkillCardView";

function BudgetBar({ check }: { check: WorkshopCheck }) {
  if (check.budget === null) return null;
  const b = check.budget;
  const v = budgetView(b);
  return (
    <div className="ws-budget">
      <div className="ws-budget-head">
        <span className={`ws-verdict ${v.tone}`}>
          {v.percentText}・{v.verdict}
        </span>
        <span className="muted small">
          技能點數 {v.total} ／ 可用預算 {v.usable}
        </span>
      </div>
      <div
        className="ws-bar"
        role="meter"
        aria-label="預算百分比"
        aria-valuenow={Math.round(b.ratio * 100)}
        aria-valuemin={0}
        aria-valuemax={150}
      >
        <div className={`ws-bar-fill ${v.tone}`} style={{ width: `${v.fill * 100}%` }} />
        <div className="ws-bar-mark" style={{ left: `${v.minMark * 100}%` }} title={`合格下限 ${Math.round(b.min_ratio * 100)}%`} />
        <div className="ws-bar-mark" style={{ left: `${v.maxMark * 100}%` }} title={`合格上限 ${Math.round(b.max_ratio * 100)}%`} />
      </div>
      <div className="muted small">{v.hint}</div>
      <details className="ws-details">
        <summary>點數明細</summary>
        <table className="ws-table">
          <thead>
            <tr>
              <th>效果</th>
              <th>說明</th>
              <th>基礎</th>
              <th>形狀×</th>
              <th>對象×</th>
              <th>條件×</th>
              <th>點數</th>
            </tr>
          </thead>
          <tbody>
            {b.lines.map((l) => (
              <tr key={l.index}>
                <td>{l.type}</td>
                <td>{l.note}</td>
                <td>{l.base}</td>
                <td>{l.shape}</td>
                <td>{l.target}</td>
                <td>{l.condition}</td>
                <td>{l.points}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="small">
          原始點數 {b.raw}，條件倍率 ×{b.condition_multiplier}，合計 {b.total}。階級預算 {b.tier_budget} × {b.coefficient_label}{" "}
          {b.coefficient}
          {b.allowance_parts.length > 0 ? `，加成：${b.allowance_parts.join("、")}` : ""}，可用 {b.usable}。
        </div>
        {b.synergies.length > 0 && <div className="small">協同：{b.synergies.join("、")}</div>}
      </details>
    </div>
  );
}

export function CheckPanel({ check, pending }: { check: WorkshopCheck | null; pending: boolean }) {
  const head = checkHeadline(check);
  const missing = check !== null && !check.complete ? missingStepNames(check) : [];
  const chosenRarity = check?.skill != null && typeof check.skill["rarity"] === "string" ? check.skill["rarity"] : null;
  return (
    <div className="panel ws-panel" aria-live="polite">
      <div className="section-title">
        即時檢查
        {pending && <span className="muted small">（更新中……）</span>}
      </div>
      <div className={`ws-headline ${head.tone}`}>{head.text}</div>
      {missing.length > 0 && <div className="small">還沒填完：{missing.join("、")}</div>}
      {check !== null && <BudgetBar check={check} />}
      {check !== null && check.problems.length > 0 && (
        <div className="ws-problems">
          <div className="section-title">違反的規則</div>
          <ul>
            {check.problems.map((p) => (
              <li key={`${p.rule}:${p.message_zh}`}>
                <span className="ws-rule">{p.rule}</span> {p.message_zh}
              </li>
            ))}
          </ul>
        </div>
      )}
      {check !== null && check.minimum_rarity !== null && (
        <div className="ws-rarity">
          <div className="small">
            最低稀有度：<strong>{rarityName(check.minimum_rarity)}</strong>
            {chosenRarity !== null && <>（目前選：{rarityName(chosenRarity)}）</>}
          </div>
          {check.rarity_reasons.length > 0 && (
            <ul className="small muted">
              {check.rarity_reasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      {check?.card != null && (
        <div>
          <div className="section-title">技能卡片預覽</div>
          <SkillCardView card={check.card} />
        </div>
      )}
    </div>
  );
}
