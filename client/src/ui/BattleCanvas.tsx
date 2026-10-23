// React 包裝：建立／銷毀 PixiJS 繪製器，模型、高亮或縮放改變時重畫。
// 滑鼠事件（Phase 3-8）：在 DOM 上接，以畫布實際的矩形把 client 座標換算成格子（`clientToTile`），
// 不論畫布被縮放多少都對得上。`children` 是疊在畫布上、以畫布左上角為原點的浮動元素（浮動資訊卡等）。
import { useEffect, useLayoutEffect, useRef, useSyncExternalStore, type MouseEvent, type MutableRefObject, type ReactNode } from "react";
import type { Pos } from "../api/types";
import type { DrawModel } from "../battle/drawModel";
import { clientToTile, scaledSize } from "../battle/stageLayout";
import { BattleRenderer, type Highlights } from "../render/BattleRenderer";
import { fontEpoch, subscribeFonts, waitForFonts } from "../render/fontLoad";

interface Props {
  model: DrawModel;
  highlights: Highlights;
  /** 畫面上的縮放比例（`fitScale` 算出）。 */
  scale: number;
  onTileClick(tile: Pos): void;
  onTileHover(tile: Pos | null): void;
  /** 右鍵（取消選取）。 */
  onCancel(): void;
  /** 給戰鬥畫面播放動畫用。 */
  rendererRef: MutableRefObject<BattleRenderer | null>;
  children?: ReactNode;
}

function tileFromEvent(e: MouseEvent<HTMLDivElement>, model: DrawModel) {
  const canvas = e.currentTarget.querySelector("canvas");
  if (canvas === null) return null;
  return clientToTile(e.clientX, e.clientY, canvas.getBoundingClientRect(), model);
}

export function BattleCanvas({ model, highlights, scale, onTileClick, onTileHover, onCancel, rendererRef, children }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const latest = useRef({ model, highlights, scale });
  latest.current = { model, highlights, scale };

  useEffect(() => {
    const host = hostRef.current;
    if (host === null) return undefined;
    const renderer = new BattleRenderer();
    rendererRef.current = renderer;
    void renderer.init(host).then(async () => {
      await waitForFonts();
      if (rendererRef.current !== renderer) return;
      if (rendererRef.current !== renderer) return;
      renderer.setScale(latest.current.scale);
      renderer.draw(latest.current.model);
      renderer.setHighlights(latest.current.highlights);
    });
    return () => {
      if (rendererRef.current === renderer) rendererRef.current = null;
      renderer.destroy();
      host.replaceChildren();
    };
  }, [rendererRef]);

  // 版面效果：逐步播放時用 flushSync 換畫面，需要同步重畫（動畫才找得到單位）。
  useLayoutEffect(() => {
    rendererRef.current?.draw(model);
    rendererRef.current?.setHighlights(latest.current.highlights);
  }, [model, rendererRef]);

  useLayoutEffect(() => {
    rendererRef.current?.setHighlights(highlights);
  }, [highlights, rendererRef]);

  // 字型載入完成後重畫（Pixi 文字已用備援字型畫過）
  const epoch = useSyncExternalStore(subscribeFonts, fontEpoch);
  useLayoutEffect(() => {
    rendererRef.current?.draw(latest.current.model);
    rendererRef.current?.setHighlights(latest.current.highlights);
  }, [epoch, rendererRef]);

  useLayoutEffect(() => {
    rendererRef.current?.setScale(scale);
  }, [scale, rendererRef]);

  // 畫布還沒建立前先用同樣大小佔位，避免版面跳動。
  const size = scaledSize(model, scale);
  return (
    <div
      className="battle-canvas"
      style={{ width: size.width, height: size.height }}
      onPointerMove={(e) => onTileHover(tileFromEvent(e, model))}
      onPointerLeave={() => onTileHover(null)}
      onClick={(e) => {
        const tile = tileFromEvent(e, model);
        if (tile !== null) onTileClick(tile);
      }}
      onContextMenu={(e) => {
        e.preventDefault();
        onCancel();
      }}
    >
      <div className="battle-canvas-host" ref={hostRef} />
      {children}
    </div>
  );
}
