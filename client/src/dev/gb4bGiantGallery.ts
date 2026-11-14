// 開發用：GB-4b 3×3 巨型灰燼之心的戰場畫法（開 `client/dev/gb4b-giant.html`；自己的 vite 後 /dev/gb4b-giant.html?mute=1）。不屬於正式 build。
// 一律用真的 `buildDrawModel`、`BattleRenderer.draw`／`setHighlights`、部位格標示 `giantMarksOf`（和點擊判定同一份 tiles）與
// 破壞演出同一組函式（`setPartFx` ＋ `partBreakFx.giantBreakCanvas`）畫手寫的場面（比照 `pb1eGallery.ts`）；外觀取
// `render/fixtures/unitDolls.json`。每格＝真 1 倍的畫布（`extract`，裝置像素比 1 時＝畫面像素）＋可選的最近鄰放大。
// 參數：
//   ?set=sprites|marks|break|after|shed|field|hud   （逗號接多段；預設 sprites）
//   &w=1600|800   地圖縮放照美術移植需求 2.3（1600＝1.308、800＝0.531）；`&scale=` 另給
//   &zoom=<k>     最近鄰放大倍數（預設 0＝不放大；800 的立繪、殼縫格、「破」字特寫用 4）
//   &grid=0       不畫 3×3 格線（預設畫：佔格外框＋格線，看核心、殼窩只在中排）
// 畫好後 `document.body.dataset.ready = "1"`。
import { Rectangle, Sprite } from "pixi.js";
import type { Action, BattleView, Facing, Glossary, PartOption, PartView, Pos, TileView, UnitView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { classifyActions } from "../battle/actions";
import { BATTLE_DRAW, buildDrawModel } from "../battle/drawModel";
import { setGlossary } from "../battle/glossary";
import { giantBreakFxOf } from "../battle/partStrip";
import { tile, unit } from "../battle/testFixtures";
import type { TileClickState } from "../battle/tileClick";
import type { Highlights } from "../render/battle/highlightLayer";
import { giantMarksOf } from "../render/battle/partTileMarks";
import { BattleRenderer } from "../render/BattleRenderer";
import dolls from "../render/fixtures/unitDolls.json";
import { waitForFonts } from "../render/fontLoad";
import { giantBreakCanvas } from "../render/partBreakFx";
import { GIANT_ANCHOR_DY, GIANT_FX_BOX, GIANT_PART_OF } from "../render/qBossGiant";

setGlossary(glossary as unknown as Glossary);
await waitForFonts();

const q = new URLSearchParams(location.search);
const SETS = (q.get("set") ?? "sprites").split(",");
const W = q.get("w") === "800" ? 800 : 1600;
const SCALE = Number(q.get("scale")) || (W === 800 ? 0.531 : 1.308);
const ZOOM = Number(q.get("zoom") ?? 0);
const GRID = q.get("grid") !== "0";
const T = 48;

const BOSS = "heart";
const HERO = "unit_0001";
const PHASE_ZH = ["", "殼", "呼吸", "熔毀"];
const st = (s: string): Record<string, unknown> => ({ status_id: s, remaining: 2, source_id: null, amount: null, blast_radius: null, charge_tiles: [], cost_status: false });
const P = (x: number, y: number): Pos => ({ x, y });

type PartSt = "ok" | "dmg" | "broken" | "hidden";
interface HeartSpec {
  x?: number;
  y?: number;
  phase?: 1 | 2 | 3;
  shell?: boolean;
  vent?: PartSt;
  seam?: PartSt;
  core?: PartSt;
  team?: "enemy" | "ally";
}

function part(id: string, name: string, s: PartSt, tiles: Pos[], over: Partial<PartView> = {}): PartView {
  const hp = s === "ok" ? 32 : s === "dmg" ? 12 : s === "broken" ? 0 : null;
  return { id, name_zh: name, hp, max_hp: s === "hidden" ? null : 32, broken: s === "broken", exposed: s !== "hidden", reach: "any", break_lines_zh: [], tiles, ...over };
}

function heartOf(b: HeartSpec): UnitView {
  const x = b.x ?? 2;
  const y = b.y ?? 2;
  const phase = b.phase ?? 1;
  const tiles = [-1, 0, 1].flatMap((dy) => [-1, 0, 1].map((dx) => P(x + dx, y + dy)));
  const over: Record<string, unknown> = {
    template_id: "ashen_heart",
    name_zh: "灰燼之心",
    facing: "south",
    hp: 120,
    max_hp: 160,
    weapon_id: "one_handed_sword",
    weapon_class: "melee",
    tags: ["boss", "elite"],
    doll_look: (dolls as Record<string, unknown>)["ashen_heart"],
    boss_phase: { index: phase, total: 3, name_zh: PHASE_ZH[phase] },
    statuses: (b.shell ?? phase === 1 ? ["molten_shell"] : []).map(st),
    footprint: 3,
    tiles,
    parts: [
      part("core", "核心", b.core ?? (phase === 1 ? "hidden" : "ok"), [P(x, y)]),
      part("shell_seam", "殼縫", b.seam ?? "ok", [P(x - 1, y), P(x + 1, y)], { counts_as_behind: true }),
      part("vent", "熔岩噴口", b.vent ?? "ok", [P(x - 1, y - 1), P(x, y - 1), P(x + 1, y - 1)], { reach: "ranged" }),
    ],
  };
  return unit(BOSS, b.team ?? "enemy", x, y, over as Partial<UnitView>);
}

function personAt(id: string, x: number, y: number, team: "ally" | "enemy", tpl = "hero_fighter", facing: Facing = "north", weaponClass = "melee"): UnitView {
  const over: Record<string, unknown> = { template_id: tpl, name_zh: id, facing, hp: 24, max_hp: 30, weapon_class: weaponClass, weapon_id: weaponClass === "ranged" ? "bow" : "one_handed_sword" };
  const look = (dolls as Record<string, unknown>)[tpl];
  if (look !== undefined && !tpl.startsWith("hero")) over.doll_look = look;
  return unit(id, team, x, y, over as Partial<UnitView>);
}

function viewOf(units: UnitView[], cols = 5, rows = 6, terrain?: (x: number, y: number) => string): BattleView {
  const tiles: TileView[] = [];
  for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) tiles.push(tile(x, y, { terrain: terrain?.(x, y) ?? "stone", height: 0 } as Partial<TileView>));
  return {
    team: "ally", map_id: "gb4b", map_name_zh: "熔心坑", width: cols, height: rows, tiles, objects: [], units, traps: [],
    turn_order: [units[0]!.id], active_unit: null, round: 4, max_rounds: 30, weather_id: null, weather_name_zh: null,
    objective: { kind: "eliminate", tiles: [], rounds: null, leader_retreat: false }, ended: false, winner: null, end_reason: null, pending: null,
    source_wells: [], zones: [], runes: [], summon_command_ap_cost: 1, summon_infuse_ap_cost: 1, region: "ashen_waste",
  } as unknown as BattleView;
}

