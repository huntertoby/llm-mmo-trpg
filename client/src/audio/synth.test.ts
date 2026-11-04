import { describe, expect, it } from "vitest";
import { AudioEngine } from "./engine";
import { FakeAudioContext, FakeBuffer } from "./fakeAudio";
import { HARSH_CAP, masterGain, trackGain } from "./mix";
import { DEFAULT_AUDIO_SETTINGS, normalizeSettings } from "./settings";
import { parseSfxTable, registerSfxLibrary, SFX_TABLE, sfxProblems, synthSource } from "./sfxLibrary";
import { frequenciesOf, HARSH_MAX_HZ, HARSH_MIN_HZ, LAYER_KINDS, layerKind, peakOf, renderSfx, sfxDuration, sfxSeed, softenSfx, type SfxDef } from "./synth";

const SR = 8000;
const defs = SFX_TABLE.defs;
const ids = Object.keys(defs).sort();

function render(id: string, variant?: string, sr = SR): Float32Array {
  const def = defs[id];
  if (def === undefined) throw new Error(id);
  return renderSfx(def, { sampleRate: sr, seed: sfxSeed(id, variant) });
}

describe("參數表 content/audio/sfx.yaml", () => {
  it("每一筆都解析成功、沒有被略過", () => {
    expect(SFX_TABLE.errors).toEqual([]);
    expect(ids.length).toBeGreaterThanOrEqual(70);
  });

  it("介面音 20 個（2.2）", () => {
    expect(ids.filter((id) => defs[id]?.cat === "ui")).toHaveLength(20);
  });

  it("每一層都對得到一個積木，每個積木都有音效在用", () => {
    const used = new Set<string>();
    for (const id of ids) for (const l of defs[id]?.layers ?? []) used.add(layerKind(l));
    expect([...used].sort()).toEqual([...LAYER_KINDS].sort());
  });

  it("每個音效都算得出聲音：有長度、不是全靜音、不超過 ±1", () => {
    for (const id of ids) {
      const data = render(id);
      expect(data.length, id).toBeGreaterThan(0);
      const peak = peakOf(data);
      expect(peak, id).toBeGreaterThan(0.01);
      expect(peak, id).toBeLessThanOrEqual(1);
      expect(data.every(Number.isFinite), id).toBe(true);
    }
  });

  it("壞掉的項目會被抓到並略過", () => {
    const t = parseSfxTable(`sfx:
  ok: {zh: 好, cat: ui, layers: [{tone: sine, freq: 440, dur: 0.1}]}
  two_kinds: {zh: 兩個種類, cat: ui, layers: [{tone: sine, noise: band, freq: 440, dur: 0.1}]}
  no_dur: {zh: 沒長度, cat: ui, layers: [{noise: band}]}
  bad_cat: {zh: 壞分類, cat: music, layers: [{tone: sine, freq: 440, dur: 0.1}]}
  Bad-Id: {zh: 壞 id, cat: ui, layers: [{tone: sine, freq: 440, dur: 0.1}]}
`);
    expect(Object.keys(t.defs)).toEqual(["ok"]);
    expect(t.errors).toHaveLength(4);
    expect(sfxProblems({ zh: "x", cat: "ui", layers: [] })).toContain("layers 不能是空的");
    expect(parseSfxTable("sfx: [").errors[0]).toMatch(/YAML/);
  });
});

describe("確定性", () => {
  it("同參數、同種子、同取樣率：逐點相同", () => {
    for (const id of ids) expect(render(id, "u1#3"), id).toEqual(render(id, "u1#3"));
  });

  it("隨機成分跟著變體鍵改變（雜訊、劈啪、脈衝抖動）", () => {
    for (const id of ["swing_slash", "elem_fire", "ui_dice_roll", "status_shock"]) {
      expect(render(id, "a"), id).not.toEqual(render(id, "b"));
    }
  });

  it("種子是 seedOf＋fmix32 的雜湊，不用 Math.random", () => {
    expect(sfxSeed("swing_slash", "k")).toBe(sfxSeed("swing_slash", "k"));
    expect(sfxSeed("swing_slash", "k")).not.toBe(sfxSeed("swing_slash", "j"));
    const orig = Math.random;
    Math.random = () => {
      throw new Error("不可以用 Math.random");
    };
    try {
      for (const id of ids) render(id, "x");
    } finally {
      Math.random = orig;
    }
  });

  it("音源經過引擎：同一個變體鍵寫進 AudioBuffer 的取樣相同、而且只算一次", () => {
    const ctx = new FakeAudioContext();
    const engine = new AudioEngine({ createContext: () => ctx, settings: normalizeSettings(DEFAULT_AUDIO_SETTINGS) });
    engine.unlock();
    expect(registerSfxLibrary(engine)).toBe(ids.length);
    expect(engine.play("hit_blunt", { at: 0, variantKey: "v" })).toBe("played");
    ctx.currentTime = 5;
    expect(engine.play("hit_blunt", { at: 5, variantKey: "v" })).toBe("played");
    expect(ctx.buffers).toHaveLength(1);
    expect((ctx.buffers[0] as FakeBuffer).data).toEqual(render("hit_blunt", "v", ctx.sampleRate));
    expect(engine.play("hit_blunt", { at: 6, variantKey: "w" })).toBe("played");
    expect(ctx.buffers).toHaveLength(2);
  });
});

