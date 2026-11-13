// 精英單挑插圖 A「暮色對峙」（320×120；RG-4，照 docs/art/sample/rgUnits.js 第 3 節的 duel／duelCanvas 逐段搬，
// docs/art/RG樣張.md 9.3、9.6 決定 1、9.7／9.7.1、9.8 第 4～7 條，以 9.8 為準）。B「對角徽記」未採用、不搬。
// - 剪影：人形用紙娃娃（Q 版 qDoll 畫法＋剪影外框）在 R 倍離屏畫 → 侵蝕 1.0 單位 → alpha 二值化 >128；主手武器和手之間一道輪廓光縫；
//   斗笠在插圖裡換寬帽緣（SIL_DOULI）＋帽緣下 0.75 寬的縫（戰場 sprite 不換）。異形不侵蝕、二值化 >40，跳過地面環、影子與直接上色的軟特效。
// - 背景：區域天色（SKY 只有雲嶺、荒原，其他區退回雲嶺）＋遠山＋地平線光＋地面暗帶；框 1px #8a6a3a＋內側暗線。
// - 交叉的武器：Q 版武器圖示（`qIcon/weapons.ts` 的圖樣，無框）；異形精英用獸爪（`qIcon/beastClaw.ts`，只在這裡用）。
// 不改共用畫法檔：qStamp 的剪影外框流程在這裡另抄一份（多一個「畫的時候換掉斗笠」的掛勾），qStamp.ts／qNpc.ts／qIcon/weapons.ts 一行不動。
// 確定性：沒有亂數。沒有 DOM 時 `duelCanvas` 回傳 null。
import { mix, Q_OUT, type M6, type QHooks, type QItem, type QPose, type QProbe, type QUnit } from "./qCore";
import { drawQ } from "./qDoll";
import { npcNeedsLayers, setNpcLayers } from "./qNpc";
import { qWeapon } from "./qWeapons";
import { Q_BOX, Q_LINE } from "./qStamp";
import { GAME_HOOKS } from "./qSpec";
import { drawCreature, type ResolvedCreature } from "./inkCreature";
import { render, type QDef } from "./qIcon/core";
import { BEAST_CLAW, paintBeastClaw } from "./qIcon/beastClaw";
import { qResolve, qWeaponDef } from "./qIcon/weapons";
import { resolveGear } from "./gearResolve";

type C2 = CanvasRenderingContext2D;
const OUT = Q_OUT;

export const DUEL_W = 320;
export const DUEL_H = 120;
/** 主角的架式（qDoll 姿勢鍵）：持劍的手往前舉、劍尖朝前上，重心前傾（9.3）。 */
export const HERO_POSE: QPose = { arm: -0.5, wpn: 1.2, lean: 0.05 };
/** 人形的大小（插圖 px／模型單位）：主角 1.9、人形精英 1.9 × 1.15（9.8 第 5 條）。 */
export const HERO_K = 1.9;
export const HUMANOID_ELITE_K = 1.9 * 1.15;
/**
 * 異形精英的大小（依身形 rigKey）：北坡狼王（hound）1.2、熔核領主（beetle）1.8（9.8 第 5 條）。
 * 其他身形還沒有美術給的倍率：先用樣張 `duel()` 的預設 1.5（待美術 PM 逐種確認）。
 */
export const CREATURE_ELITE_K: Readonly<Record<string, number>> = { hound: 1.2, beetle: 1.8 };
export const CREATURE_ELITE_K_DEFAULT = 1.5;

/** 有天色的區域；其他區退回雲嶺（9.3 移植說明）。 */
export const DUEL_SKY = {
  cloud_ridge: { top: "#22363a", mid: "#4f6f6c", glow: "#d8d4b0", far: "#3a5552", near: "#1e2c2a", ground: "#1a2422", haze: "rgba(230,236,232,0.28)" },
  ashen_waste: { top: "#1e1210", mid: "#5a2a1a", glow: "#ff9a4a", far: "#3a1e18", near: "#24140f", ground: "#1c100c", haze: "rgba(255,140,60,0.22)" },
} as const;
export type DuelRegion = keyof typeof DUEL_SKY;
export const duelRegion = (region: string | null | undefined): DuelRegion => (region === "ashen_waste" || region === "cloud_ridge" ? region : "cloud_ridge");

/** 交叉的武器：Q 版武器圖樣（`qWeaponDef` 的結果，看 `meta.diag`）或獸爪。 */
export type DuelWeapon = { kind: "icon"; def: QDef & { meta: { diag: boolean } } } | { kind: typeof BEAST_CLAW };
/** 主角剪影的「道具」（9.9.2：bow／aim／staff 三組）：主手 kind 與剪影用的 Q 版圖示（雙手槍＝手槍圖示，畫兩把）。 */
export interface DuelProp {
  kind: string;
  def: QDef;
}
/** 插圖裡的一個人物：人形（Q 版 unit＋姿勢；prop＝主角走道具剪影）或異形（已解好的外觀＋倍率）。 */
export type DuelFigure = { kind: "doll"; unit: QUnit; pose?: QPose | null; prop?: DuelProp | null } | { kind: "creature"; creature: ResolvedCreature; k: number };
/** 主角的主手（`duelArtPlan.mainWeaponOf` 的 kind；form、material、element 給雙手槍的手槍圖示用）。 */
export interface DuelMain {
  kind: string;
  form?: string | null;
  material?: string | null;
  element?: string | null;
}
/** 錯開組對異形時整組的移動（9.9.10；插圖 px，dx < 0 往左、dy < 0 往上；s＝兩把一起縮放；ok＝主角側夠 3 px）。 */
export interface DuelFit {
  dx: number;
  dy: number;
  s: number;
  ok: boolean;
}

