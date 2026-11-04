// 合成積木（AU-2；docs/art/音效與音樂方案.md 第 2、4 節）：一筆音效參數表（`content/audio/sfx.yaml`）→ 單聲道波形。
// 純函式、確定性：雜訊、劈啪時間、音高微調這類隨機成分一律由 `sfxSeed(id, 變體鍵)`（inkStyle 的 seedOf ＋ 6N-7 的 fmix32）
// 經 LCG 決定，不用 Math.random；同參數、同種子、同取樣率必定得到逐點相同的波形。
// 用 JS 直接算出取樣（不靠 OscillatorNode 排程），所以測試不需要 OfflineAudioContext 就能比對波形。
//
// 積木（每一層 `layers[i]` 只能有一個種類鍵）：
// - noise：濾波雜訊（white／band／low／high；color 白、粉紅、棕；freq 可掃頻）
// - tone：振盪器（sine／triangle／square／saw，polyBLEP 去混疊；freq 可掃頻、可加顫音、可加低通）
// - fm：FM 鐘（bell）與金屬（metal，兩組不諧和的 FM 疊在一起）；index 可隨時間變化
// - chord：和弦鐘（每個音是帶不諧和泛音的鐘；stagger＞0 就是琶音）
// - pulses：短脈衝序列（雜訊喀聲，或 pitch 給了就是一串上滑的「啵」＝冒泡）
// - crackle：劈啪（每秒 crackle 個雜訊短脈衝，時間由種子決定）
// 共用欄位：dur（秒）、env [起音, 衰減到 −40 dB 的時間, 保持]、gain（dB）、delay（秒）。
import { fmix32 } from "../render/attackVariants";
import { lcg, seedOf } from "../render/inkStyle";

export type Range = number | readonly [number, number];
/** [起音秒, 衰減秒（到 −40 dB）, 保持秒（可省）]。 */
export type Env = readonly [number, number] | readonly [number, number, number];

interface LayerCommon {
  env?: Env;
  /** dB（預設 0）。 */
  gain?: number;
  /** 秒（預設 0）。 */
  delay?: number;
}

interface LayerBase extends LayerCommon {
  dur: number;
}

export type NoiseFilter = "white" | "band" | "low" | "high";
export type NoiseColor = "white" | "pink" | "brown";
export type Wave = "sine" | "triangle" | "square" | "saw";

export interface NoiseLayer extends LayerBase {
  noise: NoiseFilter;
  color?: NoiseColor;
  freq?: Range;
  q?: number;
}
export interface ToneLayer extends LayerBase {
  tone: Wave;
  freq: Range;
  /** [速率 Hz, 深度 cents]。 */
  vibrato?: readonly [number, number];
  /** 低通 Hz。 */
  lp?: number;
}
export interface FmLayer extends LayerBase {
  fm: "bell" | "metal";
  freq: Range;
  /** 調變器／載波頻率比。 */
  ratio: number;
  index: Range;
}
export interface ChordLayer extends LayerBase {
  chord: readonly number[];
  /** 每個音之間的延遲（秒）；0＝同時。 */
  stagger?: number;
  /** 不諧和泛音的量 0～1（預設 0.5）。 */
  bright?: number;
}
export interface PulseLayer extends LayerCommon {
  /** 可省：預設由個數與間隔推出。 */
  dur?: number;
  pulses: number;
  /** 脈衝間隔（秒）。 */
  every: number;
  /** 時間抖動（間隔的比例 0～1，由種子決定）。 */
  jitter?: number;
  /** 每個脈衝的長度（秒）。 */
  click: number;
  /** 雜訊喀聲的帶通中心（第一個 → 最後一個脈衝掃過去）。 */
  freq?: Range;
  q?: number;
  /** 給了就改成正弦啵聲（每個脈衝從 pitch[0] 滑到 pitch[1]）。 */
  pitch?: Range;
  /** 每個脈衝的音量比上一個（預設 1）。 */
  fade?: number;
}
export interface CrackleLayer extends LayerBase {
  /** 每秒幾個劈啪。 */
  crackle: number;
  click?: number;
  freq: number;
  q?: number;
}

