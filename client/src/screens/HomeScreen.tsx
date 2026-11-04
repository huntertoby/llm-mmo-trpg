// 正式入口（6F-1，前 10 分鐘檢查 U10）：只有「開始」→ 建立角色（大世界）。單場戰鬥、roguelite 一輪、地圖清單、
// 技能工坊收進開發模式（網址 `?dev=1` 時 App 改顯示原本的 StartScreen）。
import { ErrorBanner } from "../ui/ErrorBanner";

interface Props {
  onStart(): void;
  /** 首頁頂端的提示（例如上次的一輪無法讀回的原因）。 */
  notice?: string | null;
  onCloseNotice?(): void;
}

export function HomeScreen({ onStart, notice = null, onCloseNotice }: Props) {
  return (
    <div className="start-screen start-home" data-testid="home">
      <h1>LLM-MMO-TRPG</h1>
      <ErrorBanner message={notice} onClose={() => onCloseNotice?.()} />
      <div className="panel start-world">
        <div className="muted small">建立角色、在主城樞島醒來，到雲嶺接任務、在格子戰場上打出你的 build。</div>
        <button type="button" className="primary" onClick={onStart} data-testid="enter-world">
          開始
        </button>
      </div>
    </div>
  );
}
