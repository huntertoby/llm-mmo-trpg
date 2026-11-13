// Phase 6C-ART2：事件插圖 10 種（場景挑法、背景依區域、繪圖確定性、快取、事件卡退回）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { WorldEventView } from "../api/types";
import { EventCard } from "../world/EventCard";
import * as capital from "./eventArtCapital";
import * as parts from "./eventArtParts";
import { T } from "./eventArtParts";
import {
  drawEventArt,
  EVENT_ART_H,
  ALTAR_GLOW,
  EVENT_ART_BGS,
  EVENT_ART_IDS,
  EVENT_ART_W,
  eventArtBg,
  eventArtCacheSize,
  eventArtScene,
  eventArtUrl,
  FALLBACK_ART,
  ICON_ART,
  SCENES,
  type EventArtBg,
  type EventArtId,
} from "./eventArt";
import { setDollSkin } from "./inkStyle";
import { setQCanvasFactory } from "./qIcon/core";
import { fakeCanvasFactory } from "../test/fakeCanvas";
import { afterEach as afterEachQ } from "vitest";

afterEachQ(() => setDollSkin("q"));

/** 記錄所有呼叫的假 Canvas 2D（漸層記下色標，量字寬回傳字數×13）。 */
function mockCtx(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const fmt = (a: unknown): string => (typeof a === "number" ? a.toFixed(3) : typeof a === "string" ? a : typeof a);
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map(fmt).join(",")})`);
        if (prop === "createRadialGradient" || prop === "createLinearGradient") return { addColorStop: (o: number, c: string) => calls.push(`stop(${fmt(o)},${c})`) };
        if (prop === "measureText") return { width: String(args[0]).length * 13 };
        return undefined;
      };
    },
    set(target, prop: string, value) {
      target[prop] = value;
      calls.push(`${prop}=${String(value)}`);
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  return { ctx, calls };
}

const record = (scene: EventArtId, bg: EventArtBg): string[] => {
  const { ctx, calls } = mockCtx();
  drawEventArt(ctx, scene, bg);
  return calls;
};

type Sol = WorldEventView["solutions"][number];
function sol(kind: string, note = "", attrs = ""): Sol {
  return { index: 0, kind, note_zh: note, attributes_zh: attrs, available: true, cost_supplies: 0 } as unknown as Sol;
}

function event(over: Partial<WorldEventView> = {}): WorldEventView {
  return {
    skeleton: "lost_acolyte",
    location_name_zh: "雨梯田",
    actor_zh: "迷路的道童",
    motive_zh: "回青霧觀",
    story: null,
    who_zh: "",
    want_zh: "",
    obstacle_zh: "",
    stakes_zh: "",
    solutions: [sol("situation", "認路", "感知"), { ...sol("combat"), index: 1 }],
    leave_zh: "離開這裡，事件就作罷",
    art_url: null,
    ...over,
  };
}

const card = (e: WorldEventView): string => renderToStaticMarkup(createElement(EventCard, { event: e, busy: false, onOpen: () => undefined, onSolve: () => undefined, onAnswer: () => undefined }));

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("場景 ID 與挑法（需求第 3 節第 2、4 點）", () => {
  it("十種場景，順序同樣張；每種都有小牌文字與圖示", () => {
    expect(EVENT_ART_IDS).toEqual(["ambush", "chest", "stele", "altar", "villager", "caravan", "trap", "camp", "anomaly", "friend"]);
    expect(Object.keys(SCENES).sort()).toEqual([...EVENT_ART_IDS].sort());
    expect(SCENES.anomaly.zh).toBe("異象・源晶裂痕");
  });

  it("有 art 用它；不認得的值退回古碑", () => {
    for (const id of EVENT_ART_IDS) expect(eventArtScene(event({ art: id }))).toBe(id);
    expect(eventArtScene(event({ art: "dragon" }))).toBe("stele");
    expect(FALLBACK_ART).toBe("stele");
  });

  it("沒寫 art：照第一個不是放棄的選項的圖示挑", () => {
    const pick = (...solutions: Sol[]): EventArtId => eventArtScene(event({ art: null, solutions }));
    expect(pick(sol("abandon"), sol("combat"))).toBe("ambush");
    expect(pick(sol("parley", "付錢"))).toBe("caravan");
    expect(pick(sol("opportunity", "帶技能靠近"))).toBe("altar");
    expect(pick(sol("situation", "說服一方", "意志"))).toBe("villager");
    expect(pick(sol("situation", "潛行", "敏捷"))).toBe("ambush");
    expect(pick(sol("situation", "看穿誰在說謊", "感知"))).toBe("stele");
    expect(pick(sol("situation", "攀爬", "力量"))).toBe("trap");
    expect(pick(sol("abandon"))).toBe("camp");
    expect(ICON_ART).toEqual({ combat: "ambush", persuade: "villager", sneak: "ambush", investigate: "stele", force: "trap", chance: "altar", trade: "caravan", leave: "camp" });
  });

  it("背景依區域（RT-2）：荒原用荒原、主城用主城、雲嶺和其他區用雲嶺", () => {
    expect(eventArtBg("ashen_waste")).toBe("ashen");
    expect(eventArtBg("cloud_ridge")).toBe("cloud");
    expect(eventArtBg("capital")).toBe("capital");
    for (const r of ["crystal_crown", "arcane_hub", "frost_tide", "somewhere"]) expect(eventArtBg(r)).toBe("cloud");
  });
});

describe("繪圖（364×156、確定性）", () => {
  it("大小是 7×3 格", () => {
    expect([EVENT_ART_W, EVENT_ART_H]).toEqual([364, 156]);
  });

  it("同一場景每次畫出來都一樣，不用亂數", () => {
    const random = vi.spyOn(Math, "random");
    for (const bg of EVENT_ART_BGS) {
      for (const id of EVENT_ART_IDS) {
        const a = record(id, bg);
        expect(a.length).toBeGreaterThan(100);
        expect(record(id, bg)).toEqual(a);
      }
    }
    expect(random).not.toHaveBeenCalled();
  });

  it("十種場景畫法彼此不同；荒原換背景", () => {
    const cloud = EVENT_ART_IDS.map((id) => record(id, "cloud").join("\n"));
    expect(new Set(cloud).size).toBe(10);
    for (const id of EVENT_ART_IDS) expect(record(id, "ashen")).not.toEqual(record(id, "cloud"));
  });

  it("主城版 10 種都有，彼此不同，也和雲嶺、荒原不同（RT-2）", () => {
    const capital = EVENT_ART_IDS.map((id) => record(id, "capital").join("\n"));
    expect(new Set(capital).size).toBe(10);
    for (const id of EVENT_ART_IDS) {
      expect(record(id, "capital")).not.toEqual(record(id, "cloud"));
      expect(record(id, "capital")).not.toEqual(record(id, "ashen"));
    }
  });

  it("小牌寫場景名；荒原祭壇是紅光、雲嶺是暖黃光", () => {
    expect(record("caravan", "cloud")).toContain("fillText(商隊,32.000,21.000)");
    expect(record("altar", "ashen").join("\n")).toContain("rgba(255,90,60,0.9)");
    expect(record("altar", "cloud").join("\n")).toContain("rgba(255,220,140,0.9)");
  });
});

describe("RT-2：主城背景與荒原火盆", () => {
  const spyParts = () => ({
    bamboo: vi.spyOn(parts, "bambooGrove"),
    pine: vi.spyOn(parts, "pine"),
    grass: vi.spyOn(parts, "ground"),
    mist: vi.spyOn(parts, "mistWisp"),
    lantern: vi.spyOn(parts, "stoneLantern"),
    brazier: vi.spyOn(parts, "hornBrazier"),
    capitalTile: vi.spyOn(capital, "capitalTile"),
    backdrop: vi.spyOn(capital, "capitalBackdrop"),
  });

  it("主城的事件 10 種都不會畫竹林、松樹、草地、霧、石燈籠（只畫主城石板與點綴）", () => {
    const s = spyParts();
    for (const id of EVENT_ART_IDS) {
      const e = event({ art: id, region: "capital" });
      drawEventArt(mockCtx().ctx, eventArtScene(e), eventArtBg(e.region));
    }
    expect(s.bamboo).not.toHaveBeenCalled();
    expect(s.pine).not.toHaveBeenCalled();
    expect(s.grass).not.toHaveBeenCalled();
    expect(s.mist).not.toHaveBeenCalled();
    expect(s.lantern).not.toHaveBeenCalled();
    expect(s.capitalTile).toHaveBeenCalledTimes(10 * 7 * 3);
    expect(s.backdrop).toHaveBeenCalledTimes(10);
  });

  it("雲嶺的伏擊仍有竹林（對照組）", () => {
    const s = spyParts();
    drawEventArt(mockCtx().ctx, "ambush", eventArtBg("cloud_ridge"));
    expect(s.bamboo).toHaveBeenCalledTimes(2);
    expect(s.capitalTile).not.toHaveBeenCalled();
  });

  it("荒原祭壇是兩座角魔火盆、位置同原本的燈籠；雲嶺祭壇保留石燈籠", () => {
    const s = spyParts();
    drawEventArt(mockCtx().ctx, "altar", eventArtBg("ashen_waste"));
    expect(s.lantern).not.toHaveBeenCalled();
    expect(s.brazier.mock.calls.map((c) => [c[1], c[2]])).toEqual([
      [1.6 * T, 0.6 * T],
      [4.4 * T, 0.6 * T],
    ]);
    s.brazier.mockClear();
    drawEventArt(mockCtx().ctx, "altar", eventArtBg("cloud_ridge"));
    expect(s.brazier).not.toHaveBeenCalled();
    expect(s.lantern.mock.calls.map((c) => [c[1], c[2]])).toEqual([
      [1.6 * T, 0.6 * T],
      [4.4 * T, 0.6 * T],
    ]);
  });

  it("火盆有火焰與橘色火光暈", () => {
    const { ctx, calls } = mockCtx();
    parts.hornBrazier(ctx, 0, 0);
    const out = calls.join("\n");
    expect(out).toContain("rgba(255,120,40,0.9)");
    expect(out).toContain("fillStyle=#ff8a1e");
  });

  it("主城祭壇是紫晶光", () => {
    expect(ALTAR_GLOW.capital).toBe("rgba(170,150,255,0.9)");
    expect(record("altar", "capital").join("\n")).toContain("rgba(170,150,255,0.9)");
  });

  it("沒有區域時退回主城（hub）版本", () => {
    expect(eventArtBg(null)).toBe("capital");
    expect(eventArtBg(undefined)).toBe("capital");
    expect(eventArtBg("")).toBe("capital");
    expect(eventArtBg("hub")).toBe("capital");
    const out = card(event({ art: "ambush", region: null }));
    expect(out).toContain('data-bg="capital"');
    expect(out).toContain('data-scene="ambush"');
  });
});

describe("快取（依場景、背景）", () => {
  it("沒有 DOM 時為 null", () => {
    expect(eventArtUrl("chest", "cloud")).toBeNull();
  });

  it("同一場景與背景只畫一次", () => {
    setDollSkin("c"); // QK-1：這一項數 C 畫法的畫布指令（Q 版的外框另開離屏畫布），鎖 C；afterEach 換回 Q
    let made = 0;
    const fake = {
      createElement: () => {
        made += 1;
        return { width: 0, height: 0, getContext: () => mockCtx().ctx, toDataURL: () => `data:image/png;base64,${made}` };
      },
    };
    vi.stubGlobal("document", fake);
    setQCanvasFactory(fakeCanvasFactory({ calls: null })); // QI-6：小牌、泡泡的 Q 版圖樣另建畫布，不算進插圖的畫布數
    const before = eventArtCacheSize();
    const a = eventArtUrl("trap", "ashen");
    expect(eventArtUrl("trap", "ashen")).toBe(a);
    expect(eventArtUrl("trap", "cloud")).not.toBe(a);
    setQCanvasFactory(null);
    expect(made).toBe(2);
    expect(eventArtCacheSize()).toBe(before + 2);
  });
});

describe("事件卡（取代 6C-7 的場景色塊）", () => {
  it("沒有 art 時照選項圖示挑場景，不再畫色塊", () => {
    const out = card(event({ art: null, region: "cloud_ridge" }));
    expect(out).toContain('data-art="scene"');
    expect(out).toContain('data-scene="stele"');
    expect(out).toContain('data-bg="cloud"');
    expect(out).not.toContain("linear-gradient");
  });

  it("有 art 與區域時照它畫", () => {
    const out = card(event({ art: "caravan", region: "ashen_waste" }));
    expect(out).toContain('data-scene="caravan"');
    expect(out).toContain('data-bg="ashen"');
    expect(out).toContain('aria-label="商隊"');
  });

  it("art_url 有值時仍優先用圖片", () => {
    const out = card(event({ art: "caravan", art_url: "/x.png" }));
    expect(out).toContain('data-art="image"');
    expect(out).toContain("url(/x.png)");
    expect(out).not.toContain("data-scene");
  });

  it("有 DOM 時背景是畫好的插圖", () => {
    vi.stubGlobal("document", { createElement: () => ({ width: 0, height: 0, getContext: () => mockCtx().ctx, toDataURL: () => "data:image/png;base64,EVT" }) });
    expect(card(event({ art: "friend" }))).toContain("url(data:image/png;base64,EVT)");
  });
});
