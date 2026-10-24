// 技能工坊的欄位編輯器：依後端回傳的 FieldSpec 畫出對應的輸入元件（單選卡片、數字、勾選、效果列表……）。
// 這裡不寫任何規則；選項、範圍、說明全部來自 `/api/workshop/options`。
import type { Choice, FieldSpec } from "../../api/types";
import {
  addEffect,
  addModifier,
  clearChoice,
  findChoice,
  getPath,
  isJson,
  isObjectChoice,
  joinPath,
  listOf,
  moveItem,
  parentPath,
  removeItem,
  replaceItem,
  selectChoice,
  setPath,
  type Json,
} from "../../workshop/draft";
import { descOf, fieldShown, hiddenCount, shownChoices } from "../../workshop/playerView";
import { rarityName } from "../../workshop/state";
import { OptionGlyph } from "../SkillIconView";
import { Hint } from "../Hint";

interface FieldProps {
  spec: FieldSpec;
  container: Json;
  /** 欄位路徑的起點（巢狀物件、效果列表項目內的欄位用）。 */
  base: string;
  onChange(next: Json): void;
}

interface ListProps {
  fields: readonly FieldSpec[];
  container: Json;
  base: string;
  onChange(next: Json): void;
}

/** 單選欄位的選項數超過這個數量時改用下拉；是否用「卡片」顯示由後端的 `FieldSpec.card` 決定。 */
const COMPACT_MAX = 8;

export function FieldList({ fields, container, base, onChange }: ListProps) {
  return (
    <>
      {fields.filter((spec) => fieldShown(spec, container, base)).map((spec) => (
        <FieldEditor key={`${base}|${spec.field}`} spec={spec} container={container} base={base} onChange={onChange} />
      ))}
    </>
  );
}

/** 千分比欄位的顯示換算：倍率 ×2（÷1000）、百分比 25%（÷10）；其他欄位不換算（3-48f）。 */
export function displayFactor(spec: FieldSpec): number {
  return spec.display === "multiplier" ? 1000 : spec.display === "percent" ? 10 : 1;
}

export function formatDisplay(spec: FieldSpec, stored: number): string {
  const factor = displayFactor(spec);
  const shown = Number((stored / factor).toFixed(2));
  if (spec.display === "multiplier") return `×${shown}`;
  if (spec.display === "percent") return `${shown}%`;
  return String(shown);
}

function rangeHint(spec: FieldSpec): string {
  if (spec.type === "dice") {
    const sides = spec.dice_sides.length > 0 ? `，面數 ${spec.dice_sides.join("／")}` : "";
    return `格式 NdM（例 2d6）${sides}`;
  }
  const f = (n: number) => formatDisplay(spec, n);
  if (spec.min != null && spec.max != null) return `範圍 ${f(spec.min)}–${f(spec.max)}`;
  if (spec.min != null) return `至少 ${f(spec.min)}`;
  if (spec.max != null) return `最多 ${f(spec.max)}`;
  return "";
}

function Label({ spec }: { spec: FieldSpec }) {
  const hint = rangeHint(spec);
  return (
    <div className="ws-label">
      <span className="ws-label-name">
        {spec.name_zh}
        {spec.required && (
          <Hint text="必填">
            <span className="ws-required">*</span>
          </Hint>
        )}
      </span>
      {hint !== "" && <span className="muted small"> {hint}</span>}
      {descOf(spec) !== "" && <div className="muted small">{descOf(spec)}</div>}
    </div>
  );
}

export function FieldEditor(props: FieldProps) {
  const { spec } = props;
  switch (spec.type) {
    case "choice":
      return <ChoiceField {...props} />;
    case "multi_choice":
      return <MultiChoiceField {...props} />;
    case "int":
    case "count":
      return <NumberField {...props} />;
    case "dice":
    case "text":
    case "tags":
      return <TextField {...props} />;
    case "bool":
      return <BoolField {...props} />;
    case "effects":
      return <EffectsField {...props} />;
    case "object":
      return <ObjectField {...props} />;
    case "modifiers":
      return <ModifiersField {...props} />;
    case "variants":
      return <ModifiersField {...props} itemLabel="戰場變奏" addLabel="新增一個戰場變奏" />;
  }
}

// ---------- 單選 ----------

