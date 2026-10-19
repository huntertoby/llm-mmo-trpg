// 單位的代號與名稱（同 CLI：我方 A、B、C……，敵方 a、b、c……，依單位 ID 排序）。
import type { BattleView, UnitView } from "../api/types";

const UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const LOWER = "abcdefghijklmnopqrstuvwxyz";

export function unitMarkers(units: readonly UnitView[]): Map<string, string> {
  const sorted = [...units].sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  const counters = { ally: 0, enemy: 0 };
  const markers = new Map<string, string>();
  for (const u of sorted) {
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
  };
}

/** 仍在戰場上（未撤離、召喚物未消失）的單位；倒下的單位保留（淡化顯示）。 */
export function onField(u: UnitView): boolean {
  return !u.escaped && !u.dismissed;
}

export function isAlive(u: UnitView): boolean {
  return !u.downed && onField(u);
}
