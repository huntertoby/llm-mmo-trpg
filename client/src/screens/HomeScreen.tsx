// 正式入口（6F-1，前 10 分鐘檢查 U10）：只有「開始」→ 建立角色（大世界）。單場戰鬥、roguelite 一輪、地圖清單、
// 技能工坊收進開發模式（網址 `?dev=1` 時 App 改顯示原本的 StartScreen）。
// UI-E1：照 docs/art/home-v2.png 換皮：浮島天空背景、中上方標題牌（遊戲名稱讀 content/ui/game.yaml）、選單在右側不擋島。
import { ErrorBanner } from "../ui/ErrorBanner";
import { EntryPanel, EntryPlaque, EntryShell } from "../ui/EntryShell";
import { GAME_INFO } from "../ui/gameInfo";

interface Props {
  onStart(): void;
  /** 首頁頂端的提示（例如上次的一輪無法讀回的原因）。 */
  notice?: string | null;
  onCloseNotice?(): void;
}

export function HomeScreen({ onStart, notice = null, onCloseNotice }: Props) {
  return (
    <EntryShell className="entry-home start-home" testId="home">
      <EntryPlaque big heading={GAME_INFO.title_zh} sub={GAME_INFO.tagline_zh} />
      <ErrorBanner message={notice} onClose={() => onCloseNotice?.()} />
      <EntryPanel className="entry-menu start-world" testId="home-menu">
        <button type="button" className="primary entry-main" onClick={onStart} data-testid="enter-world">
          開始
        </button>
        <div className="entry-menu-note">建立角色、在主城樞島醒來，到雲嶺接任務、在格子戰場上打出你的 build。</div>
      </EntryPanel>
    </EntryShell>
  );
}
