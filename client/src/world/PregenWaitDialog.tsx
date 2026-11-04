// 6L-2：LLM 的版本還沒好時的等待提示（共用彈窗 `DialogFrame`）。取消＝不送那個動作；RT-3 的羽毛筆
// 動畫之後再接。
import { DialogFrame } from "../ui/DialogFrame";

interface Props {
  text: string;
  onCancel: () => void;
}

export function PregenWaitDialog({ text, onCancel }: Props) {
  return (
    <DialogFrame label="等待說書人" title="請稍候">
      <p data-testid="world-pregen-wait" role="status">
        {text}
      </p>
      <p className="muted small">最多等 10 秒；來不及就改用一般的版本。</p>
      <div className="modal-buttons">
        <button type="button" onClick={onCancel} data-testid="world-pregen-cancel">
          取消
        </button>
      </div>
    </DialogFrame>
  );
}
