// 數值工坊（NW-1b B2）：左欄對象清單＋右邊的欄位表單。欄位一律由 `/objects/{kind}/{id}` 的 `fields` 產生（不寫死）。
// 每欄：中文名（滑過看說明，共用 `<Hint>` 浮動卡）、現值、輸入框、建議範圍、「改過」標記與單欄還原；錯誤紅字在欄位下。
import type { TuningCheckResult, TuningFieldView, TuningObjectDetail, TuningObjectSummary } from "../api/types";
import { Hint } from "../ui/Hint";
import { editKey, fieldErrorsOf, localError, rangeText, rangeWarning, valueText, type Edits } from "./model";

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
    <nav className="panel tn-objects" aria-label="可改的對象">
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
    </nav>
  );
}

interface FormProps {
  detail: TuningObjectDetail;
  edits: Edits;
  check: TuningCheckResult | null;
  onEdit(field: TuningFieldView, text: string): void;
  onDrop(key: string): void;
}

function FieldRow({ detail, field, edits, errors, onEdit, onDrop }: Omit<FormProps, "check"> & { field: TuningFieldView; errors: readonly string[] }) {
  const key = editKey(detail.file, field.path);
  const edit = edits[key];
  const changed = edit !== undefined;
  const local = localError(edit);
  const shownErrors = local !== null ? [local] : errors;
  const warn = shownErrors.length === 0 ? rangeWarning(field, edit) : null;
  // `default_zh` 已經是「沒寫＝…」的完整說法
  const current = field.value === null ? (field.default_zh ?? "沒寫") : valueText(field.value, field.kind);
  return (
    <div className={`tn-field${changed ? " changed" : ""}${shownErrors.length > 0 ? " invalid" : ""}`} data-path={field.path}>
      <div className="tn-field-name">
        <Hint text={field.note_zh}>
          <span className="tn-label" tabIndex={0}>
            {field.label_zh}
            <span className="tn-info" aria-hidden="true">
              ？
            </span>
          </span>
        </Hint>
        {field.kind === "permille" && <span className="tn-unit">‰（1000＝100%）</span>}
      </div>
      <div className="tn-field-now">
        <span className="muted small">現值</span> {current}
      </div>
      <div className="tn-field-input">
        <input
          value={edit === undefined ? "" : edit.unset === true ? "" : edit.text}
          placeholder={edit?.unset === true ? "改回沒寫" : field.value === null ? "沒寫" : String(field.value)}
          inputMode="numeric"
          aria-label={`${field.label_zh}改成`}
          aria-invalid={shownErrors.length > 0}
          onChange={(e) => onEdit(field, e.target.value)}
        />
        <span className="tn-range muted small">建議 {rangeText(field)}</span>
      </div>
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

export function FieldForm({ detail, edits, check, onEdit, onDrop }: FormProps) {
  const errors = fieldErrorsOf(check, detail.file);
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
          <FieldRow key={f.path} detail={detail} field={f} edits={edits} errors={errors.get(f.path) ?? []} onEdit={onEdit} onDrop={onDrop} />
        ))}
      </div>
    </section>
  );
}
