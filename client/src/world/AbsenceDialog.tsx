// 「你不在的時候」摘要（Phase 5F-1b；09 9.6.10 的 5F-1 代決）：玩家下次上線時跳一則，列出世界事件成敗、
// 懸賞被誰搶下、新開放的區域；按「知道了」送 `news_seen`，看過就不再跳。沿用詢問視窗外框（DialogFrame，
// 浮動卡規則 6.5.1 的共用元件，不另做彈出層）。
import type { AbsenceView } from "../api/types";
import { DialogFrame } from "../ui/DialogFrame";
import { absenceKindLabel } from "./absence";

interface Props {
  view: AbsenceView;
  busy: boolean;
  onClose(): void;
}

export function AbsenceDialog({ view, busy, onClose }: Props) {
  return (
    <DialogFrame label="你不在的時候" title="你不在的時候">
      <ul className="world-absence" data-testid="world-absence">
        {view.items.map((item, i) => (
          <li key={`${item.at}-${i}`}>
            <span className="muted small">【{absenceKindLabel(item.kind)}】</span>
            {item.text_zh}
          </li>
        ))}
      </ul>
      <div className="modal-buttons">
        <button type="button" className="primary" disabled={busy} onClick={onClose} data-testid="world-absence-close">
          知道了
        </button>
      </div>
    </DialogFrame>
  );
}
