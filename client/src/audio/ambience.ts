// 環境音（AU-3；docs/art/音效與音樂方案.md 2.3 標 ○ 的五種：風、雨雷、火、鐘、打鐵）。
// - `ambienceFor(place)`：純函式，地點（區域、室內、設施、天氣）→ 場景：循環的底聲（bed）＋ 每隔一段時間一聲的點綴（accent）。
// - 地點只從現有的畫面資料讀（`worldPlace`：大世界的 `field`、`clock.weather_zh`；`battlePlace`：戰鬥的 `region`、`weather_id`、地形），
//   不新增伺服器欄位。
// - `AmbienceDirector`：大世界與戰鬥各自設定自己的場景，戰鬥優先（戰鬥結束回到大世界的場景）。底聲交給 `LoopDeck`，放在環境軌；
//   點綴的時間照「場景鍵:id:第幾次」的雜湊決定（不用 Math.random），計時器只負責「到點了」。
// - 減少刺耳音效開啟時，`harsh` 的（遠雷、打鐵）由引擎擋掉不出聲（AU-2）。
import type { BattleView, WorldView } from "../api/types";
import { variantHash } from "../render/attackVariants";
import { weatherMark } from "../world/hud";
import type { AudioEngine } from "./engine";
import type { LoopDeck } from "./loops";

export interface AmbiencePlace {
  region: string | null;
  interior: boolean;
  /** 這張地圖的設施種類（鐵匠鋪 `smithy`、酒館 `tavern`…）。 */
  facilities: readonly string[];
  rain: boolean;
  /** 戰場有岩漿（荒原的熔岩地形）。 */
  lava?: boolean;
}

export interface AmbienceBed {
  id: string;
  /** 線性音量。 */
  gain: number;
}

export interface AmbienceAccent {
  id: string;
  /** 平均間隔（毫秒）。 */
  everyMs: number;
  /** 前後抖動（毫秒；照雜湊）。 */
  jitterMs: number;
}

export interface AmbienceScene {
  /** 場景鍵（內容相同就相同；換場景時才重開）。 */
  key: string;
  beds: AmbienceBed[];
  accents: AmbienceAccent[];
}

export const AMBIENT_SOUNDS = ["amb_wind", "amb_wind_hot", "amb_rain", "amb_fire", "amb_bell", "amb_forge", "amb_thunder"] as const;

const SMITH = ["smithy", "enchanter"];
const HEARTH = ["tavern", "tavern_storyteller", "tavern_veteran"];

/** 室外各區的底聲與點綴。之後的三區（晶冠、魔導）先不出聲；霜潮用風。 */
const REGION_BEDS: Readonly<Record<string, AmbienceBed[]>> = {
  cloud_ridge: [{ id: "amb_wind", gain: 1 }],
  ashen_waste: [
    { id: "amb_wind_hot", gain: 1 },
    { id: "amb_fire", gain: 0.5 },
  ],
  frost_tide: [{ id: "amb_wind", gain: 1 }],
};

export const BELL: AmbienceAccent = { id: "amb_bell", everyMs: 24000, jitterMs: 6000 };
export const FORGE: AmbienceAccent = { id: "amb_forge", everyMs: 3600, jitterMs: 900 };
export const FORGE_FAR: AmbienceAccent = { id: "amb_forge", everyMs: 7000, jitterMs: 2000 };
export const THUNDER: AmbienceAccent = { id: "amb_thunder", everyMs: 22000, jitterMs: 8000 };

function keyOf(beds: readonly AmbienceBed[], accents: readonly AmbienceAccent[]): string {
  const b = beds.map((x) => `${x.id}@${x.gain}`).join("+");
  const a = accents.map((x) => `${x.id}/${x.everyMs}`).join("+");
  return b === "" && a === "" ? "quiet" : `${b}|${a}`;
}

function sceneOf(beds: AmbienceBed[], accents: AmbienceAccent[]): AmbienceScene {
  const bs = [...beds].sort((x, y) => (x.id < y.id ? -1 : x.id > y.id ? 1 : 0));
  const as = [...accents].sort((x, y) => (x.id < y.id ? -1 : x.id > y.id ? 1 : x.everyMs - y.everyMs));
  return { key: keyOf(bs, as), beds: bs, accents: as };
}

/**
 * 地點 → 場景（純函式）：
 * - 室內：鐵匠鋪、附魔台＝爐火＋打鐵；酒館＝爐火（小一點）；其他（導師殿、一般屋子）＝安靜。室內聽不到雨。
 * - 室外：雲嶺＝風；荒原＝熱風＋火；主城＝遠處鐘聲；街上有鐵匠鋪＝遠一點的打鐵；有岩漿＝火；雨天＝雨＋遠雷。
 */