export interface DuelSpec {
  /** main：主手的 kind（決定剪影組、交叉組；沒給＝照劍）。 */
  hero: { unit: QUnit; weapon: DuelWeapon | null; pose?: QPose | null; main?: DuelMain | null };
  elite: { figure: DuelFigure; weapon: DuelWeapon | null };
  region: string | null | undefined;
  /** 紙娃娃的顏色（剪影只看 alpha，顏色不影響結果；開發頁比對時給樣張色）。 */
  hooks?: QHooks;
  /** 開發頁用：錯開組對異形時回報整組移動（沒走 groupFit＝不呼叫）。 */
  onFit?: (fit: DuelFit) => void;
}

// ---------------- 主手不是劍（9.9）：分組表（同樣張 rgUnits.js 第 3b 節的同名常數） ----------------
/** 剪影組：表外＝held（照劍）。 */
export const SIL_GROUP: Readonly<Record<string, "bow" | "aim" | "staff">> = { bow: "bow", crossbow: "aim", longgun: "aim", shotgun: "aim", pistol: "aim", dual_pistol: "aim", staff: "staff" };
export const silGroup = (kind: string | null | undefined): "bow" | "aim" | "staff" | "held" => (kind != null ? SIL_GROUP[kind] : undefined) ?? "held";
/** 交叉組：表外＝blade（照劍）。 */
export const CROSS_GROUP: Readonly<Record<string, "head" | "gun" | "open" | "block">> = { axe: "head", hammer: "head", scythe: "head", staff: "head", longgun: "gun", shotgun: "gun", bow: "open", crossbow: "open", whip: "open", fist: "block", dagger: "block", dual_dagger: "block", pistol: "block", dual_pistol: "block" };
export const crossGroup = (kind: string | null | undefined): "head" | "gun" | "open" | "block" | "blade" => (kind != null ? CROSS_GROUP[kind] : undefined) ?? "blade";
/** 道具（9.9.2 表）：px＝圖示大小、at＝圖示中心相對手心（模型單位，+x 朝敵、−y 往上）、rot＝轉角。 */
export const PROP: Readonly<Record<string, { px: number; at: readonly [number, number]; rot: number }>> = {
  bow: { px: 21, at: [3.5, -0.5], rot: Math.PI / 4 },
  crossbow: { px: 24, at: [5.5, 0.5], rot: Math.PI / 4 - 0.1 },
  longgun: { px: 27, at: [6.5, 0.5], rot: Math.PI / 4 - 0.1 },
  shotgun: { px: 25, at: [6, 0.5], rot: Math.PI / 4 - 0.1 },
  pistol: { px: 17, at: [3.8, -1.4], rot: 0.55 },
  dual_pistol: { px: 17, at: [3.8, -1.4], rot: 0.55 },
  staff: { px: 26, at: [5, -7], rot: -Math.PI / 4 },
};
/** 剪影組的架式（沒給 pose 時用；held＝HERO_POSE）。 */
export const GROUP_POSE: Readonly<Record<string, QPose>> = { bow: { arm: -1.0, wpn: 1.2, lean: 0.05 }, aim: { arm: -1.0, wpn: 1.2, lean: 0.05 }, staff: { arm: -0.95, wpn: 1.2, lean: 0.05 } };
/** 錯開：hero／elite＝[dx, dy]（插圖 px，交叉中心為原點）、k／ek＝圖示倍率；claw＝對異形、man＝對人形（沒寫＝照劍）。 */
interface Face {
  hero: readonly [number, number];
  elite: readonly [number, number];
  k: number;
  ek: number;
}
export const FACE: Readonly<Record<string, { claw?: Face; man?: Face }>> = {
  head: { claw: { hero: [6, -6], elite: [-3, 3], k: 1.05, ek: 1 } },
  gun: { claw: { hero: [-5, 5], elite: [4, -4], k: 1.08, ek: 1 } },
  open: { claw: { hero: [-14, 4], elite: [11, -3], k: 0.92, ek: 0.92 }, man: { hero: [-14, 5], elite: [10, -4], k: 0.8, ek: 0.95 } },
  block: { claw: { hero: [-14, 4], elite: [11, -3], k: 0.88, ek: 0.92 }, man: { hero: [-14, 5], elite: [10, -4], k: 0.8, ek: 0.95 } },
};
/** 同組裡個別 kind 的例外（優先於 FACE）：鞭對人形照劍（不帶 man）、霰彈槍的爪痕劃在槍身中段。 */
export const FACE_KIND: Readonly<Record<string, { claw?: Face; man?: Face }>> = {
  whip: { claw: { hero: [-14, 4], elite: [11, -3], k: 0.92, ek: 0.92 } },
  shotgun: { claw: { hero: [1, -1], elite: [-2, 2], k: 1.08, ek: 1 } },
};
const faceOf = (kind: string | null | undefined): { claw?: Face; man?: Face } | undefined => (kind != null ? FACE_KIND[kind] : undefined) ?? FACE[crossGroup(kind)];

// ---------------- 畫布小工具 ----------------
function canvas(w: number, h: number): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = Math.max(1, Math.ceil(w));
  c.height = Math.max(1, Math.ceil(h));
  return c;
}
const ctx2 = (c: HTMLCanvasElement): C2 => c.getContext("2d") as C2;

