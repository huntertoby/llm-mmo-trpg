// 狀態圖示與身上特效（Phase 3-36a；畫法移植自 docs/art/sample/fx.js 的 ③ 狀態圖示）。
// QI-3b 起，狀態框裡畫 Q 版圖樣（`qIcon/status.ts` 的 `paint`，第⑤批）：框 → 深底 → 類別底色（`control_group`：硬控黃、移動藍、心智紫，
// `CLASS_BG`）→ 框線 → 圖樣（自帶本色，整數裝置像素貼上）。外框由 `polarity`、身上特效由 `skip_turn`／`removed_by_element`／`absorbs_damage`／
// `prevents_move`／持續傷害元素決定——這些欄位都來自 glossary 的 `status_look`，前端不寫死狀態 ID 清單（不認得的狀態畫名稱第一個字）。
// 下面的 `glyphColor`／`CTRL_COLOR`／`OWN_COLOR`／`POL_COLOR`／`GLYPH`／`drawGlyph` 是舊的單色線條圖樣：狀態框不再用，
// 留給技能部件圓片 32 種以外的狀態（`skillParts.ts` 的 `QP.hooks.status`、`statusColor`）與召喚物頭頂（`qSummon.ts`）。
// 快取鍵用級距（尺寸、內部解析度、極性、控制類別…），不用原始比例。
import type { StatusLook } from "../api/types";
import { statusLook, statusName } from "../battle/glossary";
import { FONT } from "./labels";
import { elementColor } from "./palette";
import { blank, ctxOf, ICON_RES, qCanvasAvailable } from "./qIcon/core";
import { entry as qStatusEntry, paint as qStatusPaint } from "./qIcon/status";
import type { Ctx } from "./skillGlyphs";
import { FRAME_COLOR, framePath, polarityOf, STATUS_BASE_BG, type Polarity } from "./statusFrame";

// 框（極性、框形、框色、深底）在 `statusFrame.ts`（QI-3a 搬出，值與行為不變），這裡 re-export。
export { FRAME_COLOR, framePath, polarityOf, STATUS_BASE_BG, type Polarity };

const TAU = Math.PI * 2;

/** 舊圖樣色（部件圓片用）：控制類依 control_group。狀態框的類別色改成框底色（`qIcon/status.ts` 的 `CLASS_BG`）。 */
export const CTRL_COLOR: Readonly<Record<string, string>> = { hard: "#ffd84a", movement: "#6ac8ff", mental: "#c890ff" };
const POL_COLOR: Readonly<Record<Polarity, string>> = { buff: "#7dffb0", debuff: "#ff8a8a", neutral: "#e8d8a8" };
/** 少數保留自己顏色的狀態（原本的辨識度；圖樣查表的一部分）。 */
const OWN_COLOR: Readonly<Record<string, string>> = {
  time_bomb: "#ffb03a",
  shielded: "#8ac8ff",
  guarded: "#8ac8ff",
  stoneskin: "#c8a060", // 石膚（3-54b）：大地的土色
  defending: "#8ac8ff",
  entangled: "#6ac8ff", // 纏繞（3I-1）：移動減少，不算控制類別，但用移動控制的藍
  regenerating: "#7dffb0",
  undying: "#ff8a9a",
  soul_link: "#c8a0ff",
  revealed: "#ffd04a",
  marked: "#ff6a4a",
  overwatch: "#ffd04a",
  infused_fire: "#ff6a1a", // 臨時附魔（3I-6）：武器上纏著該元素的色
  infused_holy: "#ffe9a0",
};

/** 舊圖樣顏色（部件圓片 `skillParts.statusColor` 用；狀態框不再用）：`control_group` → 持續傷害元素 → 專屬色 → `polarity`。 */
export function glyphColor(id: string | null | undefined): string {
  const look = id == null ? undefined : statusLook(id);
  const ctrl = look?.control_group;
  if (ctrl != null) {
    const c = CTRL_COLOR[ctrl];
    if (c !== undefined) return c;
  }
  if (look?.dot_element != null) return elementColor(look.dot_element);
  return (id == null ? undefined : OWN_COLOR[id]) ?? POL_COLOR[polarityOf(id)];
}

// ---- 圖樣（中心 (0,0)、半徑約 10；顏色已設在 fill/stroke）----

