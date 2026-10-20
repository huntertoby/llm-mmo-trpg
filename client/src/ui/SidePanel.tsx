// 右側窄欄（Phase 3-8）：環境預告（上）與戰鬥紀錄（下）；可收合成一條邊，狀態由呼叫端記在 localStorage。
import type { ReactNode } from "react";

interface Props {
  collapsed: boolean;
  onToggle(): void;
  telegraph: ReactNode;
  log: ReactNode;
}

export function SidePanel({ collapsed, onToggle, telegraph, log }: Props) {
  if (collapsed) {
    return (
      <aside className="battle-side collapsed" aria-label="戰鬥紀錄與環境預告（已收合）">
        <button type="button" className="side-toggle" title="展開戰鬥紀錄與環境預告" onClick={onToggle}>
          ◀<span className="side-toggle-label">紀錄・預告</span>
        </button>
      </aside>
    );
  }
  return (
    <aside className="battle-side" aria-label="戰鬥紀錄與環境預告">
      <button type="button" className="side-toggle side-toggle-open" title="收合" onClick={onToggle}>
        收合 ▶
      </button>
      <div className="side-telegraph">{telegraph}</div>
      {log}
    </aside>
  );
}
