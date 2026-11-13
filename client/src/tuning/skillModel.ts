// 數值工坊開放技能（Phase NW-2b）的純函式：技能表單分組、骰子 ±1 級、預算比例條、技能篩選、分組改、
// 寫回前要勾的「我確定」、地圖戰結果表。畫面在 `tuning/Skill*.tsx`、`GroupPanel.tsx`、`SkillIdsEditor.tsx`、`SimPanel.tsx`。
// API 是 NW-2a 的 `/api/tuning/*`（`docs/phases/PhaseNW-2a報告.md` 第 1 節）；欄位一律由後端給，這裡不寫死欄位清單。
import type {
  TuningApplyIn,
  TuningBudgetResult,
  TuningCheckResult,
  TuningFieldView,
  TuningGroupFilter,
  TuningGroupOp,
  TuningGroupRow,
  TuningGroupTarget,
  TuningMapSimResult,
  TuningObjectSummary,
  TuningSimOptions,
  TuningSkillFacets,
} from "../api/types";
import { editKey, kindOfValues, row, type Edit, type Edits, type SimRow } from "./model";

// ---- 技能表單：依區塊分組 ----------------------------------------------------

export interface FormSection {
  key: string;
  title: string;
  fields: { field: TuningFieldView; label: string }[];
}

const EFFECT_RE = /^(effects\[\d+\])/;

/**
 * 依區塊分組（規格 B2）：消耗與冷卻／形狀與射程／效果 1、2…（標題寫原語中文名）／第二段／變奏／其他。
 * 效果欄位的後端標籤是「效果 1（傷害）：武器倍率」：冒號前當區塊標題、冒號後當欄位名；第二段與變奏保留完整標籤。
 * 順序照後端欄位的出現順序（區塊第一次出現的位置）。
 */
export function skillSections(fields: readonly TuningFieldView[]): FormSection[] {
  const out: FormSection[] = [];
  const at = new Map<string, FormSection>();
  const push = (key: string, title: string, field: TuningFieldView, label: string) => {
    let sec = at.get(key);
    if (sec === undefined) {
      sec = { key, title, fields: [] };
      at.set(key, sec);
      out.push(sec);
    }
    sec.fields.push({ field, label });
  };
  for (const f of fields) {
    const effect = EFFECT_RE.exec(f.path);
    if (effect !== null) {
      const head = effect[1]!;
      const cut = f.label_zh.indexOf("：");
      // 巢狀效果（例 effects[0].then[1].dice）併在外層效果的區塊裡，欄位名保留完整標籤
      const nested = f.path.slice(head.length).includes("[");
      const index = Number(/\d+/.exec(head)![0]) + 1;
      const title = !nested && cut > 0 ? f.label_zh.slice(0, cut) : `效果 ${index}`;
      push(head, title, f, nested || cut < 0 ? f.label_zh : f.label_zh.slice(cut + 1));
      const sec = at.get(head)!;
      if (!nested && sec.title !== title) sec.title = title; // 外層欄位出現時，標題換成有原語名的那個
    } else if (f.path.startsWith("followup.")) push("followup", "第二段", f, f.label_zh);
    else if (f.path.startsWith("variants[")) push("variants", "變奏", f, f.label_zh);
    else if (f.path.startsWith("shape.")) push("shape", "形狀與射程", f, f.label_zh);
    else if (f.path === "ap_cost" || f.path.startsWith("cost.") || f.path === "stance_upkeep") push("cost", "消耗與冷卻", f, f.label_zh);
    else push("other", "其他（暴擊、條件、觸發、陷阱）", f, f.label_zh);
  }
  return out;
}

// ---- 骰子 ±1 級 --------------------------------------------------------------

/** 骰子階梯上走 `steps` 級（和後端分組改 `_dice_step` 同一個規則：不在階梯上、走出階梯 → `null`）。 */
export function diceStep(ladder: readonly string[], current: string, steps: number): string | null {
  const i = ladder.indexOf(current);
  if (i < 0) return null;
  const j = i + steps;
  return j >= 0 && j < ladder.length ? ladder[j]! : null;
}

