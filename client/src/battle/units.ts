// 單位的代號與名稱（同 CLI：我方 A、B、C……，敵方 a、b、c……，依單位 ID 排序；召喚物不分陣營，
// 一律用數字 1–9，超過 9 個後循環）。
import type { BattleView, Team, UnitView } from "../api/types";

const UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const LOWER = "abcdefghijklmnopqrstuvwxyz";

export function unitMarkers(units: readonly UnitView[]): Map<string, string> {
  const sorted = [...units].sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  const counters = { ally: 0, enemy: 0 };
  const markers = new Map<string, string>();
  let summons = 0;
  for (const u of sorted) {
    if (u.owner_id !== null) {
      markers.set(u.id, String((summons++ % 9) + 1));
      continue;
    }
    const i = counters[u.team]++;
    const letters = u.team === "ally" ? UPPER : LOWER;
    markers.set(u.id, letters[i % 26] ?? "?");
  }
  return markers;
}

/** 單位名稱表：`unit_id → 「A 名稱」`。 */
export interface UnitNames {
  marker(id: string): string;
  name(id: string): string;
  /** 「代號 名稱」，例如「A 火焰英雄」。找不到時回傳 ID。 */
  label(id: string): string;
  /** 單位的陣營；不在名單內（例如重新整理後才出現的召喚物）時為 `undefined`。 */
  team(id: string): Team | undefined;
}

export function unitNames(view: BattleView): UnitNames {
  const markers = unitMarkers(view.units);
  const byId = new Map(view.units.map((u) => [u.id, u]));
  return {
    marker: (id) => markers.get(id) ?? "?",
    name: (id) => byId.get(id)?.name_zh ?? id,
    label: (id) => {
      const u = byId.get(id);
      return u === undefined ? id : `${markers.get(id) ?? "?"} ${u.name_zh}`;
    },
    team: (id) => byId.get(id)?.team,
  };
}

/** 仍在戰場上（未撤離、召喚物未消失）的單位；倒下的單位保留（淡化顯示）。 */
export function onField(u: UnitView): boolean {
  return !u.escaped && !u.dismissed;
}

export function isAlive(u: UnitView): boolean {
  return !u.downed && onField(u);
}