function badges(choice: Choice): string[] {
  const out: string[] = [];
  const info = choice.info;
  const rules = info["badges_zh"]; // 組合規則的標章（後端由原語資料產生，Phase 3H-8）
  if (Array.isArray(rules)) out.push(...rules.filter((r): r is string => typeof r === "string"));
  if (info["core"] === true) out.push("核心");
  else if (info["secondary"] === true) out.push("附帶");
  const min = info["min_rarity"];
  if (typeof min === "string" && min !== "common") out.push(`${rarityName(min)}以上`);
  const kinds = info["kinds"]; // 骨架選項才有 `kinds`
  if (Array.isArray(kinds) && kinds.length > 0 && !kinds.includes("active")) out.push("非主動技");
  return out;
}

/** 組合規則的說明句與不可用原因（後端由資料產生）。 */
function ruleLines(choice: Choice): string[] {
  const rules = choice.info["rules_zh"];
  return Array.isArray(rules) ? rules.filter((r): r is string => typeof r === "string") : [];
}

/** 選項分組（3-52：層數依「累積在你身上」「疊在敵人身上」分組）：後端用 `info.group_zh` 標示，
 * 沒有分組名的選項（一般欄位）都在同一組、不顯示組名；組的順序照第一次出現。 */
export function groupChoices(choices: readonly Choice[]): [string | null, Choice[]][] {
  const groups: [string | null, Choice[]][] = [];
  for (const c of choices) {
    const label = typeof c.info["group_zh"] === "string" ? c.info["group_zh"] : null;
    const found = groups.find((g) => g[0] === label);
    if (found === undefined) groups.push([label, [c]]);
    else found[1].push(c);
  }
  return groups;
}

function unavailableReason(choice: Choice): string | null {
  const reason = choice.info["unavailable_zh"];
  return typeof reason === "string" && reason !== "" ? reason : null;
}

/** 對象、狀態等參數選項的停用（3-48h）：驗證器會擋的選項不能選，原因顯示在選項旁；
 * 目前已選的那一項不停用（讓玩家看得到自己選了什麼，違規由檢查面板說明）。 */
function blockedReason(choice: Choice, chosen: Choice | undefined): string | null {
  return chosen?.value === choice.value ? null : unavailableReason(choice);
}

