// 底部技能列的分組與版面偏好（Phase 3-8；純函式＋ localStorage 包裝）。
import type { SkillCard } from "../api/types";
import { pickCountText, splitCompositeKeys, tileCount, unitCount } from "./pickCount";
import { isSelfOnly, type ActionMode, type PairKind, type SkillButton, type SkillCards } from "./targeting";

type SkillCardStats = SkillCard["stats"];

/** 以小圖示放在技能列最右側的種類：被動、反應、姿態、修正（不佔大格）。 */
export const MINOR_KINDS: readonly string[] = ["passive", "reaction", "stance", "modifier"];

/** 技能是否放在右側小圖示區。卡片還沒取得時當成主動（先佔大格，避免閃一下又跳走的反覆）。 */
export function isMinorSkill(card: Pick<SkillCard, "kind_id"> | undefined): boolean {
  return card !== undefined && MINOR_KINDS.includes(card.kind_id);
}

/** 腰包的道具技能（Phase 5D-4，8.17：卡片標籤有 `item`）：不佔技能欄位，放在技能列的獨立「道具」欄。 */
export function isItemSkill(card: Pick<SkillCard, "tags"> | undefined): boolean {
  return card !== undefined && (card.tags ?? []).includes("item");
}

/** 把技能按鈕分成主動（大格）、道具（獨立的道具欄，5D-4）與被動／反應／姿態（小圖示），各自保持原順序。 */
export function splitSkills(
  buttons: readonly SkillButton[],
  cards: SkillCards,
): { main: SkillButton[]; minor: SkillButton[]; items: SkillButton[] } {
  const main: SkillButton[] = [];
  const minor: SkillButton[] = [];
  const items: SkillButton[] = [];
  for (const b of buttons) {
    const card = cards[b.skillId];
    if (isItemSkill(card)) items.push(b);
    else (isMinorSkill(card) ? minor : main).push(b);
  }
  return { main, minor, items };
}

/** 小圖示上的字：技能名稱的第一個字（空字串時用「？」）。 */
export function minorGlyph(name: string): string {
  const first = [...name.trim()][0];
  return first ?? "？";
}

/** 技能列上方的一行提示。 */
export function actionHintText(state: {
  copying: boolean;
  canAct: boolean;
  ended: boolean;
  moveCount: number;
  attackCount: number;
  /** 只剩「結束回合」，但還有可以切換模式的召喚物（3-32b）。 */
  summonIdle?: boolean;
  /** 6F-9：選取中的技能或模式自己的提示（`modeBarHint`）；沒有選取時省略或 `null`。 */
  picked?: string | null;
}): string {
  if (state.ended) return "戰鬥結束。";
  if (state.copying) return "請為複製的技能或複合技能的第二段選擇目標（點高亮格子或左上角的方向鈕），或按 Esc 放棄。";
  if (!state.canAct) return "等待中……";
  if (state.picked != null) return state.picked;
  if (state.summonIdle === true) return "行動點數用完了，但還能調整召喚物的模式（0 AP）；準備好後按「結束回合」。";
  return `點選藍色格子移動（${state.moveCount} 格），點選紅框敵人攻擊（${state.attackCount} 個）；右鍵或 Esc 取消選取。`;
}

// ---- PR-2b（#147 測試模式；玩法 PM 定稿「測試模式戰鬥（PR-2）」表）：靶場的戰鬥（`BattleView.practice`）才用 ----

/** 測試模式上方中央的提示條（取代行動順序列）。 */
export const PRACTICE_BAR_ZH = "每次出手後自動過一輪，資源立刻補滿，木樁不會倒";
/** 測試模式右上：取代勝利條件的小牌。 */
export const PRACTICE_SANDBOX_TAG_ZH = "沙盒・不算勝負";
/** 測試模式預覽多的一行（21.5 指定的句子）。 */
export const PRACTICE_SURE_NOTE_ZH = "靶場木樁必中，實戰會有失手";
/** PR-2d：靶場提示條上「測試模式」徽章的說明卡（玩法 PM 定稿「PR-2 字串」）。其他地方的同一顆徽章（一輪的測試模式）原字不動。 */
export const PRACTICE_BADGE_HINT_ZH = "靶場測試模式：技能沒有冷卻、資源每次出手後補滿、木樁必中也不會倒。不算勝負，不給經驗與掉落。";
/** PR-2d：測試模式的開場橫幅（取代「戰鬥開始＋勝利條件」，玩法 PM 定稿「PR-2 字串」）。 */
export const PRACTICE_BANNER_ZH = "靶場：打木樁試招，按右上的離開鈕結束";

/**
 * 測試模式的操作提示句（PR-2b B1）：前端自寫的提示句裡的「敵人」寫成「木樁」，寫「目標」的不動；
 * 實戰（`practice` 為假）原字照回，一個字都不改。伺服器給的技能說明不經過這裡。
 */
export function practiceWording(text: string, practice: boolean): string {
  return practice ? text.replaceAll("敵人", "木樁") : text;
}

/** 技能列上方提示裡「取消選取」的說法（選了技能或其他模式時）。 */
const CANCEL_PICK = "右鍵或 Esc 取消選取。";

/** 兩段選取第 1 段、第 2 段要點的東西（`PairKind`）。 */
const PAIR_PARTS: Record<PairKind, [string, string]> = {
  hurl: ["要投擲的物件或人", "落點"],
  teleport: ["要傳送的人", "落點"],
  swap: ["第一個人", "要互換的另一個人"],
  shadowstep: ["目標", "落點"],
  composite: ["位移的落點或目標", "第 2 段的目標"],
};

