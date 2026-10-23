// 單位資訊卡的 React 接頭（Phase 3-30 第 32.2 項）：規則在 `hoverCard.ts`；這裡負責重繪、Esc 與點外面關閉。
import { useEffect, useReducer, useRef, type MutableRefObject } from "react";
import { TileCardController } from "./hoverCard";

export interface TileCardApi {
  ctl: TileCardController;
  cardRef: MutableRefObject<HTMLDivElement | null>;
}

export function useTileCard(): TileCardApi {
  const [, rerender] = useReducer((n: number) => n + 1, 0);
  const ref = useRef<TileCardController | null>(null);
  if (ref.current === null) ref.current = new TileCardController();
  const ctl = ref.current;
  const cardRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    ctl.onChange = rerender;
    return () => {
      ctl.onChange = () => undefined;
      ctl.dispose();
    };
  }, [ctl]);

  const open = ctl.visible;
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      e.stopPropagation(); // 卡片處理了這次 Esc：BattleScreen 的 window 監聽不再取消瞄準
      ctl.dismiss();
    };
    const onDown = (e: PointerEvent) => {
      if (!ctl.pinned) return;
      const t = e.target;
      if (!(t instanceof Element)) return;
      if (cardRef.current?.contains(t) === true || t.closest(".float-card") !== null) return;
      if (t.closest(".battle-canvas") !== null) return; // 點戰場格子由 BattleScreen 的 onTileClick 處理（3-40）
      ctl.dismiss();
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onDown);
    };
  }, [open, ctl]);

  return { ctl, cardRef };
}
