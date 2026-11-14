// 開發用：灰燼之心 3×3 的部位小圖與本體圖示（GB-4b A3；需求 docs/art/GB巨型頭目-移植需求.md 4、9、11 第 7 項）。
// 開 `client/dev/gb4b-icons.html`（自己的 vite 後 /dev/gb4b-icons.html?mute=1）。不屬於正式 build。
// 每張圖示都走遊戲端 `render/qIcon/bossParts.ts` 的 `bossPartStateIcon`（和 `PartIcon` 同一個入口：灰化、紅×共用）。
// 場面（`?scene=`）：
//   icons（預設）：20px 真 1 倍四態（本體｜熔岩噴口｜殼縫｜核心 × 一般｜打不到｜未露出｜已破壞；本體只用「一般」），
//                  上排原尺寸、下排最近鄰 ×6（畫布內放大、`imageSmoothingEnabled = false`）；另附霧鎖真人一列對照、
//                  自查數字（同樣張 `icAudit`：不算外框色的平均亮度、亮面 ≥150 的比例、外接框）與指紋（FNV-1a，對照需求第 10 節）。
//   menu：兩個 iframe（寬 1600、800，各截上方 280 px），各自是 `scene=frame` 的選單情境。
//   frame&w=<寬>&h=<高>：真正的 `PartMenu`（本體｜熔岩噴口已破壞｜殼縫打不到「射程不夠」｜核心未露出「呼吸階段才露出」）
//                  與角色卡的部位列（`UnitParts`，同一份 `PartIcon`、`PartBar`）。
// 量測放 `body.dataset.check`（JSON），畫好後 `body.dataset.ready = "1"`。
import { createElement as h, useRef } from "react";
import { createRoot } from "react-dom/client";
import type { Action, PartOption, PartView, UnitView } from "../api/types";
import type { HeightGrid } from "../battle/elevation";
import dolls from "../render/fixtures/unitDolls.json";
import { waitForFonts } from "../render/fontLoad";
import { bossPartIcon, bossPartStateIcon, type BossDoll } from "../render/qIcon/bossParts";
import { GIANT_BOSS_TEMPLATE } from "../render/qIcon/giantParts";
import { PartMenu, type PartMenuState } from "../ui/PartMenu";
import { UnitParts } from "../ui/UnitInfo";
import "../styles/index.css";

const q = new URLSearchParams(location.search);
const SCENE = q.get("scene") ?? "icons";
const NAV = "#1e2236";
const ASH_DOLL: BossDoll = { template: GIANT_BOSS_TEMPLATE, dollLook: null, weaponId: null };
const MIST_DOLL: BossDoll = { template: "sect_mist_lock_master", dollLook: (dolls as Record<string, unknown>)["sect_mist_lock_master"] as BossDoll["dollLook"], weaponId: "one_handed_sword" };

const el = <T extends keyof HTMLElementTagNameMap>(tag: T, props: Partial<HTMLElementTagNameMap[T]> = {}, ...kids: (Node | string)[]): HTMLElementTagNameMap[T] => {
  const e = Object.assign(document.createElement(tag), props);
  e.append(...kids);
  return e;
};

function canvas(w: number, hh: number): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = hh;
  return c;
}

/** 一格：navy 底、圖示置中、四周留 `pad`（樣張 `icCell`）。 */
function iconCell(id: string, doll: BossDoll | null, px: number, ok: boolean, broken: boolean, pad = 3): HTMLCanvasElement {
  const S = px + 2 * pad;
  const c = canvas(S, S);
  const g = c.getContext("2d")!;
  g.fillStyle = NAV;
  g.fillRect(0, 0, S, S);
  g.drawImage(bossPartStateIcon(id, px, 1, ok, broken, doll), pad, pad);
  return c;
}

/** 最近鄰放大 k 倍（畫布內，不靠 CSS）。 */
function nn(src: HTMLCanvasElement, k: number): HTMLCanvasElement {
  const c = canvas(src.width * k, src.height * k);
  const g = c.getContext("2d")!;
  g.imageSmoothingEnabled = false;
  g.drawImage(src, 0, 0, c.width, c.height);
  return c;
}