const h = <K extends keyof HTMLElementTagNameMap>(tag: K, props: Partial<HTMLElementTagNameMap[K]> = {}, ...kids: (Node | string)[]): HTMLElementTagNameMap[K] => {
  const e = Object.assign(document.createElement(tag), props);
  e.append(...kids);
  return e;
};

type Pixi = {
  app: { renderer: { extract: { canvas(o: unknown): HTMLCanvasElement } }; stage: unknown };
  world: { y: number };
  setPartFx(id: string, fx: unknown): void;
  unitSprites: Map<string, { x: number; y: number }>;
  effectLayer(id: string): { addChild(n: unknown): void };
  art: { figureRes(n: number): number };
};

interface Cell {
  cap: string;
  view: BattleView;
  /** 畫完之後做的事（滑過、演出的格）。 */
  after?: (r: BattleRenderer) => void;
  /** 最近鄰放大的範圍（格；預設頭目 3×3 外擴半格）。 */
  zoomBox?: { x0: number; y0: number; x1: number; y1: number };
  /** 這一格的最近鄰倍數（覆蓋 `&zoom=`）。 */
  zoom?: number;
  /** 真 1 倍只取頭目一帶（格；連拍用，不放整張地圖）。 */
  crop?: { x0: number; y0: number; x1: number; y1: number };
}

