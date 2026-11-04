import { describe, expect, it } from "vitest";
import { AudioEngine } from "./engine";
import { FakeAudioContext, MemoryStorage } from "./fakeAudio";
import { installAudio, isMuteShortcut } from "./index";
import { RegionLoader, pickFormat } from "./manifest";
import { DUCK_FACTOR, effectiveGain, HARSH_CAP, harshParams, masterGain } from "./mix";
import { AUDIO_SETTINGS_KEY, DEFAULT_AUDIO_SETTINGS, loadAudioSettings, normalizeSettings, saveAudioSettings } from "./settings";
import type { SoundSource } from "./types";
import { GLOBAL_MAX, MERGE_MAX, mergeGain, PER_ID_MAX } from "./voices";

function setup(settings = DEFAULT_AUDIO_SETTINGS) {
  const ctx = new FakeAudioContext();
  let made = 0;
  const storage = new MemoryStorage();
  const engine = new AudioEngine({
    createContext: () => {
      made += 1;
      return ctx;
    },
    storage,
    settings: normalizeSettings(settings),
  });
  return { ctx, engine, storage, made: () => made };
}

/** 長度 `dur` 秒的測試音源（每次 start 記一筆）。 */
function tone(dur = 0.5, track: SoundSource["track"] = "sfx"): SoundSource & { calls: number } {
  const src = {
    track,
    calls: 0,
    start(ctx: Parameters<SoundSource["start"]>[0], out: Parameters<SoundSource["start"]>[1], at: number) {
      src.calls += 1;
      const o = ctx.createOscillator();
      o.connect(out);
      o.start(at);
      return dur;
    },
  };
  return src;
}

const close = (a: number, b: number) => expect(a).toBeCloseTo(b, 6);

describe("四軌音量：實際音量 = 主 × 軌", () => {
  it("預設值：主 70、音效 80、音樂 50、環境 60", () => {
    const s = DEFAULT_AUDIO_SETTINGS;
    expect([s.master, s.sfx, s.music, s.ambient]).toEqual([70, 80, 50, 60]);
    close(effectiveGain(s, "sfx"), 0.7 * 0.8);
    close(effectiveGain(s, "music"), 0.7 * 0.5);
    close(effectiveGain(s, "ambient"), 0.7 * 0.6);
  });

  it("引擎節點：主 gain × 軌 gain", () => {
    const { engine } = setup();
    engine.unlock();
    engine.setSettings({ master: 50, sfx: 40 });
    const n = engine.nodes!;
    close(n.master.gain.value, 0.5);
    close(n.tracks.sfx.gain.value, 0.4);
    close(n.master.gain.value * n.tracks.sfx.gain.value, effectiveGain(engine.settings, "sfx"));
    close(n.tracks.music.gain.value, 0.5);
  });

  it("音量夾在 0～100", () => {
    const s = normalizeSettings({ master: 140, sfx: -3, music: "x", ambient: 33.4 });
    expect([s.master, s.sfx, s.music, s.ambient]).toEqual([100, 0, 50, 33]);
  });
});

