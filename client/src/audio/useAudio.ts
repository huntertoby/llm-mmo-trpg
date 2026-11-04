// 音訊的 React 掛勾（AU-1）：讀設定（跟著 `audio.setSettings` 更新）、說書人字幕或對話出現時 ducking。
import { useEffect, useSyncExternalStore } from "react";
import { audio, type AudioEngine } from "./index";
import type { AudioSettings } from "./settings";

export function useAudioSettings(engine: AudioEngine = audio): AudioSettings {
  return useSyncExternalStore(
    (fn) => engine.subscribe(fn),
    () => engine.settings,
    () => engine.settings,
  );
}

/** `active` 為真的期間壓低音樂與環境（說書人字幕、對話框）。 */
export function useDuck(active: boolean, engine: AudioEngine = audio): void {
  useEffect(() => (active ? engine.duck() : undefined), [active, engine]);
}