function line(c: Ctx, pts: ReadonlyArray<readonly [number, number]>): void {
  c.beginPath();
  pts.forEach(([px, py], i) => (i > 0 ? c.lineTo(px, py) : c.moveTo(px, py)));
  c.stroke();
}
function circle(c: Ctx, x: number, y: number, r: number, fill = false): void {
  c.beginPath();
  c.arc(x, y, r, 0, TAU);
  if (fill) c.fill();
  else c.stroke();
}
function shield(c: Ctx): void {
  c.beginPath();
  c.moveTo(0, -9);
  c.lineTo(8, -6);
  c.quadraticCurveTo(8, 5, 0, 10);
  c.quadraticCurveTo(-8, 5, -8, -6);
  c.closePath();
  c.stroke();
}
function arrow(c: Ctx, x: number, y: number, up: boolean): void {
  const s = up ? -1 : 1;
  line(c, [[x, y - 5 * s], [x, y + 5 * s]]);
  line(c, [[x - 4, y - 1 * s], [x, y - 5 * s], [x + 4, y - 1 * s]]);
}
function eye(c: Ctx, open: boolean): void {
  c.beginPath();
  c.moveTo(-10, 0);
  c.quadraticCurveTo(0, -9, 10, 0);
  c.quadraticCurveTo(0, 9, -10, 0);
  c.stroke();
  if (open) circle(c, 0, 0, 3.5, true);
}
function star(c: Ctx, x: number, y: number, r: number): void {
  c.beginPath();
  for (let i = 0; i < 10; i++) {
    const rad = i % 2 === 1 ? r * 0.45 : r;
    const a = (i / 10) * TAU - Math.PI / 2;
    c.lineTo(x + Math.cos(a) * rad, y + Math.sin(a) * rad);
  }
  c.closePath();
  c.fill();
}
function flame(c: Ctx, x: number, y: number, h: number): void {
  c.beginPath();
  c.moveTo(x, y - h);
  c.quadraticCurveTo(x + h * 0.6, y - h * 0.2, x + h * 0.35, y + h * 0.3);
  c.quadraticCurveTo(x, y + h * 0.5, x - h * 0.35, y + h * 0.3);
  c.quadraticCurveTo(x - h * 0.6, y - h * 0.2, x, y - h);
  c.fill();
}
function drop(c: Ctx, x: number, y: number, s: number): void {
  c.beginPath();
  c.moveTo(x, y - s);
  c.quadraticCurveTo(x + s * 0.8, y + s * 0.2, x, y + s * 0.7);
  c.quadraticCurveTo(x - s * 0.8, y + s * 0.2, x, y - s);
  c.fill();
}
function sword(c: Ctx): void {
  line(c, [[-6, 7], [6, -7]]);
  line(c, [[-7, 2], [-2, 7]]);
}

type Glyph = (c: Ctx) => void;

// 3W-2b 的元素姿態（`stance_<元素>_<級>`，每個元素 5 級）：劍＋該元素的小記號＋底下 N 顆級數點。
// 顏色仍走 polarity／持續元素（不另設）。
const STANCE_ELEMENTS = ["physical", "fire", "ice", "lightning", "poison", "wind", "earth", "holy", "shadow"] as const;
const STANCE_LEVELS = 5;

function elementMark(c: Ctx, element: string): void {
  switch (element) {
    case "fire":
      c.beginPath();
      c.arc(7, -5, 3, 0, TAU);
      c.fill();
      break;
    case "ice":
      line(c, [[4, -5], [10, -5]]);
      line(c, [[7, -8], [7, -2]]);
      break;
    case "lightning":
      line(c, [[5, -9], [8, -5], [5, -4], [8, 0]]);
      break;
    case "poison":
      c.beginPath();
      c.arc(7, -4, 2.5, 0, TAU);
      c.stroke();
      break;
    case "wind":
      line(c, [[3, -7], [10, -7]]);
      line(c, [[4, -3], [9, -3]]);
      break;
    case "earth":
      c.strokeRect(4, -9, 6, 6);
      break;
    case "holy":
      line(c, [[7, -9], [7, -1]]);
      line(c, [[3, -5], [11, -5]]);
      break;
    case "shadow":
      c.beginPath();
      c.arc(7, -5, 3.5, Math.PI * 0.5, Math.PI * 1.5);
      c.stroke();
      break;
    default:
      break;
  }
}

function elementStanceGlyphs(): Record<string, Glyph> {
  const out: Record<string, Glyph> = {};
  for (const element of STANCE_ELEMENTS) {
    for (let level = 1; level <= STANCE_LEVELS; level++) {
      out[`stance_${element}_${level}`] = (c) => {
        line(c, [[-8, 5], [4, -7]]);
        line(c, [[-9, 0], [-4, 5]]);
        elementMark(c, element);
        for (let i = 0; i < level; i++) {
          c.beginPath();
          c.arc(-8 + i * 4, 10, 1.2, 0, TAU);
          c.fill();
        }
      };
    }
  }
  return out;
}

