// roguelite 一輪的流程狀態（Phase 3-5c-1；純函式）：由 `RunResponse` 決定要顯示哪個畫面、有哪些按鈕，
// 以及升級畫面的配點、候選排列、欄位上限判斷。
import { END_REASONS } from "../battle/glossary";
import { objectiveBadge, objectiveLine, type ObjectiveKind, type ObjectiveLike } from "../battle/objective";
import type { AttributeId, GearCandidate, RunChoice, RunHero, RunOffer, RunResponse, SkillCard } from "../api/types";

/** 六項屬性（與後端 `Attribute` 的順序相同）與中文名。 */
export const ATTRIBUTES: readonly { id: AttributeId; label: string }[] = [
  { id: "str", label: "力量" },
  { id: "dex", label: "敏捷" },
  { id: "con", label: "體質" },
  { id: "int", label: "智力" },
  { id: "wis", label: "感知" },
  { id: "wil", label: "意志" },
];

/** 開局六項屬性都是同一個基礎值（`content/roguelite.yaml` 的 `base_attribute`，由 API 提供）。 */
export function baseAttributes(value: number): Record<AttributeId, number> {
  return Object.fromEntries(ATTRIBUTES.map((a) => [a.id, value])) as Record<AttributeId, number>;
}

/** 屬性的常駐數值（Phase 3H-1；說明文字由後端依 `core.yaml` 的 `attribute_perks` 產生，這裡只決定怎麼排）。 */
export type AttributePerk = RunHero["attribute_perks"][number];

/** 面板上的一行：有階數時寫目前的總效果與階數，還沒有階數時寫每階效果與要幾點才升到 1 階。 */
export function perkText(p: AttributePerk): string {
  return p.now_zh !== null ? `${p.now_zh}（${p.tier} 階）` : `${p.per_tier_zh}（屬性 ${p.next_at} 起）`;
}

/** 某屬性影響的招（Phase 3H-3；由後端依技能與武器的縮放屬性產生）。沒有資料時為空。 */
export function affectsOf(affects: readonly { attr: string; lines_zh: readonly string[] }[] | undefined, id: string): readonly string[] {
  return affects?.find((a) => a.attr === id)?.lines_zh ?? [];
}

/** 「影響：…」一行；沒有影響任何招時回傳 `null`。 */
export function affectsText(lines: readonly string[]): string | null {
  return lines.length === 0 ? null : `影響：${lines.join("、")}`;
}

/** 建議主屬性的一行文字（原因由後端依技能與武器產生）。 */
export function suggestionText(s: { attr: string; reason_zh: string } | null | undefined): string | null {
  return s == null ? null : `建議主屬性：${attributeLabel(s.attr)}（${s.reason_zh}）`;
}

export function attributeLabel(id: string): string {
  return ATTRIBUTES.find((a) => a.id === id)?.label ?? id;
}

/** 技能欄位上限（`content/rules/core.yaml` 的 `skill_slots`）。 */
export const SLOT_LIMITS = { active: 6, passive: 3, reaction: 1, stance: 1 } as const;
export type SlotKind = keyof typeof SLOT_LIMITS;
export const SLOT_LABELS: Readonly<Record<SlotKind, string>> = {
  active: "主動",
  passive: "被動（含修正）",
  reaction: "反應",
  stance: "姿態",
};

// ---- 畫面 ----------------------------------------------------------------------------

export type RunView =
  | {
      screen: "progress";
      /** 第幾場（1 起算）。 */
      index: number;
      boss: boolean;
      mapName: string;
      enemies: readonly string[];
      /** 本場的勝利條件（Phase 3-22）：圖示加名稱，與一行說明。 */
      goalKind: ObjectiveKind;
      goalBadge: string;
      goalLine: string;
      /** 本場已經開打（讀檔回來在戰鬥中）→ 按鈕是「繼續戰鬥」。 */
      resume: boolean;
      buttonLabel: string;
    }
  | { screen: "gear_offer"; afterBattle: number; candidates: readonly GearCandidate[] }
  | { screen: "level_up"; level: number; points: number; offer: RunOffer }
  | { screen: "campfire"; afterBattle: number; rerollsLeft: number; offer: RunOffer | null }
  | { screen: "ended"; victory: boolean };

