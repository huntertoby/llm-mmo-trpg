// 音訊設定（AU-1；docs/art/音效與音樂方案.md 第 3 節）：四軌音量（0～100）、靜音、減少刺耳音效、背景分頁靜音。
// 存 localStorage，讀寫都包 try/catch（私密視窗、封鎖儲存時照預設值跑）。
import { TRACKS, type Track } from "./types";

export interface AudioSettings {
  /** 主音量 0～100。 */
  master: number;
  sfx: number;
  music: number;
  ambient: number;
  /** 全部靜音（`Shift+M`）。 */
  muted: boolean;
  /** 各軌靜音。 */
  trackMuted: Record<Track, boolean>;
  /** 減少刺耳音效：拿掉高頻尖音與低頻轟鳴、最大音量 −6 dB（預設關）。 */
  reduceHarsh: boolean;
  /** 切到背景分頁時靜音（預設開，可關）。 */
  muteInBackground: boolean;
}

/** 使用者定的預設音量：主 70、音效 80、音樂 50、環境 60。 */
export const DEFAULT_AUDIO_SETTINGS: AudioSettings = {
  master: 70,
  sfx: 80,
  music: 50,
  ambient: 60,
  muted: false,
  trackMuted: { sfx: false, music: false, ambient: false },
  reduceHarsh: false,
  muteInBackground: true,
};

export const AUDIO_SETTINGS_KEY = "trpg.audio.v1";

/** 最小的 Storage 介面（測試用假物件）。 */
export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

function volume(v: unknown, fallback: number): number {
  if (typeof v !== "number" || !Number.isFinite(v)) return fallback;
  return Math.min(100, Math.max(0, Math.round(v)));
}

function bool(v: unknown, fallback: boolean): boolean {
  return typeof v === "boolean" ? v : fallback;
}

/** 任意 JSON → 合法設定（缺的、壞的欄位用預設值，音量夾在 0～100）。 */
export function normalizeSettings(raw: unknown): AudioSettings {
  const d = DEFAULT_AUDIO_SETTINGS;
  if (typeof raw !== "object" || raw === null) return { ...d, trackMuted: { ...d.trackMuted } };
  const r = raw as Record<string, unknown>;
  const tm = (typeof r.trackMuted === "object" && r.trackMuted !== null ? r.trackMuted : {}) as Record<string, unknown>;
  const trackMuted = { ...d.trackMuted };
  for (const t of TRACKS) trackMuted[t] = bool(tm[t], d.trackMuted[t]);
  return {
    master: volume(r.master, d.master),
    sfx: volume(r.sfx, d.sfx),
    music: volume(r.music, d.music),
    ambient: volume(r.ambient, d.ambient),
    muted: bool(r.muted, d.muted),
    trackMuted,
    reduceHarsh: bool(r.reduceHarsh, d.reduceHarsh),
    muteInBackground: bool(r.muteInBackground, d.muteInBackground),
  };
}

function defaultStorage(): StorageLike | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

export function loadAudioSettings(storage: StorageLike | null = defaultStorage()): AudioSettings {
  try {
    const text = storage?.getItem(AUDIO_SETTINGS_KEY) ?? null;
    return normalizeSettings(text === null ? null : JSON.parse(text));
  } catch {
    return normalizeSettings(null);
  }
}

export function saveAudioSettings(s: AudioSettings, storage: StorageLike | null = defaultStorage()): void {
  try {
    storage?.setItem(AUDIO_SETTINGS_KEY, JSON.stringify(s));
  } catch {
    // 存不進去就算了（下次用預設值）
  }
}