/** 一個狀態一個圖樣（圖樣查表；不認得的狀態畫名稱第一個字）。 */
export const GLYPH: Readonly<Record<string, Glyph>> = {
  ...elementStanceGlyphs(),
  defending: (c) => shield(c),
  guarded: (c) => {
    shield(c);
    arrow(c, 0, 0.5, false); // 盾＋↓（受傷減少）
  },
  stoneskin: (c) => {
    // 石膚（3-54b）：盾＋岩石的裂紋（受物理傷害減少、移動變慢）
    shield(c);
    line(c, [[-3, -4], [0, -1], [-2, 2], [1, 5]]);
    line(c, [[0, -1], [4, 0]]);
  },
  // 3W-2b：帶附帶效果的護盾（顏色走 polarity，圖樣在盾上加一個小記號）
  shielded_thorns: (c) => {
    shield(c);
    line(c, [[-3, 2], [0, -3], [3, 2]]);
  },
  shielded_mending: (c) => {
    shield(c);
    line(c, [[0, -4], [0, 4]]);
    line(c, [[-4, 0], [4, 0]]);
  },
  shielded_wet: (c) => {
    shield(c);
    c.beginPath();
    c.arc(0, 1, 2.5, 0, TAU);
    c.stroke();
  },
  shielded_marking: (c) => {
    shield(c);
    c.beginPath();
    c.arc(0, 0, 3, 0, TAU);
    c.fill();
  },
  shielded_charged: (c) => {
    shield(c);
    line(c, [[1, -4], [-2, 0], [2, 0], [-1, 4]]);
  },
  shielded: (c) => {
    circle(c, 0, 0, 9); // 泡泡（吸收量）
    c.globalAlpha *= 0.35;
    c.fill();
    c.globalAlpha /= 0.35;
    c.beginPath();
    c.arc(0, 0, 5, Math.PI * 1.1, Math.PI * 1.55);
    c.strokeStyle = "#ffffff";
    c.stroke();
  },
  prone: (c) => {
    circle(c, -6, 3, 3, true);
    line(c, [[-2, 4], [9, 4]]);
    line(c, [[-10, 8], [10, 8]]);
  },
  burning: (c) => flame(c, 0, 1, 10),
  poison: (c) => {
    drop(c, 0, 0, 10);
    c.fillStyle = "#1a2a10";
    c.beginPath();
    c.arc(-2, 2, 2, 0, TAU);
    c.arc(3, -1, 1.4, 0, TAU);
    c.fill();
  },
  bleed: (c) => {
    drop(c, -3, -1, 7);
    drop(c, 5, 3, 5);
  },
  concealed: (c) => {
    c.globalAlpha *= 0.55;
    circle(c, 0, -4, 4, true);
    c.beginPath();
    c.moveTo(-8, 9);
    c.quadraticCurveTo(0, -2, 8, 9);
    c.fill();
    c.globalAlpha /= 0.55;
    line(c, [[-9, 9], [9, -9]]);
  },
  revealed: (c) => {
    eye(c, true);
    line(c, [[-9, -9], [-5, -6]]);
    line(c, [[9, -9], [5, -6]]);
    line(c, [[0, -10], [0, -7]]);
  },
  overwatch: (c) => {
    circle(c, 0, 0, 7); // 狙擊鏡
    line(c, [[0, -10], [0, -4]]);
    line(c, [[0, 4], [0, 10]]);
    line(c, [[-10, 0], [-4, 0]]);
    line(c, [[4, 0], [10, 0]]);
    circle(c, 0, 0, 1.8, true);
  },
  marked: (c) => {
    line(c, [[-7, -7], [7, 7]]); // 靶心叉
    line(c, [[7, -7], [-7, 7]]);
    circle(c, 0, 0, 9);
  },
  time_bomb: (c) => {
    circle(c, -1, 2, 7, true);
    line(c, [[3, -4], [7, -9]]);
    c.fillStyle = "#fff";
    star(c, 8, -9, 3);
  },
  charging: (c) => {
    circle(c, 0, 0, 8);
    circle(c, 0, 0, 3.5, true);
  },
  // 碎晶（Phase 5A-M1，碎晶傀儡倒下時留下導電的水）：碎片＋水滴，只用既有筆畫
  shard_burst: (c) => {
    star(c, -4, -4, 4);
    star(c, 5, -2, 3);
    drop(c, 0, 5, 5);
  },
  // 劍陣（Phase 5A-M2，陣法範圍加成）：三把並排的劍，只用既有筆畫
  sword_formation: (c) => {
    for (const x of [-6, 0, 6]) {
      line(c, [[x, -9], [x, 6]]);
      line(c, [[x - 2.5, 3], [x + 2.5, 3]]);
    }
  },
  // 護陣（Phase 5A-M2b，陣眼石靈：附近同門減傷）：一圈外框裡一個實心圓，只用既有筆畫
  array_ward: (c) => {
    circle(c, 0, 0, 8.5);
    circle(c, 0, 0, 3, true);
  },
  // 誓約之力（Phase 5C-3，依難度 1～3 個點）：一顆星＋下方的點，只用既有筆畫
  oath_bonus_easy: (c) => {
    star(c, 0, -2, 6);
    circle(c, 0, 8, 1.5, true);
  },
  oath_bonus_medium: (c) => {
    star(c, 0, -2, 6);
    circle(c, -3, 8, 1.5, true);
    circle(c, 3, 8, 1.5, true);
  },
  oath_bonus_hard: (c) => {
    star(c, 0, -2, 6);
    for (const x of [-5, 0, 5]) circle(c, x, 8, 1.5, true);
  },
  // 破誓（Phase 5C-3，違反誓約）：一顆星被斜線劃掉
  oath_broken: (c) => {
    star(c, 0, 0, 6);
    line(c, [[-8, 8], [8, -8]]);
  },
  // 鎖霧大陣（Phase 5F-2，雲頂觀陣眼：霧鎖真人減傷）：護陣的雙圈，只用既有筆畫
  summit_array_ward: (c) => {
    circle(c, 0, 0, 8.5);
    circle(c, 0, 0, 5);
    circle(c, 0, 0, 2, true);
  },
  // 歸一（Phase 5F-2，霧鎖真人第 3 階段：每回合回血）：一滴水落進圓心，只用既有筆畫
  mist_return: (c) => {
    circle(c, 0, 2, 7.5);
    drop(c, 0, -2, 5);
  },
  // 開場休戰（Phase 5F-4b，循環賽第 1 輪不受、也不造成傷害）：圓裡的暫停符號，只用既有筆畫
  league_truce: (c) => {
    circle(c, 0, 0, 8.5);
    line(c, [[-3, -4.5], [-3, 4.5]]);
    line(c, [[3, -4.5], [3, 4.5]]);
  },
  // 源晶共鳴（Phase 5F-3，源晶柱：碎晶之主不受骰值傷害）：圓框裡一塊菱形晶體，只用既有筆畫
  rift_resonance: (c) => {
    circle(c, 0, 0, 8.5);
    line(c, [[0, -6], [4, 0], [0, 6], [-4, 0], [0, -6]]);
  },
  // 灌注源晶（Phase 5F-3b，三柱階段碎晶之主造成的傷害降低）：菱形晶體＋往外的三道細線，只用既有筆畫
  rift_channel: (c) => {
    line(c, [[0, -5], [3.5, 0], [0, 5], [-3.5, 0], [0, -5]]);
    line(c, [[0, -6.5], [0, -9.5]]);
    line(c, [[-5, 4], [-8, 6.5]]);
    line(c, [[5, 4], [8, 6.5]]);
  },
  // 晶能湧動／狂湧（Phase 5F-3，留下的柱子傷害提高）：菱形晶體＋下方 1～2 個點
  crystal_surge: (c) => {
    line(c, [[0, -8], [5, -1], [0, 6], [-5, -1], [0, -8]]);
    circle(c, 0, 9, 1.5, true);
  },
  crystal_surge_2: (c) => {
    line(c, [[0, -8], [5, -1], [0, 6], [-5, -1], [0, -8]]);
    circle(c, -3, 9, 1.5, true);
    circle(c, 3, 9, 1.5, true);
  },
  // 界崩（Phase 5F-3，第 18 輪起傷害加倍）：碎成兩半的菱形
  rift_collapse: (c) => {
    line(c, [[-1, -8], [-6, 0], [-1, 8]]);
    line(c, [[1, -8], [6, 0], [1, 8]]);
    line(c, [[0, -6], [2, -1], [-2, 2], [0, 6]]);
  },
  // 熔核爆裂（Phase 5F-5a，熔岩獸倒下時留下火）：碎片＋火苗，只用既有筆畫
  molten_burst: (c) => {
    star(c, -5, -4, 3.5);
    star(c, 5, -4, 3.5);
    flame(c, 0, 4, 7);
  },
  // 殼縫熔核（Phase 5F-5b，灰燼之心戰的殼縫餘燼蜥：同熔核爆裂、傷害倍率另調）：殼的弧線＋火苗
  heart_ember_burst: (c) => {
    line(c, [[-8, -2], [-5, -7], [0, -8.5], [5, -7], [8, -2]]);
    star(c, 0, -3, 3);
    flame(c, 0, 4, 7);
  },
  // 寒燼爆裂（Phase 5F-5a，寒燼蜥倒下時留下冰面）：碎片＋雪花的三條線
  frost_ember_burst: (c) => {
    star(c, -5, -5, 3.5);
    star(c, 5, -5, 3.5);
    for (let i = 0; i < 3; i++) {
      const a = (i / 3) * Math.PI;
      line(c, [[Math.cos(a) * -5, 4 + Math.sin(a) * -5], [Math.cos(a) * 5, 4 + Math.sin(a) * 5]]);
    }
  },
  // 熔殼（Phase 5F-5a，灰燼之心第 1 階段：受到的傷害降低、被冰打碎）：圓殼裡一團火
  molten_shell: (c) => {
    circle(c, 0, 0, 8.5);
    flame(c, 0, 2, 7);
  },
  // 硬殼（Phase 5F-5a，詞綴硬殼的：開場 2 回合傷害減半）：兩層弧形外殼
  hard_shell: (c) => {
    line(c, [[-8, 4], [-5, -4], [0, -7], [5, -4], [8, 4]]);
    line(c, [[-5, 6], [-3, 0], [0, -2], [3, 0], [5, 6]]);
  },
  // 連心（Phase 5A-M2，把傷害分給相鄰同伴）：兩個圓以一條線相連
  heart_link: (c) => {
    circle(c, -5, 0, 4);
    circle(c, 5, 0, 4);
    line(c, [[-1, 0], [1, 0]]);
  },
  slow: (c) => {
    circle(c, 0, 0, 8.5);
    line(c, [[0, 0], [0, -6]]);
    line(c, [[0, 0], [4, 3]]);
  },
  root: (c) => {
    line(c, [[0, -9], [0, 4]]);
    line(c, [[0, 4], [-7, 9]]);
    line(c, [[0, 4], [7, 9]]);
    line(c, [[0, 1], [-5, -3]]);
  },
  stun: (c) => {
    star(c, -5, -3, 5);
    star(c, 5, -3, 5);
    star(c, 0, 5, 5);
  },
  frozen: (c) => {
    for (let i = 0; i < 3; i++) {
      const a = (i / 3) * Math.PI;
      line(c, [[Math.cos(a) * -10, Math.sin(a) * -10], [Math.cos(a) * 10, Math.sin(a) * 10]]);
    }
    circle(c, 0, 0, 2.5, true);
  },
  weaken: (c) => {
    sword(c);
    arrow(c, 6, 3, false);
  },
  empowered: (c) => {
    line(c, [[-8, 0], [0, -8], [8, 0]]); // 雙箭頭↑（全屬性提升）
    line(c, [[-8, 8], [0, 0], [8, 8]]);
  },
  commanding: (c) => {
    line(c, [[-9, 9], [-1, -1]]); // 號令（BAL-19f）：指揮棒＋召喚物（小圓）＋↑（召喚物傷害提高）
    circle(c, -3, -5, 2.4, true);
    circle(c, 3, 5, 3.5);
    arrow(c, 8, -3, true);
  },
  infused_fire: (c) => {
    sword(c); // 臨時附魔（3I-6）：劍＋火星
    circle(c, 7, -7, 2.8, true);
    circle(c, -7, 7, 1.6, true);
  },
  infused_holy: (c) => {
    sword(c); // 劍＋十字光
    line(c, [[7, -10], [7, -4]]);
    line(c, [[4, -7], [10, -7]]);
  },
  race_adapt: (c) => {
    line(c, [[-9, 0], [7, 0]]); // 人類種族技「應變」（3R-2）：向前的箭頭（不被藉機攻擊）
    line(c, [[2, -6], [8, 0], [2, 6]]);
    line(c, [[-9, -6], [-4, -6]]);
    line(c, [[-9, 6], [-4, 6]]);
  },
  race_stonewall: (c) => {
    shield(c); // 矮人種族技「穩若磐石」（3R-2）：盾＋底下的岩塊（不被推、拉、擊倒）
    line(c, [[-6, 8], [6, 8]]);
    line(c, [[-3, 5], [3, 5]]);
  },
  rallied: (c) => {
    line(c, [[-6, 10], [-6, -9]]); // 戰旗
    c.beginPath();
    c.moveTo(-6, -9);
    c.lineTo(8, -5);
    c.lineTo(-6, -1);
    c.closePath();
    c.fill();
  },
  vulnerable: (c) => {
    shield(c); // 裂開的盾
    line(c, [[-2, -8], [2, -2], [-2, 2], [2, 9]]);
  },
  entangled: (c) => {
    c.beginPath(); // 纏繞（鞭，3I-1）：繞兩圈的繩＋往下的箭頭（移動減少）
    c.moveTo(-9, -6);
    c.bezierCurveTo(-2, -12, 6, -2, -1, 0);
    c.bezierCurveTo(-8, 2, 0, 8, 9, 2);
    c.stroke();
    arrow(c, -5, 5, false);
  },
  armor_broken: (c) => {
    c.beginPath(); // 胸甲＋↓
    c.moveTo(-8, -6);
    c.lineTo(0, -9);
    c.lineTo(8, -6);
    c.lineTo(8, 1);
    c.lineTo(0, 9);
    c.lineTo(-8, 1);
    c.closePath();
    c.stroke();
    arrow(c, 0, 0, false);
  },
  hasted: (c) => {
    line(c, [[-8, -7], [-1, 0], [-8, 7]]);
    line(c, [[1, -7], [8, 0], [1, 7]]);
  },
  regenerating: (c) => {
    c.fillRect(-2.5, -9, 5, 18);
    c.fillRect(-9, -2.5, 18, 5);
  },
  undying: (c) => {
    c.beginPath();
    c.moveTo(0, 9);
    c.bezierCurveTo(-12, 0, -6, -10, 0, -4);
    c.bezierCurveTo(6, -10, 12, 0, 0, 9);
    c.fill();
    c.fillStyle = "#000";
    c.fillRect(-1, -4, 2, 9);
    c.fillRect(-3.5, -1.5, 7, 2);
  },
  soul_link: (c) => {
    circle(c, -4, 0, 5.5);
    circle(c, 4, 0, 5.5);
  },
  taunted: (c) => {
    circle(c, 0, 0, 9);
    circle(c, 0, 0, 4.5);
    circle(c, 0, 0, 1.5, true);
  },
  feared: (c) => {
    c.font = `bold 17px ${FONT}`;
    c.textAlign = "center";
    c.textBaseline = "middle";
    c.fillText("!", 0, 1);
    line(c, [[-8, -6], [-5, -3]]);
    line(c, [[8, -6], [5, -3]]);
  },
  overdrawn: (c) => {
    // 透支（3-50）：下回合少 1 AP——空掉的電池＋↓
    c.beginPath();
    c.roundRect(-8, -6, 14, 12, 2);
    c.stroke();
    line(c, [[6, -2], [9, -2], [9, 2], [6, 2]]);
    arrow(c, -1, 0, false);
  },
  silenced: (c) => {
    c.beginPath();
    c.roundRect(-9, -7, 18, 12, 4);
    c.stroke();
    c.beginPath();
    c.moveTo(-3, 5);
    c.lineTo(-6, 10);
    c.lineTo(2, 5);
    c.stroke();
    line(c, [[-10, 9], [10, -9]]);
  },
  blinded: (c) => {
    eye(c, false);
    line(c, [[-9, 7], [9, -7]]);
  },
  stance_fury: (c) => {
    for (const dx of [-5, 0, 5]) line(c, [[dx - 3, 8], [dx + 3, -8]]); // 爪痕
  },
  stance_bulwark: (c) => {
    c.fillRect(-8, -2, 16, 10); // 城垛
    for (const dx of [-8, -2, 4]) c.fillRect(dx, -7, 4, 5);
  },
  // 3W-4b 的姿態狀態：顏色走 polarity／持續元素，圖樣在這裡
  stance_guard: (c) => {
    // 堅守：盾牌
    c.beginPath();
    c.moveTo(-8, -8);
    c.lineTo(8, -8);
    c.lineTo(8, 1);
    c.lineTo(0, 10);
    c.lineTo(-8, 1);
    c.closePath();
    c.stroke();
  },
  stance_bastion: (c) => {
    // 堡壘：雙層磚牆
    c.strokeRect(-9, -8, 18, 16);
    line(c, [[-9, -2], [9, -2]]);
    line(c, [[-9, 4], [9, 4]]);
    line(c, [[0, -8], [0, -2]]);
  },
  stance_ironwall: (c) => {
    // 鐵壁：磚牆
    c.strokeRect(-9, -7, 18, 14);
    line(c, [[-9, 0], [9, 0]]);
    line(c, [[-3, -7], [-3, 0]]);
    line(c, [[3, 0], [3, 7]]);
  },
  stance_flame: (c) => {
    // 焰刃：劍＋火苗
    line(c, [[-7, 8], [7, -8]]);
    line(c, [[-9, 3], [-3, 9]]);
    c.beginPath();
    c.arc(7, 6, 3, 0, TAU);
    c.fill();
  },
  stance_blaze: (c) => {
    // 烈焰：大火焰
    c.beginPath();
    c.moveTo(0, -10);
    c.quadraticCurveTo(9, -1, 6, 6);
    c.quadraticCurveTo(0, 12, -6, 6);
    c.quadraticCurveTo(-8, 0, -2, -4);
    c.quadraticCurveTo(-1, -7, 0, -10);
    c.closePath();
    c.stroke();
  },
  stance_frost: (c) => {
    // 霜刃：劍＋小雪花
    line(c, [[-7, 8], [7, -8]]);
    line(c, [[3, 4], [9, 4]]);
    line(c, [[6, 1], [6, 7]]);
  },
  stance_glacier: (c) => {
    // 冰川：雪花
    for (const [x, y] of [[0, 9], [8, 4.5], [8, -4.5]] as const) line(c, [[-x, -y], [x, y]]);
  },
};