describe("靜音", () => {
  it("全部靜音＝主 gain 0；再切一次回來", () => {
    const { engine } = setup();
    engine.unlock();
    expect(engine.toggleMute()).toBe(true);
    expect(engine.nodes!.master.gain.value).toBe(0);
    expect(effectiveGain(engine.settings, "sfx")).toBe(0);
    expect(engine.toggleMute()).toBe(false);
    close(engine.nodes!.master.gain.value, 0.7);
  });

  it("單軌靜音只影響那一軌", () => {
    const { engine } = setup();
    engine.unlock();
    engine.setSettings({ trackMuted: { ...engine.settings.trackMuted, music: true } });
    expect(engine.nodes!.tracks.music.gain.value).toBe(0);
    close(engine.nodes!.tracks.sfx.gain.value, 0.8);
  });

  it("Shift＋M：只認 Shift＋M，打字中、有其他修飾鍵不算", () => {
    expect(isMuteShortcut({ code: "KeyM", key: "M", shiftKey: true }, false)).toBe(true);
    expect(isMuteShortcut({ code: "KeyM", key: "m", shiftKey: false }, false)).toBe(false);
    expect(isMuteShortcut({ code: "KeyM", key: "M", shiftKey: true }, true)).toBe(false);
    expect(isMuteShortcut({ code: "KeyM", key: "M", shiftKey: true, ctrlKey: true }, false)).toBe(false);
  });

  it("背景分頁靜音（可關）", () => {
    const s = DEFAULT_AUDIO_SETTINGS;
    expect(masterGain(s, true)).toBe(0);
    close(masterGain({ ...s, muteInBackground: false }, true), 0.7);
    const { engine } = setup();
    engine.unlock();
    engine.setHidden(true);
    expect(engine.nodes!.master.gain.value).toBe(0);
    engine.setHidden(false);
    close(engine.nodes!.master.gain.value, 0.7);
  });
});

describe("解鎖前不出聲", () => {
  it("解鎖前 play 不建立 AudioContext、不建立任何節點", () => {
    const { engine, made, ctx } = setup();
    const src = tone();
    engine.registerSound("t", src);
    expect(engine.play("t")).toBe("silent");
    expect(made()).toBe(0);
    expect(src.calls).toBe(0);
    expect(ctx.starts).toHaveLength(0);
    engine.unlock();
    expect(made()).toBe(1);
    expect(engine.play("t")).toBe("played");
    expect(ctx.starts).toHaveLength(1);
  });

  it("installAudio：第一次 pointerdown／keydown 才解鎖，之後拿掉監聽", () => {
    const { engine, made } = setup();
    const listeners = new Map<string, Set<(e: Event) => void>>();
    const target = {
      addEventListener: (t: string, fn: (e: Event) => void) => {
        if (!listeners.has(t)) listeners.set(t, new Set());
        listeners.get(t)!.add(fn);
      },
      removeEventListener: (t: string, fn: (e: Event) => void) => listeners.get(t)?.delete(fn),
    };
    const doc = { ...target, visibilityState: "visible" };
    const fire = (t: string, e: Partial<KeyboardEvent> = {}) => {
      for (const fn of [...(listeners.get(t) ?? [])]) fn({ target: null, preventDefault: () => undefined, ...e } as unknown as Event);
    };
    const off = installAudio(target, doc, engine);
    expect(made()).toBe(0);
    fire("pointerdown");
    expect(made()).toBe(1);
    expect(engine.unlocked).toBe(true);
    expect(listeners.get("pointerdown")?.size ?? 0).toBe(0);
    fire("keydown", { code: "KeyM", key: "M", shiftKey: true });
    expect(engine.settings.muted).toBe(true);
    off();
    expect(listeners.get("keydown")?.size ?? 0).toBe(0);
  });

  it("id 對不到音源：不出聲", () => {
    const { engine } = setup();
    engine.unlock();
    expect(engine.play("nope")).toBe("silent");
  });
});

describe("同時播放上限", () => {
  it(`同一個音效最多 ${PER_ID_MAX} 個；結束後又能放`, () => {
    const { engine, ctx } = setup();
    engine.unlock();
    engine.registerSound("hit", tone(0.5));
    const out = [0, 1, 2, 3, 4].map((i) => engine.play("hit", { at: i * 0.01 }));
    expect(out).toEqual(["played", "played", "played", "dropped", "dropped"]);
    expect(engine.activeVoices("hit")).toBe(PER_ID_MAX);
    ctx.currentTime = 1;
    expect(engine.activeVoices("hit")).toBe(0);
    expect(engine.play("hit")).toBe("played");
  });

  it(`全部最多 ${GLOBAL_MAX} 個`, () => {
    const { engine } = setup();
    engine.unlock();
    for (let i = 0; i < GLOBAL_MAX + 4; i += 1) engine.registerSound(`s${i}`, tone(1));
    const out = Array.from({ length: GLOBAL_MAX + 4 }, (_, i) => engine.play(`s${i}`));
    expect(out.filter((r) => r === "played")).toHaveLength(GLOBAL_MAX);
    expect(out.slice(GLOBAL_MAX)).toEqual(["dropped", "dropped", "dropped", "dropped"]);
  });
});

