// 大世界圖（Phase 6D-5；21.1）：五區畫成漂浮的界域、主城在中央浮島。按 M 在區域圖上再按一次打開，Esc 關閉。
// 已開放的區彩色（點了進該區的區域圖）；未解鎖的灰色剪影寫條件；第一季其他三區寫「之後的賽季」。
// 站在傳送石上或在城鎮裡打開時，已開放區的城鎮可以點了直接傳送（送 `teleport`）。
// 底圖（6F-ART1）：程式畫的大世界插畫（`render/worldMapArt.ts`）。天空照尺寸快取，浮島與字牌依狀態重畫；
// 浮島、傳送鈕、條件的 DOM 節點留著當透明的點擊、滑過區，位置與畫布同一套座標。`art_url` 不再使用（欄位留著）。
// 第 2 版（6F-ART1b）：浮島連同字牌、傳送鈕、自己上下漂浮（`render/worldMapPainter.ts`）；點擊區不跟著動。
// RT-5 ③：角色第一次打開時五座島依序從雲裡浮起（每座 0.3 秒、只播一次；減少動態時直接顯示，`rise` 由 WorldScreen 決定）；
// 第一次免費傳送的那一區（伺服器的 `free`）傳送鈕發金光、寫「免費」。
// FIX-ATLAS2（美術 PM 第九任）：鎖住／之後的賽季的浮島滑過時，畫布上只把那座島的本體貼成稍亮的一張（`LOCKED_HOVER_LIGHT`）；
// 不加底色、框、金色光暈、放大，游標維持 default（那些是「能去」的語言）。開放的島滑過照舊（CSS）。
import { useLayoutEffect, useRef, useState } from "react";
import type { AtlasView, WorldMapView } from "../api/types";
import { devAnimFactor } from "../battle/playback";
import { hitPercent } from "../render/regionMapArt";
import { buttonHitBox, FREE_ZH, islandHitBox, type AtlasArtIsland } from "../render/worldMapArt";
import { AtlasPainter, atlasBaseKey, RISE_STEP_MS } from "../render/worldMapPainter";
import { Hint } from "../ui/Hint";
import { atlasNote, type AtlasIsland } from "./atlasModel";
import { atlasScene } from "./atlasScene";
import { domSurface, MapStage, type StagePaint } from "./MapStage";

interface Props {
  atlas: AtlasView;
  /** 所在區的區域圖（判斷哪些區點得進去）。 */
  map: WorldMapView;
  busy: boolean;
  /** RT-5 ③：這次打開要播「五座島依序從雲裡浮起」（只有角色第一次打開、沒有減少動態時；由呼叫端決定）。 */
  rise?: boolean;
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
  onHoverLocked,
}: {
  island: AtlasIsland;
  art: AtlasArtIsland;
  busy: boolean;
  onOpenRegion(region: string): void;
  onTeleport(region: string): void;
  capital?: boolean;
  k?: number;
  /** FIX-ATLAS2：滑進（region）／滑出（null）不能去的浮島。 */
  onHoverLocked?(region: string | null): void;
}) {
  const cls = ["atlas-island", "map-hit", island.status, capital ? "capital" : "", island.current ? "current" : "", island.canOpen ? "openable" : ""]
    .filter((c) => c !== "")
    .join(" ");
  const btn = buttonHitBox(art, k);
  const locked = island.status !== "open";
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
          onPointerEnter={locked ? () => onHoverLocked?.(island.region) : undefined}
          onPointerLeave={locked ? () => onHoverLocked?.(null) : undefined}
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
          data-free={island.free ? "1" : undefined}
        >
          <span className="map-hit-label">
            傳送到{island.caption}
            {island.free ? `（${FREE_ZH}）` : ""}
          </span>
        </button>
      )}
    </>
  );
}