export type Layer = NoiseLayer | ToneLayer | FmLayer | ChordLayer | PulseLayer | CrackleLayer;
export const LAYER_KINDS = ["noise", "tone", "fm", "chord", "pulses", "crackle"] as const;
export type LayerKind = (typeof LAYER_KINDS)[number];

export const SFX_CATEGORIES = ["ui", "windup", "swing", "hit", "element", "result", "primitive", "status", "surface", "explosion", "step", "system", "ambient"] as const;
export type SfxCategory = (typeof SFX_CATEGORIES)[number];

export interface SfxDef {
  /** 中文名（dev 頁顯示）。 */
  zh: string;
  cat: SfxCategory;
  /** 觸發點說明。 */
  use?: string;
  /** 預設軌（預設 sfx）。 */
  track?: "sfx" | "ambient";
  /** full＝第一階段合成（○）；temp＝合成暫代、之後換取樣（△）。 */
  synth?: "full" | "temp";
  /** 衝擊點綴（雷、爆炸）：減少刺耳音效開啟時，放在環境軌就不出聲。 */
  harsh?: boolean;
  /** 整體 dB（預設 0）。 */
  gain?: number;
  /** 依變體鍵的音高微調範圍（± cents，預設 0）。 */
  vary?: number;
  layers: readonly Layer[];
}

export function layerKind(l: Layer): LayerKind {
  const found = LAYER_KINDS.filter((k) => k in l);
  if (found.length !== 1 || found[0] === undefined) throw new Error(`一層只能有一個種類鍵（${found.join("、") || "沒有"}）`);
  return found[0];
}

// ---------------------------------------------------------------- 種子、數值

/** 音效的種子：`fmix32(seedOf("id#變體鍵"))`。 */
export function sfxSeed(id: string, variantKey?: string): number {
  return fmix32(seedOf(`${id}#${variantKey ?? ""}`));
}

export function dbToGain(db: number): number {
  return 10 ** (db / 20);
}

/** 掃頻：兩端都 > 0 用指數（聽起來均勻），否則線性。 */
export function rangeAt(r: Range, frac: number): number {
  if (typeof r === "number") return r;
  const [a, b] = r;
  const f = Math.min(1, Math.max(0, frac));
  return a > 0 && b > 0 ? a * (b / a) ** f : a + (b - a) * f;
}

function rangeMax(r: Range): number {
  return typeof r === "number" ? r : Math.max(r[0], r[1]);
}

const LN100 = Math.log(100);
const FADE_OUT = 0.004;

/** 包絡：線性起音 → 保持 → 指數衰減（`d` 秒到 −40 dB）；結尾 4 ms 淡出防爆音。 */
export function envAt(t: number, env: Env | undefined, dur: number): number {
  if (t < 0 || t >= dur) return 0;
  let v = 1;
  if (env !== undefined) {
    const a = Math.max(0, env[0]);
    const d = Math.max(1e-4, env[1]);
    const h = Math.max(0, env[2] ?? 0);
    v = t < a ? t / a : t < a + h ? 1 : Math.exp((-LN100 * (t - a - h)) / d);
  }
  const left = dur - t;
  return left < FADE_OUT ? v * (left / FADE_OUT) : v;
}

/** 一層的總長（秒，含 delay）。 */
export function layerLength(l: Layer): number {
  const delay = l.delay ?? 0;
  if ("pulses" in l) return delay + Math.max(l.dur ?? 0, (Math.max(1, l.pulses) - 1) * l.every * (1 + (l.jitter ?? 0) / 2) + l.click);
  if ("chord" in l) return delay + l.dur + Math.max(0, l.chord.length - 1) * (l.stagger ?? 0);
  return delay + l.dur;
}

export function sfxDuration(def: SfxDef): number {
  return def.layers.reduce((m, l) => Math.max(m, layerLength(l)), 0);
}

// ---------------------------------------------------------------- 濾波器（RBJ biquad）

type FilterType = "low" | "high" | "band";

class Biquad {
  private b0 = 1;
  private b1 = 0;
  private b2 = 0;
  private a1 = 0;
  private a2 = 0;
  private x1 = 0;
  private x2 = 0;
  private y1 = 0;
  private y2 = 0;

  constructor(
    private readonly type: FilterType,
    private readonly sr: number,
  ) {}