/** 圓盤膨脹 r（像素）：12 個方向各做一次 5 步的短線段膨脹（同 qStamp 的外框、樣張 QNpc.dilate）。 */
export function dilate12(src: HTMLCanvasElement, r: number): HTMLCanvasElement {
  const N = 12;
  const a = (r * Math.PI) / (2 * N);
  const P = [canvas(src.width, src.height), canvas(src.width, src.height)];
  let cur: HTMLCanvasElement = src;
  let n = 0;
  for (let i = 0; i < N; i++) {
    const t = (Math.PI * i) / N;
    const ux = Math.cos(t) * a;
    const uy = Math.sin(t) * a;
    const c = P[n++ % 2]!;
    const g = ctx2(c);
    g.clearRect(0, 0, c.width, c.height);
    for (const f of [-1, -0.5, 0, 0.5, 1]) g.drawImage(cur, ux * f, uy * f);
    cur = c;
  }
  return cur;
}
function inverse(src: HTMLCanvasElement): HTMLCanvasElement {
  const c = canvas(src.width, src.height);
  const g = ctx2(c);
  g.fillStyle = "#000";
  g.fillRect(0, 0, c.width, c.height);
  g.globalCompositeOperation = "destination-out";
  g.drawImage(src, 0, 0);
  return c;
}
/** alpha 二值化（> th 變不透明，其餘透明）；就地改。 */
export function hardAlpha(c: HTMLCanvasElement, th: number): HTMLCanvasElement {
  const g = ctx2(c);
  const d = g.getImageData(0, 0, c.width, c.height);
  const q = d.data;
  for (let i = 3; i < q.length; i += 4) q[i] = q[i]! > th ? 255 : 0;
  g.putImageData(d, 0, 0);
  return c;
}
/** 侵蝕 r 像素（反相 → 膨脹 → 反相 → 二值化 >128）。 */
function erode(src: HTMLCanvasElement, r: number): HTMLCanvasElement {
  return hardAlpha(inverse(dilate12(inverse(src), r)), 128);
}
/** 單色副本（不改原圖）。 */
function tinted(src: HTMLCanvasElement, color: string): HTMLCanvasElement {
  const c = canvas(src.width, src.height);
  const g = ctx2(c);
  g.drawImage(src, 0, 0);
  g.globalCompositeOperation = "source-in";
  g.fillStyle = color;
  g.fillRect(0, 0, c.width, c.height);
  return c;
}

// ---------------- 斗笠：插圖剪影專用的寬帽緣（SIL_DOULI） ----------------
/** 剪影時把斗笠的顏色換成這個鑰匙色，畫到第一筆時在同一個變換改畫寬帽緣，原本斗笠的其他筆畫都不畫。 */
const DOULI_KEY = "#ff00fe";
const DOULI_KEY_D = mix(DOULI_KEY, "#000000", 0.22); // qNpc.douli 的暗色 dk(c, 0.22)
const norm = (() => {
  const memo = new Map<string, string>();
  return (c: string): string => {
    let v = memo.get(c);
    if (v === undefined) {
      const g = ctx2(canvas(1, 1));
      g.fillStyle = c;
      v = String(g.fillStyle).toLowerCase();
      memo.set(c, v);
    }
    return v;
  };
})();
/**
 * 寬帽緣的側面斗笠（樣張 SIL_DOULI，9.7 可修 1）：帽緣後 −15.2、前 +16.8、往前低 2、錐頂 −41.6、帽緣下厚 1.2；
 * 前緣比鼻尖多伸 7 單位，帽緣下、臉前面留出缺口。只畫進剪影（顏色不影響結果）。
 */
function silDouliSide(g: C2): void {
  const c = "#c8b07a";
  g.fillStyle = c;
  g.beginPath();
  g.moveTo(-15.2, -35.4);
  g.quadraticCurveTo(-6, -40.6, 0.6, -41.6);
  g.quadraticCurveTo(8, -39.6, 16.8, -33.4);
  g.lineTo(16.4, -32.4);
  g.quadraticCurveTo(0, -34.0, -14.8, -34.4);
  g.closePath();
  g.fill();
  g.fillStyle = mix(c, "#000000", 0.22);
  g.beginPath();
  g.moveTo(16.4, -32.4);
  g.quadraticCurveTo(0, -34.0, -14.8, -34.4);
  g.lineTo(-14.6, -35.0);
  g.quadraticCurveTo(0, -34.8, 16.6, -33.2);
  g.closePath();
  g.fill();
}
/** 包一層 ctx：鑰匙色的第一筆填色改畫寬帽緣，之後鑰匙色（與它的暗色）的填色、描線都不畫。 */
function douliSwap(t: C2): C2 {
  const key = norm(DOULI_KEY);
  const keyD = norm(DOULI_KEY_D);
  let done = false;
  const isKey = (s: unknown): boolean => {
    const v = typeof s === "string" ? s.toLowerCase() : "";
    return v === key || v === keyD;
  };
  return new Proxy(t, {
    get(target, p) {
      if (p === "fill")
        return (...a: unknown[]) => {
          if (!isKey(target.fillStyle)) return Reflect.apply(target.fill, target, a) as unknown;
          target.beginPath();
          if (!done) {
            done = true;
            const keep = target.fillStyle;
            silDouliSide(target);
            target.fillStyle = keep;
          }
          return undefined;
        };
      if (p === "stroke")
        return (...a: unknown[]) => {
          if (!isKey(target.strokeStyle)) return Reflect.apply(target.stroke, target, a) as unknown;
          target.beginPath();
          return undefined;
        };
      const v = Reflect.get(target, p, target) as unknown;
      return typeof v === "function" ? (v as (...x: unknown[]) => unknown).bind(target) : v;
    },
    set(target, p, v) {
      return Reflect.set(target, p, v, target);
    },
  });
}
const hasDouli = (u: QUnit): boolean => u.gear.head?.kind === "douli";
const withDouliKey = (u: QUnit): QUnit => (hasDouli(u) ? { look: u.look, gear: { ...u.gear, head: { ...u.gear.head!, color: DOULI_KEY } } } : u);

