// 音訊引擎（AU-1）：原生 Web Audio，不加套件。
// 節點：每一聲 → 聲音 gain → 軌 gain（音效／音樂／環境）→ 主 gain → 限幅 → 輸出；
// 音效軌在軌 gain 與主 gain 之間多接高頻 shelf → 低頻 shelf（減少刺耳音效用，AU-2 起只作用在音效軌）。
// - 解鎖前完全不出聲：第一次點擊或按鍵（`unlock()`）才建立 AudioContext；之前的 `play` 直接丟掉。
// - `play(id, opts)`：id 對不到音源就不出聲（AU-2、AU-3 用 `registerSound` 掛音源）。
// - 不用 Math.random、不讀牆上時鐘；排程只用 AudioContext.currentTime。
import { harshParams, masterGain, trackGain } from "./mix";
import { DEFAULT_AUDIO_SETTINGS, loadAudioSettings, normalizeSettings, saveAudioSettings, type AudioSettings, type StorageLike } from "./settings";
import { TRACKS, type AudioContextLike, type BiquadLike, type CompressorLike, type GainLike, type LoopNode, type PlayOpts, type SoundSource, type Track } from "./types";
import { mergeGain, VoiceTracker } from "./voices";

/** 循環播放的選項（AU-3）。 */
export interface LoopOpts {
  track?: Track;
  variantKey?: string;
  /** 這一條的音量（線性，預設 1）。 */
  gain?: number;
  /** 淡入秒數（預設 0.6）。 */
  fadeIn?: number;
}

/** 循環播放的把手：`stop(fade)` 淡出後停止。 */
export interface LoopHandle {
  stop(fade?: number): void;
}

/** 設定變更的平滑時間常數（秒）。 */
const SETTING_TC = 0.02;
/** ducking 壓低／回復的時間常數（秒）。 */
const DUCK_TC = 0.15;

export type PlayResult = "played" | "merged" | "dropped" | "silent";

interface Graph {
  ctx: AudioContextLike;
  master: GainLike;
  tracks: Record<Track, GainLike>;
  high: BiquadLike;
  low: BiquadLike;
  limiter: CompressorLike;
}

export interface AudioEngineOpts {
  /** 建立 AudioContext（瀏覽器：`() => new AudioContext()`；測試：假物件）。回傳 null＝不支援，永遠不出聲。 */
  createContext: () => AudioContextLike | null;
  storage?: StorageLike | null;
  /** 不給就從 `storage` 讀。 */
  settings?: AudioSettings;
}

function setParam(p: { setTargetAtTime(v: number, t: number, tc: number): unknown; cancelScheduledValues(t: number): unknown }, v: number, t: number, tc: number): void {
  p.cancelScheduledValues(t);
  p.setTargetAtTime(v, t, tc);
}

export class AudioEngine {
  private graph: Graph | null = null;
  private current: AudioSettings;
  private readonly storage: StorageLike | null | undefined;
  private readonly sounds = new Map<string, SoundSource>();
  private readonly voices = new VoiceTracker<GainLike>();
  private readonly listeners = new Set<() => void>();
  private readonly readyWaiters: ((ctx: AudioContextLike) => void)[] = [];
  private duckCount = 0;
  private hidden = false;

  constructor(private readonly opts: AudioEngineOpts) {
    this.storage = opts.storage;
    this.current = opts.settings ?? (opts.storage === undefined ? loadAudioSettings() : loadAudioSettings(opts.storage));
  }

  // ---- 設定 ----

  get settings(): AudioSettings {
    return this.current;
  }

  setSettings(patch: Partial<AudioSettings>): void {
    this.current = normalizeSettings({ ...this.current, ...patch, trackMuted: { ...this.current.trackMuted, ...(patch.trackMuted ?? {}) } });
    if (this.storage === undefined) saveAudioSettings(this.current);
    else saveAudioSettings(this.current, this.storage);
    this.apply(SETTING_TC);
    this.emit();
  }

  toggleMute(): boolean {
    this.setSettings({ muted: !this.current.muted });
    return this.current.muted;
  }

