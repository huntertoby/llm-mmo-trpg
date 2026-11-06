// 雇用面板的技能圖示列（UI-E3；docs/archive/art/RT-2與RT-4與6H-1與AU-3檢查.md 第 20 行）：傭兵的技能從一長串文字改成圖示列，
// 最多 8 個，滑過看名字。
// UI-E3b：伺服器的傭兵、影子資料直接給技能 ID（`skill_ids`，和 `skills_zh` 同順序、同長度），用 `GET /api/skills/{id}`
// （有快取）取卡片；拿掉舊的「主題句 → build → 照名字對」間接做法。查不到卡片的（例如影子的生成技能不在內容庫）照舊寫字，
// 不畫假圖示。
import type { SkillCard } from "../api/types";

/** 一列最多畫幾個圖示（多的寫「+N」，滑過看名字）。 */
export const HIRE_ICON_MAX = 8;

export type HireSkill = { name: string; card: SkillCard | null };

/** 技能名與 ID 一一配對成卡片（照傳入順序）；最多 `max` 個，其餘的名字回傳在 `rest`。 */
export function pairSkills(
  names: readonly string[],
  ids: readonly string[],
  cards: Readonly<Record<string, SkillCard | undefined>>,
  max = HIRE_ICON_MAX,
): { shown: HireSkill[]; rest: string[] } {
  return {
    shown: names.slice(0, max).map((name, i) => {
      const id = ids[i];
      return { name, card: (id === undefined ? undefined : cards[id]) ?? null };
    }),
    rest: names.slice(max),
  };
}
