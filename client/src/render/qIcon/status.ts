// qIconsStatus.js：「小圖示改 Q 版」全量重畫第 5 批——狀態圖示（畫圖 agent 2026-11-12）。
// 規則：docs/art/Q版小圖示樣張.md 第 2 節（尤其 6、8、11、13）；紀錄：docs/art/Q版小圖示-第5批狀態.md；樣張頁：q-icons-status.html。
// 範圍：content/statuses.yaml 的全部 118 個狀態（遊戲端靠名詞表 status_look 顯示，不寫死清單）。
//   ・第 4 批已畫的 32 個（qIconsParts.js 的 STATUS）直接呼叫，不重畫（src "b4:status.<id>"）；
//   ・和第 3、4 批別的部件同題材的，直接呼叫那一個（src "b3:…"／"b4:effect.…"）；
//   ・其餘新畫，畫法照第 4 批同一套（±10 單位、原點為中心；o.tiny＝圖樣本身 ≤14px：一個主體、不包外框）。
// 框不動（規則 13）：外框形狀與顏色照現行 client/src/render/statusIcon.ts 的 paintStatusIcon（buff 圓、debuff 圓角方、neutral 六角；框色依 polarity），
//   只換框裡的圖。現行靠「圖樣顏色」表示控制類別（硬控黃、移動藍、心智紫），Q 版每個圖樣自帶本色，所以類別色改畫在**框的底色**（CLASS_BG，美術 PM 定）。
// ---------------------------------------------------------------------------------------------
// Phase QI-3a：由 docs/art/sample/qIconsStatus.js（5b838d65 之後）逐行搬成 TypeScript（需求 docs/art/Q版小圖示-狀態移植需求.md 2.2、2.4、3.1、3.2；
// 規格 docs/phases/PhaseQI-3計畫.md A2、A3）。**3a 還沒接到遊戲畫面**（接線在 QI-3b：`statusIcon.ts` 的 `paintStatusIcon` 改呼叫這裡的 `paint`）。
// 和樣張不同的地方（都不改畫法）：
// - 依賴改 import：第 4 批 `STATUS`／`entry`／`BOX` 與共用零件（`shieldBlue`、`hexPts`、`stancePlate`、`bladeSword`、`diagSword`、`bolt`、`crystal`、
//   `upArrow`、`bust`、`heart`、`star4`）從 `./parts`（樣張在這個檔「原樣抄一份」；這裡只在 parts.ts 加 export、呼叫同一份，需求 2.3「同一題材一份畫法」）；
//   `ACT` 從 `./skills`；`ART.hud.move`、`drop` 從 `./legacy48`；`render`、`halo`、`blit`、`outlinePx`、`blank` 與 `H` 的小工具從 `./core`。
// - 極性、類別、名稱讀遊戲端名詞表（`battle/glossary.ts` 的 `statusLook`／`statusName`、`statusFrame.ts` 的 `polarityOf`），不搬樣張的 `G()`／`lookOf`／`polOf`／`clsOf`；
//   框形、框色、深底用 `statusFrame.ts`（和現行同一份）。
// - 不認得的狀態（`entry` 回 null）：照遊戲端畫名稱第一個字（字色米白 `#f2e6c8`；null／空字串畫「?」），不走樣張 `def()` 的第 4 批退回（需求 2.4 第 4 列）。
// - `fitK`：先查 `statusFit.json`（開發頁 `?set=fitgen` 在真瀏覽器量出來的表）；查不到才執行期量（樣張的 `maskOf`／`outsideFrac`／`fitK`）；
//   量不到（沒有畫布或 `Path2D`，例 vitest 假畫布）回 1（規格第 0 節第 1 列）。
// - `res` 預設 `ICON_RES`（樣張寫死 2，值相同）；沒有畫布時 `glyph` 回 null、`paint` 不貼圖樣（框照畫）。
// - `ln(…, "butt")`：樣張把 "butt" 當 lineJoin 傳（瀏覽器忽略這個值），照傳、加型別轉換。用字串查表處加 `!`；`NEW` 加型別註記（鎖霧大陣在初始化式裡引用 `NEW`）。
// ---------------------------------------------------------------------------------------------
import { statusLook, statusName } from "../../battle/glossary";
import { FONT } from "../labels";
import { FRAME_COLOR, framePath, polarityOf, STATUS_BASE_BG, type Polarity } from "../statusFrame";
import { blank, blit, ci, ctxOf, el, f, flame, halo, ICON_RES, ln, OUT, outlinePx, poly, qCanvasAvailable, render, rr, starPts, TAU, type Ctx, type Pt, type QDef, type QOpts } from "./core";
import { ART, drop } from "./legacy48";
import { BOX, bladeSword, bolt, bust, crystal, diagSword, entry as partEntry, heart, shieldBlue, stancePlate, star4, STATUS, upArrow } from "./parts";
import * as QS from "./skills";
import FIT from "./statusFit.json";

type Tint = QS.Tint;
type SDraw = (c: Ctx, o: QOpts) => void;
/** 樣張 `QIconsParts` 用到的部分。 */
const QP = { entry: partEntry, BOX };
const PI = Math.PI;
/** 樣張把 "butt" 當 ln 的 lineJoin 傳（瀏覽器忽略這個值；lineCap 因此是 butt），照傳。 */
const BUTT = "butt" as CanvasLineJoin;
const CREAM = "#f2e6c8", GOLD = "#e8bb48", STONE = "#b4ac9a", STONE_L = "#ece6d6", STONE_D = "#8c8474";
const st = (c: Ctx, col: string, w: number, fn: (x: Ctx) => void, cap: CanvasLineCap = "round") => { c.beginPath(); fn(c); c.strokeStyle = col; c.lineWidth = w; c.lineCap = cap; c.lineJoin = "round"; c.stroke(); };
const at = (c: Ctx, x: number, y: number, k: number, fn: (x: Ctx) => void, rot = 0) => { c.save(); c.translate(x, y); c.rotate(rot); c.scale(k, k); fn(c); c.restore(); };
const fit = (d: SDraw, k: number): SDraw => (c, o) => at(c, 0, 0, k, (q) => d(q, o));
/** 第 3 批的效果記號、第 4 批的部件：同一個題材同一個形，直接呼叫。 */
const act = (id: string, T?: Tint): SDraw => (c, o) => QS.ACT[id]!.d(c, o, (T ?? QS.ACT[id]!.def) as Tint);
const part = (cat: string, id: string): SDraw => (c, o) => QP.entry(cat, id).d(c, o);

// ---------------- 共用零件：shieldBlue、hexPts、stancePlate、bladeSword、diagSword、bolt、crystal、upArrow、bust、heart、star4 從 ./parts（同一份） ----------------
/** 窄一號的朝上箭頭（同 upArrow 的配色；晶能狂湧兩個並排時要拉得開）。 */
const slimArrow = (c: Ctx, T: Tint = ["#ffb23a", "#fff6c8"]) => { poly(c, T[0], [[0, -11], [6, -2], [2.6, -2], [2.6, 9.6], [-2.6, 9.6], [-2.6, -2], [-6, -2]], 0.6); poly(c, T[1], [[0, -11], [-6, -2], [-2.6, -2], [-2.6, 9.6], [0, 9.6]]); };

