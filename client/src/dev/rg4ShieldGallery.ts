// 開發用：RG-4 持盾弟子的雲紋碑盾（`dev/rg4-shield-gallery.html`；不屬於正式 build）。
// 模式（?mode=）：
//   fp     既有盾（圓盾、鳶盾、塔盾）的紙娃娃像素指紋：正面、背面、側面朝東／朝西 × 幾種姿勢 × qStamp DPR 1／2／3、drawFigurePose DPR 1／2。
//          輸出 `<pre id="out">` 一行一格「key fnv1a」，最後一行是全部的總指紋；改前改後各跑一次、比對文字（必須完全相同）。
//   shield 只畫盾：樣張 docs/art/sample/rgUnits.js 的 VIEW_DRAW（SHIELDS.A）vs 遊戲端 qSectShield，同一個錨點座標，
//          front／side／back × 縮放 1、2、4 × DPR 1、2 × 錨點整數／小數，回報差異像素數（目標 0）。
//   doll   整隻持盾弟子：① 遊戲端 qDoll ＋ 樣張的鑰匙色代理（RGUnits.withShield 掛在塔盾流程上）vs 遊戲端 sect_great 分支；
//          ② 樣張 QDoll.stamp（RGUnits.stampDoll）vs 遊戲端 qStamp（SAMPLE_HOOKS），另附塔盾、持劍弟子當「兩邊 qDoll 原本的差異」基準。
//   （沒有 mode）並排看圖：樣張 vs 遊戲端的盾 ×4、整隻持盾弟子四方向。
// 重跑（無頭 Chrome）：chrome --headless --dump-dom --virtual-time-budget=60000 "http://127.0.0.1:<port>/dev/rg4-shield-gallery.html?mode=fp"
import currentSrc from "../../../docs/art/sample/current.js?raw";
import idleSrc from "../../../docs/art/sample/idleWeapons.js?raw";
import paperdollSrc from "../../../docs/art/sample/paperdoll.js?raw";
import qDollSrc from "../../../docs/art/sample/qDoll.js?raw";
import raceArtSrc from "../../../docs/art/sample/raceArt.js?raw";
import rgUnitsSrc from "../../../docs/art/sample/rgUnits.js?raw";
import type { DollSpec, GearItem } from "../render/appearance";
import type { Facing } from "../api/types";
import { weaponIdleFrame } from "../render/idleWeapons";
import { gaitPose } from "../render/motionClips";
import { drawFigurePose } from "../render/paperdoll";
import type { QItem, QPose, QUnit, QView } from "../render/qCore";
import { SAMPLE_HOOKS, sampleHitPose } from "../render/qSample";
import { sectShieldBack, sectShieldFront, sectShieldSide } from "../render/qSectShield";
import { GAME_HOOKS, qUnitOf } from "../render/qSpec";
import { qStamp } from "../render/qStamp";

type C2 = CanvasRenderingContext2D;
interface RG {
  VIEW_DRAW: Record<"front" | "side" | "back", (ctx: C2, sh: unknown) => void>;
  SHIELDS: Record<"A" | "B", unknown>;
  withShield: (unit: unknown, view: string, fn: () => void) => void;
  stampDoll: (ctx: C2, unit: unknown, view: string, cx: number, cy: number, size: number, west: boolean, opts: { dpr: number }) => void;
  sectShieldDisciple: (v: string) => { look: Record<string, unknown>; gear: Record<string, Record<string, unknown>> };
}

const MODE = new URLSearchParams(location.search).get("mode") ?? "";
const out = document.createElement("pre");
out.id = "out";
const lines: string[] = [];
const log = (s: string): void => void lines.push(s);

