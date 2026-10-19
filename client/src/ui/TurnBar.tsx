// 回合資訊：輪數、目前行動者、先攻順序。
import type { BattleView } from "../api/types";
import type { UnitNames } from "../battle/units";

interface Props {
  view: BattleView;
  names: UnitNames;
}

export function TurnBar({ view, names }: Props) {
  const byId = new Map(view.units.map((u) => [u.id, u]));
  const rounds =
    view.max_rounds === null ? `第 ${view.round} 輪` : `第 ${view.round} / ${view.max_rounds} 輪`;
  return (
    <div className="turn-bar">
      <span className="turn-round">{rounds}</span>
      <span className="turn-map">
        {view.map_name_zh}
        {view.weather_name_zh === null ? "" : `・${view.weather_name_zh}`}
      </span>
      <span className="turn-active">
        行動中：{view.active_unit === null ? "—" : names.label(view.active_unit)}
      </span>
      <ol className="turn-order" aria-label="先攻順序">
        {view.turn_order.map((id) => {
          const u = byId.get(id);
          const gone = u === undefined || u.downed || u.escaped;
          const cls = [
            "turn-chip",
            u?.team ?? "",
            id === view.active_unit ? "active" : "",
            gone ? "gone" : "",
          ].join(" ");
          return (
            <li key={id} className={cls} title={names.label(id)}>
              {names.marker(id)}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
