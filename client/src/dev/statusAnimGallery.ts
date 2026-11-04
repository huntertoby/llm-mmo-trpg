// 開發用：狀態動作與地表動畫（Phase 6N-9）。開 `client/status-anim-gallery.html`（pnpm dev 後 /status-anim-gallery.html）。
// 不屬於正式 build；供美術 PM 驗收、截圖與量 FPS。`?anim=0.1` 慢動作；`?cell=88` 放大。
// `#status`（預設）：8 個人各有一種狀態（燃燒、冰凍、中毒、暈眩、定身、隱身、潮濕（站在水上）、帶電），旁邊有水面、油面、火面；
// `#spread`：一排油從左端的火燒過去＋一整塊油同時點燃（從中間往外）＋水面消失、冰變水，每 3 秒重播；
// `#stack`：#perf 的場景（疊兩種狀態）；
// `#perf`：8 個人都有狀態（含疊兩種），動畫關掉 4 秒 vs 開著 20 秒的 FPS、貼圖數（同 walk-gallery #idle 的量法）。
// `window.__r`：繪製器（截圖腳本用 `__r.motion.setClock(ms)` 固定相位）。
import type { BattleView, Glossary, TileView, UnitView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { buildDrawModel } from "../battle/drawModel";
import { setGlossary } from "../battle/glossary";
import { tile, unit } from "../battle/testFixtures";
import { BattleRenderer } from "../render/BattleRenderer";

setGlossary(glossary as unknown as Glossary);

const MODE = decodeURIComponent(location.hash.slice(1)) || "status";
const N = 12;
const HERO = "unit_0001";
const CELL = Number(new URLSearchParams(location.search).get("cell") ?? "52") || 52;

declare global {
  interface Window {
    __r?: BattleRenderer;
    __done?: boolean;
    __spreadB?: () => void;
  }
}

const st = (...ids: string[]) => ids.map((status_id) => ({ status_id, remaining: 2, source_id: null, amount: null, charge_tiles: [], cost_status: false })) as unknown as UnitView["statuses"];

type Surf = Record<string, string>;

function grid(surf: Surf): TileView[] {
  const tiles: TileView[] = [];
  for (let y = 0; y < N; y++) {
    for (let x = 0; x < N; x++) {
      tiles.push(tile(x, y, { terrain: (x + y) % 7 === 0 ? "dirt" : "grass", surface: (surf[`${x},${y}`] ?? "none") as TileView["surface"] } as Partial<TileView>));
    }
  }
  return tiles;
}

function view(units: UnitView[], surf: Surf): BattleView {
  return {
    team: "ally", map_id: "status_anim_gallery", map_name_zh: "狀態動作", width: N, height: N, tiles: grid(surf), objects: [], units, traps: [],
    turn_order: [HERO], active_unit: null, round: 1, max_rounds: 30, weather_id: null, weather_name_zh: null,
    objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null,
    source_wells: [], zones: [], runes: [],
  } as unknown as BattleView;
}

const block = (x0: number, y0: number, x1: number, y1: number, s: string): Surf => {
  const out: Surf = {};
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) out[`${x},${y}`] = s;
  return out;
};

/** 8 個人，各一種狀態；潮濕的站在水上。 */
function statusUnits(extra = false): UnitView[] {
  const fig = (id: string, team: "ally" | "enemy", x: number, y: number, name: string, ids: string[], tpl = "hero_fighter") =>
    unit(id, team, x, y, { template_id: tpl, name_zh: name, facing: team === "ally" ? "east" : "west", statuses: st(...ids) });
  return [
    fig(HERO, "ally", 1, 2, "燃燒", extra ? ["burning", "stun"] : ["burning"]),
    fig("unit_0002", "ally", 4, 2, "冰凍", ["frozen"], "hero_mage"),
    fig("unit_0003", "ally", 7, 2, "中毒", extra ? ["poison", "root"] : ["poison"], "hero_archer"),
    fig("unit_0004", "enemy", 10, 2, "暈眩", ["stun"], "t"),
    fig("unit_0005", "ally", 1, 6, "定身", extra ? ["root", "shielded_charged"] : ["root"]),
    fig("unit_0006", "enemy", 4, 6, "隱身", ["concealed"], "t"),
    fig("unit_0007", "ally", 7, 6, "潮濕", extra ? ["poison"] : [], "hero_mage"),
    fig("unit_0008", "enemy", 10, 6, "帶電", extra ? ["shielded_charged", "burning"] : ["shielded_charged"], "t"),
  ];
}

const STATUS_SURF: Surf = { ...block(6, 5, 8, 7, "water"), ...block(1, 9, 3, 10, "oil"), ...block(5, 9, 6, 10, "fire"), ...block(8, 9, 10, 10, "water") };