  resetSettings(): void {
    this.setSettings({ ...DEFAULT_AUDIO_SETTINGS, trackMuted: { ...DEFAULT_AUDIO_SETTINGS.trackMuted } });
  }

  subscribe(fn: () => void): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  private emit(): void {
    for (const fn of [...this.listeners]) fn();
  }

  // ---- 解鎖 ----

  get unlocked(): boolean {
    return this.graph !== null;
  }

  /** 使用者第一次點擊或按鍵時呼叫：建立 AudioContext 與混音節點。回傳是否可出聲。 */
  unlock(): boolean {
    if (this.graph === null) {
      let ctx: AudioContextLike | null = null;
      try {
        ctx = this.opts.createContext();
      } catch {
        ctx = null;
      }
      if (ctx === null) return false;
      this.graph = this.build(ctx);
      this.apply(0);
      for (const w of this.readyWaiters.splice(0)) w(ctx);
      this.emit();
    }
    if (this.graph.ctx.state === "suspended") this.graph.ctx.resume().catch(() => undefined);
    return true;
  }

  /** AudioContext 已經在跑（resume 成功）。 */
  get running(): boolean {
    return this.graph?.ctx.state === "running";
  }

  /** 解鎖後 resolve（延遲載入用）。 */
  ready(): Promise<AudioContextLike> {
    if (this.graph !== null) return Promise.resolve(this.graph.ctx);
    return new Promise((resolve) => this.readyWaiters.push(resolve));
  }

  /** 現在的 AudioContext 時間（解鎖前 0）。 */
  now(): number {
    return this.graph?.ctx.currentTime ?? 0;
  }

  private build(ctx: AudioContextLike): Graph {
    const master = ctx.createGain();
    const high = ctx.createBiquadFilter();
    high.type = "highshelf";
    const low = ctx.createBiquadFilter();
    low.type = "lowshelf";
    const limiter = ctx.createDynamicsCompressor();
    limiter.knee.value = 0;
    limiter.ratio.value = 20;
    limiter.attack.value = 0.003;
    limiter.release.value = 0.1;
    master.connect(limiter);
    limiter.connect(ctx.destination);
    high.connect(low);
    low.connect(master);
    const tracks = {} as Record<Track, GainLike>;
    for (const t of TRACKS) {
      const g = ctx.createGain();
      g.connect(t === "sfx" ? high : master);
      tracks[t] = g;
    }
    return { ctx, master, tracks, high, low, limiter };
  }

  /** 把設定、背景分頁、ducking 套到節點上。 */
  private apply(tc: number): void {
    const g = this.graph;
    if (g === null) return;
    const t = g.ctx.currentTime;
    const s = this.current;
    setParam(g.master.gain, masterGain(s, this.hidden), t, tc);
    for (const tr of TRACKS) setParam(g.tracks[tr].gain, trackGain(s, tr, this.duckCount > 0), t, tc === 0 ? 0 : tr === "sfx" ? tc : Math.max(tc, DUCK_TC));
    const h = harshParams(s.reduceHarsh);
    g.high.frequency.value = h.highShelfHz;
    g.high.gain.value = h.highShelfDb;
    g.low.frequency.value = h.lowShelfHz;
    g.low.gain.value = h.lowShelfDb;
    g.limiter.threshold.value = h.limiterThresholdDb;
  }

  // ---- 背景分頁、ducking ----

  setHidden(hidden: boolean): void {
    if (hidden === this.hidden) return;
    this.hidden = hidden;
    this.apply(SETTING_TC);
  }

  get ducked(): boolean {
    return this.duckCount > 0;
  }

  /** 說書人字幕或對話出現時呼叫；回傳的函式在它消失時呼叫（可重疊，全部放開才回復）。 */
  duck(): () => void {
    this.duckCount += 1;
    if (this.duckCount === 1) this.apply(DUCK_TC);
    let released = false;
    return () => {
      if (released) return;
      released = true;
      this.duckCount -= 1;
      if (this.duckCount === 0) this.apply(DUCK_TC);
    };
  }

