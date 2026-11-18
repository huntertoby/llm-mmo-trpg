// 開發用：AR-SK2 美術移植的驗收畫面（`client/dev/arsk2-gallery.html`；不屬於正式 build）。
// 移植需求 docs/art/SK-2原語-移植需求.md：第 1 項部件圖樣、第 5 項鎖鏈下限（戰鬥演出看 sk2-gallery.html 的 `&strip=`、`&w=`）、
// 第 6 項狀態框「會擴散」記號。畫好後 `document.body.dataset.ready = "1"`；截圖存 `#shot`。
//   ?part=icons            三個部件圖樣：組裝列 30／26／18（2 倍內部解析度）＋真 1 倍 ×6 最近鄰＋18 的 2 倍 ×4 最近鄰
//   ?part=field&w=1600|800 戰場（沒給 w 時兩種都畫）狀態列（遊戲端 BattleRenderer）：盜賊由左到右 燃燒擴散｜燃燒｜流血擴散｜流血｜中毒擴散｜中毒，
//                          第二排一個帶 4 種（800 寬精簡列的「+N」膠囊）；下面是狀態列一帶的最近鄰放大
//   ?part=card             狀態卡 20（HUD 的 StatusBadge）：一般｜會擴散，真 1 倍＋×8 最近鄰；滑過第一個會擴散的看說明卡
import { createRoot } from "react-dom/client";
import type { Application } from "pixi.js";
import type { BattleView, Glossary, StatusView, UnitView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { buildDrawModel } from "../battle/drawModel";
import { setGlossary } from "../battle/glossary";
import { tile, unit } from "../battle/testFixtures";
import { BattleRenderer } from "../render/BattleRenderer";
import { waitForFonts } from "../render/fontLoad";
import * as QP from "../render/qIcon/parts";
import { statusIconTile, tileCanvas } from "../render/skillIcon";
import { CARD_PAD, spreadMarkCardCanvas } from "../render/spreadMark";
import { StatusBadge } from "../ui/StatusCardParts";
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
/** 最近鄰放大（像素看得清楚）。 */
function nn(src: HTMLCanvasElement, k: number, sx = 0, sy = 0, sw = src.width, sh = src.height): HTMLCanvasElement {
  const c = h("canvas", { width: sw * k, height: sh * k });
  const x = c.getContext("2d") as CanvasRenderingContext2D;
  x.imageSmoothingEnabled = false;
  x.drawImage(src, sx, sy, sw, sh, 0, 0, sw * k, sh * k);
  return c;
}
/** 畫布照 CSS 大小放（2 倍解析度的畫布顯示成一半大小）。 */
function at(cv: HTMLCanvasElement, css: number): HTMLCanvasElement {
  cv.style.width = cv.style.height = `${css}px`;
  return cv;
}
const cell = (...kids: Node[]): HTMLElement => h("div", { className: "cell" }, ...kids);
const line = (...kids: Node[]): HTMLElement => h("div", { className: "line" }, ...kids);

const PARTS: readonly [string, string][] = [
  ["absorb_surface", "吸收表面"],
  ["contagion", "疾病擴散"],
  ["hook", "鉤"],
];

function icons(): void {
  shot.append(h("h2", { textContent: "部件圖樣（組裝列圓片 30／26／18）：遊戲端 QP.chipCanvas" }));
  for (const [id, zh] of PARTS) {
    const cells: Node[] = [];
    for (const px of [30, 26, 18]) cells.push(cell(at(QP.chipCanvas("effect", id, px, 1), px), cap(`${px}`)));
    for (const px of [30, 26, 18]) cells.push(cell(nn(QP.chipCanvas("effect", id, px, 1, { res: 1 }), 6), cap(`${px} 真 1 倍 ×6`)));
    cells.push(cell(nn(QP.chipCanvas("effect", id, 18, 1), 4), cap("18 的 2 倍 ×4")));
    shot.append(h("h3", { textContent: `${zh}（${id}）` }), line(...cells));
  }
}

const HERO = "unit_0001";
const st = (id: string, contagious = false): StatusView => ({ status_id: id, remaining: 2, source_id: HERO, amount: null, charge_tiles: [], cost_status: false, ...(contagious ? { contagious: true } : {}) }) as StatusView;
const ROW: readonly [string, boolean][] = [
  ["burning", true],
  ["burning", false],
  ["bleed", true],
  ["bleed", false],
  ["poison", true],
  ["poison", false],
];

async function field(w: 1600 | 800): Promise<void> {
  const scale = w === 800 ? 0.53 : 1.31;
  const W = 8, H = 4;
  const tiles = [];
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) tiles.push(tile(x, y, { terrain: "stone" }));
  const units: UnitView[] = ROW.map(([id, sp], i) => unit(`u${i}`, "enemy", 1 + i, 1, { template_id: "bandit", name_zh: `盜賊${i + 1}`, hp: 30, max_hp: 40, facing: "west", statuses: [st(id, sp)] }));
  units.push(unit("u9", "enemy", 2, 3, { template_id: "bandit", name_zh: "盜賊", hp: 30, max_hp: 40, facing: "west", statuses: [st("burning", true), st("bleed", true), st("poison", true), st("weakened")] }));
  units.push(unit(HERO, "ally", 5, 3, { template_id: "hero_mage", name_zh: "法師", weapon_id: "fire_staff", hp: 40, max_hp: 40, facing: "west" }));
  const view = { team: "ally", map_id: "arsk2", map_name_zh: "AR-SK2", width: W, height: H, tiles, objects: [], units, traps: [], turn_order: [HERO], active_unit: HERO, round: 1, max_rounds: 30, weather_id: null, weather_name_zh: null, objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null, source_wells: [], zones: [], runes: [] } as unknown as BattleView;
  shot.append(h("h2", { textContent: `戰場 ${w} 寬（地圖縮放 ${scale}）真 1 倍：上排由左到右 燃燒擴散｜燃燒｜流血擴散｜流血｜中毒擴散｜中毒；下排左 4 種（燃燒擴散、流血擴散、中毒擴散、虛弱；800 寬是精簡列＋「+N」膠囊）` }));
  const frame = h("div");
  shot.append(frame);
  const r = new BattleRenderer();
  await r.init(frame);
  r.setScale(scale);
  r.setIdle(false);
  r.draw(buildDrawModel(view, HERO));
  const app = (r as unknown as { app: Application }).app;
  app.render();
  const src = app.renderer.extract.canvas({ target: app.stage }) as HTMLCanvasElement;
  const T = 48 * scale, k = w === 800 ? 8 : 5, top = Math.round(T * 1.35);
  shot.append(h("h3", { textContent: `狀態列一帶 ×${k} 最近鄰（上排）` }), nn(src, k, Math.round(T * 0.8), top - Math.round(T * 0.5), Math.round(T * 6.4), Math.round(T * 1.35)));
  shot.append(h("h3", { textContent: `下排帶 4 種的那個 ×${k} 最近鄰` }), nn(src, k, Math.round(T * 1.6), top + Math.round(T * 1.5), Math.round(T * 1.8), Math.round(T * 1.35)));
}

