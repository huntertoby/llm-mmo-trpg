// 技能卡常駐 3 行的資料（Phase 6A-1，去文字化②：`docs/archive/art/去文字化移植需求.md` 第 2 節；純函式）。
// 第 1 行名稱；第 2 行一排圖示＋數字（AP 圓點、法力／耐力、冷卻、射程、時機）；第 3 行一行效果數字
// （傷害數字＋元素、位移格數、狀態回合……＋縮放屬性）。數字來自伺服器的結構化欄位 `card.stats`，
// 每個圖示的說明卡用卡片原本的句子（`cost`、`shape`、`effects`、`formula_lines`），不另外寫新的字。
import type { SkillCard } from "../api/types";
import { ATTRIBUTES } from "../run/flow";

export type CardStats = SkillCard["stats"];
export type CostStat = CardStats["costs"][number];
export type EffectStat = CardStats["effects"][number];

/** 卡片的結構化欄位；舊的快照（fixture、還沒更新的伺服器）沒有時回傳 `null`，卡片退回只顯示句子。 */
export function cardStats(card: SkillCard): CardStats | null {
  return (card as { stats?: CardStats | null }).stats ?? null;
}

export type ChipIcon =
  | "ap"
  | "mana"
  | "stamina"
  | "hp"
  | "source"
  | "uses"
  | "cooldown"
  | "range"
  | "reaction"
  | "trigger"
  | "delayed"
  | "activation"
  | "drawback";

export interface Chip {
  key: string;
  icon: ChipIcon;
  /** 圖示旁的字；AP 用圓點時為空字串。 */
  label: string;
  /** AP 的圓點數（只有 AP）。 */
  pips?: number;
  /** 說明卡的文字（卡片原本的句子）。 */
  hint: string;
}

/** AP 超過這麼多就改寫數字（圓點太長）。 */
const MAX_AP_PIPS = 4;

const COST_ICON: Readonly<Partial<Record<CostStat["kind"], ChipIcon>>> = {
  mana: "mana",
  stamina: "stamina",
  hp_percent: "hp",
  source: "source",
  uses_per_battle: "uses",
  self_status: "drawback",
  overdraft: "drawback",
  upkeep: "drawback",
  backlash: "drawback",
};

const TIMING_LABEL: Readonly<Record<NonNullable<CardStats["timing"]>, string>> = {
  reaction: "反應",
  trigger: "觸發",
  delayed: "延遲",
  activation: "啟動",
};

function timingHint(card: SkillCard, label: string): string {
  return card.timing ?? card.activation ?? card.followup ?? label;
}

/** 第 2 行：AP、資源、冷卻、射程、時機、其他代價（每個都有說明卡）。 */
export function chipLine(card: SkillCard): Chip[] {
  const stats = cardStats(card);
  if (stats === null) return [];
  const chips: Chip[] = [];
  const sentence = (c: CostStat) => card.cost[c.index] ?? c.label;
  const ap = stats.costs.find((c) => c.kind === "ap");
  if (ap !== undefined && ap.value !== null) {
    const pips = ap.value <= MAX_AP_PIPS;
    chips.push({ key: "ap", icon: "ap", label: pips ? "" : String(ap.value), ...(pips ? { pips: ap.value } : {}), hint: sentence(ap) });
  }
  const tail: Chip[] = [];
  for (const c of stats.costs) {
    const icon = COST_ICON[c.kind];
    if (icon === undefined) continue;
    const chip = { key: `cost:${c.index}`, icon, label: c.label, hint: sentence(c) };
    (icon === "drawback" ? tail : chips).push(chip);
  }
  const cd = stats.costs.find((c) => c.kind === "cooldown");
  if (cd !== undefined) chips.push({ key: "cooldown", icon: "cooldown", label: cd.label, hint: sentence(cd) });
  if (stats.range !== null || stats.range_weapon) {
    chips.push({ key: "range", icon: "range", label: stats.range_weapon ? "武器" : String(stats.range), hint: card.shape });
  }
  if (stats.timing != null) {
    const label = TIMING_LABEL[stats.timing];
    chips.push({ key: "timing", icon: stats.timing, label, hint: timingHint(card, label) });
  }
  return [...chips, ...tail];
}