// ---------------- 人形：qStamp 的剪影外框流程（另抄一份，多一個斗笠掛勾） ----------------
/** 同 `qStamp`（樣張 QDoll.stamp）：在 (cx, cy) 貼一隻 size 倍、連外框的小人；`silDouli` 時斗笠換寬帽緣。 */
function stampSil(ctx: C2, unit0: QUnit, cx: number, cy: number, size: number, west: boolean, hooks: QHooks, pose: QPose | null, dpr: number): void {
  const sil0 = hasDouli(unit0);
  const unit = sil0 ? withDouliKey(unit0) : unit0;
  const sc = size * dpr;
  const { W, H, FOOT } = Q_BOX;
  // 畫布大小照樣張 QDoll.stamp 直接給小數（瀏覽器取整數部分；qStamp 是無條件進位，差一欄會讓縮回時的取樣不同）
  const off = document.createElement("canvas");
  off.width = W * sc;
  off.height = H * sc;
  const o0 = ctx2(off);
  o0.scale(sc, sc);
  o0.translate(W / 2, H - FOOT);
  if (west) o0.scale(-1, 1);
  const o = sil0 ? douliSwap(o0) : o0;
  let under: HTMLCanvasElement | null = null;
  let over: HTMLCanvasElement | null = null;
  if (npcNeedsLayers(unit)) {
    under = canvas(off.width, off.height);
    over = canvas(off.width, off.height);
    setNpcLayers({ under: ctx2(under), over: ctx2(over) });
    try {
      drawQ(o, unit, "side", hooks, pose, west);
    } finally {
      setNpcLayers(null);
    }
  } else drawQ(o, unit, "side", hooks, pose, west);
  const sil = tinted(off, OUT);
  const k = Q_LINE * sc;
  const dx0 = cx - (W / 2) * size;
  const dy0 = cy - (H - FOOT) * size;
  ctx.save();
  ctx.imageSmoothingEnabled = true;
  if (under) ctx.drawImage(under, dx0, dy0, W * size, H * size);
  if (qWeapon(unit.gear.main_hand)?.kind === "bow") {
    const O = dilate12(sil, k);
    const r = 1.5 * sc;
    const cl = canvas(off.width, off.height);
    const g = ctx2(cl);
    g.drawImage(inverse(dilate12(inverse(dilate12(O, r)), r)), 0, 0);
    g.drawImage(O, 0, 0);
    ctx.drawImage(tinted(cl, OUT), dx0, dy0, W * size, H * size);
  } else ctx.drawImage(tinted(dilate12(sil, k), OUT), dx0, dy0, W * size, H * size);
  ctx.drawImage(off, dx0, dy0, W * size, H * size);
  if (over) ctx.drawImage(over, dx0, dy0, W * size, H * size);
  ctx.restore();
}

/** 只留 drawImage：QCreature 的地面環、影子、直接上色的軟特效（霧團等）全部跳過（樣張 noGround）。 */
function noGround(t: C2): C2 {
  const SKIP = new Set<PropertyKey>(["fill", "stroke", "fillRect", "strokeRect"]);
  return new Proxy(t, {
    get(target, p) {
      if (SKIP.has(p)) return () => undefined;
      const v = Reflect.get(target, p, target) as unknown;
      return typeof v === "function" ? (v as (...x: unknown[]) => unknown).bind(target) : v;
    },
    set(target, p, v) {
      return Reflect.set(target, p, v, target);
    },
  });
}

/** 一張剪影：cv（R 倍內部解析度）的 (0,0) 在插圖座標 (x0, y0)、貼上大小 w×h；seam＝輪廓光縫（沒有＝null）。 */
export interface Sil {
  cv: HTMLCanvasElement;
  seam: HTMLCanvasElement | null;
  x0: number;
  y0: number;
  w: number;
  h: number;
}

/** 單位 → 剪影（樣張 silhouetteOf）：畫在 (cx, foot)、大小 k、res＝插圖的內部解析度。開發頁逐張比對也用（`duelSilhouette`）。 */
export function duelSilhouette(fig: DuelFigure, west: boolean, cx: number, foot: number, k: number, res: number, hooks: QHooks): Sil {
  const W = 160;
  const H = 130;
  const lx = W / 2;
  const ly = H - 10;
  const R = Math.max(3, res * 2); // 內部 R 倍畫（侵蝕、縫在高解析度做），貼上時縮回
  const mk = (): HTMLCanvasElement => canvas(W * R, H * R);
  if (fig.kind === "creature") {
    const cv = mk();
    const g = ctx2(cv);
    g.scale(R, R);
    g.translate(lx, ly);
    g.scale(west ? -k : k, k);
    drawCreature(noGround(g), fig.creature, null, false);
    hardAlpha(cv, 40); // 部件之間的半透明接縫填滿
    return { cv, seam: null, x0: cx - lx, y0: foot - ly, w: W, h: H };
  }
  const pose = fig.pose ?? null;
  const draw = (unit: QUnit): HTMLCanvasElement => {
    const cv = mk();
    const g = ctx2(cv);
    g.scale(R, R);
    stampSil(g, unit, lx, ly, k, west, hooks, pose, R * 1.5);
    return cv;
  };
  // 人形（9.8 第 5 條）：① 侵蝕 1.0 單位去掉外框撐出來的部分；② 拿掉主手再畫一次、相減＝伸出去的武器，往外 0.7 單位落在身體上的那圈＝縫
  const unit = fig.unit;
  const er = 1.0 * k * R;
  if (fig.prop) return propSilhouette(fig.prop, unit, pose, draw, mk, er, west, cx, foot, k, R, lx, ly, W, H, hooks);
  const full = erode(draw(unit), er);
  let seam: HTMLCanvasElement | null = null;
  if (unit.gear.main_hand) {
    const g0 = { ...unit.gear };
    delete g0.main_hand;
    const bare = erode(draw({ look: unit.look, gear: g0 }), er);
    const wpn = mk();
    const wg = ctx2(wpn);
    wg.drawImage(full, 0, 0);
    wg.globalCompositeOperation = "destination-out";
    wg.drawImage(bare, 0, 0);
    seam = mk();
    const sg = ctx2(seam);
    sg.drawImage(dilate12(wpn, 0.7 * k * R), 0, 0);
    sg.globalCompositeOperation = "destination-out";
    sg.drawImage(wpn, 0, 0);
    sg.globalCompositeOperation = "destination-in";
    sg.drawImage(full, 0, 0);
    hardAlpha(seam, 128);
  }
  if (hasDouli(unit)) {
    // 斗笠帽緣下、臉那一側一道縫（模型座標 x 1.5～10.5、y −32.0～−32.5，寬 0.75）：寬帽緣和額頭分開
    seam ??= mk();
    const sg = ctx2(seam);
    const s = west ? -1 : 1;
    sg.save();
    sg.scale(R, R);
    sg.strokeStyle = "#fff";
    sg.lineWidth = 0.75 * k;
    sg.lineCap = "round";
    sg.beginPath();
    sg.moveTo(lx + s * 1.5 * k, ly - 32.0 * k);
    sg.lineTo(lx + s * 10.5 * k, ly - 32.5 * k);
    sg.stroke();
    sg.restore();
    sg.globalCompositeOperation = "destination-in";
    sg.drawImage(full, 0, 0);
  }
  return { cv: full, seam, x0: cx - lx, y0: foot - ly, w: W, h: H };
}

