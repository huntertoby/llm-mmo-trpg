// 開發用：骨架移動片段在戰場上的樣子（Phase 6M-3）。開 `client/walk-gallery.html`（pnpm dev 後 /walk-gallery.html）。
// 不屬於正式 build；供美術 PM 驗收、截圖與量 FPS。同一張 12×12 戰場：中間一排高度 0→0→1→2→2→0→0（樣張第 2 區）、右邊一塊兩級高台。
// `#walk`：主角在平地走（每格 2.4 秒，放慢看步伐）；`#jump`：走上一級、跳上兩級高台、跳下來；`#prone`：倒地狀態持續躺著＋滑倒倒下；
// `#run`：衝刺後跑步；`#perf`：正常速度（每格 120ms）讓 4 個單位連續走 6 秒，和靜止 3 秒比 FPS，並記下貼圖快取數量。
// `window.__walkStart`：動畫開始的時間（performance.now），截圖腳本用它等到指定的時刻。
import type { BattleView, Facing, Glossary, Pos, TileView, UnitView } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { buildDrawModel } from "../battle/drawModel";
import { setGlossary } from "../battle/glossary";
import { tile, unit } from "../battle/testFixtures";
import { BEAT_HOLD_MS, BEAT_FX_MS, facingOf, TILE_STEP_MS, type Gait, type WalkAnim, type WalkPiece } from "../battle/walkAnim";
import { BattleRenderer } from "../render/BattleRenderer";

setGlossary(glossary as unknown as Glossary);

const MODE = decodeURIComponent(location.hash.slice(1)) || "walk";
const N = 12;
const HERO = "unit_0001";
const ROW = 5;
/** 格子像素（`?cell=88` 放大截圖用）。 */
const CELL = Number(new URLSearchParams(location.search).get("cell") ?? "52") || 52;
/** 中間一排（第 5 排）的高度：樣張 heightRow 的 0→0→1→2→2→0→0，往右再接一塊兩級高台。 */
const ROW_H = [0, 0, 1, 2, 2, 0, 0, 0, 2, 2, 2, 0];

declare global {
  interface Window {
    __walkStart?: number;
    __walkDone?: boolean;
  }
}

function grid(): TileView[] {
  const tiles: TileView[] = [];
  for (let y = 0; y < N; y++) {
    for (let x = 0; x < N; x++) {
      let h = 0;
      if (y === ROW) h = ROW_H[x] ?? 0;
      else if (y === ROW - 1 && x >= 8 && x <= 10) h = 2; // 高台往北多一排
      else if (y >= 9 && x <= 2) h = 1;
      tiles.push(tile(x, y, { height: h, terrain: (x + y) % 7 === 0 ? "dirt" : "stone" } as Partial<TileView>));
    }
  }
  return tiles;
}

const prone = [{ status_id: "prone", remaining: 1, source_id: null, amount: null, charge_tiles: [], cost_status: false }] as unknown as UnitView["statuses"];

function scene(): BattleView {
  const units: UnitView[] = [
    unit(HERO, "ally", 0, ROW, { template_id: "hero_fighter", name_zh: "戰士", facing: "east", weapon_id: "one_handed_sword" }),
    unit("unit_0002", "ally", 1, 2, { template_id: "hero_archer", name_zh: "弓手", facing: "east" }),
    unit("unit_0003", "ally", 2, 8, { template_id: "hero_mage", name_zh: "法師", facing: "east" }),
    unit("unit_0004", "enemy", 10, 2, { template_id: "t", name_zh: "盜賊", facing: "west" }),
    unit("unit_0005", "enemy", 9, 8, { template_id: "t", name_zh: "盜賊", facing: "west", statuses: prone }),
    unit("unit_0006", "enemy", 6, 10, { template_id: "t", name_zh: "霧狼", facing: "west", doll_look: { creature: { body: "hound", material: "fur" } } as unknown as UnitView["doll_look"] }),
    unit("unit_0007", "ally", 4, 9, { template_id: "hero_fighter", name_zh: "倒地的騎士", facing: "east", statuses: prone }),
    unit("unit_0008", "enemy", 7, 1, { template_id: "t", name_zh: "盜賊", facing: "south" }),
  ];
  return {
    team: "ally", map_id: "walk_gallery", map_name_zh: "移動片段", width: N, height: N, tiles: grid(), objects: [], units, traps: [],
    turn_order: [HERO], active_unit: HERO, round: 1, max_rounds: 30, weather_id: null, weather_name_zh: null,
    objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null,
    source_wells: [], zones: [], runes: [],
  } as unknown as BattleView;
}

function legs(unitId: string, path: Pos[], ms: number, gait?: Gait): WalkAnim {
  const pieces: WalkPiece[] = [];
  let facing: Facing = "east";
  for (let i = 1; i < path.length; i++) {
    facing = facingOf(path[i - 1]!, path[i]!, facing);
    pieces.push({ kind: "leg", from: path[i - 1]!, to: path[i]!, facing, durationMs: ms });
  }
  return { unitId, pieces, ...(gait === undefined ? {} : { gait }) };
}

const row = (from: number, to: number, y = ROW): Pos[] => Array.from({ length: Math.abs(to - from) + 1 }, (_, i) => ({ x: from + (to > from ? i : -i), y }));

async function show(): Promise<{ r: BattleRenderer; v: BattleView }> {
  const box = document.createElement("div");
  box.className = "scene";
  document.body.appendChild(box);
  const r = new BattleRenderer();
  await r.init(box);
  r.setScale(CELL / 48);
  const v = scene();
  r.draw(buildDrawModel(v, HERO));
  return { r, v };
}

