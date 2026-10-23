// 「測試模式」徽章（Phase 3-39）：標記不計入統計的一輪（進度畫面、結束摘要、存檔列表共用）。
import { Hint } from "./Hint";

export function TestModeBadge() {
  return (
    <Hint text="測試模式：戰後回滿，不計入任何統計">
      <span className="test-mode-badge" data-testid="test-mode-badge">
        測試模式
      </span>
    </Hint>
  );
}
