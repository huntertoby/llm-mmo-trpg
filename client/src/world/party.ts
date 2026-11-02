// 隊伍與系統傭兵的純函式（Phase 5C-1；docs/phases/Phase5計畫.md 22.7）。規則在後端，這裡只處理勾選與文字。
import type { WorldMercenary, WorldPartyView } from "../api/types";

/** 勾選或取消一名傭兵：保持勾選順序（＝出場順序）；已滿 `max` 時不再加。 */
export function toggleMercenary(chosen: readonly string[], id: string, max: number): string[] {
  if (chosen.includes(id)) return chosen.filter((x) => x !== id);
  if (chosen.length >= max) return [...chosen];
  return [...chosen, id];
}

/** 目前已雇用的傭兵 ID（名單順序沒有出場順序，所以從隊伍成員取）。 */
export function hiredIds(party: WorldPartyView): string[] {
  return party.members.flatMap((m) => (m.mercenary != null ? [m.mercenary] : []));
}

/** 勾選清單和目前隊伍一樣（順序也一樣）＝不用送出。 */
export function sameParty(party: WorldPartyView, chosen: readonly string[]): boolean {
  const now = hiredIds(party);
  return now.length === chosen.length && now.every((id, i) => id === chosen[i]);
}

/** 依定位分組（照名單裡定位第一次出現的順序）。 */
export function groupByRole(roster: readonly WorldMercenary[]): { role: string; role_zh: string; members: WorldMercenary[] }[] {
  const groups: { role: string; role_zh: string; members: WorldMercenary[] }[] = [];
  for (const m of roster) {
    const g = groups.find((x) => x.role === m.role);
    if (g === undefined) groups.push({ role: m.role, role_zh: m.role_zh, members: [m] });
    else g.members.push(m);
  }
  return groups;
}

/** 送出按鈕的字：全不勾＝不帶傭兵。 */
export function hireLabel(chosen: readonly string[], roster: readonly WorldMercenary[]): string {
  if (chosen.length === 0) return "確定：不帶傭兵（用標準隊友）";
  const names = chosen.map((id) => roster.find((m) => m.id === id)?.name_zh ?? id);
  return `確定雇用：${names.join("、")}`;
}
