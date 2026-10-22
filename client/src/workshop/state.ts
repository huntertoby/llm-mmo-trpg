// 技能工坊的編輯器狀態：目前草稿、看哪一步、後端回來的選項與檢查結果；以及瀏覽器暫存。
import type { BudgetSummary, DraftOptions, StepId, WorkshopCheck } from "../api/types";
import { isJson, type Json } from "./draft";

export interface EditorState {
  draft: Json;
  /** 目前顯示哪一步；`null` ＝ 等選項回來後自動決定（第一個沒填完的步驟）。 */
  step: StepId | null;
  options: DraftOptions | null;
  check: WorkshopCheck | null;
}

export type EditorAction =
  | { type: "edit"; draft: Json }
  | { type: "replace"; draft: Json }
  | { type: "goto"; step: StepId }
  | { type: "back" }
  | { type: "next" }
  | { type: "options"; options: DraftOptions }
  | { type: "check"; check: WorkshopCheck };

export function initialState(draft: Json = {}, step: StepId | null = null): EditorState {
  return { draft, step, options: null, check: null };
}

/** 現在可以走到的步驟（前面的步驟都填好才會出現）。 */
export function availableSteps(options: DraftOptions | null): StepId[] {
  return options === null ? [] : options.steps.map((s) => s.id);
}

/** 沒有指定時預設看哪一步：第一個沒填完的；全部填完就看最後一步。 */
export function defaultStep(options: DraftOptions): StepId {
  // 戰場變奏（Phase 3-25b）是最後一個可省略的步驟：全部填完時停在稀有度，不自動跳去變奏
  const last = options.steps.filter((s) => s.id !== "variants").at(-1)?.id ?? options.steps.at(-1)?.id;
  return options.next_step ?? last ?? "skeleton";
}

export function currentStep(state: EditorState): StepId | null {
  const { options, step } = state;
  if (options === null) return step;
  if (step !== null && availableSteps(options).includes(step)) return step;
  return defaultStep(options);
}

function shift(state: EditorState, delta: -1 | 1): StepId | null {
  const ids = availableSteps(state.options);
  const cur = currentStep(state);
  if (cur === null) return null;
  return ids[ids.indexOf(cur) + delta] ?? null;
}

export function canBack(state: EditorState): boolean {
  return shift(state, -1) !== null;
}

export function canNext(state: EditorState): boolean {
  return shift(state, 1) !== null;
}

export function editorReducer(state: EditorState, action: EditorAction): EditorState {
  switch (action.type) {
    case "edit":
      return { ...state, draft: action.draft };
    case "replace":
      return { draft: action.draft, step: null, options: null, check: null };
    case "goto":
      return { ...state, step: action.step };
    case "back":
      return { ...state, step: shift(state, -1) ?? currentStep(state) };
    case "next":
      return { ...state, step: shift(state, 1) ?? currentStep(state) };
    case "options":
      return { ...state, options: action.options, step: currentStep({ ...state, options: action.options }) };
    case "check":
      return { ...state, check: action.check };
  }
}

// ---------- 檢查結果的顯示 ----------

export const RARITY_NAMES: Readonly<Record<string, string>> = {
  common: "普通",
  rare: "稀有",
  epic: "史詩",
  legendary: "傳說",
};

export function rarityName(id: string | null | undefined): string {
  if (id == null) return "—";
  return RARITY_NAMES[id] ?? id;
}

export type VerdictTone = "ok" | "weak" | "over";

export interface BudgetView {
  tone: VerdictTone;
  /** 「70.7%」 */
  percentText: string;
  /** 預算條的填滿比例（0–1；條的滿格代表 150%）。 */
  fill: number;
  /** 合格區間在條上的位置（0–1）。 */
  minMark: number;
  maxMark: number;
  /** 「合格」「過弱」「過強」＋一句說明。 */
  verdict: string;
  hint: string;
  total: number;
  usable: number;
}

const BAR_SCALE = 1.5;