// ---------------- 這批新增的零件 ----------------
/** 旗桿（木桿＋金頂珠）：戰意的紅三角旗、開場休戰的白旗共用；旗的形不同（三角 vs 方形波浪）。 */
const pole = (c: Ctx) => { rr(c, "#a06a36", -8.4, -8.6, 2.8, 19.2, 1.2); f(c, "#d8a868", () => c.rect(-8.4, -8.6, 1, 19)); ci(c, GOLD, -7, -9.4, 2.2); };
/** 誓約徽章：一枚金屬圓章（中間一顆五角星）掛在兩條紅緞帶上；三個難度用銅、銀、金分。 */
const MEDAL = { bronze: ["#c27a48", "#f0b088", "#8a4a22"], silver: ["#d0d8e0", "#ffffff", "#8a96a4"], gold: ["#e8bb48", "#fff0b0", "#9c7420"] } as const;
const medal = (m: keyof typeof MEDAL): SDraw => (c, o) => { const [a, b, d] = MEDAL[m];
  for (const s of [-1, 1]) poly(c, s < 0 ? "#d8404a" : "#b02a36", [[s * 1.2, 2], [s * 6.6, 2], [s * 8.2, 10.6], [s * 5.4, 8.6], [s * 3, 10.6]], 0.3);
  ci(c, a, 0, -2.6, 8); f(c, d, () => { c.arc(0, -2.6, 8, -0.3, PI * 0.8); c.arc(0, -2.6, 6.2, PI * 0.8, -0.3, true); c.closePath(); }); poly(c, b, starPts(0, -2.6, 5, 2.1, 5), 0.2); if (!o.tiny) el(c, "#ffffff", -4, -6, 1.8, 1.1, -0.6); };
/** 熔核：一顆橘紅的熾熱圓核，表面幾塊深色硬殼、殼縫透出黃白的光；寒燼換冰色。 */
const CORE = { lava: ["#ff6a1a", "#ffe08a", "#6a3424", "#ffb23a"], frost: ["#5ab8f0", "#ffffff", "#2a4a7a", "#bfefff"] } as const;
const core = (kind: keyof typeof CORE, R = 9.4): SDraw => (c, _o) => { const [body, glow, crust, mid] = CORE[kind];
  ci(c, body, 0, 0.4, R); ci(c, mid, -1, -0.4, R * 0.62); ci(c, glow, -1.4, -0.8, R * 0.3);
  const k = R / 9.4; for (const P of [[[-9, -2.4], [-4.6, -8.2], [-1.6, -4.4], [-5, -0.6]], [[2.6, -8.6], [8.4, -4.6], [5.4, -1.4], [1.2, -3.8]], [[-6.2, 5.4], [-1.6, 3.4], [0.6, 8.8], [-3.6, 9.4]], [[4.2, 2.6], [9.2, 2.2], [6.8, 7.8], [3.2, 6.6]]] as Pt[][]) poly(c, crust, P.map(([x, y]): Pt => [x * k, y * k + 0.4]), 0.3); };
/** 龜殼形的殼（熔殼、硬殼）：上緣圓、下緣一排小圓弧（殼的邊片），殼面中間一塊六角殼片、四周放射的縫；不畫帽簷（第 1 稿有一條橫的底座，像安全帽）。 */
const dome = (body: string, hi: string, seam: string, w = 1.6, rim = body): SDraw => (c, _o) => { f(c, body, () => { c.moveTo(-10.4, 4.6); c.bezierCurveTo(-10.6, -11.4, 10.6, -11.4, 10.4, 4.6); c.closePath(); }); for (let i = 0; i < 5; i++) ci(c, rim, -8.4 + i * 4.2, 4.8, 2.4);
  f(c, hi, () => { c.moveTo(-8.4, 1.6); c.bezierCurveTo(-8.4, -5.6, -4.6, -8, -1.4, -8.4); c.lineTo(-1.6, -6.4); c.bezierCurveTo(-4.4, -5.8, -6.4, -3.6, -6.4, 1.6); c.closePath(); });
  const H: Pt[] = [[-3.4, -5], [3.4, -5], [5, -1], [3.4, 2.6], [-3.4, 2.6], [-5, -1]]; ln(c, seam, w, [...H, H[0]!]); for (const [a, b] of [[H[0], [-5.6, -8.6]], [H[1], [5.6, -8.6]], [H[2], [10.2, -1]], [H[5], [-10.2, -1]], [H[3], [5.4, 4.6]], [H[4], [-5.4, 4.6]]] as [Pt, Pt][]) ln(c, seam, w, [a, b]); };

// ---------------- 元素架勢的紋章（第 4 批 stance_holy_1、stance_shadow_1 的做法：元素色的六角臂章＋淺色紋章） ----------------
export interface Emblem { plate: readonly [string, string]; zh: string; d: SDraw }
export const EMBLEM: Readonly<Record<string, Emblem | undefined>> = {
  physical: { plate: ["#6e7884", "#a4aeba"], zh: "鋼灰臂章＋亮色直劍", d: (c, o) => at(c, 0, 0.6, 0.6, (q) => bladeSword(q, o)) },
  fire: { plate: ["#e8601a", "#ffa86a"], zh: "橘色臂章＋黃白火球（圓球拖一道往左上的火尾）", d: (c, _o) => { f(c, "#ffe08a", () => { c.moveTo(-7.6, -7.6); c.quadraticCurveTo(-1.6, -4.6, 1.8, -3.2); c.lineTo(-3.2, 1.8); c.quadraticCurveTo(-4.6, -1.6, -7.6, -7.6); c.closePath(); }); ci(c, "#ffe08a", 1.6, 1.6, 5); ci(c, "#ffffff", 0.8, 0.8, 2.6); } },
  ice: { plate: ["#3f96d0", "#94d0f4"], zh: "冰藍臂章＋白色粗雪花", d: (c, o) => { for (let i = 0; i < 3; i++) at(c, 0, 0.4, 1, (q) => { rr(q, "#ffffff", -1.3, -7, 2.6, 14, 1.3); if (!o.tiny) for (const s of [-1, 1]) ln(q, "#ffffff", 1.4, [[0, s * -4.4], [2.2, s * -6.4]]); }, (i * PI) / 3); ci(c, "#e0f6ff", 0, 0.4, 2.2); } },
  lightning: { plate: ["#5a5ac8", "#9a9af0"], zh: "靛藍臂章＋黃閃電", d: (c, o) => at(c, 0, 0.4, 0.66, (q) => bolt(q, o)) },
  poison: { plate: ["#3f8a24", "#86c85a"], zh: "綠色臂章＋淡綠毒滴（右上一顆泡）", d: (c, o) => { drop(c, "#e6ffd0", -0.8, 1, 0.68); ci(c, "#e6ffd0", 4.8, -4.6, 1.8); if (!o.tiny) el(c, "#ffffff", -2.6, 1.4, 1, 1.8, 0.4); } },
  wind: { plate: ["#24907a", "#6ad0b8"], zh: "青綠臂章＋白色旋風（一圈半的螺旋，尾巴往左下甩）", d: (c, _o) => { const P: Pt[] = [[-7.4, 6.4], [-4.6, 5.4]]; for (let i = 0; i <= 28; i++) { const t = i / 28, a = PI * 0.62 - t * PI * 2.6, r = 6.4 - t * 4.8; P.push([0.6 + Math.cos(a) * r, -0.6 + Math.sin(a) * r]); } ln(c, "#ffffff", 2.3, P); } },
  earth: { plate: ["#8a5a2a", "#c48c52"], zh: "褐色臂章＋淺土色岩塊", d: (c, _o) => { poly(c, "#f0d0a0", [[-6, 4.6], [-6.4, -1.4], [-2, -6], [4.4, -5], [6.6, 0.6], [4, 5.4]], 0.6); poly(c, "#fff0d4", [[-6.4, -1.4], [-2, -6], [-0.6, -1.4]]); poly(c, "#c89a60", [[4.4, -5], [6.6, 0.6], [4, 5.4], [1.6, 0.4]]); } },
};
/* 第 4 批已畫的兩個元素架勢（聖輝、暗影）：壹級直接呼叫第 4 批；貳～伍級同一個圖（級數不畫在圖上，見紀錄檔 6.2）。 */
export const ELEMENTS = ["physical", "fire", "ice", "lightning", "poison", "wind", "earth", "holy", "shadow"] as const;

