// 開發用：PB-1e 頭目部位的戰場畫法（開 `client/dev/pb1e-gallery.html`；自己的 vite 後 /dev/pb1e-gallery.html?mute=1）。不屬於正式 build。
// 一律用真的 `buildDrawModel` 與 `BattleRenderer.draw` 畫手寫的場面（比照 `oclGallery.ts`）；霧鎖真人的外觀取
// `render/fixtures/unitDolls.json`（和伺服器 `UnitView.doll_look` 同一份匯出）。每格＝真 1 倍的畫布＋右邊頭目一帶最近鄰放大
// （`extract` 取畫布像素、`imageSmoothingEnabled = false`）。
// 參數：
//   ?set=strip|hud|hover|after|break|qi|bm1    （逗號接多段；預設 strip；bm1＝BM-1 800 寬狀態列在 HP 條旁）
//   &w=1600|800      照這個視窗寬算雲頂觀 12×12 的地圖縮放（預設 1600）；`&scale=` 另給
//   &zoom=<k>        最近鄰放大倍數（預設 4）
//   &part=whisk|sword|dantian（break 只畫這個部位；預設三個都畫）
// 畫好後 `document.body.dataset.ready = "1"`；`window.__pb1e.renderers` 給截圖腳本。
import { Rectangle, Sprite } from "pixi.js";
import type { BattleView, Facing, Glossary, PartView, TileView, UnitView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { BATTLE_DRAW, buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { setGlossary } from "../battle/glossary";
import { breakFxOf } from "../render/bossPartArt";
import { BREAK_BOX, breakFxCanvas, partCenter, weaponToFeet } from "../render/bossPartArt";
import { fitScale, hudSideInsets } from "../battle/stageLayout";
import { tile, unit } from "../battle/testFixtures";
import { BattleRenderer } from "../render/BattleRenderer";
import dolls from "../render/fixtures/unitDolls.json";
import { waitForFonts } from "../render/fontLoad";
import { dollPx, FEET, specOfUnit } from "../render/unitSprite";

setGlossary(glossary as unknown as Glossary);
await waitForFonts();

const q = new URLSearchParams(location.search);
const SETS = (q.get("set") ?? "strip").split(",");
const W = q.get("w") === "800" ? 800 : 1600;
const H = W === 800 ? 600 : 900;
const ZOOM = Number(q.get("zoom") ?? 4);
const ONLY = q.get("part");

const BOSS = "boss";
const HERO = "unit_0001";
type PartSt = "ok" | "dmg" | "low" | "broken" | "hidden";
const PART_ZH: Record<string, string> = { whisk: "拂塵", dantian: "氣海", sword: "長劍" };
const PHASES = [
  { index: 1, total: 3, name_zh: "劍陣" },
  { index: 2, total: 3, name_zh: "鎖霧" },
  { index: 3, total: 3, name_zh: "歸一" },
];
const st = (s: string): Record<string, unknown> => ({ status_id: s, remaining: 2, source_id: null, amount: null, blast_radius: null, charge_tiles: [], cost_status: false });

function part(id: string, s: PartSt): PartView {
  const hp = s === "ok" ? 24 : s === "dmg" ? 9 : s === "low" ? 3 : s === "broken" ? 0 : null;
  return { id, name_zh: PART_ZH[id] ?? id, hp, max_hp: s === "hidden" ? null : 24, broken: s === "broken", exposed: s !== "hidden", reach: id === "dantian" ? "behind" : "any", break_lines_zh: [] };
}

interface BossSpec {
  x?: number;
  y?: number;
  facing?: Facing;
  phase?: 1 | 2 | 3;
  parts?: [PartSt, PartSt, PartSt];
  statuses?: string[];
  hidden?: boolean;
  shield?: number;
  hp?: number;
}

function bossOf(b: BossSpec): UnitView {
  const [w, d, s] = b.parts ?? ["ok", "ok", "ok"];
  const phase = b.phase ?? 3;
  const over: Record<string, unknown> = {
    template_id: "sect_mist_lock_master",
    name_zh: "霧鎖真人",
    facing: b.facing ?? "south",
    hp: b.hidden === true ? null : (b.hp ?? 60),
    max_hp: 120,
    shield: b.hidden === true ? null : (b.shield ?? 0),
    weapon_id: "one_handed_sword",
    weapon_class: "melee",
    tags: ["boss", "elite", "humanoid", "sect"],
    doll_look: (dolls as Record<string, unknown>)["sect_mist_lock_master"],
    boss_phase: PHASES[phase - 1],
    statuses: (b.statuses ?? []).map(st),
    hidden_info: b.hidden === true,
    parts: [part("dantian", phase === 1 ? "hidden" : d), part("sword", phase < 3 ? "hidden" : s), part("whisk", w)],
  };
  return unit(BOSS, "enemy", b.x ?? 2, b.y ?? 1, over as Partial<UnitView>);
}

function heroAt(x: number, y: number, facing: Facing = "north"): UnitView {
  return unit(HERO, "ally", x, y, { template_id: "hero_fighter", name_zh: "主角", facing, hp: 24, max_hp: 30 } as Partial<UnitView>);
}

function viewOf(units: UnitView[], cols = 5, rows = 4): BattleView {
  const tiles: TileView[] = [];
  for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) tiles.push(tile(x, y, { terrain: "stone", height: 0 } as Partial<TileView>));
  return {
    team: "ally", map_id: "pb1e", map_name_zh: "雲頂觀", width: cols, height: rows, tiles, objects: [], units, traps: [],
    turn_order: [units[0]!.id], active_unit: null, round: 4, max_rounds: 30, weather_id: null, weather_name_zh: null,
    objective: { kind: "eliminate", tiles: [], rounds: null, leader_retreat: false }, ended: false, winner: null, end_reason: null, pending: null,
    source_wells: [], zones: [], runes: [], summon_command_ap_cost: 1, summon_infuse_ap_cost: 1,
  } as unknown as BattleView;
}

/** 雲頂觀 12×12 在這個視窗寬的地圖縮放（同 `useBoardViewport`）。 */
function refScale(): number {
  const model = buildDrawModel(viewOf([bossOf({})], 12, 12), HERO, null, undefined, BATTLE_DRAW);
  const ins = hudSideInsets(W);
  return fitScale({ width: W - ins.left - ins.right - 16, height: H - ins.top - 16 }, model);
}
const SCALE = Number(q.get("scale")) || refScale();

const h = <T extends keyof HTMLElementTagNameMap>(tag: T, props: Partial<HTMLElementTagNameMap[T]> = {}, ...kids: (Node | string)[]): HTMLElementTagNameMap[T] => {
  const e = Object.assign(document.createElement(tag), props);
  e.append(...kids);
  return e;
};

type Pixi = { app: { renderer: { extract: { canvas(o: unknown): HTMLCanvasElement }; render(o: unknown): void }; stage: unknown }; world: { y: number } };

/** 頭目一帶（格 (x−0.6～x+1.6, y−0.9～y+1.4)，模型 px）最近鄰放大。 */
function zoomOf(r: BattleRenderer, bx: number, by: number, rows = 1.4, wide = false): HTMLCanvasElement {
  const p = r as unknown as Pixi;
  const T = 48;
  const res = devicePixelRatio * SCALE;
  // BM-1：`wide` 左右各多一格（800 寬狀態列、徽章在 HP 條兩側）
  const x0 = wide ? bx - 1.5 : bx - 0.6;
  const frame = new Rectangle(Math.round(x0 * T), Math.round((by - 0.9) * T + p.world.y), Math.round((wide ? 4 : 2.2) * T), Math.round((0.9 + rows) * T));
  const src = p.app.renderer.extract.canvas({ target: p.app.stage, frame, resolution: res });
  const out = h("canvas", { width: src.width * ZOOM, height: src.height * ZOOM });
  const g = out.getContext("2d")!;
  g.imageSmoothingEnabled = false;
  g.drawImage(src, 0, 0, out.width, out.height);
  out.style.width = `${out.width / devicePixelRatio}px`;
  return out;
}

interface Cell {
  cap: string;
  units: UnitView[];
  /** 畫完之後做的事（滑過的部位、演出的格）。 */
  after?: (r: BattleRenderer) => void;
  zoomRows?: number;
  /** BM-1：放大範圍左右各多一格。 */
  wide?: boolean;
  /** BM-1：地圖大小（預設 5×4）。 */
  cols?: number;
}

const renderers: BattleRenderer[] = [];
async function cellOf(c: Cell, row: HTMLElement): Promise<void> {
  const host = h("div");
  const box = h("div", { className: "cell" }, host);
  row.appendChild(box);
  const r = new BattleRenderer();
  await r.init(host);
  r.setIdle(false);
  r.setScale(SCALE);
  const model = buildDrawModel(viewOf(c.units, c.cols), HERO, null, undefined, BATTLE_DRAW);
  r.draw(model);
  c.after?.(r);
  const b = c.units.find((u) => u.id === BOSS)!;
  // 真 1 倍那張也從畫布取出來貼成 2D 畫布，之後銷毀繪製器（一頁幾十格時 WebGL context 會超過上限）
  const p = r as unknown as Pixi;
  const full = p.app.renderer.extract.canvas({ target: p.app.stage, resolution: devicePixelRatio * SCALE });
  full.style.width = `${full.width / devicePixelRatio}px`;
  if (q.get("full") === "0") host.remove();
  else host.replaceWith(full);
  box.appendChild(zoomOf(r, b.pos.x, b.pos.y, c.zoomRows, c.wide === true));
  if (q.get("keep") === "1") renderers.push(r);
  else r.destroy();
  box.appendChild(h("p", { className: "cap", textContent: c.cap }));
}

/** 演出某一格（和 `partBreakFx` 同一組函式）：人物蓋過＋身上以外的特效貼一張。 */
function breakFrame(r: BattleRenderer, b: UnitView, partId: string, frame: number): void {
  const anyR = r as unknown as { setPartFx(id: string, fx: unknown): void; unitDrawOf: Map<string, UnitDraw>; unitSprites: Map<string, { x: number; y: number }>; effects: { addChild(n: unknown): void }; art: { figureRes(n: number): number } };
  anyR.setPartFx(BOSS, breakFxOf(partId, frame));
  if (frame >= 4) return;
  const draw = { ...anyR.unitDrawOf.get(BOSS)!, partFx: { part: partId, k: "flash" as const } };
  const spec = specOfUnit(draw);
  const k = dollPx(draw);
  const center = partCenter(spec, b.facing, partId, k) ?? { x: 0, y: -20 };
  const weapon = weaponToFeet(spec, b.facing, partId, k);
  const res = anyR.art.figureRes(1);
  const cv = breakFxCanvas({ part: partId, frame, center, weapon, west: b.facing === "west" }, res);
  if (cv === null) return;
  const s = Sprite.from(cv);
  const at = anyR.unitSprites.get(BOSS)!;
  s.position.set(at.x + BREAK_BOX.x, at.y + FEET + BREAK_BOX.y);
  s.width = BREAK_BOX.w;
  s.height = BREAK_BOX.h;
  anyR.effects.addChild(s);
}

const SETS_OF: Record<string, () => Array<{ title: string; cells: Cell[] }>> = {
  strip: () => [
    {
      title: "頭頂部位小格（拂塵｜氣海｜長劍）：完好、破壞中、已破壞、未露出、隱蔽",
      cells: [
        { cap: "完好（歸一）", units: [bossOf({ parts: ["ok", "ok", "ok"] })] },
        { cap: "破壞中：拂塵 9/24、氣海 3/24", units: [bossOf({ parts: ["dmg", "low", "ok"] })] },
        { cap: "已破壞：拂塵×、長劍×", units: [bossOf({ parts: ["broken", "dmg", "broken"] })] },
        { cap: "未露出（劍陣：氣海、長劍）", units: [bossOf({ phase: 1, parts: ["ok", "ok", "ok"] })] },
        { cap: "隱蔽（看不到資訊）", units: [bossOf({ phase: 2, hidden: true, parts: ["dmg", "ok", "ok"] })] },
        { cap: "護盾條＋部位條", units: [bossOf({ shield: 40, parts: ["dmg", "ok", "broken"], statuses: ["mist_return"] })] },
      ],
    },
  ],
  hud: () => [
    {
      title: "南邊那格有人：頭目整組 HUD 改掛最上層（朝南三角形縮小）／南邊沒人對照",
      cells: [
        { cap: "南邊有人（朝南、狀態 2、蓄力）", units: [bossOf({ parts: ["dmg", "ok", "broken"], statuses: ["mist_return", "shielded", "charging"] }), heroAt(2, 2)], zoomRows: 2 },
        { cap: "南邊沒人（對照）", units: [bossOf({ parts: ["dmg", "ok", "broken"], statuses: ["mist_return", "shielded", "charging"] }), heroAt(3, 2)], zoomRows: 2 },
        { cap: "南邊有人、頭目朝東（三角形不移）", units: [bossOf({ facing: "east", parts: ["dmg", "ok", "broken"], statuses: ["mist_return"] }), heroAt(2, 2)], zoomRows: 2 },
      ],
    },
  ],
  hover: () => [
    {
      title: "選單打開：滑過的部位亮起；狀態列與蓄力徽章 40%（HP 條、部位條不淡）",
      cells: [
        ...(["whisk", "dantian", "sword"] as const).map((p) => ({ cap: `滑過${PART_ZH[p]}`, units: [bossOf({ parts: ["dmg", "ok", "ok"], statuses: ["mist_return", "shielded", "charging"] }), heroAt(2, 2)], after: (r: BattleRenderer) => r.setPartFocus(BOSS, p), zoomRows: 2 })),
        { cap: "選單沒開（對照）", units: [bossOf({ parts: ["dmg", "ok", "ok"], statuses: ["mist_return", "shielded", "charging"] }), heroAt(2, 2)], zoomRows: 2 },
        { cap: "滑過氣海（背面、從背後）", units: [bossOf({ facing: "north", parts: ["dmg", "ok", "ok"], statuses: ["mist_return", "shielded"] }), heroAt(2, 0, "south")], after: (r) => r.setPartFocus(BOSS, "dantian"), zoomRows: 2 },
        { cap: "選單打開、氣海已破（沒滑過）", units: [bossOf({ parts: ["dmg", "broken", "ok"], statuses: ["mist_return", "shielded"] }), heroAt(2, 2)], after: (r) => r.setPartFocus(BOSS, null), zoomRows: 2 },
      ],
    },
  ],
  after: () =>
    (["south", "east", "west", "north"] as const).map((f) => ({
      title: `破壞後外觀（${{ south: "正面", east: "朝東", west: "朝西", north: "背面" }[f]}）：完好、拂塵破、長劍破、氣海破、全破`,
      cells: (
        [
          ["完好", ["ok", "ok", "ok"]],
          ["拂塵破", ["broken", "ok", "ok"]],
          ["長劍破", ["ok", "ok", "broken"]],
          ["氣海破", ["ok", "broken", "ok"]],
          ["全破", ["broken", "broken", "broken"]],
        ] as const
      ).map(([cap, parts]) => ({ cap, units: [bossOf({ facing: f, parts: [...parts] as [PartSt, PartSt, PartSt] })] })),
    })),
  break: () =>
    (["whisk", "sword", "dantian"] as const)
      .filter((p) => ONLY === null || ONLY === p)
      .map((p) => ({
        title: `破壞演出：${PART_ZH[p]}（1 命中白閃、2 裂開、3 斷開＋「破」、4 落地、5 定格）`,
        cells: [0, 1, 2, 3, 4].map((f) => {
          const facing: Facing = p === "dantian" ? "north" : "south";
          const parts: [PartSt, PartSt, PartSt] = [p === "whisk" ? "broken" : "ok", p === "dantian" ? "broken" : "ok", p === "sword" ? "broken" : "ok"];
          const b = bossOf({ facing, parts, hp: 40 });
          return { cap: ["1 命中白閃", "2 裂開", "3 斷開・飛出", "4 落地", "5 定格"][f]!, units: [b], after: (r: BattleRenderer) => breakFrame(r, b, p, f) };
        }),
      })),
  // BM-1：800 寬狀態列移到 HP 條旁（右）、徽章在左；狀態 3 個＋蓄力時滑過三個部位（PB-1f 待決 3）；最右欄左右對調；東西兩側有人
  bm1: () => {
    const three = ["mist_return", "shielded", "burning", "charging"];
    const wide = { zoomRows: 2, wide: true } as const;
    return [
      {
        title: "BM-1：狀態 3 個＋蓄力，選單打開、滑過三個部位／選單沒開",
        cells: [
          ...(["whisk", "dantian", "sword"] as const).map((p) => ({ cap: `滑過${PART_ZH[p]}`, units: [bossOf({ parts: ["dmg", "ok", "ok"], statuses: three }), heroAt(2, 2)], after: (r: BattleRenderer) => r.setPartFocus(BOSS, p), ...wide })),
          { cap: "選單沒開", units: [bossOf({ parts: ["dmg", "ok", "ok"], statuses: three }), heroAt(2, 2)], ...wide },
        ],
      },
      {
        title: "BM-1：南邊沒人／東西兩側有人／站最右欄（左右對調）／朝東／護盾條",
        cells: [
          { cap: "南邊沒人", units: [bossOf({ parts: ["dmg", "ok", "broken"], statuses: three }), heroAt(3, 2)], ...wide },
          { cap: "東西兩側有人", units: [bossOf({ parts: ["dmg", "ok", "broken"], statuses: three }), heroAt(1, 1, "east"), unit("unit_0002", "ally", 3, 1, { template_id: "hero_archer", name_zh: "弓手", facing: "west", hp: 20, max_hp: 30 } as Partial<UnitView>)], ...wide },
          { cap: "站最右欄", units: [bossOf({ x: 4, parts: ["dmg", "ok", "broken"], statuses: three }), heroAt(4, 2)], ...wide },
          { cap: "朝東（三角形在東邊）", units: [bossOf({ facing: "east", parts: ["dmg", "ok", "broken"], statuses: three }), heroAt(2, 2)], ...wide },
          { cap: "護盾條＋炸彈＋蓄力", units: [bossOf({ shield: 40, parts: ["dmg", "ok", "broken"], statuses: ["mist_return", "time_bomb", "charging"] }), heroAt(2, 2)], ...wide },
        ],
      },
    ];
  },
  qi: () => [
    {
      title: "腹前氣旋：鎖霧／歸一有、劍陣沒有、氣海破後沒有；側面在劍柄之下",
      cells: [
        { cap: "鎖霧・正面", units: [bossOf({ phase: 2 })] },
        { cap: "歸一・正面", units: [bossOf({ phase: 3 })] },
        { cap: "劍陣・正面（沒有）", units: [bossOf({ phase: 1 })] },
        { cap: "歸一・氣海破（沒有）", units: [bossOf({ phase: 3, parts: ["ok", "broken", "ok"] })] },
        { cap: "歸一・朝東（劍柄之下）", units: [bossOf({ phase: 3, facing: "east" })] },
        { cap: "歸一・朝西", units: [bossOf({ phase: 3, facing: "west" })] },
      ],
    },
  ],
};

document.body.appendChild(h("h2", { textContent: `PB-1e 頭目部位：${W} 寬（地圖 ${SCALE.toFixed(2)}）、放大 ×${ZOOM}` }));
for (const set of SETS) {
  for (const block of (SETS_OF[set] ?? SETS_OF.strip!)()) {
    document.body.appendChild(h("h3", { textContent: block.title }));
    const row = h("div", { className: "row" });
    document.body.appendChild(row);
    for (const c of block.cells) await cellOf(c, row);
  }
}
(window as unknown as { __pb1e?: unknown }).__pb1e = { renderers };
document.body.dataset.ready = "1";
