// 音訊核心（AU-1）的對外入口：全站共用的 `audio` 引擎、`play(id, opts)`、安裝自動播放解鎖、Shift＋M、背景分頁靜音。
// AU-2（合成音庫）用 `audio.registerSound` 掛音源；AU-3（戰鬥、探索）呼叫 `play`。
import { AudioEngine, type PlayResult } from "./engine";
import type { AudioContextLike, PlayOpts } from "./types";

export { AudioEngine, type PlayResult } from "./engine";
export type { PlayOpts, SoundSource, Track } from "./types";

function browserContext(): AudioContextLike | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { AudioContext?: new () => AudioContextLike; webkitAudioContext?: new () => AudioContextLike };
  const Ctor = w.AudioContext ?? w.webkitAudioContext;
  return Ctor === undefined ? null : new Ctor();
}

/** 全站共用的音訊引擎（解鎖前不建立 AudioContext）。 */
export const audio = new AudioEngine({ createContext: browserContext });

/** 播放一個音效；id 對不到音源、還沒解鎖、超過上限時不出聲。 */
export function play(id: string, opts?: PlayOpts): PlayResult {
  return audio.play(id, opts);
}

/** 鍵盤事件是不是「全部靜音」（Shift＋M；在輸入框打字、有其他修飾鍵時不算）。 */
export function isMuteShortcut(e: { code?: string; key: string; shiftKey: boolean; ctrlKey?: boolean; altKey?: boolean; metaKey?: boolean }, typing: boolean): boolean {
  if (typing || !e.shiftKey || e.ctrlKey === true || e.altKey === true || e.metaKey === true) return false;
  return e.code === "KeyM" || e.key === "M" || e.key === "m";
}

/** 不算打字的 input（滑桿、勾選框、按鈕）：焦點在上面時 Shift＋M 照常有效。 */
const NON_TEXT_INPUTS: readonly string[] = ["range", "checkbox", "radio", "button", "submit", "reset", "color", "file"];

function typingInto(target: EventTarget | null): boolean {
  if (typeof HTMLElement === "undefined" || !(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  if (tag === "INPUT") return !NON_TEXT_INPUTS.includes((target as HTMLInputElement).type);
  return tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
}

interface ListenTarget {
  addEventListener(type: string, fn: (e: Event) => void, opts?: boolean | AddEventListenerOptions): void;
  removeEventListener(type: string, fn: (e: Event) => void, opts?: boolean | EventListenerOptions): void;
}

/** 掛上全站的監聽：第一次點擊或按鍵解鎖、Shift＋M、`visibilitychange`。回傳移除函式。 */
export function installAudio(win: ListenTarget, doc: ListenTarget & { visibilityState: string }, engine: AudioEngine = audio): () => void {
  const unlockEvents = ["pointerdown", "keydown", "touchend"] as const;
  // 有些按鍵（例如單按 Shift）不算使用者手勢，resume 會失敗；等 AudioContext 真的在跑才拿掉監聽。
  const unlock = (): void => {
    if (!engine.unlock() || !engine.running) return;
    for (const t of unlockEvents) win.removeEventListener(t, unlock, true);
  };
  for (const t of unlockEvents) win.addEventListener(t, unlock, true);
  const onKey = (e: Event): void => {
    const k = e as KeyboardEvent;
    if (k.repeat || !isMuteShortcut(k, typingInto(k.target))) return;
    k.preventDefault();
    engine.toggleMute();
  };
  win.addEventListener("keydown", onKey);
  const onVis = (): void => engine.setHidden(doc.visibilityState === "hidden");
  doc.addEventListener("visibilitychange", onVis);
  onVis();
  return () => {
    for (const t of unlockEvents) win.removeEventListener(t, unlock, true);
    win.removeEventListener("keydown", onKey);
    doc.removeEventListener("visibilitychange", onVis);
  };
}
