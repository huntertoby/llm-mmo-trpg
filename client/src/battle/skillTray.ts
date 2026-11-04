// 底部技能列的分組與版面偏好（Phase 3-8；純函式＋ localStorage 包裝）。
import type { SkillCard } from "../api/types";
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
  if (mode.kind === "vault") return `${head}：點選紫色格子，攀上高台或跳過缺口（${t.tiles.size} 個）；${CANCEL_PICK}`;
  if (mode.kind === "shove_aside") return `${head}：在左側選擇把物件撥向哪一邊；${CANCEL_PICK}`;
  if (mode.kind === "defend" && t.self !== null)
    return `${head}：點自己守護自己，或點相鄰的隊友（紅框 ${t.units.size} 個）替他承受單體攻擊；${CANCEL_PICK}`;
  if (t.hurls.size > 0) {
    const [first, second] = PAIR_PARTS[t.pairKind ?? "hurl"];
    return `${head}分兩段：先點${first}（紅框 ${t.hurls.size} 個），再點${second}；${CANCEL_PICK}`;
  }
  if (isSelfOnly(t)) return `${head}對自身施放：按左側的「施放」；${CANCEL_PICK}`;
  const picks: string[] = [];
  const units = t.units.size + t.objects.size;
  if (units > 0) picks.push(`點選紅框目標（${units} 個）`);
  if (t.tiles.size > 0) {
    const what = card?.stats.radius != null && card.stats.radius > 0 ? "範圍中心" : "目標格";
    picks.push(`${units > 0 ? "或點" : "點選"}格子當${what}（${t.tiles.size} 格）`);
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
