// 混音的純函式（AU-1）：實際音量 = 主 × 軌；靜音、背景分頁、ducking、減少刺耳音效的上限。
// AU-2（美術 PM 驗收 AU-1 的意見）：減少刺耳音效只作用在音效軌（−6 dB＋濾掉尖音與轟鳴）與環境軌（衝擊點綴不出聲，在引擎判斷）；
// 主音量與音樂不動。
import type { AudioSettings } from "./settings";
import type { Track } from "./types";

/** 減少刺耳音效：音效軌最大音量 −6 dB（約 0.501 倍）。 */
export const HARSH_CAP = 10 ** (-6 / 20);
/** 說書人字幕／對話出現時，音樂與環境壓低 30%。 */
export const DUCK_FACTOR = 0.7;
/** 哪些軌會被 ducking 壓低。 */
export const DUCKED_TRACKS: readonly Track[] = ["music", "ambient"];

/** 主音量節點的值：靜音、背景分頁＝0（減少刺耳音效不影響主音量）。 */
export function masterGain(s: AudioSettings, hidden: boolean): number {
  if (s.muted) return 0;
  if (hidden && s.muteInBackground) return 0;
  return s.master / 100;
}

/** 軌節點的值（不含主音量）：軌靜音＝0；ducking 中的音樂與環境乘 `DUCK_FACTOR`；減少刺耳音效時音效軌乘 `HARSH_CAP`。 */
export function trackGain(s: AudioSettings, track: Track, ducked: boolean): number {
  if (s.trackMuted[track]) return 0;
  const base = (s[track] / 100) * (track === "sfx" && s.reduceHarsh ? HARSH_CAP : 1);
  return ducked && DUCKED_TRACKS.includes(track) ? base * DUCK_FACTOR : base;
}

/** 某一軌實際聽到的音量 = 主 × 軌。 */
export function effectiveGain(s: AudioSettings, track: Track, opts: { hidden?: boolean; ducked?: boolean } = {}): number {
  return masterGain(s, opts.hidden ?? false) * trackGain(s, track, opts.ducked ?? false);
}

/** 減少刺耳音效的濾波與限幅參數。shelf 只接在音效軌（開：拿掉高頻尖音與低頻轟鳴；關：平坦）；
 * 主輸出的限幅固定 −1 dB 防爆音（音樂不受減少刺耳影響）。 */
export interface HarshParams {
  highShelfHz: number;
  highShelfDb: number;
  lowShelfHz: number;
  lowShelfDb: number;
  limiterThresholdDb: number;
}

export function harshParams(reduceHarsh: boolean): HarshParams {
  return reduceHarsh
    ? { highShelfHz: 5000, highShelfDb: -12, lowShelfHz: 120, lowShelfDb: -9, limiterThresholdDb: -1 }
    : { highShelfHz: 5000, highShelfDb: 0, lowShelfHz: 120, lowShelfDb: 0, limiterThresholdDb: -1 };
}
