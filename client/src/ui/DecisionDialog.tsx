// 反應詢問（簡單版；正式視窗在 3-4）。
import type { Pending } from "../api/types";
import { reactionName } from "../battle/glossary";
import type { UnitNames } from "../battle/units";

interface Props {
  pending: Pending;
  names: UnitNames;
  enabled: boolean;
  onDecide(accept: boolean): void;
}

export function costText(p: Pending): string {
  const parts: string[] = [];
  if (p.stamina_cost > 0) parts.push(`耐力 ${p.stamina_cost}`);
  if (p.mana_cost > 0) parts.push(`法力 ${p.mana_cost}`);
  if (p.hp_cost_permille > 0) parts.push(`HP ${p.hp_cost_permille / 10}%`);
  return parts.length === 0 ? "無代價" : parts.join("、");
}

export function DecisionDialog({ pending, names, enabled, onDecide }: Props) {
  const reaction = reactionName(pending.reaction);
  const trigger =
    pending.trigger_unit_id == null ? "" : `（觸發者：${names.label(pending.trigger_unit_id)}）`;
  return (
    <div className="modal-backdrop">
      <div className="modal" role="dialog" aria-label="反應詢問">
        <div className="modal-title">反應：{reaction}</div>
        <p>
          {names.label(pending.unit_id)} 可以使用「{reaction}」{trigger}。
        </p>
        <p>代價：{costText(pending)}</p>
        <div className="modal-buttons">
          <button
            type="button"
            className="primary"
            disabled={!enabled}
            onClick={() => onDecide(true)}
          >
            接受
          </button>
          <button type="button" disabled={!enabled} onClick={() => onDecide(false)}>
            拒絕
          </button>
        </div>
      </div>
    </div>
  );
}