// =====================================================================
// 新畫與借用（第 4 批沒有的 86 個裡，元素架勢以外的 43 個）
// =====================================================================
export interface NewEntry { zh: string; topic: string; src?: string; d: SDraw }
export const NEW: Readonly<Record<string, NewEntry | undefined>> = {
  // ---- 借用第 3、4 批同題材的部件（同一個題材同一個形） ----
  revealed: { zh: "被揭露", topic: "睜開的眼睛（同效果「揭露」）", src: "b4:effect.reveal", d: part("effect", "reveal") },
  time_bomb: { zh: "定時炸彈", topic: "圓炸彈、引信頭黃火花（同效果「定時炸彈」）", src: "b4:effect.delayed_damage", d: part("effect", "delayed_damage") },
  shielded: { zh: "護盾", topic: "淡藍小盾、白十字（同效果「護盾」）", src: "b3:shield", d: act("shield") },
  undying: { zh: "免死", topic: "紅心、右下一面小藍盾（同效果「免死」）", src: "b4:effect.cheat_death", d: part("effect", "cheat_death") },
  soul_link: { zh: "靈魂連結", topic: "兩個扣在一起的淡紫圓環（前後交扣）", d: (c, o) => { const ring = (q: Ctx, x: number, a0 = 0, a1 = TAU) => st(q, "#c8a0ff", o.tiny ? 3.2 : 2.8, (p) => p.arc(x, 0.4, 5.6, a0, a1), "butt"); ring(c, -3.8); halo(c, o, (q) => { ring(q, 3.8); if (!o.tiny) st(q, "#efe2ff", 1.1, (p) => p.arc(3.8, 0.4, 5.6, PI * 1.15, PI * 1.55), "butt"); }); halo(c, o, (q) => ring(q, -3.8, -0.75, 0.05)); if (!o.tiny) st(c, "#efe2ff", 1.1, (p) => p.arc(-3.8, 0.4, 5.6, PI * 1.15, PI * 1.55), "butt"); } }, /* 第 4 批效果「分擔傷害」（Y 形分岔箭頭）在 1 倍下讀不出連結，也比現行的雙環難認，這裡另畫；同題材不同形，寫進紀錄檔待決 */
  // ---- 護盾家族（第 4 批帶電護盾的做法：同一面淡藍盾，白十字換成各自的記號） ----
  shielded_thorns: { zh: "反傷護盾", topic: "淡藍盾，盾緣往外長出五根鐵刺", d: fit((c, o) => { halo(c, o, (q) => { for (const [x, y, a] of [[-9.4, -9.6, -2.36], [9.4, -9.6, -0.79], [0, -9.6, -1.57], [-9.2, -2, -2.9], [9.2, -2, -0.24]] as const) at(q, x, y, 1, (p) => poly(p, "#7d8794", [[0, -2.2], [4.6, 0], [0, 2.2]], 0.3), a); }); shieldBlue(c, o); halo(c, o, (q) => poly(q, "#5a6169", [[-4.6, 3.6], [0, -5.4], [4.6, 3.6], [0, 1.2]], 0.3)); }, 0.8) }, /* 第 1 稿盾面三根刺像遠山、城市天際線；改成盾緣長刺＋盾面一個鐵刺尖 */
  shielded_mending: { zh: "回春護盾", topic: "淡藍盾、盾面一株綠芽（同狀態「再生」的嫩芽）", d: fit((c, o) => { shieldBlue(c, o); halo(c, o, (q) => at(q, 0, -0.6, 0.62, (p) => QP.entry("status", "regenerating").d(p, o))); }, 0.86) },
  shielded_wet: { zh: "水幕護盾", topic: "淡藍盾、盾面一顆深藍水滴", d: fit((c, o) => { shieldBlue(c, o); halo(c, o, (q) => { drop(q, "#2a78d8", 0, -0.6, 0.58); if (!o.tiny) el(q, "#cfe8ff", -1.6, 0.6, 0.9, 1.6, 0.4); }); }, 0.86) },
  shielded_marking: { zh: "烙印護盾", topic: "淡藍盾、盾面一個紅準星（同狀態「被標記」）", d: fit((c, o) => { shieldBlue(c, o); halo(c, o, (q) => at(q, 0, -1, 0.56, (p) => QS.ACT.mark.d(p, o, QS.ACT.mark.def as Tint))); }, 0.86) },
  // ---- 姿態（第 4 批的六角臂章，換底色與紋章） ----
  stance_flame: { zh: "焰刃姿態", topic: "焦橘臂章、一把刃換成黃白的斜劍（劍尖一撮火）", d: stancePlate("#c4481c", "#f08a58", (c, o) => { at(c, 0, 0, 0.56, (q) => diagSword(1, ["#ffe08a", "#ffffff", "#ffb23a"])(q, o)); if (!o.tiny) flame(c, "#ffffff", 4.4, -4.6, 0.2); }) },
  stance_blaze: { zh: "烈焰姿態", topic: "酒紅臂章、一把大白刃斜劍為主，劍後左下一小團黃火", d: stancePlate("#b0283e", "#e8708a", (c, o) => { flame(c, "#ffd23f", -3.2, 3.6, 0.36); at(c, 0.6, -0.4, 0.66, (q) => diagSword(1, ["#ffffff", "#ffffff", "#ffe08a"])(q, o)); }) }, /* 第 2 版：第 1 版（深紅橘底、大火在前）頭頂 11 和狂怒（紅底黃火）分不開；底換酒紅、主體換大白刃，火縮到劍後 */
  stance_frost: { zh: "霜刃姿態", topic: "冰藍臂章、一把淡青白刃的大斜劍", d: stancePlate("#3a7cc0", "#86b8e8", (c, o) => at(c, 0.4, -0.4, 0.66, (q) => diagSword(1, ["#e8faff", "#ffffff", "#8fe3ff"])(q, o))) }, /* 第 2 版：劍放大（0.56 → 0.66），頭頂 11 讀成白斜條 */
  stance_glacier: { zh: "冰川姿態", topic: "深藍臂章、三根白色冰柱（中間高）", d: stancePlate("#2a5aa8", "#6a9ad8", (c, _o) => { poly(c, "#d8f6ff", [[-6.4, 6], [-6.4, -0.6], [-4.4, -3.6], [-2.4, -0.6], [-2.4, 6]], 0.3); poly(c, "#d8f6ff", [[2.4, 6], [2.4, -0.6], [4.4, -3.6], [6.4, -0.6], [6.4, 6]], 0.3); poly(c, "#ffffff", [[-2.2, 6], [-2.2, -3.6], [0, -7.4], [2.2, -3.6], [2.2, 6]], 0.3); }) },
  stance_bastion: { zh: "堡壘姿態", topic: "石板灰臂章、一座米白的城塔（頂上三個垛口）", d: stancePlate("#5a6478", "#8e9aae", (c, o) => { f(c, "#f2ead6", () => { c.moveTo(-5.2, 6.6); c.lineTo(-5.2, -6.6); c.lineTo(-2.6, -6.6); c.lineTo(-2.6, -4.4); c.lineTo(-0.9, -4.4); c.lineTo(-0.9, -6.6); c.lineTo(0.9, -6.6); c.lineTo(0.9, -4.4); c.lineTo(2.6, -4.4); c.lineTo(2.6, -6.6); c.lineTo(5.2, -6.6); c.lineTo(5.2, 6.6); c.closePath(); }); f(c, "#4a5262", () => c.roundRect(-1.6, 1.4, 3.2, 5.2, [1.6, 1.6, 0, 0])); if (!o.tiny) f(c, "#c8bea6", () => c.rect(2.6, -4.4, 2.6, 11)); }) },
  // ---- 種族技 ----
  race_adapt: { zh: "應變", topic: "米白人形往右閃，背後兩道速度線，一支紅箭頭從頭頂上面擦過去", d: (c, o) => { for (const [y, w] of [[-1.4, 6.4], [3.4, 4.6]] as const) rr(c, CREAM, -10.6, y, w, 2.4, 1.2); bust(c, CREAM, 3, 2.4, 1.02); halo(c, o, (q) => { ln(q, "#ff5a5a", 2.2, [[-9.4, -8.6], [5, -8.6]]); poly(q, "#ff5a5a", [[4.4, -11.6], [10.4, -8.6], [4.4, -5.6]], 0.3); }); } },
  race_stonewall: { zh: "穩若磐石", topic: "一塊寬大的平頂多面灰岩，左下一支紅箭頭撞在岩面上、撞點一顆黃火花", d: (c, o) => {
    poly(c, STONE, [[-4.4, 8.4], [-6.6, 1.6], [-4.2, -5.4], [4.4, -6.6], [10.4, -2.4], [10.6, 5.4], [7.6, 8.4]], 0.6);
    poly(c, STONE_L, [[-6.6, 1.6], [-4.2, -5.4], [4.4, -6.6], [10.4, -2.4], [3.2, -1], [-2.4, 0.6]]); poly(c, STONE_D, [[10.4, -2.4], [10.6, 5.4], [7.6, 8.4], [3.6, 8.4], [3.2, -1]]);
    if (!o.tiny) ln(c, STONE_D, 1, [[-2.4, 0.6], [-1.4, 8.4]]);
    halo(c, o, (q) => { ln(q, "#ff4a4a", 2.6, [[-10.8, 10], [-7.4, 6.6]], BUTT); poly(q, "#ff4a4a", [[-9.6, 3.6], [-4.8, 4], [-5.4, 8.8]], 0.3); });
    halo(c, o, (q) => star4(q, "#ffd23f", -5.2, 3.4, 3.6, o.tiny ? null : "#ffffff")); } }, /* 第 2 版：第 1 版（圓頂直立的石塊立在地面上、短紅箭頭）讀成墓碑；改成寬大於高的平頂岩塊、拿掉地面，箭頭放大並加撞擊火花 */
  // ---- 一般增益、減益 ----
  rallied: { zh: "戰意", topic: "木旗桿上一面紅色三角旗", d: (c, _o) => { pole(c); poly(c, "#e8403a", [[-5.6, -8.4], [10.4, -3.6], [-5.6, 1.4]], 0.6); poly(c, "#ff8a7a", [[-5.6, -8.4], [10.4, -3.6], [-5.6, -4.6]]); } },
  league_truce: { zh: "開場休戰", topic: "木旗桿上一面白旗（方形、右緣波浪）", d: (c, _o) => { pole(c); f(c, "#f6f2e6", () => { c.moveTo(-5.6, -8.8); c.lineTo(9.4, -8.8); c.quadraticCurveTo(7.4, -6, 9.8, -3.6); c.quadraticCurveTo(11, -1, 9.4, 1.6); c.lineTo(-5.6, 1.6); c.closePath(); }); f(c, "#c8c0ac", () => { c.moveTo(-5.6, -2); c.lineTo(9.6, -2); c.quadraticCurveTo(11, -0.4, 9.4, 1.6); c.lineTo(-5.6, 1.6); c.closePath(); }); } },
  commanding: { zh: "號令", topic: "青色小靈（召喚物），右上一個橘黃的朝上箭頭", d: (c, o) => { at(c, -2, 1.8, 0.84, (q) => QS.ACT.summon.d(q, o, QS.ACT.summon.def as Tint)); halo(c, o, (q) => at(q, 6, -5.6, 0.46, (p) => upArrow(p, o))); } },
  armor_broken: { zh: "破甲", topic: "亮鋼灰胸甲（T 字形：寬肩甲、挖進去的袖洞、深 V 領），一道深色裂縫，右下崩掉一塊", d: (c, o) => { const P: Pt[] = [[-10.6, -6.2], [-7.8, -9.8], [-3.8, -9.8], [0, -2.6], [3.8, -9.8], [7.8, -9.8], [10.6, -6.2], [9.8, -2], [6.4, -1.4], [6.6, 9.8], [-6.6, 9.8], [-6.4, -1.4], [-9.8, -2]]; c.save(); c.beginPath(); P.forEach(([x, y], i) => (i ? c.lineTo(x, y) : c.moveTo(x, y))); c.closePath(); c.moveTo(7, 2.6); c.lineTo(3, 5); c.lineTo(4, 10.4); c.lineTo(7.4, 10.4); c.closePath(); c.clip("evenodd"); poly(c, "#a4aebb", P, 0.6); poly(c, "#d2d9e2", [[-10.6, -6.2], [-7.8, -9.8], [-3.8, -9.8], [0, -2.6], [0, 9.8], [-6.6, 9.8], [-6.4, -1.4], [-9.8, -2]]); f(c, "#7d8794", () => c.rect(4.2, -1.4, 2.6, 11.4)); f(c, "#8a96a4", () => c.rect(-6.6, 4, 13.2, 1.6)); c.restore(); ln(c, OUT, 1.7, [[0.2, -2.2], [-1.4, 0.8], [1.2, 3.4], [-0.6, 6.4], [0.6, 9.6]], "miter"); halo(c, o, (q) => poly(q, "#a4aebb", [[10.4, 4.4], [7.8, 6], [8.4, 9.8], [10.8, 8.8]], 0.3)); } }, /* 第 2 版：第 1 版像撕開的紙箱；改成 T 字形（寬肩甲、袖洞挖進去、V 領挖深），本體換亮鋼灰不接近純白 */
  entangled: { zh: "纏繞", topic: "褐色靴子（同 HUD「移動」）的靴筒被兩圈淡褐繩子纏住", d: (c, o) => { at(c, 0.6, 0.6, 0.47, (q) => { q.translate(-27, -24); ART.hud.move.d(q, o); }); halo(c, o, (q) => { for (const y of [-6.4, -1.2]) { ln(q, "#ecc890", 2.6, [[-8.6, y + 2.4], [7.2, y - 1.8]]); } ln(q, "#ecc890", 2.2, [[7.2, -3], [10, -7.4]]); }); } },
  overdrawn: { zh: "透支", topic: "黃閃電（同卡片 AP），右下一個紅色減號", d: (c, o) => { at(c, -1.6, -0.6, 0.95, (q) => bolt(q, o)); halo(c, o, (q) => rr(q, "#ff5a5a", 2.6, 5.4, 8.6, 3.4, 1.2)); } },
  heart_link: { zh: "連心", topic: "兩顆疊著的心（後面粉、前面紅）", d: (c, o) => { heart(c, "#f49ab0", -3.6, -1.8, 0.86); if (!o.tiny) el(c, "#ffd8e0", -7, -4.6, 1.8, 1.1, -0.6); halo(c, o, (q) => { heart(q, "#f0503e", 3.4, 2.6, 0.9); if (!o.tiny) el(q, "#ffb0a0", 0.4, 0.4, 1.8, 1.1, -0.6); }); } },
  mist_return: { zh: "歸一", topic: "一道灰白的霧旋往中心收，中心一個綠十字（回血）", d: (c, o) => { st(c, "#dfe4ee", 3, (x) => { x.arc(0, 0, 8.6, PI * 0.9, PI * 2.1); }, "butt"); st(c, "#b8c0d0", 2.6, (x) => { x.arc(0.6, 0.6, 5.4, PI * 1.9, PI * 3.0); }, "butt"); halo(c, o, (q) => { rr(q, "#5ad06a", -1.5, -4.2, 3, 8.4, 0.8); rr(q, "#5ad06a", -4.2, -1.5, 8.4, 3, 0.8); }); } },
  // ---- 陣法（劍陣、護陣、鎖霧大陣） ----
  sword_formation: { zh: "劍陣", topic: "三把並排直立的亮劍（中間那把高一點）", d: (c, o) => { for (const x of [-6.4, 6.4]) at(c, x, 1.6, 0.6, (q) => bladeSword(q, o)); halo(c, o, (q) => at(q, 0, -0.4, 0.68, (p) => bladeSword(p, o))); } },
  array_ward: { zh: "護陣", topic: "地上一圈青綠的陣紋環，中心一顆陣眼玉石", d: (c, o) => { st(c, "#5ad0b0", 3, (x) => x.arc(0, 0, 8.8, 0, TAU)); if (!o.tiny) for (let i = 0; i < 6; i++) ci(c, "#c8fff0", Math.cos((i / 6) * TAU) * 8.8, Math.sin((i / 6) * TAU) * 8.8, 1); poly(c, "#7fe0c0", [[0, -5.6], [4.4, 0], [0, 5.6], [-4.4, 0]], 0.4); poly(c, "#e6fff6", [[0, -5.6], [-4.4, 0], [0, 0]]); } },
  summit_array_ward: { zh: "鎖霧大陣", topic: "同護陣的陣紋環與陣眼，下半一團灰白的霧", d: (c, o) => { NEW["array_ward"]!.d(c, o); halo(c, o, (q) => { for (const [x, y, r] of [[-5.4, 6.4, 3.6], [0, 5.4, 4.2], [5.4, 6.6, 3.4]] as const) ci(q, "#e4e8f0", x, y, r); rr(q, "#e4e8f0", -8.6, 6.4, 17.2, 3.6, 1.8); if (!o.tiny) f(q, "#b8c0d0", () => q.rect(-8.6, 8.6, 17.2, 1.4)); }); } },
  // ---- 源晶（碎晶之主一戰） ----
  shard_burst: { zh: "碎晶", topic: "淡紫源晶裂成兩半往兩邊散開，右下一顆藍水滴（晶液）", d: (c, o) => { c.save(); c.beginPath(); c.moveTo(-12, -12); c.lineTo(1.4, -12); c.lineTo(-1.2, -2); c.lineTo(1.6, 3); c.lineTo(-0.6, 12); c.lineTo(-12, 12); c.closePath(); c.clip(); at(c, -1.8, -0.6, 0.92, crystal); c.restore(); c.save(); c.beginPath(); c.moveTo(12, -12); c.lineTo(1.4, -12); c.lineTo(-1.2, -2); c.lineTo(1.6, 3); c.lineTo(-0.6, 12); c.lineTo(12, 12); c.closePath(); c.clip(); at(c, 1.8, 0.4, 0.92, crystal); c.restore(); if (!o.tiny) halo(c, o, (q) => drop(q, "#4aa8ff", 7.4, 6.6, 0.3)); } },
  rift_resonance: { zh: "源晶共鳴", topic: "淡紫源晶，左右各兩道往外的共鳴弧", d: (c, o) => { at(c, 0, 0, 0.66, crystal); for (const s of [-1, 1]) { st(c, "#e0d4ff", 2.2, (x) => x.arc(0, 0, 7.6, s > 0 ? -0.6 : PI - 0.6, s > 0 ? 0.6 : PI + 0.6), "round"); if (!o.tiny) st(c, "#b8a8ff", 1.8, (x) => x.arc(0, 0, 10.2, s > 0 ? -0.5 : PI - 0.5, s > 0 ? 0.5 : PI + 0.5), "round"); } } },
  rift_channel: { zh: "灌注源晶", topic: "中間一顆淡紫源晶，三道光往外灌進三根小晶柱", d: (c, o) => { for (let i = 0; i < 3; i++) { const a = -PI / 2 + (i * TAU) / 3, x = Math.cos(a) * 8, y = Math.sin(a) * 8; ln(c, "#d6ccff", 1.8, [[Math.cos(a) * 3.6, Math.sin(a) * 3.6], [x, y]]); poly(c, "#b8a8ff", [[x, y - 3], [x + 2, y - 1], [x + 2, y + 2.4], [x - 2, y + 2.4], [x - 2, y - 1]], 0.3); } halo(c, o, (q) => at(q, 0, 0, 0.46, crystal)); } },
  crystal_surge: { zh: "晶能湧動", topic: "淡紫源晶，右上一個橘黃的朝上箭頭", d: (c, o) => { at(c, -2.2, 1.6, 0.82, crystal); halo(c, o, (q) => at(q, 6, -5.8, 0.46, (p) => upArrow(p, o))); } },
  crystal_surge_2: { zh: "晶能狂湧", topic: "淡紫源晶，上方兩個並排拉開的橘黃朝上箭頭", d: (c, o) => { at(c, -3, 2.6, 0.72, crystal); for (const x of [1.2, 8]) halo(c, o, (q) => at(q, x, -5.4, 0.42, (p) => slimArrow(p))); } }, /* 第 2 版：第 1 版兩個箭頭上下疊在右上，20 真 1 倍要盯著看；改成左右並排、中間拉開 */
  rift_collapse: { zh: "界崩", topic: "一塊灰石浮台（平頂、底下尖）從中間裂開，右半塊往下掉、歪一邊，底下兩顆碎石", d: (c, _o) => { const half = (s: number) => (q: Ctx) => { q.save(); q.scale(s, 1); poly(q, STONE, [[0.4, -4.4], [9.6, -4.4], [8.4, -0.6], [3.6, 5.6], [0.4, 6.4], [1.8, 2], [-0.2, -1.2]], 0.4); f(q, STONE_L, () => q.rect(0.6, -4.4, 9, 1.8)); poly(q, STONE_D, [[9.6, -2.6], [8.4, -0.6], [3.6, 5.6], [5, -0.6]]); q.restore(); }; at(c, -0.6, -4, 1, half(-1), 0); at(c, 1.6, -0.6, 1, half(1), 0.42); for (const [x, y, r] of [[-1.6, 7.4, 1.8], [1.4, 9.8, 1.3]] as const) poly(c, STONE_D, [[x - r, y], [x, y - r], [x + r, y], [x, y + r]], 0.3); } }, /* 第 1 稿兩片斜板拼成一個 V（像翅膀、打開的書）、第 2 稿左右對稱往下歪（像飛蛾）；改成左半不動、右半往下掉的不對稱構圖 */
  charging: { zh: "蓄力", topic: "一顆黃白的能量球，外面兩道往內捲的橘色弧", d: (c, _o) => { for (let i = 0; i < 2; i++) st(c, "#ffb23a", 2.8, (x) => x.arc(0, 0, 8.6, i * PI + 0.2, i * PI + 1.9), "round"); for (let i = 0; i < 2; i++) at(c, Math.cos(i * PI + 1.9) * 8.6, Math.sin(i * PI + 1.9) * 8.6, 1, (q) => poly(q, "#ffb23a", [[-3, -2.4], [3, -2.4], [0, 2.4]], 0.3), i * PI + 1.9 + PI); ci(c, "#ffe08a", 0, 0, 5); ci(c, "#ffffff", -0.8, -0.8, 2.4); } },
  // ---- 誓約、循環賽 ----
  oath_bonus_easy: { zh: "誓約之力・易", topic: "銅色誓約徽章（紅緞帶、中間一顆星）", d: medal("bronze") },
  oath_bonus_medium: { zh: "誓約之力・中", topic: "銀色誓約徽章", d: medal("silver") },
  oath_bonus_hard: { zh: "誓約之力・難", topic: "金色誓約徽章", d: medal("gold") },
  oath_broken: { zh: "破誓", topic: "金色誓約徽章被一道紅斜槓劃掉", d: (c, o) => { medal("gold")(c, o); halo(c, o, (q) => { if (o.tiny) ln(q, OUT, 5.4, [[-8.6, 8.6], [8.6, -8.6]]); ln(q, "#ff4a5a", 3.4, [[-8.6, 8.6], [8.6, -8.6]]); }); } },
  // ---- 熔核、殼（灰燼之心一戰） ----
  molten_burst: { zh: "熔核爆裂", topic: "一顆橘紅熾熱的熔核（幾塊深色硬殼、殼縫透黃光）", d: core("lava") },
  heart_ember_burst: { zh: "殼縫熔核", topic: "同熔核，左上蓋著一片灰色的殼", d: (c, o) => { at(c, 1.4, 1.4, 0.86, (q) => core("lava")(q, o)); halo(c, o, (q) => { f(q, "#9a928a", () => { q.moveTo(-10.6, 3); q.bezierCurveTo(-11, -8, -4, -11, 4, -10); q.lineTo(2.6, -6.6); q.bezierCurveTo(-3, -7, -7, -4, -6.6, 3); q.closePath(); }); if (!o.tiny) f(q, "#d0c8bc", () => { q.moveTo(-9.4, -1); q.bezierCurveTo(-9.4, -6, -5.6, -8.6, -1, -9.2); q.lineTo(-1.4, -8); q.bezierCurveTo(-5, -7.4, -7.8, -5, -8, -1); q.closePath(); }); }); } },
  frost_ember_burst: { zh: "寒燼爆裂", topic: "一顆冰藍的寒燼核（深藍硬殼、殼縫透白光）", d: core("frost") },
  molten_shell: { zh: "熔殼", topic: "暗紅褐的龜殼形外殼（中間一塊六角殼片），殼片之間的縫透橘光", d: (c, o) => dome("#8a3a22", "#c46a42", "#ffb23a", 1.8, "#6a2a18")(c, o) },
  hard_shell: { zh: "硬殼", topic: "灰褐色的龜殼形硬殼（中間一塊六角殼片），殼片之間深色的縫", d: (c, o) => dome("#b0a084", "#e6dac2", "#5e4a3a", 1.6, "#8a7a62")(c, o) },
};