/** 3×3 格線（佔格外框實線、格線虛線），畫在真 1 倍的畫布上。 */
function gridOn(c: HTMLCanvasElement, cx: number, cy: number, worldY: number): void {
  const g = c.getContext("2d")!;
  const s = SCALE * devicePixelRatio;
  g.save();
  g.strokeStyle = "rgba(120,220,255,0.9)";
  g.lineWidth = 1;
  for (let i = 0; i <= 3; i++) {
    const x = Math.round((cx - 1.5 + i) * T * s) + 0.5;
    const y = Math.round(((cy - 1.5 + i) * T + worldY) * s) + 0.5;
    g.setLineDash(i === 0 || i === 3 ? [] : [3, 3]);
    g.beginPath();
    g.moveTo(x, ((cy - 1.5) * T + worldY) * s);
    g.lineTo(x, ((cy + 1.5) * T + worldY) * s);
    g.stroke();
    g.beginPath();
    g.moveTo((cx - 1.5) * T * s, y);
    g.lineTo((cx + 1.5) * T * s, y);
    g.stroke();
  }
  // 錨點（南排南緣中點）
  g.setLineDash([]);
  g.fillStyle = "#7cf";
  const ax = cx * T * s;
  const ay = ((cy + 1.5) * T + worldY) * s;
  g.fillRect(Math.round(ax) - 2, Math.round(ay) - 2, 4, 4);
  g.restore();
}

function zoomOf(r: BattleRenderer, box: { x0: number; y0: number; x1: number; y1: number }, k: number): HTMLCanvasElement {
  const p = r as unknown as Pixi;
  const frame = new Rectangle(Math.round(box.x0 * T), Math.round(box.y0 * T + p.world.y), Math.round((box.x1 - box.x0) * T), Math.round((box.y1 - box.y0) * T));
  const src = p.app.renderer.extract.canvas({ target: p.app.stage, frame, resolution: devicePixelRatio * SCALE });
  const out = h("canvas", { width: src.width * k, height: src.height * k });
  const g = out.getContext("2d")!;
  g.imageSmoothingEnabled = false;
  g.drawImage(src, 0, 0, out.width, out.height);
  out.style.width = `${out.width / devicePixelRatio}px`;
  return out;
}

async function cellOf(c: Cell, row: HTMLElement): Promise<void> {
  const host = h("div");
  const box = h("div", { className: "cell" }, host);
  row.appendChild(box);
  const r = new BattleRenderer();
  await r.init(host);
  r.setIdle(false);
  r.setScale(SCALE);
  r.draw(buildDrawModel(c.view, HERO, null, undefined, BATTLE_DRAW));
  c.after?.(r);
  const p = r as unknown as Pixi;
  const scr = (r as unknown as { app: { renderer: { screen: { width: number; height: number } } } }).app.renderer.screen;
  const full = p.app.renderer.extract.canvas({ target: p.app.stage, frame: new Rectangle(0, 0, scr.width, scr.height), resolution: devicePixelRatio * SCALE });
  full.style.width = `${full.width / devicePixelRatio}px`;
  const b = c.view.units.find((u) => u.id === BOSS);
  if (GRID && b !== undefined) gridOn(full, b.pos.x + 0.5, b.pos.y + 0.5, p.world.y);
  host.replaceWith(c.crop === undefined ? full : zoomOf(r, c.crop, 1));
  const k = c.zoom ?? ZOOM;
  if (k > 0 && b !== undefined) box.appendChild(zoomOf(r, c.zoomBox ?? { x0: b.pos.x - 1.2, y0: b.pos.y - 1.9, x1: b.pos.x + 2.2, y1: b.pos.y + 2.2 }, k));
  r.destroy();
  box.appendChild(h("p", { className: "cap", textContent: c.cap }));
}

// ---- 部位格標示：選打它的動作（普攻），伺服器的部位選項 ----
const opt = (part_id: string, name_zh: string, reason: string | null): PartOption => ({ part_id, name_zh, ok: reason === null, reason_zh: reason });
const ALL_OK = [opt("core", "核心", null), opt("shell_seam", "殼縫", null), opt("vent", "熔岩噴口", null)];

function marksCell(cap: string, heart: HeartSpec, options: PartOption[], hover: Pos | null, ranged = false): Cell {
  const boss = heartOf(heart);
  const hero = personAt(HERO, 0, 2, "ally", "hero_fighter", "east", ranged ? "ranged" : "melee");
  const view = viewOf([hero, boss]);
  const attack: Action = { type: "attack", unit_id: HERO, target_id: BOSS };
  const state: Pick<TileClickState, "view" | "hero" | "canAct" | "copying" | "command" | "mode" | "hurlPick" | "classified" | "partActions"> = {
    view, hero, canAct: true, copying: false, command: null, mode: null, hurlPick: null,
    classified: classifyActions([attack], view, {}), partActions: [{ type: "attack", skill_id: null, target_id: BOSS, options }],
  };
  const marks = giantMarksOf(state, hover);
  const hl: Highlights = { moves: [], attacks: boss.tiles ?? [], directions: [], preview: [], telegraph: [], focus: null, hover, overlays: [], picked: [], giantMarks: marks };
  return { cap, view, after: (r) => r.setHighlights(hl), zoomBox: { x0: 0.9, y0: 0.9, x1: 4.1, y1: 4.1 } };
}

