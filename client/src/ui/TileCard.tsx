// 滑過格子的地形資訊卡（Phase 3-15）：與單位浮動卡同樣式；內容由 battle/tileInfo.ts 組合。
import type { TileSection } from "../battle/tileInfo";

export function TileCard({ sections }: { sections: readonly TileSection[] }) {
  if (sections.length === 0) return null;
  return (
    <div className="panel tile-card" aria-label="格子資訊">
      {sections.map((s, i) => (
        <div key={`${s.kind}:${i}`} className={`tile-section ${s.kind}`}>
          <div className="tile-title">{s.title}</div>
          {s.lines.length > 0 && (
            <ul className="tile-lines">
              {s.lines.map((l, j) => (
                <li key={`${j}:${l}`}>{l}</li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}
