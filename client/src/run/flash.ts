// 靈感閃現的純函式（Phase 3W-6；規則在 06 6.34.3，數值由後端 `flash_rules` 提供，這裡不寫死）。
// 3W-R2：可重閃的欄、可傳承的目標、可帶走的變化與上限、不能傳承的原因都由後端下發，這裡只讀。
// 文字集中在這裡：價格說明、技能卡的「已閃 N／5 次」、稀有度提示、溶掉確認、傳承條件。
import type { FlashOption, FlashPreview, RunChoice, RunHero, SkillCard, SkillFlash } from "../api/types";
import { autoUnequip } from "./flashChoice";
import { ownedCards } from "./loadout";
import { percent } from "../battle/previewText";
import { gameRules } from "../battle/glossary";

/** 技能卡上的稀有度提示（玩法 PM 3W-4b 定案；稀有度只是標記，不是門檻）。 */
export const RARITY_HINT = "稀有度表示這招長得多複雜，不代表強度。強度看角色階級與閃現次數。";
/** 可以閃現時的提示。 */
export const CAN_FLASH_TEXT = "可以閃現了";
/** 升階後第 N 格（大變化，N＝`rules.major_flash`；HC-6b）還不是轉型時的提示（3W-5 旗標 `reflash_transform_hint`）。 */
export function transformHint(major: number = gameRules().major_flash): string {
  return `可以重閃第 ${major} 格轉型`;
}
export function transformHintTip(major: number = gameRules().major_flash): string {
  return `角色升階後，新的轉型選擇變多了；在營火重閃第 ${major} 次的變化，可能出現轉型。`;
}

/** 閃現規則（後端 `flash_rules`，`flash_templates.yaml`；HC-3 起回應一定有，前端不留備用值）。 */
type Rules = RunHero["flash_rules"];

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

/** 「已閃 N／5 次」；完整技能寫「完整技能」。沒拿到規則（只給閃現狀態的卡）時只寫次數。 */
export function flashCountText(f: SkillFlash | undefined, rules: Rules | null | undefined): string {
  if (f === undefined) return "";
  if (f.complete) return "完整技能・不能再閃現";
  return rules == null ? `已閃 ${f.flashes} 次` : `已閃 ${f.flashes}／${rules.max_flashes} 次`;
}

/** 「可以閃現了」只在真的能閃（先上場用過、沒閃滿）時顯示。 */
export function showCanFlash(f: SkillFlash | undefined): boolean {
  return f !== undefined && !f.complete && f.can_flash;
}

/** 這招目前沒有任何合法閃現選項時的灰字（FL-1c，06 6.34「費用方向」第 7 點；伺服器 `flash_problem_zh` 同一句）。 */
export const NO_FLASH_OPTIONS_TEXT = "這招目前沒有可以閃的變化";

