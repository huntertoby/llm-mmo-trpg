// 數值工坊（NW-2b B5）：單位招式組編輯器。只能選既有技能 ID（`/objects?kind=skill` 的清單）；目前的招可排序、移除；
// 加招清單可搜尋中文名或 ID，每招標「敵人專用」、武器需求、1 階預算比例；和單位武器不相容的招灰掉並寫原因
// （後端 `unit_skills.problems`，同載入檢查）。階段的招式組可以「沿用上一階段」（＝刪掉這個鍵）。
// 加招清單是表單內的一般區塊（不是浮動卡）。
import { useState } from "react";
import type { TuningObjectSummary, TuningUnitSkills } from "../api/types";
import { ratioText } from "./skillModel";

export const WEAPON_REQ_ZH: Readonly<Record<string, string>> = { any: "不限武器", melee: "近戰", ranged: "遠程", focus: "法器" };

/** 加招清單最多列幾招（其餘請用搜尋縮小）。 */
export const PICKER_LIMIT = 40;

export interface PickerRow {
  id: string;
  name_zh: string;
  enemyOnly: boolean;
  weapon: string;
  ratio: string;
  /** 不能加的原因（已在清單、武器不相容）；`null` ＝ 可以加。 */
  disabled: string | null;
}

/** 加招清單：搜尋（中文名或 ID）、依「可以加的在前、ID」排序，最多 `PICKER_LIMIT` 招。 */
export function pickerRows(skills: readonly TuningObjectSummary[], list: readonly string[], picker: TuningUnitSkills | null, query: string): { rows: PickerRow[]; more: number } {
  const q = query.trim().toLowerCase();
  const rows = skills
    .filter((s) => q === "" || s.name_zh.toLowerCase().includes(q) || s.id.toLowerCase().includes(q))
    .map<PickerRow>((s) => ({
      id: s.id,
      name_zh: s.name_zh,
      enemyOnly: s.skill?.enemy_only === true,
      weapon: WEAPON_REQ_ZH[s.skill?.weapon_req ?? ""] ?? s.skill?.weapon_req ?? "",
      ratio: ratioText(s.skill?.budget_ratio_permille),
      disabled: list.includes(s.id) ? "已經裝了" : (picker?.problems?.[s.id] ?? null),
    }))
    .sort((a, b) => Number(a.disabled !== null) - Number(b.disabled !== null) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  return { rows: rows.slice(0, PICKER_LIMIT), more: Math.max(0, rows.length - PICKER_LIMIT) };
}

/** 清單裡移一招（`delta` ＝ −1 往前、+1 往後）。 */
export function moveIn(list: readonly string[], index: number, delta: number): string[] {
  const j = index + delta;
  if (j < 0 || j >= list.length) return [...list];
  const out = [...list];
  [out[index], out[j]] = [out[j]!, out[index]!];
  return out;
}

interface Props {
  label: string;
  /** 目前的招式組；`null` ＝ 沒寫（階段沿用上一階段）。 */
  list: string[] | null;
  /** 階段欄位：沿用時實際用的招（上一階段或開場）。開場欄位是 `null`（不能沿用）。 */
  inherit: readonly string[] | null;
  skills: readonly TuningObjectSummary[];
  picker: TuningUnitSkills | null;
  onChange(list: string[] | null): void;
}

export function SkillIdsEditor({ label, list, inherit, skills, picker, onChange }: Props) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const names = new Map(skills.map((s) => [s.id, s] as const));
  if (list === null) {
    return (
      <div className="tn-moves" data-testid="skill-ids-editor">
        <div className="muted small">
          沿用上一階段：{inherit === null || inherit.length === 0 ? "（空）" : inherit.map((id) => names.get(id)?.name_zh ?? id).join("、")}
        </div>
        <button type="button" className="small-button" onClick={() => onChange([...(inherit ?? [])])}>
          改成這一階段自己的招式
        </button>
      </div>
    );
  }
  const { rows, more } = pickerRows(skills, list, picker, query);
  return (
    <div className="tn-moves" data-testid="skill-ids-editor">
      {picker !== null && (
        <div className="muted small">
          武器：{picker.weapon_zh}・欄位上限：{picker.slots_zh}
        </div>
      )}
      <ol className="tn-move-list" aria-label={`${label}（${list.length} 招）`}>
        {list.length === 0 && <li className="muted small">（空：這一階段不放任何技能，只普攻）</li>}
        {list.map((id, i) => {
          const s = names.get(id);
          return (
            <li key={id} className="tn-move" data-skill={id}>
              <span className="tn-move-name">{s?.name_zh ?? id}</span>
              <span className="tn-object-id">{id}</span>
              {s?.skill?.enemy_only === true && <span className="tn-tag enemy">敵人專用</span>}
              {picker?.problems?.[id] !== undefined && <span className="tn-error small">{picker.problems[id]}</span>}
              <span className="tn-move-tools">
                <button type="button" className="small-button" disabled={i === 0} aria-label={`${s?.name_zh ?? id}往前`} onClick={() => onChange(moveIn(list, i, -1))}>
                  ↑
                </button>
                <button type="button" className="small-button" disabled={i === list.length - 1} aria-label={`${s?.name_zh ?? id}往後`} onClick={() => onChange(moveIn(list, i, 1))}>
                  ↓
                </button>
                <button type="button" className="small-button" aria-label={`移除${s?.name_zh ?? id}`} onClick={() => onChange(list.filter((x) => x !== id))}>
                  移除
                </button>
              </span>
            </li>
          );
        })}
      </ol>
      <div className="tn-draft-row">
        <button type="button" className="small-button" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
          {open ? "收起加招清單" : "加一招…"}
        </button>
        {inherit !== null && (
          <button type="button" className="small-button" onClick={() => onChange(null)}>
            改回沿用上一階段
          </button>
        )}
      </div>
      {open && (
        <div className="tn-picker" data-testid="skill-picker">
          <input className="tn-search" value={query} placeholder="搜尋技能中文名或 ID" aria-label="搜尋要加的技能" onChange={(e) => setQuery(e.target.value)} />
          <ul className="tn-picker-list">
            {rows.map((r) => (
              <li key={r.id} className={r.disabled !== null ? "disabled" : ""} data-skill={r.id}>
                <button type="button" className="small-button" disabled={r.disabled !== null} onClick={() => onChange([...list, r.id])}>
                  加入
                </button>
                <span className="tn-move-name">{r.name_zh}</span>
                <span className="tn-object-id">{r.id}</span>
                {r.enemyOnly && <span className="tn-tag enemy">敵人專用</span>}
                <span className="tn-tag">{r.weapon}</span>
                <span className="muted small">1 階預算 {r.ratio}</span>
                {r.disabled !== null && <span className="tn-why small">{r.disabled}</span>}
              </li>
            ))}
          </ul>
          {more > 0 && <div className="muted small">還有 {more} 招，請用搜尋縮小範圍。</div>}
          <div className="muted small">敵人可以裝「敵人專用」招；玩家這一邊（build 英雄、隊友、傭兵）不能裝，驗證會擋。欄位上限與武器相容也由驗證再檢查一次。</div>
        </div>
      )}
    </div>
  );
}
