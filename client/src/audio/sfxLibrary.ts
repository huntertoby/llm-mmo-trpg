// 音效參數表（AU-2）：`content/audio/sfx.yaml` 在 build 時以 `?raw` 匯入、用 `yaml` 解析（內容即資料；Python 端
// `trpg.content.audio` 的 pydantic schema 由 `trpg content check` 驗證同一份檔）。前端這裡再做一次結構檢查，壞掉的那筆略過不出聲。
// `synthSource` 把一筆參數表包成 AU-1 的 `SoundSource`：第一次播放時算波形、寫進 AudioBuffer，之後用快取。
import { parse } from "yaml";
import sfxYaml from "../../../content/audio/sfx.yaml?raw";
import type { AudioEngine } from "./engine";
import { LAYER_KINDS, renderSfx, SFX_CATEGORIES, sfxDuration, sfxSeed, softenSfx, type Layer, type SfxDef } from "./synth";
import type { AudioBufferLike, AudioContextLike, SoundSource, StartFlags } from "./types";

export interface SfxTable {
  defs: Record<string, SfxDef>;
  /** 略過的項目與原因。 */
  errors: string[];
}

const ID_RE = /^[a-z][a-z0-9_]*$/;
const NUM_KEYS = ["dur", "gain", "delay", "q", "ratio", "stagger", "bright", "pulses", "every", "jitter", "click", "fade", "crackle", "lp"] as const;
const RANGE_KEYS = ["freq", "index", "pitch"] as const;

const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const isRange = (v: unknown): boolean => isNum(v) || (Array.isArray(v) && v.length === 2 && v.every(isNum));

/** 一層的問題（空＝合法）。 */
export function layerProblems(raw: unknown): string[] {
  if (typeof raw !== "object" || raw === null || Array.isArray(raw)) return ["層不是物件"];
  const l = raw as Record<string, unknown>;
  const kinds = LAYER_KINDS.filter((k) => k in l);
  const p: string[] = [];
  if (kinds.length !== 1) p.push(`一層只能有一個種類鍵（找到 ${kinds.join("、") || "沒有"}）`);
  if (kinds[0] === "pulses" ? "dur" in l && (!isNum(l.dur) || l.dur <= 0) : !isNum(l.dur) || l.dur <= 0) p.push("dur 必須是正數");
  for (const k of NUM_KEYS) if (k in l && !isNum(l[k])) p.push(`${k} 必須是數字`);
  for (const k of RANGE_KEYS) if (k in l && !isRange(l[k])) p.push(`${k} 必須是數字或 [起, 迄]`);
  if ("env" in l && !(Array.isArray(l.env) && (l.env.length === 2 || l.env.length === 3) && l.env.every(isNum))) p.push("env 必須是 [起音, 衰減] 或 [起音, 衰減, 保持]");
  if ("chord" in l && !(Array.isArray(l.chord) && l.chord.length > 0 && l.chord.every(isNum))) p.push("chord 必須是頻率清單");
  if (kinds[0] === "tone" && !isRange(l.freq)) p.push("tone 需要 freq");
  if (kinds[0] === "fm" && (!isRange(l.freq) || !isNum(l.ratio) || !isRange(l.index))) p.push("fm 需要 freq、ratio、index");
  if (kinds[0] === "pulses" && (!isNum(l.every) || !isNum(l.click))) p.push("pulses 需要 every、click");
  if (kinds[0] === "crackle" && !isNum(l.freq)) p.push("crackle 需要 freq");
  return p;
}

/** 一筆音效的問題（空＝合法）。 */
export function sfxProblems(raw: unknown): string[] {
  if (typeof raw !== "object" || raw === null || Array.isArray(raw)) return ["不是物件"];
  const d = raw as Record<string, unknown>;
  const p: string[] = [];
  if (typeof d.zh !== "string" || d.zh === "") p.push("缺 zh");
  if (!SFX_CATEGORIES.includes(d.cat as never)) p.push(`未知的 cat：${String(d.cat)}`);
  if ("track" in d && d.track !== "sfx" && d.track !== "ambient") p.push("track 只能是 sfx 或 ambient");
  if ("synth" in d && d.synth !== "full" && d.synth !== "temp") p.push("synth 只能是 full 或 temp");
  if ("harsh" in d && typeof d.harsh !== "boolean") p.push("harsh 必須是 true／false");
  if ("gain" in d && !isNum(d.gain)) p.push("gain 必須是數字");
  if ("vary" in d && !isNum(d.vary)) p.push("vary 必須是數字");
  if (!Array.isArray(d.layers) || d.layers.length === 0) p.push("layers 不能是空的");
  else d.layers.forEach((l, i) => p.push(...layerProblems(l).map((m) => `layers[${i}]：${m}`)));
  return p;
}

/** YAML 文字 → 參數表（檔案最上層是 `sfx:` 對照表）。 */
export function parseSfxTable(text: string): SfxTable {
  const defs: Record<string, SfxDef> = {};
  const errors: string[] = [];
  let doc: unknown;
  try {
    doc = parse(text);
  } catch (e) {
    return { defs, errors: [`YAML 格式錯誤：${String(e)}`] };
  }
  const table = (doc as { sfx?: unknown } | null)?.sfx;
  if (typeof table !== "object" || table === null) return { defs, errors: ["缺少 sfx 對照表"] };
  for (const [id, raw] of Object.entries(table as Record<string, unknown>)) {
    const p = ID_RE.test(id) ? sfxProblems(raw) : ["id 格式錯誤"];
    if (p.length > 0) errors.push(`${id}：${p.join("；")}`);
    else defs[id] = raw as SfxDef;
  }
  return { defs, errors };
}

/** 內建的參數表（build 時匯入）。 */
export const SFX_TABLE: SfxTable = parseSfxTable(sfxYaml);

const CACHE_MAX = 8;

/** 一筆參數表 → 音源。同一個變體鍵、同一個柔和與否只算一次波形。 */
export function synthSource(id: string, def: SfxDef): SoundSource {
  const cache = new Map<string, AudioBufferLike>();
  const soft = softenSfx(def);
  return {
    track: def.track ?? "sfx",
    harsh: def.harsh === true,
    start(ctx: AudioContextLike, out, at, variantKey, flags?: StartFlags) {
      const useSoft = flags?.soften === true;
      const key = `${variantKey ?? ""}|${useSoft ? 1 : 0}|${ctx.sampleRate}`;
      let buf = cache.get(key);
      if (buf === undefined) {
        const data = renderSfx(useSoft ? soft : def, { sampleRate: ctx.sampleRate, seed: sfxSeed(id, variantKey) });
        buf = ctx.createBuffer(1, data.length, ctx.sampleRate);
        buf.getChannelData(0).set(data);
        if (cache.size >= CACHE_MAX) cache.clear();
        cache.set(key, buf);
      }
      const node = ctx.createBufferSource();
      node.buffer = buf;
      node.connect(out);
      node.start(at);
      return sfxDuration(def);
    },
  };
}

/** 把整張參數表掛到引擎上（回傳掛上的數量）。 */
export function registerSfxLibrary(engine: AudioEngine, table: SfxTable = SFX_TABLE): number {
  const ids = Object.keys(table.defs).sort();
  for (const id of ids) {
    const def = table.defs[id];
    if (def !== undefined) engine.registerSound(id, synthSource(id, def));
  }
  return ids.length;
}

export type { Layer, SfxDef };
