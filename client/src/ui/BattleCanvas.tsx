// React 包裝：建立／銷毀 PixiJS 繪製器，模型、高亮或縮放改變時重畫。
// 滑鼠事件（Phase 3-8）：在 DOM 上接，以畫布實際的矩形把 client 座標換算成格子（`clientToTile`），
// 不論畫布被縮放多少都對得上。`children` 是疊在畫布上、以畫布左上角為原點的浮動元素（浮動資訊卡等）。
import { useEffect, useLayoutEffect, useRef, useState, useSyncExternalStore, type MouseEvent, type MutableRefObject, type ReactNode } from "react";
import type { Pos } from "../api/types";
import type { DrawModel } from "../battle/drawModel";
import { clientToTile, scaledSize } from "../battle/stageLayout";
import { BattleRenderer, type Highlights } from "../render/BattleRenderer";
import { fontEpoch, subscribeFonts, waitForFonts } from "../render/fontLoad";

interface Props {
  model: DrawModel;
  highlights: Highlights;
  /** 可燃小火苗明顯（true）或淡化（false；Phase 3-38）。 */
  flameOn: boolean;
  /** 畫面上的縮放比例（`fitScale` 算出）。 */
  scale: number;
  /** ``shift``：按住 Shift 點擊（3-40：釘住資訊卡）。 */
  onTileClick(tile: Pos, shift: boolean): void;
  onTileHover(tile: Pos | null): void;
  /** 右鍵（取消選取）。 */
  onCancel(): void;
  /** 給戰鬥畫面播放動畫用。 */
  rendererRef: MutableRefObject<BattleRenderer | null>;
  /** 選部位小選單開著（PB-1c）：戰場是它的觸發元素，標 `aria-expanded`（6.5.1）。省略＝沒有選單。 */
  menuOpen?: boolean;
  children?: ReactNode;
}

/** 繪製器壞掉時最多重建幾次（`REBUILD_WINDOW_MS` 內）。 */
const MAX_REBUILDS = 3;
const REBUILD_WINDOW_MS = 10_000;

function tileFromEvent(e: MouseEvent<HTMLDivElement>, model: DrawModel) {
  const canvas = e.currentTarget.querySelector("canvas");
  if (canvas === null) return null;
  return clientToTile(e.clientX, e.clientY, canvas.getBoundingClientRect(), model);
}

export function BattleCanvas({ model, highlights, flameOn, scale, onTileClick, onTileHover, onCancel, rendererRef, menuOpen, children }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const latest = useRef({ model, highlights, flameOn, scale });
  latest.current = { model, highlights, flameOn, scale };

  // 繪製器壞掉（算繪丟例外、WebGL context 沒恢復）時加一，重建繪製器（UI-T1：原本要 F5 才恢復）。
  const [generation, setGeneration] = useState(0);
  const rebuilds = useRef<number[]>([]);

  useEffect(() => {
    const host = hostRef.current;
    if (host === null) return undefined;
    const renderer = new BattleRenderer();
    rendererRef.current = renderer;
    renderer.onBroken = () => {
      if (rendererRef.current !== renderer) return;
      const now = Date.now();
      rebuilds.current = [...rebuilds.current.filter((t) => now - t < REBUILD_WINDOW_MS), now];
      if (rebuilds.current.length > MAX_REBUILDS) return; // 一直壞：不無限重建（主控台已有錯誤）
      setGeneration((g) => g + 1);
    };
    const show = () => {
      if (rendererRef.current !== renderer) return;
      renderer.setScale(latest.current.scale);
      renderer.draw(latest.current.model);
      renderer.setFlameEmphasis(latest.current.flameOn);
      renderer.setHighlights(latest.current.highlights);
    };
    void renderer
      .init(host)
      .then(async () => {
        await waitForFonts();
        show();
      })
      .catch((e: unknown) => {
        console.error("[BattleCanvas] 繪製器初始化失敗", e);
        renderer.onBroken?.();
      });
    return () => {
      if (rendererRef.current === renderer) rendererRef.current = null;
      renderer.destroy();
      host.replaceChildren();
    };
  }, [rendererRef, generation]);

  // 版面效果：逐步播放時用 flushSync 換畫面，需要同步重畫（動畫才找得到單位）。
  useLayoutEffect(() => {
    rendererRef.current?.draw(model);
    rendererRef.current?.setFlameEmphasis(latest.current.flameOn);
    rendererRef.current?.setHighlights(latest.current.highlights);
  }, [model, rendererRef]);

  useLayoutEffect(() => {
    rendererRef.current?.setHighlights(highlights);
  }, [highlights, rendererRef]);

  // 字型載入完成後重畫（Pixi 文字已用備援字型畫過）
  const epoch = useSyncExternalStore(subscribeFonts, fontEpoch);
  useLayoutEffect(() => {
    rendererRef.current?.draw(latest.current.model);
    rendererRef.current?.setFlameEmphasis(latest.current.flameOn);
    rendererRef.current?.setHighlights(latest.current.highlights);
  }, [epoch, rendererRef]);

  useLayoutEffect(() => {
    rendererRef.current?.setFlameEmphasis(flameOn);
  }, [flameOn, rendererRef]);

  useLayoutEffect(() => {
    rendererRef.current?.setScale(scale);
  }, [scale, rendererRef]);

  // 畫布還沒建立前先用同樣大小佔位，避免版面跳動。
  const size = scaledSize(model, scale);
  return (
    <div
      className="battle-canvas"
      style={{ width: size.width, height: size.height }}
      aria-haspopup={menuOpen === undefined ? undefined : "menu"}
      aria-expanded={menuOpen}
      onPointerMove={(e) => onTileHover(tileFromEvent(e, model))}
      onPointerLeave={() => onTileHover(null)}
      onClick={(e) => {
        const tile = tileFromEvent(e, model);
        if (tile !== null) onTileClick(tile, e.shiftKey);
      }}
      onContextMenu={(e) => {
        e.preventDefault();
        onCancel();
      }}
    >
      <div className="battle-canvas-host" ref={hostRef} />
      {/* 6A-4c：戰鬥區外柔和變暗（邊緣往內淡淡的暗角，不切場景） */}
      <div className="battle-vignette" aria-hidden="true" />
      {children}
    </div>
  );
}
