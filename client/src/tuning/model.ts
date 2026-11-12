// 數值工坊（Phase NW-1b）的純函式：表單的改動（改動單）、本機驗證、錯誤對到欄位、模擬規模與估時、結果表、入口狀態。
// 畫面在 `screens/TuningScreen.tsx` 與 `tuning/*.tsx`；API 是 NW-1a 的 `/api/tuning/*`（`docs/phases/PhaseNW-1a報告.md` 第 1 節）。
// 表單一律由 `/objects/{kind}/{id}` 回的欄位清單產生，這裡不寫死任何欄位。
import type {
  TuningChangeIn,
  TuningCheckResult,
  TuningDraftView,
  TuningFieldView,
  TuningObjectDetail,
  TuningSimOptions,
  TuningSimPhase,
  TuningSimResult,
  TuningSimSide,
} from "../api/types";

/** 欄位的值（NW-2a 起另有骰子字串與技能 ID 清單；`null` ＝ 沒寫）。 */
export type TuningValue = TuningFieldView["value"];

/** 改動單的一筆（畫面上的「改過」）。`text` 是使用者打的字；`unset` ＝ 改回「沒寫」（只會從還原產生）。 */
export interface Edit {
  file: string;
  path: string;
  /** 磁碟上的現值（`null` ＝ 沒寫）；送出時後端比對它，對不上就擋。 */
  old: TuningValue;
  text: string;
  unset?: boolean;
  label_zh: string;
  object_id: string;
}

/** `file|path` → 改動。 */
export type Edits = Readonly<Record<string, Edit>>;

export const DEFAULT_DRAFT = "current";
/** 後端的草稿名稱規則（`drafts.py` 的 `DRAFT_NAME_PATTERN`）。 */
export const DRAFT_NAME_RE = /^[a-z0-9][a-z0-9_-]{0,39}$/;
/** 停止輸入多久才送驗證（規格 5.5：0.5 秒）。 */
export const CHECK_DELAY_MS = 500;
/** 模擬進度多久問一次（規格 5.4：每秒）。 */
export const SIM_POLL_MS = 1000;

export const editKey = (file: string, path: string): string => `${file}|${path}`;

/** 對象 ID 由檔名來（`units/ashen_heart.yaml` → `ashen_heart`）。 */
export function objectIdOf(file: string): string {
  const base = file.split("/").pop() ?? file;
  return base.replace(/\.ya?ml$/, "");
}

export type Parsed = { ok: true; value: number } | { ok: false; error: string };

/** 輸入框文字 → 整數（全形數字與負號也收）。 */
export function parseIntText(text: string): Parsed {
  const t = text
    .trim()
    .replace(/[０-９]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0xfee0))
    .replace(/[－−]/g, "-");
  if (t === "") return { ok: false, error: "要填整數" };
  if (!/^-?\d+$/.test(t)) return { ok: false, error: "要填整數（不能有小數點或文字）" };
  const n = Number(t);
  if (!Number.isSafeInteger(n)) return { ok: false, error: "數字太大" };
  return { ok: true, value: n };
}

/**
 * 輸入框改了一個欄位：空白或等於現值 → 拿掉這筆（不算改過）；其他 → 記下（打錯字也記下，好在欄位下顯示原因）。
 */
export function setEdit(edits: Edits, detail: TuningObjectDetail, field: TuningFieldView, text: string): Edits {
  const key = editKey(detail.file, field.path);
  const parsed = parseIntText(text);
  const same = text.trim() === "" || (parsed.ok && parsed.value === field.value);
  if (same) {
    if (!(key in edits)) return edits;
    const next = { ...edits };
    delete next[key];
    return next;
  }
  return {
    ...edits,
    [key]: { file: detail.file, path: field.path, old: field.value ?? null, text, label_zh: field.label_zh, object_id: detail.id },
  };
}

/** 單欄還原（拿掉那一筆）。 */
export function dropEdit(edits: Edits, key: string): Edits {
  if (!(key in edits)) return edits;
  const next = { ...edits };
  delete next[key];
  return next;
}

