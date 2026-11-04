// 音訊核心（AU-1）用到的 Web Audio 最小介面。
// 引擎只依賴這些結構，測試用 `fakeAudio.ts` 的假物件；瀏覽器裡直接傳真的 `AudioContext`。

/** 四軌：音效、音樂、環境（主音量另外乘）。 */
export type Track = "sfx" | "music" | "ambient";
export const TRACKS: readonly Track[] = ["sfx", "music", "ambient"];

export interface ParamLike {
  value: number;
  setValueAtTime(value: number, time: number): unknown;
  setTargetAtTime(target: number, time: number, timeConstant: number): unknown;
  cancelScheduledValues(time: number): unknown;
}

export interface NodeLike {
  connect(dest: NodeLike): unknown;
  disconnect(): void;
}

export interface GainLike extends NodeLike {
  gain: ParamLike;
}

export interface BiquadLike extends NodeLike {
  type: string;
  frequency: ParamLike;
  gain: ParamLike;
}

export interface CompressorLike extends NodeLike {
  threshold: ParamLike;
  knee: ParamLike;
  ratio: ParamLike;
  attack: ParamLike;
  release: ParamLike;
}

export interface ScheduledLike extends NodeLike {
  start(when?: number): void;
  stop(when?: number): void;
}

export interface OscillatorLike extends ScheduledLike {
  type: string;
  frequency: ParamLike;
}

export interface BufferLike {
  duration: number;
}

/** 可以寫入取樣的緩衝（AU-2 合成音用）。 */
export interface AudioBufferLike extends BufferLike {
  getChannelData(channel: number): Float32Array;
}

export interface BufferSourceLike extends ScheduledLike {
  buffer: BufferLike | null;
  loop: boolean;
  /** 播放速度（AU-3：加速時只改排程、不改它，所以音高不變；測試用來確認一直是 1）。 */
  readonly playbackRate?: ParamLike;
}

export interface AudioContextLike {
  readonly currentTime: number;
  readonly state: string;
  readonly destination: NodeLike;
  readonly sampleRate: number;
  resume(): Promise<unknown>;
  createGain(): GainLike;
  createBiquadFilter(): BiquadLike;
  createDynamicsCompressor(): CompressorLike;
  createOscillator(): OscillatorLike;
  createBufferSource(): BufferSourceLike;
  createBuffer(channels: number, length: number, sampleRate: number): AudioBufferLike;
  decodeAudioData(data: ArrayBuffer): Promise<BufferLike>;
}

/**
 * 一個音源：在 `at`（AudioContext 時間，秒）把節點接到 `out` 並開始播放，回傳長度（秒）。
 * AU-2 的合成音、延遲載入的取樣都實作這個介面，用 `registerSound` 掛上。
 */
export interface SoundSource {
  /** 預設的軌（`play` 的 `opts.track` 可覆寫）。 */
  track: Track;
  /** 衝擊點綴（雷、爆炸；AU-2）：減少刺耳音效開啟時，放在環境軌就不出聲。 */
  harsh?: boolean;
  start(ctx: AudioContextLike, out: NodeLike, at: number, variantKey: string | undefined, flags?: StartFlags): number;
  /** 循環播放（AU-3：環境音、燃燒）：在 `at` 開始無縫循環，回傳停止用的把手；沒有＝這個音源不能循環。 */
  loop?(ctx: AudioContextLike, out: NodeLike, at: number, variantKey: string | undefined, flags?: StartFlags): LoopNode;
}

/** 音源內部的循環節點（`stop(at)`：在 AudioContext 時間 `at` 停止）。 */
export interface LoopNode {
  stop(at: number): void;
}

/** 引擎傳給音源的旗標（AU-2）。 */
export interface StartFlags {
  /** 減少刺耳音效開啟、而且這一聲放在音效軌：用柔和版（頻率夾在門檻內）。 */
  soften: boolean;
}

export interface PlayOpts {
  /** 開始時間（AudioContext 時間，秒）；不給＝現在。同一個 id 在同一個 `at` 只放一聲（音量依次數略增）。 */
  at?: number;
  /** 變體鍵（AU-3 依 6N 的雜湊挑；音源自己決定怎麼用）。 */
  variantKey?: string;
  /** 指定軌；不給＝音源的預設軌。 */
  track?: Track;
  /** 分組（AU-3：戰鬥排程用 `battle`）：`cancelPending(group)` 取消這一組還沒開始的聲音（「跳過」時不補放）。 */
  group?: string;
}
