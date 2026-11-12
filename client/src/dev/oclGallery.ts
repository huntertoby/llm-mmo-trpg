// 開發用：OCL-1 被遮擋剪影外框（開 `client/dev/ocl-gallery.html`；pnpm dev 後 /dev/ocl-gallery.html）。不屬於正式 build。
// 用真的 `buildDrawModel` 與 `BattleRenderer.draw` 畫手寫的場面（比照 `practiceGallery.ts`），情境照樣張
// `docs/art/sample/occlude-outline.html`（第 3 版）：
// - `?scene=boss`：灰燼之心擋友方、擋敵方；碎晶之主擋友方、擋敵方（CB-4：頭目站在目標南邊）。
// - `scene=pairs`：一般單位互擋 8 對（全部不畫，前排不是大型）。
// - `scene=collide`：第 2 列＝矮異形在高台的人後面（只有 6F-22 舊剪影）；第 4 列＝頭目＋小兵一起擋（外框只在頭目身上）；
//   另一列＝被頭目擋住、南邊又是高台（6F-22 也成立）：只有新外框。
// - `scene=concealed`：隱匿中的敵人在頭目後面（不畫）＋沒隱匿的對照。
// - `scene=team`：友／敵／第三方／召喚物各被頭目擋。
// - `scene=field`：熔心坑 12×12，12 個單位＋灰燼之心（CB-4 情境）。
// 參數：`&w=1600|800`（照 `fitScale` 與 HUD 讓位算「熔心坑 12×12」的地圖縮放，每個場面都用它；預設 1600）、`&scale=`（另給縮放）、`&ocl=0|1`（關／開外框，效能對照；只有開發頁有）、
// `&measure=1`（每個單位的面積、比例、畫不畫寫進 `body.dataset.measure` 與頁上表格，對照樣張 `?part=measure`）、
// `&perf=1`（效能量測，結果在 `body.dataset.perf`）、`&bare=1`（截圖用：不寫標題、不留邊）。待機關掉（畫面固定；`perf` 時開）。
// 畫好後 `document.body.dataset.ready = "1"`。
import type { BattleView, Glossary, TileView, UnitView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { BATTLE_DRAW, buildDrawModel } from "../battle/drawModel";
import { setGlossary } from "../battle/glossary";
import { fitScale, hudSideInsets } from "../battle/stageLayout";
import { tile, unit } from "../battle/testFixtures";
import { BattleRenderer } from "../render/BattleRenderer";
import { waitForFonts } from "../render/fontLoad";
import { UNIT_DOLLS } from "../render/testDolls";

setGlossary(glossary as unknown as Glossary);
await waitForFonts();

const params = new URLSearchParams(location.search);
const SCENE = params.get("scene") ?? "boss";
const W = params.get("w") === "800" ? 800 : 1600;
const H = W === 800 ? 600 : 900;
const OCL = params.get("ocl") !== "0";
const MEASURE = params.get("measure") === "1";
const PERF = params.get("perf") === "1";
if (params.get("bare") === "1") document.body.classList.add("bare");

const HERO = "unit_0001";
type Who = "hero" | "archer" | "mage" | "bandit" | "shield" | "lizard" | "ooze" | "pylon" | "golem" | "ah" | "sl";
const TEMPLATE: Record<Who, string> = {
  hero: "hero_fighter",
  archer: "hero_archer",
  mage: "hero_mage",
  bandit: "bandit",
  shield: "bandit_shieldbearer",
  lizard: "ember_lizard",
  ooze: "magma_slug",
  pylon: "rift_pillar_thunder",
  golem: "rift_crystal_golem",
  ah: "ashen_heart",
  sl: "rift_shard_lord",
};
const ZH: Record<Who, string> = { hero: "主角", archer: "弓手", mage: "法師", bandit: "盜匪", shield: "持盾盜匪", lizard: "餘燼蜥", ooze: "熔岩蛞蝓", pylon: "晶塔", golem: "精英碎晶傀儡", ah: "灰燼之心", sl: "碎晶之主" };
const WEAPON: Partial<Record<Who, string>> = { archer: "bow", mage: "fire_staff", shield: "one_handed_sword", bandit: "dagger" };
const status = (status_id: string) => ({ status_id, remaining: 2, source_id: null, amount: null, blast_radius: null, charge_tiles: [], cost_status: false });

interface Spec {
  id: string;
  who: Who;
  team?: "ally" | "enemy" | "third";
  x: number;
  y: number;
  facing?: "east" | "west" | "north" | "south";
  statuses?: string[];
  summon?: boolean;
}

function unitOf(s: Spec): UnitView {
  const boss = s.who === "ah" || s.who === "sl";
  const team = s.team ?? (s.who === "hero" || s.who === "archer" || s.who === "mage" ? "ally" : "enemy");
  const over: Record<string, unknown> = {
    template_id: TEMPLATE[s.who],
    name_zh: ZH[s.who],
    facing: s.facing ?? (boss ? "north" : "south"),
    hp: 30,
    max_hp: 30,
    weapon_id: WEAPON[s.who] ?? "one_handed_sword",
    weapon_class: s.who === "archer" ? "ranged" : "melee",
    statuses: [...(s.statuses ?? []), ...(s.who === "ah" ? ["molten_shell"] : [])].map(status),
  };
  if (UNIT_DOLLS[TEMPLATE[s.who]] !== undefined && !s.who.startsWith("hero")) over.doll_look = UNIT_DOLLS[TEMPLATE[s.who]];
  if (boss) {
    over.tags = ["boss", "elite"];
    // 樣張：灰燼之心第 1 階段（熔殼）、碎晶之主第 2 階段
    over.boss_phase = s.who === "ah" ? { index: 1, total: 3, name_zh: "第 1 階段" } : { index: 2, total: 4, name_zh: "第 2 階段" };
  }
  if (s.who === "golem") over.tags = ["elite"];
  if (s.summon === true) Object.assign(over, { owner_id: HERO, summon_expires_round: 5, summon_look: { body: "beast", variant: "wolf", element: null, size: "medium", trait: null } });
  return unit(s.id, team, s.x, s.y, over as Partial<UnitView>);
}

interface Scene {
  cap: string;
  cols: number;
  rows: number;
  heights?: Record<string, number>;
  terrain?: (x: number, y: number) => string;
  units: Spec[];
}

function view(sc: Scene): BattleView {
  const tiles: TileView[] = [];
  for (let y = 0; y < sc.rows; y++) {
    for (let x = 0; x < sc.cols; x++) tiles.push(tile(x, y, { terrain: sc.terrain?.(x, y) ?? "stone", height: sc.heights?.[`${x},${y}`] ?? 0 } as Partial<TileView>));
  }
  const units = sc.units.map(unitOf);
  const first = units.find((u) => u.team === "ally")?.id ?? units[0]!.id;
  return {
    team: "ally", map_id: "ocl", map_name_zh: "外框", width: sc.cols, height: sc.rows, tiles, objects: [], units, traps: [],
    turn_order: [first], active_unit: null, round: 2, max_rounds: 30, weather_id: null, weather_name_zh: null,
    objective: { kind: "eliminate", tiles: [], rounds: null, leader_retreat: false }, ended: false, winner: null, end_reason: null, pending: null,
    source_wells: [], zones: [], runes: [], summon_command_ap_cost: 1, summon_infuse_ap_cost: 1,
  } as unknown as BattleView;
}

/** 目標在 (c, 1)、前排在 (c, 2)；`h` ＝ 前排那格的高度。 */
function duo(cap: string, back: Omit<Spec, "id" | "x" | "y">, front: Omit<Spec, "id" | "x" | "y">, h = 0, cols = 5, more: Spec[] = []): Scene {
  const c = Math.floor(cols / 2);
  return { cap, cols, rows: 4, heights: h > 0 ? { [`${c},2`]: h } : {}, units: [{ id: "t", ...back, x: c, y: 1 }, { id: "f", ...front, x: c, y: 2 }, ...more] };
}

const SCENES: Record<string, () => Scene[]> = {
  boss: () => [
    duo("灰燼之心擋友方（主角）", { who: "hero" }, { who: "ah" }),
    duo("灰燼之心擋敵方（餘燼蜥）", { who: "lizard" }, { who: "ah", team: "ally" }),
    duo("碎晶之主擋友方（法師）", { who: "mage" }, { who: "sl" }),
    duo("碎晶之主擋敵方（持盾盜匪）", { who: "shield" }, { who: "sl", team: "ally" }),
  ],
  pairs: () => [
    duo("人擋人・平地", { who: "archer" }, { who: "shield" }, 0, 3),
    duo("人擋人・前排高 3 階", { who: "archer" }, { who: "shield" }, 3, 3),
    duo("人擋人・法杖、前排高 3 階", { who: "archer" }, { who: "mage", team: "enemy" }, 3, 3),
    duo("人擋異形（蛞蝓）・平地", { who: "ooze" }, { who: "hero" }, 0, 3),
    duo("人擋異形（蛞蝓）・前排高 3 階", { who: "ooze" }, { who: "shield", team: "ally" }, 3, 3),
    duo("異形擋人・精英傀儡・平地", { who: "archer" }, { who: "golem" }, 0, 3),
    duo("異形擋人・精英傀儡・高 2 階", { who: "archer" }, { who: "golem" }, 2, 3),
    duo("異形擋異形・傀儡擋蛞蝓・平地", { who: "ooze" }, { who: "golem" }, 0, 3),
  ],
  collide: () => [
    duo("第 2 列：蛞蝓在高 3 主角後（只有舊剪影）", { who: "ooze" }, { who: "hero" }, 3, 3),
    duo("第 2 列：晶塔在高 3 主角後（未達門檻：舊剪影）", { who: "pylon" }, { who: "hero" }, 3, 3),
    duo("被頭目擋、南邊又是高台（6F-22 也成立）：只有新外框", { who: "hero" }, { who: "ah" }, 2),
    { cap: "第 4 列：頭目＋小兵一起擋（外框只在頭目身上）", cols: 5, rows: 4, units: [{ id: "t", who: "lizard", x: 2, y: 1 }, { id: "b", who: "ah", x: 1, y: 2, team: "ally" }, { id: "g", who: "golem", x: 2, y: 2, team: "ally" }] },
  ],
  concealed: () => [
    { cap: "左：隱匿中的敵人（不畫）｜右：沒隱匿的敵人（畫）", cols: 9, rows: 4, units: [{ id: "c", who: "bandit", x: 2, y: 1, statuses: ["concealed"] }, { id: "b1", who: "ah", x: 2, y: 2, team: "ally" }, { id: "n", who: "bandit", x: 6, y: 1 }, { id: "b2", who: "ah", x: 6, y: 2, team: "ally" }] },
  ],
  team: () => [
    duo("友方", { who: "hero" }, { who: "ah" }),
    duo("敵方", { who: "bandit" }, { who: "ah", team: "ally" }),
    duo("第三方", { who: "bandit", team: "third" }, { who: "ah", team: "ally" }),
    duo("召喚物（狼）", { who: "hero", summon: true }, { who: "ah" }),
  ],
  field: () => [
    {
      cap: "熔心坑 12×12：灰燼之心（5, 5）正北是主角（CB-4），旁邊同排的餘燼蜥",
      cols: 12,
      rows: 12,
      terrain: (x, y) => (x === 0 || y === 0 || x === 11 || y === 11 ? "wall" : x === 1 || y === 1 || x === 10 || (y === 10 && x !== 3 && x !== 8) ? "lava" : "stone"),
      units: [
        { id: "b", who: "ah", x: 5, y: 5 },
        { id: "l1", who: "lizard", x: 3, y: 5, facing: "east" },
        { id: "l2", who: "lizard", x: 7, y: 5, facing: "west" },
        { id: HERO, who: "hero", x: 5, y: 4, statuses: ["burning"] },
        { id: "m", who: "mage", x: 4, y: 7 },
        { id: "a", who: "archer", x: 6, y: 8 },
        { id: "l3", who: "lizard", x: 6, y: 4, facing: "west" },
        { id: "s1", who: "shield", x: 3, y: 2 },
        { id: "s2", who: "bandit", x: 8, y: 2 },
        { id: "o1", who: "ooze", x: 3, y: 9 },
        { id: "g1", who: "golem", x: 8, y: 9 },
        { id: "p1", who: "pylon", x: 9, y: 7 },
        { id: "a2", who: "archer", x: 2, y: 7, team: "ally" },
      ],
    },
  ],
};

/** 1600×900／800×600 視窗的地圖縮放（同 `useBoardViewport`：讓開 HUD 左右欄與上方順序列，再留 16）。 */
function scaleFor(model: Parameters<typeof fitScale>[1]): number {
  const ins = hudSideInsets(W);
  return fitScale({ width: W - ins.left - ins.right - 16, height: H - ins.top - 16 }, model);
}

const median = (xs: number[]): number => [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)] ?? 0;
const p95 = (xs: number[]): number => [...xs].sort((a, b) => a - b)[Math.min(xs.length - 1, Math.floor(xs.length * 0.95))] ?? 0;
const nextFrame = (): Promise<number> => new Promise((r) => requestAnimationFrame(r));