/** 改動單（送後端）：依 `(file, path)` 排序；打不成整數的照原文送，後端回「要填整數」。 */
export function editsToChanges(edits: Edits): TuningChangeIn[] {
  return Object.values(edits)
    .slice()
    .sort((a, b) => (a.file === b.file ? (a.path < b.path ? -1 : a.path > b.path ? 1 : 0) : a.file < b.file ? -1 : 1))
    .map((e) => {
      if (e.unset === true) return { file: e.file, path: e.path, old: e.old, new: null };
      const p = parseIntText(e.text);
      return { file: e.file, path: e.path, old: e.old, new: p.ok ? p.value : e.text };
    });
}

/** 後端存的草稿 → 畫面的改動。 */
export function editsFromDraft(view: TuningDraftView): Edits {
  const out: Record<string, Edit> = {};
  for (const c of view.changes) {
    out[editKey(c.file, c.path)] = {
      file: c.file,
      path: c.path,
      old: c.old,
      text: c.new === null ? "" : String(c.new),
      unset: c.new === null ? true : undefined,
      label_zh: c.label_zh,
      object_id: c.object_id,
    };
  }
  return out;
}

/** 兩份改動單一樣嗎（判斷「有沒有未存的改動」）。 */
export function sameChanges(a: readonly TuningChangeIn[], b: readonly TuningChangeIn[]): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

/** 值的顯示：`null` → 「沒寫」；‰ 欄位另附百分比。 */
export function valueText(value: TuningValue, kind: TuningFieldView["kind"] = "int"): string {
  if (value === null) return "沒寫";
  if (Array.isArray(value)) return value.length === 0 ? "（空）" : value.join("、");
  if (typeof value === "string") return value === "weapon" ? "武器射程" : value;
  if (kind === "permille") return `${value}‰（${trimNumber(value / 10)}%）`;
  return String(value);
}

function trimNumber(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}

/** 改動的「改成」文字（差異清單用）。 */
export function newText(edit: Edit): string {
  if (edit.unset === true) return "沒寫（刪掉這行）";
  return edit.text.trim();
}

/** 本機先擋：打不成整數。 */
export function localError(edit: Edit | undefined): string | null {
  if (edit === undefined || edit.unset === true) return null;
  const p = parseIntText(edit.text);
  return p.ok ? null : p.error;
}

/** 建議範圍外：只提醒、不擋（規格 5.5）。 */
export function rangeWarning(field: TuningFieldView, edit: Edit | undefined): string | null {
  if (edit === undefined || edit.unset === true) return null;
  const p = parseIntText(edit.text);
  if (!p.ok) return null;
  const lo = field.hint_min ?? null;
  const hi = field.hint_max ?? null;
  if ((lo !== null && p.value < lo) || (hi !== null && p.value > hi)) {
    return `超出建議範圍 ${rangeText(field)}（只是提醒，不會擋）`;
  }
  return null;
}

export function rangeText(field: TuningFieldView): string {
  const lo = field.hint_min ?? null;
  const hi = field.hint_max ?? null;
  if (lo === null && hi === null) return "—";
  return `${lo ?? "…"}～${hi ?? "…"}`;
}

/** 後端驗證結果裡，這個對象檔的錯誤：`path` → 中文原因。 */
export function fieldErrorsOf(check: TuningCheckResult | null, file: string): ReadonlyMap<string, string[]> {
  const out = new Map<string, string[]>();
  for (const e of check?.field_errors ?? []) {
    if (e.file !== file) continue;
    out.set(e.path, [...(out.get(e.path) ?? []), e.message_zh]);
  }
  return out;
}

/**
 * 頁首的錯誤：後端說對不到欄位的（`page_errors`），加上欄位錯誤裡對不到目前改動的（例如別的檔、改動已拿掉）。
 * 對得到改動但不在目前打開的對象上的，標上對象 ID，讓使用者知道去哪裡改。
 */
export function pageErrorsOf(check: TuningCheckResult | null, edits: Edits, openFile: string | null): string[] {
  if (check === null) return [];
  const out = [...(check.page_errors ?? [])];
  for (const e of check.field_errors ?? []) {
    if (e.file === openFile) continue;
    const edit = edits[editKey(e.file, e.path)];
    const where = edit === undefined ? `${e.file} ${e.path}` : `${edit.object_id}「${edit.label_zh}」`;
    out.push(`${where}：${e.message_zh}`);
  }
  return out;
}

