// AU-3：戰鬥音效掛上 6N 時間軸、跳過不補放、加速不變調、同鍵同變體、打 5 人合併、腳步依地表、環境音依地點、減少刺耳音效。
import { describe, expect, it } from "vitest";
import type { BattleResponse, BattleView, Pos, SkillCard } from "../api/types";
import { playbackPlan, type Frame } from "../battle/playback";
import { tile, unit } from "../battle/testFixtures";
import type { WalkAnim } from "../battle/walkAnim";
import { advanceClock, type Freeze } from "../render/hitStop";
import { accentDelay, AmbienceDirector, ambienceFor, battlePlace, worldPlace, type AmbiencePlace, type Timers } from "./ambience";
import { burnLoopOn, cueRealMs, hitSfxOf, stepSfx, SWING_LEAD_MS, walkCues, windupSfx, type SfxCue } from "./battleSfx";
import { AudioEngine } from "./engine";
import { FakeAudioContext, FakeBufferSource, FakeNode, MemoryStorage } from "./fakeAudio";
import { stepSoundFor } from "./footsteps";
import { LoopDeck } from "./loops";
import { normalizeSettings, DEFAULT_AUDIO_SETTINGS } from "./settings";
import { makeLoopable, registerSfxLibrary, SFX_TABLE } from "./sfxLibrary";
import { CueScheduler, LOOKAHEAD_S, type PumpTimers } from "./sfxScheduler";
import { renderSfx, sfxSeed, type SfxDef } from "./synth";
import { GLOBAL_MAX, PER_ID_MAX } from "./voices";

const HERO = "unit_h";
const at = (x: number, y: number): Pos => ({ x, y });

function battleView(units: BattleView["units"], over: Partial<BattleView> = {}): BattleView {
  const tiles = [];
  for (let y = 0; y < 6; y++) for (let x = 0; x < 6; x++) tiles.push(tile(x, y, { terrain: x === 0 ? "grass" : "stone", surface: x === 5 ? "water" : "none" }));
  return {
    team: "ally",
    map_id: "m_test",
    map_name_zh: "測試",
    width: 6,
    height: 6,
    tiles,
    objects: [],
    units,
    traps: [],
    turn_order: units.map((u) => u.id),
    active_unit: HERO,
    round: 1,
    max_rounds: 30,
    weather_id: null,
    weather_name_zh: null,
    objective: { kind: "eliminate" },
    ended: false,
    winner: null,
    end_reason: null,
    pending: null,
    source_wells: [],
    zones: [],
    runes: [],
    summon_command_ap_cost: 1,
    summon_infuse_ap_cost: 1,
    ...over,
  } as unknown as BattleView;
}

const foes = (n: number) => Array.from({ length: n }, (_, i) => unit(`unit_f${i}`, "enemy", 3, i, { hp: 100, max_hp: 100 }));
const hero = unit(HERO, "ally", 2, 0, { hp: 100, max_hp: 100 });

function card(range: number, shape = "single", shapeZh = "單體"): SkillCard {
  return { id: "sk", shape: shapeZh, skeleton: "strike", effect_ids: ["damage"], icon: { segments: [{ skeleton: "strike", shape_id: shape, range, effects: [{ type: "damage" }] }] } } as unknown as SkillCard;
}

const used = (tiles: Pos[], seq = 1) => ({ seq, round: 1, type: "skill_used", unit_id: HERO, skill_id: "sk", tiles });
const dmg = (target: string, seq: number, element = "physical", amount = 30) => ({ seq, round: 1, type: "damage_dealt", target_id: target, source_id: HERO, element, amount, hp_before: 100, hp_after: 100 - amount, crit: false });

function response(events: Record<string, unknown>[], v: BattleView): BattleResponse {
  return { battle_id: "b", hero_id: HERO, initial_view: v, view: v, steps: [{ actor_id: HERO, events, view: v, step: { type: "use_skill" } }] } as unknown as BattleResponse;
}

function frameOf(events: Record<string, unknown>[], v: BattleView, weapon = "blade", cards: Record<string, SkillCard> = { sk: card(1) }, speed: "normal" | "fast" | "skip" = "normal"): Frame {
  const plan = playbackPlan(response(events, v), HERO, speed, cards, new Set(), () => weapon as never, () => null);
  return plan.frames[0] as Frame;
}