const REF_SCALE = scaleFor(buildDrawModel(view(SCENES.field!()[0]!), HERO, null, undefined, BATTLE_DRAW));
const measure: Array<Record<string, unknown>> = [];
const row = document.createElement("div");
row.className = "row";
document.body.appendChild(Object.assign(document.createElement("h2"), { textContent: `OCL-1 被遮擋剪影外框：scene=${SCENE}、${W} 寬、外框${OCL ? "開" : "關"}` }));
document.body.appendChild(row);
const renderers: BattleRenderer[] = [];
for (const sc of (SCENES[SCENE] ?? SCENES.boss!)()) {
  const box = document.createElement("div");
  box.className = "scene";
  const host = document.createElement("div");
  box.appendChild(host);
  box.appendChild(Object.assign(document.createElement("p"), { className: "cap", textContent: sc.cap }));
  row.appendChild(box);
  const r = new BattleRenderer();
  await r.init(host);
  r.outlinesEnabled = OCL;
  r.outlineMeasure = MEASURE;
  r.setIdle(PERF);
  const model = buildDrawModel(view(sc), HERO, null, undefined, BATTLE_DRAW);
  // 小場面一律用「熔心坑 12×12 在這個寬度」的實際地圖縮放（外框線寬照真的戰場）；`&scale=` 可以另給
  const scale = Number(params.get("scale")) || REF_SCALE;
  r.setScale(scale);
  r.draw(model);
  renderers.push(r);
  const st = r.occlusionStats();
  const names = new Map(sc.units.map((u) => [u.id, ZH[u.who]]));
  for (const e of st.entries) measure.push({ scene: sc.cap, id: e.id, who: names.get(e.id), area: e.area, ratio: Math.round(e.ratio * 10000) / 10000, drawn: e.drawn, skip: e.skip ?? null, scale: Math.round(scale * 1000) / 1000 });
  if (PERF) {
    const first = st.ms;
    const all: number[] = [];
    const ocl: number[] = [];
    for (let i = 0; i < 55; i++) {
      const t0 = performance.now();
      r.draw(model);
      const t = performance.now() - t0;
      if (i >= 5) {
        all.push(t);
        ocl.push(r.occlusionStats().ms);
      }
    }
    const gaps: number[] = [];
    let last = await nextFrame();
    const until = last + 10000;
    while (last < until) {
      const now = await nextFrame();
      gaps.push(now - last);
      last = now;
    }
    const tex = (window as unknown as { __texStats?: () => { count: number; bytes: number } }).__texStats?.() ?? null;
    const fin = r.occlusionStats();
    document.body.dataset.perf = JSON.stringify({
      ocl: OCL, w: W, scale, dpr: devicePixelRatio, firstOutlineMs: first,
      drawMedian: median(all), drawP95: p95(all), outlineMedian: median(ocl), outlineP95: p95(ocl),
      frameMedian: median(gaps), frameP95: p95(gaps), frames: gaps.length, tex, alphaReads: fin.alphaReads, alphaMasks: fin.alphaMasks,
      drawn: fin.entries.filter((e) => e.drawn).map((e) => e.id),
    });
  }
}
if (MEASURE) {
  document.body.dataset.measure = JSON.stringify(measure);
  const table = document.createElement("table");
  table.innerHTML = `<tr><th>場面</th><th>id</th><th>單位</th><th>面積（模型 px²）</th><th>大型前排比例</th><th>畫</th><th>沒算的原因</th></tr>${measure.map((m) => `<tr><td>${String(m.scene)}</td><td>${String(m.id)}</td><td>${String(m.who)}</td><td>${m.area ?? "—"}</td><td>${(Number(m.ratio) * 100).toFixed(1)}%</td><td>${m.drawn ? "畫" : ""}</td><td>${m.skip ?? ""}</td></tr>`).join("")}`;
  document.body.appendChild(table);
}
(window as unknown as { __ocl?: unknown }).__ocl = { renderers, measure };
document.body.dataset.ready = "1";
