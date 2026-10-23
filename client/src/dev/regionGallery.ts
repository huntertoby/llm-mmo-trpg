// 開發用：區域主題「雲嶺」的 7 種地圖類型場景（Phase 3-37b），對照 docs/art/realms.png 的雲嶺樣張。
// 開 `client/region-gallery.html`（pnpm dev 後 /region-gallery.html）；不屬於正式 build。用真正的 BattleRenderer 畫。
// 正式地圖只有 bridge_chasm（雲海吊橋）與 dark_forest（竹林）標了 region；其他類型與兩種 look 覆寫在這裡擺場景驗證。
import type { BattleView, Glossary, ObjectView, TileView, UnitView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { buildDrawModel } from "../battle/drawModel";
import { setGlossary } from "../battle/glossary";
import { object, tile, unit } from "../battle/testFixtures";
import { BattleRenderer } from "../render/BattleRenderer";
import { waitForFonts } from "../render/fontLoad";

setGlossary(glossary as unknown as Glossary);
await waitForFonts();

const HERO = "unit_0001";

const TERRAIN: Readonly<Record<string, string>> = { ".": "stone", ",": "grass", ":": "dirt", "#": "wall", "~": "chasm", "^": "lava", o: "ice_hole" };
const SURFACE: Readonly<Record<string, TileView["surface"]>> = { w: "water", i: "ice", f: "fire", s: "smoke", p: "poison", l: "oil" };
const OBJ: Readonly<Record<string, string>> = {
  c: "crate",
  L: "low_wall",
  P: "stone_pillar",
  b: "oil_barrel",
  g: "fallen_log",
  r: "grass",
  B: "wooden_bridge",
  T: "dead_tree",
  I: "thin_ice",
  W: "ice_wall",
  H: "thorn_wall",
  R: "rubble",
};

interface Scene {
  title: string;
  /** 每格兩個字元：地形（或表面）與物件；以空白分隔。 */
  rows: string[];
  heights?: string[];
  region?: string;
  look?: Record<string, string>;
  weather?: string;
  units: Array<["ally" | "enemy", number, number]>;
}

function build(scene: Scene): BattleView {
  const tiles: TileView[] = [];
  const objects: ObjectView[] = [];
  const h = scene.rows.length;
  const w = (scene.rows[0] ?? "").split(" ").length;
  scene.rows.forEach((row, y) => {
    row.split(" ").forEach((cell, x) => {
      const t = cell.charAt(0);
      const o = cell.charAt(1);
      const height = Number(scene.heights?.[y]?.charAt(x) ?? "0");
      const surface = SURFACE[t];
      const terrain = surface === undefined ? (TERRAIN[t] ?? "stone") : "stone";
      tiles.push(tile(x, y, { terrain, height, surface: surface ?? "none" }));
      const kind = OBJ[o];
      if (kind !== undefined) objects.push(object(`o${x}_${y}`, kind, x, y, kind === "thin_ice" ? { hp: 5, max_hp: 10 } : { hp: 10, max_hp: 10 }));
    });
  });
  const units: UnitView[] = scene.units.map(([team, x, y], i) =>
    unit(i === 0 ? HERO : `unit_${String(i + 1).padStart(4, "0")}`, team, x, y, { template_id: team === "ally" ? "hero_fighter" : "bandit", name_zh: `單位${i}` }),
  );
  return {
    team: "ally",
    map_id: "region_gallery",
    map_name_zh: scene.title,
    width: w,
    height: h,
    tiles,
    objects,
    units,
    traps: [],
    turn_order: [HERO],
    active_unit: HERO,
    round: 2,
    max_rounds: 30,
    weather_id: scene.weather ?? null,
    weather_name_zh: scene.weather ?? null,
    objective: { kind: "eliminate", tiles: [], rounds: null },
    ended: false,
    winner: null,
    end_reason: null,
    pending: null,
    source_wells: [],
    zones: [],
    runes: [],
    region: scene.region ?? null,
    look: scene.look ?? {},
  } as unknown as BattleView;
}

const CLOUD = "cloud_ridge";

/** 每行十個格子，格子由「地形（或表面）字元＋物件字元」組成；物件省略時補底線。 */
const grid = (...rows: string[][]): string[] => rows.map((r) => r.map((c) => (c.length === 1 ? `${c}_` : c)).join(" "));

const SCENES: Scene[] = [];
SCENES.push(
  {
    title: "高原草甸（開闊平原）",
    region: CLOUD,
    rows: grid(
      [",", ",", ",", ",r", ",", ",", ",c", ",", ",", ","],
      [",", ",", ",g", ",", ":", ":", ",", ",", ",P", ","],
      [",r", ",", ",", ":", ":", ",", ",", ",", ",", ","],
      [",", ",", ",c", ":", ",", ",", ",", ",b", ",", ",r"],
      [",", ",", ",L", ",L", ":", ",", ",", ",", ",", ","],
      [",", ",", ",", ":", ":", ",r", ",", ",", ",g", ","],
    ),
    units: [["ally", 1, 3], ["enemy", 8, 2]],
  },
  {
    title: "峽谷棧道（狹窄長廊）｜look: wall=canyon_rock, floor=plank_walk",
    region: CLOUD,
    look: { wall: "canyon_rock", floor: "plank_walk" },
    rows: grid(
      ["#", "#", "#", "#", "#", "#", "#", "#", "#", "#", "#", "#"],
      ["#", ".", ".", ".c", ".", ".", ".", ".b", ".", ".", ".", "#"],
      ["#", ".", ".L", ".", ".", ".P", ".", ".", ".", ".g", ".", "#"],
      ["#", ".", ".", ".", ".", ".", ".", ".c", ".", ".", ".", "#"],
      ["#", "#", "#", "#", "#", "#", "#", "#", "#", "#", "#", "#"],
    ),
    units: [["ally", 1, 2], ["enemy", 10, 2]],
  },
  {
    title: "山寺石階（高台廢墟）",
    region: CLOUD,
    rows: grid(
      ["#", "#", ".P", ".", ".", ".", ".P", "#", "#", "#"],
      [".", ".", ".", ".L", ".L", ".L", ".", ".", ".", "."],
      [".", ".", ".", ".", ".", ".", ".", ".c", ".", "."],
      [",", ".", ".", ".", ".", ".", ".", ".", ".", ","],
      [",", ",", ".", ".b", ".", ".", ".", ".", ",", ","],
      [",", ",", ",", ".", ".", ".", ".", ",", ",", ","],
    ),
    heights: ["3333333333", "2222222222", "2211111122", "1100000011", "0000000000", "0000000000"],
    units: [["ally", 2, 4], ["enemy", 5, 1]],
  },
  {
    title: "雲海吊橋（吊橋深淵）｜正式地圖 bridge_chasm 同款外觀",
    region: CLOUD,
    rows: grid(
      [",", ",c", ",", "~", "~", "~", "~", ",", ",", ","],
      [",", ",", ",L", "~", "~", "~", "~", ",L", ",", ",g"],
      [",", ",", ",", "~B", "~B", "~B", "~B", ",", ",b", ","],
      [",", ",P", ",", "~", "~", "~", "~", ",", ",", ","],
      [",", ",", ",", "~B", "~B", "~B", "~B", ",", ",", ","],
      [",", ",", ",", "~", "~", "^", "~", ",", ",c", ","],
    ),
    units: [["ally", 1, 2], ["enemy", 8, 4]],
  },
  {
    title: "雲海吊橋（沒標區域＝預設畫法，對照用）",
    rows: grid(
      [",", ",c", ",", "~", "~", "~", "~", ",", ",", ","],
      [",", ",", ",L", "~", "~", "~", "~", ",L", ",", ",g"],
      [",", ",", ",", "~B", "~B", "~B", "~B", ",", ",b", ","],
      [",", ",P", ",", "~", "~", "~", "~", ",", ",", ","],
      [",", ",", ",", "~B", "~B", "~B", "~B", ",", ",", ","],
      [",", ",", ",", "~", "~", "^", "~", ",", ",c", ","],
    ),
    units: [["ally", 1, 2], ["enemy", 8, 4]],
  },
  {
    title: "竹林（森林）｜霧天薄霧加濃",
    region: CLOUD,
    weather: "fog",
    rows: grid(
      [",r", ",r", ",", ",T", ",", ",r", ",r", ",", ",T", ","],
      [",", ",", ",g", ",r", ",", ",", ",", ",r", ",", ",r"],
      [",T", ",", ",r", ",", ",", ",g", ",", ",", ",", ","],
      [",", ",r", ",", ",", ",T", ",", ",r", ",", ",r", ","],
      [",r", ",", ",", ",g", ",", ",", ",", ",T", ",", ","],
      [",", ",", ",r", ",", ",r", ",", ",", ",", ",", ",r"],
    ),
    units: [["ally", 1, 4], ["enemy", 8, 1]],
  },
  {
    title: "竹林（同上，無天氣）",
    region: CLOUD,
    rows: grid(
      [",r", ",r", ",", ",T", ",", ",r", ",r", ",", ",T", ","],
      [",", ",", ",g", ",r", ",", ",", ",", ",r", ",", ",r"],
      [",T", ",", ",r", ",", ",", ",g", ",", ",", ",", ","],
      [",", ",r", ",", ",", ",T", ",", ",r", ",", ",r", ","],
      [",r", ",", ",", ",g", ",", ",", ",", ",T", ",", ","],
      [",", ",", ",r", ",", ",r", ",", ",", ",", ",", ",r"],
    ),
    units: [["ally", 1, 4], ["enemy", 8, 1]],
  },
  {
    title: "雨中梯田（沼澤）｜look: floor=paddy, water_tint=green",
    region: CLOUD,
    look: { floor: "paddy", water_tint: "green" },
    weather: "rain",
    rows: grid(
      [",", ",", ",", ",", ",", ",", ",", ",", ",", ","],
      [",", "w", "w", ",", ",", ",", "w", "w", "w", ","],
      [",", "w", "w", ",c", ",", ",", "w", "w", ",", ","],
      [",", ",", ",", ",", ",r", ",", ",", "w", ",", ","],
      [",", ",", ",", ",g", ",", "w", "w", ",", ",P", ","],
      [",", ",", ",", ",", ",", "w", ",", ",", ",", ","],
    ),
    units: [["ally", 0, 3], ["enemy", 8, 3]],
  },
  {
    title: "雨中梯田（對照：只有 floor=paddy，水面維持藍色）",
    region: CLOUD,
    look: { floor: "paddy" },
    rows: grid(
      [",", "w", "w", ",", ",", ",", "w", "w", "w", ","],
      [",", "w", "w", ",c", ",", ",", "w", "w", ",", ","],
    ),
    units: [["ally", 0, 1], ["enemy", 8, 1]],
  },
  {
    title: "冬湖（冰湖）",
    region: CLOUD,
    rows: grid(
      ["i", "i", "i", "i", "i", "i", "i", "i", "i", "i"],
      ["i", "i", "oI", "o", "i", "i", "i", "i", "i", "i"],
      ["i", "i", "o", "o", "i", "iL", "i", "i", "i", "i"],
      [",", "i", "oI", "oI", "i", "i", "i", "oI", "o", "i"],
      [",", ",", "i", "i", "i", "i", "i", "o", "o", "i"],
      [",c", ",", ",", "i", "i", "i", ",", ",g", ",", ","],
    ),
    units: [["ally", 1, 4], ["enemy", 8, 1]],
  },
  {
    title: "致命地形與技能物件（地熱泉＝岩漿，寒潭＝冰窟；技能物件、表面不換皮）",
    region: CLOUD,
    rows: grid(
      ["^", "^", ".", "o", "o", ".", ".W", ".W", ".H", ".H"],
      ["^", "^", ".", "o", "o", ".", ".W", ".", ".H", ".R"],
      [".", ".", ".", ".", ".", ".", ".", ".", ".", "."],
      ["f", "f", "s", "s", "p", "p", "l", "l", "w", "w"],
    ),
    units: [["ally", 2, 2], ["enemy", 7, 2]],
  },
);

const box = document.createElement("div");
box.className = "scene";
document.body.appendChild(box);
for (const scene of SCENES) {
  const section = document.createElement("section");
  section.appendChild(Object.assign(document.createElement("h2"), { textContent: scene.title }));
  box.appendChild(section);
  const renderer = new BattleRenderer();
  await renderer.init(section);
  renderer.setScale(1.5);
  renderer.draw(buildDrawModel(build(scene), HERO));
}