/** 在以 (0,0) 為中心、半徑約 10 的範圍畫狀態圖樣（顏色與線寬由呼叫端設）；不認得的狀態畫名稱第一個字。 */
export function drawGlyph(c: Ctx, id: string | null | undefined): void {
  const known = id == null ? undefined : GLYPH[id];
  if (known !== undefined) {
    known(c);
    return;
  }
  const name = id == null || id === "" ? "?" : statusName(id);
  c.font = `bold 13px ${FONT}`;
  c.textAlign = "center";
  c.textBaseline = "middle";
  c.fillText([...name][0] ?? "?", 0, 1);
}

/**
 * 畫一個完整的狀態圖示（QI-3b：現行的框＋Q 版圖樣，`qIcon/status.ts` 的 `paint`），中心 (cx, cy)、框邊長 `size`（ctx 的單位）。
 * `unitPx`＝ctx 的 1 單位是幾個 CSS px、`res`＝每 CSS px 幾個裝置像素（框線寬、`fitK`、整數像素貼圖要用；選填，舊呼叫照樣成立）。
 * 流程：框 → 深底 → 類別底色 → 框線 → 圖樣（不認得的畫名稱第一個字，米白）。
 */
export function paintStatusIcon(ctx: Ctx, id: string | null | undefined, cx: number, cy: number, size: number, unitPx = 1, res: number = ICON_RES): void {
  qStatusPaint(ctx, id, cx, cy, size, unitPx, res);
}