/** 骰子按鈕不能按的原因（`null` ＝ 可以）。 */
export function diceStepProblem(ladder: readonly string[] | null, current: string, steps: number): string | null {
  if (ladder === null) return "讀不到骰子階梯";
  if (!ladder.includes(current)) return `${current} 不在骰子階梯上，請直接打字`;
  return diceStep(ladder, current, steps) === null ? (steps > 0 ? "已經是最強的一級" : "已經是最弱的一級") : null;
}

// ---- 預算比例條 --------------------------------------------------------------

/** 比例條的刻度上限（‰）：0～150%，超過就停在右端。 */
export const BUDGET_SCALE_MAX = 1500;

export interface BudgetGeometry {
  /** 比例的位置（0～100，%）。 */
  at: number;
  bandLeft: number;
  bandWidth: number;
  /** 超出刻度（> 150%）。 */
  clipped: boolean;
}

export function budgetGeometry(ratio: number | null, min: number, max: number): BudgetGeometry {
  const pct = (v: number) => Math.max(0, Math.min(100, (v / BUDGET_SCALE_MAX) * 100));
  return {
    at: ratio === null ? 0 : pct(ratio),
    bandLeft: pct(min),
    bandWidth: pct(max) - pct(min),
    clipped: ratio !== null && ratio > BUDGET_SCALE_MAX,
  };
}

/** 判定 → 顏色 class 與中文（合格／超出預算／過弱／算不出來）。 */
export function verdictClass(verdict: TuningBudgetResult["verdict"] | TuningGroupRow["verdict"]): string {
  return verdict === "ok" ? "tn-v-ok" : verdict === "over" ? "tn-v-over" : verdict === "weak" ? "tn-v-weak" : "tn-v-error";
}

export function verdictText(verdict: TuningGroupRow["verdict"]): string {
  return { ok: "合格", over: "超出預算", weak: "過弱", error: "算不出來", skipped: "跳過" }[verdict];
}

/** ‰ → 「112.4%」。 */
export function ratioText(permille: number | null | undefined): string {
  if (permille === null || permille === undefined) return "—";
  return `${(permille / 10).toFixed(1)}%`;
}

/** 這招需要勾「我確定」嗎（超出合格區間、不在例外清單；後端驗證的 `needs_confirm_budget` 才是寫回的依據）。 */
export function budgetNeedsConfirm(b: TuningBudgetResult | null): boolean {
  return b !== null && (b.verdict === "over" || b.verdict === "weak") && !b.known_exception;
}

// ---- 技能清單的篩選 ----------------------------------------------------------

export type SkillFilter = TuningGroupFilter;

export const EMPTY_FILTER: SkillFilter = {};

/** 沒有任何條件（分組改不給「全部技能」）。 */
export function filterEmpty(f: SkillFilter): boolean {
  const lists = [f.tier, f.category, f.weapon_req, f.ap_cost, f.kind, f.shape, f.tags];
  const flags = [f.enemy_only, f.has_condition, f.ranged, f.single_damage];
  return lists.every((l) => l === undefined || l.length === 0) && flags.every((x) => x === undefined || x === null);
}

function inList<T>(allowed: readonly T[] | undefined, v: T): boolean {
  return allowed === undefined || allowed.length === 0 || allowed.includes(v);
}

function flagOk(want: boolean | null | undefined, have: boolean): boolean {
  return want === undefined || want === null || want === have;
}

/** 和後端分組改 `_matches` 同一套（全部條件都要符合；空的條件不篩）。 */
export function matchesFilter(s: TuningSkillFacets, f: SkillFilter): boolean {
  return (
    inList(f.tier, s.tier) &&
    inList(f.category, s.category) &&
    inList(f.weapon_req, s.weapon_req) &&
    (f.ap_cost === undefined || f.ap_cost.length === 0 || (s.ap_cost !== null && f.ap_cost.includes(s.ap_cost))) &&
    inList(f.kind, s.kind) &&
    inList(f.shape, s.shape) &&
    (f.tags ?? []).every((t) => s.tags.includes(t)) &&
    flagOk(f.enemy_only, s.enemy_only) &&
    flagOk(f.has_condition, s.has_condition) &&
    flagOk(f.ranged, s.ranged) &&
    flagOk(f.single_damage, s.single_damage ?? false)
  );
}

