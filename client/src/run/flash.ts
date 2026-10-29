// 靈感閃現的純函式（Phase 3W-6；規則在 06 6.34.3，數值由後端 `flash_rules` 提供，這裡不寫死）。
// 文字集中在這裡：價格說明、技能卡的「已閃 N／5 次」、稀有度提示、溶掉確認、傳承條件。
import type { FlashOption, FlashPreview, PendingFlash, RunChoice, RunHero, SkillCard, SkillFlash } from "../api/types";
import { ownedCards } from "./loadout";

/** 技能卡上的稀有度提示（玩法 PM 3W-4b 定案；稀有度只是標記，不是門檻）。 */
export const RARITY_HINT = "稀有度表示這招長得多複雜，不代表強度。強度看角色階級與閃現次數。";
/** 可以閃現時的提示。 */
export const CAN_FLASH_TEXT = "可以閃現了";
/** 升階後第 3 格（大變化）還不是轉型時的提示（3W-5 旗標 `reflash_transform_hint`）。 */
export const TRANSFORM_HINT = "可以重閃第 3 格轉型";
export const TRANSFORM_HINT_TIP = "角色升階後，新的轉型選擇變多了；在營火重閃第 3 次的變化，可能出現轉型。";

type Rules = RunHero["flash_rules"];

/** 後端沒給規則時的備用（舊回應）；數值與 `flash_templates.yaml` 初值相同。 */
const FALLBACK = { open_cost: 1, open_options: 4, focused_cost: 2, focused_options: 3, max_flashes: 5, major_flash: 3 };

export function rulesOf(rules: Rules | undefined) {
  return { ...FALLBACK, ...(rules ?? {}) };
}

/** 一招技能的閃現狀態（依目前 ID；備用技能也找得到）。 */
export function flashOf(hero: RunHero, skillId: string): SkillFlash | undefined {
  return (hero.flash ?? []).find((f) => f.skill_id === skillId);
}

export interface OwnedSkill {
  card: SkillCard;
  flash: SkillFlash | undefined;
  equipped: boolean;
}

/** 所有學會的技能（裝備＋備用），含閃現狀態。 */
export function ownedSkills(hero: RunHero): OwnedSkill[] {
  const equipped = new Set(hero.skills.map((s) => s.id));
  return [...ownedCards(hero).values()].map((card) => ({ card, flash: flashOf(hero, card.id), equipped: equipped.has(card.id) }));
}

// ---- 技能卡上的文字 ----------------------------------------------------------------------

/** 「已閃 N／5 次」；完整技能寫「完整技能」。 */
export function flashCountText(f: SkillFlash | undefined, rules: Rules | undefined): string {
  if (f === undefined) return "";
  if (f.complete) return "完整技能・不能再閃現";
  return `已閃 ${f.flashes}／${rulesOf(rules).max_flashes} 次`;
}

/** 「可以閃現了」只在真的能閃（先上場用過、沒閃滿）時顯示。 */
export function showCanFlash(f: SkillFlash | undefined): boolean {
  return f !== undefined && !f.complete && f.can_flash;
}

/** 變化歷程的一行：「第 2 次・連段：多打一下（重閃 1 次）」。 */
export function recordLine(r: SkillFlash["records"][number]): string {
  const tag = r.source === "transform" ? "轉型" : r.source === "major" ? "大變化" : r.category_zh;
  const again = r.reflashes > 0 ? `（重閃 ${r.reflashes} 次）` : "";
  return `第 ${r.nth} 次・${tag}：${r.summary_zh}${again}`;
}

// ---- 價格與類別 --------------------------------------------------------------------------

export interface FlashMode {
  /** 不指定（`null`）或指定的類別 ID。 */
  category: string | null;
  cost: number;
  options: number;
}

export function openMode(rules: Rules | undefined): FlashMode {
  const r = rulesOf(rules);
  return { category: null, cost: r.open_cost, options: r.open_options };
}