const cue = (f: Frame, id: string): SfxCue | undefined => f.sfx?.find((c) => c.id === id);

function setupEngine(settings = DEFAULT_AUDIO_SETTINGS) {
  const ctx = new FakeAudioContext();
  const engine = new AudioEngine({ createContext: () => ctx, storage: new MemoryStorage(), settings: normalizeSettings(settings) });
  registerSfxLibrary(engine);
  engine.unlock();
  return { ctx, engine };
}

/** 手動推進的計時器（排程測試用）。 */
function manualTimers(): PumpTimers & { run(): void; pending: number } {
  let fns: Array<() => void> = [];
  return {
    set(fn) {
      fns.push(fn);
      return fns.length;
    },
    clear() {
      fns = [];
    },
    run() {
      const now = fns;
      fns = [];
      for (const f of now) f();
    },
    get pending() {
      return fns.length;
    },
  };
}

const bufferStarts = (ctx: FakeAudioContext) => ctx.starts.filter((s) => s.node instanceof FakeBufferSource);

// ---------------------------------------------------------------------------------------------

describe("時間點對齊 6N 時間軸", () => {
  it("近身：咻在命中點前 60 ms，命中聲在命中點（＝出招片段的 hitAt）", () => {
    const v = battleView([hero, ...foes(1)]);
    const f = frameOf([used([at(3, 0)]), dmg("unit_f0", 2)], v);
    const strike = f.skill?.find((r) => r.strike);
    expect(strike?.hitMs).not.toBeNull();
    const hitMs = strike?.hitMs as number;
    expect(cue(f, "swing_slash")?.atMs).toBe(Math.round(hitMs - SWING_LEAD_MS));
    expect(cue(f, "hit_blunt")?.atMs).toBe(Math.round(hitMs));
    // 命中聲＝受擊反應的時間（畫面白閃的那一刻）
    expect(f.vfx?.reactions?.length).toBeGreaterThan(0);
    expect(f.vfx?.reactions?.[0]?.atMs).toBe(cue(f, "hit_blunt")?.atMs);
  });

  it("起手：技能的蓄力音在起手片段開始；元素命中依元素", () => {
    const v = battleView([hero, ...foes(1)]);
    const f = frameOf([used([at(3, 0)]), dmg("unit_f0", 2, "fire")], v);
    const windup = f.skill?.find((r) => !r.strike && !r.recover && r.startMs < (f.skill?.find((s) => s.strike)?.startMs ?? 0));
    expect(windup).toBeDefined();
    expect(cue(f, "windup_charge")?.atMs).toBe(windup?.startMs);
    expect(cue(f, "elem_fire")).toBeDefined();
    expect(cue(f, "hit_blunt")).toBeUndefined();
  });

  it("弓：拉弓在起手、放箭在放出那一刻（出招的 hitAt），命中在箭到的時候", () => {
    const v = battleView([unit(HERO, "ally", 0, 0, { hp: 100, max_hp: 100 }), unit("unit_f0", "enemy", 4, 0, { hp: 100, max_hp: 100 })]);
    const f = frameOf([used([at(4, 0)]), dmg("unit_f0", 2)], v, "bow", { sk: card(5) });
    const strike = f.skill?.find((r) => r.strike);
    expect(cue(f, "windup_bow_draw")).toBeDefined();
    expect(cue(f, "release_bow")?.atMs).toBe(Math.round(strike?.hitMs as number));
    expect((cue(f, "hit_blunt")?.atMs ?? 0) > (cue(f, "release_bow")?.atMs ?? 0)).toBe(true);
  });

  it("起手音的對照：法杖遠程＝詠唱、魔導劍遠程＝畫符、火槍＝上膛、近身普攻不出聲", () => {
    expect(windupSfx({ weapon: "staff", mode: "ranged", basic: false })).toBe("windup_chant");
    expect(windupSfx({ weapon: "arcane", mode: "ranged", basic: false })).toBe("windup_sigil");
    expect(windupSfx({ weapon: "gun", mode: "ranged", basic: true })).toBe("windup_reload");
    expect(windupSfx({ weapon: "blade", mode: "melee", basic: true })).toBeNull();
    expect(hitSfxOf("shadow")).toBe("elem_dark");
    expect(hitSfxOf("support")).toBe("hit_magic");
  });

  it("停頓、最後一擊放慢：音效的實際時間和效果時鐘（advanceClock）走到那一刻的時間一樣", () => {
    const vfx = { stops: [{ atMs: 300, ms: 100 }], slow: { atMs: 300, fromMs: 180, toMs: 580, rampMs: 60, rate: 0.4, reason: "last" as const, unitId: "x" } };
    for (const t of [100, 250, 300, 301, 450, 700]) {
      // 模擬繪製器：每 1 ms 走一次效果時鐘，記下到達 t 的實際時間
      const freezes: Freeze[] = vfx.stops.map((s) => ({ at: s.atMs, left: s.ms }));
      let clock = 0;
      let real = 0;
      while (clock < t - 1e-6) {
        clock = advanceClock(clock, 1, freezes, [vfx.slow]);
        real += 1;
      }
      expect(Math.abs(cueRealMs(t, vfx, false) - real), `t=${t}`).toBeLessThanOrEqual(2);
    }
    expect(cueRealMs(300, vfx, false)).toBeLessThan(cueRealMs(301, vfx, false) - 90); // 命中聲在停住那一刻，停頓之後的聲音往後推
    expect(cueRealMs(450, vfx, true)).toBe(450); // 減少動態：繪製器不停頓不放慢，聲音也不等
  });

  it("快速播放：時間跟著縮放一半", () => {
    const v = battleView([hero, ...foes(1)]);
    const events = [used([at(3, 0)]), dmg("unit_f0", 2)];
    const n = frameOf(events, v, "blade", { sk: card(1) }, "normal");
    const fast = frameOf(events, v, "blade", { sk: card(1) }, "fast");
    expect(cue(fast, "hit_blunt")?.atMs).toBe(Math.round((cue(n, "hit_blunt")?.atMs ?? 0) * 0.5));
  });
});

