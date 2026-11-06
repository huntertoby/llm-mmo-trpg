// 6L-2：LLM 的版本還沒好時的等待提示（共用彈窗 `DialogFrame`）。取消＝不送那個動作。
// RT-3：內容換成「技能生成」的等待動畫（羽毛筆羊皮紙，`ui/WaitScene.tsx`）；完成時卡面淡入 0.3 秒再關。
import { DialogFrame } from "../ui/DialogFrame";
import { WaitScene } from "../ui/WaitScene";
import type { WaitStatus } from "../render/waitArt";
import { WAIT_SOUND_DELAY_MS } from "../audio/waitSounds";

interface Props {
  /** 這次在等什麼（彈窗的無障礙標籤）。 */
  text: string;
  requestId: string;
  status?: WaitStatus;
  /** 彈窗出現前已經等了多久（毫秒）：等待聲照「等超過 0.7 秒」算。 */
  waitedMs?: number;
  onCancel: () => void;
}

export function PregenWaitDialog({ text, requestId, status = "wait", waitedMs = 0, onCancel }: Props) {
  return (
    <DialogFrame label={text} title="請稍候">
      <div className="pregen-wait-body" data-testid="world-pregen-wait" data-status={status}>
        <WaitScene scene="skill" requestId={requestId} status={status} soundDelayMs={WAIT_SOUND_DELAY_MS - waitedMs} testId="world-pregen-scene" />
        <p className="muted small">最多等 10 秒；來不及就改用一般的版本。</p>
      </div>
      <div className="modal-buttons">
        <button type="button" onClick={onCancel} disabled={status === "done"} data-testid="world-pregen-cancel">
          取消
        </button>
      </div>
    </DialogFrame>
  );
}