// ---------------- 主手不是劍（9.9.2）：道具剪影 ----------------
/** 載體：拳套（不是雙手武器，手臂照架式往前舉，手上沒有東西伸出去）。 */
const CARRIER: QItem = { slot: "main_hand", kind: "fist", form: "knuckle", material: "iron" };
const QUIVER: QItem = { slot: "back", kind: "quiver", material: "leather" };
/**
 * 載體拿在手上時，手心在 R 倍剪影畫布上的位置（qDoll 的 probe，取 kind `gauntlet` 的第一筆矩陣 (e, f)）。
 * 座標系和剪影同一個：scale(R) → translate(lx, ly) → scale(k)（9.9.5 第 5 條；不在 stampSil 的離屏裡取）。取不到就丟錯（不退回預設）。
 */
function handOf(unit: QUnit, pose: QPose | null, west: boolean, k: number, R: number, lx: number, ly: number, hooks: QHooks): [number, number] {
  let m: M6 | null = null;
  const g = ctx2(canvas(4, 4));
  g.scale(R, R);
  g.translate(lx, ly);
  g.scale(west ? -k : k, k);
  const probe: QProbe = (kind, _h, _t, _v, _o, mm) => {
    if (kind === "gauntlet" && m === null) m = mm;
  };
  const p = { ...(pose ?? {}), probe };
  if (npcNeedsLayers(unit)) {
    setNpcLayers({ under: ctx2(canvas(4, 4)), over: ctx2(canvas(4, 4)) });
    try {
      drawQ(g, unit, "side", hooks, p, west);
    } finally {
      setNpcLayers(null);
    }
  } else drawQ(g, unit, "side", hooks, p, west);
  const hit = m as M6 | null;
  if (hit === null) throw new Error("duelArt: probe 取不到拳套（gauntlet）的手心");
  return [hit.e, hit.f];
}
/** 一把道具（二值化 >128）：手心 → scale(k·R) → at（＋extra）→ rot，圖示 px 模型單位見方。 */
function propCanvas(mk: () => HTMLCanvasElement, prop: DuelProp, hand: readonly [number, number], s: number, west: boolean, extra: readonly [number, number] = [0, 0]): HTMLCanvasElement {
  const P0 = PROP[prop.kind]!;
  const d = Math.round(P0.px * s);
  const ic = render(prop.def, d, 1, {});
  const cv = mk();
  if (ic !== null) {
    const g = ctx2(cv);
    g.translate(hand[0], hand[1]);
    g.scale(west ? -s : s, s);
    g.translate(P0.at[0] + extra[0], P0.at[1] + extra[1]);
    g.rotate(P0.rot);
    g.drawImage(ic, -P0.px / 2, -P0.px / 2, P0.px, P0.px);
  }
  return hardAlpha(cv, 128); // 圖示的半透明光暈、亮點不算進剪影
}
/**
 * 主手 → 剪影的道具：圖示和中間交叉的同一個（`weapon` 的 def）；雙手槍改用手槍圖示（先經 resolveGear 解析再丟 qWeaponDef，9.9.5 第 6 條）。
 * 中間沒有圖示時照主手解析；解析不出圖示就丟錯（不退回 held）。
 */