/** 兩段選取第 1 段的可選數量（6F-10）：複合技能的落點算「格」、目標算「個」；其他（物件、人）都是「個」。 */
function firstPickCount(t: ActionMode["targets"]): string {
  if (t.pairKind !== "composite") return unitCount(t.hurls.size);
  const n = splitCompositeKeys(t.hurls.keys());
  return pickCountText(n.units, n.tiles);
}

/** 技能的射程與範圍（卡片 `stats`）：「射程 4・半徑 1」；都沒有時空字串。 */
export function reachText(stats: Pick<SkillCardStats, "range" | "range_weapon" | "radius"> | undefined): string {
  if (stats === undefined) return "";
  const parts: string[] = [];
  if (stats.range_weapon) parts.push("武器射程");
  else if (stats.range !== null) parts.push(`射程 ${stats.range}`);
  if (stats.radius != null && stats.radius > 0) parts.push(`半徑 ${stats.radius}`);
  return parts.join("・");
}

/**
 * 6F-9（美術 PM 6F-8 檢查第 3 節：選了技能後，技能列上方還寫「點選藍色格子移動…」）：選取中的技能或模式自己的提示。
 * 依目標的種類（自身、單體、格子、方向、兩段選取）與卡片上的射程、半徑產生，最後一律說怎麼取消。
 */
export function modeBarHint(mode: ActionMode, card?: Pick<SkillCard, "stats">): string {
  const t = mode.targets;
  const reach = reachText(card?.stats);
  const head = `「${mode.label}」${reach === "" ? "" : `（${reach}）`}`;
  if (mode.kind === "vault") return `${head}：點選紫色格子，攀上高台或跳過缺口（${tileCount(t.tiles.size)}）；${CANCEL_PICK}`;
  if (mode.kind === "shove_aside") return `${head}：在左側選擇把物件撥向哪一邊；${CANCEL_PICK}`;
  if (mode.kind === "defend" && t.self !== null)
    return `${head}：點自己守護自己，或點相鄰的隊友（紅框 ${t.units.size} 個）替他承受單體攻擊；${CANCEL_PICK}`;
  if (t.hurls.size > 0) {
    const [first, second] = PAIR_PARTS[t.pairKind ?? "hurl"];
    return `${head}分兩段：先點${first}（紅框 ${firstPickCount(t)}），再點${second}；${CANCEL_PICK}`;
  }
  if (isSelfOnly(t)) return `${head}對自身施放：按左側的「施放」；${CANCEL_PICK}`;
  const picks: string[] = [];
  const units = t.units.size + t.objects.size;
  if (units > 0) picks.push(`點選紅框目標（${unitCount(units)}）`);
  if (t.tiles.size > 0) {
    const what = card?.stats.radius != null && card.stats.radius > 0 ? "範圍中心" : "目標格";
    picks.push(`${units > 0 ? "或點" : "點選"}紅框格子當${what}（${tileCount(t.tiles.size)}）`);
  }
  if (t.directions.size > 0) picks.push(`${picks.length > 0 ? "或" : ""}選擇方向（主角旁的箭頭格或左側方向鈕）`);
  if (t.self !== null) picks.push("也可以按左側的「施放於自身」");
  return `${head}：${picks.join("，")}；${CANCEL_PICK}`;
}

/**
 * 技能列上方那一行是不是操作說明句（6A-3：前 3 次之後收進「?」）：移動／攻擊的說明、複製技能的說明是；
 * 「等待中」「戰鬥結束」「召喚物還能調整」這類狀態句不是，照常顯示。
 */
export function actionHintKind(state: Parameters<typeof actionHintText>[0]): "move" | "copy" | null {
  if (state.ended) return null;
  if (state.copying) return "copy";
  if (!state.canAct || state.picked != null || state.summonIdle === true) return null; // 6F-9：選取中的提示每次都完整顯示
  return "move";
}

/** 頂端列的彈出面板（同時只開一個）。 */
export type TopPopup = "reactions" | "orders" | "legend" | "layout";

/** 點了某個頂端按鈕：再點同一個關閉，點別的換成別的。 */
export function togglePopup(current: TopPopup | null, clicked: TopPopup): TopPopup | null {
  return current === clicked ? null : clicked;
}

/** 視窗寬度小於這個值時：右側窄欄預設收合、主角狀態卡縮成一行。 */
export const NARROW_WIDTH = 1100;

const SIDE_KEY = "trpg.battleSideCollapsed";

/** 玩家記下的右側窄欄收合狀態；沒有記錄（或 localStorage 不能用）時 `null`。 */
export function loadSidePref(): boolean | null {
  try {
    const v = window.localStorage.getItem(SIDE_KEY);
    if (v === "1") return true;
    if (v === "0") return false;
  } catch {
    // 私密視窗等：沒有記錄
  }
  return null;
}

/** 右側窄欄是否收合：有記錄時照記錄，沒有時窄螢幕（隨視窗寬度即時變化）預設收合。 */
export function sideCollapsed(pref: boolean | null, narrow: boolean): boolean {
  return pref ?? narrow;
}

export function saveSideCollapsed(collapsed: boolean): void {
  try {
    window.localStorage.setItem(SIDE_KEY, collapsed ? "1" : "0");
  } catch {
    // 無法存取 localStorage 時只在本次有效。
  }
}
