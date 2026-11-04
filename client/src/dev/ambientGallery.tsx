// 開發用：Phase 6N-10 的 NPC 小動作、環境動態、介面動畫（開 `client/ambient-gallery.html`，pnpm dev 後 /ambient-gallery.html）。
// 不屬於正式 build；供美術 PM 驗收與截圖。地圖用真正的 BattleRenderer＋`fieldDrawModel`（假的 FieldView），介面用正式元件。
// `#all`（預設）：上面一張雲嶺小鎮（酒館、酒旗、燈籠、營火、竹叢、冰洞水波、薄霧；鐵匠、掌櫃、一般 NPC 各自的小動作），
//   下面一排介面動畫（傷害數字、暴擊、延遲血條、Lv 翻動、升級光柱、物品飛進背包），每 3 秒重播一次。
// `#npc`：只有地圖；`#ui`：只有介面。`?anim=0.1`：環境動態放慢 10 倍（傷害數字的時間照 playback）。
// `?still=1`：關掉待機與環境動態（對照用）。小動作的名字寫在每個 NPC 下面（只在這頁）。
import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import type { FieldView, Glossary, WorldInventory, WorldView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { setGlossary } from "../battle/glossary";
import type { FeedbackItem } from "../battle/feedback";
import { BattleRenderer } from "../render/BattleRenderer";
import { waitForFonts } from "../render/fontLoad";
import { DelayTrail, FlipNumber } from "../ui/MotionBits";
import { fieldDrawModel, fieldHighlights } from "../world/fieldModel";
import { ItemFly, LevelPillar } from "../world/GainEffects";
import "../styles/index.css";

setGlossary(glossary as unknown as Glossary);
await waitForFonts();

const MODE = decodeURIComponent(location.hash.slice(1)) || "all";
const STILL = new URLSearchParams(location.search).get("still") === "1";
const W = 12;
const H = 8;

/** 酒館 5×3（左上 [0,0]，門 [2,2]）＋右邊鐵匠攤、中間商店攤；南邊營火、竹叢、東北角冰洞。 */
function townField(): FieldView {
  const tiles = Array.from({ length: W * H }, (_, i) => {
    const x = i % W;
    const y = Math.floor(i / W);
    const wall = x < 5 && y < 3 && !(x === 2 && y === 2);
    const hole = (x === 10 || x === 11) && (y === 1 || y === 2);
    return { x, y, height: 0, terrain: wall ? "wall" : hole ? "ice_hole" : (x + y) % 5 === 0 ? "dirt" : "stone", surface: "none", walkable: !wall && !hole };
  });
  const grass = [
    [0, 6],
    [1, 7],
    [3, 7],
    [10, 5],
    [11, 6],
    [9, 7],
  ].map(([x, y], i) => ({ id: `g${i}`, kind: "grass", x: x!, y: y! }));
  return {
    map_id: "ambient_gallery",
    name_zh: "環境動態",
    region: "cloud_ridge",
    location: "ambient_gallery",
    interior: false,
    width: W,
    height: H,
    tiles,
    objects: [...grass, { id: "anvil", kind: "crate", x: 8, y: 3 }, { id: "stall", kind: "crate", x: 5, y: 4 }],
    buildings: [{ kind: "tavern", x: 0, y: 0, width: 5, height: 3 }],
    exits: [],
    doors: [{ id: "d", x: 2, y: 2, to: "x", to_name_zh: "酒館" }],
    stones: [],
    npcs: [
      { id: "smith_shi", name_zh: "石師傅", x: 8, y: 4, rank: "neutral", rank_zh: "中立", alert: null, alert_zh: null, look: null, portrait: null },
      { id: "shopkeeper_liu", name_zh: "柳掌櫃", x: 5, y: 5, rank: "neutral", rank_zh: "中立", alert: null, alert_zh: null, look: null, portrait: null },
      { id: "granny_du", name_zh: "渡婆婆", x: 2, y: 4, rank: "neutral", rank_zh: "中立", alert: null, alert_zh: null, look: null, portrait: null },
      { id: "acolyte_xiaolian", name_zh: "小蓮", x: 7, y: 6, rank: "neutral", rank_zh: "中立", alert: null, alert_zh: null, look: null, portrait: null },
    ],
    facilities: [
      { kind: "smithy", x: 8, y: 3 },
      { kind: "shop", x: 5, y: 4 },
    ],
    me: { x: 4, y: 6, facing: "e" },
    max_climb: 1,
    stone_targets: [],
    enemies: [],
    friends: [],
    campfires: [{ id: "c", x: 5, y: 7 }],
    event_mark: null,
    situation_objects: [],
    sneaking: false,
    sneak_cost: 1,
    sneak_problem_zh: null,
    footprints: [],
    note_stone: null,
  } as unknown as FieldView;
}

let renderer: BattleRenderer | null = null;

async function drawTown(host: HTMLElement): Promise<void> {
  const r = new BattleRenderer();
  renderer = r;
  await r.init(host);
  r.setScale(1.5);
  if (STILL) r.setIdle(false);
  const field = townField();
  r.draw(fieldDrawModel(field));
  r.setHighlights(fieldHighlights(field, null));
}

/** 每 3 秒在地圖上跳一次傷害數字（一般、暴擊、治療）。 */
function floats(): void {
  const items: FeedbackItem[] = [
    { kind: "float", pos: { x: 7, y: 6 }, text: "-12", tone: "damage", big: false, slot: 0 },
    { kind: "float", pos: { x: 2, y: 4 }, text: "-38", tone: "damage", big: true, slot: 0 },
    { kind: "float", pos: { x: 4, y: 6 }, text: "+9", tone: "heal", big: false, slot: 0 },
  ];
  renderer?.playFeedback(items, 1200);
}

const inv = (n: number): WorldInventory =>
  ({ bag: [{ item: "herb", name_zh: "草藥", count: n, gear: false }, ...(n > 1 ? [{ item: "blade", name_zh: "短刀", count: 1, gear: true }] : [])], pouch: [], equipment: [] }) as unknown as WorldInventory;

const fakeView = (level: number, hp: number, items: number): WorldView =>
  ({
    character: { character_id: "c1", name: "你", level, hp, max_hp: 100 },
    inventory: inv(items),
  }) as unknown as WorldView;

function UiStrip({ tick }: { tick: number }) {
  const level = 3 + tick;
  const hp = tick % 2 === 0 ? 100 : 55;
  const view = fakeView(level, hp, 1 + (tick % 2));
  const grid = { width: 3, height: 3, tiles: [] } as never;
  return (
    <div style={{ display: "flex", gap: 28, alignItems: "flex-start", marginTop: 16 }}>
      <div style={{ width: 220 }}>
        <h2>延遲血條（掉血時白色殘量慢慢縮回）</h2>
        <div className="stat-bar hp" style={{ width: 200 }} data-testid="gallery-hp">
          <DelayTrail ratio={hp / 100} />
          <i className="stat-bar-fill" style={{ width: `${hp}%` }} />
          <span className="stat-bar-text">
            {hp} / 100
          </span>
        </div>
        <h2 style={{ marginTop: 12 }}>HUD 的 Lv（升級時翻動）</h2>
        <span className="world-hud-lv" style={{ position: "static", fontSize: 16, padding: "2px 8px" }}>
          Lv <FlipNumber value={level} />
        </span>
      </div>
      <div style={{ position: "relative", width: 160, height: 190 }}>
        <h2>升級光柱</h2>
        <div style={{ position: "absolute", left: 0, top: 30, width: 144, height: 150, background: "#3b4a3a", borderRadius: 6 }}>
          <LevelPillar view={view} grid={grid} at={{ x: 1, y: 1 }} scale={1} />
        </div>
      </div>
      <div style={{ position: "relative", width: 360, height: 190, background: "#22262c", borderRadius: 6 }}>
        <h2 style={{ margin: 6 }}>拿到物品：圖示飛進背包</h2>
        <div className="world-hud" style={{ pointerEvents: "auto" }}>
          <button type="button" className="world-hud-btn" data-hud="btn-bag" style={{ position: "absolute", right: 14, bottom: 12, width: 40, height: 40 }} aria-label="背包">
            袋
          </button>
          <ItemFly view={view} />
        </div>
      </div>
    </div>
  );
}

function App() {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => {
      setTick((t) => t + 1);
      floats();
    }, 3000);
    return () => window.clearInterval(timer);
  }, []);
  return MODE === "npc" ? null : <UiStrip tick={tick} />;
}

const page = document.getElementById("root")!;
if (MODE !== "ui") {
  const h = document.createElement("h2");
  h.textContent = "雲嶺小鎮：石師傅（鐵匠：搥打、擦汗）、柳掌櫃（掌櫃：擦桌子）、渡婆婆、小蓮（一般：張望、伸懶腰、搔頭）；酒旗、燈籠、營火、竹叢、冰洞水波、薄霧";
  page.before(h);
  const host = document.createElement("div");
  page.before(host);
  await drawTown(host);
}
createRoot(page).render(<App />);
