// 區域圖（Phase 6C-6；21.1）：按 M 或 HUD 地圖鈕打開的浮動全畫面面板，Esc 關閉。
// 只能看（不能點了走過去）；站在傳送石上或在城鎮裡打開時，已解鎖的傳送石可以點了傳送。
// 底圖（6F-ART1）：程式畫的區域插畫（B 俯視彩繪）。地景照區域與尺寸快取，迷霧與標記在狀態變時重畫
// （`render/regionMapPainter.ts`）；地點、任務、傳送石的 DOM 節點留著當透明的點擊、滑過區，位置用同一套 `P()` 換算。
// `art_url` 不再使用（欄位留著）。
import type { WorldMapView } from "../api/types";
import { hitPercent, questHitBox, spotHitBox, stoneHitBox } from "../render/regionMapArt";
import { baseKey, overlayKey, RegionMapPainter } from "../render/regionMapPainter";
import { Hint } from "../ui/Hint";
import { domSurface, MapStage, type StagePaint } from "./MapStage";
import { regionNodes, regionNote, regionScene, stoneTarget, type RegionNode, type RegionStone } from "./regionModel";

interface Props {
  map: WorldMapView;
  busy: boolean;
  onTeleport(to: string): void;
  /** 切到大世界圖（6D-5；M 再按一次也一樣）。 */
  onAtlas?: () => void;
  onClose(): void;
}

let shared: RegionMapPainter | null = null;
/** 整個畫面共用一個（快取跨開關保留：同一區開兩次直接用快取的地景）。 */
function painter(): RegionMapPainter {
  shared ??= new RegionMapPainter(domSurface);
  return shared;
}

function StoneMark({ stone, x, y, k, index, busy, onTeleport }: { stone: RegionStone; x: number; y: number; k: number; index: number; busy: boolean; onTeleport(to: string): void }) {
  const to = stoneTarget(stone);
  const box = stoneHitBox(x, y, k);
  return (
    <Hint text={stone.hint}>
      <button
        type="button"
        className={`region-stone map-hit ${stone.state}`}
        style={hitPercent({ ...box, y: box.y + index * box.h })}
        data-stone={stone.id}
        data-state={stone.state}
        aria-label={stone.hint}
        aria-disabled={to === null || busy}
        onClick={() => {
          if (to !== null && !busy) onTeleport(to);
        }}
      />
    </Hint>
  );
}

function NodeHits({ node, k, busy, onTeleport }: { node: RegionNode; k: number; busy: boolean; onTeleport(to: string): void }) {
  if (node.fog === "fog") return null;
  const cls = ["region-node", "map-hit", node.fog, node.town ? "town" : "", node.current ? "current" : ""].filter((c) => c !== "").join(" ");
  return (
    <>
      <Hint text={node.hint}>
        <span className={cls} style={hitPercent(spotHitBox(node.x, node.y, k))} data-loc={node.id} data-fog={node.fog} tabIndex={0} aria-label={node.hint}>
          {node.current && <span className="map-hit-label" data-testid="region-me">目前位置</span>}
          {node.footprints.length > 0 && <span className="map-hit-label" data-testid="region-footprint">足跡</span>}
        </span>
      </Hint>
      {node.quests.length > 0 && (
        <Hint text={node.quests.map((q) => `任務：${q}`).join("\n")}>
          <span
            className="region-quest map-hit"
            style={hitPercent(questHitBox(node.x, node.y, k))}
            data-testid="region-quest"
            tabIndex={0}
            aria-label={`任務：${node.quests.join("、")}`}
          />
        </Hint>
      )}
      {node.stones.map((s, i) => (
        <StoneMark key={s.id} stone={s} x={node.x} y={node.y} k={k} index={i} busy={busy} onTeleport={onTeleport} />
      ))}
    </>
  );
}

export function RegionMap({ map, busy, onTeleport, onAtlas, onClose }: Props) {
  const nodes = regionNodes(map);
  const scene = regionScene(map);
  const paint = (pw: number, ph: number, k: number, epoch: number): StagePaint => ({
    baseKey: baseKey(map.region, pw, ph, epoch),
    overlayKey: overlayKey(scene, pw, ph, k, epoch),
    paintBase: (ctx, w, h, e) => painter().paintBase(ctx, map.region, w, h, e),
    paintOverlay: (ctx, w, h, kk) => painter().paintOverlay(ctx, scene, w, h, kk),
  });
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
          <span className="region-map-keys muted">{onAtlas !== undefined ? "M 大世界圖／Esc 關閉" : "Esc 關閉"}</span>
          {onAtlas !== undefined && (
            <button type="button" className="atlas-switch" onClick={onAtlas} data-testid="region-map-atlas">
              大世界圖（M）
            </button>
          )}
          <button data-sfx="ui_cancel" type="button" className="world-hud-panel-close" onClick={onClose} aria-label="關閉區域圖（Esc）" data-testid="region-map-close">
            ×
          </button>
        </header>
        <MapStage className="region-map-canvas" paint={paint} testId="region-map-stage">
          {(k) => nodes.map((n) => <NodeHits key={n.id} node={n} k={k} busy={busy} onTeleport={onTeleport} />)}
        </MapStage>
      </div>
    </div>
  );
}