describe("跳過時不放音", () => {
  it("略過的播放計畫沒有任何音效", () => {
    const v = battleView([hero, ...foes(1)]);
    const f = frameOf([used([at(3, 0)]), dmg("unit_f0", 2)], v, "blade", { sk: card(1) }, "skip");
    expect(f.sfx).toBeUndefined();
    expect(f.viewSfx).toBeUndefined();
  });

  it("播放中按跳過：排好還沒響的全部取消，之後不補放", () => {
    const { ctx, engine } = setupEngine();
    const timers = manualTimers();
    const s = new CueScheduler(engine, timers);
    s.start([
      { id: "swing_slash", realMs: 50, key: "a", count: 1 },
      { id: "hit_blunt", realMs: 110, key: "a", count: 1 },
      { id: "res_kill", realMs: 900, key: "a", count: 1 },
    ]);
    expect(bufferStarts(ctx).length).toBe(2); // 120 ms 內的先交給引擎
    expect(engine.activeVoices()).toBe(2);
    s.cancelAll();
    expect(engine.activeVoices()).toBe(0);
    // 被取消的聲音的 gain 斷開：排好的取樣不會接到輸出
    const voiceGains = ctx.created.filter((n) => n.kind === "gain" && (n as FakeNode).outputs.length === 0);
    expect(voiceGains.length).toBeGreaterThanOrEqual(2);
    ctx.currentTime = 1;
    timers.run();
    expect(bufferStarts(ctx).length).toBe(2);
    expect(s.waiting).toBe(0);
  });
});