/** 自查（樣張 `icAudit`）：20 真 1 倍、alpha ≥128、不算外框色。 */
function audit(cv: HTMLCanvasElement): { lum: number; hi: number; bbox: string } {
  const d = cv.getContext("2d")!.getImageData(0, 0, cv.width, cv.height).data;
  let n = 0;
  let sum = 0;
  let hi = 0;
  let x0 = 99;
  let x1 = -1;
  let y0 = 99;
  let y1 = -1;
  for (let i = 0; i < d.length; i += 4) {
    if (d[i + 3]! < 128) continue;
    const p = i / 4;
    const x = p % cv.width;
    const y = Math.floor(p / cv.width);
    x0 = Math.min(x0, x);
    x1 = Math.max(x1, x);
    y0 = Math.min(y0, y);
    y1 = Math.max(y1, y);
    if (Math.abs(d[i]! - 22) + Math.abs(d[i + 1]! - 18) + Math.abs(d[i + 2]! - 26) < 30) continue;
    const L = 0.299 * d[i]! + 0.587 * d[i + 1]! + 0.114 * d[i + 2]!;
    n++;
    sum += L;
    if (L >= 150) hi++;
  }
  return { lum: Math.round(sum / Math.max(1, n)), hi: Math.round((100 * hi) / Math.max(1, n)), bbox: `${x1 - x0 + 1}×${y1 - y0 + 1}` };
}

/** 指紋（樣張 `icHash`，FNV-1a over 像素）。 */
function fnv(cv: HTMLCanvasElement): string {
  const d = cv.getContext("2d")!.getImageData(0, 0, cv.width, cv.height).data;
  let x = 2166136261;
  for (let i = 0; i < d.length; i++) x = Math.imul(x ^ d[i]!, 16777619);
  return (x >>> 0).toString(16).padStart(8, "0");
}

/** 需求第 10 節的樣張指紋（20-1／20-2／16-1／16-2／12-1／12-2；本體只有 20-1／20-2）。 */
const SAMPLE_HASH: Record<string, readonly string[]> = {
  vent: ["2d58f9a4", "5c3f969e", "ac2b41f1", "863b9984", "a675efd6", "2191515c"],
  shell_seam: ["7d454b49", "73cc5128", "63d8883c", "07db5b2b", "dc8520d7", "23f9b7d9"],
  core: ["60d02581", "91e5ea21", "6615c0bf", "3d321d67", "ad5967fe", "181bf42e"],
  body: ["e30abe08", "e4653c2a"],
};

const STATES = [
  ["一般", true, false],
  ["打不到", false, false],
  ["未露出", false, false],
  ["已破壞", false, true],
] as const;

const STYLE = `
body { background: ${NAV}; color: #d8dbe0; font: 12px "Noto Sans TC", "Microsoft JhengHei", sans-serif; margin: 0; }
.sheet { padding: 10px 12px; display: inline-block; }
.sheet h2 { font-size: 13px; margin: 8px 0 4px; color: #f2e6c8; font-weight: 600; }
.sheet .note { color: #b8ab96; font-size: 11px; margin: 2px 0 6px; white-space: pre-wrap; }
.strip { display: flex; gap: 14px; align-items: flex-end; margin: 4px 0; }
.grp { display: flex; gap: 4px; align-items: flex-end; }
.grp + .grp { padding-left: 10px; border-left: 1px solid #3a3440; }
.cellc { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.cellc span { font-size: 11px; color: #b8ab96; }
canvas { display: block; flex: none; }
`;

const FRAME_STYLE = `
body { margin: 0; background: ${NAV}; }
.gb4b-board { position: relative; background: #2a2630; overflow: hidden; }
.gb4b-label { padding: 8px 12px 0; color: #b8ab96; font-size: 12px; }
.gb4b-row { display: flex; gap: 28px; align-items: flex-start; padding: 10px 12px; }
.gb4b-card { width: 240px; flex: none; }
.gb4b-slot { position: relative; width: 240px; flex: none; }
`;

