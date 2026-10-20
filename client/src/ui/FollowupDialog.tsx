// 複合技能第二段的選取（Phase 3F-4b）：「動作 → 位移」「擊殺 → 接下一段」的第一段結算後，伺服器
// 暫停等主角為第二段選目標。目標在戰場上點選（高亮的格子），滑過會預覽；這裡只顯示提示與「放棄第二段」。
import { DialogFrame } from "./DialogFrame";
import { followupPromptText } from "../battle/followup";

interface Props {
  skillName: string;
  /** 目前合法的選取數。 */
  optionCount: number;
  enabled: boolean;
  onCancel(): void;
}

export function FollowupDialog({ skillName, optionCount, enabled, onCancel }: Props) {
  return (
    <DialogFrame label="第二段選目標" title="第二段：選擇目標">
      <p>{followupPromptText(skillName, optionCount)}</p>
      <p className="small muted">
        第一段的代價已經付了；放棄（按 Esc 也可以）只略過第二段。滑過高亮的格子或左上角選取面板的方向鈕會預覽第二段（紫色）。
      </p>
      <div className="modal-buttons">
        <button type="button" disabled={!enabled} onClick={onCancel}>
          放棄第二段
        </button>
      </div>
    </DialogFrame>
  );
}