describe("按住 2 倍速：排程縮短，playbackRate 不變", () => {
  it("同一批音效在 2 倍速下時間減半，所有取樣的 playbackRate 都是 1", () => {
    const run = (boost: number) => {
      const { ctx, engine } = setupEngine();
      const timers = manualTimers();
      const s = new CueScheduler(engine, timers);
      s.setBoost(boost);
      s.start([
        { id: "swing_slash", realMs: 200, key: "k", count: 1 },
        { id: "hit_blunt", realMs: 400, key: "k", count: 1 },
      ]);
      for (let t = 0; t < 1; t += 0.03) {
        ctx.currentTime = t;
        timers.run();
      }
      const starts = bufferStarts(ctx).map((x) => x.at);
      const rates = ctx.created.filter((n): n is FakeBufferSource => n instanceof FakeBufferSource).map((n) => n.playbackRate.value);
      return { starts, rates };
    };
    const normal = run(1);
    const boosted = run(2);
    expect(normal.starts.length).toBe(2);
    expect(boosted.starts.length).toBe(2);
    normal.starts.forEach((t, i) => expect(boosted.starts[i]).toBeCloseTo(t / 2, 6));
    expect([...normal.rates, ...boosted.rates].every((r) => r === 1)).toBe(true);
  });

  it("播放中途按住加速：還沒響的照新倍率提早（已交給引擎的取消重排）", () => {
    const { ctx, engine } = setupEngine();
    const timers = manualTimers();
    const s = new CueScheduler(engine, timers);
    s.start([{ id: "hit_blunt", realMs: 100, key: "k", count: 1 }, { id: "res_kill", realMs: 600, key: "k", count: 1 }]);
    expect(bufferStarts(ctx)[0]?.at).toBeCloseTo(0.1, 6);
    ctx.currentTime = 0.05;
    s.setBoost(2);
    // 0.05 秒時進度 50 ms；剩下 50 ms → 2 倍速 25 ms；600 ms → (600-50)/2
    expect(bufferStarts(ctx).at(-1)?.at).toBeCloseTo(0.075, 6);
    for (let t = 0.05; t < 0.5; t += 0.03) {
      ctx.currentTime = t;
      timers.run();
    }
    expect(bufferStarts(ctx).at(-1)?.at).toBeCloseTo(0.05 + 0.55 / 2, 6);
    expect(LOOKAHEAD_S).toBeLessThanOrEqual(0.15);
  });
});

describe("同一個鍵挑到同一個變體", () => {
  it("同一場同一步：音效清單（含變體鍵）完全相同；鍵和動畫同一把", () => {
    const v = battleView([hero, ...foes(1)]);
    const events = [used([at(3, 0)]), dmg("unit_f0", 2)];
    const a = frameOf(events, v).sfx;
    const b = frameOf(events, v).sfx;
    expect(a).toEqual(b);
    expect(cue(frameOf(events, v), "swing_slash")?.key).toBe("m_test:1:unit_h:skill:sk"); // = skillVariantKey
    expect(cue(frameOf(events, v), "hit_blunt")?.key).toBe("m_test:2:unit_f0:hit"); // = reactVariantKey
    const other = frameOf([used([at(3, 0)], 7), dmg("unit_f0", 8)], v);
    expect(cue(other, "swing_slash")?.key).not.toBe(cue(frameOf(events, v), "swing_slash")?.key);
  });

  it("同鍵同波形、不同鍵不同波形（變體由鍵的雜湊決定）", () => {
    const def = SFX_TABLE.defs.step_grass as SfxDef;
    const r = (key: string) => renderSfx(def, { sampleRate: 8000, seed: sfxSeed("step_grass", key) });
    expect(r("m:1,1:0")).toEqual(r("m:1,1:0"));
    expect(r("m:1,1:0")).not.toEqual(r("m:1,1:1"));
  });
});

describe("一次打 5 人：合併，不超過上限", () => {
  it("同一刻同一個命中聲合併成一筆（次數 5），引擎只放一聲、其餘合併", () => {
    const v = battleView([hero, ...foes(5)]);
    const tiles = [0, 1, 2, 3, 4].map((y) => at(3, y));
    const events = [used(tiles), ...[0, 1, 2, 3, 4].map((i) => dmg(`unit_f${i}`, 2 + i))];
    const f = frameOf(events, v, "blade", { sk: card(1, "line", "直線") });
    const hits = (f.sfx ?? []).filter((c) => c.id === "hit_blunt");
    expect(hits.length).toBe(1);
    expect(hits[0]?.count).toBe(5);
    const { ctx, engine } = setupEngine();
    const s = new CueScheduler(engine, manualTimers());
    s.start((f.sfx ?? []).map((c) => ({ id: c.id, realMs: c.atMs, key: c.key, count: c.count })));
    ctx.currentTime = 0;
    for (let t = 0; t < 3; t += 0.03) {
      ctx.currentTime = t;
      s.pump();
      expect(engine.activeVoices("hit_blunt")).toBeLessThanOrEqual(PER_ID_MAX);
      expect(engine.activeVoices()).toBeLessThanOrEqual(GLOBAL_MAX);
    }
    const hitBuffers = bufferStarts(ctx).length;
    expect(hitBuffers).toBe((f.sfx ?? []).length); // 每個不同的聲音只建立一個取樣節點
  });
});