export function focusedMode(rules: Rules | undefined, category: string): FlashMode {
  const r = rulesOf(rules);
  return { category, cost: r.focused_cost, options: r.focused_options };
}

/** 類別按鈕文字：「連段（2）」。 */
export function categoryLabel(c: FlashPreview["categories"][number]): string {
  return `${c.name_zh}（${c.count}）`;
}

/** 這個類別能不能選：至少有 1 個合法變化。 */
export function categorySelectable(c: FlashPreview["categories"][number]): boolean {
  return c.count > 0;
}

/** 付不起的原因（點數不足）；付得起為 `null`。 */
export function costProblem(insight: number, mode: FlashMode): string | null {
  return insight >= mode.cost ? null : `靈感點不足（要 ${mode.cost} 點，目前 ${insight} 點）`;
}

/** 出題前的說明：一定會扣點、一定要選一個。 */
export function flashWarning(mode: FlashMode): string {
  return `按下確定會立刻扣 ${mode.cost} 點靈感，接著從 ${mode.options} 個變化裡一定要選 1 個，不能放棄、不會退點。`;
}

export function flashConfirmLabel(mode: FlashMode): string {
  return `確定，扣 ${mode.cost} 點並出題`;
}

/** 送出閃現／重閃的選擇。`slot`：`null` ＝ 閃現；數字 ＝ 重閃第幾次（完整技能 0）。 */
export function flashChoice(skill: string, slot: number | null, category: string | null): RunChoice {
  return { kind: "flash", skill, slot, category };
}

// ---- 重閃 --------------------------------------------------------------------------------

export interface ReflashSlot {
  slot: number;
  label: string;
  /** 這格是不是第 3 次大變化但還不是轉型（升階後建議重閃）。 */
  transformHint: boolean;
}

/** 這招可以重閃的格子：一般技能是已有的各次變化；完整技能只有「調整欄」（0）。 */
export function reflashSlots(f: SkillFlash | undefined, rules: Rules | undefined): ReflashSlot[] {
  if (f === undefined) return [];
  if (f.complete) return [{ slot: 0, label: "調整欄", transformHint: false }];
  const major = rulesOf(rules).major_flash;
  return f.records.map((r) => ({
    slot: r.nth,
    label: recordLine(r),
    transformHint: f.reflash_transform_hint && r.nth === major,
  }));
}

/** 營火重閃列表：有格子可重閃的技能。 */
export function reflashable(hero: RunHero): OwnedSkill[] {
  return ownedSkills(hero).filter((s) => reflashSlots(s.flash, hero.flash_rules).length > 0);
}

// ---- 溶掉 --------------------------------------------------------------------------------

/** 溶掉的確認文字：退幾點、這招會消失（06 6.34.3）。 */
export function dissolveConfirm(name: string, f: SkillFlash | undefined): string[] {
  const spent = f?.spent ?? 0;
  const refund = f?.dissolve_refund ?? 0;
  return [
    `溶掉「${name}」：這招會從技能庫消失，拿不回來。`,
    `這招共花了 ${spent} 點靈感，退回一半（無條件捨去）＝ ${refund} 點。`,
  ];
}

export function dissolveChoice(skill: string): RunChoice {
  return { kind: "dissolve", skill };
}

// ---- 傳承 --------------------------------------------------------------------------------

/** 能接受傳承的技能：還沒閃過、不是完整技能。 */
export function inheritTargets(hero: RunHero): OwnedSkill[] {
  return ownedSkills(hero).filter((s) => s.flash !== undefined && !s.flash.complete && s.flash.records.length === 0);
}

/** 可以帶走的小變化（大變化、轉型、完整技能的調整欄都不行）。 */
export function carryable(f: SkillFlash | undefined): SkillFlash["records"] {
  if (f === undefined || f.complete) return [];
  return f.records.filter((r) => r.source === "minor");
}