function card(): void {
  shot.append(h("h2", { textContent: "狀態卡 20（HUD 的 StatusBadge）：一般｜會擴散；說明卡是滑過第一個會擴散的燃燒" }));
  const host = h("div", { className: "line" });
  host.style.marginTop = "16px";
  shot.append(host);
  createRoot(host).render(
    <div style={{ display: "flex", gap: 14, alignItems: "center", padding: "10px 4px" }}>
      {ROW.map(([id, sp], i) => (
        <span key={i} data-spread={sp ? "1" : "0"} data-id={id}>
          <StatusBadge status={st(id, sp)} text={`${glossaryName(id)} 2 回合`} />
        </span>
      ))}
    </div>,
  );
  const cells: Node[] = [];
  for (const [id, sp] of ROW) {
    const px = 20, pad = CARD_PAD, side = px + 2 * pad;
    const c = h("canvas", { width: side, height: side });
    const x = c.getContext("2d") as CanvasRenderingContext2D;
    x.drawImage(tileCanvas(statusIconTile(id), px, 1), pad, pad);
    if (sp) {
      const m = spreadMarkCardCanvas(px, 1);
      if (m !== null) x.drawImage(m, 0, 0);
    }
    cells.push(cell(nn(c, 8), cap(`${id}${sp ? " 會擴散" : ""} 真 1 倍 ×8`)));
  }
  shot.append(h("h3", { textContent: "真 1 倍（DPR 1）×8 最近鄰：圖示＋記號（四周各留 8 px）" }), line(...cells));
}

function glossaryName(id: string): string {
  const g = (glossary as unknown as { statuses: { id: string; name_zh: string }[] }).statuses.find((s) => s.id === id);
  return g?.name_zh ?? id;
}

if (part === "field") for (const w of params.get("w") === "800" ? [800 as const] : params.get("w") === "1600" ? [1600 as const] : [1600 as const, 800 as const]) await field(w);
else if (part === "card") card();
else icons();
await new Promise((r) => setTimeout(r, 300));
document.body.dataset.ready = "1";