  set(freq: number, q: number): void {
    const f = Math.min(this.sr * 0.45, Math.max(10, freq));
    const w = (2 * Math.PI * f) / this.sr;
    const cos = Math.cos(w);
    const alpha = Math.sin(w) / (2 * Math.max(0.05, q));
    const a0 = 1 + alpha;
    let b0: number;
    let b1: number;
    let b2: number;
    if (this.type === "low") {
      b0 = (1 - cos) / 2;
      b1 = 1 - cos;
      b2 = b0;
    } else if (this.type === "high") {
      b0 = (1 + cos) / 2;
      b1 = -(1 + cos);
      b2 = b0;
    } else {
      b0 = alpha;
      b1 = 0;
      b2 = -alpha;
    }
    this.b0 = b0 / a0;
    this.b1 = b1 / a0;
    this.b2 = b2 / a0;
    this.a1 = (-2 * cos) / a0;
    this.a2 = (1 - alpha) / a0;
  }

  run(x: number): number {
    const y = this.b0 * x + this.b1 * this.x1 + this.b2 * this.x2 - this.a1 * this.y1 - this.a2 * this.y2;
    this.x2 = this.x1;
    this.x1 = x;
    this.y2 = this.y1;
    this.y1 = y;
    return y;
  }
}

/** 掃頻時每幾個取樣重算一次係數。 */
const COEF_STEP = 32;

// ---------------------------------------------------------------- 產生器

type Rng = () => number;

function noiseGen(color: NoiseColor, rng: Rng): () => number {
  if (color === "white") return () => rng() * 2 - 1;
  if (color === "brown") {
    let b = 0;
    return () => {
      b = (b + 0.02 * (rng() * 2 - 1)) / 1.02;
      return b * 3.5;
    };
  }
  // Paul Kellet 的粉紅雜訊（經濟版）
  let b0 = 0;
  let b1 = 0;
  let b2 = 0;
  return () => {
    const w = rng() * 2 - 1;
    b0 = 0.99765 * b0 + w * 0.099046;
    b1 = 0.963 * b1 + w * 0.2965164;
    b2 = 0.57 * b2 + w * 1.0526913;
    return (b0 + b1 + b2 + w * 0.1848) * 0.25;
  };
}

function polyBlep(t: number, dt: number): number {
  if (t < dt) {
    const x = t / dt;
    return x + x - x * x - 1;
  }
  if (t > 1 - dt) {
    const x = (t - 1) / dt;
    return x * x + x + x + 1;
  }
  return 0;
}

function waveAt(wave: Wave, phase: number, dt: number): number {
  switch (wave) {
    case "sine":
      return Math.sin(2 * Math.PI * phase);
    case "triangle":
      return 1 - 4 * Math.abs(phase - 0.5);
    case "saw":
      return 2 * phase - 1 - polyBlep(phase, dt);
    case "square": {
      const v = phase < 0.5 ? 1 : -1;
      return v + polyBlep(phase, dt) - polyBlep((phase + 0.5) % 1, dt);
    }
  }
}

interface Ctx {
  sr: number;
  rng: Rng;
  /** 音高倍率（vary）。 */
  pitch: number;
  out: Float32Array;
}

function startIndex(l: Layer, sr: number): number {
  return Math.round((l.delay ?? 0) * sr);
}

function renderNoise(l: NoiseLayer, c: Ctx): void {
  const n = Math.round(l.dur * c.sr);
  const s0 = startIndex(l, c.sr);
  const gen = noiseGen(l.color ?? "white", c.rng);
  const filt = l.noise === "white" ? null : new Biquad(l.noise, c.sr);
  const q = l.q ?? 0.9;
  const amp = dbToGain(l.gain ?? 0);
  for (let i = 0; i < n && s0 + i < c.out.length; i++) {
    if (filt !== null && i % COEF_STEP === 0) filt.set(rangeAt(l.freq ?? 1000, i / n) * c.pitch, q);
    const x = gen();
    const y = filt === null ? x : filt.run(x);
    c.out[s0 + i] = (c.out[s0 + i] ?? 0) + y * envAt(i / c.sr, l.env, l.dur) * amp;
  }
}

