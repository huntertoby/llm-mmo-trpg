// 數值工坊（NW-1b B2；NW-2b 加骰子、射程、招式組）：左欄的敵人與頭目清單＋欄位表單。欄位一律由 `/objects/{kind}/{id}`
// 的 `fields` 產生（不寫死）。每欄：中文名（滑過看說明，共用 `<Hint>` 浮動卡）、現值、輸入框、建議範圍（技能另有允許範圍）、
// 「改過」標記與單欄還原；錯誤紅字在欄位下。骰子欄位另有「−1 級／＋1 級」；唯讀欄位（武器射程）只顯示原因；
// 招式組欄位用 `SkillIdsEditor`。
import type { TuningCheckResult, TuningFieldView, TuningObjectDetail, TuningObjectSummary } from "../api/types";
import { Hint } from "../ui/Hint";
import { editKey, fieldErrorsOf, listOf, localError, normalizeDice, parseValue, rangeText, rangeWarning, valueText, type Edit, type Edits } from "./model";
import { diceStep, diceStepProblem } from "./skillModel";
import { SkillIdsEditor } from "./SkillIdsEditor";

interface ListProps {
  objects: readonly TuningObjectSummary[];
  selected: string | null;
  query: string;
  edits: Edits;
  onQuery(q: string): void;
  onSelect(id: string): void;
}

const GROUPS: readonly { key: TuningObjectSummary["category"]; label: string }[] = [
  { key: "boss", label: "頭目" },
  { key: "enemy", label: "一般敵人" },
];

/** 搜尋：中文名或 ID 含關鍵字（不分大小寫）。 */
export function filterObjects(objects: readonly TuningObjectSummary[], query: string): TuningObjectSummary[] {
  const q = query.trim().toLowerCase();
  if (q === "") return [...objects];
  return objects.filter((o) => o.name_zh.toLowerCase().includes(q) || o.id.toLowerCase().includes(q));
}

/** 每個對象有幾筆改動（清單上的小標記）。 */
export function editCounts(edits: Edits): ReadonlyMap<string, number> {
  const out = new Map<string, number>();
  for (const e of Object.values(edits)) out.set(e.object_id, (out.get(e.object_id) ?? 0) + 1);
  return out;
}

export function ObjectList({ objects, selected, query, edits, onQuery, onSelect }: ListProps) {
  const shown = filterObjects(objects, query);
  const counts = editCounts(edits);
  return (
    <div className="tn-object-groups">
      <input className="tn-search" value={query} placeholder="搜尋名字或 ID" aria-label="搜尋對象" onChange={(e) => onQuery(e.target.value)} />
      {GROUPS.map(({ key, label }) => {
        const rows = shown.filter((o) => o.category === key);
        return (
          <div key={key} className="tn-group">
            <div className="section-title">
              {label}（{rows.length}）
            </div>
            {rows.length === 0 && <div className="muted small">沒有符合的</div>}
            {rows.map((o) => (
              <button
                key={o.id}
                type="button"
                className={`tn-object${o.id === selected ? " active" : ""}`}
                aria-current={o.id === selected ? "true" : undefined}
                data-object={o.id}
                onClick={() => onSelect(o.id)}
              >
                <span className="tn-object-name">{o.name_zh}</span>
                <span className="tn-object-id">{o.id}</span>
                {(counts.get(o.id) ?? 0) > 0 && <span className="tn-badge">改 {counts.get(o.id)}</span>}
              </button>
            ))}
          </div>
        );
      })}
    </div>
  );
}

/** 表單的額外資料（技能與招式組用；NW-1b 的單位表單可以不給）。 */
export interface FieldExtras {
  /** 骰子階梯（由弱到強；讀不到是 `null`）。 */
  ladder?: readonly string[] | null;
  /** 技能清單（招式組的加招選單）。 */
  skills?: readonly TuningObjectSummary[];
  onList?(field: TuningFieldView, list: string[] | null): void;
}

interface FormProps extends FieldExtras {
  detail: TuningObjectDetail;
  edits: Edits;
  check: TuningCheckResult | null;
  onEdit(field: TuningFieldView, text: string): void;
  onDrop(key: string): void;
}

/** 骰子目前的值（改過且寫法對就用改的，否則用現值）。 */
function diceNow(field: TuningFieldView, edit: Edit | undefined): string {
  if (edit !== undefined && edit.unset !== true) {
    const p = parseValue("dice", edit.text);
    if (p.ok) return p.value as string;
  }
  return typeof field.value === "string" ? field.value : "";
}

function DiceSteps({ field, edit, ladder, onEdit }: { field: TuningFieldView; edit: Edit | undefined; ladder: readonly string[] | null; onEdit(field: TuningFieldView, text: string): void }) {
  const now = diceNow(field, edit);
  return (
    <span className="tn-dice-steps">
      {[-1, 1].map((step) => {
        const problem = diceStepProblem(ladder, now, step);
        const next = ladder === null ? null : diceStep(ladder, now, step);
        const button = (
          <button type="button" className="small-button" disabled={problem !== null} data-step={step} onClick={() => next !== null && onEdit(field, next)}>
            {step < 0 ? "−1 級" : "＋1 級"}
          </button>
        );
        return problem === null ? (
          <Hint key={step} text={`改成 ${next ?? ""}（骰子階梯，依平均值由弱到強）`}>
            {button}
          </Hint>
        ) : (
          <Hint key={step} text={problem}>
            {button}
          </Hint>
        );
      })}
    </span>
  );
}

function rangeLine(field: TuningFieldView): string {
  const hint = `建議 ${rangeText(field)}`;
  const lo = field.limit_min ?? null;
  const hi = field.limit_max ?? null;
  return lo === null && hi === null ? hint : `${hint}・允許 ${lo ?? "…"}～${hi ?? "…"}`;
}

