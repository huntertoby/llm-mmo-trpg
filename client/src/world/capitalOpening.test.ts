// Phase RT-5：主城開場四格（① awaken 插圖、② 浮橋石碑小牌＋守印人「！」、③ 大世界圖浮起＋「免費」、④ 抵達霧渡鎮）。
// 文案來自內容檔（`content/world/newcomer.yaml` 的 opening，由伺服器的 `guide` 帶來）；這裡測分配、狀態與畫法。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { parse } from "yaml";
import { type AtlasRegionView, type AtlasView, type FieldView, type WorldMapView, type WorldOpeningLine } from "../api/types";
import { BRIDGE_BREAK_Y, BRIDGE_PLANKS, drawSkyBridge } from "../render/capitalArt";
import { AWAKEN_ART, AWAKEN_HERO, AWAKEN_LIE_MS, drawAwakenArt, EVENT_ART_IDS } from "../render/eventArt";
import { type Surface } from "../render/regionMapPainter";
import { buttonHitBox, buttonText, FREE_ZH } from "../render/worldMapArt";
import { AtlasPainter, RISE_FROM_PX, RISE_STEP_MS, riseAt } from "../render/worldMapPainter";
import { AtlasMap } from "./AtlasMap";
import { atlasScene } from "./atlasScene";
import { FieldHeads, FieldSteleTags } from "./FieldHeads";
import { GUIDE_ALERT_ZH, headMarks } from "./fieldPeople";
import { AwakenDialog } from "./OpeningDialog";
import { atlasRisen, EDGE_ARROW, guideAnchor, heroDoll, openingStage, RISE_KEY, splitOpening, STELE_SUB_ZH, steleTags, takeAtlasRise, GUIDE_BUBBLE_MS, mainQuestNpc } from "./opening";
import { AWAKEN_BANNERS, AWAKEN_HERO as AWAKEN_HERO__rt5b, AWAKEN_RING } from "../render/eventArtAwaken";
import { T } from "../render/eventArtParts";
import { hudLayout } from "./hud";
import { captionRect, clearOfHud, hudAvoidRects, hudReach, nudgeCamera, placeTag, tagSize } from "./hudAvoid";
import newcomerYaml from "../../../content/world/newcomer.yaml?raw";
import capitalYaml from "../../../content/world/fields/capital/capital.yaml?raw";

// ---------------- 測試用的資料 ----------------

const NEWCOMER = parse(newcomerYaml) as { opening: WorldOpeningLine[] };
const OPENING = NEWCOMER.opening;

function region(over: Partial<AtlasRegionView> & { region: string; name_zh: string }): AtlasRegionView {
  return { status: "open", condition_zh: null, town: null, town_name_zh: null, current: false, can_teleport: false, free: false, ...over };
}

/** 新角色在主城時的大世界圖（伺服器 `tests/api/test_capital_opening_api.py` 鎖的那一組狀態）。 */
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

