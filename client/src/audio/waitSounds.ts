// 等待聲（RT-3；docs/art/AU-2檢查.md 待決 3）：0.7 秒的規則保留（一般動作很快就回來，不出聲），聲音依場合不同：
// 技能生成＝羽毛筆刮紙、事件判定＝沙漏的細沙、NPC 聊天＝不出聲（要輕）、多講一點＝翻頁。
// 由等待動畫 `ui/WaitScene.tsx` 掛上（動畫在畫面上、還在等的時候才放），參數表在 `content/audio/sfx.yaml`。
import { useEffect } from "react";
import type { WaitSceneId } from "../ui/waitNarration";
import { uiSound, type UiSound } from "./uiSounds";

/** 等待超過這麼久才開始放（毫秒；AU-2 的 0.7 秒規則）。 */
export const WAIT_SOUND_DELAY_MS = 700;

/** 各場合的等待聲與重複間隔（`null`＝不出聲）。 */
export const WAIT_SOUNDS: Readonly<Record<WaitSceneId, { id: UiSound; everyMs: number } | null>> = {
  skill: { id: "ui_wait_quill", everyMs: 1600 },
  judge: { id: "ui_wait_sand", everyMs: 1400 },
  npc: null,
  retell: { id: "ui_wait_page", everyMs: 2600 },
};

/** 這個場合等了 `elapsedMs` 時，已經該放過幾聲（純函式，測試用）。 */
export function waitSoundCount(scene: WaitSceneId, elapsedMs: number, delayMs = WAIT_SOUND_DELAY_MS): number {
  const s = WAIT_SOUNDS[scene];
  if (s === null || elapsedMs < delayMs) return 0;
  return 1 + Math.floor((elapsedMs - delayMs) / s.everyMs);
}

/** 還在等（`active`）時，`delayMs` 後放第一聲，之後照間隔重複；不再等、卸載就停。 */
export function useWaitSound(scene: WaitSceneId, active: boolean, delayMs = WAIT_SOUND_DELAY_MS, play: (id: UiSound) => unknown = uiSound): void {
  useEffect(() => {
    const s = WAIT_SOUNDS[scene];
    if (!active || s === null) return undefined;
    let every: number | undefined;
    const first = window.setTimeout(
      () => {
        play(s.id);
        every = window.setInterval(() => play(s.id), s.everyMs);
      },
      Math.max(0, delayMs),
    );
    return () => {
      window.clearTimeout(first);
      if (every !== undefined) window.clearInterval(every);
    };
  }, [scene, active, delayMs, play]);
}
