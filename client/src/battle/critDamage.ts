// CR-1b（05 5.4.2 第 8 點，佇列 (v)）：角色面板的暴擊傷害。
// 倍率與來源都由後端算（`UnitView.crit_damage_permille`、`crit_damage_detail_zh`，和結算共用同一個函式），
// 前端只排版、不重算。看不到資訊的單位（隱蔽中的敵人）後端送 `null`，這一格不畫。
import type { UnitView } from "../api/types";

/** 數值區那一格：「暴擊傷害 250%」（200% 也顯示）；後端沒給時 `null`。 */
export function critDamageText(unit: Pick<UnitView, "crit_damage_permille">): string | null {
  const p = unit.crit_damage_permille;
  if (p == null) return null;
  return `暴擊傷害 ${p / 10}%`;
}

/** CR-1c：「▸ 詳細」暴擊傷害列最後的提示行（有「條件看目標」的修正技時後端才給，看不到技能名的陣營不給）；沒有時 `null`。 */
export function critDamageHint(unit: { crit_damage_hint_zh?: string | null }): string | null {
  const h = unit.crit_damage_hint_zh;
  return h == null || h === "" ? null : h;
}

/** 「▸ 詳細」的來源列（後端排好的字）；沒有時 `null`。 */
export function critDamageDetail(unit: Pick<UnitView, "crit_damage_detail_zh">): string | null {
  const d = unit.crit_damage_detail_zh;
  return d == null || d === "" ? null : d;
}
