// Phase RT-5：主城開場四格（① awaken 插圖、② 浮橋石碑小牌＋守印人「！」、③ 大世界圖浮起＋「免費」、④ 抵達霧渡鎮）。
// 文案來自內容檔（`content/world/newcomer.yaml` 的 opening，由伺服器的 `guide` 帶來）；這裡測分配、狀態與畫法。
import newcomerYaml from "../../../content/world/newcomer.yaml?raw";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { parse } from "yaml";
import type { AtlasRegionView, AtlasView, FieldView, WorldMapView, WorldOpeningLine } from "../api/types";
import { BRIDGE_BREAK_Y, BRIDGE_PLANKS, drawSkyBridge } from "../render/capitalArt";
import { AWAKEN_ART, AWAKEN_HERO, AWAKEN_LIE_MS, drawAwakenArt, EVENT_ART_IDS } from "../render/eventArt";
import type { Surface } from "../render/regionMapPainter";
import { buttonHitBox, buttonText, FREE_ZH } from "../render/worldMapArt";
import { AtlasPainter, RISE_FROM_PX, RISE_STEP_MS, riseAt } from "../render/worldMapPainter";
import { AtlasMap } from "./AtlasMap";
import { atlasScene } from "./atlasScene";
import { FieldHeads, FieldSteleTags } from "./FieldHeads";
import { GUIDE_ALERT_ZH, headMarks } from "./fieldPeople";
import { AwakenDialog } from "./OpeningDialog";
import { atlasRisen, EDGE_ARROW, guideAnchor, heroDoll, openingStage, RISE_KEY, splitOpening, STELE_SUB_ZH, steleTags, takeAtlasRise } from "./opening";

// ---------------- 測試用的資料 ----------------

const NEWCOMER = parse(newcomerYaml) as { opening: WorldOpeningLine[] };
const OPENING = NEWCOMER.opening;

function region(over: Partial<AtlasRegionView> & { region: string; name_zh: string }): AtlasRegionView {
  return { status: "open", condition_zh: null, town: null, town_name_zh: null, current: false, can_teleport: false, free: false, ...over };
}

/** 新角色在主城時的大世界圖（伺服器 `tests/api/test_opening_rt5.py` 鎖的那一組狀態）。 */
function atlas(free = true): AtlasView {
  return {
    regions: [
      region({ region: "cloud_ridge", name_zh: "雲嶺", town: "mist_ferry", town_name_zh: "霧渡鎮", can_teleport: true, free }),
      region({ region: "ashen_waste", name_zh: "灰燼荒原", status: "locked", condition_zh: "世界事件：霧潮入侵", town: "ember_market", town_name_zh: "餘燼集" }),
      region({ region: "crystal_crown", name_zh: "晶冠城邦", status: "later", condition_zh: "之後的賽季" }),
      region({ region: "arcane_hub", name_zh: "魔導樞市", status: "later", condition_zh: "之後的賽季" }),
      region({ region: "frost_tide", name_zh: "霜潮海境", status: "later", condition_zh: "之後的賽季" }),
    ],
    capital: region({ region: "capital", name_zh: "主城", town: "capital", town_name_zh: "樞島", current: true }),
    can_teleport: true,
    teleport_problem_zh: null,
    art_url: null,
    maps: [],
  };
}

function capitalMap(): WorldMapView {
  return { region: "capital", name_zh: "主城", level_zh: "Lv 1", locations: [], edges: [], stones: [], can_teleport: true, hub: true } as unknown as WorldMapView;
}

const KEEPER = {
  id: "seal_keeper",
  name_zh: "守印人",
  x: 25,
  y: 3,
  use: "note",
  usable: false,
  panel: "board",
  figure: { portrait: { look: { skin: "#d9a47a" }, gear: {}, extras: [] }, facing: "w" },
};

function stele(region: string, x: number, y: number) {
  return { id: `stele_${region}`, name_zh: `${region}的橋頭石碑`, x, y, use: "note", usable: false, stele_region: region };
}

