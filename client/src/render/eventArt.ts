// 事件卡插圖（Phase 6C-ART2；移植自 docs/art/sample/events.js，需求 docs/art/事件插圖.md 第 1～3 節、
// docs/art/Phase6剩餘美術移植需求.md 第 3 節）。和實地地圖同一套畫法：7×3 格的小場景（364×156）、格子地面、
// C 畫風紙娃娃、地物；四周暗角、金邊，左上角一個事件類型的小牌（圖示＋兩三個字）。
// 背景依區域換：荒原用焦土、熔岩、枯木，其他區用雲嶺的草地、竹林、石板；事件內容不變，敵人材質跟著區域。
// 確定性：沒有亂數，每種場景固定擺法；離屏畫好依（場景、背景、解析度）快取成圖片網址。
import type { WorldEventView } from "../api/types";
import type { DollSpec } from "./appearance";
import { type Ctx } from "./artDraw";
import {
  altar,
  ashObj,
  ashTile,
  bambooGrove,
  boulder,
  bubble,
  cart,
  chest,
  campfire,
  deadGrove,
  enemyRing,
  flowers,
  glow,
  ground,
  hornAltar,
  ICON,
  type IconId,
  mistWisp,
  OUT,
  pine,
  stele,
  stoneLantern,
  T,
} from "./eventArtParts";
import { drawCreature, resolveCreature } from "./inkCreature";
import { drawFigure } from "./paperdoll";
import { solutionIcon, type SolutionIcon } from "../world/narration";

export const COLS = 7;
export const ROWS = 3;
/** 插圖的虛擬大小（事件卡上照卡寬等比縮放）。 */
export const EVENT_ART_W = COLS * T;
export const EVENT_ART_H = ROWS * T;

export type EventArtId = "ambush" | "chest" | "stele" | "altar" | "villager" | "caravan" | "trap" | "camp" | "anomaly" | "friend";
export type EventArtBg = "cloud" | "ashen";

/** 已知的場景 ID（順序同樣張；伺服器 `EVENT_ART_IDS` 同一份）。 */
export const EVENT_ART_IDS: readonly EventArtId[] = ["ambush", "chest", "stele", "altar", "villager", "caravan", "trap", "camp", "anomaly", "friend"];

/** 不認得的 `art` 退回古碑。 */
export const FALLBACK_ART: EventArtId = "stele";

/** 沒寫 `art` 時：第一個不是放棄的選項的圖示 → 場景（需求第 3 節第 4 點）。 */
export const ICON_ART: Readonly<Record<SolutionIcon, EventArtId>> = {
  combat: "ambush",
  persuade: "villager",
  sneak: "ambush",
  investigate: "stele",
  force: "trap",
  chance: "altar",
  trade: "caravan",
  leave: "camp",
};

const isArt = (v: string): v is EventArtId => (EVENT_ART_IDS as readonly string[]).includes(v);

/** 事件要畫哪個場景：有 `art` 用它（不認得退回古碑），沒有照第一個不是放棄的選項的圖示挑。 */
export function eventArtScene(event: Pick<WorldEventView, "art" | "solutions">): EventArtId {
  const art = event.art ?? null;
  if (art !== null) return isArt(art) ? art : FALLBACK_ART;
  const lead = event.solutions.find((s) => s.kind !== "abandon") ?? event.solutions[0];
  return lead !== undefined ? ICON_ART[solutionIcon(lead)] : FALLBACK_ART;
}

/** 背景依區域：灰燼荒原用荒原背景，其他區（含沒有區域）用雲嶺背景。 */
export const eventArtBg = (region: string | null | undefined): EventArtBg => (region === "ashen_waste" ? "ashen" : "cloud");

// ---------------- 人物 ----------------

const HERO: DollSpec = {
  look: { skin: "#f1c9a5", hair: "short", hairColor: "#3a2414" },
  gear: { body: { kind: "leather", color: "#2f5a5a" }, feet: { kind: "boots", material: "leather" }, main_hand: { kind: "sword", material: "steel" } },
};
const BANDIT: DollSpec = {
  look: { skin: "#a8724c", hair: "short", hairColor: "#1a1a1a" },
  gear: { body: { kind: "leather", color: "#7a6a4a" }, feet: { kind: "boots", material: "leather" }, main_hand: { kind: "axe", material: "iron" }, head: { kind: "hood", color: "#6a5a3a" } },
};
const VILLAGER: DollSpec = {
  look: { skin: "#e8b890", hair: "bun", hairColor: "#3a2414", bunBand: "#b8432f" },
  gear: { body: { kind: "robe", color: "#8a6a3a" }, feet: { kind: "shoes", color: "#3a2a1a" } },
};
const MERCHANT: DollSpec = { look: { skin: "#f1c9a5", hair: "short", hairColor: "#2a1a10" }, gear: { body: { kind: "robe", color: "#3a5ad0", trim: "#e8bb48" } } };