/** 技能清單：搜尋（中文名或 ID）＋篩選，依 ID 排序。 */
export function filterSkills(objects: readonly TuningObjectSummary[], query: string, f: SkillFilter): TuningObjectSummary[] {
  const q = query.trim().toLowerCase();
  return objects
    .filter((o) => o.skill != null && matchesFilter(o.skill, f))
    .filter((o) => q === "" || o.name_zh.toLowerCase().includes(q) || o.id.toLowerCase().includes(q))
    .sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
}

/** 篩選的一個選項（清單上方的切換鈕）。 */
export interface FilterChoice {
  key: string;
  label: string;
  /** 套上去：回傳新的篩選。 */
  apply(f: SkillFilter, on: boolean): SkillFilter;
  on(f: SkillFilter): boolean;
}

function listChoice<K extends "tier" | "category" | "ap_cost" | "kind", V extends NonNullable<SkillFilter[K]>[number]>(key: K, value: V, label: string): FilterChoice {
  return {
    key: `${key}:${String(value)}`,
    label,
    on: (f) => ((f[key] ?? []) as V[]).includes(value),
    apply: (f, on) => {
      const cur = ((f[key] ?? []) as V[]).filter((x) => x !== value);
      return { ...f, [key]: on ? [...cur, value] : cur };
    },
  };
}

function flagChoice(key: "enemy_only" | "has_condition" | "ranged", value: boolean, label: string): FilterChoice {
  return {
    key: `${key}:${String(value)}`,
    label,
    on: (f) => f[key] === value,
    apply: (f, on) => ({ ...f, [key]: on ? value : null }),
  };
}

/** 篩選列（規格 B1：階級、武器技／法術、近戰／遠程、AP、主動／被動、敵人專用、有條件）。 */
export const FILTER_ROWS: readonly { label: string; choices: readonly FilterChoice[] }[] = [
  { label: "階級", choices: [1, 2, 3].map((t) => listChoice("tier", t, `${t} 階`)) },
  { label: "類別", choices: [listChoice("category", "weapon", "武器技"), listChoice("category", "spell", "法術")] },
  { label: "距離", choices: [flagChoice("ranged", false, "近戰"), flagChoice("ranged", true, "遠程")] },
  { label: "AP", choices: [1, 2, 3].map((a) => listChoice("ap_cost", a, `${a} AP`)) },
  {
    label: "種類",
    choices: [listChoice("kind", "active", "主動"), listChoice("kind", "passive", "被動"), listChoice("kind", "stance", "姿態"), listChoice("kind", "reaction", "反應")],
  },
  { label: "其他", choices: [flagChoice("enemy_only", true, "敵人專用"), flagChoice("enemy_only", false, "不含敵人專用"), flagChoice("has_condition", true, "有條件")] },
];

// ---- 分組改 ------------------------------------------------------------------

export const MAX_GROUP = 100;

export const GROUP_TARGETS: readonly { key: TuningGroupTarget; label: string }[] = [
  { key: "damage_base", label: "基礎傷害（沒有條件的傷害效果）" },
  { key: "damage_conditional", label: "條件段傷害（帶條件的傷害效果）" },
  { key: "damage_all", label: "所有傷害效果" },
  { key: "ap_cost", label: "AP 消耗" },
  { key: "cost.stamina", label: "耐力消耗" },
  { key: "cost.mana", label: "法力消耗" },
  { key: "cost.cooldown", label: "冷卻（回合）" },
  { key: "shape.range", label: "射程" },
];