function ChoiceField({ spec, container, base, onChange }: FieldProps) {
  const path = joinPath(base, spec.field);
  const raw = getPath(container, path);
  const chosen = findChoice(spec, raw);
  const objectChoice = isObjectChoice(spec);
  // 選項專屬的參數：物件選項（形狀、條件）寫在該物件裡，其他寫在同一層。
  const paramBase = objectChoice ? path : parentPath(path);
  const pick = (c: Choice) => onChange(selectChoice(container, spec, c, base));
  const card = spec.card === true; // 用卡片排列：後端 `FieldSpec.card` 旗標
  if (spec.locked === true) {
    // 鎖定欄位（武器技的縮放屬性看武器）：唯讀顯示規則決定的那個值
    return (
      <div className="ws-field">
        <Label spec={spec} />
        <div className="ws-locked">{chosen !== undefined ? chosen.name_zh : "（先選武器需求）"}</div>
      </div>
    );
  }
  return (
    <div className="ws-field">
      <Label spec={spec} />
      {card && spec.choices.length <= 24 ? (
        <div className="ws-cards">
          {spec.choices.map((c) => (
            <button
              type="button"
              key={String(c.value)}
              className={`ws-card${chosen?.value === c.value ? " selected" : ""}${blockedReason(c, chosen) !== null ? " unavailable" : ""}`}
              aria-pressed={chosen?.value === c.value}
              disabled={blockedReason(c, chosen) !== null}
              onClick={() => pick(c)}
            >
              <span className="ws-card-title">
                <OptionGlyph field={spec.field} value={c.value} />
                {c.name_zh}
              </span>
              {badges(c).map((b) => (
                <span key={b} className="ws-badge">
                  {b}
                </span>
              ))}
              {descOf(c) !== "" && <span className="ws-card-desc">{descOf(c)}</span>}
              {blockedReason(c, chosen) !== null && <span className="ws-card-block">不能選：{blockedReason(c, chosen)}</span>}
            </button>
          ))}
        </div>
      ) : spec.choices.length <= COMPACT_MAX ? (
        <div className="ws-chips">
          {spec.choices.map((c) => (
            <Hint key={String(c.value)} text={blockedReason(c, chosen) !== null ? `不能選：${blockedReason(c, chosen)}` : descOf(c)}>
              <button
                type="button"
                className={`ws-chip${chosen?.value === c.value ? " selected" : ""}${blockedReason(c, chosen) !== null ? " unavailable" : ""}`}
                aria-pressed={chosen?.value === c.value}
                disabled={blockedReason(c, chosen) !== null}
                onClick={() => pick(c)}
              >
                <OptionGlyph field={spec.field} value={c.value} px={20} />
                {c.name_zh}
              </button>
            </Hint>
          ))}
        </div>
      ) : (
        <select
          value={chosen === undefined ? "" : String(chosen.value)}
          onChange={(e) => {
            const c = spec.choices.find((x) => String(x.value) === e.target.value);
            if (c !== undefined) pick(c);
          }}
        >
          <option value="" disabled>
            請選擇……
          </option>
          {groupChoices(spec.choices).map(([label, items]) => {
            const options = items.map((c) => (
              <option key={String(c.value)} value={String(c.value)} disabled={blockedReason(c, chosen) !== null}>
                {blockedReason(c, chosen) !== null ? `${c.name_zh}（不能選：${blockedReason(c, chosen)}）` : c.name_zh}
              </option>
            ));
            return label === null ? options : (
              <optgroup key={label} label={label}>
                {options}
              </optgroup>
            );
          })}
        </select>
      )}
      {!card && chosen !== undefined && descOf(chosen) !== "" && (
        <div className="muted small">{descOf(chosen)}</div>
      )}
      {!card && spec.choices.some((c) => blockedReason(c, chosen) !== null) && (
        <ul className="ws-notes ws-unavailable-list" aria-label="不能選的選項">
          {spec.choices
            .filter((c) => blockedReason(c, chosen) !== null)
            .map((c) => (
              <li key={String(c.value)}>
                {c.name_zh}：{blockedReason(c, chosen)}
              </li>
            ))}
        </ul>
      )}
      {!spec.required && raw !== undefined && (
        <button type="button" className="ws-link" onClick={() => onChange(clearChoice(container, spec, base))}>
          不使用「{spec.name_zh}」
        </button>
      )}
      {chosen !== undefined && chosen.params.length > 0 && (
        <div className="ws-nested">
          <FieldList fields={chosen.params} container={container} base={paramBase} onChange={onChange} />
        </div>
      )}
    </div>
  );
}

function MultiChoiceField({ spec, container, base, onChange }: FieldProps) {
  const path = joinPath(base, spec.field);
  const raw = getPath(container, path);
  const value = Array.isArray(raw) ? raw.map(String) : [];
  const toggle = (v: string) => {
    const next = value.includes(v) ? value.filter((x) => x !== v) : [...value, v];
    onChange(setPath(container, path, next.length === 0 ? undefined : next));
  };
  return (
    <div className="ws-field">
      <Label spec={spec} />
      <div className="ws-chips">
        {spec.choices.map((c) => {
          const picked = value.includes(String(c.value));
          // 事前停用（3I-5）：驗證器會擋的選項不能勾；已勾的不停用，讓玩家看得到自己選了什麼
          const reason = picked ? null : unavailableReason(c);
          return (
            <Hint key={String(c.value)} text={reason !== null ? `不能選：${reason}` : descOf(c)}>
              <label className={`ws-chip${picked ? " selected" : ""}${reason !== null ? " unavailable" : ""}`}>
                <input type="checkbox" checked={picked} disabled={reason !== null} onChange={() => toggle(String(c.value))} />
                {c.name_zh}
              </label>
            </Hint>
          );
        })}
      </div>
    </div>
  );
}

// ---------- 數字、文字、勾選 ----------