// ---- 快取 ----

const iconCache = new Map<string, HTMLCanvasElement>();

/** 字型載入後（`fontLoad`）清掉，讓「名稱第一個字」用正確的字型重畫。 */
export function clearStatusIconCache(): void {
  iconCache.clear();
}
export const statusIconCacheSize = (): number => iconCache.size;

/** 頭頂狀態圖示的快取鍵（QI-3b 加 `res`）。 */
export function statusIconKey(id: string, size: number, res: number = ICON_RES): string {
  return `${lookKey(id)}|${size}|${res}`;
}

function lookKey(id: string): string {
  const l = statusLook(id);
  // 沒有 Q 版圖樣的（不認得）畫名稱第一個字：字會變，放進鍵
  const first = qStatusEntry(id) === null ? ([...statusName(id)][0] ?? "?") : "";
  return `${id}|${l?.polarity ?? "-"}|${l?.control_group ?? "-"}|${l?.dot_element ?? "-"}|${first}`;
}

/**
 * 一個狀態圖示的離屏 canvas（邊長 `size` CSS px，畫布 `round(size × res)`；框邊長 `size − 2`、`unitPx` 1）；沒有畫布時回傳 `null`。
 * 戰場頭頂 `ROW_ICON_FEET`（11）＝框 9：染底的不包外框、四周留 1 裝置像素底色圈（`qIcon/status.ts` 的 `tintInset`）。
 */