// =====================================================================
// 狀態 → 圖樣：src 寫明圖樣從哪裡來（清單用遊戲端名詞表，見 list()）
// =====================================================================
export type StatusKind = "b4" | "new" | "borrow";
export interface StatusEntry { zh: string; topic: string; src: string; kind: StatusKind; family?: string; level?: number; d: SDraw }
const STANCE_RE = /^stance_(\w+)_([1-5])$/;
/** 狀態的 Q 版圖樣；沒有（不認得的狀態）回 null。 */
export function entry(id: string): StatusEntry | null {
  if (STATUS[id]) { const e = QP.entry("status", id); return { zh: e.zh, topic: e.topic ?? "", src: "b4:status." + id, kind: "b4", d: e.d }; }
  const m = STANCE_RE.exec(id);
  if (m && (ELEMENTS as readonly string[]).includes(m[1]!)) {
    if (m[1] === "holy" || m[1] === "shadow") { const e = QP.entry("status", "stance_" + m[1] + "_1"); return { zh: e.zh.replace("·壹", ""), topic: (e.topic ?? "") + "（各級同一個圖）", src: "b4:status.stance_" + m[1] + "_1", kind: "b4", d: e.d, level: Number(m[2]) }; }
    const E = EMBLEM[m[1]!]!; return { zh: m[1]!, topic: E.zh + "（各級同一個圖）", src: "new:emblem." + m[1], kind: "new", family: "element_stance", d: stancePlate(E.plate[0], E.plate[1], E.d), level: Number(m[2]) };
  }
  const n = NEW[id]; if (n) return { ...n, kind: n.src ? "borrow" : "new", src: n.src ?? "new" };
  return null;
}
/** 類別 → 框的底色（美術 PM 定：類別色畫在底色；硬控偏黃不偏褐、提亮後和圖樣再比一次亮度）。沒有類別的照現行的深底。 */
export const BASE_BG = STATUS_BASE_BG;
export const CLASS_BG: Readonly<Record<string, string | undefined>> = { hard: "#d4ac20", movement: "#2f78c8", mental: "#8a4ccc" };
export const CLASS_ZH: Readonly<Record<string, string | undefined>> = { hard: "硬控（暈眩、冰凍）", movement: "移動控制（緩速、定身）", mental: "心智控制（嘲諷、恐懼、沉默）" };
/** 框色（同現行 `FRAME_COLOR`）。 */
export const FRAME: Readonly<Record<Polarity, string>> = FRAME_COLOR;
/** 控制類別（名詞表 `status_look.control_group`；沒有回 null）。 */
export const clsOf = (id: string | null | undefined): string | null => (id == null ? null : (statusLook(id)?.control_group ?? null));
export { polarityOf as polOf };