function field(objects: unknown[] = [KEEPER, stele("cloud_ridge", 1, 14), stele("ashen_waste", 17, 22), stele("frost_tide", 28, 22), stele("crystal_crown", 11, 1), stele("arcane_hub", 30, 6)]): FieldView {
  return { map_id: "capital", name_zh: "樞島", region: "capital", width: 32, height: 24, npcs: [], friends: [], situation_objects: objects } as unknown as FieldView;
}

// ---------------- 畫布記錄 ----------------

function mockCtx(calls: string[] = []): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const store: Record<string, unknown> = {};
  const fmt = (a: unknown): string => (typeof a === "number" ? a.toFixed(3) : typeof a === "string" ? a : typeof a);
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map(fmt).join(",")})`);
        if (prop === "createLinearGradient" || prop === "createRadialGradient" || prop === "createPattern") return { addColorStop: (o: number, c: string) => calls.push(`stop(${o},${c})`) };
        if (prop === "measureText") return { width: String(args[0]).length * 10 };
        if (prop === "getImageData") return { data: new Uint8ClampedArray(4) };
        return undefined;
      };
    },
    set(target, prop: string, value) {
      target[prop] = value;
      calls.push(`${prop}=${fmt(value)}`);
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  return { ctx, calls };
}

const record = (draw: (c: CanvasRenderingContext2D) => void): string[] => {
  const r = mockCtx();
  draw(r.ctx);
  return r.calls;
};

afterEach(() => {
  vi.unstubAllGlobals();
});

// ---------------- ① 醒來 ----------------

describe("RT-5 ① 醒來：awaken 插圖＋說書人卡", () => {
  it("開場的句子來自內容檔：說書人那句放插圖卡、守印人那句給地圖上的守印人（文案定稿）", () => {
    expect(OPENING.map((l) => l.speaker_zh)).toEqual(["說書人", "守印人"]);
    const split = splitOpening(OPENING, field());
    expect(split.narrator.map((l) => l.text_zh)).toEqual(["傳送陣的光暗了下去。你在樞島中央醒來，晶柱還在低鳴。五座浮橋斷在雲上，各自指向一個界域。"]);
    expect([...split.spoken]).toEqual([["seal_keeper", { name: "守印人", text: "新來的？雲嶺那邊缺人手。站上傳送陣，去霧渡鎮找渡婆婆。", x: 25, y: 3 }]]);
  });

  it("地圖上沒有守印人時，兩句都放插圖卡（不漏句子）", () => {
    const split = splitOpening(OPENING, field([]));
    expect(split.narrator).toHaveLength(2);
    expect(split.spoken.size).toBe(0);
    expect(splitOpening(OPENING, null).narrator).toHaveLength(2);
  });

  it("階段：伺服器有給開場且沒看過＝awaken；看過＝guide；沒給（到過霧渡鎮）＝none", () => {
    const guide = { text_zh: "到霧渡鎮找渡婆婆", how_zh: null, opening: OPENING };
    expect(openingStage(guide, false)).toBe("awaken");
    expect(openingStage(guide, true)).toBe("guide");
    expect(openingStage({ ...guide, opening: [] }, false)).toBe("none");
    expect(openingStage(null, false)).toBe("none");
  });

  it("插圖卡只有一個按鈕「站起來」，說書人那句照內容檔，插圖是 awaken 場景", () => {
    const html = renderToStaticMarkup(createElement(AwakenDialog, { lines: splitOpening(OPENING, field()).narrator, hero: heroDoll(null), open: ["cloud_ridge"], place: "樞島", onStand: () => undefined }));
    // 動作按鈕只有「站起來」（另一顆是 DialogFrame 在戰鬥外框才有的「移到下方」；大世界有 HUD 位置時不顯示）
    const actions = html.match(/<div class="modal-buttons">([\s\S]*?)<\/div>/)?.[1] ?? "";
    expect(actions.match(/<button/g)?.length).toBe(1);
    expect(actions).toContain("站起來");
    expect(html).toContain("傳送陣的光暗了下去。");
    expect(html).not.toContain("新來的？");
    expect(html).toContain(`data-scene="${AWAKEN_ART}"`);
  });

  it("awaken 不是伺服器的事件骨架場景（不進 EVENT_ART_IDS）；畫法確定、兩格動作不同、主角外觀不同畫出來就不同", () => {
    expect(EVENT_ART_IDS).not.toContain(AWAKEN_ART);
    const hero = heroDoll(null);
    const lie = record((c) => drawAwakenArt(c, hero, 0, ["cloud_ridge"], "樞島"));
    expect(lie.length).toBeGreaterThan(500);
    expect(record((c) => drawAwakenArt(c, hero, 0, ["cloud_ridge"], "樞島"))).toEqual(lie);
    expect(record((c) => drawAwakenArt(c, hero, 1, ["cloud_ridge"], "樞島"))).not.toEqual(lie);
    const other = heroDoll({ template_id: "hero", doll_look: { skin: "#7a4e32", hair: "long", hair_color: "#e8e0d0" }, weapon_id: "fire_staff", weapon_class: "focus" } as never);
    expect(record((c) => drawAwakenArt(c, other, 0, ["cloud_ridge"], "樞島"))).not.toEqual(lie);
    // 光圈照已開放的區：開放的區不同，畫法不同
    expect(record((c) => drawAwakenArt(c, hero, 0, [], "樞島"))).not.toEqual(lie);
    // 躺著幾乎水平、半坐起上身往後仰；先躺著約 0.9 秒
    expect(Math.abs(AWAKEN_HERO[0].rot)).toBeGreaterThan(1.3);
    expect(Math.abs(AWAKEN_HERO[1].rot)).toBeLessThan(1);
    expect(AWAKEN_LIE_MS).toBeGreaterThan(0);
  });
});

// ---------------- ② 廣場、浮橋、石碑小牌、守印人 ----------------

describe("RT-5 ② 浮橋石碑的小牌、守印人頭上「！」", () => {
  it("小牌照大世界圖的開放狀態：雲嶺寫區名；荒原「尚未開放」；其他三區「之後的賽季」", () => {
    const tags = steleTags(field(), atlas());
    const by = Object.fromEntries(tags.map((t) => [t.region, [t.status, t.name, t.sub]]));
    expect(by).toEqual({
      cloud_ridge: ["open", "雲嶺", ""],
      ashen_waste: ["locked", "灰燼荒原", "尚未開放"],
      crystal_crown: ["later", "晶冠城邦", "之後的賽季"],
      arcane_hub: ["later", "魔導樞市", "之後的賽季"],
      frost_tide: ["later", "霜潮海境", "之後的賽季"],
    });
    expect(STELE_SUB_ZH.open).toBe("");
    // 荒原開放之後（世界事件）就寫區名
    const opened = atlas();
    opened.regions[1] = { ...opened.regions[1]!, status: "open" };
    expect(steleTags(field(), opened).find((t) => t.region === "ashen_waste")?.sub).toBe("");
    // 大世界圖沒有的區不畫
    expect(steleTags(field([stele("nowhere", 2, 2)]), atlas())).toEqual([]);
  });

  it("小牌畫出來：沒開放的灰色加鎖、兩行；已開放的只有區名", () => {
    const grid = { width: 32, height: 24, tiles: [] } as never;
    const html = renderToStaticMarkup(createElement(FieldSteleTags, { tags: steleTags(field(), atlas()), grid, scale: 1, colors: { cloud_ridge: "#6aa84a" } }));
    expect(html.match(/data-testid="field-stele-tag"/g)?.length).toBe(5);
    expect(html.match(/field-stele-lock/g)?.length).toBe(4);
    expect(html).toContain("border-color:#6aa84a");
  });

  it("守印人頭上「！」＋整句指示（不截成 1～2 句）；只在 guide 階段給", () => {
    const split = splitOpening(OPENING, field());
    const marks = headMarks(field(), new Map(), split.spoken);
    const keeper = marks.find((m) => m.kind === "figure");
    expect(keeper).toMatchObject({ key: "figure:seal_keeper", name: "守印人", alert: "quest", alertZh: GUIDE_ALERT_ZH, pos: { x: 25, y: 3 } });
    expect(keeper?.bubble).toBe("新來的？雲嶺那邊缺人手。站上傳送陣，去霧渡鎮找渡婆婆。");
    expect(headMarks(field()).some((m) => m.kind === "figure")).toBe(false);
  });

  it("說話的人在畫面外（800×600：守印人在北邊）時，「！」和泡泡夾到畫面邊上、加方向箭頭；在畫面裡照原位", () => {
    const box = { left: 100, top: 200, right: 700, bottom: 600 };
    expect(guideAnchor({ left: 400, top: 400 }, box)).toEqual({ left: 400, top: 400, side: "w", edge: "" });
    const north = guideAnchor({ left: 650, top: 50 }, box);
    expect(north.edge).toBe("n");
    expect(north.top).toBeGreaterThan(box.top);
    expect(north.left).toBe(650);
    expect(guideAnchor({ left: 900, top: 50 }, box)).toMatchObject({ left: 674, edge: "ne", side: "w" });
    // 左邊放不下泡泡時放右邊
    expect(guideAnchor({ left: 150, top: 400 }, box).side).toBe("e");
    // 人在整個可視區裡（只是在 HUD 安全區外，例如 1600×900 的守印人）就照原位，不夾
    const visible = { left: 0, top: 0, right: 800, bottom: 700 };
    expect(guideAnchor({ left: 650, top: 100 }, box, visible)).toEqual({ left: 650, top: 100, side: "w", edge: "" });
    expect(guideAnchor({ left: 650, top: 10 }, box, visible).edge).toBe("n");
    expect(EDGE_ARROW.ne).toBe("↗");
    // 沒有鏡頭（不是 HUD 版面）照原位
    expect(guideAnchor({ left: 5, top: 5 }, null)).toEqual({ left: 5, top: 5, side: "w", edge: "" });
    const html = renderToStaticMarkup(
      createElement(FieldHeads, { marks: headMarks(field(), new Map(), splitOpening(OPENING, field()).spoken), grid: { width: 32, height: 24, tiles: [] } as never, scale: 1, onPick: () => undefined, view: { left: 0, top: 400, right: 2000, bottom: 1200 } }),
    );
    expect(html).toContain('data-edge="n"');
    expect(html).toContain("↑");
  });

  it("浮橋斷在雲上：外端缺兩塊木板、最外面那塊歪掉；繩欄在斷口斷開；四個方向畫法都確定", () => {
    expect(BRIDGE_PLANKS.filter((p) => p === null)).toHaveLength(2);
    expect(BRIDGE_PLANKS.at(-1)).toBeNull();
    const last = [...BRIDGE_PLANKS].reverse().find((p) => p !== null);
    expect(Math.abs(last?.[1] ?? 0)).toBeGreaterThan(0.1);
    expect(last?.[0] ?? 0).toBeLessThan(BRIDGE_BREAK_Y);
    // 木板不鋪到地圖邊（往外的半格 −26）
    expect(Math.min(...BRIDGE_PLANKS.filter((p) => p !== null).map((p) => p[0]))).toBeGreaterThan(-26 + 7);
    for (const side of ["n", "e", "s", "w"] as const) {
      const a = record((c) => drawSkyBridge(c, side, true, true));
      expect(a).toEqual(record((c) => drawSkyBridge(c, side, true, true)));
      expect(a.filter((x) => x.startsWith("quadraticCurveTo"))).toHaveLength(2); // 兩條垂下的斷繩
    }
  });
});

// ---------------- ③ 大世界圖：浮起與「免費」 ----------------

interface FakeSurface extends Surface {
  calls: string[];
}

function surfaces(): { make: (w: number, h: number) => Surface; list: FakeSurface[] } {
  const list: FakeSurface[] = [];
  return {
    list,
    make: (w, h) => {
      const { ctx, calls } = mockCtx();
      const s: FakeSurface = { width: w, height: h, calls, getContext: () => ctx };
      list.push(s);
      return s;
    },
  };
}

describe("RT-5 ③ 大世界圖：五座島依序浮起（只播一次）、雲嶺「免費」", () => {
  it("每座 0.3 秒、照順序：第 i 座在 i×0.3 秒開始；null＝不播（直接到位）；主城不動", () => {
    expect(RISE_STEP_MS).toBe(300);
    expect(riseAt(0, 0)).toEqual({ dy: RISE_FROM_PX, alpha: 0 });
    expect(riseAt(0, 300)).toEqual({ dy: 0, alpha: 1 });
    expect(riseAt(4, 1199).alpha).toBe(0);
    expect(riseAt(4, 1500)).toEqual({ dy: 0, alpha: 1 });
    expect(riseAt(2, null)).toEqual({ dy: 0, alpha: 1 });
    expect(riseAt(-1, 0)).toEqual({ dy: 0, alpha: 1 });
    const mid = riseAt(1, 450);
    expect(mid.dy).toBeGreaterThan(0);
    expect(mid.dy).toBeLessThan(RISE_FROM_PX);
  });

  it("浮起中還沒輪到的島不貼；到位後和不播一模一樣", () => {
    const { scene } = atlasScene(atlas(), capitalMap());
    const blits = (rise: number | null): string[] => {
      const { ctx, calls } = mockCtx();
      new AtlasPainter(surfaces().make).paintOverlay(ctx, scene, true, 1280, 860, 1, { t: 1000, rise });
      return calls.filter((c) => c.startsWith("drawImage"));
    };
    const all = blits(null);
    expect(blits(0).length).toBeLessThan(all.length);
    expect(blits(5 * RISE_STEP_MS)).toEqual(all);
  });

  it("前端記住播過了：同一個角色第二次打開不播；減少動態時不播也不記", () => {
    const store = new Map<string, string>();
    vi.stubGlobal("window", { localStorage: { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => void store.set(k, v) } });
    expect(takeAtlasRise("c1", true)).toBe(false);
    expect(atlasRisen("c1")).toBe(false);
    expect(takeAtlasRise("c1", false)).toBe(true);
    expect(takeAtlasRise("c1", false)).toBe(false);
    expect(takeAtlasRise("c2", false)).toBe(true);
    expect(JSON.parse(store.get(RISE_KEY) ?? "[]")).toEqual(["c1", "c2"]);
    expect(takeAtlasRise(null, false)).toBe(false);
  });

  it("「免費」照伺服器的 free：傳送鈕寫「（免費）」、點擊區跟著變寬；到過之後就沒有", () => {
    const free = atlasScene(atlas(true), capitalMap()).scene.islands[0]!;
    const paid = atlasScene(atlas(false), capitalMap()).scene.islands[0]!;
    expect(buttonText(free)).toBe(`傳送到霧渡鎮（${FREE_ZH}）`);
    expect(buttonText(paid)).toBe("傳送到霧渡鎮");
    expect(buttonHitBox(free)!.w).toBeGreaterThan(buttonHitBox(paid)!.w);
    const html = renderToStaticMarkup(createElement(AtlasMap, { atlas: atlas(true), map: capitalMap(), busy: false, rise: true, onOpenRegion: () => undefined, onTeleport: () => undefined, onClose: () => undefined }));
    expect(html).toContain('data-rise="1"');
    expect(html).toMatch(/data-testid="atlas-teleport-cloud_ridge" data-free="1"/);
    expect(html).toContain("傳送到霧渡鎮（免費）");
    const again = renderToStaticMarkup(createElement(AtlasMap, { atlas: atlas(false), map: capitalMap(), busy: false, onOpenRegion: () => undefined, onTeleport: () => undefined, onClose: () => undefined }));
    expect(again).toContain('data-rise="0"');
    expect(again).not.toContain("免費");
  });

  it("免費的傳送鈕發金光（金框＋較強的光暈）", () => {
    const free = atlasScene(atlas(true), capitalMap()).scene;
    const paid = atlasScene(atlas(false), capitalMap()).scene;
    const marks = (s: typeof free): string => {
      const f = surfaces();
      new AtlasPainter(f.make).paintOverlay(mockCtx().ctx, s, true, 1280, 860);
      return f.list.flatMap((x) => x.calls).join("\n");
    };
    expect(marks(free)).toContain("strokeStyle=#ffe08a");
    expect(marks(paid)).not.toContain("strokeStyle=#ffe08a");
  });
});
