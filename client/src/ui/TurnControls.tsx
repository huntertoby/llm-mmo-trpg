// 右下角（Phase 3-8、3-21b）：常駐 5 鈕——移動、普攻、跑步、守護、結束回合；旁邊一個「更多動作」選單，
// 只列出當下合法的動作（推擊、絆倒、互動、換位、瞄準、攀跳），選了之後在地圖上點目標。
// 播放速度控制在下面。戰鬥結束時換成結束面板。
import { useState, type ReactNode } from "react";
import type { Action } from "../api/types";
import type { LabeledAction } from "../battle/actions";
import type { ActionMode } from "../battle/targeting";

interface Props {
  enabled: boolean;
  endTurn: Action | null;
  /** 普攻的模式（沒有可攻擊的目標時 `null`，按鈕灰掉）。 */
  attack: ActionMode | null;
  /** 守護的模式（沒有合法的守護時 `null`）。 */
  defend: ActionMode | null;
  /** 跑步的模式（不合法時 `null`，按鈕灰掉並顯示 `runReason`）。 */
  run: ActionMode | null;
  runReason: string | null;
  /** 可移動的格子數（顯示在「移動」鈕的說明）。 */
  moveCount: number;
  /** 沒有選取任何模式 ＝ 移動模式（點亮的格子即移動）。 */
  moving: boolean;
  /** 「移動」：回到移動模式（取消目前選取的動作）。 */
  onMove(): void;
  /** 滑過跑步按鈕時預覽（顯示跑步後的移動範圍）；移開時傳 `null`。 */
  onPreviewAction(action: Action | null): void;
  selectedKey: string | null;
  /** 「更多動作」選單的項目（只含當下合法的動作）。 */
  more: readonly ActionMode[];
  /** 選單裡技能與基本動作都沒涵蓋的動作（正常為空）。 */
  extra: readonly LabeledAction[];
  onPickMode(mode: ActionMode): void;
  onAction(action: Action): void;
  /** 播放速度控制。 */
  speed: ReactNode;
}

export function TurnControls({
  enabled,
  endTurn,
  attack,
  defend,
  run,
  runReason,
  moveCount,
  moving,
  onMove,
  onPreviewAction,
  selectedKey,
  more,
  extra,
  onPickMode,
  onAction,
  speed,
}: Props) {
  const [open, setOpen] = useState(false);
  const count = more.length + extra.length;
  return (
    <div className="turn-controls" aria-label="回合操作">
      <div className="resident-actions" aria-label="常駐動作">
        <button
          type="button"
          className={`resident-button${moving ? " selected" : ""}`}
          disabled={!enabled}
          title={`移動：點亮起的格子（目前可到 ${moveCount} 格）`}
          onClick={onMove}
        >
          移動
        </button>
        <button
          type="button"
          className={`resident-button${selectedKey === attack?.key && attack !== null ? " selected" : ""}`}
          disabled={!enabled || attack === null}
          title={attack === null ? "普攻：目前沒有可攻擊的目標" : "普攻：花 1 AP，點選紅框的目標"}
          onClick={() => attack !== null && onPickMode(attack)}
        >
          普攻
        </button>
        <button
          type="button"
          className={`resident-button run-button${selectedKey === run?.key && run !== null ? " selected" : ""}`}
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
        <button
          type="button"
          className={`resident-button${selectedKey === defend?.key && defend !== null ? " selected" : ""}`}
          disabled={!enabled || defend === null}
          title="守護：花 1 AP，防禦 +25% 到下回合開始；相鄰有隊友時可點他，改由你替他承受單體攻擊"
          onClick={() => defend !== null && onPickMode(defend)}
        >
          守護
        </button>
        <button
          type="button"
          className="resident-button primary end-turn-button"
          disabled={!enabled || endTurn === null}
          onClick={() => endTurn !== null && onAction(endTurn)}
        >
          結束回合
        </button>
      </div>
      <div className="more-actions">
        <button
          type="button"
          aria-expanded={open}
          disabled={count === 0}
          title={count === 0 ? "目前沒有其他可用的動作" : "推擊、絆倒、互動、換位、瞄準、攀跳（只列出現在合法的）"}
          onClick={() => setOpen((o) => !o)}
        >
          更多動作（{count}）
        </button>
        {open && count > 0 && (
          <ul className="action-list more-list" aria-label="更多動作">
            {more.map((m) => (
              <li key={m.key}>
                <button
                  type="button"
                  className={selectedKey === m.key ? "selected" : ""}
                  disabled={!enabled}
                  onClick={() => {
                    setOpen(false);
                    onPickMode(m);
                  }}
                >
                  {m.label}
                </button>
              </li>
            ))}
            {extra.map((o, i) => (
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
      {enabled && run === null && runReason !== null && <p className="run-reason muted">跑步：{runReason}</p>}
      {speed}
    </div>
  );
}
