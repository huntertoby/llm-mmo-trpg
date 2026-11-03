// 戰鬥版 HUD 的半透明避讓（Phase 6A-4g）：每次重畫、捲動、縮放、視窗大小改變後量一次 HUD 各塊與畫布的位置，
// 算出底下有單位或可點格子的塊（`battle/hudFade.ts`），以 `data-hud-faded` 屬性交給 CSS（battle-hud.css）變半透明。
import { useEffect, useLayoutEffect, useState, type RefObject } from "react";
import type { DrawModel } from "../../battle/drawModel";
import { FADE_BLOCKS, FADE_SELECTORS, fadeCells, fadedHudBlocks, tileClientRect, type FadeBlockId } from "../../battle/hudFade";
import type { ClientRect } from "../../battle/stageLayout";
import type { Highlights } from "../../render/BattleRenderer";

const rectOf = (el: Element | null): ClientRect | null => {
  if (el === null) return null;
  const r = el.getBoundingClientRect();
  return { left: r.left, top: r.top, width: r.width, height: r.height };
};

/** 回傳要放在 `data-hud-faded` 的字串（空白分隔的塊名稱；沒有為空字串）。 */
export function useHudFade(rootRef: RefObject<HTMLElement>, scrollRef: RefObject<HTMLElement>, model: DrawModel, highlights: Highlights): string {
  const [faded, setFaded] = useState("");
  const [tick, setTick] = useState(0);
  // 捲動、視窗大小改變時重量（一幀一次）
  useEffect(() => {
    const scroller = scrollRef.current;
    let frame = 0;
    const bump = () => {
      if (frame !== 0) return;
      frame = window.requestAnimationFrame(() => {
        frame = 0;
        setTick((t) => t + 1);
      });
    };
    scroller?.addEventListener("scroll", bump, { passive: true });
    window.addEventListener("resize", bump);
    const ro = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(bump);
    if (ro !== null && scroller !== null) ro.observe(scroller);
    return () => {
      scroller?.removeEventListener("scroll", bump);
      window.removeEventListener("resize", bump);
      ro?.disconnect();
      if (frame !== 0) window.cancelAnimationFrame(frame);
    };
  }, [scrollRef]);
  useLayoutEffect(() => {
    const root = rootRef.current;
    const canvas = scrollRef.current?.querySelector("canvas") ?? null;
    if (root === null || canvas === null) {
      setFaded("");
      return;
    }
    const canvasRect = rectOf(canvas) as ClientRect;
    const cells = fadeCells(model, highlights).map((p) => tileClientRect(p, model, canvasRect));
    const blocks: Partial<Record<FadeBlockId, ClientRect | null>> = {};
    for (const id of FADE_BLOCKS) blocks[id] = rectOf(root.querySelector(FADE_SELECTORS[id]));
    const next = fadedHudBlocks(blocks, cells).join(" ");
    setFaded((cur) => (cur === next ? cur : next));
  });
  void tick;
  return faded;
}