// --- 原 rt5b.test.ts ---
describe("原 rt5b.test.ts", () => {
// Phase RT-5b：主城開場的驗收修正（docs/archive/art/RT-5檢查.md）。石碑小牌與重要的人避開 HUD、守印人泡泡收起與展開、
// 主線「！」突出、浮動卡換行、醒來插圖、斷橋、守印人站位與南側石碑對齊、任務欄文字。
const AWAKEN_HERO = AWAKEN_HERO__rt5b;

type Spot = { id: string; at: [number, number]; figure?: { facing?: string } };
type Obj = { at: [number, number]; kind: string; look?: string };
const CAPITAL = parse(capitalYaml) as { situation_objects: Spot[]; objects: Obj[]; teleport_stones: { at: [number, number] }[]; entry: [number, number]; terrain: string };
const NEWCOMER = parse(newcomerYaml) as { guide_town_zh: string };

const VIEW = { width: 1568, height: 832 };
const LAYOUT = hudLayout(VIEW.width, VIEW.height, { mates: 2, narrow: false, collapsed: false });

/** 錄下 Canvas 呼叫的假 2D context（只記方法名稱與參數）。 */
function record(draw: (ctx: CanvasRenderingContext2D) => void): string[] {
  const calls: string[] = [];
  const target: Record<string, unknown> = {};
  const ctx = new Proxy(target, {
    get(t, k) {
      if (typeof k === "symbol") return undefined;
      if (k in t) return t[k];
      if (k === "createLinearGradient" || k === "createRadialGradient") return () => ({ addColorStop: () => undefined });
      if (k === "measureText") return () => ({ width: 10 });
      return (...args: unknown[]) => {
        calls.push(`${k}(${args.map((a) => (typeof a === "number" ? Math.round(a * 10) / 10 : String(a))).join(",")})`);
      };
    },
    set(t, k, v) {
      if (typeof k === "string") {
        t[k] = v;
        calls.push(`${k}=${String(v)}`);
      }
      return true;
    },
  });
  draw(ctx as unknown as CanvasRenderingContext2D);
  return calls;
}

describe("RT-5b 必修 1、2：石碑小牌與重要的人避開 HUD", () => {
  const avoid = hudAvoidRects(LAYOUT, VIEW);

  it("要避開的 HUD 有右上的小地圖、金幣欄、底部的功能列與說明列（說明列疊在功能列上方中央）", () => {
    const ids = ["hero", "mates", "place", "minimap", "clock", "wallet", "tracker", "bar"] as const;
    for (const id of ids) expect(avoid).toContainEqual(LAYOUT.blocks[id]);
    const cap = captionRect(VIEW, LAYOUT.scale);
    expect(avoid).toContainEqual(cap);
    expect(cap.top + cap.height).toBeLessThanOrEqual(LAYOUT.blocks.bar.top);
    // 地圖下緣微調時可以捲到說明列上面
    expect(hudReach(LAYOUT, VIEW).bottom).toBeGreaterThan(VIEW.height - LAYOUT.blocks.bar.top);
  });

  it("小牌預設在石碑上方；壓到右上的金幣欄時換到石碑左邊；壓到下方功能列時抬到說明列上面；都放不下就不畫", () => {
    const size = tagSize("魔導樞市", "之後的賽季");
    const cam = { x: 0, y: 0 };
    const wallet = LAYOUT.blocks.wallet;
    // 石碑在畫面中央：照預設放上方
    const mid = { left: 700, top: 400, width: 32, height: 66 };
    expect(placeTag(mid, size, cam, VIEW, avoid).side).toBe("n");
    // 石碑就在金幣欄正下方、靠右欄的左緣：上方會壓到金幣欄 → 換位置，而且不壓 HUD
    const east = { left: wallet.left - 40, top: wallet.top + wallet.height + 8, width: 32, height: 66 };
    const at = placeTag(east, size, cam, VIEW, avoid);
    expect(at.left + size.width).toBeLessThanOrEqual(wallet.left);
    expect(clearOfHud({ left: at.left, top: at.top, ...size }, cam, VIEW, avoid)).toBe(true);
    // 石碑被功能列蓋住：小牌抬到說明列上面
    const bar = LAYOUT.blocks.bar;
    const south = { left: bar.left + bar.width / 2 - 16, top: bar.top + 4, width: 32, height: 66 };
    const lifted = placeTag(south, size, cam, VIEW, avoid);
    expect(lifted.side).toBe("lift");
    expect(lifted.top + size.height).toBeLessThanOrEqual(captionRect(VIEW, LAYOUT.scale).top);
    // 石碑整個在功能列底下更下面（抬超過 2 格）：不畫，也不壓在 HUD 上
    const deep = { ...south, top: VIEW.height - 10 };
    expect(placeTag(deep, size, cam, VIEW, avoid).side).toBe("hidden");
    // 沒有 HUD（不是 HUD 版面）照預設
    expect(placeTag(east, size, null, null, []).side).toBe("n");
  });

  it("鏡頭微調：露出一部分的石碑整個露出來，主角不被蓋住，最多移 2 格；完全在畫面外的不拉鏡頭；同樣輸入同樣結果", () => {
    const insets = { top: 300, right: VIEW.width - LAYOUT.blocks.minimap.left, bottom: VIEW.height - LAYOUT.blocks.bar.top, left: 0 };
    const content = { width: 1536, height: 1180 };
    const cam = { x: 111, y: 100, scale: 1 };
    const hero = { left: 768, top: 520, width: 48, height: 76 };
    // 東側石碑（含上方小牌）一半在右欄底下
    const wallet = LAYOUT.blocks.wallet;
    const stele = { left: wallet.left + cam.x - 30, top: wallet.top + cam.y - 5, width: 83, height: 110 };
    expect(clearOfHud(stele, cam, VIEW, hudAvoidRects(LAYOUT, VIEW))).toBe(false);
    const input = { cam, view: VIEW, content, insets, avoid: hudAvoidRects(LAYOUT, VIEW), hero, targets: [stele] };
    const moved = nudgeCamera(input);
    expect(moved).not.toEqual(cam);
    expect(Math.abs(moved.x - cam.x) + Math.abs(moved.y - cam.y)).toBeLessThanOrEqual(96 * 2);
    expect(clearOfHud(stele, moved, VIEW, input.avoid)).toBe(true);
    expect(clearOfHud(hero, moved, VIEW, input.avoid)).toBe(true);
    expect(nudgeCamera(input)).toEqual(moved);
    // 在畫面外的東西不拉鏡頭
    expect(nudgeCamera({ ...input, targets: [{ ...stele, left: 5000 }] })).toBe(cam);
    // 都已經露出來：不動
    expect(nudgeCamera({ ...input, targets: [{ left: 600, top: 400, width: 40, height: 60 }] })).toBe(cam);
  });

  it("石碑小牌畫出來時帶 data-side（給截圖與煙霧檢查看）", () => {
    const html = renderToStaticMarkup(
      createElement(FieldSteleTags, {
        tags: [{ id: "stele_arcane_hub", region: "arcane_hub", x: 30, y: 6, name: "魔導樞市", status: "later", sub: "之後的賽季" }],
        grid: { width: 32, height: 24, tiles: [] } as never,
        scale: 1,
        colors: {},
        cam: { x: 0, y: 0 },
        view: VIEW,
        avoid: hudAvoidRects(LAYOUT, VIEW),
      }),
    );
    expect(html).toMatch(/data-side="(n|w|e|s|lift|hidden)"/);
  });
});

describe("RT-5b 必修 6：守印人的泡泡", () => {
  const field = { npcs: [], friends: [] } as unknown as FieldView;
  const guides = new Map([["seal_keeper", { name: "守印人", text: "新來的？雲嶺那邊缺人手。站上傳送陣，去霧渡鎮找渡婆婆。", x: 14, y: 12 }]]);

  it("整句留約 8 秒；收起來只剩「！」（沒有泡泡、標記 folded），「！」照樣在、是主線樣式", () => {
    expect(GUIDE_BUBBLE_MS).toBe(8000);
    const open = headMarks(field, new Map(), guides)[0]!;
    expect(open).toMatchObject({ folded: false, main: true, alert: "quest" });
    expect(open.bubble).toContain("霧渡鎮");
    const folded = headMarks(field, new Map(), guides, { guideFolded: true })[0]!;
    expect(folded).toMatchObject({ folded: true, bubble: null, alert: "quest", main: true });
  });

  it("收起時點「！」＝展開（onExpand），展開時點＝照舊走過去開公告板（onPick）", () => {
    const folded = headMarks(field, new Map(), guides, { guideFolded: true });
    const html = renderToStaticMarkup(createElement(FieldHeads, { marks: folded, grid: { width: 32, height: 24, tiles: [] } as never, scale: 1, onPick: () => undefined, onExpand: () => undefined }));
    expect(html).toContain('data-guide="folded"');
    expect(html).toContain("點了看指示");
    expect(html).not.toContain("field-bubble\"");
    const open = renderToStaticMarkup(createElement(FieldHeads, { marks: headMarks(field, new Map(), guides), grid: { width: 32, height: 24, tiles: [] } as never, scale: 1, onPick: () => undefined }));
    expect(open).toContain('data-guide="open"');
    expect(open).toContain("field-bubble");
  });

  it("站在傳送陣旁、上面放得下時泡泡放頭頂往左上（nw），不蓋到東邊的主角；夾到畫面邊上時往畫面中間那一邊放", () => {
    const visible = { left: 0, top: 0, right: 1600, bottom: 900 };
    expect(guideAnchor({ left: 700, top: 500 }, visible, visible).side).toBe("nw");
    expect(guideAnchor({ left: 700, top: 60 }, visible, visible).side).toBe("w");
    const box = { left: 100, top: 200, right: 700, bottom: 600 };
    expect(guideAnchor({ left: 150, top: 50 }, box)).toMatchObject({ edge: "n", side: "e" });
    expect(guideAnchor({ left: 650, top: 50 }, box)).toMatchObject({ edge: "n", side: "w" });
  });
});

describe("RT-5b 小修 10：主線「！」比支線突出；任務欄文字（玩法 PM 決定）", () => {
  const npc = (id: string, name: string, alert: "quest" | "rumor" | null) => ({ id, name_zh: name, x: 1, y: 1, alert, alert_zh: null, rank: "neutral", rank_zh: "中立" });
  const ferry = { npcs: [npc("granny_du", "渡婆婆", "quest"), npc("shopkeeper_liu", "柳掌櫃", "quest"), npc("gran", "葛蘭", "rumor")], friends: [] } as unknown as FieldView;

  it("任務欄是內容檔的「找渡婆婆」（拿掉「頭上有「！」的」）", () => {
    expect(NEWCOMER.guide_town_zh).toBe("找渡婆婆");
  });

  it("指引點名的那位（有任務「！」）是主線；開場（主城）、沒有指引、點名的人沒有任務「！」時沒有主線", () => {
    expect(mainQuestNpc({ text_zh: NEWCOMER.guide_town_zh, how_zh: null, opening: [] }, ferry)).toBe("granny_du");
    expect(mainQuestNpc({ text_zh: "到霧渡鎮找渡婆婆", how_zh: null, opening: [{ speaker_zh: "說書人", text_zh: "……" }] }, ferry)).toBeNull();
    expect(mainQuestNpc(null, ferry)).toBeNull();
    expect(mainQuestNpc({ text_zh: "找葛蘭", how_zh: null, opening: [] }, ferry)).toBeNull();
  });

  it("主線的「！」多一個 main 樣式，支線照舊", () => {
    const marks = headMarks(ferry, new Map(), new Map(), { main: "granny_du" });
    expect(marks.map((m) => [m.id, m.main])).toEqual([
      ["granny_du", true],
      ["shopkeeper_liu", false],
      ["gran", false],
    ]);
    const html = renderToStaticMarkup(createElement(FieldHeads, { marks, grid: { width: 32, height: 24, tiles: [] } as never, scale: 1, onPick: () => undefined }));
    expect(html.match(/field-alert quest main/g)).toHaveLength(1);
    expect(html.match(/field-alert quest"/g)).toHaveLength(1);
    expect(html.match(/field-alert rumor"/g)).toHaveLength(1);
  });
});

describe("RT-5b 必修 4、7：醒來插圖與斷橋", () => {
  it("主角在晶柱右側（頭不壓晶柱）；晶冠的旗桿在遠處建築（4.2～5.7 格）左邊（半坐起的姿勢 RT-5c 改成髖部彎，見 capitalOpeningReview.test.ts）", () => {
    for (const pose of [0, 1] as const) expect(AWAKEN_HERO[pose].x - AWAKEN_RING.x).toBeGreaterThan(60);
    const [bx] = AWAKEN_BANNERS.crystal_crown;
    const poleX = bx * T + 24; // drawBanner：旗桿在畫布中央（U/2），旗面往右 20
    expect(poleX + 20).toBeLessThan(4.2 * T);
  });

  it("斷口：最後一塊整板斷了一半（鋸齒）、脫落的碎板、斷繩末端散成三股；四個方向確定", () => {
    expect(BRIDGE_PLANKS.filter((p) => p === null)).toHaveLength(2);
    for (const side of ["n", "e", "s", "w"] as const) {
      const a = record((c) => drawSkyBridge(c, side, true, true));
      expect(a).toEqual(record((c) => drawSkyBridge(c, side, true, true)));
      expect(a.filter((x) => x.startsWith("quadraticCurveTo"))).toHaveLength(2);
      // 斷繩粗 2.6、深色
      expect(a).toContain("lineWidth=2.6");
      // 兩條斷繩各三股
      expect(a.filter((x) => x.startsWith("lineTo")).length).toBeGreaterThan(10);
    }
    expect(BRIDGE_BREAK_Y).toBeLessThan(0);
  });
});

describe("RT-5b 必修 8、小修 9：守印人站位與南側石碑", () => {
  const spot = (id: string) => CAPITAL.situation_objects.find((s) => s.id === id)!;
  const objAt = (x: number, y: number) => CAPITAL.objects.filter((o) => o.at[0] === x && o.at[1] === y);

  it("守印人站在傳送石旁相鄰的空格，不在傳送石、抵達點上，那一格沒有擋路的物件", () => {
    const keeper = spot("seal_keeper");
    const stone = CAPITAL.teleport_stones[0]!.at;
    expect(Math.max(Math.abs(keeper.at[0] - stone[0]), Math.abs(keeper.at[1] - stone[1]))).toBe(1);
    expect(keeper.at).not.toEqual(stone);
    expect(keeper.at).not.toEqual(CAPITAL.entry);
    expect(objAt(...keeper.at)).toEqual([]);
    expect(CAPITAL.terrain.split("\n").map((r) => r.trim())[keeper.at[1]]![keeper.at[0]]).toBe(".");
    expect(keeper.figure?.facing).toBe("e");
  });

  it("南側兩座石碑站在各自浮橋的那一欄（橋頭），石碑的物件與情境物件同一格", () => {
    for (const region of ["ashen_waste", "frost_tide"]) {
      const stele = spot(`stele_${region}`);
      const bridge = spot(`bridge_${region}`);
      const bridgeCols = CAPITAL.objects.filter((o) => o.look === "sky_bridge" && o.at[1] === bridge.at[1] && Math.abs(o.at[0] - bridge.at[0]) <= 1).map((o) => o.at[0]);
      expect(bridgeCols).toContain(stele.at[0]);
      expect(stele.at[1]).toBe(bridge.at[1] - 1);
      expect(objAt(...stele.at).map((o) => o.look)).toEqual(["stele"]);
    }
  });
});
});