function NumberField({ spec, container, base, onChange }: FieldProps) {
  const path = joinPath(base, spec.field);
  const raw = getPath(container, path);
  const special = spec.allow_weapon ? "weapon" : spec.type === "count" ? "all" : null;
  const specialLabel = spec.allow_weapon ? "用武器射程" : "全部";
  const isSpecial = special !== null && raw === special;
  const factor = displayFactor(spec);
  const step = factor === 1 ? undefined : factor === 1000 ? 0.1 : 1;
  return (
    <div className="ws-field">
      <Label spec={spec} />
      <div className="ws-row">
        <input
          type="number"
          inputMode="numeric"
          min={spec.min != null ? spec.min / factor : undefined}
          max={spec.max != null ? spec.max / factor : undefined}
          step={step}
          disabled={isSpecial}
          value={typeof raw === "number" ? Number((raw / factor).toFixed(2)) : ""}
          onChange={(e) => {
            const text = e.target.value.trim();
            const n = Number(text);
            onChange(
              setPath(container, path, text === "" || !Number.isFinite(n) ? undefined : Math.round(n * factor)),
            );
          }}
        />
        {special !== null && (
          <label className="ws-inline">
            <input
              type="checkbox"
              checked={isSpecial}
              onChange={(e) => onChange(setPath(container, path, e.target.checked ? special : undefined))}
            />
            {specialLabel}
          </label>
        )}
      </div>
    </div>
  );
}

function TextField({ spec, container, base, onChange }: FieldProps) {
  const path = joinPath(base, spec.field);
  const raw = getPath(container, path);
  const text = Array.isArray(raw) ? raw.join(", ") : typeof raw === "string" ? raw : "";
  const listId = `ws-dice-${base}-${spec.field}`;
  const diceHints =
    spec.type === "dice"
      ? spec.dice_sides.flatMap((s) =>
          Array.from({ length: Math.max(1, spec.max ?? 1) }, (_, i) => `${i + (spec.min ?? 1)}d${s}`),
        )
      : [];
  const placeholder =
    spec.type === "dice" ? "例：1d6" : spec.type === "tags" ? "用逗號分隔，例：fire, burst" : spec.default != null ? String(spec.default) : "";
  return (
    <div className="ws-field">
      <Label spec={spec} />
      <input
        type="text"
        value={text}
        placeholder={placeholder}
        list={diceHints.length > 0 ? listId : undefined}
        onChange={(e) => {
          const v = e.target.value;
          if (spec.type === "tags") {
            const tags = v
              .split(/[,，\s]+/)
              .map((t) => t.trim())
              .filter((t) => t !== "");
            onChange(setPath(container, path, tags.length === 0 ? undefined : tags));
          } else {
            onChange(setPath(container, path, v === "" ? undefined : v));
          }
        }}
      />
      {diceHints.length > 0 && (
        <datalist id={listId}>
          {diceHints.map((h) => (
            <option key={h} value={h} />
          ))}
        </datalist>
      )}
    </div>
  );
}

function BoolField({ spec, container, base, onChange }: FieldProps) {
  const path = joinPath(base, spec.field);
  const on = getPath(container, path) === true;
  return (
    <div className="ws-field">
      <label className="ws-inline">
        <input type="checkbox" checked={on} onChange={(e) => onChange(setPath(container, path, e.target.checked ? true : undefined))} />
        <span className="ws-label-name">{spec.name_zh}</span>
      </label>
      {descOf(spec) !== "" && <div className="muted small">{descOf(spec)}</div>}
    </div>
  );
}

// ---------- 物件、效果、修正規則 ----------

function ObjectField({ spec, container, base, onChange }: FieldProps) {
  const path = joinPath(base, spec.field);
  const value = getPath(container, path);
  const used = isJson(value);
  return (
    <fieldset className="ws-group">
      <legend>
        {spec.name_zh}
        {spec.required && <span className="ws-required">*</span>}
      </legend>
      {descOf(spec) !== "" && <div className="muted small">{descOf(spec)}</div>}
      {!spec.required && (
        <label className="ws-inline">
          <input
            type="checkbox"
            checked={used}
            onChange={(e) => onChange(setPath(container, path, e.target.checked ? {} : undefined))}
          />
          使用
        </label>
      )}
      {used && <FieldList fields={spec.fields} container={container} base={path} onChange={onChange} />}
    </fieldset>
  );
}