/** 由一輪的回應決定畫面。節點資料不完整（不該發生）時拋出錯誤，讓畫面顯示錯誤而不是空白。 */
export function runView(run: RunResponse): RunView {
  const node = run.node;
  if (node.kind === "ended") return { screen: "ended", victory: node.victory === true };
  if (node.kind === "gear_offer") {
    if (node.gear == null) throw new Error("裝備三選一節點缺少候選");
    return { screen: "gear_offer", afterBattle: node.gear.after_battle, candidates: node.gear.candidates };
  }
  if (node.kind === "level_up") {
    if (node.offer == null) throw new Error("升級節點缺少技能候選");
    return { screen: "level_up", level: node.level ?? run.hero.level, points: node.points ?? 0, offer: node.offer };
  }
  if (node.kind === "campfire") {
    return {
      screen: "campfire",
      afterBattle: node.after_battle ?? run.battles_done,
      rerollsLeft: node.rerolls_left ?? 0,
      offer: node.offer ?? null,
    };
  }
  const index = node.battle_index ?? run.battles_done + 1;
  const plan = run.plan.find((p) => p.index === index);
  const boss = node.boss === true || plan?.boss === true;
  const resume = run.battle_id !== null;
  const base = boss ? "Boss 戰" : `第 ${index} 場`;
  const goal: ObjectiveLike = plan?.objective ?? { kind: "eliminate" };
  return {
    screen: "progress",
    index,
    boss,
    mapName: plan?.map_name_zh ?? "",
    enemies: plan?.enemies ?? [],
    goalKind: goal.kind,
    goalBadge: objectiveBadge(goal),
    goalLine: objectiveLine(goal),
    resume,
    // 「Boss 戰」是英文開頭，前面要空格；「第 3 場」是中文，不用。
    buttonLabel: resume ? `繼續${boss ? " " : ""}${base}` : `開始${boss ? " " : ""}${base}`,
  };
}

/** 「第 3 場」「Boss 戰」。 */
export function battleName(index: number, boss: boolean): string {
  return boss ? "Boss 戰" : `第 ${index} 場`;
}

/** 主角在歷程中倒下過的場次（結束摘要與提示用）。 */
export function downedBattles(run: RunResponse): number[] {
  return run.history.filter((h) => h.hero_downed).map((h) => h.index);
}

// ---- 戰鬥結果文字 ----------------------------------------------------------------------

export function recordText(r: RunResponse["history"][number]): string {
  const result = r.won ? "勝利" : "失敗";
  const reason = !r.won && r.end_reason !== null ? `（${END_REASONS[r.end_reason] ?? r.end_reason}）` : "";
  return `${result}${reason}・${r.rounds} 輪${r.hero_downed ? "・主角曾倒下" : ""}`;
}

// ---- 候選排列（偏離路線的位置不固定） ----------------------------------------------------