// ---- 破壞演出（和 `partBreakFx.giantBreakEffect` 同一組函式） ----
function breakCell(cap: string, before: HeartSpec, after: HeartSpec, partId: string, frame: number, side: -1 | 1, shed: boolean): Cell {
  // 播放時 `view` 在命中＋停頓後就是破了的樣子：演出前 4 格由 `PartFx` 蓋回（同正式播放）
  const view = viewOf([personAt(HERO, 4, 5, "ally"), heartOf(frame >= 4 ? after : after)]);
  return {
    cap,
    view,
    zoom: 0,
    crop: { x0: 0.3, y0: -1.7, x1: 4.7, y1: 4.1 },
    after: (r) => {
      const p = r as unknown as Pixi;
      p.setPartFx(BOSS, giantBreakFxOf(partId, frame, side, shed));
      if (frame >= 4) return;
      const res = p.art.figureRes(1);
      const cv = giantBreakCanvas({ phase: before.phase ?? 1, fx: { part: GIANT_PART_OF[partId]!, k: frame, side } }, res, SCALE);
      if (cv === null) return;
      const s = Sprite.from(cv);
      const at = p.unitSprites.get(BOSS)!;
      s.position.set(at.x + GIANT_FX_BOX.x, at.y + GIANT_ANCHOR_DY + GIANT_FX_BOX.y);
      s.width = GIANT_FX_BOX.w;
      s.height = GIANT_FX_BOX.h;
      p.effectLayer("effects").addChild(s);
    },
  };
}

const FRAME_ZH = ["1 命中", "2 裂開", "3 斷開", "4 落地", "5 定格"];