function iconsScene(): void {
  document.head.append(el("style", { textContent: STYLE }));
  const root = el("div", { className: "sheet" });
  document.body.append(root);
  const rows: [string, string, BossDoll | null][] = [
    ["body", "本體（灰燼之心）", ASH_DOLL],
    ["vent", "熔岩噴口", null],
    ["shell_seam", "殼縫", null],
    ["core", "核心", null],
  ];
  root.append(
    el("h2", { textContent: "GB-4b A3：灰燼之心部位小圖 20px 真 1 倍（DPR 1）・一般｜打不到｜未露出｜已破壞（本體只用「一般」）" }),
    el("div", { className: "note", textContent: "每個部位一組：上排原尺寸（20＋四周 3 px 底），下排最近鄰 ×6。圖示走遊戲端 bossPartStateIcon（＝PartIcon），內部解析度 1。" }),
  );
  for (const [id, zh, doll] of rows) {
    const states = id === "body" ? STATES.slice(0, 1) : STATES;
    const g1 = el("div", { className: "grp" });
    const g2 = el("div", { className: "grp" });
    for (const [st, ok, broken] of states) {
      const cv = iconCell(id, doll, 20, ok, broken);
      g1.append(el("div", { className: "cellc" }, cv));
      g2.append(el("div", { className: "cellc" }, nn(cv, 6), el("span", { textContent: `${zh}・${st}` })));
    }
    root.append(el("div", { className: "strip" }, g1, g2));
  }
  // 霧鎖真人對照（同一套灰化與紅×）
  root.append(el("h2", { textContent: "對照：霧鎖真人（1 格頭目）同一套四態，20 真 1 倍 ×6" }));
  const mist = el("div", { className: "strip" });
  for (const [id, zh, doll] of [
    ["body", "本體（頭像）", MIST_DOLL],
    ["whisk", "拂塵", null],
  ] as const) {
    const g = el("div", { className: "grp" });
    for (const [st, ok, broken] of id === "body" ? STATES.slice(0, 1) : STATES)
      g.append(el("div", { className: "cellc" }, nn(iconCell(id, doll, 20, ok, broken), 6), el("span", { textContent: `${zh}・${st}` })));
    mist.append(g);
  }
  root.append(mist);
  // 自查與指紋
  const checks: Record<string, unknown> = {};
  const lines: string[] = [];
  for (const [id, zh, doll] of rows) {
    const cv = bossPartIcon(id, 20, 1, doll);
    if (cv === null) continue;
    const a = audit(cv);
    const sizes = id === "body" ? ([[20, 1], [20, 2]] as const) : ([[20, 1], [20, 2], [16, 1], [16, 2], [12, 1], [12, 2]] as const);
    const hashes = sizes.map(([px, res]) => {
      const c = bossPartIcon(id, px, res, doll);
      return c === null ? "-" : fnv(c);
    });
    const want = SAMPLE_HASH[id] ?? [];
    const same = hashes.map((x, i) => x === want[i]);
    checks[id] = { ...a, hashes, sameAsSample: same };
    lines.push(`${zh}：亮度 ${a.lum}、亮面 ${a.hi}%、外接 ${a.bbox}／20；指紋 ${hashes.map((x, i) => `${x}${same[i] ? "＝" : "≠"}`).join(" ")}`);
  }
  root.append(el("h2", { textContent: "自查（20 真 1 倍、不算外框色；需求 4.2：噴口 107／12％／18×18、殼縫 106／8％／18×20、核心 151／61％／18×19、本體 120／14％／18×18）" }));
  root.append(el("div", { className: "note", textContent: `${lines.join("\n")}\n（指紋後的＝／≠：和需求第 10 節樣張指紋比；遊戲端不要求相同）` }));
  document.body.dataset.check = JSON.stringify(checks);
}

// ---------------- 選單情境 ----------------

