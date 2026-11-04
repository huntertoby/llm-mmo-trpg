// 大世界圖（Phase 6D-5；21.1）：五區畫成漂浮的界域、主城在中央浮島。按 M 在區域圖上再按一次打開，Esc 關閉。
// 已開放的區彩色（點了進該區的區域圖）；未解鎖的灰色剪影寫條件；第一季其他三區寫「之後的賽季」。
// 站在傳送石上或在城鎮裡打開時，已開放區的城鎮可以點了直接傳送（送 `teleport`）。
// 底圖（6F-ART1）：程式畫的大世界插畫（`render/worldMapArt.ts`）。天空照尺寸快取，浮島與字牌依狀態重畫；
// 浮島、傳送鈕、條件的 DOM 節點留著當透明的點擊、滑過區，位置與畫布同一套座標。`art_url` 不再使用（欄位留著）。
// 第 2 版（6F-ART1b）：浮島連同字牌、傳送鈕、自己上下漂浮（`render/worldMapPainter.ts`）；點擊區不跟著動。
import type { AtlasView, WorldMapView } from "../api/types";
import { hitPercent } from "../render/regionMapArt";
import { buttonHitBox, islandHitBox, type AtlasArtIsland } from "../render/worldMapArt";
import { AtlasPainter, atlasBaseKey } from "../render/worldMapPainter";
import { Hint } from "../ui/Hint";
import { atlasNote, type AtlasIsland } from "./atlasModel";
import { atlasScene } from "./atlasScene";
import { domSurface, MapStage, type StagePaint } from "./MapStage";

interface Props {
  atlas: AtlasView;
  /** 所在區的區域圖（判斷哪些區點得進去）。 */
  map: WorldMapView;
  busy: boolean;
  onOpenRegion(region: string): void;
  onTeleport(region: string): void;
  onClose(): void;
}

let shared: AtlasPainter | null = null;
function painter(): AtlasPainter {
  shared ??= new AtlasPainter(domSurface);
  return shared;
}

function IslandHits({
  island,
  art,
  busy,
  onOpenRegion,
  onTeleport,
  capital = false,
  k = 1,
}: {
  island: AtlasIsland;
  art: AtlasArtIsland;
  busy: boolean;
  onOpenRegion(region: string): void;
  onTeleport(region: string): void;
  capital?: boolean;
  k?: number;
}) {
  const cls = ["atlas-island", "map-hit", island.status, capital ? "capital" : "", island.current ? "current" : "", island.canOpen ? "openable" : ""]
    .filter((c) => c !== "")
    .join(" ");
  const btn = buttonHitBox(art, k);
  return (
    <>
      <Hint text={island.hint} rich={<HintPhrases text={island.hint} />}>
        <button
          type="button"
          className={cls}
          style={hitPercent(islandHitBox(art))}
          data-region={island.region}
          data-status={island.status}
          data-testid={`atlas-${island.region}`}
          aria-label={island.hint}
          aria-disabled={!island.canOpen}
          onClick={() => {
            if (island.canOpen) onOpenRegion(island.region);
          }}
        >
          <span className="map-hit-label">{island.name}</span>
          {island.status === "open" ? (
            island.caption !== "" && <span className="map-hit-label">{island.caption}</span>
          ) : (
            <span className="map-hit-label" data-testid={`atlas-condition-${island.region}`}>
              {island.caption}
            </span>
          )}
          {island.current && <span className="map-hit-label" data-testid="atlas-me">你在這裡</span>}
        </button>
      </Hint>
      {btn !== null && (
        <button
          type="button"
          className="atlas-town go map-hit"
          style={hitPercent(btn)}
          disabled={busy}
          onClick={() => onTeleport(island.region)}
          data-testid={`atlas-teleport-${island.region}`}
        >
          <span className="map-hit-label">傳送到{island.caption}</span>
        </button>
      )}
    </>
  );
}

/** 說明卡的每一段（「・」分開）不在中間斷行（6F-3 巡檢 bug 18：「點了看區域圖」斷成「點了看區／域圖」）。 */
function HintPhrases({ text }: { text: string }) {
  return (
    <span>
      {text.split("・").map((part, i) => (
        <span key={i} style={{ whiteSpace: "nowrap" }}>
          {i > 0 ? "・" : ""}
          {part}
        </span>
      ))}
    </span>
  );
}

export function AtlasMap({ atlas, map, busy, onOpenRegion, onTeleport, onClose }: Props) {
  const { scene, islands, capital } = atlasScene(atlas, map);
  const paint = (pw: number, ph: number, k: number, epoch: number): StagePaint => ({
    baseKey: atlasBaseKey(scene, pw, ph),
    overlayKey: JSON.stringify([scene, atlas.can_teleport, pw, ph, k, epoch]),
    paintBase: (ctx, w, h) => painter().paintBase(ctx, scene, w, h),
    paintOverlay: (ctx, w, h, kk, ep, t) => painter().paintOverlay(ctx, scene, atlas.can_teleport, w, h, kk, { t, epoch: ep }),
    animated: true,
  });
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
          <span className="region-map-keys muted">M／Esc 關閉</span>
          <button type="button" className="world-hud-panel-close" onClick={onClose} aria-label="關閉大世界圖（Esc）" data-testid="atlas-close">
            ×
          </button>
        </header>
        <MapStage className="region-map-canvas atlas-canvas" paint={paint} testId="atlas-stage">
          {(k) => (
            <>
              {islands.map((i, n) => {
                const art = scene.islands[n];
                return art === undefined ? null : (
                  <IslandHits key={i.region} island={i} art={art} busy={busy} onOpenRegion={onOpenRegion} onTeleport={onTeleport} k={k} />
                );
              })}
              <IslandHits island={capital} art={scene.capital} busy={busy} onOpenRegion={onOpenRegion} onTeleport={onTeleport} capital k={k} />
            </>
          )}
        </MapStage>
      </div>
    </div>
  );
}