/** 說明卡的每一段（「・」分開）不在中間斷行（6F-3 巡檢 bug 18：「點了看區域圖」斷成「點了看區／域圖」）。 */
export function HintPhrases({ text }: { text: string }) {
  // RT-5b 必修 3：每一段不拆開，段與段之間可以換行，照卡片寬度排成幾行，不會整句擠成一行被切掉。
  // RT-5c 小修 9：「・」是不能放在行首的字（禁則），換行時會被推到上一行的行尾（第一行結尾多一個「・」）。
  // 改成：每一段是一個 inline-block（段與段之間一定能換行），「・」放在段尾；排好之後，段尾剛好是行尾的那個「・」藏起來
  //（`visibility: hidden`，寬度不變，不會因為藏起來又把下一段拉上來）。
  const ref = useRef<HTMLSpanElement | null>(null);
  useLayoutEffect(() => {
    const box = ref.current;
    if (box === null) return;
    const mark = () => {
      const parts = [...box.querySelectorAll<HTMLElement>(".atlas-hint-phrase")];
      parts.forEach((el, i) => {
        const next = parts[i + 1];
        const eol = next !== undefined && next.offsetTop > el.offsetTop + 2;
        if (eol) el.dataset.eol = "1";
        else delete el.dataset.eol;
      });
    };
    mark();
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(mark);
    ro.observe(box);
    return () => ro.disconnect();
  }, [text]);
  const parts = text.split("・");
  return (
    <span className="atlas-hint-phrases" ref={ref}>
      {parts.map((part, i) => (
        <span key={i} className="atlas-hint-phrase">
          {part}
          {i < parts.length - 1 && <span className="atlas-hint-sep">・</span>}
        </span>
      ))}
    </span>
  );
}

export function AtlasMap({ atlas, map, busy, rise = false, onOpenRegion, onTeleport, onClose }: Props) {
  const { scene, islands, capital } = atlasScene(atlas, map);
  const [hoverLocked, setHoverLocked] = useState<string | null>(null);
  // 浮起的起點＝第一格動畫的時間（`?anim=` 放慢時照倍率拉長，逐格截圖用）
  const riseStart = useRef<number | null>(null);
  const slow = typeof window === "undefined" ? 1 : devAnimFactor(window.location.search);
  const riseAtT = (t: number | null): number | null => {
    if (!rise || t === null) return null;
    riseStart.current ??= t;
    const elapsed = (t - riseStart.current) / slow;
    return elapsed >= scene.islands.length * RISE_STEP_MS ? null : elapsed;
  };
  const paint = (pw: number, ph: number, k: number, epoch: number): StagePaint => ({
    baseKey: atlasBaseKey(scene, pw, ph),
    overlayKey: JSON.stringify([scene, atlas.can_teleport, pw, ph, k, epoch, hoverLocked]),
    paintBase: (ctx, w, h) => painter().paintBase(ctx, scene, w, h),
    paintOverlay: (ctx, w, h, kk, ep, t) => painter().paintOverlay(ctx, scene, atlas.can_teleport, w, h, kk, { t, epoch: ep, rise: riseAtT(t), hoverLocked }),
    animated: true,
  });
  return (
    <div className="region-map-backdrop" data-testid="atlas-backdrop" onClick={onClose}>
      <div
        className={`region-map atlas-map${atlas.can_teleport ? " can-teleport" : ""}`}
        role="dialog"
        aria-label="大世界圖"
        data-testid="atlas-map"
        data-rise={rise ? "1" : "0"}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="region-map-head">
          <h2>大世界圖</h2>
          <span className={`region-map-note${atlas.can_teleport ? " go" : ""}`} data-testid="atlas-note">
            {atlasNote(atlas)}
          </span>
          <span className="region-map-keys muted">M／Esc 關閉</span>
          <button data-sfx="ui_cancel" type="button" className="world-hud-panel-close" onClick={onClose} aria-label="關閉大世界圖（Esc）" data-testid="atlas-close">
            ×
          </button>
        </header>
        <MapStage className="region-map-canvas atlas-canvas" paint={paint} testId="atlas-stage">
          {(k) => (
            <>
              {islands.map((i, n) => {
                const art = scene.islands[n];
                return art === undefined ? null : (
                  <IslandHits
                    key={i.region}
                    island={i}
                    art={art}
                    busy={busy}
                    onOpenRegion={onOpenRegion}
                    onTeleport={onTeleport}
                    k={k}
                    onHoverLocked={setHoverLocked}
                  />
                );
              })}
              <IslandHits island={capital} art={scene.capital} busy={busy} onOpenRegion={onOpenRegion} onTeleport={onTeleport} capital k={k} onHoverLocked={setHoverLocked} />
            </>
          )}
        </MapStage>
      </div>
    </div>
  );
}