function bossView(): UnitView {
  const parts: PartView[] = [
    { id: "vent", name_zh: "熔岩噴口", hp: 0, max_hp: 32, broken: true, exposed: true, reach: "ranged", break_lines_zh: ["封住熔岩飛濺"], tiles: null },
    { id: "shell_seam", name_zh: "殼縫", hp: 32, max_hp: 32, broken: false, exposed: true, reach: "any", break_lines_zh: ["熔殼停止運作"], tiles: null, counts_as_behind: true },
    { id: "core", name_zh: "核心", hp: null, max_hp: null, broken: false, exposed: false, reach: "any", break_lines_zh: ["打斷蓄力", "封住吸氣 2 回合"], tiles: null },
  ];
  return {
    id: "ah",
    team: "enemy",
    template_id: GIANT_BOSS_TEMPLATE,
    name_zh: "灰燼之心",
    hp: 128,
    max_hp: 160,
    footprint: 3,
    boss_phase: { index: 1, total: 3, name_zh: "殼" },
    parts,
    doll_look: null,
    weapon_id: null,
  } as unknown as UnitView;
}

const OPTIONS: PartOption[] = [
  { part_id: "vent", name_zh: "熔岩噴口", ok: false, reason_zh: null },
  { part_id: "shell_seam", name_zh: "殼縫", ok: false, reason_zh: "射程不夠" },
  { part_id: "core", name_zh: "核心", ok: false, reason_zh: "呼吸階段才露出" },
];

function Frame({ w, hh }: { w: number; hh: number }) {
  const board = useRef<HTMLDivElement>(null);
  const boss = bossView();
  const menu: PartMenuState = { targetId: boss.id, tile: { x: 5, y: 3 }, action: { type: "attack", target: boss.id } as unknown as Action, options: OPTIONS, submit: false, dismissPin: false };
  const noop = (): void => undefined;
  // 版面用 `FRAME_STYLE` 的 class（浮動卡規則：元件裡不寫內聯 absolute／fixed）；選單本身仍是正式的 `.popup-menu.part-menu`
  return h(
    "div",
    { ref: board, className: "gb4b-board", style: { width: w, height: hh } },
    h("div", { className: "gb4b-label" }, `視窗寬 ${w}（開發頁・實機未看）：左＝角色卡部位列，右＝選部位小選單；圖示 20px、DPR 1`),
    h(
      "div",
      { className: "gb4b-row" },
      h("div", { className: "panel unit-info unit-card gb4b-card" }, h("div", { className: "unit-title" }, h("span", { className: "unit-name" }, boss.name_zh)), h(UnitParts, { unit: boss })),
      h("div", { className: "gb4b-slot" }, h(PartMenu, { menu, boss, model: {} as unknown as HeightGrid, scale: 1, boardRef: board, onPick: noop, onClose: noop, onPreview: noop })),
    ),
  );
}

async function main(): Promise<void> {
  await waitForFonts();
  if (SCENE === "frame") {
    const w = Number(q.get("w") ?? 1600);
    const hh = Number(q.get("h") ?? 900);
    document.head.append(el("style", { textContent: FRAME_STYLE }));
    createRoot(document.getElementById("root")!).render(h(Frame, { w, hh }));
    await new Promise((r) => setTimeout(r, 300));
  } else if (SCENE === "menu") {
    document.head.append(el("style", { textContent: STYLE }));
    const mk = (w: number, hh: number): HTMLIFrameElement => {
      const f = el("iframe", { src: `?scene=frame&w=${w}&h=${hh}&mute=1`, width: String(w), height: String(hh) });
      f.style.cssText = "display:block;border:0;margin:0 0 8px 0";
      return f;
    };
    // 選單與部位列沒有依視窗寬變化的樣式（float-card.css 沒有 @media），兩種寬度只截上方 280 px
    const frames = [mk(1600, 280), mk(800, 280)];
    document.body.append(...frames);
    await Promise.all(frames.map((f) => new Promise<void>((r) => { const tick = (): void => { if (f.contentDocument?.body?.dataset.ready === "1") r(); else setTimeout(tick, 100); }; tick(); })));
  } else iconsScene();
  document.body.dataset.ready = "1";
}

void main();