describe("腳步聲依地表", () => {
  it("表面優先、室內地板、荒原的土是沙", () => {
    expect(stepSoundFor({ terrain: "grass", surface: "water" })).toBe("step_water");
    expect(stepSoundFor({ terrain: "stone", surface: "ice" })).toBe("step_ice");
    expect(stepSoundFor({ terrain: "grass", surface: "none" })).toBe("step_grass");
    expect(stepSoundFor({ terrain: "stone" })).toBe("step_stone");
    expect(stepSoundFor({ terrain: "dirt" }, { region: "ashen_waste" })).toBe("step_sand");
    expect(stepSoundFor({ terrain: "dirt" }, { region: "cloud_ridge" })).toBe("step_dirt");
    expect(stepSoundFor({ terrain: "stone" }, { floor: "plank" })).toBe("step_wood");
    expect(stepSoundFor(null)).toBe("step_dirt");
  });

  it("戰鬥中一格一格走：每格開始踏一步，照那一格的地表；踩到陷阱放夾住", () => {
    const v = battleView([hero]);
    const walk: WalkAnim = {
      unitId: HERO,
      pieces: [
        { kind: "leg", from: at(1, 0), to: at(0, 0), facing: "west", durationMs: 120 },
        { kind: "leg", from: at(0, 0), to: at(0, 1), facing: "south", durationMs: 120 },
        { kind: "beat", beat: "trap", pos: at(0, 1), holdMs: 400, fxMs: 600, feedback: [], feedbackMs: 0 },
        { kind: "leg", from: at(4, 1), to: at(5, 1), facing: "east", durationMs: 120 },
      ],
    };
    const cues = walkCues(walk, v);
    expect(cues.map((c) => [c.id, c.atMs])).toEqual([
      ["step_grass", 0],
      ["step_grass", 120],
      ["surface_trap", 240],
      ["step_water", 640],
    ]);
  });
});