export function statusIconCanvas(id: string, size: number, res: number = ICON_RES): HTMLCanvasElement | null {
  if (!qCanvasAvailable()) return null;
  const key = statusIconKey(id, size, res);
  const hit = iconCache.get(key);
  if (hit !== undefined) return hit;
  const canvas = blank(Math.round(size * res));
  const ctx = ctxOf(canvas);
  ctx.scale(res, res);
  paintStatusIcon(ctx, id, size / 2, size / 2, size - 2, 1, res);
  iconCache.set(key, canvas);
  return canvas;
}

// ---- 頭頂狀態列 ----

/** 戰場上的排序：硬控 → 移動／心智控制 → 持續傷害 → 其他減益 → 增益 → 中性。同級依 ID 排序（與輸入順序無關）。 */
export function statusRank(id: string): number {
  const l = statusLook(id);
  if (l?.control_group === "hard") return 0;
  if (l?.control_group != null) return 1;
  if (l?.dot_element != null) return 2;
  const pol = polarityOf(id);
  if (pol === "debuff") return 3;
  if (pol === "buff") return 4;
  return 5;
}

export function sortStatuses(ids: readonly string[]): string[] {
  return [...new Set(ids)].sort((a, b) => statusRank(a) - statusRank(b) || (a < b ? -1 : a > b ? 1 : 0));
}