function EffectsField({ spec, container, base, onChange }: FieldProps) {
  const path = joinPath(base, spec.field);
  const list = listOf(container, path);
  if (spec.choices.length === 0) {
    return (
      <div className="ws-field">
        <Label spec={spec} />
        <div className="ws-note">
          這一層的巢狀效果在這裡不展開。
          {list.length > 0 && <code className="ws-json">{JSON.stringify(list)}</code>}
        </div>
      </div>
    );
  }
  const full = spec.max_count != null && list.length >= spec.max_count;
  const count = `${list.length}${spec.max_count != null ? ` / ${spec.max_count}` : ""}`;
  return (
    <div className="ws-field">
      <Label spec={spec} />
      <div className="muted small">
        已選 {count} 個
        {spec.min_count != null && spec.min_count > 0 ? `（至少 ${spec.min_count} 個）` : ""}
      </div>
      {list.map((item, index) => {
        const choice = spec.choices.find((c) => c.value === item["type"]);
        return (
          <div className="ws-item" key={`${index}:${String(item["type"])}`}>
            <div className="ws-item-head">
              <strong>
                {index + 1}. <OptionGlyph field="effects" value={item["type"]} px={22} />
                {choice?.name_zh ?? String(item["type"])}
              </strong>
              <span className="ws-item-tools">
                <button type="button" disabled={index === 0} onClick={() => onChange(moveItem(container, spec, index, -1, base))} aria-label="上移">
                  ↑
                </button>
                <button type="button" disabled={index === list.length - 1} onClick={() => onChange(moveItem(container, spec, index, 1, base))} aria-label="下移">
                  ↓
                </button>
                <button type="button" onClick={() => onChange(removeItem(container, spec, index, base))}>
                  移除
                </button>
              </span>
            </div>
            {choice !== undefined && descOf(choice) !== "" && <div className="muted small">{descOf(choice)}</div>}
            {choice === undefined ? (
              <div className="error-text small">這個效果不在目前的選項內，請移除。</div>
            ) : (
              <FieldList
                fields={choice.params}
                container={item}
                base=""
                onChange={(next) => onChange(replaceItem(container, spec, index, next, base))}
              />
            )}
          </div>
        );
      })}
      <div className="ws-add">{full ? "已達效果數量上限。" : "新增一個效果："}</div>
      {!full && hiddenCount(spec.choices) > 0 && <div className="muted small">這類效果之後開放：{spec.choices.filter((c) => c.later === true).map((c) => c.name_zh).join("、")}。</div>}
      {!full && (
        <div className="ws-cards">
          {shownChoices(spec.choices).map((c) => {
            const blocked = unavailableReason(c);
            return (
              <button
                type="button"
                key={String(c.value)}
                className={`ws-card${blocked !== null ? " unavailable" : ""}`}
                disabled={blocked !== null}
                onClick={() => onChange(addEffect(container, spec, c, base))}
              >
                <span className="ws-card-title">
                  <OptionGlyph field="effects" value={c.value} />
                  {c.name_zh}
                </span>
                {badges(c).map((b) => (
                  <span key={b} className="ws-badge">
                    {b}
                  </span>
                ))}
                {descOf(c) !== "" && <span className="ws-card-desc">{descOf(c)}</span>}
                {ruleLines(c).map((r) => (
                  <span key={r} className="ws-card-rule">
                    {r}
                  </span>
                ))}
                {blocked !== null && <span className="ws-card-block">現在不能加：{blocked}</span>}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ModifiersField({
  spec,
  container,
  base,
  onChange,
  itemLabel = "修正規則",
  addLabel = "新增一條修正規則",
}: FieldProps & { itemLabel?: string; addLabel?: string }) {
  const path = joinPath(base, spec.field);
  const list = listOf(container, path);
  const full = spec.max_count != null && list.length >= spec.max_count;
  return (
    <div className="ws-field">
      <Label spec={spec} />
      {list.map((item, index) => (
        <div className="ws-item" key={index}>
          <div className="ws-item-head">
            <strong>
              {itemLabel} {index + 1}
              {typeof item["name_zh"] === "string" && item["name_zh"] !== "" ? `：${item["name_zh"]}` : ""}
            </strong>
            <button type="button" onClick={() => onChange(removeItem(container, spec, index, base))}>
              移除
            </button>
          </div>
          <FieldList
            fields={spec.fields}
            container={item}
            base=""
            onChange={(next) => onChange(replaceItem(container, spec, index, next, base))}
          />
        </div>
      ))}
      <button type="button" disabled={full} onClick={() => onChange(addModifier(container, spec, base))}>
        {addLabel}
      </button>
    </div>
  );
}