/** 紙娃娃（腳底在 (x, y)）：`front` 正面、`side` 側面；`west` 朝左。 */
function person(ctx: Ctx, x: number, y: number, who: DollSpec, view: "front" | "side", west = false, k = 1.1): void {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(west ? -k : k, k);
  drawFigure(ctx, who, view === "front" ? "south" : "east");
  ctx.restore();
}

/** 異形犬（霧狼／灰燼犬）：腳下紅環＋本體（朝左）。 */
function hound(ctx: Ctx, x: number, y: number, bg: EventArtBg): void {
  const r = resolveCreature({ look: { body: "hound", material: bg === "ashen" ? "magma" : "fur", tint: "#c8ccd0" } });
  ctx.save();
  ctx.translate(x, y);
  enemyRing(ctx, 13);
  ctx.scale(-1, 1);
  drawCreature(ctx, r);
  ctx.restore();
}

// ---------------- 十種場景 ----------------

interface Scene {
  zh: string;
  icon: IconId;
  draw(ctx: Ctx, bg: EventArtBg): void;
}

function drawTrap(ctx: Ctx): void {
  const cx = 3.5 * T;
  const cy = 1.9 * T;
  ctx.save();
  ctx.strokeStyle = OUT;
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.ellipse(cx, cy, 20, 11, 0, 0, Math.PI * 2);
  ctx.stroke();
  ctx.strokeStyle = "#9aa0a8";
  ctx.lineWidth = 2.4;
  ctx.stroke();
  ctx.fillStyle = "#c8ccd0";
  for (let k = 0; k < 10; k++) {
    const a = (k / 10) * Math.PI * 2;
    ctx.beginPath();
    ctx.moveTo(cx + Math.cos(a) * 20 - 2, cy + Math.sin(a) * 11);
    ctx.lineTo(cx + Math.cos(a) * 13, cy + Math.sin(a) * 6);
    ctx.lineTo(cx + Math.cos(a) * 20 + 2, cy + Math.sin(a) * 11);
    ctx.fill();
  }
  ctx.restore();
  ashObj(ctx, "grass", 2.9 * T, 1.3 * T);
  ctx.save();
  ctx.strokeStyle = "rgba(255,255,255,0.95)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(cx + 14, cy - 12);
  ctx.lineTo(cx + 22, cy - 20);
  ctx.moveTo(cx + 18, cy - 10);
  ctx.lineTo(cx + 26, cy - 12);
  ctx.stroke();
  ctx.restore();
  person(ctx, 1.4 * T, 2.85 * T, HERO, "side");
}

function drawAnomaly(ctx: Ctx): void {
  const cx = 3.5 * T;
  const cy = 1.6 * T;
  glow(ctx, cx, cy, 90, "rgba(160,120,255,0.9)", 0.6);
  ctx.save();
  ctx.shadowColor = "#c8a0ff";
  ctx.shadowBlur = 14;
  ctx.strokeStyle = "#e8d8ff";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(cx - 60, cy + 10);
  ctx.lineTo(cx - 20, cy - 4);
  ctx.lineTo(cx, cy + 12);
  ctx.lineTo(cx + 26, cy - 8);
  ctx.lineTo(cx + 64, cy + 6);
  ctx.stroke();
  ctx.restore();
  for (const [dx, h] of [[-30, 26], [8, 34], [40, 22]] as const) {
    ctx.beginPath();
    ctx.moveTo(cx + dx - 6, cy + 8);
    ctx.lineTo(cx + dx, cy + 8 - h);
    ctx.lineTo(cx + dx + 6, cy + 8);
    ctx.closePath();
    ctx.fillStyle = "#c8bcff";
    ctx.fill();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = OUT;
    ctx.stroke();
  }
}

