// 戰場變奏（Phase 3-25b，docs/design/06-技能.md 6.24）的顯示規則（純函式）。
// 型態由伺服器的引擎判定（`BattleResponse.variant_states`、`PreviewOut.variant`），前端不自己判斷任何條件，
// 只決定「怎麼顯示」：技能列按鈕是否發亮、換成哪個圖示、預覽寫哪一行。
import type { PreviewOut, SkillCard, SkillVariantCard, VariantState } from "../api/types";

/** 一個技能按鈕上的變奏狀態。 */
export interface SkillVariantView {
  /** 目前就生效的型態（只看施放者位置的條件）；沒有為 `null`。 */
  activeId: string | null;
  /** 目前的合法目標中，某個目標點會選到的型態（含居高、目標點表面）。 */
  reachableIds: readonly string[];
  /** 按鈕是否發亮：有任何型態現在生效或選得到。 */
  glow: boolean;
}

/** 技能的變奏狀態；技能沒有變奏（卡片沒有型態、伺服器沒有列）時 `undefined`。 */
export function skillVariantView(card: SkillCard | undefined, state: VariantState | undefined): SkillVariantView | undefined {
  if (card === undefined || (card.variants ?? []).length === 0 || state === undefined) return undefined;
  const known = new Set((card.variants ?? []).map((v) => v.id));
  const activeId = state.active != null && known.has(state.active) ? state.active : null;
  const reachableIds = state.available.filter((id) => known.has(id));
  return { activeId, reachableIds, glow: activeId !== null || reachableIds.length > 0 };
}

/** 目前生效的型態（技能列的圖示換成它）；沒有為 `null`。 */
export function activeVariantCard(card: SkillCard | undefined, view: SkillVariantView | null | undefined): SkillVariantCard | null {
  if (card === undefined || view == null || view.activeId === null) return null;
  return (card.variants ?? []).find((v) => v.id === view.activeId) ?? null;
}

/** 目前會選到的型態（生效的在前，其後是對某些目標才選得到的；依卡片順序）。 */
export function readyVariants(card: SkillCard | undefined, view: SkillVariantView | null | undefined): SkillVariantCard[] {
  if (card === undefined || view == null) return [];
  const ids = new Set([...(view.activeId === null ? [] : [view.activeId]), ...view.reachableIds]);
  return (card.variants ?? []).filter((v) => ids.has(v.id));
}

/** 技能按鈕上的一小行：生效的型態名；只對某些目標才生效時寫「可用：型態名」。 */
export function variantBadge(card: SkillCard | undefined, view: SkillVariantView): string {
  const active = activeVariantCard(card, view);
  if (active !== null) return active.name_zh;
  const ready = readyVariants(card, view);
  return ready.length === 0 ? "" : `可用：${ready.map((v) => v.name_zh).join("、")}`;
}

/** 預覽的第一行：這個目標點生效的型態；基礎型態（沒有變奏成立）省略。 */
export function previewVariantLine(p: PreviewOut): string | null {
  return p.variant == null ? null : `型態：${p.variant.name_zh}`;
}

/** 技能卡上條件的小標籤：看目標點的條件要在預覽才知道。 */
export function conditionNote(v: SkillVariantCard): string {
  return v.target_dependent ? "（看目標點，預覽時顯示）" : "";
}
