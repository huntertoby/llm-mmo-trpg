// 帳號紀念稱號（Phase 5F-3c；19.7「碎晶的終結者」）：接在玩家名字後面，名片（影子）、主城評分榜與首殺、
// 編年史共用。戰鬥畫面不用（5F-3b 代決）。沒有稱號時什麼都不畫。
import { accountTitlesLabel } from "./titleLabel";

export function AccountTitles({ titles, testId }: { titles?: readonly string[] | null; testId?: string }) {
  const label = accountTitlesLabel(titles);
  if (label === "") return null;
  return (
    <span className="account-titles small" data-testid={testId ?? "account-titles"}>
      {label}
    </span>
  );
}
