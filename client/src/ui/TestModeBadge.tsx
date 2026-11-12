// 「測試模式」徽章（Phase 3-39）：標記不計入統計的一輪（進度畫面、結束摘要、存檔列表共用）。
// PR-2d：靶場的提示條（`PracticeBar`）傳自己的說明卡句子（`hint`）；其他地方不傳，原字不動。
import { Hint } from "./Hint";

/** 一輪的測試模式（3-39）徽章的說明卡原字。 */
export const TEST_MODE_BADGE_HINT_ZH = "測試模式：戰後回滿，不計入任何統計";

export function TestModeBadge({ hint = TEST_MODE_BADGE_HINT_ZH }: { hint?: string }) {
  return (
    <Hint text={hint}>
      <span className="test-mode-badge" data-testid="test-mode-badge">
        測試模式
      </span>
    </Hint>
  );
}