function drawStele(ctx: Ctx): void {
  stele(ctx, 3, 0.8);
  ctx.save();
  ctx.shadowColor = "#8fe0ff";
  ctx.shadowBlur = 8;
  ctx.strokeStyle = "#8fe0ff";
  ctx.lineWidth = 1.4;
  for (const y of [1.15, 1.3, 1.45]) {
    ctx.beginPath();
    ctx.moveTo(3.4 * T, y * T);
    ctx.lineTo(3.6 * T, y * T);
    ctx.stroke();
  }
  ctx.restore();
  mistWisp(ctx, 1.5 * T, 1.2 * T, 300);
  mistWisp(ctx, 4.2 * T, 1.4 * T, 900);
  person(ctx, 1.8 * T, 2.9 * T, HERO, "side");
}

function drawFriend(ctx: Ctx): void {
  ctx.fillStyle = "rgba(255,255,255,0.85)";
  for (let k = 0; k < 7; k++) {
    const x = 0.6 * T + k * 0.55 * T;
    const y = 2.2 * T - k * 6 + (k % 2) * 8;
    ctx.beginPath();
    ctx.ellipse(x, y, 4, 6, 0.4, 0, Math.PI * 2);
    ctx.fill();
  }
  stele(ctx, 4.6, 0.7);
  bubble(ctx, 5.1 * T, 0.9 * T, "scroll", "info");
}

/** 十種場景（需求第 3 節第 2 點）：小牌文字、小牌圖示、畫法。 */
export const SCENES: Readonly<Record<EventArtId, Scene>> = {
  ambush: {
    zh: "遭遇・伏擊",
    icon: "sword",
    draw(ctx, bg) {
      if (bg === "ashen") deadGrove(ctx, 0, 0, 2, 1);
      else {
        bambooGrove(ctx, 0, 0, 2, 1);
        bambooGrove(ctx, 5 * T, 0, 2, 1);
      }
      person(ctx, 1.6 * T, 2.85 * T, HERO, "side");
      person(ctx, 4.6 * T, 2.6 * T, BANDIT, "side", true);
      person(ctx, 5.6 * T, 2.2 * T, BANDIT, "side", true);
      hound(ctx, 3.8 * T, 2.9 * T, bg);
      bubble(ctx, 4.6 * T, 1.15 * T, "bang", "danger");
    },
  },
  chest: {
    zh: "寶箱",
    icon: "coin",
    draw(ctx, bg) {
      chest(ctx, 3, 1);
      glow(ctx, 3.5 * T, 1.55 * T, 60, "rgba(255,230,140,0.9)", 0.45);
      if (bg === "ashen") ashObj(ctx, "dead_tree", 0.4 * T, 0);
      else {
        pine(ctx, 0.4 * T, 0);
        flowers(ctx, 4.5 * T, 1.5 * T, 4, 1);
      }
      boulder(ctx, 5.2 * T, 1.2 * T);
    },
  },
  stele: { zh: "古碑", icon: "ask", draw: drawStele },
  altar: {
    zh: "祭壇・機遇",
    icon: "rest",
    draw(ctx, bg) {
      for (let gx = 2; gx < 5; gx++) ground(ctx, "s", gx, 1);
      if (bg === "ashen") hornAltar(ctx, 3 * T, 0.6 * T);
      else altar(ctx, 3 * T, 0.6 * T);
      glow(ctx, 3.5 * T, 1.2 * T, 70, bg === "ashen" ? "rgba(255,90,60,0.9)" : "rgba(255,220,140,0.9)", 0.35);
      stoneLantern(ctx, 1.6 * T, 0.6 * T);
      stoneLantern(ctx, 4.4 * T, 0.6 * T);
    },
  },
  villager: {
    zh: "村民求助",
    icon: "bang",
    draw(ctx) {
      cart(ctx, 3.6 * T, 1.3 * T);
      ground(ctx, "p", 3, 2);
      ashObj(ctx, "crate", 4.6 * T, 1.9 * T);
      person(ctx, 2.4 * T, 2.8 * T, VILLAGER, "front");
      bubble(ctx, 2.4 * T, 1.55 * T, "bang", "quest");
    },
  },
  caravan: {
    zh: "商隊",
    icon: "coin",
    draw(ctx) {
      cart(ctx, 2.2 * T, 1.2 * T);
      cart(ctx, 3.4 * T, 1.3 * T);
      ashObj(ctx, "crate", 4.6 * T, 1.7 * T);
      person(ctx, 5.4 * T, 2.85 * T, MERCHANT, "side", true);
      bubble(ctx, 5.4 * T, 1.6 * T, "coin", "talk");
      campfire(ctx, 0.8, 1.5);
    },
  },
  trap: { zh: "陷阱", icon: "warn", draw: drawTrap },
  camp: {
    zh: "營火休息",
    icon: "rest",
    draw(ctx) {
      campfire(ctx, 3, 1);
      glow(ctx, 3.5 * T, 1.6 * T, 90, "rgba(255,170,80,0.9)", 0.35);
      person(ctx, 2.3 * T, 2.6 * T, HERO, "side", false, 1);
      person(ctx, 4.7 * T, 2.6 * T, VILLAGER, "side", true, 1);
      ctx.fillStyle = "rgba(20,24,40,0.35)";
      ctx.fillRect(0, 0, EVENT_ART_W, EVENT_ART_H);
    },
  },
  anomaly: { zh: "異象・源晶裂痕", icon: "portal", draw: drawAnomaly },
  friend: { zh: "朋友的足跡", icon: "notes", draw: drawFriend },
};