/** 圖樣本身（±10 單位）在框裡畫多大：框邊長的 GLYPH_K（現行圖樣是 ±10 單位 × size/26 × 0.95 ≈ 0.73）。 */
export const GLYPH_K = 0.74;
/** 狀態卡（`statusIconTile`＋`tileCanvas` 20）的框邊長、頭頂（`statusIconCanvas` 11）的框邊長（CSS px）。 */
export const CARD_FRAME = 16.8, HEAD_FRAME = 9;
/** 第 2 版：頭頂 11 染底的框（圖樣不包外框、四周留 1 裝置像素的底色圈）裡，和底色同色系、或塞滿框的圖樣另給一個頭頂用的形（同題材）。
 *  暈眩：省掉暈眩弧與小星，只畫一顆米白大星（黃星在黃底上沒有外框會黏成一塊）；沉默：對話框換淡紫白；嘲諷：四道青筋往外推、中心留大一點的洞露出紫底。 */
export const HEAD_TINT: Readonly<Record<string, { topic: string; d: SDraw } | undefined>> = {
  stun: { topic: "一顆米白大星", d: (c) => poly(c, "#fbf3dc", starPts(0, 0.8, 10.6, 4.6, 5), 0.5) },
  silenced: { topic: "淡紫白對話框、深色叉（紫對話框在紫底上沒有外框會黏住）", d: (c) => { poly(c, "#f0e2ff", [[-5.4, 3], [-7, 10], [0.6, 3.6]], 0.4); rr(c, "#f0e2ff", -10, -9.4, 20, 13.8, 5); ln(c, "#3a2458", 3, [[-4.4, -6], [4.4, 1.6]]); ln(c, "#3a2458", 3, [[4.4, -6], [-4.4, 1.6]]); } },
  taunted: { topic: "四道橘青筋往外推、中心留洞", d: (c) => { for (let i = 0; i < 4; i++) { c.save(); c.rotate((i * PI) / 2); st(c, "#ff7a3a", 3.6, (x) => { x.moveTo(4.6, 10); x.quadraticCurveTo(4.6, 4.6, 10, 4.6); }); c.restore(); } } },
};
/** 圖樣定義（給 core.render）：畫在 48 格，±10 單位放大 1.8 倍。cpx＝圖樣本身顯示的 CSS px；head＝頭頂 11 染底框用的形（HEAD_TINT，沒有就同一個）。 */
export function def(id: string, cpx: number, head = false): QDef { const e = (head ? HEAD_TINT[id] : undefined) ?? entry(id) ?? { d: (c: Ctx, o: QOpts) => QP.entry("status", id).d(c, o) }; return { d: (c, o) => { c.save(); c.translate(24, 24); c.scale(1.8, 1.8); e.d(c, { ...o, small: cpx <= 24, tiny: cpx <= 14 }); c.restore(); } }; }
export interface GlyphOpt { ow?: number; head?: boolean }
/** 只有圖樣的 canvas：≤14px 不包外框（規則 8）；opt.ow 指定外框（CSS px）。狀態卡染類別底色的框裡給 1 個裝置像素的外框；頭頂 11 染底的不包（見 paint）。沒有畫布時回 null。 */
export const glyph = (id: string, cpx: number, res = ICON_RES, opt: GlyphOpt = {}): HTMLCanvasElement | null => render(def(id, cpx, opt.head), cpx * QP.BOX, res, { ow: opt.ow ?? (cpx <= 14 ? 0 : outlinePx(cpx)) });
/** 框線的內緣（CSS px，中心在原點）：圖樣要收在這裡面，不然會蓋掉框（極性的形狀）。size＝框邊長，線寬照現行 max(1.5, size×0.09)。 */
export function innerPath(pol: Polarity, size: number, inset = 0): Path2D { const r = size / 2, lw = Math.max(1.5, size * 0.09), hw = lw / 2 + inset, p = new Path2D();
  if (pol === "buff") p.arc(0, 0, r - hw, 0, TAU); else if (pol === "debuff") p.roundRect(-r * 0.9 + hw, -r * 0.9 + hw, r * 1.8 - lw, r * 1.8 - lw, Math.max(0, r * 0.35 - hw));
  else { const R = (r * 0.866 - hw) / 0.866; for (let i = 0; i < 6; i++) p.lineTo(Math.cos((i / 6) * TAU + TAU / 12) * R, Math.sin((i / 6) * TAU + TAU / 12) * R); } p.closePath(); return p; }
