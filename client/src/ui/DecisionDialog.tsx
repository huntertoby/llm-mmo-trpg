// 反應詢問視窗：觸發者（格子上以洋紅色雙框標示）、反應名稱與說明、代價、接受／拒絕。
// 不遮住戰場（戰場上要看得到觸發者；視窗靠上，可切到下方）。「之後都自動」只在接受時有意義：詢問期間伺服器不收
// 動作，所以由呼叫端記在本地，輪到主角時再送 `set_reaction_mode`。
import { useState } from "react";
import { DialogFrame } from "./DialogFrame";
import type { Pending, ReactionRuleView } from "../api/types";
import { glossaryEntry, reactionName } from "../battle/glossary";
import { costText } from "../battle/reactions";
import type { UnitNames } from "../battle/units";

interface Props {
  pending: Pending;
  rule: ReactionRuleView | null;
  names: UnitNames;
  /** 引發詢問的事件的中文描述（找不到時 `null`）。 */
  eventText: string | null;
  enabled: boolean;
  onDecide(accept: boolean, always: boolean): void;
  /** 一開始放在畫面下方（觸發者在戰場上半部時）。 */
  startLow?: boolean;
}

export function DecisionDialog({ pending, rule, names, eventText, enabled, onDecide, startLow = false }: Props) {
  const [always, setAlways] = useState(false);
  const reaction = rule?.name_zh ?? reactionName(pending.reaction);
  const description = rule?.description_zh ?? glossaryEntry("reactions", pending.reaction)?.description_zh ?? null;
  const trigger = pending.trigger_unit_id == null ? null : names.label(pending.trigger_unit_id);
  return (
    <DialogFrame label="反應詢問" title={`反應詢問：${reaction}`} startLow={startLow}>
      {eventText !== null && <p className="small muted">{eventText}</p>}
      <p>
        {names.label(pending.unit_id)} 可以使用「{reaction}」
        {trigger !== null && (
          <>
            （觸發者：<b>{trigger}</b>，已在戰場上以洋紅色框標示）
          </>
        )}
        。
      </p>
      {description !== null && <p className="small muted">{description}</p>}
      <p>
        代價：<b>{costText(pending)}</b>
      </p>
      <label className="small always-auto">
        <input type="checkbox" checked={always} onChange={(e) => setAlways(e.target.checked)} />
        接受，且之後都自動（輪到你時改為「自動」）
      </label>
      <div className="modal-buttons">
        <button type="button" className="primary" disabled={!enabled} onClick={() => onDecide(true, always)}>
          接受
        </button>
        <button type="button" disabled={!enabled} onClick={() => onDecide(false, false)}>
          拒絕
        </button>
      </div>
    </DialogFrame>
  );
}
