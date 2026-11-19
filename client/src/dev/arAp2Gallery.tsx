// 開發用：AR-AP2 預支美術移植的驗收畫面（`client/dev/arap2-gallery.html`；不屬於正式 build）。
// 移植需求 docs/art/AP-2-移植需求.md 第 1 節 1～5 項；對照樣張截圖 docs/art/shots/ap2-borrow/。
// 演出用真引擎事件（`dev/fixtures/ap2Events.json`）走正式的 playbackPlan → frameOps → BattleRenderer；
// 每一格各自一個繪製器：停掉 Pixi 的 ticker、每次手動推 10 ms，停在「預支演出開始後第幾毫秒」（不靠 requestAnimationFrame 的時間點）。
// 畫好後 `document.body.dataset.ready = "1"`。
//   ?part=icons                 效果「預支」、觸發「這回合用完所有 AP 時」：組裝列 30／26／18、真 1 倍 ×6、18 的 2 倍 ×4（左：移植前暫借）
//   ?part=status                狀態「預支」和「透支」並排：狀態卡 20、說明行 16、頭頂 11（向量與真 1 倍 ×6）
//   ?part=field&w=1600|800      戰場頭頂狀態列：法師＝透支＋預支、戰士＝預支、弓手＝透支；整張真 1 倍，下面 ×3（1600）／×4（800）最近鄰
//   ?part=anim&w=1600|800       施放演出 50／110／170／220／270／310 ms，三種站位（a 頭頂兩個狀態、b 面前有人、c 面向西）＋上一排站人；真 1 倍 ×2／×4
//   ?part=aprow&w=1600          AP 列淡入的時間點：演出 100／214／216／270／320／420 ms 的戰場＋主角 AP 列
import { createRoot } from "react-dom/client";
import { flushSync } from "react-dom";
import type { Application } from "pixi.js";
import type { BattleResponse, BattleView, Facing, Glossary, SkillCard, StatusView, StepOut, UnitView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import fixture from "./fixtures/ap2Events.json";
import { buildDrawModel } from "../battle/drawModel";
import { setGlossary } from "../battle/glossary";
import { frameOps, playbackPlan } from "../battle/playback";
import { BORROW_MS } from "../battle/borrowFx";
import { tile, unit } from "../battle/testFixtures";
import { attackFamilyInView, creatureStrikeInView, weaponClassInView } from "../battle/viewGrip";
import { BattleRenderer } from "../render/BattleRenderer";
import { waitForFonts } from "../render/fontLoad";
import * as QP from "../render/qIcon/parts";
import * as QT from "../render/qIcon/status";
import { statusIconTile, tileCanvas } from "../render/skillIcon";
import { statusIconCanvas } from "../render/statusIcon";
import { apChip } from "../ui/statusCard";
import { StatChipView } from "../ui/StatusCardParts";
import { AP_FRESH_DELAY_VAR } from "../ui/apFade";
import "../styles/index.css";

setGlossary(glossary as unknown as Glossary);
await waitForFonts();

const params = new URLSearchParams(location.search);
const part = params.get("part") ?? "icons";
const W800 = params.get("w") === "800";
const SCALE = W800 ? 0.53 : 1.31;
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
const cell = (...kids: Node[]): HTMLElement => h("div", { className: "cell" }, ...kids);
const line = (...kids: Node[]): HTMLElement => h("div", { className: "line" }, ...kids);
/** 最近鄰放大（真 1 倍的畫布 → k 倍）。 */
function nn(src: HTMLCanvasElement, k: number, sx = 0, sy = 0, sw = src.width, sh = src.height): HTMLCanvasElement {
  const c = h("canvas", { width: Math.max(1, Math.round(sw * k)), height: Math.max(1, Math.round(sh * k)), className: "px" });
  const x = c.getContext("2d") as CanvasRenderingContext2D;
  x.imageSmoothingEnabled = false;
  x.drawImage(src, sx, sy, sw, sh, 0, 0, sw * k, sh * k);
  return c;
}
function at(cv: HTMLCanvasElement | null, css: number): HTMLCanvasElement {
  const c = cv ?? h("canvas");
  c.style.width = c.style.height = `${css}px`;
  return c;
}

// ---- 1、2、3：部件與狀態圖示 ----

function icons(): void {
  shot.append(h("h2", { textContent: "部件圖樣（組裝列圓片 30／26／18）：遊戲端 QP.chipCanvas；每組左＝移植前暫借、右＝AR-AP2" }));
  const rows: readonly [string, string, string, string][] = [
    ["effect", "borrow_ap", "grant_ap", "效果「預支」（暫借：給予 AP）"],
    ["trigger", "on_ap_spent_all", "on_turn_end", "觸發「這回合用完所有 AP 時」（暫借：回合結束時）"],
  ];
  for (const [cat, id, old, title] of rows) {
    const vec: Node[] = [], t1: Node[] = [];
    for (const px of [30, 26, 18]) {
      vec.push(cell(at(QP.chipCanvas(cat, old, px, 1), px), cap(`${px} 暫借`)), cell(at(QP.chipCanvas(cat, id, px, 1), px), cap(`${px} 新`)));
      t1.push(cell(nn(QP.chipCanvas(cat, old, px, 1, { res: 1 }), 6), cap(`${px} 暫借 真 1 倍 ×6`)), cell(nn(QP.chipCanvas(cat, id, px, 1, { res: 1 }), 6), cap(`${px} 新 真 1 倍 ×6`)));
    }
    t1.push(cell(nn(QP.chipCanvas(cat, id, 18, 1), 4), cap("18 的 2 倍 ×4")));
    shot.append(h("h3", { textContent: `${title}：${cat}:${id}（${QP.entry(cat, id).zh}）` }), line(...vec), line(...t1));
  }
}

function status(): void {
  shot.append(h("h2", { textContent: "狀態「預支」borrowed_ap 和「透支」overdrawn 並排：狀態卡 20（statusIconTile）、說明行 16（statusIconCanvas）、頭頂 11（headCanvas，框 9）" }));
  for (const [id, zh] of [["overdrawn", "透支"], ["borrowed_ap", "預支"]] as const) {
    const cells: Node[] = [];
    cells.push(cell(at(tileCanvas(statusIconTile(id), 20), 20), cap("卡 20")));
    cells.push(cell(at(statusIconCanvas(id, 16), 16), cap("說明 16")));
    cells.push(cell(at(QT.headCanvas(id, 11), 11), cap("頭頂 11")));
    cells.push(cell(nn(tileCanvas(statusIconTile(id), 20, 1), 6), cap("卡 20 真 1 倍 ×6")));
    const s16 = statusIconCanvas(id, 16, 1);
    if (s16 !== null) cells.push(cell(nn(s16, 6), cap("說明 16 真 1 倍 ×6")));
    const hd = QT.headCanvas(id, 11, 1, { res: 1 });
    if (hd !== null) cells.push(cell(nn(hd, 6), cap("頭頂 11 真 1 倍 ×6")));
    shot.append(h("h3", { textContent: `${zh}（${id}）` }), line(...cells));
  }
}

// ---- 戰場 ----

const HERO = "unit_0001";
const SKILL = "skill_t_prim";
const EVENTS = (fixture as unknown as { borrow: { events: Record<string, unknown>[] } }).borrow.events;
const CARD = { id: SKILL, shape: "自身", skeleton: "aura", effect_ids: ["borrow_ap"], icon: { segments: [{ skeleton: "aura", shape_id: "self", range: 0, effects: [{ type: "borrow_ap" }] }] } } as unknown as SkillCard;
const MW = 6, MH = 5;

const st = (id: string, remaining: number | null = 1): StatusView => ({ status_id: id, remaining, source_id: HERO, amount: null, charge_tiles: [], cost_status: false }) as StatusView;
function viewOf(units: UnitView[]): BattleView {
  const tiles = [];
  for (let y = 0; y < MH; y++) for (let x = 0; x < MW; x++) tiles.push(tile(x, y, { terrain: (x * 3 + y) % 7 === 0 ? "dirt" : "stone" }));
  return { team: "ally", map_id: "arap2", map_name_zh: "AR-AP2", width: MW, height: MH, tiles, objects: [], units, traps: [], turn_order: [HERO], active_unit: HERO, round: 1, max_rounds: 30, weather_id: null, weather_name_zh: null, objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null, source_wells: [], zones: [], runes: [] } as unknown as BattleView;
}
const AP_BEFORE = { ap: 3, ap_per_turn: 3, ap_max: 4 };
const AP_AFTER = { ap: 4, ap_per_turn: 3, ap_max: 4, ap_borrowed: 1, ap_next_loss: 1, ap_next_loss_borrowed: 1 };
const mage = (x: number, facing: Facing, statuses: StatusView[], ap: Partial<UnitView>): UnitView =>
  unit(HERO, "ally", x, 2, { template_id: "hero_mage", name_zh: "法師", weapon_id: "fire_staff", hp: 40, max_hp: 40, facing, statuses, ...ap });
const upper = (): UnitView[] => [
  unit("unit_0011", "ally", 1, 1, { template_id: "hero_archer", name_zh: "弓手", weapon_id: "longbow", hp: 30, max_hp: 30, facing: "east" }),
  unit("unit_0012", "enemy", 2, 1, { template_id: "bandit", name_zh: "盜賊", hp: 30, max_hp: 30, facing: "west" }),
  unit("unit_0013", "ally", 3, 1, { template_id: "hero_fighter", name_zh: "戰士", weapon_id: "longsword", hp: 40, max_hp: 40, facing: "west" }),
];

interface Stage {
  title: string;
  before: UnitView[];
  after: UnitView[];
}
/** 三種站位（樣張 4.1）：a 頭頂兩個狀態（透支＋預支）、b 面前那格站一個盜賊、c 面向西。上一排照舊站人。 */
function stages(): Stage[] {
  const foe = unit("unit_0014", "enemy", 3, 2, { template_id: "bandit", name_zh: "盜賊", hp: 30, max_hp: 30, facing: "west" });
  const a = [st("overdrawn"), st("borrowed_ap")];
  return [
    { title: "(a) 施放者頭頂兩個狀態（透支＋預支）", before: [mage(2, "east", a, AP_BEFORE), ...upper()], after: [mage(2, "east", a, AP_AFTER), ...upper()] },
    { title: "(b) 面前那格站一個盜賊", before: [mage(2, "east", [], AP_BEFORE), foe, ...upper()], after: [mage(2, "east", [st("borrowed_ap")], AP_AFTER), foe, ...upper()] },
    { title: "(c) 面向西", before: [mage(3, "west", [], AP_BEFORE), ...upper()], after: [mage(3, "west", [st("borrowed_ap")], AP_AFTER), ...upper()] },
  ];
}

const appOf = (r: BattleRenderer): Application => (r as unknown as { app: Application }).app;
const clockOf = (r: BattleRenderer): number => (r as unknown as { effectClock: number }).effectClock;

async function renderer(host: HTMLElement): Promise<BattleRenderer> {
  const r = new BattleRenderer();
  await r.init(host);
  r.setScale(SCALE);
  r.setIdle(false);
  return r;
}

/** 這一步的播放：預支片段從出招原點的第幾毫秒開始、速度倍率、畫面更新在第幾毫秒、AP 列延後幾毫秒。 */
function stepPlan(s: Stage) {
  const before = viewOf(s.before), after = viewOf(s.after);
  // 事件是在 (1,3) 跑的：自身技能的格子換成這一頁施放者站的格子（不然施放者會轉向舊格子）
  const pos = s.before[0]!.pos;
  const events = EVENTS.map((e) => (e.type === "skill_used" ? { ...e, tiles: [{ x: pos.x, y: pos.y }] } : e));
  const res = { steps: [{ actor_id: HERO, events, view: after, step: { type: "use_skill", unit_id: HERO, skill_id: SKILL } } as unknown as StepOut], initial_view: before, view: after } as unknown as BattleResponse;
  const plan = playbackPlan(res, HERO, "normal", { [SKILL]: CARD }, new Set(), weaponClassInView, attackFamilyInView, creatureStrikeInView, false);
  const frame = plan.frames.find((f) => f.skill?.some((r) => r.clip === "borrow_pull"));
  if (frame === undefined) throw new Error("no borrow_pull row");
  const ops = frameOps(frame);
  const vfx = ops.find((o) => o.op === "vfx"), view = ops.find((o) => o.op === "view");
  if (vfx?.op !== "vfx" || view?.op !== "view") throw new Error("no vfx/view op");
  const row = frame.skill!.find((r) => r.clip === "borrow_pull")!;
  return { before, after, vfx, row, k: row.ms / BORROW_MS, viewAt: vfx.vfx.leadMs > 0 ? vfx.vfx.leadMs : 0, delay: view.apFadeDelayMs ?? 0 };
}

/** 一格：播到預支演出開始後 `ms` 毫秒停住（每次推 10 ms），回傳整張戰場的真 1 倍畫布。 */
async function frameAt(host: HTMLElement, s: Stage, ms: number): Promise<{ cv: HTMLCanvasElement; atMs: number }> {
  const p = stepPlan(s);
  const r = await renderer(host);
  r.draw(buildDrawModel(p.before, HERO));
  const app = appOf(r);
  app.ticker.stop();
  let now = performance.now();
  app.ticker.update(now);
  const t0 = clockOf(r);
  const origins = p.vfx.skill === undefined ? undefined : r.playSkill(p.vfx.skill);
  r.playVfx(p.vfx.vfx, p.vfx.impactMs, false, origins);
  const target = p.row.startMs + ms * p.k;
  let shown = false;
  while (clockOf(r) - t0 < target - 1e-6) {
    const step = Math.min(10, target - (clockOf(r) - t0));
    now += step;
    app.ticker.update(now);
    if (!shown && clockOf(r) - t0 >= p.viewAt) {
      r.draw(buildDrawModel(p.after, HERO));
      shown = true;
    }
  }
  app.render();
  return { cv: app.renderer.extract.canvas({ target: app.stage }) as HTMLCanvasElement, atMs: clockOf(r) - t0 };
}

async function field(): Promise<void> {
  const w = W800 ? 800 : 1600, k = W800 ? 4 : 3;
  shot.append(h("h2", { textContent: `戰場頭頂狀態列 ${w} 寬（地圖縮放 ${SCALE}）：法師＝透支＋預支、戰士＝只有預支、弓手＝只有透支；上：整張真 1 倍，下：單位一帶 ×${k} 最近鄰` }));
  const units = [
    mage(1, "east", [st("overdrawn"), st("borrowed_ap")], AP_BEFORE),
    unit("unit_0013", "ally", 3, 2, { template_id: "hero_fighter", name_zh: "戰士", weapon_id: "longsword", hp: 40, max_hp: 40, facing: "east", statuses: [st("borrowed_ap")] }),
    unit("unit_0011", "ally", 5, 2, { template_id: "hero_archer", name_zh: "弓手", weapon_id: "longbow", hp: 30, max_hp: 30, facing: "west", statuses: [st("overdrawn")] }),
  ];
  const host = h("div");
  shot.append(host);
  const r = await renderer(host);
  r.draw(buildDrawModel(viewOf(units), HERO));
  await new Promise((ok) => setTimeout(ok, 200));
  const app = appOf(r);
  app.render();
  const cv = app.renderer.extract.canvas({ target: app.stage }) as HTMLCanvasElement;
  host.remove();
  const T = 48 * SCALE;
  shot.append(cell(nn(cv, 1), cap("真 1 倍")), h("div", {}, nn(cv, k, 0, Math.round(T * 1.6), cv.width, Math.round(T * 1.6))));
  shot.append(h("h3", { textContent: "狀態卡 20（側欄）" }));
  for (const [id, zh] of [["overdrawn", "透支"], ["borrowed_ap", "預支"]] as const) shot.append(line(cell(at(tileCanvas(statusIconTile(id), 20), 20)), h("span", { textContent: zh })));
}

/** 戰場畫布裡施放者一帶（往上半格含上一排血條、往下到腳底）。 */
function crop(cv: HTMLCanvasElement, x: number, k: number): HTMLCanvasElement {
  const T = 48 * SCALE;
  return nn(cv, k, Math.round(T * (x - 1)), Math.round(T * 0.55), Math.round(T * 3), Math.round(T * 2.25));
}

const STRIP = [50, 110, 170, 220, 270, 310];
async function anim(): Promise<void> {
  const w = W800 ? 800 : 1600, k = W800 ? 4 : 2;
  const p0 = stepPlan(stages()[0]!);
  shot.append(h("h2", { textContent: `施放演出 borrow_pull ${w} 寬（地圖縮放 ${SCALE}）：預支演出開始後 ${STRIP.join("／")} ms；施放者一帶真 1 倍 ×${k} 最近鄰（片段從出招原點 ${Math.round(p0.row.startMs)} ms 開始、長 ${Math.round(p0.row.ms)} ms）` }));
  const scratch = h("div");
  scratch.className = "offscreen"; // 繪製器的畫布放在畫面外（截圖只看下面最近鄰放大的那一份）
  document.body.append(scratch);
  for (const s of stages()) {
    const cells: Node[] = [];
    for (const ms of STRIP) {
      const host = h("div");
      scratch.append(host);
      const f = await frameAt(host, s, ms);
      const x = s.before[0]!.pos.x;
      cells.push(cell(crop(f.cv, x, k), cap(`${ms} ms`)));
    }
    shot.append(h("h3", { textContent: s.title }), line(...cells));
  }
  scratch.remove();
}

const AP_STRIP = [100, 214, 216, 270, 320, 420];
async function aprow(): Promise<void> {
  const s = stages()[1]!;
  const p = stepPlan(s);
  const fadeAt = (p.viewAt + p.delay - p.row.startMs) / p.k;
  shot.append(h("h2", { textContent: `AP 列淡入的時間點（${W800 ? 800 : 1600} 寬）：畫面更新在預支演出的 ${Math.round((p.viewAt - p.row.startMs) / p.k)} ms，AP 列延後 ${p.delay} ms → 演出 ${Math.round(fadeAt)} ms 開始淡入 200 ms（菱形到胸口）` }));
  const scratch = h("div");
  scratch.className = "offscreen"; // 繪製器的畫布放在畫面外（截圖只看下面最近鄰放大的那一份）
  document.body.append(scratch);
  const row = line();
  shot.append(row);
  for (const ms of AP_STRIP) {
    const host = h("div");
    scratch.append(host);
    const f = await frameAt(host, s, ms);
    const box = h("div");
    box.style.background = "#232631";
    box.style.padding = "4px 6px";
    const shownAt = p.row.startMs + ms * p.k;
    const after = shownAt >= p.viewAt;
    if (after) box.style.setProperty(AP_FRESH_DELAY_VAR, `${p.delay}ms`);
    const hero = (after ? s.after : s.before)[0]!;
    row.append(cell(crop(f.cv, hero.pos.x, W800 ? 4 : 2), box, cap(`${ms} ms${after ? "" : "（畫面還沒更新）"}`)));
    flushSync(() => createRoot(box).render(<StatChipView chip={apChip(hero)} />));
    // 淡入停在這一刻：動畫從畫面更新那一刻起算（含延後）
    for (const a of box.getAnimations({ subtree: true })) {
      a.pause();
      a.currentTime = Math.max(0, shownAt - p.viewAt);
    }
  }
  scratch.remove();
}

if (part === "status") status();
else if (part === "field") await field();
else if (part === "anim") await anim();
else if (part === "aprow") await aprow();
else icons();
await new Promise((r) => setTimeout(r, 300));
document.body.dataset.ready = "1";
