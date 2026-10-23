// 層數說明框的文字（Phase 3-41c）：一般說明來自 /api/glossary 的 `stacks`（後端依 `stacks.yaml` 產生），
// 「你擁有的、會製造／消耗它的技能」由技能卡的 `stacks` 欄位（後端依技能效果產生）過濾而來；前端不寫死規則。
import type { SkillCard } from "../api/types";
import { glossaryEntry } from "./glossary";

type Cards = Readonly<Record<string, SkillCard | undefined>>;

/** 某層數有關的技能名稱：`owned` 是持有者的技能 ID。 */
export function stackSkillNames(
  id: string,
  cards: Cards,
  owned: readonly string[],
): { makes: string[]; uses: string[] } {
  const makes: string[] = [];
  const uses: string[] = [];
  for (const skillId of owned) {
    const card = cards[skillId];
    if (card === undefined) continue;
    for (const ref of card.stacks ?? []) {
      if (ref.id !== id) continue;
      const list = ref.role === "makes" ? makes : uses;
      if (!list.includes(card.name_zh)) list.push(card.name_zh);
    }
  }
  return { makes, uses };
}

/**
 * 層數的說明框文字：名稱、一句話、逐條規則；有持有者（戰鬥中的角色面板）時再列「你的技能」中會製造／
 * 消耗它的。工坊等沒有持有者的地方傳 `owned = null`，只寫一般說明。對照表沒有這個層數時 `null`。
 */
export function stackHintText(id: string, cards: Cards = {}, owned: readonly string[] | null = null): string | null {
  const e = glossaryEntry("stacks", id);
  if (e === undefined) return null;
  const lines = [e.name_zh];
  if ((e.description_zh ?? "") !== "") lines.push(e.description_zh ?? "");
  lines.push(...e.rules_zh.map((line) => `・${line}`));
  if (owned !== null) {
    const { makes, uses } = stackSkillNames(id, cards, owned);
    if (makes.length > 0) lines.push(`你的技能・累積：${makes.join("、")}`);
    if (uses.length > 0) lines.push(`你的技能・消耗／利用：${uses.join("、")}`);
    if (makes.length === 0 && uses.length === 0) lines.push("你目前沒有會累積或消耗它的技能");
  }
  return lines.join("\n");
}
