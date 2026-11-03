// 右側窄欄（Phase 3-8）：環境預告；可收合成一條邊，狀態由呼叫端記在 localStorage。
// 6A-3 起戰鬥紀錄移到戰場左下（`BattleLogDock`：浮動提示＋展開＋釘選），窄欄只剩預告；`log` 保留給還要放紀錄的呼叫端。
import type { ReactNode } from "react";
import { Hint } from "./Hint";

interface Props {
  collapsed: boolean;
  onToggle(): void;
  telegraph: ReactNode;
  log?: ReactNode;
}

export function SidePanel({ collapsed, onToggle, telegraph, log }: Props) {
  const what = log === undefined ? "環境預告" : "戰鬥紀錄與環境預告";
  if (collapsed) {
    return (
      <aside className="battle-side collapsed" aria-label={`${what}（已收合）`}>
        <Hint text={`展開${what}`}>
          <button type="button" className="side-toggle" onClick={onToggle}>
            ◀<span className="side-toggle-label">{log === undefined ? "預告" : "紀錄・預告"}</span>
          </button>
        </Hint>
      </aside>
    );
  }
  return (
    <aside className={`battle-side${log === undefined ? " no-log" : ""}`} aria-label={what}>
      <button type="button" className="side-toggle side-toggle-open" onClick={onToggle}>
        收合 ▶
      </button>
      <div className="side-telegraph">{telegraph}</div>
      {log}
    </aside>
  );
}