export function propOf(main: DuelMain, weapon: DuelWeapon | null): DuelProp {
  const dual = main.kind === "dual_pistol";
  let def: QDef | null = !dual && weapon?.kind === "icon" ? weapon.def : null;
  if (def === null) {
    const r = resolveGear({ kind: dual ? "pistol" : main.kind, form: main.form ?? null, material: main.material ?? null, element: main.element ?? null }, "main_hand");
    def = qWeaponDef(qResolve(r, main.element ?? null));
  }
  if (def === null) throw new Error(`duelArt: 主手 ${main.kind} 沒有 Q 版圖示`);
  return { kind: main.kind, def };
}
/** 道具剪影（樣張 propSilhouette）：身體拿載體（弓手另掛箭袋）、侵蝕；道具貼在手心、不侵蝕；縫＝道具往外 0.7 單位落在身體上的那圈。 */
function propSilhouette(
  prop: DuelProp,
  unit0: QUnit,
  pose: QPose | null,
  draw: (u: QUnit) => HTMLCanvasElement,
  mk: () => HTMLCanvasElement,
  er: number,
  west: boolean,
  cx: number,
  foot: number,
  k: number,
  R: number,
  lx: number,
  ly: number,
  W: number,
  H: number,
  hooks: QHooks,
): Sil {
  if (PROP[prop.kind] === undefined) throw new Error(`duelArt: 沒有道具表的主手 ${prop.kind}`);
  const gear = { ...unit0.gear, main_hand: CARRIER };
  if (prop.kind === "bow" && !gear.back) gear.back = QUIVER; // 弓手照紙娃娃背箭袋（箭羽露在後腦旁）
  const carry: QUnit = { look: unit0.look, gear };
  const body = erode(draw(carry), er);
  const hand = handOf(carry, pose, west, k, R, lx, ly, hooks);
  const s = k * R;
  // 雙手槍：遠側那把（往前 1.5、往下 4.5）先畫，近側那把蓋在上面、兩把之間也開縫
  const props = prop.kind === "dual_pistol" ? [propCanvas(mk, prop, hand, s, west, [1.5, 4.5]), propCanvas(mk, prop, hand, s, west)] : [propCanvas(mk, prop, hand, s, west)];
  const seam = mk();
  const sg = ctx2(seam);
  const full = mk();
  const fg = ctx2(full);
  fg.drawImage(body, 0, 0);
  const ring = (p: HTMLCanvasElement, under: HTMLCanvasElement): HTMLCanvasElement => {
    const r = mk();
    const rg = ctx2(r);
    rg.drawImage(dilate12(p, 0.7 * s), 0, 0);
    rg.globalCompositeOperation = "destination-out";
    rg.drawImage(p, 0, 0);
    rg.globalCompositeOperation = "destination-in";
    rg.drawImage(under, 0, 0);
    return r;
  };
  for (const p of props) {
    sg.globalCompositeOperation = "destination-out";
    sg.drawImage(p, 0, 0);
    sg.globalCompositeOperation = "source-over";
    sg.drawImage(ring(p, full), 0, 0);
    fg.drawImage(p, 0, 0);
  }
  hardAlpha(seam, 128);
  return { cv: full, seam, x0: cx - lx, y0: foot - ly, w: W, h: H };
}

// ---------------- 交叉的武器 ----------------
const isDiag = (w: DuelWeapon): boolean => (w.kind === BEAST_CLAW ? true : w.def.meta.diag);
function weaponCanvas(w: DuelWeapon, px: number, res: number): HTMLCanvasElement {
  const cv = canvas(Math.round(px * res), Math.round(px * res));
  const g = ctx2(cv);
  g.scale(res, res);
  if (w.kind === BEAST_CLAW) paintBeastClaw(g, px);
  else {
    const art = render(w.def, px, res, {});
    if (art !== null) g.drawImage(art, 0, 0, px, px);
  }
  return cv;
}
/**
 * 交叉（9.8 第 4 條）：精英那把左右鏡像。異形精英（獸爪）先畫主角的劍（放大 1.12 倍）、再畫爪痕蓋在上面；
 * 人形精英先畫精英、再畫主角。
 */
/** 一把交叉的武器畫在 g：中心 (cx + dx, cy + dy)、大小 px0·k；精英那把鏡像；不是斜放的圖示先轉 0.62。 */
function putWeapon(g: C2, w: DuelWeapon, mirror: boolean, k: number, dx: number, dy: number, cx: number, cy: number, px0: number, res: number): void {
  const px = px0 * k;
  const c = weaponCanvas(w, px, res);
  g.save();
  g.translate(cx + dx, cy + dy);
  if (mirror) g.scale(-1, 1);
  if (!isDiag(w)) g.rotate(0.62);
  g.drawImage(c, -px / 2, -px / 2, px, px);
  g.restore();
}
/**
 * 錯開組對異形時整組移（9.9.5 第 7 條、9.9.10；樣張 groupFit）：插圖 × res 的離屏逐列掃（alpha > 64），
 * 整組右緣 ≤ 精英剪影（含往左 1.6 的輪廓光）同列左緣 −3 px；整組左緣 ≥ 主角剪影（含往右 1.6）同列右緣 +3 px（第 1 版本來就更近的以第 1 版為門檻）。
 * 第 1 版位置夠就不動 → 往上 0～4 px 挑剩最少的 → 剩下的往左移 → 主角側不夠就兩把一起縮小（每次 0.02，下限 0.8）。
 */