function renderTone(l: ToneLayer, c: Ctx): void {
  const n = Math.round(l.dur * c.sr);
  const s0 = startIndex(l, c.sr);
  const amp = dbToGain(l.gain ?? 0);
  const lp = l.lp === undefined ? null : new Biquad("low", c.sr);
  lp?.set(l.lp ?? 0, 0.707);
  let phase = 0;
  for (let i = 0; i < n && s0 + i < c.out.length; i++) {
    const t = i / c.sr;
    let f = rangeAt(l.freq, i / n) * c.pitch;
    if (l.vibrato !== undefined) f *= 2 ** ((Math.sin(2 * Math.PI * l.vibrato[0] * t) * l.vibrato[1]) / 1200);
    const dt = f / c.sr;
    const x = waveAt(l.tone, phase, dt);
    phase = (phase + dt) % 1;
    const y = lp === null ? x : lp.run(x);
    c.out[s0 + i] = (c.out[s0 + i] ?? 0) + y * envAt(t, l.env, l.dur) * amp;
  }
}

/** 金屬：第二組 FM 的載波比例（不諧和）。 */
const METAL_SECOND = 1.483;

function renderFm(l: FmLayer, c: Ctx): void {
  const n = Math.round(l.dur * c.sr);
  const s0 = startIndex(l, c.sr);
  const amp = dbToGain(l.gain ?? 0);
  const pairs = l.fm === "metal" ? [1, METAL_SECOND] : [1];
  const pc = pairs.map(() => 0);
  const pm = pairs.map(() => 0);
  for (let i = 0; i < n && s0 + i < c.out.length; i++) {
    const t = i / c.sr;
    const fc = rangeAt(l.freq, i / n) * c.pitch;
    const idx = rangeAt(l.index, i / n);
    let y = 0;
    pairs.forEach((mul, k) => {
      const carrier = fc * mul;
      const mod = carrier * l.ratio;
      y += Math.sin(2 * Math.PI * (pc[k] ?? 0) + idx * Math.sin(2 * Math.PI * (pm[k] ?? 0))) * (k === 0 ? 1 : 0.6);
      pc[k] = ((pc[k] ?? 0) + carrier / c.sr) % 1;
      pm[k] = ((pm[k] ?? 0) + mod / c.sr) % 1;
    });
    c.out[s0 + i] = (c.out[s0 + i] ?? 0) + (y / pairs.length) * envAt(t, l.env, l.dur) * amp;
  }
}

/** 鐘的不諧和泛音（比例、相對音量、衰減加快倍數）。 */
const BELL_PARTIALS: readonly (readonly [number, number, number])[] = [
  [1, 1, 1],
  [2.756, 0.5, 1.8],
  [5.404, 0.25, 3],
];

function renderChord(l: ChordLayer, c: Ctx): void {
  const amp = dbToGain(l.gain ?? 0) / Math.max(1, Math.sqrt(l.chord.length));
  const bright = Math.min(1, Math.max(0, l.bright ?? 0.5));
  const n = Math.round(l.dur * c.sr);
  l.chord.forEach((note, k) => {
    const s0 = startIndex(l, c.sr) + Math.round(k * (l.stagger ?? 0) * c.sr);
    const f = note * c.pitch;
    for (let i = 0; i < n && s0 + i < c.out.length; i++) {
      const t = i / c.sr;
      let y = 0;
      for (const [ratio, level, speed] of BELL_PARTIALS) {
        const lv = ratio === 1 ? level : level * bright;
        if (lv === 0 || f * ratio > c.sr * 0.45) continue;
        y += Math.sin(2 * Math.PI * f * ratio * t) * lv * (speed === 1 ? 1 : Math.exp(-speed * t * 3));
      }
      c.out[s0 + i] = (c.out[s0 + i] ?? 0) + y * envAt(t, l.env, l.dur) * amp;
    }
  });
}

