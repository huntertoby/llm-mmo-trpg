// 右下角（Phase 3-8）：大的「結束回合」、「守護」（原防禦）、「其他動作（備援）」（點開在上方彈出清單）；
// 播放速度控制在旁邊。戰鬥結束時換成結束面板。
import { useState, type ReactNode } from "react";
import type { Action } from "../api/types";
import type { LabeledAction } from "../battle/actions";
import type { ActionMode } from "../battle/targeting";

interface Props {
  enabled: boolean;
  endTurn: Action | null;
  /** 守護自己的模式（沒有合法的守護時 `null`）。 */
  defend: ActionMode | null;
  /** 跑步的模式（不合法時 `null`，按鈕灰掉並顯示 `runReason`）。 */
  run: ActionMode | null;
  runReason: string | null;
  /** 滑過跑步按鈕時預覽（顯示跑步後的移動範圍）；移開時傳 `null`。 */
  onPreviewAction(action: Action | null): void;
  selectedKey: string | null;
  fallback: readonly LabeledAction[];
  onPickMode(mode: ActionMode): void;
  onAction(action: Action): void;
  /** 播放速度控制。 */
  speed: ReactNode;
}

export function TurnControls({
  enabled,
  endTurn,
  defend,
  run,
  runReason,
  onPreviewAction,
  selectedKey,
  fallback,
  onPickMode,
  onAction,
  speed,
}: Props) {
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
          title="守護：花 1 AP，防禦 +25% 到下回合開始；要守護相鄰隊友請用「其他動作」"
          onClick={() => defend !== null && onPickMode(defend)}
        >
          守護
        </button>
        <button
          type="button"
          className="run-button"
          disabled={!enabled || run === null}
          title={
            run === null && runReason !== null
              ? `不能跑步：${runReason}`
              : "跑步：花 1 AP，本回合移動點數 +3 格（每回合 1 次）"
          }
          onClick={() => run !== null && onPickMode(run)}
          onMouseEnter={() => run !== null && onPreviewAction(run.targets.self)}
          onMouseLeave={() => onPreviewAction(null)}
          onFocus={() => run !== null && onPreviewAction(run.targets.self)}
          onBlur={() => onPreviewAction(null)}
        >
          跑步
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
      {enabled && run === null && runReason !== null && <p className="run-reason muted">跑步：{runReason}</p>}
      {speed}
    </div>
  );
}