// ---- 模擬 ------------------------------------------------------------------

export interface SimScale {
  key: "small" | "medium";
  label: string;
  seeds: number;
}

/** 預設「小」（0.0 第 5 點：約 24 場）；「中」約 80 場。種子數也可以自己填。 */
export const SIM_SCALES: readonly SimScale[] = [
  { key: "small", label: "小", seeds: 3 },
  { key: "medium", label: "中", seeds: 10 },
];

export const battleCount = (builds: number, seeds: number): number => builds * seeds;

/** 規模檢查：沒選 build、種子不是正整數、超過上限 → 中文原因。 */
export function scaleProblem(options: TuningSimOptions, builds: number, seeds: number): string | null {
  if (builds === 0) return "至少勾一個 build";
  if (!Number.isInteger(seeds) || seeds < 1) return "種子數要填 1 以上的整數";
  const n = battleCount(builds, seeds);
  if (n > options.max_battles) return `一次最多 ${options.max_battles} 場（現在 ${n} 場），請少勾幾個 build 或減少種子數`;
  return null;
}

/** 預估秒數：場數 × 每場秒數 ÷ 程序數；改前沒有快取時要多跑一倍。 */
export function estimateSeconds(options: TuningSimOptions, battles: number, beforeCached: boolean): number {
  const per = (battles * options.seconds_per_battle) / Math.max(1, options.workers);
  return Math.max(1, Math.round(beforeCached ? per : per * 2));
}

/** 「24 場（改前、改後各 24 場），預估約 11～22 秒」。 */
export function estimateText(options: TuningSimOptions, battles: number): string {
  const lo = estimateSeconds(options, battles, true);
  const hi = estimateSeconds(options, battles, false);
  return `${battles} 場（改前、改後各 ${battles} 場），預估約 ${lo}～${hi} 秒（改前結果已有快取時較快）`;
}

/** 秒數的中文（`75` → `1 分 15 秒`）。 */
export function secondsText(s: number): string {
  const t = Math.max(0, Math.round(s));
  return t < 60 ? `${t} 秒` : `${Math.floor(t / 60)} 分 ${t % 60} 秒`;
}

/** 分母小於這個數時標「樣本小」（後端 `SMALL_SAMPLE`，規格 5.4）。 */
export const SMALL_SAMPLE = 30;

/** 一格：比例或平均，附分子分母。 */
export interface SimCell {
  /** 比例（0～1）或平均；分母 0 時 `null`。 */
  value: number | null;
  text: string;
  /** 分子／分母（「19/24」）。 */
  frac: string;
  small: boolean;
}

export type SimMetric = "rate" | "avg";

export function simCell(num: number, den: number, metric: SimMetric, small?: boolean): SimCell {
  const value = den > 0 ? num / den : null;
  let text = "—";
  if (value !== null) text = metric === "rate" ? `${trimNumber(Math.round(value * 1000) / 10)}%` : trimNumber(Math.round(value * 10) / 10);
  return { value, text, frac: `${num}/${den}`, small: small ?? den < SMALL_SAMPLE };
}

/** 差值：比例用「百分點」，平均用原單位；分母 0 → 「—」。 */
export function deltaText(before: SimCell, after: SimCell, metric: SimMetric): string {
  if (before.value === null || after.value === null) return "—";
  const d = metric === "rate" ? Math.round((after.value - before.value) * 1000) / 10 : Math.round((after.value - before.value) * 10) / 10;
  if (d === 0) return "±0";
  const unit = metric === "rate" ? " 個百分點" : "";
  return `${d > 0 ? "+" : ""}${trimNumber(d)}${unit}`;
}

export interface SimRow {
  group: string;
  label: string;
  metric: SimMetric;
  before: SimCell;
  after: SimCell;
  delta: string;
}

function row(group: string, label: string, metric: SimMetric, b: [number, number, boolean?], a: [number, number, boolean?]): SimRow {
  const before = simCell(b[0], b[1], metric, b[2]);
  const after = simCell(a[0], a[1], metric, a[2]);
  return { group, label, metric, before, after, delta: deltaText(before, after, metric) };
}

function phaseOf(side: TuningSimSide, phase: number): TuningSimPhase | undefined {
  return side.phases.find((p) => p.phase === phase);
}

