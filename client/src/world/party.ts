// 隊伍、系統傭兵與影子的純函式（Phase 5C-1、5C-2；docs/phases/Phase5計畫.md 22.7、23.9）。
// 規則在後端，這裡只處理勾選與文字。
import type { WorldAction, WorldMercenary, WorldPartyView, WorldShadow } from "../api/types";

/** 勾選或取消一名隊友：保持勾選順序（＝出場順序）；和另一頁合計已滿 `max` 時不再加。 */
export function toggleMercenary(chosen: readonly string[], id: string, max: number, others = 0): string[] {
  if (chosen.includes(id)) return chosen.filter((x) => x !== id);
  if (chosen.length + others >= max) return [...chosen];
  return [...chosen, id];
}

/** 目前已雇用的傭兵 ID（名單順序沒有出場順序，所以從隊伍成員取）。 */
export function hiredIds(party: WorldPartyView): string[] {
  return party.members.flatMap((m) => (m.mercenary != null ? [m.mercenary] : []));
}

/** 目前借用的影子（主人的角色 ID，依出場順序）。 */
export function hiredShadows(party: WorldPartyView): string[] {
  return party.members.flatMap((m) => (m.shadow != null ? [m.shadow] : []));
}

/** 只留給目前成員的打法設定（成員換掉時打法一起拿掉）。 */
export function memberAi(ai: Readonly<Record<string, string>>, members: readonly string[]): Record<string, string> {
  const kept: Record<string, string> = {};
  for (const id of members) {
    const value = ai[id];
    if (value !== undefined) kept[id] = value;
  }
  return kept;
}

/** 勾選清單、影子、打法都和目前隊伍一樣（順序也一樣）＝不用送出。 */
export function sameParty(
  party: WorldPartyView,
  chosen: readonly string[],
  shadows: readonly string[] = [],
  ai: Readonly<Record<string, string>> = {},
): boolean {
  const same = (a: readonly string[], b: readonly string[]) => a.length === b.length && a.every((id, i) => id === b[i]);
  const now = party.ai ?? {};
  const want = memberAi(ai, [...chosen, ...shadows]);
  const keys = new Set([...Object.keys(now), ...Object.keys(want)]);
  const aiSame = [...keys].every((k) => now[k] === want[k]);
  return same(hiredIds(party), chosen) && same(hiredShadows(party), shadows) && aiSame;
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

/** 送出按鈕的字：全不勾＝獨行（5C-2 玩法 PM 定 ③）。 */
export function hireLabel(
  chosen: readonly string[],
  roster: readonly WorldMercenary[],
  shadows: readonly string[] = [],
  shadowList: readonly WorldShadow[] = [],
): string {
  if (chosen.length === 0 && shadows.length === 0) return "確定：獨行（只帶主角）";
  const names = chosen.map((id) => roster.find((m) => m.id === id)?.name_zh ?? id);
  names.push(...shadows.map((id) => `${shadowList.find((s) => s.owner === id)?.name_zh ?? id}的影子`));
  return `確定隊伍：${names.join("、")}`;
}

/** 送出的 `hire` 動作（打法只送給這次的成員）。 */
export function hireAction(
  chosen: readonly string[],
  shadows: readonly string[],
  ai: Readonly<Record<string, string>>,
): WorldAction {
  return { kind: "hire", mercenaries: [...chosen], shadows: [...shadows], ai: memberAi(ai, [...chosen, ...shadows]) };
}