interface RowProps extends FieldExtras {
  detail: TuningObjectDetail;
  field: TuningFieldView;
  /** 顯示的欄位名（技能表單會拿掉「效果 N（原語）：」前綴）。 */
  label?: string;
  edits: Edits;
  errors: readonly string[];
  /** 招式組：階段沿用時實際用的招。 */
  inherit?: readonly string[] | null;
  onEdit(field: TuningFieldView, text: string): void;
  onDrop(key: string): void;
}

export function FieldRow({ detail, field, label, edits, errors, inherit = null, ladder = null, skills = [], onList, onEdit, onDrop }: RowProps) {
  const key = editKey(detail.file, field.path);
  const edit = edits[key];
  const changed = edit !== undefined;
  const local = localError(edit);
  const shownErrors = local !== null ? [local] : errors;
  const warn = shownErrors.length === 0 ? rangeWarning(field, edit) : null;
  // `default_zh` 已經是「沒寫＝…」的完整說法
  const current = field.value === null ? (field.default_zh ?? "沒寫") : valueText(field.value, field.kind);
  const readonly = field.readonly_zh ?? null;
  const isList = field.kind === "skill_ids";
  const name = label ?? field.label_zh;
  const placeholder = edit?.unset === true ? "改回沒寫" : field.value === null ? "沒寫" : String(field.value);
  return (
    <div className={`tn-field${changed ? " changed" : ""}${shownErrors.length > 0 ? " invalid" : ""}${isList ? " tn-field-wide" : ""}`} data-path={field.path} data-kind={field.kind}>
      <div className="tn-field-name">
        <Hint text={field.note_zh}>
          <span className="tn-label" tabIndex={0}>
            {name}
            <span className="tn-info" aria-hidden="true">
              ？
            </span>
          </span>
        </Hint>
        {field.kind === "permille" && <span className="tn-unit">‰（1000＝100%）</span>}
        {field.kind === "dice" && <span className="tn-unit">骰子（例 2d6）</span>}
      </div>
      <div className="tn-field-now">
        <span className="muted small">現值</span> {current}
      </div>
      {isList ? (
        <div className="tn-field-input">
          <SkillIdsEditor
            label={name}
            list={listOf(field, edit)}
            inherit={field.path.startsWith("phases[") ? inherit : null}
            skills={skills}
            picker={detail.unit_skills ?? null}
            onChange={(list) => onList?.(field, list)}
          />
        </div>
      ) : readonly !== null ? (
        <div className="tn-field-input tn-readonly-field muted small" data-testid="readonly-field">
          唯讀：{readonly}
        </div>
      ) : (
        <div className="tn-field-input">
          <input
            value={edit === undefined ? "" : edit.unset === true ? "" : edit.text}
            placeholder={placeholder}
            inputMode={field.kind === "dice" ? "text" : "numeric"}
            aria-label={`${name}改成`}
            aria-invalid={shownErrors.length > 0}
            onChange={(e) => onEdit(field, e.target.value)}
            onBlur={field.kind === "dice" && edit !== undefined ? () => onEdit(field, normalizeDice(edit.text)) : undefined}
          />
          {field.kind === "dice" && <DiceSteps field={field} edit={edit} ladder={ladder} onEdit={onEdit} />}
          <span className="tn-range muted small">{rangeLine(field)}</span>
        </div>
      )}
      <div className="tn-field-mark">
        {changed && (
          <>
            <span className="tn-changed">改過</span>
            <button type="button" className="small-button" onClick={() => onDrop(key)}>
              還原這欄
            </button>
          </>
        )}
      </div>
      {shownErrors.map((m) => (
        <div key={m} className="tn-error" role="alert">
          {m}
        </div>
      ))}
      {warn !== null && <div className="tn-warn">{warn}</div>}
    </div>
  );
}

/** 招式組欄位：階段沿用時實際用的招（開場 → 第 2 階段 → …，依欄位順序往下傳）。 */
export function inheritedLists(fields: readonly TuningFieldView[], edits: Edits, file: string): ReadonlyMap<string, string[]> {
  const out = new Map<string, string[]>();
  let last: string[] = [];
  for (const f of fields) {
    if (f.kind !== "skill_ids") continue;
    out.set(f.path, last);
    const own = listOf(f, edits[editKey(file, f.path)]);
    if (own !== null) last = own;
  }
  return out;
}

export function FieldForm({ detail, edits, check, onEdit, onDrop, ladder, skills, onList }: FormProps) {
  const errors = fieldErrorsOf(check, detail.file);
  const inherit = inheritedLists(detail.fields, edits, detail.file);
  return (
    <section className="panel tn-form" aria-label={`${detail.name_zh}的數值`} data-object={detail.id}>
      <div className="tn-form-head">
        <h2>{detail.name_zh}</h2>
        <span className="muted small">
          {detail.category === "boss" ? "頭目" : "一般敵人"}・{detail.file}
        </span>
      </div>
      {(detail.notes_zh ?? []).map((n) => (
        <div key={n} className="tn-note muted small">
          {n}
        </div>
      ))}
      <div className="muted small">直接在「改成」欄填新數字；空白＝不改。滑過欄位名看說明。</div>
      <div className="tn-fields">
        {detail.fields.map((f) => (
          <FieldRow
            key={f.path}
            detail={detail}
            field={f}
            edits={edits}
            errors={errors.get(f.path) ?? []}
            inherit={inherit.get(f.path) ?? null}
            ladder={ladder}
            skills={skills}
            onList={onList}
            onEdit={onEdit}
            onDrop={onDrop}
          />
        ))}
      </div>
    </section>
  );
}
