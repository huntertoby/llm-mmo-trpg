// 大世界圖（Phase 6D-5；21.1）：五區畫成漂浮的界域、主城在中央浮島。按 M 在區域圖上再按一次打開，Esc 關閉。
// 已開放的區彩色（點了進該區的區域圖）；未解鎖的灰色剪影寫條件；第一季其他三區寫「之後的賽季」。
// 站在傳送石上或在城鎮裡打開時，已開放區的城鎮可以點了直接傳送（送 `teleport`）。
// 底圖：`art_url` 有值時畫插畫，否則用程式畫的簡單浮島。
import type { AtlasView, WorldMapView } from "../api/types";
import { Hint } from "../ui/Hint";
import { atlasIslands, atlasNote, capitalIsland, type AtlasIsland } from "./atlasModel";

interface Props {
  atlas: AtlasView;
  /** 所在區的區域圖（判斷哪些區點得進去）。 */
  map: WorldMapView;
  busy: boolean;
  onOpenRegion(region: string): void;
  onTeleport(region: string): void;
  onClose(): void;
}

/** 浮島：上面是地面（橢圓）、下面是倒三角的岩塊，旁邊一抹雲。 */
function IslandArt({ tone }: { tone: string }) {
  return (
    <svg viewBox="0 0 100 70" className="atlas-island-art" aria-hidden="true">
      <path d="M12 30 Q50 72 88 30 Z" className="atlas-rock" />
      <path d="M30 40 L50 68 L66 42 Z" className="atlas-rock deep" />
      <ellipse cx="50" cy="28" rx="40" ry="13" className={`atlas-land ${tone}`} />
      <ellipse cx="50" cy="25" rx="30" ry="7" className={`atlas-land-top ${tone}`} />
      <path d="M2 46 q8 -6 16 0 q6 -5 12 0" className="atlas-cloud" />
      <path d="M72 52 q7 -5 14 0 q5 -4 11 0" className="atlas-cloud" />
    </svg>
  );
}

function Island({
  island,
  busy,
  onOpenRegion,
  onTeleport,
  capital = false,
}: {
  island: AtlasIsland;
  busy: boolean;
  onOpenRegion(region: string): void;
  onTeleport(region: string): void;
  capital?: boolean;
}) {
  const { spot } = island;
  const style = { left: `${spot.x}%`, top: `${spot.y}%`, width: `${spot.size}%` };
  const tone = capital ? "capital" : island.status === "open" ? island.region : "grey";
  const cls = ["atlas-island", island.status, capital ? "capital" : "", island.current ? "current" : "", island.canOpen ? "openable" : ""]
    .filter((c) => c !== "")
    .join(" ");
  return (
    <div className={cls} style={style} data-region={island.region} data-status={island.status} data-testid={`atlas-${island.region}`}>
      <Hint text={island.hint}>
        <button
          type="button"
          className="atlas-island-body"
          aria-label={island.hint}
          aria-disabled={!island.canOpen}
          onClick={() => {
            if (island.canOpen) onOpenRegion(island.region);
          }}
        >
          <IslandArt tone={tone} />
          {island.current && <span className="atlas-me" aria-hidden="true" data-testid="atlas-me" />}
        </button>
      </Hint>
      <div className="atlas-island-name">{island.name}</div>
      {island.status === "open" ? (
        island.canTeleport ? (
          <button
            type="button"
            className="atlas-town go"
            disabled={busy}
            onClick={() => onTeleport(island.region)}
            data-testid={`atlas-teleport-${island.region}`}
          >
            傳送到{island.caption}
          </button>
        ) : (
          island.caption !== "" && <div className="atlas-town">{island.caption}</div>
        )
      ) : (
        <div className="atlas-condition" data-testid={`atlas-condition-${island.region}`}>
          {island.caption}
        </div>
      )}
    </div>
  );
}

export function AtlasMap({ atlas, map, busy, onOpenRegion, onTeleport, onClose }: Props) {
  const islands = atlasIslands(atlas, map);
  const capital = capitalIsland(atlas);
  const art = atlas.art_url ?? null;
  return (
    <div className="region-map-backdrop" data-testid="atlas-backdrop" onClick={onClose}>
      <div
        className={`region-map atlas-map${atlas.can_teleport ? " can-teleport" : ""}`}
        role="dialog"
        aria-label="大世界圖"
        data-testid="atlas-map"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="region-map-head">
          <h2>大世界圖</h2>
          <span className={`region-map-note${atlas.can_teleport ? " go" : ""}`} data-testid="atlas-note">
            {atlasNote(atlas)}
          </span>
          <button type="button" className="world-hud-panel-close" onClick={onClose} aria-label="關閉大世界圖（Esc）" data-testid="atlas-close">
            ×
          </button>
        </header>
        <div className="region-map-canvas atlas-canvas" style={art !== null ? { backgroundImage: `url(${art})` } : undefined} data-art={art ?? ""}>
          <svg className="atlas-bridges" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
            {islands.map((i) => (
              <line
                key={i.region}
                x1={capital.spot.x}
                y1={capital.spot.y}
                x2={i.spot.x}
                y2={i.spot.y}
                className={i.status === "open" ? "open" : "dim"}
                vectorEffect="non-scaling-stroke"
              />
            ))}
          </svg>
          {islands.map((i) => (
            <Island key={i.region} island={i} busy={busy} onOpenRegion={onOpenRegion} onTeleport={onTeleport} />
          ))}
          <Island island={capital} busy={busy} onOpenRegion={onOpenRegion} onTeleport={onTeleport} capital />
        </div>
        <footer className="region-map-legend" aria-label="圖例">
          <span><i className="lg-open" />已開放（點了看區域圖）</span>
          <span><i className="lg-sil" />未解鎖（寫條件）</span>
          <span><i className="lg-later" />之後的賽季</span>
          <span><i className="lg-me" />自己</span>
          <span className="muted">M／Esc 關閉</span>
        </footer>
      </div>
    </div>
  );
}