  // ---- 音源與播放 ----

  registerSound(id: string, source: SoundSource): void {
    this.sounds.set(id, source);
  }

  unregisterSound(id: string): void {
    this.sounds.delete(id);
  }

  hasSound(id: string): boolean {
    return this.sounds.has(id);
  }

  /** 同時在播的聲音數（測試、開發頁用）。 */
  activeVoices(id?: string): number {
    this.prune();
    return id === undefined ? this.voices.active : this.voices.countOf(id);
  }

  play(id: string, opts: PlayOpts = {}): PlayResult {
    const g = this.graph;
    if (g === null) return "silent"; // 解鎖前不出聲
    const src = this.sounds.get(id);
    if (src === undefined) return "silent";
    const now = g.ctx.currentTime;
    const at = Math.max(now, opts.at ?? now);
    this.prune();
    const admit = this.voices.admit(id, at);
    if (admit.kind === "drop") return "dropped";
    if (admit.kind === "merge") {
      setParam(admit.voice.handle.gain, mergeGain(admit.voice.count), at, 0.005);
      return "merged";
    }
    const track = opts.track ?? src.track;
    // 減少刺耳音效：環境軌的衝擊點綴（雷、爆炸）不出聲
    if (this.current.reduceHarsh && track === "ambient" && src.harsh === true) return "silent";
    const voice = g.ctx.createGain();
    voice.gain.value = 1;
    voice.connect(g.tracks[track]);
    let dur = 0;
    try {
      dur = src.start(g.ctx, voice, at, opts.variantKey, { soften: this.current.reduceHarsh && track === "sfx" });
    } catch {
      voice.disconnect();
      return "silent";
    }
    this.voices.add(id, at, at + Math.max(0, dur), voice, opts.group);
    return "played";
  }

  /**
   * AU-3：取消 `group` 這一組還沒開始的聲音（斷開它們的 gain，排好的取樣就不會出聲）。回傳取消的數量。
   * 「跳過」時不補放、按住加速時重排都用它。
   */
  cancelPending(group: string): number {
    const g = this.graph;
    if (g === null) return 0;
    const gone = this.voices.takePending(g.ctx.currentTime, group);
    for (const v of gone) {
      v.handle.gain.value = 0;
      v.handle.disconnect();
    }
    return gone.length;
  }

  /**
   * AU-3：循環播放（環境音、燃燒）。不算進同時播放上限（全場同一個循環只放一條由 `LoopDeck` 管）。
   * 解鎖前、音源不能循環、減少刺耳音效開啟時環境軌的 `harsh` 音源：回傳 `null`（不出聲）。
   */
  startLoop(id: string, opts: LoopOpts = {}): LoopHandle | null {
    const g = this.graph;
    if (g === null) return null;
    const src = this.sounds.get(id);
    if (src?.loop === undefined) return null;
    const track = opts.track ?? src.track;
    if (this.current.reduceHarsh && track === "ambient" && src.harsh === true) return null;
    const now = g.ctx.currentTime;
    const voice = g.ctx.createGain();
    voice.gain.value = 0;
    voice.connect(g.tracks[track]);
    const fadeIn = Math.max(0.01, opts.fadeIn ?? 0.6);
    setParam(voice.gain, opts.gain ?? 1, now, fadeIn / 3);
    let node: LoopNode;
    try {
      node = src.loop(g.ctx, voice, now, opts.variantKey, { soften: this.current.reduceHarsh && track === "sfx" });
    } catch {
      voice.disconnect();
      return null;
    }
    let stopped = false;
    return {
      stop: (fade = 0.6) => {
        if (stopped) return;
        stopped = true;
        const t = g.ctx.currentTime;
        const f = Math.max(0.01, fade);
        setParam(voice.gain, 0, t, f / 3);
        node.stop(t + f);
      },
    };
  }

  private prune(): void {
    for (const v of this.voices.prune(this.now())) v.handle.disconnect();
  }

  /** 測試、開發頁用：目前的混音節點。 */
  get nodes(): Readonly<Graph> | null {
    return this.graph;
  }
}
