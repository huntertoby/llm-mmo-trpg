// 延遲載入（AU-1；docs/art/音效與音樂方案.md 第 3 節）：依區域的取樣清單，進區域才載入。
// 格式照 `canPlayType` 選（Opus 的 .ogg 優先，其次 AAC 的 .m4a）；載入或解碼失敗一律靜默降級（那個 id 不出聲）。
// 第一階段不用外部素材，清單是空的；第二階段放進取樣後在這裡登記。
import type { AudioEngine } from "./engine";
import type { BufferLike, SoundSource, Track } from "./types";

export interface ManifestEntry {
  id: string;
  track: Track;
  /** 各格式的網址（至少一種）。 */
  src: { ogg?: string; m4a?: string };
  /** 循環播放（音樂、環境）。 */
  loop?: boolean;
}

/** 區域 → 取樣清單。`"common"` 是每個區域都要的。 */
export const AUDIO_MANIFEST: Readonly<Record<string, readonly ManifestEntry[]>> = {};

const FORMATS: readonly { key: keyof ManifestEntry["src"]; mime: string }[] = [
  { key: "ogg", mime: 'audio/ogg; codecs="opus"' },
  { key: "m4a", mime: 'audio/mp4; codecs="mp4a.40.2"' },
];

/** 依 `canPlayType` 挑網址："probably" 優先於 "maybe"，同等級照 ogg → m4a；都不行回傳 null。 */
export function pickFormat(src: ManifestEntry["src"], canPlayType: (mime: string) => string): string | null {
  let best: string | null = null;
  let bestRank = 0;
  for (const f of FORMATS) {
    const url = src[f.key];
    if (url === undefined) continue;
    let answer = "";
    try {
      answer = canPlayType(f.mime);
    } catch {
      answer = "";
    }
    const rank = answer === "probably" ? 2 : answer === "maybe" ? 1 : 0;
    if (rank > bestRank) {
      best = url;
      bestRank = rank;
    }
  }
  return best;
}

/** 已解碼的取樣 → 音源。 */
export function bufferSource(buffer: BufferLike, track: Track, loop = false): SoundSource {
  return {
    track,
    start(ctx, out, at) {
      const node = ctx.createBufferSource();
      node.buffer = buffer;
      node.loop = loop;
      node.connect(out);
      node.start(at);
      return loop ? Number.POSITIVE_INFINITY : buffer.duration;
    },
  };
}

export interface LoaderDeps {
  fetchBytes: (url: string) => Promise<ArrayBuffer>;
  canPlayType: (mime: string) => string;
  manifest?: Readonly<Record<string, readonly ManifestEntry[]>>;
}

/** 依區域載入取樣（重複呼叫同一區域不重載）。 */
export class RegionLoader {
  private readonly loaded = new Set<string>();

  constructor(
    private readonly engine: AudioEngine,
    private readonly deps: LoaderDeps,
  ) {}

  /** 載入區域的清單；回傳成功登記的音源數。任何失敗都吞掉。 */
  async load(region: string): Promise<number> {
    if (this.loaded.has(region)) return 0;
    this.loaded.add(region);
    const entries = (this.deps.manifest ?? AUDIO_MANIFEST)[region] ?? [];
    let ok = 0;
    for (const e of entries) {
      if (this.engine.hasSound(e.id)) continue;
      const url = pickFormat(e.src, this.deps.canPlayType);
      if (url === null) continue;
      try {
        const bytes = await this.deps.fetchBytes(url);
        const ctx = await this.engine.ready();
        const buffer = await ctx.decodeAudioData(bytes);
        this.engine.registerSound(e.id, bufferSource(buffer, e.track, e.loop ?? false));
        ok += 1;
      } catch {
        // 靜默降級：這個 id 不出聲
      }
    }
    return ok;
  }
}

/** 瀏覽器用的依賴：`fetch` 與 `<audio>.canPlayType`。 */
export function browserLoaderDeps(): LoaderDeps {
  const probe = typeof document === "undefined" ? null : document.createElement("audio");
  return {
    fetchBytes: async (url) => {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`audio ${res.status}`);
      return res.arrayBuffer();
    },
    canPlayType: (mime) => probe?.canPlayType(mime) ?? "",
  };
}
