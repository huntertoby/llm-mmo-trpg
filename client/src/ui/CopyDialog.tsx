// 複製技能（copy_skill）的第二段選取：伺服器暫停等主角為「被複製的技能」選目標。
// 目標在戰場上點選（高亮的格子）；這裡只顯示提示與「放棄施放」（放棄不付任何代價）。
import { DialogFrame } from "./DialogFrame";
import { copyPromptText } from "../battle/targeting";

interface Props {
  /** 被複製的技能名稱。 */
  skillName: string;
  /** 目前合法的選取數。 */
  optionCount: number;
  enabled: boolean;
  onCancel(): void;
}

export function CopyDialog({ skillName, optionCount, enabled, onCancel }: Props) {
  return (
    <DialogFrame label="複製技能選目標" title="複製技能：選擇目標">
      <p>{copyPromptText(skillName, optionCount)}</p>
      <p className="small muted">複製的技能不扣法力與 AP、不進冷卻；放棄施放（按 Esc 也可以）不會付出任何代價；滑過目標會預覽整個施放。</p>
      <div className="modal-buttons">
        <button type="button" disabled={!enabled} onClick={onCancel}>
          放棄施放
        </button>
      </div>
    </DialogFrame>
  );
}
