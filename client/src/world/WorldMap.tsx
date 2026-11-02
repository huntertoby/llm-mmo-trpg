// 地點圖（Phase 5A-5；09 9.6.2「點哪裡就走過去」）：程式繪製，座標用內容的 `pos`（0～100）。
// 連線畫在底下的 SVG；地點是按鈕（滑過用共用說明卡 `Hint` 顯示種類、建議等級、說明，6.5.1）。
// 未發現的隱藏地點後端根本不送；可以走的相鄰地點才可點。
import type { WorldView } from "../api/types";
import { Hint } from "../ui/Hint";
import { canTravel, edgeLine, locationBadge, locationClass, locationHint } from "./mapView";

interface Props {
  view: WorldView;
  busy: boolean;
  onTravel(to: string): void;
}

export function WorldMap({ view, busy, onTravel }: Props) {
  const encounter = view.encounter !== null || view.battle_id !== null;
  return (
    <div className="world-map" data-testid="world-map">
      <div className="world-map-area">
      <svg className="world-map-lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        {view.map.edges.map((edge) => {
          const line = edgeLine(view, edge);
          if (line === null) return null;
          return (
            <line
              key={`${edge[0]}-${edge[1]}`}
              x1={line.x1}
              y1={line.y1}
              x2={line.x2}
              y2={line.y2}
              className={line.near ? "near" : undefined}
              vectorEffect="non-scaling-stroke"
            />
          );
        })}
      </svg>
      {view.map.locations.map((loc) => {
        const go = canTravel(loc, encounter);
        const badge = locationBadge(loc);
        return (
          <Hint key={loc.id} text={locationHint(loc, encounter)}>
            <button
              type="button"
              className={locationClass(loc, encounter)}
              style={{ left: `${loc.x}%`, top: `${loc.y}%` }}
              aria-disabled={!go || busy}
              aria-current={loc.current ? "location" : undefined}
              aria-label={`${loc.name_zh}${loc.current ? "（目前位置）" : ""}`}
              data-loc={loc.id}
              onClick={() => {
                if (go && !busy) onTravel(loc.id);
              }}
            >
              <span className="world-loc-dot" aria-hidden="true" />
              <span className="world-loc-name">{loc.name_zh}</span>
              {badge !== null && <span className="world-loc-badge">{badge}</span>}
            </button>
          </Hint>
        );
      })}
      </div>
    </div>
  );
}
