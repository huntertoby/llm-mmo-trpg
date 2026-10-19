// 操作面板：其他動作清單、結束回合、略過動畫開關（技能 UI 在 3-4 取代）。
import type { Action } from "../api/types";
import type { ClassifiedActions } from "../battle/actions";

interface Props {
  classified: ClassifiedActions;
  enabled: boolean;
  skipAnimation: boolean;
  onSkipAnimation(value: boolean): void;
  onAction(action: Action): void;
}

export function ActionPanel({
  classified,
  enabled,
  skipAnimation,
  onSkipAnimation,
  onAction,
}: Props) {
  const { moves, attacks, others, endTurn } = classified;
  return (
    <div className="panel action-panel">
      <div className="action-hint">
        {enabled
          ? `點選藍色格子移動（${moves.size} 格），點選紅框敵人攻擊（${attacks.size} 個）。`
          : "等待中……"}
      </div>
      <div className="section-title">其他動作</div>
      <ul className="action-list">
        {others.length === 0 && <li className="muted">（無）</li>}
        {others.map((o, i) => (
          <li key={`${i}:${o.label}`}>
            <button type="button" disabled={!enabled} onClick={() => onAction(o.action)}>
              {o.label}
            </button>
          </li>
        ))}
      </ul>
      <div className="action-footer">
        <button
          type="button"
          className="primary"
          disabled={!enabled || endTurn === null}
          onClick={() => {
            if (endTurn !== null) onAction(endTurn);
          }}
        >
          結束回合
        </button>
        <label className="skip-toggle">
          <input
            type="checkbox"
            checked={skipAnimation}
            onChange={(e) => onSkipAnimation(e.target.checked)}
          />
          略過動畫
        </label>
      </div>
    </div>
  );
}