export function budgetView(budget: BudgetSummary): BudgetView {
  const tone: VerdictTone = budget.verdict === "weak" ? "weak" : budget.verdict === "over" ? "over" : "ok";
  const low = Math.round(budget.min_ratio * 100);
  const high = Math.round(budget.max_ratio * 100);
  const hints: Record<VerdictTone, string> = {
    ok: `落在合格範圍（${low}–${high}%）`,
    weak: `低於 ${low}%：太弱，請多加效果或加強數值`,
    over: `超過 ${high}%：太強，請減少效果、降低數值或加冷卻`,
  };
  return {
    tone,
    percentText: budget.ratio_text,
    fill: Math.max(0, Math.min(1, budget.ratio / BAR_SCALE)),
    minMark: budget.min_ratio / BAR_SCALE,
    maxMark: budget.max_ratio / BAR_SCALE,
    verdict: budget.verdict_zh,
    hint: hints[tone],
    total: budget.total,
    usable: budget.usable,
  };
}

/** 檢查面板最上方的一句話。 */
export function checkHeadline(check: WorkshopCheck | null): { tone: "pending" | "ok" | "bad" | "partial"; text: string } {
  if (check === null) return { tone: "pending", text: "檢查中……" };
  if (!check.complete) return { tone: "partial", text: "還沒組完：完成所有必填步驟後才會算預算" };
  if (check.legal) return { tone: "ok", text: "合法：可以匯出，也可以裝上試玩" };
  return { tone: "bad", text: `不合法：有 ${check.problems.length} 項問題，修正後才能裝上試玩` };
}

// ---------- 瀏覽器暫存 ----------

export const STORAGE_KEY = "trpg.workshop.v1";

export interface TryoutPrefs {
  build?: string;
  replace?: string;
  map?: string;
  opponents?: string;
}

export interface SavedWorkshop {
  draft: Json;
  step: StepId | null;
  tryout: TryoutPrefs;
}

/** 只需要 `getItem`／`setItem` 的儲存介面（瀏覽器的 localStorage 符合；測試用假的）。 */
export interface KeyValueStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

const STEP_IDS: readonly string[] = ["skeleton", "basics", "shape", "effects", "followup", "condition", "cost", "rarity", "variants"];

function stringField(obj: Json, key: string): string | undefined {
  const v = obj[key];
  return typeof v === "string" ? v : undefined;
}

export function parseSaved(text: string | null): SavedWorkshop | null {
  if (text === null) return null;
  let raw: unknown;
  try {
    raw = JSON.parse(text);
  } catch {
    return null;
  }
  if (!isJson(raw) || !isJson(raw["draft"])) return null;
  const step = raw["step"];
  const tryoutRaw = isJson(raw["tryout"]) ? raw["tryout"] : {};
  const tryout: TryoutPrefs = {};
  for (const key of ["build", "replace", "map", "opponents"] as const) {
    const v = stringField(tryoutRaw, key);
    if (v !== undefined) tryout[key] = v;
  }
  return {
    draft: raw["draft"],
    step: typeof step === "string" && STEP_IDS.includes(step) ? (step as StepId) : null,
    tryout,
  };
}

export function loadSaved(store: KeyValueStore | null): SavedWorkshop | null {
  if (store === null) return null;
  try {
    return parseSaved(store.getItem(STORAGE_KEY));
  } catch {
    return null;
  }
}

/** 存不進去（無痕視窗、容量滿）時悄悄略過：暫存只是方便，不影響編輯。 */
export function save(store: KeyValueStore | null, saved: SavedWorkshop): boolean {
  if (store === null) return false;
  try {
    store.setItem(STORAGE_KEY, JSON.stringify(saved));
    return true;
  } catch {
    return false;
  }
}

export function browserStore(): KeyValueStore | null {
  try {
    return typeof localStorage === "undefined" ? null : localStorage;
  } catch {
    return null;
  }
}

export const STEP_NAMES: Readonly<Record<StepId, string>> = {
  skeleton: "骨架",
  basics: "基本設定",
  shape: "形狀",
  effects: "效果",
  followup: "第二段",
  condition: "條件",
  cost: "代價",
  rarity: "稀有度",
  variants: "戰場變奏",
};

/** 還沒填完的步驟（中文，依序）。條件與代價大多可省略，只有其他步驟都完成時才提到條件（有些骨架必填）。 */
export function missingStepNames(check: WorkshopCheck): string[] {
  const core = check.missing_steps.filter((s) => s !== "condition" && s !== "cost");
  const shown = core.length > 0 ? core : check.missing_steps.filter((s) => s === "condition");
  return shown.map((s) => STEP_NAMES[s]);
}
