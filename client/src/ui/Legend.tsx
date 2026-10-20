// 戰場顏色圖例（只在需要時出現，見 battle/legend.ts）。
import { cssColor, type LegendEntry } from "../battle/legend";

export function Legend({ entries }: { entries: readonly LegendEntry[] }) {
  if (entries.length === 0) return null;
  return (
    <div className="battle-legend" aria-label="顏色圖例">
      {entries.map((e) => (
        <span key={e.label} className="legend-item">
          <span className="legend-swatch" style={{ background: cssColor(e.color) }} />
          {e.label}
        </span>
      ))}
    </div>
  );
}
