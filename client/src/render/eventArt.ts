// 事件卡插圖（Phase 6C-ART2；移植自 docs/art/sample/events.js，需求 docs/art/事件插圖.md 第 1～3 節、
// docs/archive/art/Phase6剩餘美術移植需求.md 第 3 節）。和實地地圖同一套畫法：7×3 格的小場景（364×156）、格子地面、
// C 畫風紙娃娃、地物；四周暗角、金邊，左上角一個事件類型的小牌（圖示＋兩三個字）。
// 背景依區域換：荒原用焦土、熔岩、枯木；主城（RT-2）用主城實地圖的白石板、源晶燈、遠處藍頂白牆（沒有竹林、草地）；
// 雲嶺和其他區用雲嶺的草地、竹林、石板；事件內容不變，敵人材質跟著區域。荒原祭壇的燈是角魔火盆（RT-2）。
// 確定性：沒有亂數，每種場景固定擺法；離屏畫好依（場景、背景、解析度）快取成圖片網址。
import type { WorldEventView } from "../api/types";
import type { DollSpec } from "./appearance";
import { type Ctx } from "./artDraw";
import {
  altar,
  obsidianSlab,
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
  hornBrazier,
  drawBadgeIcon,
  type BadgeIconId,
  mistWisp,
  OUT,
  pine,
  stele,
  stoneLantern,
  T,
} from "./eventArtParts";
import { capitalBackdrop, capitalTile } from "./eventArtCapital";
import { AWAKEN_W as AWAKEN_W_PX } from "./eventArtAwaken";
import { drawCreature, resolveCreature } from "./inkCreature";
import { drawFigure } from "./paperdoll";
import { solutionIcon, type SolutionIcon } from "../world/narration";

export const COLS = 7;
export const ROWS = 3;
/** 插圖的虛擬大小（事件卡上照卡寬等比縮放）。 */
export const EVENT_ART_W = COLS * T;
export const EVENT_ART_H = ROWS * T;

export type EventArtId = "ambush" | "chest" | "stele" | "altar" | "villager" | "caravan" | "trap" | "camp" | "anomaly" | "friend";
export type EventArtBg = "cloud" | "ashen" | "capital";

/** 三種背景（測試、開發頁用）。 */
export const EVENT_ART_BGS: readonly EventArtBg[] = ["cloud", "ashen", "capital"];

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

/** 拿不到區域時（沒有、空字串、`hub`）當作主城（RT-2；同 RT-1 的 `hub` 主題，碎界中樞）。 */
const HUB_REGIONS: ReadonlySet<string> = new Set(["", "hub", "capital"]);

/**
 * 背景依區域（RT-2）：灰燼荒原用荒原背景；主城（含 `hub`、沒有區域）用主城背景；雲嶺和其他區用雲嶺背景
 * （之後三區開放時各補一種）。
 */
export function eventArtBg(region: string | null | undefined): EventArtBg {
  if (region == null || HUB_REGIONS.has(region)) return "capital";
  return region === "ashen_waste" ? "ashen" : "cloud";
}

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
  icon: BadgeIconId;
  draw(ctx: Ctx, bg: EventArtBg): void;
}