/**
 * 結果表（改前／改後／差值）：總覽（勝率、平均輪數、我方倒下率）→ 每個階段（到達場數、該階段每招每回合施放率）→ 每個 build 的勝場。
 * 階段與招式取改前改後的聯集（某邊沒有就是 0／0）；順序：階段編號、招式 ID。
 */
export function simRows(result: TuningSimResult, skillName: (id: string) => string, buildName: (id: string) => string): SimRow[] {
  const { before: b, after: a } = result;
  const rows: SimRow[] = [
    row("總覽", "我方勝率", "rate", [b.wins, b.n, b.small], [a.wins, a.n, a.small]),
    row("總覽", "平均輪數", "avg", [b.rounds, b.n, b.small], [a.rounds, a.n, a.small]),
    row("總覽", "我方倒下率（倒下人次／出場人數）", "rate", [b.downed, b.allies], [a.downed, a.allies]),
  ];
  const phases = [...new Set([...b.phases, ...a.phases].map((p) => p.phase))].sort((x, y) => x - y);
  for (const n of phases) {
    const pb = phaseOf(b, n);
    const pa = phaseOf(a, n);
    const name = pa?.name_zh ?? pb?.name_zh ?? "";
    const group = `第 ${n} 階段「${name}」`;
    rows.push(row(group, "到達這個階段的場數", "rate", [pb?.reached ?? 0, b.n], [pa?.reached ?? 0, a.n]));
    const skills = [...new Set([...(pb?.skills ?? []), ...(pa?.skills ?? [])].map((s) => s.skill))].sort();
    for (const id of skills) {
      const sb = pb?.skills.find((s) => s.skill === id);
      const sa = pa?.skills.find((s) => s.skill === id);
      rows.push(
        row(group, `「${skillName(id)}」每回合施放率`, "rate", [sb?.casts ?? 0, sb?.turns ?? pb?.turns ?? 0], [sa?.casts ?? 0, sa?.turns ?? pa?.turns ?? 0]),
      );
    }
  }
  const builds = [...new Set([...b.builds, ...a.builds].map((x) => x.build))];
  for (const id of builds) {
    const xb = b.builds.find((x) => x.build === id);
    const xa = a.builds.find((x) => x.build === id);
    rows.push(row("各 build 勝率", buildName(id), "rate", [xb?.wins ?? 0, xb?.n ?? 0], [xa?.wins ?? 0, xa?.n ?? 0]));
  }
  return rows;
}

/** 勝負翻轉（同種子配對）的一句話。 */
export function flipsText(result: TuningSimResult): string {
  const { won_to_lost: wl, lost_to_won: lw } = result.flips;
  if (wl === 0 && lw === 0) return `勝負翻轉：沒有（${result.battles} 場同種子配對，結果都一樣）`;
  return `勝負翻轉（${result.battles} 場同種子配對）：改前贏→改後輸 ${wl} 場、改前輸→改後贏 ${lw} 場`;
}

// ---- 入口 ------------------------------------------------------------------

/** 開關沒開時怎麼開（入口與畫面共用）。 */
export const ENABLE_HOWTO_ZH =
  "開伺服器前設定環境變數 TRPG_TUNING=1 再啟動（PowerShell：$env:TRPG_TUNING=1; uv run trpg serve；Git Bash：TRPG_TUNING=1 uv run trpg serve），然後重新整理這頁。";

export type EntryState =
  | { kind: "checking" }
  | { kind: "open" }
  | { kind: "off"; reason: string }
  | { kind: "blocked"; reason: string }
  | { kind: "offline"; reason: string };

/** `/api/tuning/status` 的錯誤 → 入口狀態（404＝開關沒開或伺服器不是開發模式；403＝經 Tunnel 轉發）。 */
export function entryFromError(status: number, message: string): EntryState {
  if (status === 404) return { kind: "off", reason: `數值工坊未開啟。${ENABLE_HOWTO_ZH}（伺服器設定的開發模式 dev_mode 也要是開的）` };
  if (status === 403) return { kind: "blocked", reason: message };
  if (status === 0) return { kind: "offline", reason: message };
  return { kind: "offline", reason: `讀不到數值工坊的狀態：${message}` };
}