export function groupFit(es: Sil, hs: Sil | null, heroW: DuelWeapon, eliteW: DuelWeapon, F: Face, cx: number, cy: number, px0: number, res: number): DuelFit {
  const W = DUEL_W * res;
  const H = DUEL_H * res;
  const alphaOf = (c: HTMLCanvasElement): Uint8Array => {
    const d = ctx2(c).getImageData(0, 0, W, H).data;
    const a = new Uint8Array(W * H);
    for (let i = 0; i < a.length; i++) a[i] = d[i * 4 + 3]! > 64 ? 1 : 0;
    return a;
  };
  const silMask = (s: Sil, rim: number): Uint8Array => {
    const c = canvas(W, H);
    const g = ctx2(c);
    g.scale(res, res);
    g.drawImage(s.cv, s.x0 + rim, s.y0 - 0.6, s.w, s.h);
    g.drawImage(s.cv, s.x0, s.y0, s.w, s.h);
    return alphaOf(c);
  };
  const eA = silMask(es, -1.6);
  const hA = hs ? silMask(hs, 1.6) : null;
  const eL = new Int32Array(H).fill(-1);
  const hR = new Int32Array(H).fill(-1);
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++)
      if (eA[y * W + x]) {
        eL[y] = x;
        break;
      }
    if (hA)
      for (let x = W - 1; x >= 0; x--)
        if (hA[y * W + x]) {
          hR[y] = x;
          break;
        }
  }
  /** 整組在 (s, dx, dy)：精英側要往左多少（> 0 ＝超過）、主角側還剩多少（< 0 ＝不夠 3 px），插圖 px。 */
  const measure = (s: number, dx: number, dy: number): { need: number; room: number } => {
    const c = canvas(W, H);
    const g = ctx2(c);
    g.scale(res, res);
    putWeapon(g, heroW, false, F.k * s, F.hero[0] * s + dx, F.hero[1] * s + dy, cx, cy, px0, res);
    putWeapon(g, eliteW, true, F.ek * s, F.elite[0] * s + dx, F.elite[1] * s + dy, cx, cy, px0, res);
    const a = alphaOf(c);
    let need = 0;
    let room = Infinity;
    for (let y = 0; y < H; y++) {
      let l = -1;
      let r = -1;
      for (let x = 0; x < W; x++)
        if (a[y * W + x]) {
          l = x;
          break;
        }
      if (l < 0) continue;
      for (let x = W - 1; x >= 0; x--)
        if (a[y * W + x]) {
          r = x;
          break;
        }
      if (eL[y]! >= 0) need = Math.max(need, r - (eL[y]! - 3 * res));
      if (hR[y]! >= 0) room = Math.min(room, l - (hR[y]! + 3 * res));
    }
    return { need: Math.ceil(need) / res, room: room / res };
  };
  const m0 = measure(1, 0, 0);
  const floor = Math.min(0, m0.room);
  if (m0.need <= 0) return { dx: 0, dy: 0, s: 1, ok: true };
  let up = 0;
  let need = m0.need;
  for (let u = 1; u <= 4; u++) {
    const m = measure(1, 0, -u);
    if (m.need < need) {
      up = u;
      need = m.need;
    }
  }
  let best: DuelFit = { dx: 0, dy: 0, s: 1, ok: false };
  for (let i = 0; i <= 10; i++) {
    const s = Math.round((1 - i * 0.02) * 100) / 100;
    const dx = -measure(s, 0, -up).need;
    const m = measure(s, dx, -up);
    best = { dx, dy: -up, s, ok: m.room >= floor && m.need <= 0 };
    if (best.ok) return best;
  }
  return best;
}
/**
 * 交叉（9.8 第 4 條；9.9.3）：精英那把左右鏡像。主手在 FACE／FACE_KIND 有值的組（head、gun、open、block）照表錯開；
 * 對異形時整組套 groupFit（要精英剪影 es、主角剪影 hs）。其他（劍那組、heroW 為 null）照現行：
 * 異形精英（獸爪）先畫主角的劍（放大 1.12 倍）、再畫爪痕蓋在上面；人形精英先畫精英、再畫主角。
 */
function crossed(ctx: C2, heroW: DuelWeapon | null, eliteW: DuelWeapon | null, cx: number, cy: number, px0: number, res: number, heroKind: string | null, es: Sil, hs: Sil, onFit?: (f: DuelFit) => void): void {
  const put = (w: DuelWeapon | null, mirror: boolean, k = 1, dx = 0, dy = 0): void => {
    if (w === null) return;
    putWeapon(ctx, w, mirror, k, dx, dy, cx, cy, px0, res);
  };
  const claw = eliteW?.kind === BEAST_CLAW;
  const F = heroW !== null && eliteW !== null ? faceOf(heroKind)?.[claw ? "claw" : "man"] : undefined;
  if (F !== undefined && heroW !== null && eliteW !== null) {
    if (claw) {
      const t = groupFit(es, hs, heroW, eliteW, F, cx, cy, px0, res);
      onFit?.(t);
      put(heroW, false, F.k * t.s, F.hero[0] * t.s + t.dx, F.hero[1] * t.s + t.dy);
      put(eliteW, true, F.ek * t.s, F.elite[0] * t.s + t.dx, F.elite[1] * t.s + t.dy);
    } else {
      put(eliteW, true, F.ek, F.elite[0], F.elite[1]);
      put(heroW, false, F.k, F.hero[0], F.hero[1]);
    }
    return;
  }
  if (eliteW?.kind === BEAST_CLAW) {
    put(heroW, false, 1.12);
    put(eliteW, true);
  } else {
    put(eliteW, true);
    put(heroW, false);
  }
}
/** 四芒星火花（交叉點）。 */
function spark(ctx: C2, x: number, y: number, r: number, c1 = "#fff7c0", c2 = "#ffffff"): void {
  const star = (rr: number, w: number): void => {
    ctx.beginPath();
    for (let i = 0; i < 8; i++) {
      const a = (i * Math.PI) / 4 - Math.PI / 2;
      const q = i % 2 ? w : rr;
      ctx.lineTo(x + Math.cos(a) * q, y + Math.sin(a) * q);
    }
    ctx.closePath();
  };
  ctx.save();
  ctx.fillStyle = c1;
  star(r, r * 0.28);
  ctx.fill();
  ctx.fillStyle = c2;
  star(r * 0.55, r * 0.16);
  ctx.fill();
  ctx.restore();
}

