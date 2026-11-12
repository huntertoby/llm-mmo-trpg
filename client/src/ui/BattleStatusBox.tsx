// 戰鬥版 HUD 右上的狀態框（Phase 6A-4e，版面 A 戰鬥版）：地名、回合數字、天氣圖示、勝利條件圖示。
// 字只留地名與數字；天氣與勝利條件的說明滑過看（`Hint`）。地名：大世界的戰鬥寫大世界的地點名（`battle/placeName.ts`）。
import type { BattleView } from "../api/types";
import { OBJECTIVE_ICONS, objectiveHud, objectiveLine, roundsLeft } from "../battle/objective";
import { battlePlaceName } from "../battle/placeName";
import { PRACTICE_SANDBOX_TAG_ZH } from "../battle/skillTray";
import { weatherMark } from "../world/hud";
import { HudIcon } from "../world/HudIcons";
import { Hint } from "./Hint";

interface Props {
  view: BattleView;
  /** 大世界帶進來的地點名；省略或 `null` 用戰場地圖名。 */
  placeName?: string | null;
}

/** 回合的說明：「第 2 輪」或「第 2 / 8 輪」。 */
export function roundHint(view: Pick<BattleView, "round" | "max_rounds">): string {
  return view.max_rounds === null ? `第 ${view.round} 輪` : `第 ${view.round} / ${view.max_rounds} 輪`;
}

export function BattleStatusBox({ view, placeName }: Props) {
  const place = battlePlaceName(view, placeName);
  const weather = view.weather_name_zh === null ? null : weatherMark(view.weather_name_zh);
  const left = roundsLeft(view.objective, view.round);
  const goal = `${objectiveHud(view.objective, view.round)}　${objectiveLine(view.objective)}`;
  return (
    <div className="bhud-status" aria-label="戰況">
      <Hint text={`地點：${place}`}>
        <span className="bhud-place" tabIndex={0} data-testid="battle-place">
          {place}
        </span>
      </Hint>
      <span className="bhud-status-row">
        <Hint text={roundHint(view)}>
          <span className="bhud-round" tabIndex={0} data-testid="battle-round">
            第 <b>{view.round}</b> 輪
          </span>
        </Hint>
        {weather !== null && (
          <Hint text={`天氣：${view.weather_name_zh ?? ""}`}>
            <span className="bhud-weather" tabIndex={0} data-testid="battle-weather" aria-label={`天氣：${view.weather_name_zh ?? ""}`}>
              <HudIcon name={weather.icon} size={18} />
            </span>
          </Hint>
        )}
        {view.practice ? (
          // PR-2b（#147 測試模式）：勝利條件換成「沙盒・不算勝負」小牌；輪數照舊（沒有上限）
          <span className="practice-sandbox-tag" data-testid="battle-sandbox-tag">
            {PRACTICE_SANDBOX_TAG_ZH}
          </span>
        ) : (
          <Hint text={goal}>
            <span className={`bhud-goal ${view.objective.kind}`} tabIndex={0} data-testid="battle-objective" aria-label={goal}>
              <span className="bhud-goal-icon" aria-hidden="true">
                {OBJECTIVE_ICONS[view.objective.kind]}
              </span>
              {left !== null && <span className="bhud-goal-left">{left}</span>}
            </span>
          </Hint>
        )}
      </span>
    </div>
  );
}
