// 測試用的最小假 AudioContext（AU-1；不加套件）：只記錄節點、連線與參數值，不產生聲音。
// `setTargetAtTime` 直接把值設成目標值，測試讀 `.value` 就是最後的音量。
import type { AudioContextLike, BiquadLike, BufferLike, BufferSourceLike, CompressorLike, GainLike, NodeLike, OscillatorLike, ParamLike } from "./types";

export class FakeParam implements ParamLike {
  constructor(public value = 0) {}
  setValueAtTime(v: number): void {
    this.value = v;
  }
  setTargetAtTime(v: number): void {
    this.value = v;
  }
  cancelScheduledValues(): void {}
}

export class FakeNode implements NodeLike {
  outputs: NodeLike[] = [];
  constructor(
    readonly kind: string,
    readonly ctx: FakeAudioContext,
  ) {
    ctx.created.push(this);
  }
  connect(dest: NodeLike): NodeLike {
    this.outputs.push(dest);
    return dest;
  }
  disconnect(): void {
    this.outputs = [];
  }
}

class FakeGain extends FakeNode implements GainLike {
  gain = new FakeParam(1);
}

class FakeBiquad extends FakeNode implements BiquadLike {
  type = "lowpass";
  frequency = new FakeParam(350);
  gain = new FakeParam(0);
}

class FakeCompressor extends FakeNode implements CompressorLike {
  threshold = new FakeParam(-24);
  knee = new FakeParam(30);
  ratio = new FakeParam(12);
  attack = new FakeParam(0.003);
  release = new FakeParam(0.25);
}

class FakeScheduled extends FakeNode {
  startedAt: number | null = null;
  start(when = 0): void {
    this.startedAt = when;
    this.ctx.starts.push({ node: this, at: when });
  }
  stop(): void {}
}

class FakeOscillator extends FakeScheduled implements OscillatorLike {
  type = "sine";
  frequency = new FakeParam(440);
}

class FakeBufferSource extends FakeScheduled implements BufferSourceLike {
  buffer: BufferLike | null = null;
  loop = false;
}

export class FakeAudioContext implements AudioContextLike {
  currentTime = 0;
  state = "suspended";
  created: FakeNode[] = [];
  starts: { node: FakeNode; at: number }[] = [];
  readonly destination: FakeNode;
  /** 解碼失敗的測試用。 */
  failDecode = false;

  constructor() {
    this.destination = new FakeNode("destination", this);
  }
  resume(): Promise<void> {
    this.state = "running";
    return Promise.resolve();
  }
  createGain(): GainLike {
    return new FakeGain("gain", this);
  }
  createBiquadFilter(): BiquadLike {
    return new FakeBiquad("biquad", this);
  }
  createDynamicsCompressor(): CompressorLike {
    return new FakeCompressor("compressor", this);
  }
  createOscillator(): OscillatorLike {
    return new FakeOscillator("oscillator", this);
  }
  createBufferSource(): BufferSourceLike {
    return new FakeBufferSource("bufferSource", this);
  }
  decodeAudioData(data: ArrayBuffer): Promise<BufferLike> {
    if (this.failDecode) return Promise.reject(new Error("decode"));
    return Promise.resolve({ duration: data.byteLength / 1000 });
  }
}

/** 最小的記憶體 Storage。 */
export class MemoryStorage {
  data = new Map<string, string>();
  throwOnGet = false;
  throwOnSet = false;
  getItem(k: string): string | null {
    if (this.throwOnGet) throw new Error("blocked");
    return this.data.get(k) ?? null;
  }
  setItem(k: string, v: string): void {
    if (this.throwOnSet) throw new Error("quota");
    this.data.set(k, v);
  }
}