export type EffectIcon = "damage" | "heal" | "shield" | "move" | "status" | "surface" | "summon" | "stack";

export interface EffectChip {
  key: string;
  icon: EffectIcon;
  label: string;
  /** 數字後面的小字：元素、狀態或表面名、單位、「2 擊」。 */
  tag: string;
  /** 元素代碼（上色用）；沒有為 `null`。 */
  element: string | null;
  /** 滑過數字看的說明：效果句＋算式。 */
  hint: string;
  /** BS-2：這個效果本場不會發動（帶整場固定條件、條件不成立；`conditionOff` 的 `effects`）。 */
  off?: true;
}

export interface EffectLine {
  items: EffectChip[];
  /** 縮放屬性（有傷害、治療、護盾時才列）：`[{ id: "str", label: "力量" }]`。 */
  scaling: { id: string; label: string }[];
  /** 沒有可以用數字表示的效果（修正、規則改變……）：改放第一句的字（一行，超出省略）。 */
  fallback: string | null;
}

const FORMULA_PREFIX: Readonly<Partial<Record<EffectStat["category"], string>>> = {
  damage: "傷害算法",
  heal: "治療算法",
  shield: "護盾算法",
};

function effectHint(card: SkillCard, e: EffectStat): string {
  const lines = [card.effects[e.index] ?? ""];
  const prefix = FORMULA_PREFIX[e.category];
  if (prefix !== undefined) lines.push(...(card.formula_lines ?? []).filter((l) => l.startsWith(prefix)));
  return lines.filter((l) => l !== "").join("\n");
}

function effectTag(e: EffectStat): string {
  if (e.category === "damage") return e.element_zh ?? (e.weapon === true ? "武器" : "");
  const name = e.name_zh ?? "";
  const unit = e.label !== null && e.unit !== null ? e.unit : "";
  return name !== "" && unit !== "" ? `${unit}・${name}` : name || unit;
}

const NO_OFF: ReadonlySet<number> = new Set();

const same = (a: EffectStat, b: EffectStat) =>
  a.category === b.category && a.label === b.label && a.element === b.element && a.name_zh === b.name_zh;

/** 第 3 行：效果數字（相鄰而且完全相同的效果——連打——合成一個「N 擊」）。
 *  `off`（BS-2）：本場不會發動的效果位置；標灰的和沒標灰的不合併（例：孤狼撲擊兩段 ×1，第二段帶獨狼）。 */
export function effectLine(card: SkillCard, off: ReadonlySet<number> = NO_OFF): EffectLine {
  const stats = cardStats(card);
  const items: EffectChip[] = [];
  let numeric = false;
  if (stats !== null) {
    let prev: EffectStat | null = null;
    let run = 1;
    for (const e of stats.effects) {
      if (e.category === "other") continue;
      if (prev !== null && same(prev, e) && off.has(prev.index) === off.has(e.index) && items.length > 0) {
        run += 1;
        const last = items[items.length - 1]!;
        last.tag = `${effectTag(e)}${effectTag(e) === "" ? "" : "・"}${run} 擊`;
        continue;
      }
      run = 1;
      prev = e;
      if (e.category in FORMULA_PREFIX) numeric = true;
      items.push({
        key: `effect:${e.index}`,
        icon: e.category,
        label: e.label ?? "",
        tag: effectTag(e),
        element: e.element ?? null,
        hint: effectHint(card, e),
        ...(off.has(e.index) ? { off: true as const } : {}),
      });
    }
  }
  const attrs = numeric ? (stats?.scaling_attrs ?? card.scaling_attrs) : [];
  const scaling = attrs.map((id) => ({ id, label: ATTRIBUTES.find((a) => a.id === id)?.label ?? id }));
  const first = card.effects[0] ?? card.modifiers[0] ?? null;
  return { items, scaling, fallback: items.length === 0 ? first : null };
}
