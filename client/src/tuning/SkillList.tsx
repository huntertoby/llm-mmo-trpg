// 數值工坊（NW-2b B1）：左欄的兩個分頁「敵人與頭目」「技能」。技能分頁：搜尋、篩選（階級、武器技／法術、近戰／遠程、
// AP、主動／被動、敵人專用、有條件）、常用預設組；每招顯示 1 階預算比例，可勾選給「分組改」用（手動勾選，最多 100 招）。
import type { TuningGroupPreset, TuningObjectSummary } from "../api/types";
import { editCounts, ObjectList } from "./FieldForm";
import type { Edits } from "./model";
import { FILTER_ROWS, filterEmpty, filterSkills, MAX_GROUP, ratioText, type SkillFilter } from "./skillModel";

export type ObjectTab = "unit" | "skill";

interface SkillListProps {
  skills: readonly TuningObjectSummary[];
  presets: readonly TuningGroupPreset[];
  selected: string | null;
  query: string;
  filter: SkillFilter;
  /** 目前套的預設組（`""` ＝ 沒有）。 */
  preset: string;
  checked: readonly string[];
  edits: Edits;
  onQuery(q: string): void;
  onFilter(f: SkillFilter, preset: string): void;
  onSelect(id: string): void;
  onCheck(ids: string[]): void;
}

/** 清單最多畫幾列（401 招全畫太長；請用篩選或搜尋縮小）。 */
export const LIST_LIMIT = 150;

export function SkillList({ skills, presets, selected, query, filter, preset, checked, edits, onQuery, onFilter, onSelect, onCheck }: SkillListProps) {
  const shown = filterSkills(skills, query, filter);
  const counts = editCounts(edits);
  const toggle = (id: string) => onCheck(checked.includes(id) ? checked.filter((x) => x !== id) : [...checked, id].sort());
  return (
    <div className="tn-object-groups tn-skill-list">
      <input className="tn-search" value={query} placeholder="搜尋技能中文名或 ID" aria-label="搜尋技能" onChange={(e) => onQuery(e.target.value)} />
      <label className="tn-preset">
        常用預設組
        <select
          value={preset}
          aria-label="常用預設組"
          onChange={(e) => {
            const p = presets.find((x) => x.key === e.target.value);
            onFilter(p === undefined ? {} : { ...p.filter }, p?.key ?? "");
          }}
        >
          <option value="">（不用）</option>
          {presets.map((p) => (
            <option key={p.key} value={p.key}>
              {p.label_zh}
            </option>
          ))}
        </select>
      </label>
      <div className="tn-filters" role="group" aria-label="技能篩選">
        {FILTER_ROWS.map((r) => (
          <div key={r.label} className="tn-filter-row">
            <span className="muted small">{r.label}</span>
            {r.choices.map((c) => {
              const on = c.on(filter);
              return (
                <button key={c.key} type="button" className={`small-button${on ? " active" : ""}`} aria-pressed={on} onClick={() => onFilter(c.apply(filter, !on), "")}>
                  {c.label}
                </button>
              );
            })}
          </div>
        ))}
        {!filterEmpty(filter) && (
          <button type="button" className="small-button" onClick={() => onFilter({}, "")}>
            清除篩選
          </button>
        )}
      </div>
      <div className="section-title">
        技能（{shown.length}）
        {checked.length > 0 && (
          <span className={`tn-checked-count${checked.length > MAX_GROUP ? " over" : ""}`}>
            已勾 {checked.length}
            <button type="button" className="small-button" onClick={() => onCheck([])}>
              清除勾選
            </button>
          </span>
        )}
      </div>
      {shown.length === 0 && <div className="muted small">沒有符合的</div>}
      {shown.slice(0, LIST_LIMIT).map((o) => (
        <div key={o.id} className={`tn-skill-row${o.id === selected ? " active" : ""}`}>
          <input type="checkbox" checked={checked.includes(o.id)} aria-label={`勾選${o.name_zh}（分組改）`} onChange={() => toggle(o.id)} />
          <button type="button" className={`tn-object${o.id === selected ? " active" : ""}`} aria-current={o.id === selected ? "true" : undefined} data-object={o.id} onClick={() => onSelect(o.id)}>
            <span className="tn-object-name">{o.name_zh}</span>
            <span className="tn-object-id">{o.id}</span>
            {o.skill?.enemy_only === true && <span className="tn-tag enemy">敵人專用</span>}
            <span className="tn-ratio muted small">{ratioText(o.skill?.budget_ratio_permille)}</span>
            {(counts.get(o.id) ?? 0) > 0 && <span className="tn-badge">改 {counts.get(o.id)}</span>}
          </button>
        </div>
      ))}
      {shown.length > LIST_LIMIT && <div className="muted small">只列前 {LIST_LIMIT} 招，請用篩選或搜尋縮小（分組改照篩選選到的全部招）。</div>}
    </div>
  );
}

interface PanelProps {
  tab: ObjectTab;
  onTab(tab: ObjectTab): void;
  units: Parameters<typeof ObjectList>[0];
  skills: SkillListProps;
}

/** 左欄：分頁＋清單。 */
export function ObjectPanel({ tab, onTab, units, skills }: PanelProps) {
  return (
    <nav className="panel tn-objects" aria-label="可改的對象">
      <div className="tn-tabs" role="tablist">
        {(
          [
            ["unit", "敵人與頭目"],
            ["skill", "技能"],
          ] as const
        ).map(([key, label]) => (
          <button key={key} type="button" role="tab" aria-selected={tab === key} className={tab === key ? "active" : ""} onClick={() => onTab(key)}>
            {label}
          </button>
        ))}
      </div>
      {tab === "unit" ? <ObjectList {...units} /> : <SkillList {...skills} />}
    </nav>
  );
}