/** 7×3 格的地面：雲嶺草地＋中間一段黃土路；荒原焦土＋右上角熔岩。 */
function drawGround(ctx: Ctx, bg: EventArtBg): void {
  for (let gy = 0; gy < ROWS; gy++) {
    for (let gx = 0; gx < COLS; gx++) {
      if (bg === "ashen") ashTile(ctx, gy === 0 && gx > 4 ? "lava" : "stone", gx, gy);
      else ground(ctx, gy === 1 && gx > 1 && gx < 5 ? "p" : "g", gx, gy);
    }
  }
}

const BADGE_FONT = "bold 13px 'Noto Sans TC', 'Microsoft JhengHei', sans-serif";

/** 畫一張事件插圖（左上角在原點、大小 EVENT_ART_W×EVENT_ART_H）。 */
export function drawEventArt(ctx: Ctx, scene: EventArtId, bg: EventArtBg): void {
  const s = SCENES[scene];
  const W = EVENT_ART_W;
  const H = EVENT_ART_H;
  ctx.save();
  ctx.beginPath();
  ctx.roundRect(0, 0, W, H, 12);
  ctx.clip();
  drawGround(ctx, bg);
  s.draw(ctx, bg);
  const v = ctx.createRadialGradient(W / 2, H / 2, H * 0.4, W / 2, H / 2, W * 0.62);
  v.addColorStop(0, "rgba(0,0,0,0)");
  v.addColorStop(1, "rgba(10,8,6,0.65)");
  ctx.fillStyle = v;
  ctx.fillRect(0, 0, W, H);
  ctx.restore();
  ctx.lineWidth = 2;
  ctx.strokeStyle = "#c8a868";
  ctx.beginPath();
  ctx.roundRect(1, 1, W - 2, H - 2, 12);
  ctx.stroke();
  ctx.font = BADGE_FONT;
  const measured = ctx.measureText(s.zh) as TextMetrics | undefined;
  const tw = (measured?.width ?? s.zh.length * 13) + 34;
  ctx.fillStyle = "rgba(24,20,16,0.85)";
  ctx.beginPath();
  ctx.roundRect(8, 8, tw, 24, 12);
  ctx.fill();
  ctx.strokeStyle = "#c8a868";
  ctx.lineWidth = 1.2;
  ctx.stroke();
  ICON[s.icon](ctx, 21, 20, 13);
  ctx.fillStyle = "#f2e6c8";
  ctx.textBaseline = "middle";
  ctx.fillText(s.zh, 32, 21);
}

const cache = new Map<string, string>();

/** 快取鍵（場景、背景、解析度）。 */
export const eventArtKey = (scene: EventArtId, bg: EventArtBg, dpr: number): string => `${scene}|${bg}|${dpr}`;

/** 事件插圖的圖片網址（離屏畫好快取；沒有 DOM 時為 `null`）。 */
export function eventArtUrl(scene: EventArtId, bg: EventArtBg, dpr = 2): string | null {
  if (typeof document === "undefined") return null;
  const key = eventArtKey(scene, bg, dpr);
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  const c = document.createElement("canvas");
  c.width = EVENT_ART_W * dpr;
  c.height = EVENT_ART_H * dpr;
  const ctx = c.getContext("2d");
  if (ctx === null) return null;
  ctx.scale(dpr, dpr);
  drawEventArt(ctx, scene, bg);
  const url = c.toDataURL("image/png");
  cache.set(key, url);
  return url;
}

/** 快取裡的張數（測試用）。 */
export const eventArtCacheSize = (): number => cache.size;
