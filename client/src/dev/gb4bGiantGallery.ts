// 開發用：GB-4b 3×3 巨型灰燼之心的戰場畫法（開 `client/dev/gb4b-giant.html`；自己的 vite 後 /dev/gb4b-giant.html?mute=1）。不屬於正式 build。
// 一律用真的 `buildDrawModel`、`BattleRenderer.draw`／`setHighlights`、部位格標示 `giantMarksOf`（和點擊判定同一份 tiles）與
// 破壞演出同一組函式（`setPartFx` ＋ `partBreakFx.giantBreakCanvas`）畫手寫的場面（比照 `pb1eGallery.ts`）；外觀取
// `render/fixtures/unitDolls.json`。每格＝真 1 倍的畫布（`extract`，裝置像素比 1 時＝畫面像素）＋可選的最近鄰放大。
// 參數：
//   ?set=sprites|marks|break|after|shed|field|side   （逗號接多段；預設 sprites；side＝BM-1 狀態 3 個＋蓄力的 HUD；tele＝BM-1 延遲預告字）
//   set=clips：GB-4c（美術 GB-4b 待決 6）攻擊片段停格——熔岩噴發（第 1 階段 spout）、熔心吸氣（第 2 階段；GB-4d 起播吸氣變體 inhale，
//              pose 給遊戲同樣的 `atk:@area`）、受擊、倒下各 4 格（&u=a,b,… 換停格的 u）；
//              本體貼圖直接用遊戲的 `drawGiantFrame`（`inkCreature` 巨型分支畫的同一個函式，pose＝片段＋u），底色是石地＋3×3 格線
//   &w=1600|800   地圖縮放照美術移植需求 2.3（1600＝1.308、800＝0.531）；`&scale=` 另給
//   &zoom=<k>     最近鄰放大倍數（預設 0＝不放大；800 的立繪、殼縫格、「破」字特寫用 4）
//   &only=<i,…>   每一段只畫第幾格（0 起；特寫用）
//   &group=<i,…>  只畫第幾段（0 起；破壞連拍分張用）
//   &grid=0       不畫 3×3 格線（預設畫：佔格外框＋格線，看核心、殼窩只在中排）
// 畫好後 `document.body.dataset.ready = "1"`。
import { Rectangle, Sprite } from "pixi.js";
import type { Action, BattleView, Facing, Glossary, PartOption, PartView, Pos, TelegraphOut, TileView, UnitView } from "../api/types";
import { telegraphMarks } from "../battle/telegraph";
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
import { giantBreakCanvas, giantSmokeCeil } from "../render/partBreakFx";
import { drawGiantFrame, GIANT_ANCHOR_DY, GIANT_BOX, GIANT_FEET_TO_ANCHOR, GIANT_FX_BOX, GIANT_PART_OF, GT, type GiantLook } from "../render/qBossGiant";

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
  /** BM-1：狀態（預設照熔殼）。 */
  statuses?: string[];
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
    statuses: (b.statuses ?? (b.shell ?? phase === 1 ? ["molten_shell"] : [])).map(st),
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
function gridOn(c: HTMLCanvasElement, cx: number, cy: number, ox: number, oy: number): void {
  // 世界座標（格）→ 這張畫布的像素：(X × T − ox) × s；`ox`、`oy`＝畫布左上角的世界座標（模型 px，含頭頂預留）
  const g = c.getContext("2d")!;
  const s = SCALE * devicePixelRatio;
  const px = (X: number): number => (X * T - ox) * s;
  const py = (Y: number): number => (Y * T - oy) * s;
  g.save();
  g.strokeStyle = "rgba(120,220,255,0.9)";
  g.lineWidth = 1;
  for (let i = 0; i <= 3; i++) {
    const x = Math.round(px(cx - 1.5 + i)) + 0.5;
    const y = Math.round(py(cy - 1.5 + i)) + 0.5;
    g.setLineDash(i === 0 || i === 3 ? [] : [3, 3]);
    g.beginPath();
    g.moveTo(x, py(cy - 1.5));
    g.lineTo(x, py(cy + 1.5));
    g.stroke();
    g.beginPath();
    g.moveTo(px(cx - 1.5), y);
    g.lineTo(px(cx + 1.5), y);
    g.stroke();
  }
  // 錨點（南排南緣中點）
  g.setLineDash([]);
  g.fillStyle = "#7cf";
  g.fillRect(Math.round(px(cx)) - 2, Math.round(py(cy + 1.5)) - 2, 4, 4);
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
  const shown = c.crop === undefined ? full : zoomOf(r, c.crop, 1);
  if (GRID && b !== undefined) gridOn(shown, b.pos.x + 0.5, b.pos.y + 0.5, c.crop === undefined ? 0 : c.crop.x0 * T, c.crop === undefined ? -p.world.y : c.crop.y0 * T);
  host.replaceWith(shown);
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
  const marks = giantMarksOf(state, hover ?? P(2, 3)); // 沒有選取模式時要滑到身上才畫：沒指定滑過時用前殼（打本體，標示不另畫⑤）
  const hl: Highlights = { moves: [], attacks: boss.tiles ?? [], directions: [], preview: [], telegraph: [], focus: null, hover, overlays: [], picked: [], giantMarks: marks };
  return { cap, view, after: (r) => r.setHighlights(hl), zoomBox: { x0: 0.9, y0: 0.9, x1: 4.1, y1: 4.1 }, crop: { x0: 0.8, y0: 0.8, x1: 4.2, y1: 4.2 } };
}