function renderPulses(l: PulseLayer, c: Ctx): void {
  const count = Math.max(1, Math.round(l.pulses));
  const amp = dbToGain(l.gain ?? 0);
  const base = startIndex(l, c.sr);
  const total = layerLength(l) - (l.delay ?? 0);
  const clickN = Math.max(1, Math.round(l.click * c.sr));
  const gen = noiseGen("white", c.rng);
  for (let p = 0; p < count; p++) {
    const frac = count === 1 ? 0 : p / (count - 1);
    const jit = (l.jitter ?? 0) * l.every * (c.rng() - 0.5);
    const at = Math.max(0, p * l.every + jit);
    const s0 = base + Math.round(at * c.sr);
    const level = (l.fade ?? 1) ** p * amp;
    const filt = l.pitch === undefined ? new Biquad("band", c.sr) : null;
    filt?.set(rangeAt(l.freq ?? 2000, frac) * c.pitch, l.q ?? 2);
    let phase = 0;
    for (let i = 0; i < clickN && s0 + i < c.out.length; i++) {
      const t = i / c.sr;
      const pe = Math.min(1, t / 0.001) * Math.exp((-LN100 * t) / l.click);
      let y: number;
      if (l.pitch !== undefined) {
        const f = rangeAt(l.pitch, i / clickN) * c.pitch;
        y = Math.sin(2 * Math.PI * phase);
        phase = (phase + f / c.sr) % 1;
      } else {
        y = (filt as Biquad).run(gen());
      }
      c.out[s0 + i] = (c.out[s0 + i] ?? 0) + y * pe * level * envAt(at + t, l.env, total);
    }
  }
}

function renderCrackle(l: CrackleLayer, c: Ctx): void {
  const count = Math.max(0, Math.round(l.crackle * l.dur));
  const amp = dbToGain(l.gain ?? 0);
  const base = startIndex(l, c.sr);
  const click = l.click ?? 0.004;
  const clickN = Math.max(1, Math.round(click * c.sr));
  const times = Array.from({ length: count }, () => c.rng() * Math.max(0, l.dur - click)).sort((a, b) => a - b);
  const levels = times.map(() => 0.3 + 0.7 * c.rng());
  const gen = noiseGen("white", c.rng);
  const buf = new Float32Array(Math.round(l.dur * c.sr));
  times.forEach((at, k) => {
    const s0 = Math.round(at * c.sr);
    for (let i = 0; i < clickN && s0 + i < buf.length; i++) buf[s0 + i] = (buf[s0 + i] ?? 0) + gen() * Math.exp((-LN100 * i) / clickN) * (levels[k] ?? 1);
  });
  const filt = new Biquad("band", c.sr);
  filt.set(l.freq * c.pitch, l.q ?? 1.2);
  for (let i = 0; i < buf.length && base + i < c.out.length; i++) {
    c.out[base + i] = (c.out[base + i] ?? 0) + filt.run(buf[i] ?? 0) * envAt(i / c.sr, l.env, l.dur) * amp * 2;
  }
}

function renderLayer(l: Layer, c: Ctx): void {
  switch (layerKind(l)) {
    case "noise":
      return renderNoise(l as NoiseLayer, c);
    case "tone":
      return renderTone(l as ToneLayer, c);
    case "fm":
      return renderFm(l as FmLayer, c);
    case "chord":
      return renderChord(l as ChordLayer, c);
    case "pulses":
      return renderPulses(l as PulseLayer, c);
    case "crackle":
      return renderCrackle(l as CrackleLayer, c);
  }
}

export interface RenderOpts {
  sampleRate: number;
  seed: number;
}

/** 參數表 → 單聲道波形（夾在 ±1）。同 `def`、同 `seed`、同 `sampleRate` 逐點相同。 */
export function renderSfx(def: SfxDef, opts: RenderOpts): Float32Array {
  const sr = opts.sampleRate;
  const out = new Float32Array(Math.max(1, Math.ceil(sfxDuration(def) * sr)));
  const master = lcg(opts.seed);
  const cents = (master() * 2 - 1) * (def.vary ?? 0);
  const pitch = 2 ** (cents / 1200);
  def.layers.forEach((l, i) => {
    const rng = lcg(fmix32((opts.seed ^ Math.imul(i + 1, 0x9e3779b1)) >>> 0));
    renderLayer(l, { sr, rng, pitch, out });
  });
  const g = dbToGain(def.gain ?? 0);
  for (let i = 0; i < out.length; i++) out[i] = Math.max(-1, Math.min(1, (out[i] ?? 0) * g));
  return out;
}

/** 波形峰值（dev 頁、測試用）。 */
export function peakOf(data: Float32Array): number {
  let m = 0;
  for (const v of data) m = Math.max(m, Math.abs(v));
  return m;
}

// ---------------------------------------------------------------- 減少刺耳音效

