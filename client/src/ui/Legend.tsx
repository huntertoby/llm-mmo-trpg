// 戰場顏色圖例（Phase 3-8 起放在頂端列「圖例」的彈出面板）：目前畫面上需要說明的顏色（複合技能，
// 見 battle/legend.ts）在前，常見的顏色與標記在後。
import { BASE_LEGEND, cssColor, type LegendEntry } from "../battle/legend";

function Item({ e }: { e: LegendEntry }) {
  return (
    <span className="legend-item">
      <span className="legend-swatch" style={{ background: cssColor(e.color) }} />
      {e.label}
    </span>
  );
}

export function Legend({ entries }: { entries: readonly LegendEntry[] }) {
  return (
    <div className="battle-legend" aria-label="顏色圖例">
      {entries.length > 0 && (
        <>
          <div className="section-title">目前的選取</div>
          {entries.map((e) => (
            <Item key={`now:${e.label}`} e={e} />
          ))}
          <div className="section-title">戰場</div>
        </>
      )}
      {BASE_LEGEND.map((e) => (
        <Item key={e.label} e={e} />
      ))}
    </div>
  );
}
