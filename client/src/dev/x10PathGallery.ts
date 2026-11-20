// 開發用：X10-3d 走路預覽的傷害範圍（開 `client/dev/x10-3d-path.html`；自己的 vite 後 /dev/x10-3d-path.html?mute=1）。不屬於正式 build。
// 目前的內容沒有敵方陷阱，實機走不出「陷阱 −a–b」（藉機攻擊落空時沒有最小值，只寫最大值），所以用手寫的路徑預覽
// （和 `pathPreview.test.ts` 的冰後陷阱同一種形狀），經過真的 `pathDraw` ＋ `BattleRenderer.setHighlights` 畫在戰場上。
// 參數：&w=1600|800（地圖縮放照美術移植需求 2.3：1600＝1.308、800＝0.531）。畫好後 `document.body.dataset.ready = "1"`。
import type { BattleView, Glossary, TileView, UnitView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { BATTLE_DRAW, buildDrawModel } from "../battle/drawModel";
import { setGlossary } from "../battle/glossary";
import { type PathEvent, type PathPreview, type PathStep, pathDraw } from "../battle/pathPreview";
import { tile, unit } from "../battle/testFixtures";
import type { Highlights } from "../render/battle/highlightLayer";
import { BattleRenderer } from "../render/BattleRenderer";
import { waitForFonts } from "../render/fontLoad";

setGlossary(glossary as unknown as Glossary);
await waitForFonts();

const q = new URLSearchParams(location.search);
const W = q.get("w") === "800" ? 800 : 1600;
const SCALE = W === 800 ? 0.531 : 1.308;
const HERO = "unit_0001";
const COLS = 10;
const ROWS = 3;

function ev(kind: PathEvent["kind"], extra: Partial<PathEvent> = {}): PathEvent {
  return { kind, certain: true, other_id: null, status_id: null, surface: null, pos: null, amount_min: null, amount_max: null, chance_permille: null, detail: null, ...extra };
}

function step(index: number, x: number, extra: Partial<PathStep> = {}): PathStep {
  return { pos: [x, 1], index, surface: "none", trap: false, reach: "certain", events: [], ...extra };
}

// 第 3 格踩到看得見的陷阱：傷害 60–140（最少／最多後果兩次模擬）＋可能定身
const steps: PathStep[] = [
  step(0, 0),
  step(1, 1),
  step(2, 2),
  step(3, 3, { trap: true, events: [ev("trap", { other_id: "trap_1" }), ev("damage", { other_id: "trap_1", amount_min: 60, amount_max: 140 }), ev("status", { status_id: "rooted", certain: false })] }),
  step(4, 4),
];
const last = steps[steps.length - 1]!;
const pv = {
  unit_id: HERO, path: steps.map((s) => s.pos), legal_length: steps.length, reachable: true, reason: null, steps,
  stop: last.pos, worst_stop: [3, 1], stops: [last.pos, [3, 1]], stop_certain: false, certain: false, move_cost: steps.length - 1, slip_runs: [],
} as unknown as PathPreview;

const tiles: TileView[] = [];
for (let y = 0; y < ROWS; y++) for (let x = 0; x < COLS; x++) tiles.push(tile(x, y, { terrain: "stone", height: 0 } as Partial<TileView>));
const hero = unit(HERO, "ally", 0, 1, { template_id: "hero_fighter", name_zh: "冒險者", facing: "east", hp: 400, max_hp: 400 } as Partial<UnitView>);
const view = {
  team: "ally", map_id: "x10_3d", map_name_zh: "石地", width: COLS, height: ROWS, tiles, objects: [], units: [hero], traps: [],
  turn_order: [HERO], active_unit: HERO, round: 1, max_rounds: 30, weather_id: null, weather_name_zh: null,
  objective: { kind: "eliminate", tiles: [], rounds: null, leader_retreat: false }, ended: false, winner: null, end_reason: null, pending: null,
  source_wells: [], zones: [], runes: [], summon_command_ap_cost: 1, summon_infuse_ap_cost: 1,
} as unknown as BattleView;

const host = document.createElement("div");
const cell = document.createElement("div");
cell.className = "cell";
const title = document.createElement("h2");
title.textContent = `走路預覽：陷阱的傷害範圍用「–」（${W} 寬、地圖縮放 ${SCALE}）`;
document.body.append(title, cell);
cell.appendChild(host);
const r = new BattleRenderer();
await r.init(host);
r.setIdle(false);
r.setScale(SCALE);
r.draw(buildDrawModel(view, HERO, null, undefined, BATTLE_DRAW));
const hl: Highlights = {
  moves: tiles.filter((t) => t.y === 1 && t.x > 0).map((t) => ({ x: t.x, y: t.y })),
  attacks: [], directions: [], preview: [], telegraph: [], focus: null, hover: { x: 4, y: 1 }, overlays: [], picked: [],
  path: pathDraw(pv),
};
r.setHighlights(hl);
const cap = document.createElement("p");
cap.className = "cap";
cap.textContent = `小牌字：${hl.path?.tags.map((t) => t.text).join("／") ?? ""}（真的 pathDraw）`;
cell.appendChild(cap);
document.body.dataset.ready = "1";
