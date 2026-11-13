// 選取時量出戰鬥紀錄可用的高度（Phase 6A-4c）：選取面板（`.mode-panel`）底下到紀錄底部；戰場或面板大小改變時重量。
// 6A-4e：紀錄放在底部列上方（不一定貼著戰場底），所以用紀錄自己的底邊算，不用戰場高度。
import { useLayoutEffect, useState, type RefObject } from "react";
import { heroLogCap, LOG_DOCK_BOTTOM, logRoom } from "../../battle/logRoom";

export function useLogRoom(boardRef: RefObject<HTMLElement | null>, selecting: boolean, panelKey: string): number | null {
  const [room, setRoom] = useState<number | null>(null);
  useLayoutEffect(() => {
    const board = boardRef.current;
    if (!selecting || board === null) {
      setRoom(null);
      return undefined;
    }
    const panel = board.querySelector<HTMLElement>(".mode-panel");
    const dock = board.querySelector<HTMLElement>(".log-dock");
    const measure = () => {
      if (panel === null || !panel.isConnected) {
        setRoom(null);
        return;
      }
      const b = board.getBoundingClientRect();
      const p = panel.getBoundingClientRect();
      // 紀錄底邊（相對戰場頂端）＋ `LOG_DOCK_BOTTOM` ＝ `logRoom` 心目中的「戰場高度」
      const dockBottom = dock === null || !dock.isConnected ? b.height - LOG_DOCK_BOTTOM : dock.getBoundingClientRect().bottom - b.top;
      setRoom(logRoom(dockBottom + LOG_DOCK_BOTTOM, p.bottom - b.top));
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

/** UI-1：量主角卡（`.bhud-hero`）下緣到紀錄底邊的可用高度；戰場、主角卡（打開詳細）或紀錄大小改變時重量。
 *  `bottomKey` 是底部列高度（紀錄底邊跟著它移，但戰場大小不變，所以另外當成重量的時機）。 */
export function useHeroLogCap(boardRef: RefObject<HTMLElement | null>, bottomKey: number | null): number | null {
  const [cap, setCap] = useState<number | null>(null);
  useLayoutEffect(() => {
    const board = boardRef.current;
    if (board === null) return undefined;
    const hero = board.querySelector<HTMLElement>(".bhud-hero");
    const dock = board.querySelector<HTMLElement>(".log-dock");
    const measure = () => {
      if (hero === null || dock === null || !hero.isConnected || !dock.isConnected) {
        setCap(null);
        return;
      }
      const b = board.getBoundingClientRect();
      setCap(heroLogCap(dock.getBoundingClientRect().bottom - b.top, hero.getBoundingClientRect().bottom - b.top));
    };
    measure();
    if (typeof ResizeObserver === "undefined") return undefined;
    const ro = new ResizeObserver(measure);
    ro.observe(board);
    if (hero !== null) ro.observe(hero);
    if (dock !== null) ro.observe(dock);
    return () => ro.disconnect();
  }, [boardRef, bottomKey]);
  return cap;
}