export const GROUP_OPS: readonly { key: TuningGroupOp["kind"]; label: string; hint: string }[] = [
  { key: "ladder", label: "±N 級", hint: "傷害：武器倍率照倍率階梯、骰子照骰子階梯；其他欄位等於 ±N" },
  { key: "scale_permille", label: "× ‰ 倍率", hint: "新值 ＝ 舊值 × N ÷ 1000，四捨五入（.5 進位）；骰子不能乘倍率（會跳過，請改用 ±級）" },
  { key: "add", label: "± 加減", hint: "直接加減 N，再夾在允許範圍內" },
  { key: "set", label: "設成", hint: "全部設成 N" },
];

/** 分組預覽不能按的原因（`null` ＝ 可以）。`filterCount`＝目前篩選選到幾招（清單算的；後端預覽會再算一次）。 */
export function groupProblem(useFilter: boolean, f: SkillFilter, manual: readonly string[], filterCount: number, valueText: string): string | null {
  if (useFilter ? filterEmpty(f) : manual.length === 0) return "至少選一個篩選條件或手動勾選技能（不提供「全部技能」）";
  const n = useFilter ? filterCount : manual.length;
  if (n === 0) return "沒有選到任何技能";
  if (n > MAX_GROUP) return `一次最多 ${MAX_GROUP} 招（現在 ${n} 招），請加篩選條件`;
  if (!/^-?\d+$/.test(valueText.trim())) return "N 要填整數";
  return null;
}

/** 預覽列的改動放進草稿（逐招逐欄；跳過的列不放）。標籤先用路徑，存草稿後由後端換成中文標籤。 */
export function mergeGroupRows(edits: Edits, rows: readonly TuningGroupRow[]): Edits {
  const next: Record<string, Edit> = { ...edits };
  for (const r of rows) {
    if (r.verdict === "skipped") continue;
    for (const c of r.changes) {
      const kind = kindOfValues(c.old, c.new);
      next[editKey(c.file, c.path)] = {
        file: c.file,
        path: c.path,
        old: c.old,
        text: c.new === null ? "" : Array.isArray(c.new) ? c.new.join(",") : String(c.new),
        label_zh: `${r.name_zh} ${c.path}`,
        object_id: r.skill_id,
        ...(kind !== undefined ? { kind } : {}),
      };
    }
  }
  return next;
}

// ---- 寫回前要勾的「我確定」 --------------------------------------------------

/** 還沒勾「我確定」的項目 → 寫回停用的原因（`null` ＝ 都勾了或不需要）。 */
export function confirmBlock(check: TuningCheckResult | null, budgetOk: ReadonlySet<string>, movesOk: ReadonlySet<string>): string | null {
  if (check === null) return null;
  const budget = (check.needs_confirm_budget ?? []).filter((f) => !budgetOk.has(f.skill_id));
  const moves = (check.needs_confirm_min_moves ?? []).filter((f) => !movesOk.has(f.unit_id));
  const parts = [
    ...budget.map((f) => `「${f.name_zh}」預算 ${f.ratio_text} ${f.verdict === "over" ? "超出" : "低於"}合格區間`),
    ...moves.map((f) => `「${f.name_zh}」低於 #149 的招數下限`),
  ];
  return parts.length === 0 ? null : `${parts.join("；")}：要寫回請勾「我確定」`;
}

/** 寫回時帶的確認清單：恰好是驗證回的那幾個（後端要求完全相符）。 */
export function applyConfirm(check: TuningCheckResult | null): TuningApplyIn {
  return {
    confirm_budget: (check?.needs_confirm_budget ?? []).map((f) => f.skill_id),
    confirm_min_moves: (check?.needs_confirm_min_moves ?? []).map((f) => f.unit_id),
  };
}

// ---- 地圖戰（規格 5.6、B6） --------------------------------------------------

/** 規模：小＝24 場、中＝80 場（每張圖的種子數＝場數 ÷ 張數，無條件捨去）。 */
export const MAP_SCALES: readonly { key: "small" | "medium"; label: string; battles: number }[] = [
  { key: "small", label: "小", battles: 24 },
  { key: "medium", label: "中", battles: 80 },
];