/** 32 位元的字串雜湊（FNV-1a）；只用於顯示順序，不影響遊戲結果。 */
export function hashText(text: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * 候選的顯示順序（回傳原索引的排列）：由「一輪的種子 ＋ 第幾組」決定，同一組永遠相同，
 * 重新整理或讀檔後也一樣；偏離路線的那張因此不固定在最後。
 */
export function displayOrder(runSeed: number, groupKey: string, count: number): number[] {
  const order = Array.from({ length: count }, (_, i) => i);
  const rand = mulberry32(hashText(`${runSeed}:${groupKey}`));
  for (let i = order.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [order[i], order[j]] = [order[j] as number, order[i] as number];
  }
  return order;
}

/** 這一組候選的識別字串（升級：第幾級；營火：第幾場後 ＋ 剩餘重骰次數）。 */
export function offerGroupKey(view: RunView): string {
  if (view.screen === "level_up") return `level_up:${view.level}`;
  if (view.screen === "campfire") return `campfire:${view.afterBattle}:${view.rerollsLeft}`;
  return "none";
}

export const OFF_ROUTE_LABEL = "偏離路線";
export function offRouteHint(topAttribute: string): string {
  return `縮放屬性與目前主屬性（${attributeLabel(topAttribute)}）不同`;
}

// ---- 屬性配點 ----------------------------------------------------------------------------

export type Allocation = Readonly<Partial<Record<AttributeId, number>>>;

export function allocationTotal(alloc: Allocation): number {
  return ATTRIBUTES.reduce((sum, a) => sum + (alloc[a.id] ?? 0), 0);
}

/** 體質高於（低於）基準 `conBase` 帶來的最大 HP 加成（主角面板用）。 */
export function conHpBonus(con: number, conBase: number, hpPerCon: number): number {
  return (con - conBase) * hpPerCon;
}

/** 「＋6 HP」「−3 HP」；0 時為空字串。 */
export function hpDeltaText(delta: number): string {
  if (delta === 0) return "";
  return `${delta > 0 ? "＋" : "−"}${Math.abs(delta)} HP`;
}

/** 加減一點（不會小於 0；已配滿 `points` 時不能再加）。 */
export function adjustAllocation(alloc: Allocation, id: AttributeId, delta: 1 | -1, points: number): Allocation {
  const now = alloc[id] ?? 0;
  if (delta > 0 && allocationTotal(alloc) >= points) return alloc;
  if (delta < 0 && now <= 0) return alloc;
  return { ...alloc, [id]: now + delta };
}

export function allocationComplete(alloc: Allocation, points: number): boolean {
  return allocationTotal(alloc) === points;
}

/** 只送非 0 的項目。 */
export function cleanAllocation(alloc: Allocation): Partial<Record<AttributeId, number>> {
  const out: Partial<Record<AttributeId, number>> = {};
  for (const a of ATTRIBUTES) {
    const v = alloc[a.id] ?? 0;
    if (v > 0) out[a.id] = v;
  }
  return out;
}

// ---- 技能欄位 ----------------------------------------------------------------------------

/** 技能占哪一種欄位：修正技能裝在被動欄位（與後端 `skill_slot_problems` 相同）。 */
export function slotOf(card: Pick<SkillCard, "kind_id">): SlotKind {
  const k = card.kind_id;
  if (k === "modifier" || k === "passive") return "passive";
  if (k === "reaction" || k === "stance") return k;
  return "active";
}

export function slotUsage(skills: readonly Pick<SkillCard, "kind_id">[]): Record<SlotKind, number> {
  const usage: Record<SlotKind, number> = { active: 0, passive: 0, reaction: 0, stance: 0 };
  for (const s of skills) usage[slotOf(s)] += 1;
  return usage;
}

/** 裝上 `card` 會超過欄位上限嗎？（規則改變型傳說的限制前端不知道，由後端 422 補上。） */
export function needsReplacement(skills: readonly SkillCard[], card: SkillCard): boolean {
  const kind = slotOf(card);
  return slotUsage(skills)[kind] >= SLOT_LIMITS[kind];
}

/** 可以被換掉的技能：預設只列同種欄位；後端拒絕後（`any`）列出全部。 */
export function replaceOptions(skills: readonly SkillCard[], card: SkillCard, any = false): SkillCard[] {
  const kind = slotOf(card);
  return skills.filter((s) => any || slotOf(s) === kind);
}

/** 升級／營火選好一張候選後送出的請求。`replace` 只在需要替換時帶。 */
export function pickChoice(
  view: RunView,
  alloc: Allocation,
  pick: number | null,
  replace: string | null,
  levels: Readonly<Record<string, number>> = {},
  evolve: Readonly<Record<string, number>> = {},
): RunChoice {
  if (view.screen === "level_up") {
    const base = { kind: "level_up" as const, attributes: cleanAllocation(alloc), pick, replace };
    // 選完候選之後順便花技能點（Phase 3-26a）與分歧進化的選擇（3-26b）；沒有要花的就不帶
    const withLevels = Object.keys(levels).length > 0 ? { ...base, levels: { ...levels } } : base;
    return Object.keys(evolve).length > 0 ? { ...withLevels, evolve: { ...evolve } } : withLevels;
  }
  return { kind: "pick", pick, replace };
}

/** 升級畫面能不能按「確定」：配點配滿，且（有選技能時）需要替換就已選好要換掉的。 */
export function levelUpReady(
  points: number,
  alloc: Allocation,
  hero: RunHero,
  offer: RunOffer,
  pick: number | null,
  replace: string | null,
  forceReplace = false,
): boolean {
  if (!allocationComplete(alloc, points)) return false;
  return pickReady(hero, offer, pick, replace, forceReplace);
}

/** 營火重骰後能不能按「選這個」。 */
export function pickReady(
  hero: RunHero,
  offer: RunOffer,
  pick: number | null,
  replace: string | null,
  forceReplace = false,
): boolean {
  if (pick === null) return true; // 跳過
  const card = offer.candidates[pick];
  if (card === undefined) return false;
  if (needsReplacement(hero.skills, card) || forceReplace) return replace !== null;
  return true;
}

// ---- 存檔列表與目前進行中的一輪 ----------------------------------------------------------------

export function saveLabel(s: {
  node: string;
  battles_done: number;
  battles_total: number;
  in_battle: boolean;
  level: number;
  victory?: boolean | null;
}): string {
  const ended = s.victory === true ? "已結束（勝利）" : s.victory === false ? "已結束（失敗）" : "已結束";
  const where: Record<string, string> = {
    battle: s.in_battle ? "戰鬥中" : "戰鬥之間",
    gear_offer: "裝備三選一",
    level_up: "升級",
    campfire: "營火",
    ended,
  };
  return `${s.battles_done}/${s.battles_total} 場・Lv${s.level}・${where[s.node] ?? s.node}`;
}

export const CURRENT_RUN_KEY = "trpg.currentRun";

/** 讀記在 localStorage 的進行中的 run id；不能用或沒有時 `null`。 */
export function readCurrentRun(storage: Pick<Storage, "getItem"> | null = defaultStorage()): string | null {
  try {
    const v = storage?.getItem(CURRENT_RUN_KEY) ?? null;
    return v !== null && /^[A-Za-z0-9_-]{1,64}$/.test(v) ? v : null;
  } catch {
    return null;
  }
}

export function writeCurrentRun(
  runId: string | null,
  storage: Pick<Storage, "setItem" | "removeItem"> | null = defaultStorage(),
): void {
  try {
    if (storage === null) return;
    if (runId === null) storage.removeItem(CURRENT_RUN_KEY);
    else storage.setItem(CURRENT_RUN_KEY, runId);
  } catch {
    // 無法存取 localStorage（私密視窗等）時，重新整理後不會自動回到這一輪。
  }
}

function defaultStorage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

// ---- 重新整理後回到一輪（Phase 3-6） ----------------------------------------------------------

/** 伺服器沒有這一輪（重啟過）時的 HTTP 狀態碼。 */
const NOT_FOUND = 404;

/**
 * 重新整理後回到上次的一輪：先問伺服器（記憶體裡的一輪不會丟步驟，伺服器已自動存檔）；伺服器說
 * 沒有這一輪（404，例如重啟過）才讀存檔。其他錯誤照樣丟出去。
 */
export async function resumeRun<T>(
  runId: string,
  fetchRun: (runId: string) => Promise<T>,
  loadRun: (runId: string) => Promise<T>,
  isNotFound: (e: unknown) => boolean,
): Promise<T> {
  try {
    return await fetchRun(runId);
  } catch (e) {
    if (isNotFound(e)) return loadRun(runId);
    throw e;
  }
}

export function isNotFoundStatus(status: number): boolean {
  return status === NOT_FOUND;
}

/** 進入戰鬥時沒有任何步驟（接續進行中的戰鬥或讀檔）→ 要向伺服器取回戰鬥紀錄；新戰鬥已經帶著開場的步驟。 */
export function needsLogRestore(res: { steps: readonly unknown[] }): boolean {
  return res.steps.length === 0;
}
