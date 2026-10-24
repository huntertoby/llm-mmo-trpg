// 換主手武器的確認（Phase 3K-2b）：新武器的縮放屬性和目前的不同時，換上前先問玩家。
// 排在卡片／按鈕列的同一個位置（不是彈出層，不涉及浮動卡），三選一與營火背包共用。
import type { GearCandidate } from "../../api/types";
import { swapQuestion } from "../../run/gearOffer";

type Props = {
  cand: Pick<GearCandidate, "item" | "weapon_swap_zh">;
  busy: boolean;
  onConfirm(): void;
  onCancel(): void;
};

export function WeaponSwapConfirm({ cand, busy, onConfirm, onCancel }: Props) {
  return (
    <div className="weapon-swap-confirm" role="alertdialog" aria-label="換武器確認" data-testid="weapon-swap-confirm">
      <p className="weapon-swap-text">{swapQuestion(cand)}</p>
      <div className="weapon-swap-buttons">
        <button type="button" className="primary" disabled={busy} onClick={onConfirm} data-testid="weapon-swap-yes">
          換上
        </button>
        <button type="button" disabled={busy} onClick={onCancel} data-testid="weapon-swap-no">
          不換
        </button>
      </div>
    </div>
  );
}