function caption(text: string): void {
  const h = document.createElement("h2");
  h.textContent = text;
  document.body.prepend(h);
}

const never = () => false;

async function perf(r: BattleRenderer): Promise<void> {
  const out = document.createElement("div");
  out.id = "perf";
  document.body.appendChild(out);
  /** 量 `ms` 毫秒內的 FPS、第 95 百分位的幀時間、超過 50ms 的幀數。 */
  const count = (ms: number) =>
    new Promise<{ fps: number; p95Ms: number; over50: number }>((resolve) => {
      const gaps: number[] = [];
      let last = performance.now();
      const t0 = last;
      const tick = (now: number) => {
        gaps.push(now - last);
        last = now;
        if (now - t0 < ms) {
          requestAnimationFrame(tick);
          return;
        }
        const sorted = [...gaps].sort((x, y) => x - y);
        const p95 = sorted[Math.floor(sorted.length * 0.95)] ?? 0;
        resolve({ fps: Number(((gaps.length * 1000) / (now - t0)).toFixed(1)), p95Ms: Number(p95.toFixed(1)), over50: gaps.filter((g) => g > 50).length });
      };
      requestAnimationFrame(tick);
    });
  await count(1000); // 暖身（第一次繪製的卡頓不算）
  const idle = await count(3000);
  let walking = true;
  // 來回走、不重畫場景（重畫是播放流程的事，這裡只量走路動畫本身）
  const loop = async (unitId: string, path: Pos[], gait?: Gait) => {
    let way = path;
    while (walking) {
      await r.animateWalk(legs(unitId, way, TILE_STEP_MS, gait), never);
      way = [...way].reverse();
    }
  };
  // 四個單位同時一直走（正常速度每格 120ms）：平地與上下一級、跳上跳下兩級、跑步、異形
  void loop(HERO, row(0, 11));
  void loop("unit_0002", row(1, 10, 2), "run");
  void loop("unit_0003", row(2, 11, 8));
  void loop("unit_0006", row(6, 0, 10));
  const moving = await count(6000);
  walking = false;
  const size = (r as unknown as { art: { size: number } }).art.size;
  out.textContent = JSON.stringify({ grid: `${N}x${N}`, cell: CELL, dpr: window.devicePixelRatio, idle, walking4: moving, cacheSize: size });
}

/**
 * 6M-4：待機的效能（`#idle`）：8 個人站著 20 秒（呼吸＋小動作），和關掉待機時比 FPS；
 * 記下貼圖快取數量（開始、待機 20 秒後、重畫一次後）。
 */
async function idlePerf(r: BattleRenderer, v: BattleView): Promise<void> {
  const out = document.createElement("div");
  out.id = "perf";
  document.body.appendChild(out);
  const fps = (ms: number) =>
    new Promise<{ fps: number; p95Ms: number }>((resolve) => {
      const gaps: number[] = [];
      let last = performance.now();
      const t0 = last;
      const tick = (now: number) => {
        gaps.push(now - last);
        last = now;
        if (now - t0 < ms) {
          requestAnimationFrame(tick);
          return;
        }
        const sorted = [...gaps].sort((x, y) => x - y);
        resolve({ fps: Number(((gaps.length * 1000) / (now - t0)).toFixed(1)), p95Ms: Number((sorted[Math.floor(sorted.length * 0.95)] ?? 0).toFixed(1)) });
      };
      requestAnimationFrame(tick);
    });
  r.setIdle(false);
  await fps(1000);
  const off = await fps(4000);
  const before = r.textureCount();
  r.setIdle(true);
  const on = await fps(20000);
  const after = r.textureCount();
  r.draw(buildDrawModel(v, HERO));
  const redrawn = r.textureCount();
  out.textContent = JSON.stringify({ grid: `${N}x${N}`, cell: CELL, units: v.units.length, idleOff: off, idleOn20s: on, textures: { before, after20s: after, afterRedraw: redrawn } });
}

async function main(): Promise<void> {
  const { r, v } = await show();
  if (MODE === "idle") {
    caption("6M-4・待機（8 人站著 20 秒）FPS 與貼圖數");
    await idlePerf(r, v);
    window.__walkDone = true;
    return;
  }
  r.setIdle(false); // 6M-3 的截圖與量測照舊不含待機
  const start = () => {
    window.__walkStart = performance.now();
  };
  switch (MODE) {
    case "perf":
      caption("6M-3・12×12 戰場 FPS（靜止 3 秒 vs. 4 人連續走 6 秒）");
      await perf(r);
      return;
    case "jump":
      caption("6M-3・高低差：平地走到兩級高台前，跳上去（每格 1.6 秒）");
      start();
      await r.animateWalk(legs(HERO, row(5, 9), 1600), never);
      break;
    case "run":
      caption("6M-3・衝刺後跑步（每格 2.4 秒）");
      start();
      await r.animateWalk(legs("unit_0002", row(1, 10, 2), 2400, "run"), never);
      break;
    case "prone": {
      caption("6M-3・倒地狀態持續躺著（騎士、盜賊）＋走兩格在冰上滑倒");
      const walk = legs("unit_0003", row(2, 4, 8), 1400);
      walk.pieces.push({ kind: "beat", beat: "slip", pos: { x: 4, y: 8 }, holdMs: BEAT_HOLD_MS.slip * 4, fxMs: BEAT_FX_MS.slip * 4, feedback: [], feedbackMs: 0 });
      start();
      await r.animateWalk(walk, never);
      break;
    }
    default:
      caption("6M-3・走路（平地，每格 2.4 秒）");
      start();
      await r.animateWalk(legs("unit_0003", row(2, 11, 8), 2400), never);
  }
  window.__walkDone = true;
}

void main();
