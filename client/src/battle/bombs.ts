// 定時炸彈與復活（Phase 3D-8b）：單位身上炸彈的倒數、預覽的說明文字（純函式）。
import type { PreviewOut, StatusView, UnitView } from "../api/types";
import { statusName } from "./glossary";
import type { UnitNames } from "./units";

export const TIME_BOMB = "time_bomb";

/** 單位身上的定時炸彈狀態（沒有時 `null`）。 */
export function bombStatus(u: UnitView): StatusView | null {
  return u.statuses.find((s) => s.status_id === TIME_BOMB) ?? null;
}

/** 還要幾次環境回合爆炸；沒有炸彈時 `null`。 */
export function bombCountdown(u: UnitView): number | null {
  const s = bombStatus(u);
  return s === null ? null : (s.remaining ?? 0);
}

/** 炸彈狀態的一行：「定時炸彈（還要 2 次環境回合爆炸，半徑 1 格）」；下一次環境回合就爆炸時特別標出。 */
export function bombStatusText(s: StatusView): string {
  const left = s.remaining ?? 0;
  const when = left <= 1 ? "下一次環境回合就會爆炸" : `還要 ${left} 次環境回合爆炸`;
  const radius = s.blast_radius == null ? "" : `，半徑 ${s.blast_radius} 格`;
  return `${statusName(TIME_BOMB)}（${when}${radius}）`;
}

const xy = (p: readonly number[]): string => `(${p[0]}, ${p[1]})`;

/** 預覽會綁上的定時炸彈：倒數與爆炸範圍（炸彈會跟著攜帶者移動，範圍以目前位置展開）。 */
export function bombLines(p: PreviewOut, names: UnitNames): string[] {
  return (p.bombs ?? []).map(
    (b) =>
      `${names.label(b.unit_id)} 身上綁上定時炸彈：${b.rounds} 次環境回合後在他當下的位置爆炸，` +
      `半徑 ${b.radius} 格（目前波及 ${b.tiles.length} 格；敵我不分，施放者也算）；淨化可以拆除`,
  );
}

/** 預覽的復活：站起來的單位、HP 與站的格子（原位置被占用時註明）。 */
export function reviveLines(p: PreviewOut, names: UnitNames): string[] {
  return (p.revives ?? []).map((r) => {
    const moved = r.pos[0] === r.from_pos[0] && r.pos[1] === r.from_pos[1] ? "" : `（原位置 ${xy(r.from_pos)} 被占用）`;
    return `復活 ${names.label(r.unit_id)}：以 ${r.hp} HP 站在 ${xy(r.pos)}${moved}`;
  });
}