/** 伺服器實際算過、這一次閃現一個合法選項都沒有（`flash_available: false`）：面板整列標灰、不能按。 */
export function noFlashOptions(f: SkillFlash | undefined): boolean {
  return f !== undefined && f.flash_available === false;
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

export function openMode(r: Rules): FlashMode {
  return { category: null, cost: r.open_cost, options: r.open_options };
}

export function focusedMode(r: Rules, category: string): FlashMode {
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
  /** 伺服器實際算過、重閃這格一個合法選項都沒有（RR-1，比照 FL-1c `flash_available`）：按鈕標灰、不能按。 */
  none: boolean;
  /** 不能重閃這格的灰字（伺服器 `problem_zh`）。 */
  problem: string | null;
}

/** 重閃某一格沒有任何合法選項時的灰字（RR-1；伺服器 `problem_zh` 同一句；玩法 PM 11-13 定稿，TXT-2）。 */
export const NO_REFLASH_OPTIONS_TEXT = "這一格目前沒有可以重閃的變化";

/** 這招可以重閃的格子（後端 `reflash_slots`）；完整技能的調整欄（0）標「調整欄」。 */
export function reflashSlots(f: SkillFlash | undefined): ReflashSlot[] {
  if (f === undefined) return [];
  return (f.reflash_slots ?? []).map((s) => {
    const record = f.records.find((r) => r.nth === s.slot);
    const label = s.slot === 0 || record === undefined ? "調整欄" : recordLine(record);
    const none = s.available === false;
    return { slot: s.slot, label, transformHint: s.transform_hint, none, problem: none ? (s.problem_zh ?? NO_REFLASH_OPTIONS_TEXT) : null };
  });
}

/** 營火重閃列表：有格子可重閃的技能。 */
export function reflashable(hero: RunHero): OwnedSkill[] {
  return ownedSkills(hero).filter((s) => reflashSlots(s.flash).length > 0);
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

/** 能接受傳承的技能（後端 `inherit_target`：還沒閃過、不是完整技能）。 */
export function inheritTargets(hero: RunHero): OwnedSkill[] {
  return ownedSkills(hero).filter((s) => s.flash?.inherit_target === true);
}

/** 可以帶走的變化（後端 `carryable`；大變化、轉型、完整技能的調整欄都不行）。 */
export function carryable(f: SkillFlash | undefined): SkillFlash["records"] {
  if (f === undefined) return [];
  const allowed = new Set(f.carryable ?? []);
  return f.records.filter((r) => allowed.has(r.nth));
}

/** 這招不能傳承給別招的原因（後端 `inherit_problem_zh`）；可以時 `undefined`。 */
export function inheritProblem(f: SkillFlash | undefined): string | undefined {
  if (f === undefined) return "這招沒有可以帶走的小變化";
  return f.inherit_problem_zh ?? undefined;
}

/** 最多帶走幾個小變化（後端 `flash_rules.max_carry`）。 */
export function maxCarry(rules: Rules): number {
  return rules.max_carry;
}

export function toggleCarry(picked: readonly number[], nth: number, limit: number): number[] {
  if (picked.includes(nth)) return picked.filter((n) => n !== nth);
  return picked.length >= limit ? [...picked] : [...picked, nth];
}

export function inheritChoice(skill: string, source: string, records: readonly number[]): RunChoice {
  return { kind: "inherit", skill, source, records: [...records].sort((a, b) => a - b) };
}

/** 閃現選擇畫面「不指定」那格的說明（至少涵蓋幾類照伺服器 `rules.flash_open_min_categories`；HC-6b）。 */
export function openMixText(minCategories: number = gameRules().flash_open_min_categories): string {
  return `混合各類變化，至少涵蓋 ${minCategories} 類`;
}

/** 閃現選擇畫面：這次是大變化時的說明（第幾次照 `rules.major_flash`；HC-6b）。 */
export function majorNoteText(major: number = gameRules().major_flash): string {
  return `第 ${major} 次是大變化；指定類別時，轉型保底會另外列在最後並標「轉型」。`;
}

/** 傳承的規則句；最多帶走幾個照伺服器（`flash_rules.max_carry`；HC-6b）。 */
export function inheritRuleText(limit: number): string {
  return `傳承：把另一招的小變化（最多 ${limit} 個）帶給這招，算已閃次數；舊技能會消失，花掉的靈感點不退。完整技能不能接受傳承。`;
}

/** 傳承表單第 1 步：帶走的小變化依序成為新技能的第 1、2…次（列到上限；HC-6b）。 */
export function inheritStepText(limit: number): string {
  const order = Array.from({ length: limit }, (_, i) => i + 1).join("、");
  return `1. 帶走哪些小變化（最多 ${limit} 個，依序成為新技能的第 ${order} 次）`;
}

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

/** 選好了沒：要卸下時先選卸下哪一招；姿態欄自動換下原姿態（FL-1b 8.3），不用選。 */
export function pickReady(o: FlashOption | undefined, unequip: string | null): boolean {
  if (o === undefined) return false;
  return !needsUnequip(o) || unequip !== null || autoUnequip(o) !== null;
}

export function pickChoice(o: FlashOption, unequip: string | null): RunChoice {
  return { kind: "flash_pick", pick: o.index, unequip: needsUnequip(o) ? (unequip ?? autoUnequip(o)) : null };
}

export function previewProblem(p: FlashPreview | null): string | null {
  return p?.problem_zh ?? null;
}

// ---- 完整技能三選一 ----------------------------------------------------------------------

export const COMPLETE_BADGE = "完整技能";
/**
 * 完整技能三選一畫面的說明（06 6.34.6）。預算加成照伺服器（`/api/glossary` 的 `rules.complete_budget_permille`，‰；HC-3）；
 * 6F-7：畫面上顯示成百分比（+12%），內部照舊千分比。
 */
export function completeIntro(
  budgetPermille: number = gameRules().complete_budget_permille,
  flashes: number = gameRules().complete_flashes,
): readonly string[] {
  return [
    `完整技能是整招設計好的技能，強度視為已經閃現 ${flashes} 次（預算 +${percent(budgetPermille)}）。`,
    "完整技能不能再閃現；之後可以在營火重閃它的「調整欄」，換一個小變化。",
    "三張都不想要可以都不拿，技能不變。",
  ];
}

export function completeSkipText(): string {
  return "目前：都不拿（技能不變）。";
}