describe("減少刺耳音效", () => {
  it("預設是關閉的", () => {
    expect(DEFAULT_AUDIO_SETTINGS.reduceHarsh).toBe(false);
    expect(normalizeSettings(null).reduceHarsh).toBe(false);
    expect(normalizeSettings({ reduceHarsh: "yes" }).reduceHarsh).toBe(false);
  });

  it("柔和版沒有超過門檻的頻率設定，也沒有鋸齒、方波、白雜訊、高通", () => {
    for (const id of ids) {
      const soft = softenSfx(defs[id] as SfxDef);
      for (const f of frequenciesOf(soft)) {
        expect(f, id).toBeLessThanOrEqual(HARSH_MAX_HZ);
        expect(f, id).toBeGreaterThanOrEqual(HARSH_MIN_HZ);
      }
      for (const l of soft.layers) {
        if ("tone" in l) expect(["sine", "triangle"], id).toContain(l.tone);
        if ("noise" in l) expect(["band", "low"], id).toContain(l.noise);
      }
    }
  });

  it("原本的參數表裡確實有超過門檻的設定（測試不是空轉）", () => {
    expect(ids.some((id) => frequenciesOf(defs[id] as SfxDef).some((f) => f > HARSH_MAX_HZ))).toBe(true);
  });

  it("只作用在音效軌（−6 dB）；主音量與音樂不動", () => {
    const on = { ...DEFAULT_AUDIO_SETTINGS, reduceHarsh: true };
    expect(masterGain(on, false)).toBe(masterGain(DEFAULT_AUDIO_SETTINGS, false));
    expect(trackGain(on, "music", false)).toBe(trackGain(DEFAULT_AUDIO_SETTINGS, "music", false));
    expect(trackGain(on, "ambient", false)).toBe(trackGain(DEFAULT_AUDIO_SETTINGS, "ambient", false));
    expect(trackGain(on, "sfx", false)).toBeCloseTo(trackGain(DEFAULT_AUDIO_SETTINGS, "sfx", false) * HARSH_CAP, 9);
  });

  it("音效軌放柔和版；環境軌的衝擊點綴（harsh）不出聲，其他環境音照常", () => {
    const ctx = new FakeAudioContext();
    const engine = new AudioEngine({ createContext: () => ctx, settings: normalizeSettings({ ...DEFAULT_AUDIO_SETTINGS, reduceHarsh: true }) });
    engine.unlock();
    registerSfxLibrary(engine);
    expect(engine.play("amb_thunder")).toBe("silent");
    expect(engine.play("elem_mist", { track: "ambient" })).toBe("played");
    expect(engine.play("explosion")).toBe("played"); // 音效軌：柔和版
    const soft = renderSfx(softenSfx(defs.explosion as SfxDef), { sampleRate: ctx.sampleRate, seed: sfxSeed("explosion") });
    expect((ctx.buffers.at(-1) as FakeBuffer).data).toEqual(soft);
    engine.setSettings({ reduceHarsh: false });
    expect(engine.play("amb_thunder")).toBe("played");
  });

  it("長度照參數表；柔和版不改長度", () => {
    for (const id of ids) {
      const def = defs[id] as SfxDef;
      expect(sfxDuration(softenSfx(def)), id).toBeCloseTo(sfxDuration(def), 9);
      // AU-3：循環的環境音底聲一筆 6 秒；其他音效最多 3 秒
      expect(sfxDuration(def), id).toBeLessThanOrEqual(def.cat === "ambient" ? 6 : 3);
    }
    const src = synthSource("ui_tap", defs.ui_tap as SfxDef);
    expect(src.track).toBe("sfx");
  });
});