const SETS_OF: Record<string, () => Array<{ title: string; cells: Cell[] }>> = {
  sprites: () => [
    {
      title: `A1 六種外觀（三階段 × 熔殼在／不在），${W} 寬、地圖縮放 ${SCALE}、真 1 倍；青線＝3×3 佔格與格線、青點＝錨點`,
      cells: ([1, 2, 3] as const).flatMap((ph) => [true, false].map((shell) => ({ cap: `第 ${ph} 階段（${PHASE_ZH[ph]}）・熔殼${shell ? "在" : "不在"}`, view: viewOf([personAt(HERO, 0, 5, "ally"), heartOf({ phase: ph, shell })]) }))),
    },
  ],
  marks: () => [
    {
      title: `A2 九種狀態（${W} 寬、真 1 倍）`,
      cells: [
        marksCell("① 完好（近戰：殼縫有背刺記號）", { phase: 2 }, ALL_OK, null),
        marksCell("② 滑過噴口（三格一起亮、身上噴口亮起）", { phase: 2 }, ALL_OK, P(2, 1)),
        marksCell("③ 滑過殼縫（東西兩格一起亮）", { phase: 2 }, ALL_OK, P(1, 2)),
        marksCell("④ 滑過核心", { phase: 2 }, ALL_OK, P(2, 2)),
        marksCell("⑤ 滑過前殼＝打本體（目標紅框框整個 3×3）", { phase: 2 }, ALL_OK, P(2, 3)),
        marksCell("⑥ 打不到：噴口×近戰、殼縫射程、核心視線", { phase: 2 }, [opt("core", "核心", "看不到那一格"), opt("shell_seam", "殼縫", "那一格超出射程"), opt("vent", "熔岩噴口", "只有遠程才打得到")], null),
        marksCell("⑦ 破掉（每格一個紅×）", { phase: 2, vent: "broken", seam: "broken", core: "broken" }, ALL_OK, null),
        marksCell("⑧ 未露出（第 1 階段核心）", { phase: 1 }, [opt("core", "核心", "呼吸階段才露出"), opt("shell_seam", "殼縫", null), opt("vent", "熔岩噴口", null)], null),
        marksCell("⑨ 遠程攻擊者（殼縫沒有背刺記號）", { phase: 2 }, ALL_OK, null, true),
      ],
    },
  ],
  break: () =>
    (
      [
        ["熔岩噴口封住（第 2 階段）", { phase: 2 }, { phase: 2, vent: "broken" }, "vent", 1, false],
        ["殼縫破（第 1 階段，熔殼掉落；打中西側）", { phase: 1 }, { phase: 1, shell: false, seam: "broken" }, "shell_seam", -1, true],
        ["核心破（第 2 階段）", { phase: 2 }, { phase: 2, core: "broken" }, "core", 1, false],
        ["殼縫破（第 2 階段，熔殼本來就不在；打中東側）", { phase: 2 }, { phase: 2, seam: "broken" }, "shell_seam", 1, false],
      ] as const
    ).map(([title, before, after, partId, side, shed]) => ({
      title: `A4 ${title}・${W} 寬・5 格`,
      cells: [0, 1, 2, 3, 4].map((f) => breakCell(FRAME_ZH[f]!, before as HeartSpec, after as HeartSpec, partId, f, side as -1 | 1, shed)),
    })),
  after: () => [
    {
      title: `破壞後定稿（同一張、照 broken 旗標）・${W} 寬`,
      cells: [
        { cap: "噴口封住（第 2 階段）", view: viewOf([heartOf({ phase: 2, vent: "broken" })]) },
        { cap: "殼縫破（第 2 階段）", view: viewOf([heartOf({ phase: 2, seam: "broken" })]) },
        { cap: "核心破（第 2 階段）", view: viewOf([heartOf({ phase: 2, core: "broken" })]) },
        { cap: "全破（第 2 階段）", view: viewOf([heartOf({ phase: 2, vent: "broken", seam: "broken", core: "broken" })]) },
        { cap: "全破（第 3 階段：白熱裂紋改暗裂痕）", view: viewOf([heartOf({ phase: 3, vent: "broken", seam: "broken", core: "broken" })]) },
      ],
    },
  ],
  shed: () => [
    {
      title: "熔殼脫落：殼片往北飛過噴口進岩漿（第 3、4 格），離開佔格不帶金外光；最近鄰 ×3",
      cells: [2, 3].map((f) => ({ ...breakCell(`第 ${f + 1} 格（breakT ${f === 2 ? 0.35 : 0.72}）`, { phase: 1 }, { phase: 1, shell: false, seam: "broken" }, "shell_seam", f, -1, true), zoom: 3, zoomBox: { x0: 0.6, y0: -0.6, x1: 4.4, y1: 4.1 } })),
    },
  ],
  field: () => {
    const lava = (x: number, y: number): string => (y === 0 || (y === 1 && (x < 3 || x > 7)) ? "lava" : "stone");
    const units = (ph: 1 | 2 | 3): UnitView[] => [
      heartOf({ x: 5, y: 3, phase: ph, seam: ph === 3 ? "broken" : "ok", core: ph === 1 ? "hidden" : "dmg" }),
      personAt(HERO, 5, 5, "ally"),
      personAt("a1", 4, 5, "ally", "hero_archer", "north", "ranged"),
      personAt("a2", 6, 5, "ally", "hero_mage"),
      personAt("e1", 3, 3, "enemy", "ember_lizard", "east"),
      personAt("e2", 7, 3, "enemy", "ember_lizard", "west"),
      personAt("n1", 3, 2, "ally", "hero_fighter", "east"),
      personAt("n2", 7, 2, "ally", "hero_archer", "west", "ranged"),
    ];
    return [
      {
        title: `場面：北邊岩漿、南邊與兩側有人（${W} 寬）`,
        cells: ([1, 3] as const).map((ph) => ({ cap: `第 ${ph} 階段${ph === 3 ? "（坑底紅光在地面層）" : ""}`, view: viewOf(units(ph), 11, 7, lava), zoomBox: { x0: 2.4, y0: -0.4, x1: 8.6, y1: 6.2 } })),
      },
    ];
  },
};

const renderers: BattleRenderer[] = [];
document.body.appendChild(h("h2", { textContent: `GB-4b 巨型灰燼之心：set=${SETS.join(",")}、${W} 寬、地圖縮放 ${SCALE}` }));
for (const set of SETS) {
  for (const group of (SETS_OF[set] ?? SETS_OF.sprites!)()) {
    document.body.appendChild(h("h3", { textContent: group.title }));
    const row = h("div", { className: "row" });
    document.body.appendChild(row);
    for (const c of group.cells) await cellOf(c, row);
  }
}
(window as unknown as { __gb4b?: unknown }).__gb4b = { renderers };
document.body.dataset.ready = "1";
