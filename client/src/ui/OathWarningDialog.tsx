// 誓約警告視窗（Phase 5C-3b）：主角的動作會違反誓約時，送出前先問。沿用戰鬥詢問視窗外框（DialogFrame，
// 沒有遮罩、戰場仍可看；浮動卡規則 6.5.1 的共用元件，不另做彈出層）。警告文字由引擎判定（預覽的 `oath_warning`）。
import { DialogFrame } from "./DialogFrame";
import { OATH_CANCEL_LABEL, OATH_CONFIRM_LABEL } from "../battle/oathWarning";

interface Props {
  warning: string;
  enabled: boolean;
  onConfirm(): void;
  onCancel(): void;
}

export function OathWarningDialog({ warning, enabled, onConfirm, onCancel }: Props) {
  return (
    <DialogFrame label="誓約警告" title="誓約警告">
      <p data-testid="oath-warning-text">{warning}</p>
      <div className="modal-buttons">
        <button type="button" className="primary" disabled={!enabled} onClick={onCancel} data-testid="oath-warning-cancel">
          {OATH_CANCEL_LABEL}
        </button>
        <button type="button" disabled={!enabled} onClick={onConfirm} data-testid="oath-warning-confirm">
          {OATH_CONFIRM_LABEL}
        </button>
      </div>
    </DialogFrame>
  );
}