describe("環境音依區域、天氣、室內挑選", () => {
  const place = (o: Partial<AmbiencePlace>): AmbiencePlace => ({ region: null, interior: false, facilities: [], rain: false, ...o });
  const beds = (p: AmbiencePlace) => ambienceFor(p).beds.map((b) => b.id);
  const accents = (p: AmbiencePlace) => ambienceFor(p).accents.map((a) => a.id);

  it("雲嶺有風；荒原有熱風加火；主城有鐘；雨天有雨和遠雷", () => {
    expect(beds(place({ region: "cloud_ridge" }))).toEqual(["amb_wind"]);
    expect(beds(place({ region: "ashen_waste" }))).toEqual(["amb_fire", "amb_wind_hot"]);
    expect(accents(place({ region: "capital" }))).toEqual(["amb_bell"]);
    expect(beds(place({ region: "cloud_ridge", rain: true }))).toEqual(["amb_rain", "amb_wind"]);
    expect(accents(place({ region: "cloud_ridge", rain: true }))).toEqual(["amb_thunder"]);
  });

  it("室內：鐵匠鋪＝爐火＋打鐵；酒館＝爐火；其他安靜；室內聽不到雨", () => {
    expect(beds(place({ interior: true, facilities: ["smithy"], rain: true }))).toEqual(["amb_fire"]);
    expect(accents(place({ interior: true, facilities: ["smithy"] }))).toEqual(["amb_forge"]);
    expect(beds(place({ interior: true, facilities: ["tavern"] }))).toEqual(["amb_fire"]);
    const quiet = ambienceFor(place({ region: "cloud_ridge", interior: true, facilities: ["mentor"], rain: true }));
    expect(quiet.beds).toEqual([]);
    expect(quiet.accents).toEqual([]);
    expect(quiet.key).toBe("quiet");
  });

  it("地點從現有畫面資料讀：大世界的 field 與天氣字、戰鬥的 region／weather_id／岩漿", () => {
    const w = worldPlace({ field: { region: "cloud_ridge", interior: false, facilities: [{ kind: "smithy", x: 1, y: 1 }] }, clock: { weather_zh: "下雨" } } as never);
    expect(w).toEqual({ region: "cloud_ridge", interior: false, facilities: ["smithy"], rain: true });
    expect(worldPlace({ field: null, clock: { weather_zh: "晴朗" } } as never).rain).toBe(false);
    const b = battlePlace({ region: "ashen_waste", weather_id: "rain", tiles: [tile(0, 0, { terrain: "lava" })] });
    expect(b).toEqual({ region: "ashen_waste", interior: false, facilities: [], rain: true, lava: true });
    expect(beds(battlePlace({ region: null, weather_id: null, tiles: [tile(0, 0, { terrain: "lava" })] }))).toEqual(["amb_fire"]);
  });

  it("場景鍵只看內容；點綴的間隔照雜湊（同輸入同結果）", () => {
    expect(ambienceFor(place({ region: "cloud_ridge" })).key).toBe(ambienceFor(place({ region: "cloud_ridge" })).key);
    const a = ambienceFor(place({ region: "capital" }));
    const acc = a.accents[0]!;
    expect(accentDelay(a.key, acc, 3)).toBe(accentDelay(a.key, acc, 3));
    for (let n = 0; n < 20; n++) {
      const d = accentDelay(a.key, acc, n);
      const base = n === 0 ? acc.everyMs / 2 : acc.everyMs;
      expect(Math.abs(d - base)).toBeLessThanOrEqual(acc.jitterMs);
    }
  });

  it("導演：底聲放在環境軌、戰鬥優先於大世界、戰鬥結束回到大世界", () => {
    const { ctx, engine } = setupEngine();
    const deck = new LoopDeck(engine);
    const timers: Timers & { fns: Array<() => void> } = { fns: [], set(fn) { this.fns.push(fn); return this.fns.length; }, clear() {} };
    const d = new AmbienceDirector(engine, deck, timers);
    d.set("world", ambienceFor(place({ region: "cloud_ridge" })));
    expect(deck.playing()).toEqual(["amb:amb_wind"]);
    const loop = ctx.created.filter((n): n is FakeBufferSource => n instanceof FakeBufferSource).at(-1);
    expect(loop?.loop).toBe(true);
    // 接到環境軌：聲音 gain → 環境軌 gain
    const ambientTrack = engine.nodes!.tracks.ambient;
    expect(ctx.created.some((n) => n.kind === "gain" && (n as FakeNode).outputs.includes(ambientTrack))).toBe(true);
    d.set("battle", ambienceFor(place({ region: "ashen_waste" })));
    expect(deck.playing()).toEqual(["amb:amb_fire", "amb:amb_wind_hot"]);
    d.set("battle", null);
    expect(deck.playing()).toEqual(["amb:amb_wind"]);
  });
});

describe("減少刺耳音效：harsh 的不放", () => {
  it("遠雷、打鐵（環境軌 harsh）不出聲；風、雨照常；關掉後打鐵照常", () => {
    const { engine } = setupEngine({ ...DEFAULT_AUDIO_SETTINGS, reduceHarsh: true });
    expect(SFX_TABLE.defs.amb_forge?.harsh).toBe(true);
    expect(engine.play("amb_thunder")).toBe("silent");
    expect(engine.play("amb_forge")).toBe("silent");
    expect(engine.startLoop("amb_rain")).not.toBeNull();
    engine.setSettings({ reduceHarsh: false });
    expect(engine.play("amb_forge")).toBe("played");
  });

  it("導演的點綴走引擎：雨天的遠雷在減少刺耳音效開著時不出聲", () => {
    const { ctx, engine } = setupEngine({ ...DEFAULT_AUDIO_SETTINGS, reduceHarsh: true });
    const deck = new LoopDeck(engine);
    const fns: Array<() => void> = [];
    const d = new AmbienceDirector(engine, deck, { set: (fn) => fns.push(fn), clear: () => undefined });
    d.set("world", ambienceFor({ region: "cloud_ridge", interior: false, facilities: [], rain: true }));
    const before = bufferStarts(ctx).length;
    fns.shift()?.(); // 第一次遠雷到點
    expect(bufferStarts(ctx).length).toBe(before);
    expect(deck.playing()).toEqual(["amb:amb_rain", "amb:amb_wind"]);
  });
});