/** 框的內緣以內有多大（CSS px）：圓＝直徑、圓角方＝邊長、六角＝對邊距離。佔框比例（規則 7）的分母。 */
export const innerWidth = (pol: Polarity, size: number): number => { const r = size / 2, lw = Math.max(1.5, size * 0.09); return pol === "buff" ? 2 * r - lw : pol === "debuff" ? 1.8 * r - lw : 2 * r * 0.866 - lw; };
const FIT_K = 6, maskMemo = new Map<string, { M: number; d: Uint8ClampedArray }>(), fitMemo = new Map<string, number>();
/** 框內緣的遮罩（FIT_K 倍解析度）。 */
function maskOf(pol: Polarity, size: number, inset = 0): { M: number; d: Uint8ClampedArray } { const key = pol + "|" + size.toFixed(2) + "|" + inset.toFixed(2); if (!maskMemo.has(key)) { const M = Math.ceil(size * 1.6 * FIT_K), cv = blank(M), x = ctxOf(cv); x.translate(M / 2, M / 2); x.scale(FIT_K, FIT_K); x.fillStyle = "#fff"; x.fill(innerPath(pol, size, inset)); maskMemo.set(key, { M, d: x.getImageData(0, 0, M, M).data }); } return maskMemo.get(key)!; }
/** 圖樣畫到框內緣（再內縮 inset CSS px）以外的像素比例（k＝圖樣再縮放的倍率）。inset＞0 是頭頂 11 染底的框，量頭頂用的形（HEAD_TINT）。 */
export function outsideFrac(id: string, size: number, k = 1, inset = 0): number { const { M, d: md } = maskOf(polarityOf(id), size, inset), g = glyph(id, size * GLYPH_K * k, FIT_K, { ow: 0, head: inset > 0 }); if (!g) return 0; const S = g.width, d = ctxOf(g).getImageData(0, 0, S, S).data, off = Math.round((M - S) / 2); let all = 0, out = 0;
  for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) { if ((d[(y * S + x) * 4 + 3] ?? 0) < 128) continue; all++; const mx = x + off, my = y + off; if (mx < 0 || my < 0 || mx >= M || my >= M || (md[(my * M + mx) * 4 + 3] ?? 0) < 128) out++; } return out / Math.max(1, all); }
