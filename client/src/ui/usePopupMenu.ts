// 點擊式選單／面板的共用行為（Phase 3E-2d；規則見 docs/開發PM交接.md 6.5.1）：
// Esc 關閉（並攔下事件，BattleScreen 的 Esc 不會再取消瞄準）、點外面關閉、同時只開一張。
// 彈出位置與最大高度捲動由 CSS（`.popup-menu`）負責。
import { useCallback, useEffect, useRef, useState, type RefObject } from "react";

/** 目前開著的點擊式選單的關閉函式；新的打開時，舊的先關。 */
const openMenus = new Set<() => void>();

interface PopupMenu {
  open: boolean;
  setOpen(open: boolean): void;
  toggle(): void;
  /** 掛在「觸發按鈕＋選單」的共同外層，點到它以外的地方才算外面。 */
  rootRef: RefObject<HTMLDivElement>;
}

/** `controlled`：開關狀態由外面管（頂端面板）；省略時自己管。 */
export function usePopupMenu(controlled?: { open: boolean; setOpen(open: boolean): void }): PopupMenu {
  const [inner, setInner] = useState(false);
  const open = controlled?.open ?? inner;
  const setRaw = controlled?.setOpen ?? setInner;
  const setRef = useRef(setRaw);
  setRef.current = setRaw;
  const rootRef = useRef<HTMLDivElement>(null);
  const close = useCallback(() => setRef.current(false), []);

  useEffect(() => {
    if (!open) return;
    for (const other of [...openMenus]) other();
    openMenus.add(close);
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      e.stopPropagation(); // 先關選單；BattleScreen 的 window 監聽不會再處理這次 Esc
      close();
    };
    const onDown = (e: PointerEvent) => {
      const t = e.target;
      if (t instanceof Node && rootRef.current?.contains(t) === true) return;
      if (t instanceof Element && t.closest(".float-card") !== null) return;
      close();
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown);
    return () => {
      openMenus.delete(close);
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onDown);
    };
  }, [open, close]);

  return { open, setOpen: setRaw, toggle: () => setRaw(!open), rootRef };
}
