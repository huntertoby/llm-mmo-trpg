// 賭博型技能的預覽（Phase 3D-7a）：列出賭注每個分支的機率與結果，玩家在知情下下注（純函式）。
import type { PreviewOut } from "../api/types";
import { statusName } from "./glossary";
import type { UnitNames } from "./units";

export type GambleOut = NonNullable<PreviewOut["gamble"]>;
export type GambleBranchOut = GambleOut["branches"][number];

function percent(permille: number): string {
  const p = permille / 10;
  return `${Number.isInteger(p) ? p : p.toFixed(1)}%`;
}

function range(min: number, max: number): string {
  return min === max ? `${min}` : `${min}–${max}`;
}

function multiplierText(milli: number): string {
  const v = milli / 1000;
  return `×${Number.isInteger(v) ? v : v.toFixed(1)}`;
}

/** 一個分支的結果（不含機率）：「傷害 ×2（目標 16–32）」「你受 6–12 傷害」「你獲得「倒地」」；沒有變化為「照常」。 */
export function branchResult(b: GambleBranchOut): string {
  const parts: string[] = [];
  if (b.multiplier_permille !== 1000) {
    const target = b.targets.find((t) => !t.ally && t.damage !== null);
    const detail = target?.damage == null ? "" : `（目標 ${range(target.damage.minimum, target.damage.maximum)}）`;
    parts.push(`傷害 ${multiplierText(b.multiplier_permille)}${detail}`);
  }
  if (b.self_damage_max > 0) parts.push(`你受 ${range(b.self_damage_min, b.self_damage_max)} 傷害`);
  for (const s of b.self_statuses) parts.push(`你獲得「${statusName(s)}」`);
  if (b.self_healed_max > 0) parts.push(`你回復 ${range(b.self_healed_min, b.self_healed_max)}`);
  return parts.length === 0 ? "照常" : parts.join("，");
}

/** 一句話摘要：「60%：傷害 ×2｜40%：你受 6–12 傷害」；技能沒有賭注為 `null`。 */
export function gambleSummary(p: PreviewOut): string | null {
  const g = p.gamble;
  if (g == null) return null;
  return g.branches.map((b) => `${percent(b.permille)}：${branchResult(b)}`).join("｜");
}

/** 預覽的賭注行：摘要一行，再列出每個分支下各目標的傷害範圍（含倍率）。 */
export function gambleLines(p: PreviewOut, names: UnitNames): string[] {
  const g = p.gamble;
  const summary = gambleSummary(p);
  if (g == null || summary === null) return [];
  const lines = [`賭注（命中後擲 d1000）：${summary}`];
  for (const b of g.branches) {
    const label = b.kind === "win" ? "成功" : "失敗";
    for (const t of b.targets) {
      if (t.damage === null) continue;
      const who = names.label(t.unit_id);
      const d = t.damage;
      lines.push(`　${label}（${percent(b.permille)}）：${who} 傷害 ${range(d.minimum, d.maximum)}`);
    }
  }
  return lines;
}