// ---- 破壞演出（和 `partBreakFx.giantBreakEffect` 同一組函式） ----
function breakCell(cap: string, before: HeartSpec, after: HeartSpec, partId: string, frame: number, side: -1 | 1, shed: boolean): Cell {
  // 播放時 `view` 在命中＋停頓後就是破了的樣子：演出前 4 格由 `PartFx` 蓋回（同正式播放）
  const view = viewOf([personAt(HERO, 4, 5, "ally"), heartOf(frame >= 4 ? after : after)]);
  return {
    cap,
    view,
    crop: { x0: 0.8, y0: 0, x1: 4.2, y1: 4.05 },
    after: (r) => {
      const p = r as unknown as Pixi;
      p.setPartFx(BOSS, giantBreakFxOf(partId, frame, side, shed));
      if (frame >= 4) return;
      const res = p.art.figureRes(1);
      // GB-4d：煙頂上限照遊戲（`giantBreakEffect` 同一個 `giantSmokeCeil`，看這一格的 HUD 下緣；800、1600 都壓）
      const d = buildDrawModel(view, HERO, null, undefined, BATTLE_DRAW).units.find((u) => u.id === BOSS);
      const ceil = d === undefined ? undefined : giantSmokeCeil(d, SCALE);
      const cv = giantBreakCanvas({ phase: before.phase ?? 1, fx: { part: GIANT_PART_OF[partId]!, k: frame, side } }, res, SCALE, ceil);
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
      cells: ([1, 2, 3] as const).flatMap((ph) => [true, false].map((shell) => ({ cap: `第 ${ph} 階段（${PHASE_ZH[ph]}）・熔殼${shell ? "在" : "不在"}`, view: viewOf([personAt(HERO, 0, 5, "ally"), heartOf({ phase: ph, shell })]), crop: { x0: 0.7, y0: -1.75, x1: 4.3, y1: 4.15 } }))),
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
      title: "熔殼脫落：殼片往北飛過噴口進岩漿（第 3、4 格），離開佔格不帶金外光；最近鄰 ×2",
      cells: [2, 3].map((f) => ({ ...breakCell(`第 ${f + 1} 格（breakT ${f === 2 ? 0.35 : 0.72}）`, { phase: 1 }, { phase: 1, shell: false, seam: "broken" }, "shell_seam", f, -1, true), zoom: 2, zoomBox: { x0: 0.6, y0: -0.2, x1: 4.4, y1: 4.1 } })),
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
  // BM-1：狀態 3 個＋蓄力（800 寬狀態列在 HP 條右邊、徽章在左邊；1600 照原本）；頭目在最北（中心第 1 排）、HUD 不被畫面上緣切掉
  side: () => {
    const lava = (_x: number, y: number): string => (y === 0 ? "lava" : "stone");
    const statuses = ["molten_shell", "burning", "shielded", "charging"];
    const units = (y: number): UnitView[] => [heartOf({ x: 3, y, phase: 1, statuses }), personAt(HERO, 3, y + 2, "ally"), personAt("e1", 1, y, "enemy", "ember_lizard", "east")];
    return [
      {
        title: `狀態 3 個＋蓄力（${W} 寬）：一般位置／最北（中心在第 1 排）`,
        cells: [2, 1].map((y) => ({ cap: y === 1 ? "最北" : "一般", view: viewOf(units(y), 7, 6, lava), zoomBox: { x0: 0.4, y0: y === 1 ? -1.6 : -0.6, x1: 6.6, y1: y + 2.6 } })),
      },
    ];
  },
  // BM-1：延遲落格預告字（熔岩濺落「蓄」、施放者「蓄1」、炸彈倒數）：800 寬放大到畫面字 ≥10 px、錨在格子右上角
  tele: () => {
    const spot = P(3, 5);
    const sq = [-1, 0, 1].flatMap((dy) => [-1, 0, 1].map((dx) => P(spot.x + dx, spot.y + dy)));
    const units = [heartOf({ x: 3, y: 2, phase: 1 }), personAt(HERO, 3, 5, "ally"), personAt("a1", 2, 6, "ally", "hero_archer", "north", "ranged"), personAt("a2", 5, 5, "ally", "hero_mage")];
    const view = viewOf(units, 7, 7);
    const tele = {
      round: 1, changes: [], burning: [], upcoming: [],
      bombs: [{ unit_id: "a2", pos: P(5, 5), tiles: [P(5, 4), P(6, 5)], remaining: 2, text: "炸彈：2 回合後爆炸" }],
      charges: [{ unit_id: BOSS, skill_id: "skill_lava_splash", name_zh: "熔岩濺落", release: "next_turn", remaining: 1, pos: spot, tiles: sq, anchored: true, text: "灰燼之心的熔岩濺落：下回合開始時落在指定位置，影響 9 格" }],
    } as unknown as TelegraphOut;
    const hl: Highlights = { moves: [], attacks: [], directions: [], preview: [], telegraph: telegraphMarks(tele, view), focus: null, hover: null, overlays: [], picked: [] };
    return [{ title: `延遲落格預告字（${W} 寬）`, cells: [{ cap: "熔岩濺落落點 3×3＋炸彈倒數", view, after: (r: BattleRenderer) => r.setHighlights(hl), zoomBox: { x0: 0.6, y0: 3.4, x1: 6.6, y1: 7 } }] }];
  },
};

// ---- GB-4c：攻擊片段停格（本體貼圖；位置、白閃、縮小照 `giantStateFor`） ----
const CLIP_U = q.get("u")?.split(",").map(Number) ?? [0.1, 0.35, 0.6, 0.85];
const CLIPS: ReadonlyArray<{ zh: string; clip: string; phase: 1 | 2 | 3; u: readonly number[] }> = [
  { zh: "熔岩噴發（第 1 階段・熔岩濺落施放，spout）", clip: "spout", phase: 1, u: CLIP_U },
  { zh: "熔心吸氣（第 2 階段，GB-4d 吸氣變體 inhale：吸氣火星往核心收＋核心蓄力光，不畫熔岩柱）", clip: "atk:@area", phase: 2, u: CLIP_U },
  { zh: "受擊（hit，整隻白閃；3×3 不位移）", clip: "hit", phase: 2, u: [0, 0.25, 0.5, 0.9] },
  { zh: "倒下（death，縮小變暗）", clip: "death", phase: 3, u: [0.15, 0.45, 0.75, 1] },
];
function clipCanvas(look: GiantLook, clip: string, u: number): HTMLCanvasElement {
  // 畫面 px＝模型 px × 地圖縮放；畫布＝本體外框（錨點座標 `GIANT_BOX`）上方多留一點給熔岩柱
  const pad = 30;
  const [x0, y0, x1, y1] = GIANT_BOX;
  const s = SCALE * devicePixelRatio;
  const c = h("canvas", { width: Math.ceil((x1 - x0) * s), height: Math.ceil((y1 - y0 + pad) * s) });
  const g = c.getContext("2d")!;
  g.fillStyle = "#4a423c";
  g.fillRect(0, 0, c.width, c.height);
  g.setTransform(s, 0, 0, s, -x0 * s, (-(y0 - pad)) * s); // 原點＝錨點
  g.strokeStyle = "rgba(120,220,255,0.55)";
  g.lineWidth = 1 / s;
  for (let i = 0; i <= 3; i++) {
    g.strokeRect(-1.5 * GT + i * GT, -3 * GT, 0, 3 * GT);
    g.strokeRect(-1.5 * GT, -3 * GT + i * GT, 3 * GT, 0);
  }
  g.translate(0, -GIANT_FEET_TO_ANCHOR); // 原點＝腳底（`drawGiantFrame` 自己再往南到錨點）
  drawGiantFrame(g as unknown as Parameters<typeof drawGiantFrame>[0], look, { clip, u });
  c.style.width = `${c.width / devicePixelRatio}px`;
  return c;
}
function clipsSection(): void {
  document.body.appendChild(h("h3", { textContent: `攻擊片段停格（${W} 寬、地圖縮放 ${SCALE}、真 1 倍；青線＝3×3 格線；開發頁・本體貼圖函式同遊戲）` }));
  for (const [ci, c] of CLIPS.entries()) {
    if (GROUPS !== null && !GROUPS.includes(ci)) continue; // GB-4d：&group= 也能挑片段（0 起）
    document.body.appendChild(h("p", { className: "cap", textContent: c.zh }));
    const row = h("div", { className: "row" });
    row.style.flexWrap = "nowrap";
    document.body.appendChild(row);
    const look: GiantLook = { phase: c.phase, shell: c.phase === 1 ? 1 : 0, broken: {}, fx: null };
    for (const u of c.u) row.appendChild(h("div", { className: "cell" }, clipCanvas(look, c.clip, u), h("p", { className: "cap", textContent: `u=${u}` })));
  }
}

const renderers: BattleRenderer[] = [];
document.body.appendChild(h("h2", { textContent: `GB-4b 巨型灰燼之心：set=${SETS.join(",")}、${W} 寬、地圖縮放 ${SCALE}` }));
const GROUPS = q.get("group")?.split(",").map(Number) ?? null; // 只畫第幾段（0 起；連拍分張用）
for (const set of SETS) {
  if (set === "clips") {
    clipsSection();
    continue;
  }
  for (const [gi, group] of (SETS_OF[set] ?? SETS_OF.sprites!)().entries()) {
    if (GROUPS !== null && !GROUPS.includes(gi)) continue;
    document.body.appendChild(h("h3", { textContent: group.title }));
    const row = h("div", { className: "row" });
    document.body.appendChild(row);
    const only = q.get("only")?.split(",").map(Number) ?? null; // 只畫第幾格（0 起；特寫用）
    for (const [i, c] of group.cells.entries()) if (only === null || only.includes(i)) await cellOf(c, row);
  }
}
(window as unknown as { __gb4b?: unknown }).__gb4b = { renderers };
document.body.dataset.ready = "1";