function drawTrap(ctx: Ctx, bg: EventArtBg): void {
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
  if (bg !== "capital") ashObj(ctx, "grass", 2.9 * T, 1.3 * T);
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

function drawStele(ctx: Ctx, bg: EventArtBg): void {
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
  if (bg !== "capital") {
    mistWisp(ctx, 1.5 * T, 1.2 * T, 300);
    mistWisp(ctx, 4.2 * T, 1.4 * T, 900);
  }
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

/** 祭壇的光：荒原紅光、雲嶺暖黃光、主城紫晶光。 */
export const ALTAR_GLOW: Readonly<Record<EventArtBg, string>> = {
  cloud: "rgba(255,220,140,0.9)",
  ashen: "rgba(255,90,60,0.9)",
  capital: "rgba(170,150,255,0.9)",
};

/** 十種場景（需求第 3 節第 2 點）：小牌文字、小牌圖示、畫法。 */
export const SCENES: Readonly<Record<EventArtId, Scene>> = {
  ambush: {
    zh: "遭遇・伏擊",
    icon: "sword",
    draw(ctx, bg) {
      if (bg === "ashen") deadGrove(ctx, 0, 0, 2, 1);
      else if (bg === "cloud") {
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
      else if (bg === "cloud") {
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
      // 6V-3：荒原祭壇前改成黑曜岩石板加暗紅裂紋（青石是雲嶺的材質）
      if (bg === "ashen") for (let gx = 2; gx < 5; gx++) obsidianSlab(ctx, gx, 1);
      else if (bg !== "capital") for (let gx = 2; gx < 5; gx++) ground(ctx, "s", gx, 1);
      if (bg === "ashen") hornAltar(ctx, 3 * T, 0.6 * T);
      else altar(ctx, 3 * T, 0.6 * T);
      glow(ctx, 3.5 * T, 1.2 * T, 70, ALTAR_GLOW[bg], 0.35);
      // 兩側的燈：荒原是角魔火盆（RT-2），雲嶺保留石燈籠；主城已有背景的兩盞源晶燈，不另放
      if (bg === "ashen") {
        hornBrazier(ctx, 1.6 * T, 0.6 * T);
        hornBrazier(ctx, 4.4 * T, 0.6 * T);
      } else if (bg === "cloud") {
        stoneLantern(ctx, 1.6 * T, 0.6 * T);
        stoneLantern(ctx, 4.4 * T, 0.6 * T);
      }
    },
  },
  villager: {
    zh: "村民求助",
    icon: "bang",
    draw(ctx, bg) {
      cart(ctx, 3.6 * T, 1.3 * T);
      if (bg !== "capital") ground(ctx, "p", 3, 2);
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

/** 7×3 格的地面：雲嶺草地＋中間一段黃土路；荒原焦土＋右上角熔岩；主城白石板＋金色嵌線，再加遠處白牆與兩盞源晶燈。 */
function drawGround(ctx: Ctx, bg: EventArtBg): void {
  for (let gy = 0; gy < ROWS; gy++) {
    for (let gx = 0; gx < COLS; gx++) {
      if (bg === "ashen") ashTile(ctx, gy === 0 && gx > 4 ? "lava" : "stone", gx, gy);
      else if (bg === "capital") capitalTile(ctx, gx, gy);
      else ground(ctx, gy === 1 && gx > 1 && gx < 5 ? "p" : "g", gx, gy);
    }
  }
  if (bg === "capital") capitalBackdrop(ctx);
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
  drawBadgeIcon(ctx, s.icon, 21, 20); /* QI-6：Q 版小牌（中心 (21,20)、邊長 14） */
  ctx.fillStyle = "#f2e6c8";
  ctx.textBaseline = "middle";
  ctx.fillText(s.zh, 32, 21);
}

const cache = new Map<string, string>();

/** 快取鍵（場景、背景、解析度）。 */
export const eventArtKey = (scene: EventArtId, bg: EventArtBg, dpr: number): string => `${scene}|${bg}|${dpr}`;

/**
 * QI-6：插圖照卡寬縮放時，照「實際顯示的裝置像素」出圖（需求 3 第 7 點：小牌、泡泡的 Q 版圖樣用當下的變換算大小、貼整數裝置像素，
 * 不要畫好再被 CSS 縮放拉糊）。`cssWidth`＝插圖在畫面上的寬（`getBoundingClientRect`，含外層 CSS 縮放）、`devicePixelRatio`；
 * 回傳每個插圖單位幾個裝置像素（畫布寬 ＝ round(cssWidth × dpr)，剛好一個裝置像素對一個畫布像素）。量不到時 2（舊值）。
 */
export function eventArtScale(cssWidth: number, devicePixelRatio: number): number {
  return artScale(cssWidth, devicePixelRatio, EVENT_ART_W, 2);
}

/** 照顯示寬出圖的共用算法：畫布寬 ＝ round(cssWidth × dpr)，回傳每個插圖單位幾個裝置像素；量不到時 `fallback`。 */
function artScale(cssWidth: number, devicePixelRatio: number, artW: number, fallback: number): number {
  const w = Math.round(cssWidth * (devicePixelRatio > 0 ? devicePixelRatio : 1));
  return w > 0 ? w / artW : fallback;
}

/** 覺醒插圖量到之前的解析度（舊做法：裝置像素比最多 2，再 ×2 超取樣）。 */
export const awakenArtFallback = (devicePixelRatio: number): number => Math.min(2, devicePixelRatio > 0 ? devicePixelRatio : 1) * 2;

/**
 * PNL-4（QI-6 待決 2、QI-6 美術驗收可修 1）：覺醒插圖（`OpeningDialog` 的 `AwakenArt`）也照顯示寬出圖，做法同事件插圖的 `eventArtScale`：
 * 畫布寬 ＝ 顯示寬 × 裝置像素比，一個畫布像素對一個裝置像素，小牌的 Q 版圖樣（`ctxRes`）不再被 CSS 縮放取樣。量不到時退回舊的 ×4。
 */
export function awakenArtScale(cssWidth: number, devicePixelRatio: number): number {
  return artScale(cssWidth, devicePixelRatio, AWAKEN_W_PX, awakenArtFallback(devicePixelRatio));
}
/** 快取上限（照卡寬出圖後，視窗改大小會產生新的解析度；超過就丟最舊的）。 */
const CACHE_MAX = 48;

/** 事件插圖的圖片網址（離屏畫好快取；沒有 DOM 時為 `null`）。`dpr`＝每個插圖單位幾個裝置像素（QI-6 起可以是小數，畫布寬高四捨五入）。 */
export function eventArtUrl(scene: EventArtId, bg: EventArtBg, dpr = 2): string | null {
  if (typeof document === "undefined") return null;
  const key = eventArtKey(scene, bg, dpr);
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  if (cache.size >= CACHE_MAX) cache.delete(cache.keys().next().value as string);
  const c = document.createElement("canvas");
  c.width = Math.round(EVENT_ART_W * dpr);
  c.height = Math.round(EVENT_ART_H * dpr);
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

// RT-5：開場專用的第 11 種場景 `awaken`（主角是玩家自己的紙娃娃，所以不進 `EVENT_ART_IDS` 與快取；畫法在 eventArtAwaken.ts）。
export {
  AWAKEN_ART,
  AWAKEN_BANNERS,
  AWAKEN_COLS,
  AWAKEN_H,
  AWAKEN_HERO,
  AWAKEN_LIE_MS,
  AWAKEN_RING,
  AWAKEN_ROWS,
  AWAKEN_W,
  drawAwakenArt,
  type AwakenPose,
} from "./eventArtAwaken";