export const MAX_MAPS = 3;

export function mapSeedsFor(battles: number, maps: number): number {
  return Math.max(1, Math.floor(battles / Math.max(1, maps)));
}

/** 地圖戰的規模問題：沒選地圖、超過 3 張、種子數不對、超過上限。 */
export function mapScaleProblem(options: TuningSimOptions, maps: number, seeds: number): string | null {
  if (maps === 0) return "至少選一張地圖";
  if (maps > MAX_MAPS) return `一次最多 ${MAX_MAPS} 張地圖`;
  if (!Number.isInteger(seeds) || seeds < 1) return "種子數要填 1 以上的整數";
  const n = maps * seeds;
  if (n > options.max_battles) return `一次最多 ${options.max_battles} 場（現在 ${n} 場），請少選地圖或減少種子數`;
  return null;
}

const TEAM_ZH = { ally: "我方", enemy: "敵方" } as const;

/**
 * 地圖戰結果表：總覽（勝率、平均輪數、我方倒下率）→ 受測招每一招（我方／敵方分開）：每回合施放率（分子＝施放次數、
 * 分母＝裝了這招的單位的行動回合數）與每場平均次數 → 各地圖勝率。招式取改前改後聯集，依（招、陣營）排序。
 */
export function mapSimRows(result: TuningMapSimResult, skillName: (id: string) => string, mapName: (id: string) => string): SimRow[] {
  const { before: b, after: a } = result;
  const rows: SimRow[] = [
    row("總覽", "我方勝率", "rate", [b.wins, b.n, b.small], [a.wins, a.n, a.small]),
    row("總覽", "平均輪數", "avg", [b.rounds, b.n, b.small], [a.rounds, a.n, a.small]),
    row("總覽", "我方倒下率（倒下人次／出場人數）", "rate", [b.downed, b.allies], [a.downed, a.allies]),
  ];
  const keys = [...new Set([...b.skills, ...a.skills].map((s) => `${s.skill}|${s.team}`))].sort();
  for (const key of keys) {
    const [skill, team] = key.split("|") as [string, "ally" | "enemy"];
    const sb = b.skills.find((s) => s.skill === skill && s.team === team);
    const sa = a.skills.find((s) => s.skill === skill && s.team === team);
    const group = `「${skillName(skill)}」（${TEAM_ZH[team]}）`;
    rows.push(row(group, "每回合施放率（施放次數／裝了這招的單位的行動回合）", "rate", [sb?.casts ?? 0, sb?.turns ?? 0], [sa?.casts ?? 0, sa?.turns ?? 0]));
    rows.push(row(group, "每場平均次數", "avg", [sb?.casts ?? 0, sb?.battles ?? 0, (sb?.turns ?? 0) < 30], [sa?.casts ?? 0, sa?.battles ?? 0, (sa?.turns ?? 0) < 30]));
  }
  const maps = [...new Set([...b.maps, ...a.maps].map((m) => m.build))];
  for (const id of maps) {
    const mb = b.maps.find((m) => m.build === id);
    const ma = a.maps.find((m) => m.build === id);
    rows.push(row("各地圖勝率", mapName(id), "rate", [mb?.wins ?? 0, mb?.n ?? 0], [ma?.wins ?? 0, ma?.n ?? 0]));
  }
  return rows;
}

/** 受測招在改前改後都沒有人用（行動回合 0）：提示改用「裝到 build」。 */
export function unusedProbes(result: TuningMapSimResult, probes: readonly string[]): string[] {
  const used = new Set([...result.before.skills, ...result.after.skills].filter((s) => s.turns > 0).map((s) => s.skill));
  return probes.filter((p) => !used.has(p));
}

/** 草稿改到的技能（地圖戰預設的受測招；依 ID 排序）。 */
export function editedSkills(edits: Edits): string[] {
  return [...new Set(Object.values(edits).filter((e) => e.file.startsWith("skills/")).map((e) => e.object_id))].sort();
}