/** 最多帶走幾個小變化（第 3 次是大變化，所以是 major_flash − 1）。 */
export function maxCarry(rules: Rules | undefined): number {
  return rulesOf(rules).major_flash - 1;
}

export function toggleCarry(picked: readonly number[], nth: number, limit: number): number[] {
  if (picked.includes(nth)) return picked.filter((n) => n !== nth);
  return picked.length >= limit ? [...picked] : [...picked, nth];
}

export function inheritChoice(skill: string, source: string, records: readonly number[]): RunChoice {
  return { kind: "inherit", skill, source, records: [...records].sort((a, b) => a - b) };
}

export const INHERIT_RULE_TEXT =
  "傳承：把另一招的小變化（最多 2 個）帶給這招，算已閃次數；舊技能會消失，花掉的靈感點不退。完整技能不能接受傳承。";

// ---- 閃現選項 ----------------------------------------------------------------------------

/** 選項排序：一般選項照原順序，轉型保底排最後。 */
export function sortedOptions(options: readonly FlashOption[]): FlashOption[] {
  const rest = options.filter((o) => !o.transform);
  const transform = options.filter((o) => o.transform);
  return [...rest, ...transform];
}

/** 選項卡上方的標籤：類別名；大變化、轉型另標。 */
export function optionTag(o: FlashOption): string {
  if (o.transform || o.source === "transform") return "轉型";
  return o.source === "major" ? `大變化・${o.category_zh}` : o.category_zh;
}

/** 轉型讓技能換到已滿的欄位時，要先選卸下哪一招。 */
export function needsUnequip(o: FlashOption): boolean {
  return o.unequip_candidates.length > 0;
}

export function pickReady(o: FlashOption | undefined, unequip: string | null): boolean {
  if (o === undefined) return false;
  return !needsUnequip(o) || unequip !== null;
}

export function pickChoice(o: FlashOption, unequip: string | null): RunChoice {
  return { kind: "flash_pick", pick: o.index, unequip: needsUnequip(o) ? unequip : null };
}

export function pendingTitle(p: PendingFlash, name: string): string {
  const what = p.slot === null ? `第 ${p.nth} 次閃現${p.major ? "（大變化）" : ""}` : p.slot === 0 ? "重閃調整欄" : `重閃第 ${p.slot} 次`;
  const focus = p.category === null ? "不指定" : "指定類別";
  return `「${name}」${what}（${focus}，已扣 ${p.cost} 點）`;
}

/** 新舊卡片的差異行（預覽數字）：形狀、費用與每條效果／修正的變動。 */
export function cardDiff(before: SkillCard | undefined, after: SkillCard): string[] {
  if (before === undefined) return [];
  const lines: string[] = [];
  if (before.shape !== after.shape) lines.push(`形狀：${before.shape} → ${after.shape}`);
  if (before.cost.join("，") !== after.cost.join("，")) lines.push(`費用：${before.cost.join("，")} → ${after.cost.join("，")}`);
  const was = [...before.effects, ...before.modifiers.map((m) => `修正：${m}`)];
  const now = [...after.effects, ...after.modifiers.map((m) => `修正：${m}`)];
  for (const line of was) if (!now.includes(line)) lines.push(`原：${line}`);
  for (const line of now) if (!was.includes(line)) lines.push(`新：${line}`);
  return lines;
}

export function previewProblem(p: FlashPreview | null): string | null {
  return p?.problem_zh ?? null;
}

// ---- 完整技能三選一 ----------------------------------------------------------------------

export const COMPLETE_BADGE = "完整技能";
/** 完整技能三選一畫面的說明（06 6.34.6）。 */
export const COMPLETE_INTRO: readonly string[] = [
  "完整技能是整招設計好的技能，強度視為已經閃現 3 次（預算 +120‰）。",
  "完整技能不能再閃現；之後可以在營火重閃它的「調整欄」，換一個小變化。",
  "三張都不想要可以跳過，技能不變。",
];

export function completeSkipText(): string {
  return "目前：跳過（技能不變）。";
}