describe("同一 hitAt 合併", () => {
  it("同一個 id、同一個 at 只放一聲，音量依次數略增（有上限）", () => {
    const { engine, ctx } = setup();
    engine.unlock();
    const src = tone(0.4);
    engine.registerSound("hit", src);
    const out = [0, 1, 2, 3, 4, 5, 6].map(() => engine.play("hit", { at: 0.25 }));
    expect(out[0]).toBe("played");
    expect(out.slice(1).every((r) => r === "merged")).toBe(true);
    expect(src.calls).toBe(1);
    expect(ctx.starts).toHaveLength(1);
    expect(engine.activeVoices("hit")).toBe(1);
    close(mergeGain(2), 1.15);
    expect(mergeGain(20)).toBe(MERGE_MAX);
    // 不同時間點就是另一聲
    expect(engine.play("hit", { at: 0.3 })).toBe("played");
  });

  it("at 毫秒取整：浮點誤差不會拆成兩聲", () => {
    const { engine } = setup();
    engine.unlock();
    engine.registerSound("hit", tone());
    expect(engine.play("hit", { at: 0.1 + 0.2 })).toBe("played");
    expect(engine.play("hit", { at: 0.3 })).toBe("merged");
  });
});

describe("減少刺耳音效", () => {
  it("音效軌最大音量 −6 dB、音效軌開高低頻 shelf；主音量、音樂、限幅不動（AU-2）", () => {
    close(HARSH_CAP, 0.501187);
    const on = { ...DEFAULT_AUDIO_SETTINGS, master: 100, reduceHarsh: true };
    close(masterGain(on, false), 1);
    close(effectiveGain({ ...on, sfx: 100 }, "sfx"), HARSH_CAP);
    close(effectiveGain({ ...on, music: 100 }, "music"), 1);
    const { engine } = setup();
    engine.unlock();
    engine.setSettings({ master: 100, reduceHarsh: true });
    const n = engine.nodes!;
    close(n.master.gain.value, 1);
    close(n.tracks.sfx.gain.value, 0.8 * HARSH_CAP);
    close(n.tracks.music.gain.value, 0.5);
    expect(n.high.type).toBe("highshelf");
    expect(n.high.gain.value).toBeLessThan(0);
    expect(n.low.gain.value).toBeLessThan(0);
    // shelf 只接在音效軌上
    expect((n.tracks.sfx as unknown as { outputs: unknown[] }).outputs).toEqual([n.high]);
    expect((n.tracks.music as unknown as { outputs: unknown[] }).outputs).toEqual([n.master]);
    expect(n.limiter.threshold.value).toBe(harshParams(true).limiterThresholdDb);
    expect(harshParams(true).limiterThresholdDb).toBe(harshParams(false).limiterThresholdDb);
    engine.setSettings({ reduceHarsh: false });
    expect(n.high.gain.value).toBe(0);
    close(n.tracks.sfx.gain.value, 0.8);
  });
});

describe("ducking", () => {
  it("字幕／對話出現時音樂、環境壓低，音效不變；全部放開才回復", () => {
    const { engine } = setup();
    engine.unlock();
    const n = engine.nodes!;
    const a = engine.duck();
    const b = engine.duck();
    close(n.tracks.music.gain.value, 0.5 * DUCK_FACTOR);
    close(n.tracks.ambient.gain.value, 0.6 * DUCK_FACTOR);
    close(n.tracks.sfx.gain.value, 0.8);
    a();
    a(); // 重複放開不影響
    expect(engine.ducked).toBe(true);
    b();
    expect(engine.ducked).toBe(false);
    close(n.tracks.music.gain.value, 0.5);
  });
});

