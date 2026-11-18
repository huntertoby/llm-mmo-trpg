// 開發用：AR-SK3 美術移植的驗收畫面（`client/dev/arsk3-gallery.html`；不屬於正式 build）。
// 移植需求 docs/art/SK-3-移植需求.md：第 1 項部件圖樣、第 5 項戰前佈置的格子記號；第 4 節吸收表面的染色。
// 重擲演出看 sk3-gallery.html（`&strip=`、`&w=`、`&upper=1`、`&boss=`）；會擴散記號看 arsk2-gallery.html?part=field（`&scale=`）。
// 畫好後 `document.body.dataset.ready = "1"`；截圖存 `#shot`。
//   ?part=icons              六個部件：組裝列 30／26／18（條件另加 16）＋真 1 倍 ×6 最近鄰＋18 的 2 倍 ×4 最近鄰
//   ?part=tint               吸收表面的部件照表面染色（沒指定、水、火、冰、毒、聖光、黑暗、油、煙霧）：30／18 與真 1 倍 ×6
//   ?part=prep&w=1600|800    戰前佈置（遊戲端 BattleRenderer＋PrepDialog）：待放三格｜指著＋陷阱預覽｜刻印預覽｜表面預覽｜放下的一下（140 ms）
import { createRoot } from "react-dom/client";
import type { Application } from "pixi.js";
import type { BattleView, Glossary, PrepOut, SkillCard, UnitView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { buildDrawModel } from "../battle/drawModel";
import { setGlossary } from "../battle/glossary";
import { prepMarksOf } from "../battle/prep";
import { PREP_HINT_ZH } from "../battle/skillTray";
import { tile, unit } from "../battle/testFixtures";
import { BattleRenderer, type Highlights } from "../render/BattleRenderer";
import { waitForFonts } from "../render/fontLoad";
import * as QP from "../render/qIcon/parts";
import { effectPart } from "../render/skillParts";
import { PrepDialog } from "../ui/PrepDialog";
import "../styles/index.css";

setGlossary(glossary as unknown as Glossary);
await waitForFonts();

const params = new URLSearchParams(location.search);
const part = params.get("part") ?? "icons";
const shot = document.createElement("div");
shot.id = "shot";
shot.style.display = "inline-block";
shot.style.padding = "8px";
document.body.appendChild(shot);

const h = <K extends keyof HTMLElementTagNameMap>(tag: K, props: Partial<HTMLElementTagNameMap[K]> = {}, ...kids: Node[]): HTMLElementTagNameMap[K] => {
  const e = Object.assign(document.createElement(tag), props);
  e.append(...kids);
  return e;
};
const cap = (text: string): HTMLElement => h("div", { textContent: text, className: "cap" });
/** 最近鄰放大。 */
function nn(src: HTMLCanvasElement, k: number, sx = 0, sy = 0, sw = src.width, sh = src.height): HTMLCanvasElement {
  const c = h("canvas", { width: Math.max(1, Math.round(sw * k)), height: Math.max(1, Math.round(sh * k)) });
  const x = c.getContext("2d") as CanvasRenderingContext2D;
  x.imageSmoothingEnabled = false;
  x.drawImage(src, sx, sy, sw, sh, 0, 0, sw * k, sh * k);
  return c;
}
function at(cv: HTMLCanvasElement, css: number): HTMLCanvasElement {
  cv.style.width = cv.style.height = `${css}px`;
  return cv;
}
const cell = (...kids: Node[]): HTMLElement => h("div", { className: "cell" }, ...kids);
const line = (...kids: Node[]): HTMLElement => h("div", { className: "line" }, ...kids);

const PARTS: readonly [string, string, string][] = [
  ["effect", "reroll", "重擲"],
  ["trigger", "on_keyword_exploited", "你造的關鍵字被利用時"],
  ["trigger", "ally_missed_roll", "隊友擲失手時"],
  ["trigger", "enemy_hit_roll", "敵人擲中你時"],
  ["condition", "point_blank", "貼身"],
  ["condition", "long_range", "遠距"],
];

function icons(): void {
  shot.append(h("h2", { textContent: "部件圖樣（組裝列圓片 30／26／18；條件另加 16＝戰鬥說明行）：遊戲端 QP.chipCanvas" }));
  for (const [cat, id, zh] of PARTS) {
    const sizes = cat === "condition" ? [30, 26, 18, 16] : [30, 26, 18];
    const cells: Node[] = [];
    for (const px of sizes) cells.push(cell(at(QP.chipCanvas(cat, id, px, 1), px), cap(`${px}`)));
    for (const px of sizes) cells.push(cell(nn(QP.chipCanvas(cat, id, px, 1, { res: 1 }), 6), cap(`${px} 真 1 倍 ×6`)));
    cells.push(cell(nn(QP.chipCanvas(cat, id, 18, 1), 4), cap("18 的 2 倍 ×4")));
    shot.append(h("h3", { textContent: `${zh}（${cat}:${id}；${QP.entry(cat, id).zh}）` }), line(...cells));
  }
}

const SURFACES: readonly (string | null)[] = [null, "water", "fire", "ice", "poison", "holy", "darkness", "oil", "smoke"];
function tint(): void {
  shot.append(h("h2", { textContent: "吸收表面：部件圖樣照技能指定的表面染色（effectPart → QP.chip 的 tint；沒有對應色用水色）" }));
  const cells: Node[] = [];
  for (const s of SURFACES) {
    const p = effectPart(s === null ? { type: "absorb_surface" } : { type: "absorb_surface", surface: s });
    const T = p.q?.tint ?? null;
    const box = h("div", { className: "cell" });
    for (const px of [30, 18]) box.append(at(QP.chipCanvas("effect", "absorb_surface", px, 1, { tint: T }), px));
    box.append(nn(QP.chipCanvas("effect", "absorb_surface", 30, 1, { res: 1, tint: T }), 6));
    box.append(cap(s === null ? "沒指定" : s));
    cells.push(box);
  }
  shot.append(line(...cells));
}

const HERO = "unit_0001";
const W = 7, H = 8;
const ZONE: readonly [number, number][] = [[0, 4], [1, 5], [0, 6]];
const PREP = { unit_id: HERO, zone: [...ZONE, [1, 6], [0, 5]], options: [{ skill_id: "skill_trap", kind: "trap", tiles: ZONE }, { skill_id: "skill_rune", kind: "rune", tiles: ZONE }, { skill_id: "skill_pool", kind: "surface", tiles: ZONE }] } as unknown as PrepOut;
const POOL = { id: "skill_pool", icon: { segments: [{ effects: [{ type: "create_surface", surface: "ice" }] }] } } as unknown as SkillCard;
const NAMES: Readonly<Record<string, string>> = { skill_trap: "捕獸夾", skill_rune: "符文刻印", skill_pool: "冰面" };

function prepView(): BattleView {
  const tiles = [];
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) tiles.push(tile(x, y, { terrain: (x * 3 + y) % 5 === 0 ? "stone" : "grass" }));
  const units: UnitView[] = [
    unit(HERO, "ally", 2, 5, { template_id: "hero_fighter", name_zh: "衝鋒流英雄", weapon_id: "longsword", hp: 40, max_hp: 40, facing: "east" }),
    unit("unit_0002", "enemy", 5, 2, { template_id: "bandit_archer", name_zh: "盜賊弓手", hp: 30, max_hp: 30, facing: "west" }),
  ];
  return { team: "ally", map_id: "arsk3", map_name_zh: "AR-SK3", width: W, height: H, tiles, objects: [], units, traps: [], turn_order: ["unit_0002", HERO], active_unit: "unit_0002", round: 1, max_rounds: 30, weather_id: null, weather_name_zh: null, objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null, source_wells: [], zones: [], runes: [] } as unknown as BattleView;
}
const NONE: Highlights = { moves: [], attacks: [], directions: [], preview: [], telegraph: [], focus: null, hover: null, overlays: [], picked: [], vaults: [] };

