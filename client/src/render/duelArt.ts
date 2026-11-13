// 精英單挑插圖 A「暮色對峙」（320×120；RG-4，照 docs/art/sample/rgUnits.js 第 3 節的 duel／duelCanvas 逐段搬，
// docs/art/RG樣張.md 9.3、9.6 決定 1、9.7／9.7.1、9.8 第 4～7 條，以 9.8 為準）。B「對角徽記」未採用、不搬。
// - 剪影：人形用紙娃娃（Q 版 qDoll 畫法＋剪影外框）在 R 倍離屏畫 → 侵蝕 1.0 單位 → alpha 二值化 >128；主手武器和手之間一道輪廓光縫；
//   斗笠在插圖裡換寬帽緣（SIL_DOULI）＋帽緣下 0.75 寬的縫（戰場 sprite 不換）。異形不侵蝕、二值化 >40，跳過地面環、影子與直接上色的軟特效。
// - 背景：區域天色（SKY 只有雲嶺、荒原，其他區退回雲嶺）＋遠山＋地平線光＋地面暗帶；框 1px #8a6a3a＋內側暗線。
// - 交叉的武器：Q 版武器圖示（`qIcon/weapons.ts` 的圖樣，無框）；異形精英用獸爪（`qIcon/beastClaw.ts`，只在這裡用）。
// 不改共用畫法檔：qStamp 的剪影外框流程在這裡另抄一份（多一個「畫的時候換掉斗笠」的掛勾），qStamp.ts／qNpc.ts／qIcon/weapons.ts 一行不動。
// 確定性：沒有亂數。沒有 DOM 時 `duelCanvas` 回傳 null。
import { mix, Q_OUT, type QHooks, type QPose, type QUnit } from "./qCore";
import { drawQ } from "./qDoll";
import { npcNeedsLayers, setNpcLayers } from "./qNpc";
import { qWeapon } from "./qWeapons";
import { Q_BOX, Q_LINE } from "./qStamp";
import { GAME_HOOKS } from "./qSpec";
import { drawCreature, type ResolvedCreature } from "./inkCreature";
import { render, type QDef } from "./qIcon/core";
import { BEAST_CLAW, paintBeastClaw } from "./qIcon/beastClaw";

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

/** 插圖裡的一個人物：人形（Q 版 unit＋姿勢）或異形（已解好的外觀＋倍率）。 */
export type DuelFigure = { kind: "doll"; unit: QUnit; pose?: QPose | null } | { kind: "creature"; creature: ResolvedCreature; k: number };
/** 交叉的武器：Q 版武器圖樣（`qWeaponDef` 的結果，看 `meta.diag`）或獸爪。 */
export type DuelWeapon = { kind: "icon"; def: QDef & { meta: { diag: boolean } } } | { kind: typeof BEAST_CLAW };

export interface DuelSpec {
  hero: { unit: QUnit; weapon: DuelWeapon | null; pose?: QPose | null };
  elite: { figure: DuelFigure; weapon: DuelWeapon | null };
  region: string | null | undefined;
  /** 紙娃娃的顏色（剪影只看 alpha，顏色不影響結果；開發頁比對時給樣張色）。 */
  hooks?: QHooks;
}

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
function crossed(ctx: C2, heroW: DuelWeapon | null, eliteW: DuelWeapon | null, cx: number, cy: number, px0: number, res: number): void {
  const put = (w: DuelWeapon | null, mirror: boolean, k = 1): void => {
    if (w === null) return;
    const px = px0 * k;
    const c = weaponCanvas(w, px, res);
    ctx.save();
    ctx.translate(cx, cy);
    if (mirror) ctx.scale(-1, 1);
    if (!isDiag(w)) ctx.rotate(0.62);
    ctx.drawImage(c, -px / 2, -px / 2, px, px);
    ctx.restore();
  };
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
  const hs = duelSilhouette({ kind: "doll", unit: spec.hero.unit, pose: spec.hero.pose === undefined ? HERO_POSE : spec.hero.pose }, false, heroX, foot, HERO_K, res, hooks);
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
  crossed(ctx, spec.hero.weapon, spec.elite.weapon, cx, cy, 58, res);
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