describe("設定存讀", () => {
  it("setSettings 存進 localStorage，新的引擎讀得回來", () => {
    const storage = new MemoryStorage();
    const e1 = new AudioEngine({ createContext: () => null, storage });
    e1.setSettings({ master: 35, reduceHarsh: true });
    e1.toggleMute();
    expect(storage.data.has(AUDIO_SETTINGS_KEY)).toBe(true);
    const e2 = new AudioEngine({ createContext: () => null, storage });
    expect(e2.settings.master).toBe(35);
    expect(e2.settings.reduceHarsh).toBe(true);
    expect(e2.settings.muted).toBe(true);
  });

  it("讀寫失敗、內容壞掉都用預設值，不丟例外", () => {
    const st = new MemoryStorage();
    st.data.set(AUDIO_SETTINGS_KEY, "{not json");
    expect(loadAudioSettings(st)).toEqual(DEFAULT_AUDIO_SETTINGS);
    st.throwOnGet = true;
    expect(loadAudioSettings(st)).toEqual(DEFAULT_AUDIO_SETTINGS);
    st.throwOnSet = true;
    expect(() => saveAudioSettings(DEFAULT_AUDIO_SETTINGS, st)).not.toThrow();
    expect(loadAudioSettings(null)).toEqual(DEFAULT_AUDIO_SETTINGS);
  });
});

describe("延遲載入", () => {
  it("canPlayType 選格式：probably 優先，都不行回傳 null", () => {
    const src = { ogg: "a.ogg", m4a: "a.m4a" };
    expect(pickFormat(src, (m) => (m.includes("ogg") ? "probably" : "maybe"))).toBe("a.ogg");
    expect(pickFormat(src, (m) => (m.includes("mp4") ? "probably" : "maybe"))).toBe("a.m4a");
    expect(pickFormat(src, (m) => (m.includes("mp4") ? "maybe" : ""))).toBe("a.m4a");
    expect(pickFormat(src, () => "")).toBeNull();
  });

  it("載入失敗靜默降級；成功的登記成音源；同區域不重載", async () => {
    const { engine, ctx } = setup();
    engine.unlock();
    const manifest = {
      cloud: [
        { id: "ok", track: "ambient" as const, src: { ogg: "ok.ogg" } },
        { id: "bad", track: "sfx" as const, src: { ogg: "bad.ogg" } },
      ],
    };
    let fetches = 0;
    const loader = new RegionLoader(engine, {
      manifest,
      canPlayType: () => "probably",
      fetchBytes: (url) => {
        fetches += 1;
        return url === "bad.ogg" ? Promise.reject(new Error("404")) : Promise.resolve(new ArrayBuffer(2000));
      },
    });
    expect(await loader.load("cloud")).toBe(1);
    expect(engine.hasSound("ok")).toBe(true);
    expect(engine.hasSound("bad")).toBe(false);
    expect(engine.play("bad")).toBe("silent");
    expect(engine.play("ok")).toBe("played");
    expect(await loader.load("cloud")).toBe(0);
    expect(fetches).toBe(2);
    ctx.failDecode = true;
    expect(await new RegionLoader(engine, { manifest: { x: [{ id: "y", track: "sfx", src: { ogg: "y" } }] }, canPlayType: () => "maybe", fetchBytes: () => Promise.resolve(new ArrayBuffer(1)) }).load("x")).toBe(0);
  });

  it("預設清單是空的：載入任何區域都不出錯", async () => {
    const { engine } = setup();
    const loader = new RegionLoader(engine, { canPlayType: () => "probably", fetchBytes: () => Promise.reject(new Error("no")) });
    expect(await loader.load("cloud_peaks")).toBe(0);
  });
});
