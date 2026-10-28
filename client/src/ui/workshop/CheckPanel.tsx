// 即時檢查面板：預算條、違反的規則、最低稀有度、技能卡片預覽。
import type { BudgetLine, KeywordHint, WorkshopCheck, WorkshopWeapon } from "../../api/types";
import { noKeywords } from "../keywords";
import { budgetView, checkHeadline, missingStepNames, rarityName } from "../../workshop/state";
import { KeywordLine } from "../KeywordLine";
import { SkillCardView } from "../SkillCardView";
import { AssemblyFormula, SkillIconView } from "../SkillIconView";
import { Hint } from "../Hint";

/** 想接上關鍵字的建議（玩法決定 #55）：加哪一種效果或條件就能製造或利用哪個關鍵字。只是提示，不擋。 */
function KeywordHints({ hints, open }: { hints: readonly KeywordHint[]; open: boolean }) {
  if (hints.length === 0) return null;
  return (
    <details className="ws-details ws-keyword-hints" open={open}>
      <summary>想和其他技能協同？加這些就能接上關鍵字</summary>
      <ul className="small">
        {hints.map((h) => (
          <li key={h.id}>
            <strong>{h.name_zh}</strong>
            {h.makes.length > 0 && <div>製造：加{h.makes.join("、")}</div>}
            {h.uses.length > 0 && <div>利用：加{h.uses.join("、")}</div>}
          </li>
        ))}
      </ul>
    </details>
  );
}