// ---------- 共用 ----------
function cv(w: number, h: number): [HTMLCanvasElement, C2] {
  const c = document.createElement("canvas");
  c.width = Math.max(1, Math.ceil(w));
  c.height = Math.max(1, Math.ceil(h));
  return [c, c.getContext("2d")!];
}
function fnv(c: HTMLCanvasElement): string {
  const d = c.getContext("2d")!.getImageData(0, 0, c.width, c.height).data;
  let h = 0x811c9dc5;
  for (let i = 0; i < d.length; i++) {
    h ^= d[i]!;
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h.toString(16).padStart(8, "0");
}
function diffPx(a: HTMLCanvasElement, b: HTMLCanvasElement): number {
  const A = a.getContext("2d")!.getImageData(0, 0, a.width, a.height).data;
  const B = b.getContext("2d")!.getImageData(0, 0, b.width, b.height).data;
  let n = 0;
  for (let i = 0; i < A.length; i += 4) if (A[i] !== B[i] || A[i + 1] !== B[i + 1] || A[i + 2] !== B[i + 2] || A[i + 3] !== B[i + 3]) n++;
  return n;
}
let sampleLoaded = false;
/** 樣張腳本照 rg-units.html 的順序以傳統 <script> 載入（共用全域詞法作用域）。 */
function loadSample(): void {
  if (sampleLoaded) return;
  for (const src of [currentSrc, raceArtSrc, paperdollSrc, qDollSrc, idleSrc, rgUnitsSrc]) {
    const s = document.createElement("script");
    s.textContent = src;
    document.head.appendChild(s);
  }
  sampleLoaded = true;
}
const RGU = (): RG => (window as unknown as { RGUnits: RG }).RGUnits;

const VIEWS: ReadonlyArray<readonly [QView, boolean, string]> = [
  ["front", false, "front"],
  ["back", false, "back"],
  ["side", false, "east"],
  ["side", true, "west"],
];
const facingOf = (v: QView, west: boolean): Facing => (v === "front" ? "south" : v === "back" ? "north" : west ? "west" : "east");

// ---------- 單位 ----------
const SECT_LOOK = { skin: "#d9a47a", hair: "bun" as const, hairColor: "#1c1c22" };
const ROBE: GearItem = { kind: "robe", material: "cloth", color: "#5f8f8a", trim: "#dfe4e2" };
const SWORD: GearItem = { kind: "sword", material: "iron" };
const SECT_SHIELD: QItem = { kind: "shield_kite", form: "sect_great", material: "wood", color: "#5f8f8a", trim: "#dfe4e2", emblem: "peak" };
const SHIELDS: ReadonlyArray<readonly [string, GearItem]> = [
  ["round-iron", { kind: "shield_round", material: "iron" }],
  ["round-blue", { kind: "shield_round", material: "wood", color: "#2f5fae", trim: "#e8bb48" }],
  ["kite-iron", { kind: "shield_kite", material: "iron" }],
  ["kite-form", { kind: "shield_kite", form: "kite", material: "steel" }],
  ["kite-color", { kind: "shield_kite", material: "wood", color: "#5f8f8a", trim: "#dfe4e2" }],
  ["tower-wood", { kind: "shield_kite", form: "tower", material: "wood" }],
  ["tower-color", { kind: "shield_kite", form: "tower", material: "wood", color: "#6a4a2e" }],
];
const BASES: ReadonlyArray<readonly [string, (off: GearItem) => DollSpec]> = [
  ["sect", (off) => ({ look: { ...SECT_LOOK }, gear: { body: ROBE, main_hand: SWORD, off_hand: off } })],
  ["plate", (off) => ({ look: { skin: "#f1c9a5", hair: "short", hairColor: "#6a3d1e" }, gear: { body: { kind: "plate", material: "steel" }, feet: { kind: "boots", material: "leather" }, off_hand: off } })],
];
function poses(view: QView): ReadonlyArray<readonly [string, QPose | null]> {
  const idle = (ms: number): QPose => weaponIdleFrame("sword_shield", "rg4", ms, { view, breath: false, live: false }).pose as QPose;
  return [
    ["rest", null],
    ["idle0", idle(0)],
    ["idle700", idle(700)],
    ["idle1400", idle(1400)],
    ["walk", gaitPose(1.1, "walk") as QPose],
    ["slash", sampleHitPose("sword")],
    ["fb1-2", { fbk: 1, fbt: 2 } as QPose],
    ["fb1-4", { fbk: 1, fbt: 4 } as QPose],
  ];
}

// ---------- hash：既有盾的指紋 ----------
function stampHash(spec: DollSpec, v: QView, west: boolean, pose: QPose | null, dpr: number): string {
  const [c, g] = cv(96 * dpr, 96 * dpr);
  g.scale(dpr, dpr);
  qStamp(g, qUnitOf(spec), v, 48, 78, 1, west, GAME_HOOKS, pose, { dpr });
  return fnv(c);
}
function figureHash(spec: DollSpec, v: QView, west: boolean, pose: QPose | null, dpr: number): string {
  const [c, g] = cv(96 * dpr, 96 * dpr);
  g.scale(dpr * 1.4, dpr * 1.4);
  g.translate(34, 56);
  drawFigurePose(g, spec, facingOf(v, west), false, true, pose as never);
  return fnv(c);
}
function runHash(): void {
  let all = 0x811c9dc5;
  for (const [sk, off] of SHIELDS)
    for (const [bk, base] of BASES)
      for (const [v, west, vk] of VIEWS)
        for (const [pk, pose] of poses(v)) {
          const spec = base(off);
          const hs = [stampHash(spec, v, west, pose, 1), stampHash(spec, v, west, pose, 2), stampHash(spec, v, west, pose, 3), figureHash(spec, v, west, pose, 1), figureHash(spec, v, west, pose, 2)];
          const line = `${sk}/${bk}/${vk}/${pk} ${hs.join(" ")}`;
          log(line);
          for (let i = 0; i < line.length; i++) all = Math.imul(all ^ line.charCodeAt(i), 0x01000193) >>> 0;
        }
  log(`TOTAL ${lines.length} cells ${all.toString(16).padStart(8, "0")}`);
}

// ---------- shield：樣張 vs 遊戲端（只畫盾） ----------
const GAME_DRAW: Record<"front" | "side" | "back", (ctx: C2, it: QItem) => void> = { front: sectShieldFront, side: sectShieldSide, back: sectShieldBack };
function shieldPair(view: "front" | "side" | "back", k: number, dpr: number, ax: number, ay: number): [HTMLCanvasElement, HTMLCanvasElement] {
  const res: HTMLCanvasElement[] = [];
  for (const who of ["sample", "game"] as const) {
    const [c, g] = cv(44 * k * dpr, 44 * k * dpr);
    g.scale(k * dpr, k * dpr);
    g.translate(ax, ay);
    if (who === "sample") RGU().VIEW_DRAW[view](g, RGU().SHIELDS.A);
    else GAME_DRAW[view](g, SECT_SHIELD);
    res.push(c);
  }
  return [res[0]!, res[1]!];
}
function runShield(): void {
  loadSample();
  let total = 0;
  for (const view of ["front", "side", "back"] as const)
    for (const k of [1, 2, 4])
      for (const dpr of [1, 2])
        for (const [ax, ay] of [
          [22, 22],
          [22.3, 21.6],
        ] as const) {
          const [a, b] = shieldPair(view, k, dpr, ax, ay);
          const n = diffPx(a, b);
          total += n;
          log(`shield ${view} k${k} dpr${dpr} anchor(${ax},${ay}) diff=${n} sample=${fnv(a)} game=${fnv(b)}`);
        }
  log(`SHIELD TOTAL diff=${total}`);
}

// ---------- doll：整隻 ----------
const gameSect = (): QUnit => qUnitOf({ look: { ...SECT_LOOK }, gear: { body: ROBE, main_hand: SWORD, off_hand: SECT_SHIELD as GearItem } });
const proxySect = (): QUnit => qUnitOf({ look: { ...SECT_LOOK }, gear: { body: ROBE, main_hand: SWORD, off_hand: { kind: "shield_kite", form: "tower", color: "#ff00ff", rg: "A" } as GearItem } });
function dollCanvas(draw: (g: C2) => void, dpr: number): HTMLCanvasElement {
  const [c, g] = cv(96 * dpr, 96 * dpr);
  g.scale(dpr, dpr);
  draw(g);
  return c;
}
function runDoll(): void {
  loadSample();
  const rg = RGU();
  let t1 = 0;
  for (const [v, west, vk] of VIEWS)
    for (const [pk, pose] of poses(v))
      for (const dpr of [1, 2, 3]) {
        const a = dollCanvas((g) => rg.withShield(proxySect(), v, () => qStamp(g, proxySect(), v, 48, 78, 1, west, GAME_HOOKS, pose, { dpr })), dpr);
        const b = dollCanvas((g) => qStamp(g, gameSect(), v, 48, 78, 1, west, GAME_HOOKS, pose, { dpr }), dpr);
        const n = diffPx(a, b);
        t1 += n;
        log(`doll① proxy-vs-branch ${vk}/${pk} dpr${dpr} diff=${n}`);
      }
  log(`DOLL① TOTAL diff=${t1}`);
  // ② 樣張 QDoll vs 遊戲端 qStamp（同一套樣張顏色 SAMPLE_HOOKS）
  const sampleSect = rg.sectShieldDisciple("A");
  const towerU = { look: { ...sampleSect.look }, gear: { ...sampleSect.gear, off_hand: { kind: "shield_kite", form: "tower", material: "wood", color: "#6a4a2e" } } };
  const swordU = { look: { ...sampleSect.look }, gear: { body: sampleSect.gear["body"], main_hand: sampleSect.gear["main_hand"] } };
  const gameOf = (u: { look: Record<string, unknown>; gear: Record<string, unknown> }, off: QItem | null): QUnit => {
    const gear = { ...(u.gear as QUnit["gear"]) };
    if (off) gear.off_hand = off;
    return { look: u.look as unknown as QUnit["look"], gear };
  };
  const pairs: ReadonlyArray<readonly [string, unknown, QUnit]> = [
    ["持盾弟子（碑盾）", sampleSect, gameOf(sampleSect, SECT_SHIELD)],
    ["塔盾（基準）", towerU, gameOf(towerU, null)],
    ["持劍弟子（基準）", swordU, gameOf(swordU, null)],
  ];
  // 「多出來的差異」：持盾弟子那一對的差異像素中，不在持劍弟子（同一個頭、身、劍，沒有盾）那一對差異裡的（＝盾造成的差異）
  const mask = (a: HTMLCanvasElement, b: HTMLCanvasElement): Uint8Array => {
    const A = a.getContext("2d")!.getImageData(0, 0, a.width, a.height).data;
    const B = b.getContext("2d")!.getImageData(0, 0, b.width, b.height).data;
    const m = new Uint8Array(A.length / 4);
    for (let i = 0; i < m.length; i++) m[i] = A[i * 4] !== B[i * 4] || A[i * 4 + 1] !== B[i * 4 + 1] || A[i * 4 + 2] !== B[i * 4 + 2] || A[i * 4 + 3] !== B[i * 4 + 3] ? 1 : 0;
    return m;
  };
  for (const [v, west, vk] of VIEWS)
    for (const dpr of [1, 2]) {
      const masks = pairs.map(([, su, gu]) =>
        mask(
          dollCanvas((g) => rg.stampDoll(g, su, v, 48, 78, 1, west, { dpr }), dpr),
          dollCanvas((g) => qStamp(g, gu, v, 48, 78, 1, west, SAMPLE_HOOKS, null, { dpr }), dpr),
        ),
      );
      const base = masks[2]!;
      pairs.forEach(([zh], i) => {
        const m = masks[i]!;
        let n = 0;
        let extra = 0;
        for (let j = 0; j < m.length; j++) {
          n += m[j]!;
          if (m[j] && !base[j]) extra++;
        }
        log(`doll② sample-QDoll-vs-game ${zh} ${vk} dpr${dpr} diff=${n} extra-vs-sword-baseline=${extra}`);
      });
    }
}

// ---------- 看圖 ----------
function show(): void {
  loadSample();
  const sec = (title: string): HTMLDivElement => {
    const h = document.createElement("h2");
    h.textContent = title;
    document.body.appendChild(h);
    const row = document.createElement("div");
    row.className = "row";
    document.body.appendChild(row);
    return row;
  };
  const put = (row: HTMLElement, c: HTMLCanvasElement, cap: string, z = 1): void => {
    const d = document.createElement("div");
    d.className = "cell";
    c.style.width = `${c.width * z}px`;
    c.style.height = `${c.height * z}px`;
    d.appendChild(c);
    const t = document.createElement("div");
    t.textContent = cap;
    d.appendChild(t);
    row.appendChild(d);
  };
  const r1 = sec("盾（×4、DPR 2）：樣張 vs 遊戲端");
  for (const view of ["front", "side", "back"] as const) {
    const [a, b] = shieldPair(view, 4, 2, 22, 22);
    put(r1, a, `樣張 ${view}`, 0.5);
    put(r1, b, `遊戲 ${view} diff=${diffPx(a, b)}`, 0.5);
  }
  const r2 = sec("持盾弟子：樣張 QDoll（上）vs 遊戲端（下），×3");
  const su = RGU().sectShieldDisciple("A");
  for (const [v, west, vk] of VIEWS) put(r2, dollCanvas((g) => RGU().stampDoll(g, su, v, 48, 78, 1, west, { dpr: 3 }), 3), `樣張 ${vk}`);
  const r3 = sec("");
  for (const [v, west, vk] of VIEWS) put(r3, dollCanvas((g) => qStamp(g, { look: su.look as unknown as QUnit["look"], gear: { ...(su.gear as QUnit["gear"]), off_hand: SECT_SHIELD } }, v, 48, 78, 1, west, SAMPLE_HOOKS, null, { dpr: 3 }), 3), `遊戲 ${vk}`);
  const r4 = sec("遊戲端（GAME_HOOKS）持盾弟子 × 待機");
  for (const [v, west, vk] of VIEWS)
    for (const [pk, pose] of poses(v).slice(0, 3)) put(r4, dollCanvas((g) => qStamp(g, gameSect(), v, 48, 78, 1, west, GAME_HOOKS, pose, { dpr: 2 }), 2), `${vk} ${pk}`);
}

try {
  if (MODE === "fp") runHash();
  else if (MODE === "shield") runShield();
  else if (MODE === "doll") runDoll();
  else show();
} catch (e) {
  log(`ERROR ${(e as Error).stack ?? String(e)}`);
}
out.textContent = lines.join("\n");
document.body.appendChild(out);
document.body.dataset["done"] = "1";
