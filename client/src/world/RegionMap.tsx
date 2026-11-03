// 區域圖（Phase 6C-6；21.1）：按 M 或 HUD 地圖鈕打開的浮動全畫面面板，Esc 關閉。
// 只能看（不能點了走過去）；站在傳送石上或在城鎮裡打開時，已解鎖的傳送石可以點了傳送。
// 底圖：`art_url` 有值時畫區域插畫，否則用節點圖的座標與連線（座標 0～100，同 `WorldMap`）。
import type { WorldMapView } from "../api/types";
import { Hint } from "../ui/Hint";
import { footprintHint, regionEdges, regionNodes, regionNote, stoneTarget, type RegionNode, type RegionStone } from "./regionModel";

interface Props {
  map: WorldMapView;
  busy: boolean;
  onTeleport(to: string): void;
  /** 切到大世界圖（6D-5；M 再按一次也一樣）。 */
  onAtlas?: () => void;
  onClose(): void;
}

function StoneMark({ stone, busy, onTeleport }: { stone: RegionStone; busy: boolean; onTeleport(to: string): void }) {
  const to = stoneTarget(stone);
  return (
    <Hint text={stone.hint}>
      <button
        type="button"
        className={`region-stone ${stone.state}`}
        data-stone={stone.id}
        data-state={stone.state}
        aria-label={stone.hint}
        aria-disabled={to === null || busy}
        onClick={() => {
          if (to !== null && !busy) onTeleport(to);
        }}
      >
        <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
          <path d="M8 1.5 L12.5 6 L8 14.5 L3.5 6 Z" className="region-stone-gem" />
          {(stone.state === "locked" || stone.state === "view") && (
            <g className="region-stone-lock">
              <rect x="8.5" y="9" width="6.5" height="5.5" rx="1" />
              <path d="M10 9 V7.6 a1.75 1.75 0 0 1 3.5 0 V9" fill="none" />
            </g>
          )}
        </svg>
      </button>
    </Hint>
  );
}

function Node({ node, busy, onTeleport }: { node: RegionNode; busy: boolean; onTeleport(to: string): void }) {
  const style = { left: `${node.x}%`, top: `${node.y}%` };
  if (node.fog === "fog") {
    return <div className="region-fog" style={style} data-loc={node.id} data-fog="fog" aria-hidden="true" />;
  }
  const cls = ["region-node", node.fog, node.town ? "town" : "", node.current ? "current" : ""].filter((c) => c !== "").join(" ");
  return (
    <div className={cls} style={style} data-loc={node.id} data-fog={node.fog}>
      <Hint text={node.hint}>
        <span className="region-node-dot" tabIndex={0} aria-label={node.hint}>
          {node.current && <span className="region-me" aria-hidden="true" data-testid="region-me" />}
        </span>
      </Hint>
      {node.label !== null && <span className="region-node-name">{node.label}</span>}
      {(node.level !== null || node.cleared) && <span className="region-node-badge">{node.cleared ? "已清空" : node.level}</span>}
      {(node.quests.length > 0 || node.stones.length > 0 || node.footprints.length > 0) && (
        <span className="region-node-marks">
          {node.footprints.length > 0 && (
            <Hint text={footprintHint(node.footprints)}>
              <span className="region-footprint" data-testid="region-footprint" aria-label={footprintHint(node.footprints)}>
                足
              </span>
            </Hint>
          )}
          {node.quests.length > 0 && (
            <Hint text={node.quests.map((q) => `任務：${q}`).join("\n")}>
              <span className="region-quest" data-testid="region-quest" aria-label={`任務：${node.quests.join("、")}`}>
                !
              </span>
            </Hint>
          )}
          {node.stones.map((s) => (
            <StoneMark key={s.id} stone={s} busy={busy} onTeleport={onTeleport} />
          ))}
        </span>
      )}
    </div>
  );
}

export function RegionMap({ map, busy, onTeleport, onAtlas, onClose }: Props) {
  const nodes = regionNodes(map);
  const edges = regionEdges(map);
  const art = map.art_url ?? null;
  return (
    <div className="region-map-backdrop" data-testid="region-map-backdrop" onClick={onClose}>
      <div
        className={`region-map${map.can_teleport ? " can-teleport" : ""}`}
        role="dialog"
        aria-label={`區域圖：${map.name_zh}`}
        data-testid="region-map"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="region-map-head">
          <h2>
            {map.name_zh}
            <span className="region-map-level">{map.level_zh}</span>
          </h2>
          <span className={`region-map-note${map.can_teleport ? " go" : ""}`} data-testid="region-map-note">
            {regionNote(map)}
          </span>
          {onAtlas !== undefined && (
            <button type="button" className="atlas-switch" onClick={onAtlas} data-testid="region-map-atlas">
              大世界圖（M）
            </button>
          )}
          <button type="button" className="world-hud-panel-close" onClick={onClose} aria-label="關閉區域圖（Esc）" data-testid="region-map-close">
            ×
          </button>
        </header>
        <div className="region-map-canvas" style={art !== null ? { backgroundImage: `url(${art})` } : undefined} data-art={art ?? ""}>
          <div className="region-map-area">
            <svg className="region-map-lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
              {edges.map((e) => (
                <line key={e.key} x1={e.x1} y1={e.y1} x2={e.x2} y2={e.y2} className={e.known ? "known" : "dim"} vectorEffect="non-scaling-stroke" />
              ))}
            </svg>
            {nodes.map((n) => (
              <Node key={n.id} node={n} busy={busy} onTeleport={onTeleport} />
            ))}
          </div>
        </div>
        <footer className="region-map-legend" aria-label="圖例">
          <span><i className="lg-me" />自己</span>
          <span><i className="lg-quest">!</i>任務</span>
          <span><i className="lg-stone" />傳送石</span>
          <span><i className="lg-foot">足</i>朋友的足跡</span>
          <span><i className="lg-sil" />沒去過（？？？）</span>
          <span><i className="lg-fog" />霧</span>
          <span className="muted">M 大世界圖／Esc 關閉</span>
        </footer>
      </div>
    </div>
  );
}