/** 量得到嗎（有畫布、有 Path2D；vitest 的假畫布沒有 Path2D）。 */
const canMeasure = (): boolean => qCanvasAvailable() && typeof Path2D !== "undefined";
/** `fitK` 表與執行期量測的鍵：`id|框邊長 toFixed(2)|inset toFixed(2)`。 */
export const fitKey = (id: string, size: number, inset = 0): string => id + "|" + size.toFixed(2) + "|" + inset.toFixed(2);
/** 開發頁 `?set=fitgen` 在真瀏覽器量出來的表（`statusFit.json`，不手改）。 */
const FIT_TABLE: Readonly<Record<string, number | undefined>> = (FIT as { fit: Record<string, number> }).fit;
/** 執行期量（樣張的 fitK 原樣：從 1 往下，每次 0.02，直到畫到框外的像素 ≤0.5%；最小 0.7，留底色圈的最小 0.4）。量不到回 1。 */
export function fitKMeasured(id: string, size: number, inset = 0): number { const key = fitKey(id, size, inset); if (!fitMemo.has(key)) { if (!canMeasure()) return 1; let k = 1; const min = inset > 0 ? 0.4 : 0.7; while (k > min && outsideFrac(id, size, k, inset) > 0.005) k = Math.round((k - 0.02) * 100) / 100; fitMemo.set(key, k); } return fitMemo.get(key)!; }
/** 圖樣收進框內緣的縮放（照圓章自動縮放的做法）。框邊長不同（狀態卡 16.8、頭頂 9）各算一次：先查表，查不到才量，量不到回 1。 */
export function fitK(id: string, size: number, inset = 0): number { return FIT_TABLE[fitKey(id, size, inset)] ?? fitKMeasured(id, size, inset); }
/** 表上有幾筆（開發頁、測試用）。 */
export const fitTableSize = (): number => Object.keys(FIT_TABLE).length;
/** 清掉執行期量測與遮罩的快取（測試換畫布用）。 */
export function clearQStatusMemo(): void { maskMemo.clear(); fitMemo.clear(); }
/** 頭頂 11 這一級（框邊長 < 12 CSS px）染底的框：圖樣不包外框，四周留 1 個裝置像素的底色圈（第 2 版，美術 PM 定）。回傳要內縮幾 CSS px，不是就回 0。 */
export const HEAD_MAX = 12;
export const tintInset = (frameCss: number, res: number, cls: string | null): number => (cls && frameCss < HEAD_MAX ? 1 / res : 0);
/** 不認得的狀態：名稱第一個字的字色（需求 2.4 第 4 列）。 */
export const UNKNOWN_INK = "#f2e6c8";
/** 不認得的狀態畫名稱第一個字（遊戲端 drawGlyph 的字型與位置：±10 單位的座標 × size/26 × 0.95、bold 13px）；null／空字串畫「?」。 */
function paintUnknown(ctx: Ctx, id: string | null | undefined, cx: number, cy: number, size: number): void {
  const name = id == null || id === "" ? "?" : statusName(id), k = (size / 26) * 0.95;
  ctx.save(); ctx.translate(cx, cy); ctx.scale(k, k); ctx.fillStyle = UNKNOWN_INK; ctx.font = `bold 13px ${FONT}`; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText([...name][0] ?? "?", 0, 1); ctx.restore();
}
export interface PaintOpt { tint?: boolean }
/** 畫一個完整的狀態圖示（現行的框＋Q 版圖樣），中心 (cx,cy)、框邊長 size（ctx 的單位）；unitPx＝ctx 1 單位是幾個 CSS px，res＝每 CSS px 幾個裝置像素。
 *  opt.tint＝false 時不染類別底色（對照用）。流程：框 → 深底 → 類別底色 → 框線 → `blit` 圖樣（不認得的畫名稱第一個字）。 */