async function board(host: HTMLElement, scale: number, title: string, skill: string | null, hover: [number, number] | null, burst = false): Promise<HTMLCanvasElement> {
  const frame = h("div");
  host.append(cell(frame, cap(title)));
  const r = new BattleRenderer();
  await r.init(frame);
  r.setScale(scale);
  r.setIdle(false);
  r.draw(buildDrawModel(prepView(), HERO));
  const marks = skill === null ? null : prepMarksOf(PREP, skill, hover === null ? null : { x: hover[0], y: hover[1] }, skill === "skill_pool" ? POOL : undefined);
  r.setHighlights({ ...NONE, ...(marks === null ? {} : { prep: marks }) });
  if (burst) {
    r.playPlaceBurst([{ x: 1, y: 5 }]);
    const clock = () => (r as unknown as { effectClock: number }).effectClock;
    while (clock() < 140) await new Promise((ok) => requestAnimationFrame(ok));
    r.setBoost(1e-6);
  }
  await new Promise((ok) => setTimeout(ok, 120));
  const app = (r as unknown as { app: Application }).app;
  app.render();
  return app.renderer.extract.canvas({ target: app.stage }) as HTMLCanvasElement;
}

async function prep(w: 1600 | 800): Promise<void> {
  const scale = w === 800 ? 0.53 : 1.31;
  shot.append(h("h2", { textContent: `戰前佈置 ${w} 寬（地圖縮放 ${scale}）：放得下的三格（金色四角括號＋中央金菱形），指著的那格整圈金框＋要放的東西半透明預覽＋「放在這裡」` }));
  const dlg = h("div");
  dlg.style.maxWidth = "520px";
  dlg.style.minHeight = "150px"; // DialogFrame 固定在畫面上方：留空，戰場不被視窗蓋到
  shot.append(dlg);
  createRoot(dlg).render(<PrepDialog prep={PREP} skillNames={NAMES} picked="skill_trap" enabled onPick={() => undefined} onSkip={() => undefined} />);
  shot.append(h("p", { textContent: `技能列提示：${PREP_HINT_ZH}`, className: "cap" }));
  const row = line();
  shot.append(row);
  const shots = [
    await board(row, scale, "選了一招：三格待放", "skill_trap", null),
    await board(row, scale, "指著 (0,6)：陷阱預覽＋放在這裡", "skill_trap", [0, 6]),
    await board(row, scale, "指著 (0,6)：刻印預覽", "skill_rune", [0, 6]),
    await board(row, scale, "指著 (0,6)：表面預覽（冰）", "skill_pool", [0, 6]),
    await board(row, scale, "放下 (1,5) 的一下（140 ms）", null, null, true),
  ];
  const T = 48 * scale, k = w === 800 ? 4 : 2;
  const zoom = line();
  shot.append(h("h3", { textContent: `起始區一帶真 1 倍 ×${k} 最近鄰` }), zoom);
  for (const src of shots) zoom.append(nn(src, k, 0, Math.round(T * 3.6), Math.round(T * 3.4), Math.round(T * 3.6)));
}

if (part === "prep") for (const w of params.get("w") === "800" ? [800 as const] : params.get("w") === "1600" ? [1600 as const] : [1600 as const, 800 as const]) await prep(w);
else if (part === "tint") tint();
else icons();
await new Promise((r) => setTimeout(r, 300));
document.body.dataset.ready = "1";
