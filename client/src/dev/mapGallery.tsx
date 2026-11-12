// 開發用：6F-ART1 的區域圖與大世界圖插畫（開 `client/dev/map-gallery.html`，pnpm dev 後 /dev/map-gallery.html）。
// 不屬於正式 build；供美術 PM 驗收與截圖。畫面用正式元件（RegionMap、AtlasMap）與樣式；地點、連線讀
// `content/world/maps/*.yaml`，玩家狀態（去過、清空、任務、傳送石、足跡）照樣張 `docs/art/sample/regionArt.js` 的假資料。
// `?map=cloud_ridge`（預設）、`?map=ashen_waste`、`?map=atlas`；`?map=atlas&ashen=locked`：灰燼荒原改成鎖住（世界事件：霧潮入侵；FIX-ATLAS2 截圖用）。
import { createRoot } from "react-dom/client";
import { parse } from "yaml";
import type { AtlasRegionView, AtlasView, WorldLocationView, WorldMapView } from "../api/types";
import { AtlasMap } from "../world/AtlasMap";
import { RegionMap } from "../world/RegionMap";
import cloudYaml from "../../../content/world/maps/cloud_ridge.yaml?raw";
import ashenYaml from "../../../content/world/maps/ashen_waste.yaml?raw";
import "../styles/index.css";

interface YamlLoc {
  id: string;
  name_zh: string;
  kind: string;
  level_min?: number;
  level_max?: number;
  hidden?: boolean;
  pos: { x: number; y: number };
}
interface YamlMap {
  region: string;
  name_zh: string;
  level_min: number;
  level_max: number;
  locations: YamlLoc[];
  edges: [string, string][];
}
interface State {
  visited: string[];
  cleared: string[];
  here: string;
  quests: string[];
  stones: [string, boolean][];
  trail: string;
}

const STATES: Record<string, State> = {
  cloud_ridge: {
    visited: ["mist_ferry", "ferry_steps", "bamboo_path", "rain_terraces", "cliff_gang_fort", "cloud_sea_bridge", "hunter_hut", "mist_temple_gate", "old_pine_altar", "sword_tomb"],
    cleared: ["ferry_steps", "bamboo_path", "rain_terraces", "cliff_gang_fort"],
    here: "rain_terraces",
    quests: ["mist_temple_gate", "sword_tomb"],
    stones: [["mist_ferry", true], ["rain_terraces", true], ["cloud_sea_bridge", false]],
    trail: "mist_temple_gate",
  },
  ashen_waste: {
    visited: ["ember_market", "ash_ferry", "scorched_outskirts", "old_iron_post", "deadwood_forest", "red_sand_village", "cooling_well", "gang_convoy_road"],
    cleared: ["scorched_outskirts", "red_sand_village", "old_iron_post"],
    here: "deadwood_forest",
    quests: ["old_iron_post", "overseer_camp"],
    stones: [["ember_market", true], ["old_iron_post", true], ["tar_pits", false]],
    trail: "deadwood_forest",
  },
};

const lv = (lo?: number, hi?: number): string | null => (lo === undefined ? null : hi === undefined || hi === lo ? `Lv ${lo}` : `Lv ${lo}～${hi}`);

function toView(m: YamlMap, s: State): WorldMapView {
  const visited = new Set(s.visited);
  const adj = (id: string): boolean => m.edges.some(([a, b]) => (a === id && visited.has(b)) || (b === id && visited.has(a)));
  const fogOf = (l: YamlLoc): WorldLocationView["fog"] => (visited.has(l.id) ? "visited" : adj(l.id) ? "silhouette" : "fog");
  const locations: WorldLocationView[] = m.locations
    .filter((l) => l.hidden !== true || visited.has(l.id))
    .map((l) => ({
      id: l.id,
      name_zh: l.name_zh,
      kind: l.kind,
      kind_zh: l.kind,
      level_zh: lv(l.level_min, l.level_max),
      description_zh: "",
      x: l.pos.x,
      y: l.pos.y,
      current: l.id === s.here,
      adjacent: false,
      blocked_zh: null,
      cleared: s.cleared.includes(l.id),
      hidden: l.hidden === true,
      fog: fogOf(l),
      quest_marks: s.quests.includes(l.id) ? ["樣張任務"] : [],
      footprints: l.id === s.trail ? ["阿岳"] : [],
    }));
  return {
    region: m.region,
    name_zh: m.name_zh,
    level_zh: lv(m.level_min, m.level_max) ?? "",
    hub: false,
    locations,
    edges: m.edges,
    stones: s.stones.map(([loc, unlocked]) => ({ id: `stone_${loc}`, location: loc, unlocked, here: false })),
    can_teleport: true,
    teleport_problem_zh: null,
    art_url: null,
  };
}

const MAPS: Record<string, WorldMapView> = {};
for (const y of [cloudYaml, ashenYaml]) {
  const m = parse(y) as YamlMap;
  const st = STATES[m.region];
  if (st !== undefined) MAPS[m.region] = toView(m, st);
}

function region(over: Partial<AtlasRegionView> & { region: string; name_zh: string }): AtlasRegionView {
  return { status: "open", condition_zh: null, town: null, town_name_zh: null, current: false, can_teleport: false, free: false, ...over };
}

const ATLAS: AtlasView = {
  regions: [
    region({ region: "cloud_ridge", name_zh: "雲嶺", town: "mist_ferry", town_name_zh: "霧渡鎮", current: true }),
    region({ region: "crystal_crown", name_zh: "晶冠城邦", status: "later", condition_zh: "之後的賽季" }),
    region({ region: "arcane_hub", name_zh: "魔導樞市", status: "later", condition_zh: "之後的賽季" }),
    new URLSearchParams(location.search).get("ashen") === "locked"
      ? region({ region: "ashen_waste", name_zh: "灰燼荒原", status: "locked", condition_zh: "世界事件：霧潮入侵", town: "ember_market", town_name_zh: "餘燼集" })
      : region({ region: "ashen_waste", name_zh: "灰燼荒原", town: "ember_market", town_name_zh: "餘燼集", can_teleport: true }),
    region({ region: "frost_tide", name_zh: "霜潮海境", status: "later", condition_zh: "之後的賽季" }),
  ],
  capital: region({ region: "capital", name_zh: "主城", town: "capital", town_name_zh: "樞島", can_teleport: true }),
  can_teleport: true,
  teleport_problem_zh: null,
  art_url: null,
  maps: Object.values(MAPS),
};

const which = new URLSearchParams(location.search).get("map") ?? "cloud_ridge";
const log = (what: string) => () => console.info(what);

function Gallery() {
  if (which === "atlas") {
    const here = MAPS.cloud_ridge;
    if (here === undefined) return null;
    return <AtlasMap atlas={ATLAS} map={here} busy={false} onOpenRegion={(r) => location.assign(`?map=${r}`)} onTeleport={(r) => console.info("teleport", r)} onClose={log("close")} />;
  }
  const m = MAPS[which];
  if (m === undefined) return <p>沒有這張圖：{which}</p>;
  return <RegionMap map={m} busy={false} onTeleport={(to) => console.info("teleport", to)} onAtlas={() => location.assign("?map=atlas")} onClose={log("close")} />;
}

const root = document.getElementById("root");
if (root !== null) createRoot(root).render(<Gallery />);
