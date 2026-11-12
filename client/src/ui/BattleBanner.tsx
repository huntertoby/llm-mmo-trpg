// 開場橫幅（自 `BattleScreen` 抽出，PR-2d）：實戰「戰鬥開始」＋勝利條件＋開場訊息；
// 測試模式（`BattleView.practice`，靶場）拿掉「戰鬥開始＋勝利條件」，改成定稿的一行（開場訊息照舊接在下面）。
import type { BattleView } from "../api/types";
import { objectiveLine } from "../battle/objective";
import { PRACTICE_BANNER_ZH } from "../battle/skillTray";

interface Props {
  practice: boolean;
  objective: BattleView["objective"];
  notes?: readonly string[];
}

export function BattleBanner({ practice, objective, notes }: Props) {
  const lines = (notes ?? []).map((line) => (
    <div key={line} className="battle-banner-note">
      {line}
    </div>
  ));
  if (practice) {
    return (
      <div className="battle-banner practice" data-testid="battle-banner">
        <div className="battle-banner-goal">{PRACTICE_BANNER_ZH}</div>
        {lines}
      </div>
    );
  }
  return (
    <div className="battle-banner">
      戰鬥開始
      <div className="battle-banner-goal">{objectiveLine(objective)}</div>
      {lines}
    </div>
  );
}