export const ROW_ICON = 14;
/** 狀態列最多顯示的格數（含「+N」）。 */
export const ROW_SLOTS = 3;

export type RowItem = { kind: "icon"; id: string; x: number } | { kind: "more"; extra: number; x: number };

/**
 * 頭頂狀態列的排版（相對列中心的 x）：最多 `slots` 格；超過時顯示 `slots - 1` 個圖示加「+N」。
 * 0 個狀態回傳空陣列。
 */
export function statusRowLayout(ids: readonly string[], slots = ROW_SLOTS, size = ROW_ICON): RowItem[] {
  const sorted = sortStatuses(ids);
  const shown = sorted.slice(0, sorted.length > slots ? slots - 1 : slots);
  const extra = sorted.length - shown.length;
  const gap = size + 1;
  const n = shown.length + (extra > 0 ? 1 : 0);
  const items: RowItem[] = [];
  let x = -((n - 1) * gap) / 2;
  for (const id of shown) {
    items.push({ kind: "icon", id, x });
    x += gap;
  }
  if (extra > 0) items.push({ kind: "more", extra, x });
  return items;
}

// ---- 身上特效 ----

/** 身上特效的描述（只有 5 類，依欄位決定）；也是特效貼圖的快取鍵來源。 */
export interface BodyEffects {
  /** `skip_turn` 且 `removed_by_element` 含 fire：冰塊罩全身。 */
  frozen: boolean;
  /** 其他 `skip_turn`：頭上轉圈星星。 */
  stunned: boolean;
  /** `absorbs_damage`：淡藍泡泡。 */
  absorb: boolean;
  /** `prevents_move`：腳下藤蔓。 */
  noMove: boolean;
  /** `on_turn_start_damage` 的元素（去重、依狀態 ID 排序、最多 2 種）。 */
  dots: string[];
}

