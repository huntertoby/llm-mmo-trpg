// 開發用：冷卻井（CW-1；docs/art/冷卻井-移植需求.md 第 7 節的驗收截圖）。用真正的 BattleRenderer 畫熔心坑
// （地形、高台、矮牆、4 口井、灰燼之心 3×3 照 content/maps/molten_heart_pit.yaml；灰燼之心、餘燼蜥的畫面資料取自實機 API 的
// `dev/fixtures/moltenHeartUnits.json`）。
// 開 `client/dev/cooling-well-gallery.html`（pnpm dev 後 /dev/cooling-well-gallery.html）；不屬於正式 build。
//   ?scene=open      開場，4 口井完好
//   ?scene=damaged   (3, 8) 受損 1、(8, 8) 受損 2（耐久條、水滴記號）
//   ?scene=break&freeze=<ms>   (3, 8) 打破後第 <ms> 毫秒停格（K0 0、K1 90、K2 200、K3 340、K4 520 起）；&sheet=1 四格連拍
//   ?scene=after     (3, 8) 打破後（演出播完，600 ms）：3×3 水＋碎屑，主角站在水裡
//   &scale=<倍率>    畫面縮放（預設 1.4；800 寬用 0.9）
//   &crop=x0,y0,w,h  只露出這幾格（連拍時放大看井附近）
// 畫好後 `document.body.dataset.ready = "1"`。
import type { Application } from "pixi.js";
import type { BattleView, Glossary, ObjectView, TileView, UnitView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import looks from "./fixtures/moltenHeartUnits.json";
import { buildDrawModel } from "../battle/drawModel";
import { setGlossary } from "../battle/glossary";
import { object, tile, unit } from "../battle/testFixtures";
import { topReserve } from "../battle/elevation";
import { TILE_SIZE } from "../battle/geometry";
import { BattleRenderer } from "../render/BattleRenderer";
import { waitForFonts } from "../render/fontLoad";

setGlossary(glossary as unknown as Glossary);
await waitForFonts();

const HERO = "unit_0001";
const TERRAIN = [
  "############",
  "#vvvvvvvvvv#",
  "#v........v#",
  "#v........v#",
  "#v........v#",
  "#v........v#",
  "#v........v#",
  "#v........v#",
  "#v........v#",
  "#v........v#",
  "#vv.vvvv.vv#",
  "#..........#",
];
const CODE: Readonly<Record<string, string>> = { ".": "stone", v: "lava", "#": "wall" };
const HIGH = new Set(["2,9", "9,9"]);
const WELLS: ReadonlyArray<readonly [number, number]> = [[3, 4], [7, 4], [3, 8], [8, 8]];
const GIANT = new Set(["4,2", "5,2", "6,2", "4,3", "5,3", "6,3", "4,4", "5,4", "6,4"]);

const params = new URLSearchParams(location.search);
const sceneId = params.get("scene") ?? "open";
const scale = Number(params.get("scale") ?? "1.4");

interface Setup {
  wellHp: Record<string, number>;
  broken: ReadonlyArray<readonly [number, number]>;
  heroAt: readonly [number, number];
}

function view(s: Setup): BattleView {
  const water = new Set<string>();
  for (const [bx, by] of s.broken) {
    for (let y = by - 1; y <= by + 1; y++) {
      for (let x = bx - 1; x <= bx + 1; x++) {
        const t = CODE[TERRAIN[y]![x]!];
        if (t === "stone" && !GIANT.has(`${x},${y}`)) water.add(`${x},${y}`);
      }
    }
  }
  const tiles: TileView[] = [];
  for (let y = 0; y < 12; y++) {
    for (let x = 0; x < 12; x++) {
      tiles.push(tile(x, y, { terrain: CODE[TERRAIN[y]![x]!] ?? "stone", height: HIGH.has(`${x},${y}`) ? 1 : 0, surface: water.has(`${x},${y}`) ? "water" : "none" }));
    }
  }
  const objects: ObjectView[] = [object("obj_0001", "low_wall", 4, 9, { hp: 40, max_hp: 40 }), object("obj_0002", "low_wall", 7, 9, { hp: 40, max_hp: 40 })];
  WELLS.forEach(([x, y], i) => {
    if (s.broken.some(([bx, by]) => bx === x && by === y)) return;
    objects.push(object(`obj_000${i + 3}`, "cooling_well", x, y, { hp: s.wellHp[`${x},${y}`] ?? 15, max_hp: 15 }));
  });
  const units: UnitView[] = [
    unit(HERO, "ally", s.heroAt[0], s.heroAt[1], { template_id: "hero_fighter", name_zh: "主角", hp: 30, max_hp: 30 }),
    unit("unit_0002", "ally", 8, 11, { template_id: "hero_archer", name_zh: "賽倫", hp: 24, max_hp: 24, weapon_id: "bow", weapon_class: "ranged" }),
    unit("unit_0003", "ally", 2, 11, { template_id: "hero_mage", name_zh: "法師", hp: 20, max_hp: 20, weapon_id: "fire_staff" }),
    looks.ashen_heart as unknown as UnitView,
    { ...(looks.heart_ember_lizard as unknown as UnitView), id: "unit_0005", pos: { x: 2, y: 4 }, facing: "south" },
    { ...(looks.heart_ember_lizard as unknown as UnitView), id: "unit_0006", pos: { x: 8, y: 4 }, facing: "south" },
  ];
  return {
    team: "ally", map_id: "molten_heart_pit", map_name_zh: "熔心坑", width: 12, height: 12, tiles, objects, units, traps: [],
    turn_order: [HERO], active_unit: HERO, round: 2, max_rounds: 30, weather_id: null, weather_name_zh: null,
    objective: { kind: "eliminate", tiles: [], rounds: null, leader_retreat: true }, ended: false, winner: null, end_reason: null, pending: null,
    source_wells: [], zones: [], runes: [], region: "ashen_waste", look: {},
  } as unknown as BattleView;
}

const INTACT: Setup = { wellHp: {}, broken: [], heroAt: [3, 11] };
const appOf = (r: BattleRenderer): Application => (r as unknown as { app: Application }).app;

/** `&crop=x0,y0,w,h`：只露出這幾格（格子座標；連拍時每格放大看井附近）。 */
const crop = (params.get("crop") ?? "").split(",").map(Number);

async function show(host: HTMLElement, caption: string, draw: (r: BattleRenderer) => void): Promise<void> {
  const section = document.createElement("section");
  section.appendChild(Object.assign(document.createElement("h2"), { textContent: caption }));
  host.appendChild(section);
  const frame = document.createElement("div");
  section.appendChild(frame);
  const r = new BattleRenderer();
  await r.init(frame);
  r.setScale(scale);
  r.setIdle(false);
  draw(r);
  if (crop.length === 4 && crop.every((n) => Number.isFinite(n))) {
    const [x0, y0, w, h] = crop as [number, number, number, number];
    const reserve = topReserve(buildDrawModel(view(INTACT), HERO));
    Object.assign(frame.style, { width: `${w * TILE_SIZE * scale}px`, height: `${h * TILE_SIZE * scale}px`, overflow: "hidden" });
    const canvas = frame.querySelector("canvas");
    // 用負邊距位移（不用 position，浮動卡規則的原始碼掃描不收開發頁的 absolute）
    if (canvas !== null) Object.assign(canvas.style, { display: "block", marginLeft: `${-x0 * TILE_SIZE * scale}px`, marginTop: `${-(reserve + y0 * TILE_SIZE) * scale}px` });
  }
}

/** 打破的那一步：先畫打破前（(3, 8) 受損 2），再畫打破後，停在第 `ms` 毫秒。 */
function breakAt(r: BattleRenderer, ms: number, heroAt: readonly [number, number] = [3, 10], other: Record<string, number> = {}): void {
  const app = appOf(r);
  app.ticker.stop();
  r.motion.setClock(0);
  r.draw(buildDrawModel(view({ wellHp: { ...other, "3,8": 3 }, broken: [], heroAt }), HERO));
  r.draw(buildDrawModel(view({ wellHp: other, broken: [[3, 8]], heroAt }), HERO));
  r.motion.surface.clock = ms;
  r.motion.surface.tick(0);
  app.render();
}

const box = document.createElement("div");
box.className = "scene";
document.body.appendChild(box);
if (sceneId === "open") {
  await show(box, "熔心坑開場：4 口冷卻井完好", (r) => r.draw(buildDrawModel(view(INTACT), HERO)));
} else if (sceneId === "damaged") {
  await show(box, "受損：(3, 8) 受損 1（HP 9/15）、(8, 8) 受損 2（HP 4/15）", (r) => r.draw(buildDrawModel(view({ wellHp: { "3,8": 9, "8,8": 4 }, broken: [], heroAt: [3, 11] }), HERO)));
} else if (sceneId === "after") {
  await show(box, "打破後：(3, 8) 的 3×3 變成水＋碎屑，主角站在水裡 (3, 9)", (r) => breakAt(r, 600, [3, 9], { "8,8": 9 }));
} else if (params.get("sheet") === "1") {
  for (const [k, ms] of [["K0", 45], ["K1", 145], ["K2", 270], ["K3", 430]] as const) await show(box, `打破演出 ${k}（${ms} ms）`, (r) => breakAt(r, ms));
} else {
  const ms = Number(params.get("freeze") ?? "145");
  await show(box, `打破演出第 ${ms} ms`, (r) => breakAt(r, ms));
}
document.body.dataset.ready = "1";
