// React 包裝：建立／銷毀 PixiJS 繪製器，模型或高亮改變時重畫。
import { useEffect, useLayoutEffect, useRef, type MutableRefObject } from "react";
import type { Pos } from "../api/types";
import type { DrawModel } from "../battle/drawModel";
import { BattleRenderer, type Highlights } from "../render/BattleRenderer";

interface Props {
  model: DrawModel;
  highlights: Highlights;
  onTileClick(tile: Pos): void;
  onTileHover(tile: Pos | null): void;
  /** 右鍵（取消選取）。 */
  onCancel(): void;
  /** 給戰鬥畫面播放動畫用。 */
  rendererRef: MutableRefObject<BattleRenderer | null>;
}

export function BattleCanvas({ model, highlights, onTileClick, onTileHover, onCancel, rendererRef }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const callbacks = useRef({ onTileClick, onTileHover });
  callbacks.current = { onTileClick, onTileHover };
  const latest = useRef({ model, highlights });
  latest.current = { model, highlights };

  useEffect(() => {
    const host = hostRef.current;
    if (host === null) return undefined;
    const renderer = new BattleRenderer({
      onTileClick: (t) => callbacks.current.onTileClick(t),
      onTileHover: (t) => callbacks.current.onTileHover(t),
    });
    rendererRef.current = renderer;
    void renderer.init(host).then(() => {
      if (rendererRef.current !== renderer) return;
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

  return (
    <div
      className="battle-canvas"
      ref={hostRef}
      onContextMenu={(e) => {
        e.preventDefault();
        onCancel();
      }}
    />
  );
}