function LinesTable({ lines }: { lines: BudgetLine[] }) {
  return (
    <table className="ws-table">
      <thead>
        <tr>
          <th>效果</th>
          <th>說明</th>
          <th>基礎</th>
          <th>形狀×</th>
          <th>射程×</th>
          <th>對象×</th>
          <th>條件×</th>
          <th>點數</th>
        </tr>
      </thead>
      <tbody>
        {lines.map((l) => (
          <tr key={l.index}>
            <td>{l.type}</td>
            <td>{l.note}</td>
            <td>{l.base}</td>
            <td>{l.shape}</td>
            <td>{l.range}</td>
            <td>{l.target}</td>
            <td>{l.condition}</td>
            <td>{l.points}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

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
        <Hint text={`合格下限 ${Math.round(b.min_ratio * 100)}%`}>
          <div className="ws-bar-mark" style={{ left: `${v.minMark * 100}%` }} />
        </Hint>
        <Hint text={`合格上限 ${Math.round(b.max_ratio * 100)}%`}>
          <div className="ws-bar-mark" style={{ left: `${v.maxMark * 100}%` }} />
        </Hint>
      </div>
      <div className="muted small">{v.hint}</div>
      {b.variants.length > 0 && (
        <div className="ws-variant-budgets small" aria-label="各型態預算">
          <div>
            戰場變奏：基礎型態因 {b.variants.length} 個變奏多算 {b.variant_surcharge_permille / 10}%（已含在上面的點數）；每個型態各自要落在合格區間內：
          </div>
          <ul>
            {b.variants.map((f) => (
              <li key={f.id}>
                <span className={`ws-verdict ${f.verdict}`}>{f.ratio_text}</span> {f.name_zh}（{f.verdict_zh}，點數 {f.total} ／ 可用 {f.usable}
                {f.range_text !== "" ? `，${f.range_text}` : ""}）
              </li>
            ))}
          </ul>
        </div>
      )}
      <details className="ws-details">
        <summary>點數明細</summary>
        {b.segments.length > 0 ? (
          <>
            {b.segments.map((seg) => (
              <div key={seg.label}>
                <div className="small">
                  <strong>{seg.label}</strong>（骨架 {seg.skeleton}，形狀 {seg.shape}）
                </div>
                <LinesTable lines={seg.lines} />
                <div className="small">
                  {seg.range_text !== "" ? `${seg.range_text}，` : ""}原始點數 {seg.raw}，條件倍率 ×{seg.condition_multiplier}，該段點數 {seg.total}
                  {seg.synergies.length > 0 ? `，協同：${seg.synergies.join("、")}` : ""}
                </div>
              </div>
            ))}
            <div className="small">
              複合技能：兩段點數加總 {b.segments.map((seg) => seg.total).join(" ＋ ")} × (1000 ＋ {b.composite_tax_permille}‰) ÷ 1000 ＝{" "}
              {b.total}（加成 +{b.composite_tax_permille / 10}%，省下一次行動的代價）。
            </div>
          </>
        ) : (
          <LinesTable lines={b.lines} />
        )}
        <div className="small">
          {b.range_text !== "" ? `${b.range_text}（已乘在作用於單位的效果點數上），` : ""}原始點數 {b.raw}，條件倍率 ×{b.condition_multiplier}，合計 {b.total}。階級預算 {b.tier_budget} × {b.coefficient_label}{" "}
          {b.coefficient}
          {b.allowance_parts.length > 0 ? `，加成：${b.allowance_parts.join("、")}` : ""}，可用 {b.usable}。
        </div>
        {b.synergies.length > 0 && <div className="small">協同：{b.synergies.join("、")}</div>}
      </details>
    </div>
  );
}

/** 預覽武器下拉（06 6.10）：只影響卡片預覽與檢查（武器技的屬性寫那把武器的），不改技能本身。 */
export interface PreviewWeapon {
  weapons: readonly WorkshopWeapon[];
  /** 選到的武器 ID；空字串＝不指定（列例子）。 */
  value: string;
  onChange(id: string): void;
}

function PreviewWeaponSelect({ preview }: { preview: PreviewWeapon }) {
  return (
    <label className="ws-preview-weapon small">
      預覽武器：
      <select value={preview.value} onChange={(e) => preview.onChange(e.target.value)} aria-label="預覽武器">
        <option value="">不指定（列例子）</option>
        {preview.weapons.map((w) => (
          <option key={w.id} value={w.id}>
            {w.name_zh}（{w.class_zh}）
          </option>
        ))}
      </select>
    </label>
  );
}

export function CheckPanel({
  check,
  pending,
  dev = false,
  preview,
}: {
  check: WorkshopCheck | null;
  pending: boolean;
  dev?: boolean;
  preview?: PreviewWeapon;
}) {
  const head = checkHeadline(check);
  const missing = check !== null && !check.complete ? missingStepNames(check) : [];
  const chosenRarity = check?.skill != null && typeof check.skill["rarity"] === "string" ? check.skill["rarity"] : null;
  return (
    <div className="panel ws-panel" aria-live="polite">
      <div className="section-title">
        即時檢查
        {pending && <span className="muted small">（更新中……）</span>}
      </div>
      {preview !== undefined && <PreviewWeaponSelect preview={preview} />}
      {check?.icon != null && (
        <div className="ws-icon-preview">
          <div className="section-title">技能圖示（每完成一步，多一個部件）</div>
          <div className="ws-preview">
            <SkillIconView icon={check.icon} size={96} />
            <div className="ws-preview-sizes">
              <Hint text="技能列的大小（40px）">
                <span className="ws-size-demo">
                  <SkillIconView icon={check.icon} size={40} />
                </span>
              </Hint>
              <Hint text="被動、反應等小圖示（28px）">
                <span className="ws-size-demo">
                  <SkillIconView icon={check.icon} size={28} />
                </span>
              </Hint>
            </div>
          </div>
          <AssemblyFormula icon={check.icon} />
        </div>
      )}
      {check !== null && (
        <KeywordLine keywords={check.keywords} showBasic={check.complete} empty="關鍵字：還沒有（沒有關鍵字也可以，就是基礎技能）" />
      )}
      {check !== null && <KeywordHints hints={check.keyword_hints ?? []} open={check.complete && noKeywords(check.keywords)} />}
      <div className={`ws-headline ${head.tone}`}>{head.text}</div>
      {missing.length > 0 && <div className="small">還沒填完：{missing.join("、")}</div>}
      {check !== null && <BudgetBar check={check} />}
      {check !== null && check.problems.length > 0 && (
        <div className="ws-problems">
          <div className="section-title">違反的規則</div>
          <ul>
            {check.problems.map((p) => (
              <li key={`${p.rule}:${p.message_zh}`}>
                {dev && <span className="ws-rule">{p.rule}</span>} {p.message_zh}
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
        <div style={pending ? { opacity: 0.45 } : undefined} data-stale={pending ? "true" : undefined}>
          <div className="section-title">技能卡片預覽</div>
          <SkillCardView card={check.card} hideConcept={!dev && check.concept_provisional === true} />
        </div>
      )}
    </div>
  );
}
