// 情境物件的說明卡（Phase 6C-5；21.6「情境判定、祭壇、遺跡變成地圖上的物件，走到旁邊點了就開」）：
// 名稱、說明，能用時有按鈕（調查＝開這個地點的事件、挑戰＝Boss 戰）送 `use_field_object`；
// 只能看的（霧牆、守點目標、還沒開放的通道）只有說明。能不能用由伺服器判定（`usable`、`problem_zh`）。
// 6V-1：站著人的物件（主城功能型 NPC，`figure`）名稱前加頭像，大小同對話框（48px）。
import type { WorldAction, WorldView } from "../api/types";
import { PORTRAIT_SIZES } from "../render/portrait";
import { nearTarget } from "./fieldModel";
import { Portrait } from "./StoryIcons";
import "./fieldThings.css";

interface Props {
  view: WorldView;
  object: string;
  busy: boolean;
  onAct(action: WorldAction): void;
  onClose(): void;
}

/** 卡上按鈕的字（`note` 沒有按鈕）。 */
export function objectButtonText(use: string): string | null {
  if (use === "encounter") return "挑戰";
  if (use === "event") return "調查";
  return null;
}

export function FieldObjectCard({ view, object, busy, onAct, onClose }: Props) {
  const field = view.field;
  const o = (field?.situation_objects ?? []).find((x) => x.id === object);
  if (field == null || o === undefined) return null;
  const label = objectButtonText(o.use);
  const near = nearTarget(field.me, o);
  const blocked = view.encounter != null || view.battle_id != null || view.event != null;
  return (
    <div className="panel field-object-card" data-testid="world-hud-object" data-object={o.id} data-use={o.use}>
      {o.figure != null ? (
        <div className="section-title field-object-who" data-testid="world-object-who">
          <Portrait portrait={o.figure.portrait} region={field.region} size={PORTRAIT_SIZES.line} label={o.name_zh} />
          <span>{o.name_zh}</span>
        </div>
      ) : (
        <div className="section-title">{o.name_zh}</div>
      )}
      {o.note_zh !== "" && <p className="small">{o.note_zh}</p>}
      {o.problem_zh != null && <div className="muted small" data-testid="world-object-problem">{o.problem_zh}</div>}
      {label !== null && (
        <button
          type="button"
          disabled={busy || blocked || !o.usable || !near}
          onClick={() => {
            onAct({ kind: "use_field_object", object: o.id });
            onClose();
          }}
          data-testid="world-object-use"
        >
          {label}
        </button>
      )}
      {label !== null && !near && <div className="muted small">走到旁邊才能{label}</div>}
    </div>
  );
}
