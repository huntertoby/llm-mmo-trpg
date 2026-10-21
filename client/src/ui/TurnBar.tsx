// 回合列：輪數、目前行動者、先攻順序（每個單位的代號與 HP 小條，目前行動者強調）。
import type { BattleView } from "../api/types";
import { objectiveHud, objectiveLine } from "../battle/objective";
import { remainingRounds, summonKind } from "../battle/summons";
import type { UnitNames } from "../battle/units";

interface Props {
  view: BattleView;
  names: UnitNames;
  /** 逐步播放時指定的行動者；省略時用 `view.active_unit`。 */
  acting?: string | null;
}

export function TurnBar({ view, names, acting }: Props) {
  const byId = new Map(view.units.map((u) => [u.id, u]));
  const activeId = acting === undefined || acting === null ? view.active_unit : acting;
  const rounds =
    view.max_rounds === null ? `第 ${view.round} 輪` : `第 ${view.round} / ${view.max_rounds} 輪`;
  return (
    <div className="turn-bar">
      <span className="turn-round">{rounds}</span>
      <span
        className={`turn-objective ${view.objective.kind}`}
        title={objectiveLine(view.objective)}
      >
        {objectiveHud(view.objective, view.round)}
      </span>
      <span className="turn-map">
        {view.map_name_zh}
        {view.weather_name_zh === null ? "" : `・${view.weather_name_zh}`}
      </span>
      <span className="turn-active">行動中：{activeId === null ? "—" : names.label(activeId)}</span>
      <ol className="turn-order" aria-label="先攻順序">
        {view.turn_order.map((id) => {
          const u = byId.get(id);
          const gone = u === undefined || u.downed || u.escaped || u.dismissed;
          const ratio = u === undefined || u.max_hp <= 0 ? 0 : Math.max(0, Math.min(1, u.hp / u.max_hp));
          const cls = [
            "turn-chip",
            u?.team ?? "",
            id === activeId ? "active" : "",
            gone ? "gone" : "",
            u?.owner_id == null ? "" : "summon",
          ].join(" ");
          const kind = u === undefined ? null : summonKind(u);
          const left = u === undefined ? null : remainingRounds(view, u);
          const note =
            kind === null || u === undefined || u.owner_id === null
              ? ""
              : `　${kind}（${names.name(u.owner_id)}召喚${left === null ? "" : `，剩 ${left} 輪`}）`;
          return (
            <li key={id} className={cls} title={`${names.label(id)}　HP ${u?.hp ?? 0} / ${u?.max_hp ?? 0}${note}`}>
              <span className="turn-chip-marker">{names.marker(id)}</span>
              {left !== null && <span className="turn-chip-left">{left}</span>}
              <span className="turn-chip-hp">
                <span style={{ width: `${ratio * 100}%` }} />
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