export function ambienceFor(place: AmbiencePlace): AmbienceScene {
  const has = (kinds: readonly string[]) => place.facilities.some((f) => kinds.includes(f));
  if (place.interior) {
    if (has(SMITH)) return sceneOf([{ id: "amb_fire", gain: 0.8 }], [FORGE]);
    if (has(HEARTH)) return sceneOf([{ id: "amb_fire", gain: 0.55 }], []);
    return sceneOf([], []);
  }
  const beds = [...(place.region === null ? [] : (REGION_BEDS[place.region] ?? []))];
  const accents: AmbienceAccent[] = [];
  if (place.region === "capital") accents.push(BELL);
  if (has(SMITH)) accents.push(FORGE_FAR);
  if (place.lava === true && !beds.some((b) => b.id === "amb_fire")) beds.push({ id: "amb_fire", gain: 0.5 });
  if (place.rain) {
    beds.push({ id: "amb_rain", gain: 1 });
    accents.push(THUNDER);
  }
  return sceneOf(beds, accents);
}

/** 大世界的地點：所在的實地地圖（區域、室內、設施）＋ 天氣字（含「雨」）。沒有實地地圖時只看天氣。 */
export function worldPlace(view: Pick<WorldView, "field" | "clock">): AmbiencePlace {
  const f = view.field ?? null;
  return {
    region: f?.region ?? null,
    interior: f?.interior === true,
    facilities: (f?.facilities ?? []).map((x) => x.kind),
    rain: weatherMark(view.clock.weather_zh).icon === "rain",
  };
}

/** 戰鬥的地點：`region`、`weather_id`、有沒有岩漿格。戰場一律當室外。 */
export function battlePlace(view: Pick<BattleView, "region" | "weather_id" | "tiles">): AmbiencePlace {
  return {
    region: view.region ?? null,
    interior: false,
    facilities: [],
    rain: view.weather_id === "rain",
    lava: view.tiles.some((t) => t.terrain === "lava"),
  };
}

/** 第 `n` 次點綴距離上一次多久（毫秒）：第一次是半個間隔；之後一個間隔；都加上照雜湊的抖動。純函式。 */
export function accentDelay(sceneKey: string, a: AmbienceAccent, n: number): number {
  const base = n === 0 ? a.everyMs / 2 : a.everyMs;
  const span = 2 * a.jitterMs + 1;
  return Math.max(200, Math.round(base + (variantHash(`${sceneKey}:${a.id}:${n}`) % span) - a.jitterMs));
}

export type Owner = "world" | "battle";

export interface Timers {
  set(fn: () => void, ms: number): unknown;
  clear(handle: unknown): void;
}

const browserTimers: Timers = {
  set: (fn, ms) => window.setTimeout(fn, ms),
  clear: (h) => window.clearTimeout(h as number),
};

export class AmbienceDirector {
  private readonly owners = new Map<Owner, AmbienceScene | null>();
  private current: AmbienceScene | null = null;
  private handles: unknown[] = [];

  constructor(
    private readonly engine: AudioEngine,
    private readonly deck: LoopDeck,
    private readonly timers: Timers = browserTimers,
  ) {}

  /** 設定某一方的場景（`null`＝這一方沒有）。戰鬥優先於大世界。 */
  set(owner: Owner, scene: AmbienceScene | null): void {
    this.owners.set(owner, scene);
    this.apply();
  }

  /** 目前在放的場景（測試、開發頁用）。 */
  get scene(): AmbienceScene | null {
    return this.current;
  }

  private apply(): void {
    const next = this.owners.get("battle") ?? this.owners.get("world") ?? null;
    if ((next?.key ?? null) === (this.current?.key ?? null)) return;
    const old = this.current;
    this.current = next;
    for (const b of old?.beds ?? []) if (!(next?.beds ?? []).some((x) => x.id === b.id)) this.deck.set(`amb:${b.id}`, null);
    for (const b of next?.beds ?? []) this.deck.set(`amb:${b.id}`, { id: b.id, track: "ambient", gain: b.gain });
    for (const h of this.handles) this.timers.clear(h);
    this.handles = [];
    if (next === null) return;
    next.accents.forEach((a, i) => this.schedule(next, a, i, 0));
  }

  private schedule(scene: AmbienceScene, a: AmbienceAccent, slot: number, n: number): void {
    this.handles[slot] = this.timers.set(() => {
      if (this.current !== scene) return;
      this.engine.play(a.id, { track: "ambient", variantKey: `${scene.key}:${n}` });
      this.schedule(scene, a, slot, n + 1);
    }, accentDelay(scene.key, a, n));
  }
}