// ---------------- 背景 ----------------
const FAR_HILLS: Readonly<Record<DuelRegion, ReadonlyArray<readonly [number, number]>>> = {
  ashen_waste: [[0, 84], [30, 80], [44, 70], [70, 70], [84, 80], [130, 82], [150, 74], [170, 76], [196, 84], [236, 80], [250, 66], [266, 60], [282, 66], [296, 78], [320, 80]],
  cloud_ridge: [[0, 78], [22, 60], [40, 70], [60, 48], [84, 66], [110, 74], [138, 62], [160, 70], [190, 56], [214, 40], [238, 62], [262, 70], [288, 54], [306, 64], [320, 58]],
};
function farHills(ctx: C2, reg: DuelRegion, c: string): void {
  ctx.fillStyle = c;
  ctx.beginPath();
  ctx.moveTo(0, 92);
  for (const [x, y] of FAR_HILLS[reg]) ctx.lineTo(x, y);
  ctx.lineTo(320, 92);
  ctx.closePath();
  ctx.fill();
}
function hexA(h: string, a: number): string {
  const n = parseInt(h.slice(1, 7), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

/** 插圖畫在 ctx 的 (0,0)～(320,120)；res＝內部解析度（剪影的離屏倍率跟著它）。 */
export function drawDuel(ctx: C2, spec: DuelSpec, res = 2): void {
  const W = DUEL_W;
  const H = DUEL_H;
  const reg = duelRegion(spec.region);
  const sk = DUEL_SKY[reg];
  const hooks = spec.hooks ?? GAME_HOOKS;
  const foot = 112;
  const heroX = 72;
  const eliteX = 250;
  ctx.save();
  ctx.beginPath();
  ctx.roundRect(0, 0, W, H, 6);
  ctx.clip();
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, sk.top);
  g.addColorStop(0.62, sk.mid);
  g.addColorStop(0.8, sk.glow);
  g.addColorStop(0.81, sk.near);
  g.addColorStop(1, sk.ground);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);
  const r = ctx.createRadialGradient(W / 2, 92, 4, W / 2, 92, 120);
  r.addColorStop(0, hexA(sk.glow, 0.55));
  r.addColorStop(1, hexA(sk.glow, 0));
  ctx.fillStyle = r;
  ctx.fillRect(0, 0, W, H);
  farHills(ctx, reg, sk.far);
  ctx.fillStyle = sk.near;
  ctx.beginPath();
  ctx.moveTo(0, 104);
  ctx.quadraticCurveTo(80, 96, 160, 99);
  ctx.quadraticCurveTo(240, 102, 320, 96);
  ctx.lineTo(320, 120);
  ctx.lineTo(0, 120);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = sk.haze;
  ctx.fillRect(0, 86, W, 8);

  const ef = spec.elite.figure;
  const main = spec.hero.main ?? null;
  const sg = silGroup(main?.kind);
  const pose = spec.hero.pose === undefined ? (GROUP_POSE[sg] ?? HERO_POSE) : spec.hero.pose;
  const prop = sg === "held" || main === null ? null : propOf(main, spec.hero.weapon);
  const hs = duelSilhouette({ kind: "doll", unit: spec.hero.unit, pose, prop }, false, heroX, foot, HERO_K, res, hooks);
  const es = duelSilhouette(ef, true, eliteX, foot, ef.kind === "creature" ? ef.k : HUMANOID_ELITE_K, res, hooks);
  const put = (s: Sil, c: HTMLCanvasElement, dx = 0, dy = 0): void => {
    ctx.save();
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(c, s.x0 + dx, s.y0 + dy, s.w, s.h);
    ctx.restore();
  };
  // 輪廓光：朝中間那側位移 1.6 px 的亮色剪影墊在下面，再蓋墨色剪影（主角 #a9ccff 我方環色、精英 #ffbf3a 精英金）
  put(hs, tinted(hs.cv, "#a9ccff"), 1.6, -0.6);
  put(hs, tinted(hs.cv, OUT));
  put(es, tinted(es.cv, "#ffbf3a"), -1.6, -0.6);
  put(es, tinted(es.cv, OUT));
  if (hs.seam) put(hs, tinted(hs.seam, "#a9ccff"));
  if (es.seam) put(es, tinted(es.seam, "#ffbf3a"));
  // 交叉的武器（背後淡暖光）；爪痕那組不加交叉點火花（9.7.1）
  const cx = W / 2;
  const cy = 56;
  const rg = ctx.createRadialGradient(cx, cy, 2, cx, cy, 34);
  rg.addColorStop(0, "rgba(255,240,200,0.55)");
  rg.addColorStop(1, "rgba(255,240,200,0)");
  ctx.fillStyle = rg;
  ctx.fillRect(cx - 40, cy - 40, 80, 80);
  crossed(ctx, spec.hero.weapon, spec.elite.weapon, cx, cy, 58, res, main?.kind ?? null, es, hs, spec.onFit);
  if (spec.elite.weapon?.kind !== BEAST_CLAW) spark(ctx, cx, cy - 9, 7);
  ctx.restore();
  // 框：1px 金邊（同事件插圖小牌外框色 #8a6a3a），內側一道暗線
  ctx.save();
  ctx.lineWidth = 1;
  ctx.strokeStyle = "#8a6a3a";
  ctx.beginPath();
  ctx.roundRect(0.5, 0.5, W - 1, H - 1, 6);
  ctx.stroke();
  ctx.strokeStyle = "rgba(0,0,0,0.5)";
  ctx.beginPath();
  ctx.roundRect(1.5, 1.5, W - 3, H - 3, 5);
  ctx.stroke();
  ctx.restore();
}

/** 整張插圖的畫布（320×120 × res 裝置像素）；沒有 DOM 時 null。 */
export function duelCanvas(spec: DuelSpec, res = 2): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  const cv = canvas(DUEL_W * res, DUEL_H * res);
  const g = cv.getContext("2d");
  if (g === null) return null;
  g.scale(res, res);
  drawDuel(g as C2, spec, res);
  return cv;
}

/** 測試、開發頁用：獸爪單獨（48 格畫法，px 顯示、res 倍）。 */
export function beastClawCanvas(px: number, res: number): HTMLCanvasElement | null {
  if (typeof document === "undefined") return null;
  return weaponCanvas({ kind: BEAST_CLAW }, px, res);
}

