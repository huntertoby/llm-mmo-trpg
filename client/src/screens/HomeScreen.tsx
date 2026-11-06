// 正式入口（6F-1，前 10 分鐘檢查 U10）。單場戰鬥、地圖清單、技能工坊收進開發模式（網址 `?dev=1` 時 App 改顯示原本的 StartScreen）。
// UI-E1：照 docs/art/shots/misc/home-v2.png 換皮：浮島天空背景、中上方標題牌（遊戲名稱讀 content/ui/game.yaml）、選單在右側不擋島。
// UI-E1b（UI-E1 待決 1 定案）：選單照樣張改成四顆鈕——繼續（最近的角色，寫「霜月 Lv 5・灰燼荒原・餘燼集」；沒有角色時停用）、
// 建立新角色、roguelite 一輪、設定（在同一個框裡展開聲音與減少動態，「返回」收回）。
// 「繼續」讀現有的角色列表（`GET /world/characters`，背景請求，收到 401 不導到登入畫面）；不新增 API。
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { WorldCharacterSummary } from "../api/types";
import { AudioSettingsPanel } from "../audio/AudioSettingsPanel";
import { ErrorBanner } from "../ui/ErrorBanner";
import { EntryPanel, EntryPlaque, EntryShell } from "../ui/EntryShell";
import { GAME_INFO } from "../ui/gameInfo";
import { MotionSettingsSection } from "../ui/MotionSettingsSection";
import { readWorldChar } from "../world/mapView";

interface Props {
  /** 繼續：進大世界、直接進這個角色。 */
  onContinue(characterId: string): void;
  /** 建立新角色：進大世界的角色畫面。 */
  onCreate(): void;
  /** roguelite 一輪：開新一輪的畫面。 */
  onRun(): void;
  /** 首頁頂端的提示（例如上次的一輪無法讀回的原因）。 */
  notice?: string | null;
  onCloseNotice?(): void;
  /** 測試用：直接給角色列表（省略＝向伺服器讀）。 */
  initialChars?: readonly WorldCharacterSummary[] | null;
}

/** 首頁選單的四顆鈕（照 home-v2.png 的順序）。 */
export const HOME_BUTTONS = ["繼續", "建立新角色", "roguelite 一輪", "設定"] as const;

/** 「繼續」接的角色：上次用的（瀏覽器記住的）還在列表裡就用它，否則列表第一個；沒有角色時 `null`。 */
export function continueTarget(chars: readonly WorldCharacterSummary[], remembered: string | null): WorldCharacterSummary | null {
  return chars.find((c) => c.character_id === remembered) ?? chars[0] ?? null;
}

/** 「繼續」下面的一行：「霜月 Lv 5・灰燼荒原・餘燼集」。 */
export function continueLine(c: WorldCharacterSummary): string {
  return `${c.name} Lv ${c.level}・${c.region_name_zh}・${c.location_name_zh}`;
}

/** 背景讀角色列表：先看登入狀態（沒登入、也不是開發模式時不讀，避免 401）；讀不到當作沒有角色。 */
function loadChars(): Promise<WorldCharacterSummary[]> {
  return api.authStatus().then(
    (s) => (s.account != null || s.dev_mode ? api.worldCharactersQuiet() : []),
    () => [],
  );
}

export function HomeScreen({ onContinue, onCreate, onRun, notice = null, onCloseNotice, initialChars }: Props) {
  const [chars, setChars] = useState<readonly WorldCharacterSummary[] | null>(initialChars ?? null);
  const [settings, setSettings] = useState(false);

  useEffect(() => {
    if (initialChars !== undefined) return undefined;
    let cancelled = false;
    loadChars().then(
      (list) => !cancelled && setChars(list),
      () => !cancelled && setChars([]),
    );
    return () => {
      cancelled = true;
    };
  }, [initialChars]);

  const target = chars === null ? null : continueTarget(chars, readWorldChar());
  return (
    <EntryShell className="entry-home start-home" testId="home">
      <EntryPlaque big heading={GAME_INFO.title_zh} sub={GAME_INFO.tagline_zh} />
      <ErrorBanner message={notice} onClose={() => onCloseNotice?.()} />
      <EntryPanel className="entry-menu start-world" testId="home-menu">
        {settings ? (
          <div className="entry-menu-settings" data-testid="home-settings">
            <div className="entry-menu-settings-head">設定</div>
            <AudioSettingsPanel />
            <MotionSettingsSection />
            <button type="button" className="entry-btn entry-menu-btn" data-sfx="ui_cancel" onClick={() => setSettings(false)} data-testid="home-settings-back">
              返回
            </button>
          </div>
        ) : (
          <>
            <button
              type="button"
              className="primary entry-main entry-continue"
              disabled={target === null}
              onClick={() => target !== null && onContinue(target.character_id)}
              data-testid="home-continue"
            >
              <span>繼續</span>
              <span className="entry-continue-sub">{chars === null ? "讀取中……" : target === null ? "還沒有角色" : continueLine(target)}</span>
            </button>
            <button type="button" className="entry-btn entry-menu-btn" onClick={onCreate} data-testid="enter-world">
              建立新角色
            </button>
            <button type="button" className="entry-btn entry-menu-btn" onClick={onRun} data-testid="home-run">
              roguelite 一輪
            </button>
            <button type="button" className="entry-btn entry-menu-btn" onClick={() => setSettings(true)} aria-expanded={false} data-testid="home-settings-open">
              設定
            </button>
            <div className="entry-menu-note">建立角色、在主城樞島醒來，到雲嶺接任務、在格子戰場上打出你的 build。</div>
          </>
        )}
      </EntryPanel>
    </EntryShell>
  );
}
