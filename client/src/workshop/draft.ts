// 技能工坊：編輯「組到一半的技能」的純函式。
// 技能草稿就是技能定義 JSON（與 content/skills/*.yaml 同欄位）；選項（FieldSpec／Choice）由後端
// `/api/workshop/options` 推導，這裡只負責「把使用者的選擇寫進草稿」，不重寫任何規則。
import type { Choice, FieldSpec } from "../api/types";

export type Json = Record<string, unknown>;

/** 複合技能的第二段（Phase 3F-3b；3F-4b 起先選種類 `followup.when`）：欄位路徑都在 `followup.` 底下。 */
export const FOLLOWUP_WHEN = "followup.when";
export const FOLLOWUP_SKELETON = "followup.skeleton";
const FOLLOWUP_SHAPE = "followup.shape";
const FOLLOWUP_EFFECTS = "followup.effects";

export function isJson(value: unknown): value is Json {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function getPath(obj: unknown, path: string): unknown {
  let cur: unknown = obj;
  for (const part of path.split(".")) {
    if (!isJson(cur)) return undefined;
    cur = cur[part];
  }
  return cur;
}

/** 不可變地寫入（`a.b.c`）；`value` 為 `undefined` 時刪除，並清掉因此變空的上層物件。 */
export function setPath(obj: Json, path: string, value: unknown): Json {
  const parts = path.split(".");
  const [head, ...rest] = parts;
  if (head === undefined) return obj;
  if (rest.length === 0) {
    const next: Json = { ...obj };
    if (value === undefined) delete next[head];
    else next[head] = value;
    return next;
  }
  const child = obj[head];
  const inner = setPath(isJson(child) ? child : {}, rest.join("."), value);
  const next: Json = { ...obj };
  if (value === undefined && Object.keys(inner).length === 0) delete next[head];
  else next[head] = inner;
  return next;
}

/** 欄位路徑的上一層（`cost.self_status` → `cost`；頂層 → 空字串）。 */
export function parentPath(path: string): string {
  const i = path.lastIndexOf(".");
  return i < 0 ? "" : path.slice(0, i);
}

export function joinPath(base: string, field: string): string {
  return base === "" ? field : `${base}.${field}`;
}

/** 值是物件（`{type: ...}`）的單選欄位（形狀、條件……）：由後端的 `FieldSpec.object_choice` 旗標決定。 */
export function isObjectChoice(spec: FieldSpec): boolean {
  return spec.object_choice === true;
}

/** 目前的單選欄位選了哪個值（物件選項取 `type`）。 */
export function chosenValue(raw: unknown): string | number | boolean | undefined {
  const v = isJson(raw) ? raw["type"] : raw;
  return typeof v === "string" || typeof v === "number" || typeof v === "boolean" ? v : undefined;
}

export function findChoice(spec: FieldSpec, raw: unknown): Choice | undefined {
  const v = chosenValue(raw);
  if (v === undefined) return undefined;
  return spec.choices.find((c) => c.value === v && typeof c.value === typeof v);
}

/** `value` 是否落在這個欄位的選項或範圍內（換選項時決定要不要保留舊值）。 */
export function valueFits(spec: FieldSpec, value: unknown): boolean {
  switch (spec.type) {
    case "choice":
      return findChoice(spec, value) !== undefined;
    case "int":
    case "count":
      if (spec.allow_weapon && value === "weapon") return true;
      if (spec.type === "count" && value === "all") return true;
      return (
        typeof value === "number" &&
        Number.isInteger(value) &&
        (spec.min == null || value >= spec.min) &&
        (spec.max == null || value <= spec.max)
      );
    default:
      return true;
  }
}

/** 必填但還沒填的欄位，補上「合理的起始值」：整數取預設或最小值、必填物件先給空物件。
 * 單選與其他型別不替使用者決定（單選欄位若只有一個選項會直接選好）。 */
export function prefill(container: Json, fields: readonly FieldSpec[], base = ""): Json {
  let out = container;
  for (const spec of fields) {
    const path = joinPath(base, spec.field);
    if (getPath(out, path) !== undefined) continue;
    out = prefillOne(out, spec, base);
  }
  return out;
}

function prefillOne(container: Json, spec: FieldSpec, base: string): Json {
  const path = joinPath(base, spec.field);
  if (!spec.required) return container;
  if (spec.type === "int" || spec.type === "count") {
    const start = spec.default ?? spec.min ?? 1;
    return typeof start === "number" ? setPath(container, path, start) : container;
  }
  if (spec.type === "object") {
    return prefill(setPath(container, path, {}), spec.fields, path);
  }
  if (spec.type === "choice" && spec.choices.length === 1 && spec.choices[0] !== undefined) {
    return selectChoice(container, spec, spec.choices[0], base);
  }
  return container;
}

/** 選了單選欄位的某個選項。
 * - 物件選項（形狀、條件）：整個值換成 `{type}`，再補上它的必填參數。
 * - 一般選項：寫入值；其他選項專屬的參數（`ap_cost`、`weapon_req`……）若不適用就清掉，再補必填參數。
 * `base` 是這個欄位所在物件的路徑（效果列表項目、巢狀物件內的欄位用）。 */
export function selectChoice(container: Json, spec: FieldSpec, choice: Choice, base = ""): Json {
  const path = joinPath(base, spec.field);
  if (path === FOLLOWUP_WHEN && getPath(container, path) !== choice.value) {
    // 換第二段的種類：骨架、形狀、效果、條件、釋放時機的限制都不同，整個第二段從頭選。
    return setPath(container, "followup", { when: choice.value });
  }
  if (path === FOLLOWUP_SKELETON && getPath(container, path) !== choice.value) {
    // 換動作段的骨架：已選的形狀與效果不一定適用新骨架，清掉重選。
    let reset = setPath(container, FOLLOWUP_SHAPE, undefined);
    reset = setPath(reset, FOLLOWUP_EFFECTS, undefined);
    return setPath(reset, path, choice.value);
  }
  if (isObjectChoice(spec)) {
    const next = setPath(container, path, { type: choice.value });
    return prefill(next, choice.params, path);
  }
  const level = parentPath(path);
  let next = container;
  for (const other of spec.choices) {
    if (other.value === choice.value) continue;
    for (const p of other.params) {
      const pPath = joinPath(level, p.field);
      const fitsNew = choice.params.find((q) => q.field === p.field);
      if (fitsNew !== undefined && valueFits(fitsNew, getPath(next, pPath))) continue;
      next = setPath(next, pPath, undefined);
    }
  }
  next = setPath(next, path, choice.value);
  return prefill(next, choice.params, level);
}

/** 清除單選欄位（含它專屬的參數）。 */
export function clearChoice(container: Json, spec: FieldSpec, base = ""): Json {
  const path = joinPath(base, spec.field);
  if (path === FOLLOWUP_WHEN) return setPath(container, "followup", undefined); // 不接第二段
  if (path === FOLLOWUP_SKELETON && getPath(container, FOLLOWUP_WHEN) === undefined) {
    return setPath(container, "followup", undefined); // 3F-3b 的舊草稿（沒有種類）：不接動作段
  }
  if (path === FOLLOWUP_SKELETON) {
    // 有種類時只清骨架與它的形狀、效果、條件（種類與釋放時機保留）
    let next = setPath(container, FOLLOWUP_SHAPE, undefined);
    next = setPath(next, FOLLOWUP_EFFECTS, undefined);
    next = setPath(next, "followup.condition", undefined);
    return setPath(next, path, undefined);
  }
  const level = parentPath(path);
  let next = container;
  for (const c of spec.choices) {
    for (const p of c.params) next = setPath(next, joinPath(level, p.field), undefined);
  }
  return setPath(next, path, undefined);
}

// ---------- 列表（效果、修正規則）----------

export function listOf(container: Json, path: string): Json[] {
  const v = getPath(container, path);
  return Array.isArray(v) ? v.filter(isJson) : [];
}

/** 新增一個效果（`choice` 是效果的原語，如 `push`）。已達上限時原樣回傳。 */
export function addEffect(container: Json, spec: FieldSpec, choice: Choice, base = ""): Json {
  const path = joinPath(base, spec.field);
  const list = listOf(container, path);
  if (spec.max_count != null && list.length >= spec.max_count) return container;
  const item = prefill({ type: choice.value }, choice.params);
  return setPath(container, path, [...list, item]);
}

export function addModifier(container: Json, spec: FieldSpec, base = ""): Json {
  const path = joinPath(base, spec.field);
  const list = listOf(container, path);
  if (spec.max_count != null && list.length >= spec.max_count) return container;
  return setPath(container, path, [...list, prefill({}, spec.fields)]);
}

export function replaceItem(container: Json, spec: FieldSpec, index: number, item: Json, base = ""): Json {
  const path = joinPath(base, spec.field);
  const list = listOf(container, path);
  if (index < 0 || index >= list.length) return container;
  return setPath(container, path, list.map((x, i) => (i === index ? item : x)));
}

/** 刪除一項；刪完整個列表就移除這個欄位。 */
export function removeItem(container: Json, spec: FieldSpec, index: number, base = ""): Json {
  const path = joinPath(base, spec.field);
  const list = listOf(container, path).filter((_, i) => i !== index);
  return setPath(container, path, list.length === 0 ? undefined : list);
}

export function moveItem(container: Json, spec: FieldSpec, index: number, delta: -1 | 1, base = ""): Json {
  const path = joinPath(base, spec.field);
  const list = [...listOf(container, path)];
  const to = index + delta;
  const a = list[index];
  const b = list[to];
  if (a === undefined || b === undefined) return container;
  list[index] = b;
  list[to] = a;
  return setPath(container, path, list);
}

// ---------- 技能層級的操作 ----------

/** 換骨架：骨架決定後面所有選項，所以只保留名稱，其餘重填。 */
export function changeSkeleton(draft: Json, skeleton: string): Json {
  const out: Json = { skeleton };
  if (typeof draft["name_zh"] === "string") out["name_zh"] = draft["name_zh"];
  return out;
}

/** 草稿裡有沒有任何內容（空草稿不需要確認就能被取代）。 */
export function isEmptyDraft(draft: Json): boolean {
  return Object.keys(draft).length === 0;
}

/**
 * 「清空重來」按下去要做什麼（頁內確認，不用 `window.confirm`；內嵌瀏覽器會直接回傳否）：
 * 空草稿直接清空；有內容時第一下先問（`ask`），已經問過再按一次才清空。
 */
export function resetStep(draft: Json, confirming: boolean): "clear" | "ask" {
  return isEmptyDraft(draft) || confirming ? "clear" : "ask";
}

/** 必填、而且只有一個選項的單選欄位（例：被動技的形狀只能是「自己」）直接幫使用者選好。
 * 沒有任何變動時回傳原物件（呼叫端可用 `===` 判斷）。 */
export function autoSingles(container: Json, fields: readonly FieldSpec[], base = ""): Json {
  let out = container;
  for (const spec of fields) {
    const only = spec.choices[0];
    if (!spec.required || spec.type !== "choice" || spec.choices.length !== 1 || only === undefined) continue;
    if (getPath(out, joinPath(base, spec.field)) !== undefined) continue;
    out = selectChoice(out, spec, only, base);
  }
  return out;
}