describe("循環音", () => {
  it("解鎖前不出聲，解鎖後才開始；同一個槽設兩次只有一條", () => {
    const ctx = new FakeAudioContext();
    const engine = new AudioEngine({ createContext: () => ctx, storage: new MemoryStorage(), settings: normalizeSettings(DEFAULT_AUDIO_SETTINGS) });
    registerSfxLibrary(engine);
    const deck = new LoopDeck(engine);
    deck.set("status:burn", { id: "status_burn", track: "sfx" });
    expect(deck.playing()).toEqual([]);
    engine.unlock();
    expect(deck.playing()).toEqual(["status:burn"]);
    deck.set("status:burn", { id: "status_burn", track: "sfx" });
    expect(ctx.created.filter((n) => n instanceof FakeBufferSource).length).toBe(1);
    deck.set("status:burn", null);
    expect(deck.playing()).toEqual([]);
    expect((ctx.created.find((n) => n instanceof FakeBufferSource) as FakeBufferSource).stoppedAt).not.toBeNull();
  });

  it("燃燒：全場有任何人燃燒就開（一條），倒下的不算", () => {
    const burning = unit("a", "enemy", 0, 0, { statuses: [{ status_id: "burning" }] as never });
    const v = (units: BattleView["units"]) => ({ units });
    expect(burnLoopOn(v([burning, unit("b", "enemy", 1, 0, { statuses: [{ status_id: "burning" }] as never })]))).toBe(true);
    expect(burnLoopOn(v([unit("c", "enemy", 0, 0)]))).toBe(false);
    expect(burnLoopOn(v([{ ...burning, downed: true }]))).toBe(false);
  });

  it("循環接縫：結尾接回開頭是連續的取樣（沒有喀聲）", () => {
    const def = SFX_TABLE.defs.amb_wind as SfxDef;
    const raw = renderSfx(def, { sampleRate: 8000, seed: sfxSeed("amb_wind") });
    const loop = makeLoopable(raw, 8000);
    expect(loop.length).toBe(raw.length - 4000);
    // 結尾 → 開頭 ＝ 原本的 raw[n-1] → raw[n]
    expect(loop[0]).toBeCloseTo(raw[loop.length] as number, 6);
    expect(loop[loop.length - 1]).toBeCloseTo(raw[loop.length - 1] as number, 6);
  });
});

describe("事件 → 音效（狀態、地表、回合）", () => {
  it("狀態上身跟著命中點；冰凍、暈眩各有聲音；燃燒不放一次性的聲音", () => {
    const v = battleView([hero, ...foes(1)]);
    const out = stepSfx({
      events: [used([at(3, 0)]), dmg("unit_f0", 2), { seq: 3, round: 1, type: "status_applied", target_id: "unit_f0", status_id: "frozen" }, { seq: 4, round: 1, type: "status_applied", target_id: "unit_f0", status_id: "burning" }],
      before: v,
      after: v,
      vfx: frameOf([used([at(3, 0)]), dmg("unit_f0", 2)], v).vfx,
    });
    const ids = out.vfx.map((c) => c.id);
    expect(ids).toContain("status_freeze");
    expect(ids).not.toContain("status_burn");
  });

  it("沒有特效的步驟：回合開始在畫面更新時放", () => {
    const v = battleView([hero]);
    const out = stepSfx({ events: [{ seq: 1, round: 2, type: "round_started" }], before: v, after: v, vfx: null });
    expect(out.view.map((c) => c.id)).toEqual(["sys_round_start"]);
    expect(out.vfx).toEqual([]);
  });
});
