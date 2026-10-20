// 右下角（Phase 3-8）：大的「結束回合」、「防禦」、「其他動作（備援）」（點開在上方彈出清單）；
// 播放速度控制在旁邊。戰鬥結束時換成結束面板。
import { useState, type ReactNode } from "react";
import type { Action } from "../api/types";
import type { LabeledAction } from "../battle/actions";
import type { ActionMode } from "../battle/targeting";

interface Props {
  enabled: boolean;
  endTurn: Action | null;
  /** 防禦的模式（沒有合法的防禦時 `null`）。 */
  defend: ActionMode | null;
  selectedKey: string | null;
  fallback: readonly LabeledAction[];
  onPickMode(mode: ActionMode): void;
  onAction(action: Action): void;
  /** 播放速度控制。 */
  speed: ReactNode;
}

export function TurnControls({ enabled, endTurn, defend, selectedKey, fallback, onPickMode, onAction, speed }: Props) {
  const [open, setOpen] = useState(false);
  return (
    <div className="turn-controls" aria-label="回合操作">
      <button
        type="button"
        className="primary end-turn-button"
        disabled={!enabled || endTurn === null}
        onClick={() => endTurn !== null && onAction(endTurn)}
      >
        結束回合
      </button>
      <div className="turn-controls-row">
        <button
          type="button"
          className={selectedKey === defend?.key ? "selected" : ""}
          disabled={!enabled || defend === null}
          onClick={() => defend !== null && onPickMode(defend)}
        >
          防禦
        </button>
        <div className="fallback">
          <button type="button" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
            其他動作（備援，{fallback.length}）
          </button>
          {open && (
            <ul className="action-list fallback-list" aria-label="其他動作">
              {fallback.length === 0 && <li className="muted">（無）</li>}
              {fallback.map((o, i) => (
                <li key={`${i}:${o.label}`}>
                  <button
                    type="button"
                    disabled={!enabled}
                    onClick={() => {
                      setOpen(false);
                      onAction(o.action);
                    }}
                  >
                    {o.label}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
      {speed}
    </div>
  );
}