export function bodyEffects(ids: readonly string[]): BodyEffects {
  const looks: StatusLook[] = [...new Set(ids)]
    .sort()
    .map((id) => statusLook(id))
    .filter((l): l is StatusLook => l !== undefined);
  const frozen = looks.some((l) => l.skip_turn && l.removed_by_element.includes("fire"));
  const dots: string[] = [];
  for (const l of looks) if (l.dot_element != null && !dots.includes(l.dot_element)) dots.push(l.dot_element);
  return {
    frozen,
    stunned: !frozen && looks.some((l) => l.skip_turn),
    absorb: looks.some((l) => l.absorbs_damage),
    noMove: looks.some((l) => l.prevents_move),
    dots: dots.slice(0, 2),
  };
}

export const hasUnderEffect = (e: BodyEffects): boolean => e.noMove;
export const hasOverEffect = (e: BodyEffects): boolean => e.frozen || e.stunned || e.absorb || e.dots.length > 0;

/** 特效貼圖的快取鍵（級距：只看有哪幾類）。 */
export function effectsKey(e: BodyEffects): string {
  return `${e.frozen ? "F" : ""}${e.stunned ? "S" : ""}${e.absorb ? "A" : ""}${e.noMove ? "R" : ""}|${e.dots.join(",")}`;
}

function rgba(hex: string, a: number): string {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

/** 腳下特效（畫在小人之前）：定身的藤蔓。`cx` 為格子中心、`feet` 為腳底 y。 */
export function bodyUnder(ctx: Ctx, e: BodyEffects, cx: number, feet: number): void {
  if (!e.noMove) return;
  ctx.save();
  ctx.strokeStyle = "#6ac8ff";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.ellipse(cx, feet - 2, 13, 4.5, 0, 0, TAU);
  ctx.stroke();
  ctx.strokeStyle = "#3d8a2a";
  ctx.lineWidth = 2.5;
  for (const s of [-1, 1]) {
    ctx.beginPath();
    ctx.moveTo(cx + s * 12, feet);
    ctx.quadraticCurveTo(cx + s * 14, feet - 10, cx + s * 5, feet - 13);
    ctx.stroke();
  }
  ctx.restore();
}

/** 身上特效（畫在小人之後）：冰塊、星星、泡泡、腳邊粒子。`t` 為星星的轉動角度（弧度）。 */
export function bodyOver(ctx: Ctx, e: BodyEffects, cx: number, feet: number, t = 0, bodyH = 34): void {
  const head = feet - bodyH;
  if (e.frozen) {
    ctx.save();
    ctx.beginPath();
    ctx.roundRect(cx - 15, head - 6, 30, feet - head + 8, 5);
    ctx.fillStyle = rgba("#9fe6ff", 0.42);
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#e8fbff";
    ctx.stroke();
    ctx.strokeStyle = rgba("#ffffff", 0.8);
    ctx.beginPath();
    ctx.moveTo(cx - 10, feet - 4);
    ctx.lineTo(cx - 6, head);
    ctx.stroke();
    ctx.restore();
  }
  if (e.stunned) {
    ctx.save();
    ctx.strokeStyle = rgba("#ffd84a", 0.7);
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.ellipse(cx, head - 2, 14, 4, 0, 0, TAU);
    ctx.stroke();
    ctx.fillStyle = "#ffd84a";
    for (let i = 0; i < 3; i++) {
      const a = t + (i / 3) * TAU;
      star(ctx, cx + Math.cos(a) * 14, head - 2 + Math.sin(a) * 4, 3.6);
    }
    ctx.restore();
  }
  if (e.absorb) {
    ctx.save();
    ctx.beginPath();
    ctx.ellipse(cx, feet - bodyH * 0.6, 19, bodyH * 0.7, 0, 0, TAU);
    const g = ctx.createRadialGradient(cx - 6, feet - bodyH * 0.9, 2, cx, feet - bodyH * 0.6, 24);
    g.addColorStop(0, rgba("#ffffff", 0.18));
    g.addColorStop(1, rgba("#8ac8ff", 0.22));
    ctx.fillStyle = g;
    ctx.fill();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = rgba("#bfe2ff", 0.85);
    ctx.stroke();
    ctx.restore();
  }
  e.dots.forEach((el, k) => dotParticles(ctx, el, k === 0 ? 1 : -1, cx, feet));
}

function dotParticles(ctx: Ctx, el: string, side: number, cx: number, feet: number): void {
  ctx.save();
  ctx.fillStyle = elementColor(el);
  ctx.strokeStyle = "#1a0e06";
  ctx.lineWidth = 1;
  for (let i = 0; i < 2; i++) {
    const px = cx + side * (11 + i * 5);
    const py = feet - 4 - i * 9;
    if (el === "fire") flame(ctx, px, py, 5.5);
    else if (el === "poison") {
      ctx.beginPath();
      ctx.arc(px, py, 2.6 - i * 0.6, 0, TAU);
      ctx.fill();
      ctx.stroke();
    } else drop(ctx, px, py, 4);
  }
  ctx.restore();
}

/** 隱蔽的單位畫成半透明。 */
export const CONCEALED_ALPHA = 0.55;
/** 隱蔽狀態的 ID（和 `TIME_BOMB`、`CHARGING` 一樣是引擎規則直接引用的狀態）。 */
export const CONCEALED = "concealed";
