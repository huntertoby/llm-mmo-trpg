// 選取時量出戰鬥紀錄可用的高度（Phase 6A-4c）：選取面板（`.mode-panel`）底下到紀錄底部；戰場或面板大小改變時重量。
import { useLayoutEffect, useState, type RefObject } from "react";
import { logRoom } from "../../battle/logRoom";

export function useLogRoom(boardRef: RefObject<HTMLElement | null>, selecting: boolean, panelKey: string): number | null {
  const [room, setRoom] = useState<number | null>(null);
  useLayoutEffect(() => {
    const board = boardRef.current;
    if (!selecting || board === null) {
      setRoom(null);
      return undefined;
    }
    const panel = board.querySelector<HTMLElement>(".mode-panel");
    const measure = () => {
      if (panel === null || !panel.isConnected) {
        setRoom(null);
        return;
      }
      const b = board.getBoundingClientRect();
      const p = panel.getBoundingClientRect();
      setRoom(logRoom(b.height, p.bottom - b.top));
    };
    measure();
    if (typeof ResizeObserver === "undefined") return undefined;
    const ro = new ResizeObserver(measure);
    ro.observe(board);
    if (panel !== null) ro.observe(panel);
    return () => ro.disconnect();
  }, [boardRef, selecting, panelKey]);
  return selecting ? room : null;
}