async function show(model: BattleView): Promise<BattleRenderer> {
  const box = document.createElement("div");
  box.className = "scene";
  document.body.appendChild(box);
  const r = new BattleRenderer();
  await r.init(box);
  r.setScale(CELL / 48);
  r.draw(buildDrawModel(model, HERO));
  window.__r = r;
  return r;
}

function caption(text: string, legend = ""): void {
  const h = document.createElement("h2");
  h.textContent = text;
  document.body.prepend(h);
  if (legend !== "") {
    const p = document.createElement("p");
    p.className = "legend";
    p.textContent = legend;
    h.after(p);
  }
}

const SPREAD_A: Surf = { "0,4": "fire", ...block(1, 4, 8, 4, "oil"), ...block(3, 7, 7, 9, "oil"), "10,2": "water", "6,1": "ice" };
const SPREAD_B: Surf = { ...block(0, 4, 8, 4, "fire"), ...block(3, 7, 7, 9, "fire"), "6,1": "water" };

const spreadUnits = (): UnitView[] => [unit(HERO, "ally", 0, 1, { template_id: "hero_mage", name_zh: "法師", facing: "east" })];

function wait(ms: number): Promise<void> {
  return new Promise((r) => window.setTimeout(r, ms));
}

async function spread(): Promise<void> {
  caption("6N-9・火蔓延（左端的火沿油燒過去；下面一整塊同時點燃、從中間往外）、水面消失、冰變水（每 3 秒重播）");
  const r = await show(view(spreadUnits(), SPREAD_A));
  // `?still`：不自動重播，截圖腳本自己呼叫 `__spreadB()` 換成燒起來的畫面
  if (new URLSearchParams(location.search).has("still")) {
    window.__spreadB = () => r.draw(buildDrawModel(view(spreadUnits(), SPREAD_B), HERO));
    window.__done = true;
    return;
  }
  for (;;) {
    await wait(1200);
    r.draw(buildDrawModel(view(spreadUnits(), SPREAD_B), HERO));
    await wait(1800);
    r.draw(buildDrawModel(view(spreadUnits(), SPREAD_A), HERO));
  }
}

function fps(ms: number): Promise<{ fps: number; p95Ms: number }> {
  return new Promise((resolve) => {
    const gaps: number[] = [];
    let last = performance.now();
    const t0 = last;
    const tick = (now: number) => {
      gaps.push(now - last);
      last = now;
      if (now - t0 < ms) {
        requestAnimationFrame(tick);
        return;
      }
      const sorted = [...gaps].sort((x, y) => x - y);
      resolve({ fps: Number(((gaps.length * 1000) / (now - t0)).toFixed(1)), p95Ms: Number((sorted[Math.floor(sorted.length * 0.95)] ?? 0).toFixed(1)) });
    };
    requestAnimationFrame(tick);
  });
}

async function perf(): Promise<void> {
  caption("6N-9・8 人都有狀態（含疊兩種）＋水油火面：動畫關 4 秒 vs 開 20 秒的 FPS 與貼圖數（待機照開）");
  const v = view(statusUnits(true), STATUS_SURF);
  const r = await show(v);
  const out = document.createElement("div");
  out.id = "perf";
  document.body.appendChild(out);
  r.motion.force(false);
  await fps(1000);
  const off = await fps(4000);
  const before = { art: r.textureCount(), ...r.motion.stats() };
  r.motion.force(true);
  const on = await fps(20000);
  const after = { art: r.textureCount(), ...r.motion.stats() };
  r.draw(buildDrawModel(v, HERO));
  await fps(500);
  const redrawn = { art: r.textureCount(), ...r.motion.stats() };
  out.textContent = JSON.stringify({ grid: `${N}x${N}`, cell: CELL, dpr: window.devicePixelRatio, units: v.units.length, animOff: off, animOn20s: on, textures: { before, after20s: after, afterRedraw: redrawn } }, null, 1);
  window.__done = true;
}

async function main(): Promise<void> {
  if (MODE === "spread") return spread();
  if (MODE === "perf") return perf();
  if (MODE === "stack") {
    caption("6N-9・疊兩種狀態（燃燒＋暈眩、中毒＋定身、定身＋帶電、帶電＋燃燒、中毒＋潮濕）", "#perf 量測用的同一個場景。");
    await show(view(statusUnits(true), STATUS_SURF));
    window.__done = true;
    return;
  }
  caption(
    "6N-9・狀態動作（8 種）與水面、油面、火面",
    "上排：燃燒、冰凍、中毒、暈眩；中排：定身、隱身、潮濕（站在水上）、帶電。下排：油面、火面、水面。",
  );
  await show(view(statusUnits(), STATUS_SURF));
  window.__done = true;
}

void main();