export function paint(ctx: Ctx, id: string | null | undefined, cx: number, cy: number, size: number, unitPx = 1, res = ICON_RES, opt: PaintOpt = {}): void {
  const pol = polarityOf(id), cls = opt.tint === false ? null : clsOf(id), r = size / 2, frameCss = size * unitPx, inset = tintInset(frameCss, res, cls);
  ctx.save(); ctx.translate(cx, cy); framePath(ctx, pol, r); ctx.fillStyle = BASE_BG; ctx.fill(); const bg = cls ? CLASS_BG[cls] : undefined; if (bg) { ctx.fillStyle = bg; ctx.fill(); }
  ctx.lineWidth = Math.max(1.5, frameCss * 0.09) / unitPx; ctx.strokeStyle = FRAME[pol]; ctx.stroke(); ctx.restore();
  if (id == null || entry(id) === null) { paintUnknown(ctx, id, cx, cy, size); return; }
  const cpx = frameCss * GLYPH_K * fitK(id, frameCss, inset), g = glyph(id, cpx, res, inset ? { ow: 0, head: true } : cls ? { ow: 1 / res } : {}), a = (cpx * QP.BOX) / unitPx;
  if (g) blit(ctx, g, cx - a / 2, cy - a / 2, a, unitPx * res);
}
export interface CanvasOpt extends PaintOpt { res?: number }
/** 戰場頭頂（現行 statusIconCanvas）：px 邊長的 canvas，框邊長 px−2。沒有畫布時回 null。 */
export function headCanvas(id: string | null | undefined, px: number, zoom = 1, opt: CanvasOpt = {}): HTMLCanvasElement | null { if (!qCanvasAvailable()) return null; const res = opt.res ?? (zoom === 1 ? ICON_RES : zoom), cv = blank(Math.round(px * res)); if (cv.style) cv.style.width = cv.style.height = px * zoom + "px"; const x = ctxOf(cv); x.scale(res, res); paint(x, id, px / 2, px / 2, px - 2, 1, res, opt); return cv; }
/** 狀態卡（現行 statusIconTile＋tileCanvas）：100 單位的方塊、裁成半徑 49 的圓，框畫在 50,50、邊長 84。沒有畫布時回 null。 */
export function cardCanvas(id: string | null | undefined, px: number, zoom = 1, opt: CanvasOpt = {}): HTMLCanvasElement | null { if (!qCanvasAvailable()) return null; const res = opt.res ?? (zoom === 1 ? ICON_RES : zoom), cv = blank(Math.round(px * res)); if (cv.style) cv.style.width = cv.style.height = px * zoom + "px"; const x = ctxOf(cv); x.scale((px * res) / 100, (px * res) / 100); x.beginPath(); x.arc(50, 50, 49, 0, TAU); x.clip(); paint(x, id, 50, 50, 84, px / 100, res, opt); return cv; }
export interface StatusListRow { id: string; zh: string; pol: Polarity; cls: string | null; dot: string | null; kind: StatusKind | "missing"; src: string; topic: string; family: string | null; level: number | null }
/** 給定的狀態（名詞表的順序）各自的圖樣來源（開發頁、紀錄用）。 */
export const list = (ids: readonly string[]): StatusListRow[] => ids.map((id) => { const e = entry(id); return { id, zh: statusName(id), pol: polarityOf(id), cls: clsOf(id), dot: statusLook(id)?.dot_element ?? null, kind: e?.kind ?? "missing", src: e?.src ?? "-", topic: e?.topic ?? "（沒有圖樣）", family: e?.family ?? null, level: e?.level ?? null }; });
