// 底部技能列的分組與版面偏好（Phase 3-8；純函式＋ localStorage 包裝）。
import type { SkillCard } from "../api/types";
import type { SkillButton, SkillCards } from "./targeting";

/** 以小圖示放在技能列最右側的種類：被動、反應、姿態、修正（不佔大格）。 */
export const MINOR_KINDS: readonly string[] = ["passive", "reaction", "stance", "modifier"];

/** 技能是否放在右側小圖示區。卡片還沒取得時當成主動（先佔大格，避免閃一下又跳走的反覆）。 */
export function isMinorSkill(card: Pick<SkillCard, "kind_id"> | undefined): boolean {
  return card !== undefined && MINOR_KINDS.includes(card.kind_id);
}

/** 把技能按鈕分成主動（大格）與被動／反應／姿態（小圖示），各自保持原順序。 */
export function splitSkills(
  buttons: readonly SkillButton[],
  cards: SkillCards,
): { main: SkillButton[]; minor: SkillButton[] } {
  const main: SkillButton[] = [];
  const minor: SkillButton[] = [];
  for (const b of buttons) (isMinorSkill(cards[b.skillId]) ? minor : main).push(b);
  return { main, minor };
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
}): string {
  if (state.ended) return "戰鬥結束。";
  if (state.copying) return "請為複製的技能或複合技能的第二段選擇目標（點高亮格子或左上角的方向鈕），或按 Esc 放棄。";
  if (!state.canAct) return "等待中……";
  return `點選藍色格子移動（${state.moveCount} 格），點選紅框敵人攻擊（${state.attackCount} 個）；右鍵或 Esc 取消選取。`;
}

/** 頂端列的彈出面板（同時只開一個）。 */
export type TopPopup = "reactions" | "orders" | "legend";

/** 點了某個頂端按鈕：再點同一個關閉，點別的換成別的。 */
export function togglePopup(current: TopPopup | null, clicked: TopPopup): TopPopup | null {
  return current === clicked ? null : clicked;
}

/** 視窗寬度小於這個值時：右側窄欄預設收合、主角狀態卡縮成一行。 */
export const NARROW_WIDTH = 1100;

const SIDE_KEY = "trpg.battleSideCollapsed";

/** 右側窄欄是否收合：有記錄時照記錄，沒有時窄螢幕預設收合。localStorage 不能用時只看寬度。 */
export function loadSideCollapsed(narrow: boolean): boolean {
  try {
    const v = window.localStorage.getItem(SIDE_KEY);
    if (v === "1") return true;
    if (v === "0") return false;
  } catch {
    // 私密視窗等：沒有記錄
  }
  return narrow;
}

export function saveSideCollapsed(collapsed: boolean): void {
  try {
    window.localStorage.setItem(SIDE_KEY, collapsed ? "1" : "0");
  } catch {
    // 無法存取 localStorage 時只在本次有效。
  }
}