/** 減少刺耳音效開啟時，所有頻率設定的上限與下限（Hz）。 */
export const HARSH_MAX_HZ = 3500;
export const HARSH_MIN_HZ = 70;

const clampHz = (f: number): number => Math.min(HARSH_MAX_HZ, Math.max(HARSH_MIN_HZ, f));
const clampRange = (r: Range): Range => (typeof r === "number" ? clampHz(r) : [clampHz(r[0]), clampHz(r[1])]);
/** 和弦的音降八度到門檻以下（保留和聲）。 */
function octaveDown(f: number): number {
  let x = f;
  while (x > HARSH_MAX_HZ) x /= 2;
  return Math.max(HARSH_MIN_HZ, x);
}

/** 柔和版：頻率夾在門檻內；鋸齒、方波改三角波；白雜訊與高通改成低通／帶通；FM 調變指數減半；鐘不加泛音。 */
export function softenLayer(l: Layer): Layer {
  switch (layerKind(l)) {
    case "noise": {
      const x = l as NoiseLayer;
      const noise: NoiseFilter = x.noise === "white" ? "low" : x.noise === "high" ? "band" : x.noise;
      return { ...x, noise, freq: clampRange(x.freq ?? HARSH_MAX_HZ) };
    }
    case "tone": {
      const x = l as ToneLayer;
      const tone: Wave = x.tone === "saw" || x.tone === "square" ? "triangle" : x.tone;
      return { ...x, tone, freq: clampRange(x.freq), lp: clampHz(x.lp ?? HARSH_MAX_HZ) };
    }
    case "fm": {
      const x = l as FmLayer;
      const freq = clampRange(x.freq);
      const top = rangeMax(freq) * METAL_SECOND;
      const ratio = top * x.ratio > HARSH_MAX_HZ ? HARSH_MAX_HZ / top : x.ratio;
      const index: Range = typeof x.index === "number" ? x.index / 2 : [x.index[0] / 2, x.index[1] / 2];
      return { ...x, freq, ratio, index };
    }
    case "chord": {
      const x = l as ChordLayer;
      return { ...x, chord: x.chord.map(octaveDown), bright: 0 };
    }
    case "pulses": {
      const x = l as PulseLayer;
      const out: PulseLayer = { ...x, freq: clampRange(x.freq ?? 2000) };
      if (x.pitch !== undefined) out.pitch = clampRange(x.pitch);
      return out;
    }
    case "crackle": {
      const x = l as CrackleLayer;
      return { ...x, freq: clampHz(x.freq) };
    }
  }
}

export function softenSfx(def: SfxDef): SfxDef {
  return { ...def, layers: def.layers.map(softenLayer) };
}

/** 一筆參數表裡所有的頻率設定（Hz；測試「減少刺耳後沒有超過門檻」用）。 */
export function frequenciesOf(def: SfxDef): number[] {
  const out: number[] = [];
  const add = (r: Range | undefined): void => {
    if (r === undefined) return;
    if (typeof r === "number") out.push(r);
    else out.push(r[0], r[1]);
  };
  for (const l of def.layers) {
    switch (layerKind(l)) {
      case "noise": {
        const x = l as NoiseLayer;
        // 白雜訊與高通沒有上限，算成取樣率一半（一定超過門檻）
        add(x.noise === "white" || x.noise === "high" ? 24000 : (x.freq ?? 1000));
        break;
      }
      case "tone": {
        const x = l as ToneLayer;
        add(x.freq);
        if (x.tone === "saw" || x.tone === "square") add(rangeMax(x.freq) * 9); // 明顯的高次諧波
        add(x.lp);
        break;
      }
      case "fm": {
        const x = l as FmLayer;
        add(x.freq);
        const top = rangeMax(x.freq) * (x.fm === "metal" ? METAL_SECOND : 1);
        add(top * x.ratio);
        break;
      }
      case "chord": {
        const x = l as ChordLayer;
        for (const f of x.chord) add((x.bright ?? 0.5) > 0 ? f * 5.404 : f);
        break;
      }
      case "pulses": {
        const x = l as PulseLayer;
        add(x.pitch ?? x.freq ?? 2000);
        break;
      }
      case "crackle":
        add((l as CrackleLayer).freq);
        break;
    }
  }
  return out;
}
