// Q 版人形敵人、NPC 的新部件（QK-8；照 docs/art/sample/qNpc.js 的 prep 與 PART 改寫，需求 docs/art/QK移植需求.md 第 8.5 節）。
// 樣張是「本體填色層＋B（本體後）＋C（本體前）三層合起來描同一圈外框，D（外框之後）不描」；
// 這裡改成直接長進 qDoll 的畫法：B 層在 drawBody 一開始畫、C 層在最後畫（同一張離屏，qStamp 一起描外框，新部件不多一圈內框），
// D 層（白紗面罩、傀儡線）畫到 qStamp 給的「外框之上」離屏（沒有時畫在本體上）；朝西遠側手的傀儡線畫到「外框之下」離屏。
// 劍穗、傀儡線要武器在畫布上的位置：借 POSE.probe 記下每把武器的變換（樣張 setPose({probe})）。
// 座標同 qDoll：腳底 (0,0)、頭心 (0,−29)；側面一律朝東畫（外層鏡像），左右手、左右腰照朝西換邊（ww）。確定性：沒有亂數。
import type { Ctx } from "./artDraw";
import { fill, getM, mix, rr, setM, TAU, tp, type M6, type P2, type QItem, type QPose, type QUnit, type QView } from "./qCore";
import { belowBreak, BRK_SIDE_DY } from "./qWeapons";
import { HELD_KINDS, type QHeldItem } from "./qNpcHeld";

/** 一個新部件：k＝種類；edge＝亮一階的邊（皮圍裙）；pocket＝圍裙口袋；cap＝戴帽時護目鏡架在帽沿上；who＝傀儡線在哪隻手。 */
export interface NpcPart {
  k: string;
  color?: string | undefined;
  edge?: string | undefined;
  pocket?: boolean;
  cap?: boolean;
  who?: "main_hand" | "off_hand";
}

/** 一隻的換算結果：qDoll 認得的 unit、新部件、（需要時）包了 probe 的姿勢與記下的武器變換。 */
export interface NpcFrame {
  unit: QUnit;
  parts: NpcPart[];
  pose: QPose | null;
  /** 武器 kind → 每次畫這把武器時的變換（畫布座標）。 */
  wms: Record<string, M6[]>;
  /** 側面朝西（左手、左腰在近側）。 */
  ww: boolean;
}

const BACK_PARTS = ["gourd", "puppet_box", "mailbag"];
const dk = (c: string, t = 0.3): string => mix(c, "#000000", t);

type GearLike = QItem & { apron?: string; tassel?: string };

/**
 * 資料 → qDoll 認得的 unit＋新部件（樣張 QNpc.prep；遊戲資料的寫法另外接：圍裙 waist apron、範本 robe 的 apron 色、
 * 霧行者 veil → 白兜帽＋白紗、傀儡線 puppet_cross、頭上 douli／headband／goggles_up、帽上 form goggles／goggles_up）。不改原物件。
 */
export function npcPrep(unit0: QUnit, pose: QPose | null, ww: boolean): NpcFrame {
  const look = { ...unit0.look };
  const gear: QUnit["gear"] = { ...unit0.gear };
  const parts: NpcPart[] = [];
  const P = (k: string, o: Omit<NpcPart, "k"> = {}): void => void parts.push({ k, ...o });
  const b = gear.body as GearLike | undefined;
  if (b?.kind === "bare") {
    // 赤膊：軀幹與手臂＝膚色；原本的 body.color 是腰帶色
    if (b.color) look.belt = b.color;
    gear.body = { kind: "bare", color: look.skin };
  } else if (b?.apron) {
    const { apron, ...rest } = b;
    gear.body = rest;
    P("apron", { color: apron });
  }
  const w = gear.waist;
  if (w?.kind === "apron") {
    P("apron", { color: w.color, edge: w.trim, pocket: w.material !== "leather" });
    delete gear.waist;
  } else if (w?.kind === "talismans") {
    P("talismans", { color: w.color });
    delete gear.waist;
  }
  if (gear.back && BACK_PARTS.includes(gear.back.kind)) {
    P(gear.back.kind, { color: gear.back.color });
    delete gear.back;
  }
  const h = gear.head;
  if (h?.kind === "veil" || h?.kind === "gauze") {
    P("gauze", { color: h.kind === "gauze" ? h.color : undefined });
    gear.head = { kind: "hood", color: h.color ?? "#eef2f2" };
  } else if (h?.kind === "douli" || h?.kind === "headband") {
    P(h.kind, { color: h.color });
    delete gear.head;
  } else if (h?.kind === "goggles_up") {
    P("goggles_up");
    delete gear.head;
  } else if (h?.form === "goggles_up" || h?.form === "goggles") {
    // 帽子上加護目鏡（老鐵：帽＋護目鏡戴在眼睛上；戴帽的工坊師傅：額上護目鏡架在帽沿上）
    P(h.form, { cap: true });
  }
  if (gear.cloak?.form === "feather") {
    gear.neck = { kind: "feathers", ...(gear.cloak.color ? { color: gear.cloak.color } : {}) };
    delete gear.cloak;
  }
  const tassel = (gear.main_hand as GearLike | undefined)?.tassel;
  if (tassel) P("tassel", { color: tassel });
  const skin = gear.hands && gear.hands.kind !== "bracers" ? null : look.skin;
  for (const slot of ["main_hand", "off_hand"] as const) {
    let it = gear[slot] as QHeldItem | undefined;
    if (!it) continue;
    if (it.kind === "puppet_cross") it = { ...it, kind: "puppet_strings" };
    if (HELD_KINDS.includes(it.kind)) {
      gear[slot] = { ...it, skin: it.skin ?? skin ?? "#f1c9a5" } as QHeldItem;
      if (it.kind === "puppet_strings") P("strings", { who: slot });
    }
  }
  // PB-1e：氣海（霧鎖真人）的氣旋或裂痕：外框之後畫（不描外框）、側面挖掉主手武器那一塊（＝排在武器之下）
  if (unit0.dantian !== undefined) P(unit0.dantian === "qi" ? "dantian_qi" : "dantian_crack");
  const wms: Record<string, M6[]> = {};
  let p2 = pose;
  if (parts.some((p) => p.k === "tassel" || p.k === "strings" || p.k === "dantian_qi" || p.k === "dantian_crack")) {
    const inner = pose?.probe;
    p2 = {
      ...(pose ?? {}),
      probe: (kind, hand, tip, view, off, m, wkey) => {
        (wms[kind] ??= []).push(m);
        if (inner) inner(kind, hand, tip, view, off, m, wkey);
      },
    };
  }
  return { unit: { look, gear }, parts, pose: p2, wms, ww };
}

/** 這隻需不需要外框之外的兩張離屏（白紗、傀儡線）。 */
export function npcNeedsLayers(unit: QUnit): boolean {
  const h = unit.gear.head?.kind;
  const held = (it: QItem | undefined): boolean => it?.kind === "puppet_strings" || it?.kind === "puppet_cross";
  return h === "veil" || h === "gauze" || held(unit.gear.main_hand) || held(unit.gear.off_hand) || unit.dantian !== undefined;
}

/** qStamp 給的兩張離屏：over＝外框之上（不描外框）、under＝外框之下。和本體同一個畫布座標。 */
export interface NpcLayers {
  over: Ctx;
  under: Ctx;
}
let LAYERS: NpcLayers | null = null;
/** qStamp 畫一隻時設好、畫完清掉。 */
export function setNpcLayers(l: NpcLayers | null): void {
  LAYERS = l;
}

// ---------- 小工具 ----------
function line(ctx: Ctx, c: string, w: number, pts: ReadonlyArray<readonly [number, number]>): void {
  ctx.strokeStyle = c;
  ctx.lineWidth = w;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.beginPath();
  pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
  ctx.stroke();
}
/** 頭下面的部件：挖掉頭。 */
function headClip(ctx: Ctx): void {
  ctx.beginPath();
  ctx.rect(-80, -120, 160, 200);
  ctx.arc(0, -29, 8.7, 0, TAU);
  ctx.clip("evenodd");
}
function gourdShape(ctx: Ctx, c: string): void {
  fill(ctx, c, () => ctx.arc(0, 2.6, 3.4, 0, TAU));
  fill(ctx, c, () => ctx.arc(0, -2.4, 2.3, 0, TAU));
  fill(ctx, "#c0392b", () => ctx.roundRect(-1.8, -0.6, 3.6, 1, 0.4));
  fill(ctx, "#6a4a2a", () => ctx.roundRect(-0.8, -5.6, 1.6, 1.6, 0.4));
  fill(ctx, "rgba(255,255,255,0.35)", () => ctx.arc(-1.2, 1.6, 0.9, 0, TAU));
}
function bagShape(ctx: Ctx, x: number, y: number, col: string | undefined, back = false): void {
  const c = col ?? "#d8c8a0";
  fill(ctx, c, () => rr(ctx, x, y, 6, 5.6, 1.2));
  fill(ctx, dk(c, 0.25), () => rr(ctx, x, y, 6, 2.4, 1));
  if (!back) fill(ctx, "#2a2420", () => rr(ctx, x + 2.4, y + 1.8, 1.2, 1.4, 0.3));
}

// ---------- B 層（本體後面） ----------
function partBehind(ctx: Ctx, v: QView, p: NpcPart, W: boolean): void {
  if (p.k === "gourd") {
    if (v === "back") return;
    ctx.save();
    if (v === "front") {
      ctx.translate(7.2, -24.6);
      ctx.rotate(0.45);
    } else {
      ctx.translate(-8.4, -15);
      ctx.rotate(-0.35);
    }
    gourdShape(ctx, p.color ?? "#c8903a");
    ctx.restore();
  } else if (p.k === "puppet_box") {
    const c = p.color ?? "#8a6a48";
    const [x, w, h] = v === "front" ? [-11.6, 23.2, 7] : v === "side" ? [-15, 9.4, 20] : [0, 0, 0];
    if (!w) return;
    fill(ctx, c, () => rr(ctx, x, -26, w, h, 1.2));
    fill(ctx, dk(c), () => ctx.rect(x, -26, w, 1.4));
    fill(ctx, "#c0392b", () => ctx.rect(x, -22.6, w, 0.9));
  } else if (p.k === "mailbag") {
    if (v === "front") bagShape(ctx, -12.6, -12.2, p.color, true);
    else if (v === "side" && W) bagShape(ctx, -11.2, -12.4, p.color, true);
  }
}

// ---------- C 層（本體前面，和本體一起描外框） ----------
function apron(ctx: Ctx, v: QView, p: NpcPart): void {
  const c = p.color ?? "#e8dcc0";
  const d = dk(c, 0.25);
  const e = p.edge ?? d;
  if (v === "front") {
    fill(ctx, e, () => {
      ctx.moveTo(-4.3, -19.2);
      ctx.lineTo(4.3, -19.2);
      ctx.lineTo(5.1, -11);
      ctx.lineTo(6.3, -2.4);
      ctx.lineTo(-6.3, -2.4);
      ctx.lineTo(-5.1, -11);
      ctx.closePath();
    });
    fill(ctx, c, () => {
      ctx.moveTo(-3.6, -18.6);
      ctx.lineTo(3.6, -18.6);
      ctx.lineTo(4.4, -11);
      ctx.lineTo(5.6, -3);
      ctx.lineTo(-5.6, -3);
      ctx.lineTo(-4.4, -11);
      ctx.closePath();
    });
    line(ctx, e, 0.7, [[-3.6, -18.8], [-2.6, -20.8]]);
    line(ctx, e, 0.7, [[3.6, -18.8], [2.6, -20.8]]);
    if (p.pocket !== false) fill(ctx, d, () => rr(ctx, -2.2, -8, 4.4, 2.6, 0.6));
  } else if (v === "side") {
    fill(ctx, e, () => {
      ctx.moveTo(4.1, -18.8);
      ctx.lineTo(5.6, -18.8);
      ctx.lineTo(6.3, -9.6);
      ctx.lineTo(6.9, -2.8);
      ctx.lineTo(5.2, -2.8);
      ctx.lineTo(4.6, -9.6);
      ctx.closePath();
    });
    fill(ctx, c, () => {
      ctx.moveTo(4.3, -18.4);
      ctx.lineTo(5.2, -18.4);
      ctx.lineTo(5.8, -9.6);
      ctx.lineTo(6.4, -3.2);
      ctx.lineTo(5.5, -3.2);
      ctx.lineTo(4.9, -9.6);
      ctx.closePath();
    });
    line(ctx, e, 0.6, [[-5, -9.4], [4.6, -9.4]]);
    line(ctx, e, 0.6, [[4.6, -18.6], [1.6, -21]]);
  } else {
    line(ctx, e, 0.7, [[-3, -20.8], [0, -21.6], [3, -20.8]]);
    line(ctx, e, 0.7, [[-5.4, -9.4], [5.4, -9.4]]);
    fill(ctx, e, () => ctx.ellipse(0, -9.4, 1.2, 0.8, 0, 0, TAU));
    line(ctx, e, 0.6, [[0, -9], [-0.8, -6.4]]);
    line(ctx, e, 0.6, [[0, -9], [0.9, -6.6]]);
  }
}

function douli(ctx: Ctx, v: QView, p: NpcPart): void {
  const c = p.color ?? "#c8b07a";
  const d = dk(c, 0.22);
  if (v === "side") {
    fill(ctx, c, () => {
      ctx.moveTo(-12.6, -33.8);
      ctx.quadraticCurveTo(0, -36, 12.4, -32.8);
      ctx.lineTo(0.8, -43.4);
      ctx.closePath();
    });
    line(ctx, d, 0.5, [[0.8, -43], [-5.4, -34.8]]);
    line(ctx, d, 0.5, [[0.8, -43], [6.6, -33.8]]);
    fill(ctx, d, () => rr(ctx, -8.6, -35.8, 16.8, 1.2, 0.6));
    return;
  }
  fill(ctx, c, () => {
    ctx.moveTo(-12.6, -33);
    ctx.quadraticCurveTo(0, -31.6, 12.6, -33);
    ctx.lineTo(0, -43.6);
    ctx.closePath();
  });
  for (const x of [-6.6, 0, 6.6]) line(ctx, d, 0.5, [[0, -43.2], [x, -32.4]]);
  line(ctx, d, 0.7, [[-12.6, -33], [12.6, -33]]);
  if (v === "front") {
    // 下巴綁繩只在臉兩側
    line(ctx, "#6a4a2a", 0.6, [[-6.4, -31.8], [-5.2, -24.6]]);
    line(ctx, "#6a4a2a", 0.6, [[6.4, -31.8], [5.2, -24.6]]);
  }
}

function headband(ctx: Ctx, v: QView, p: NpcPart): void {
  const c = p.color ?? "#b8432f";
  const d = dk(c, 0.25);
  if (v === "side") {
    fill(ctx, c, () => {
      ctx.moveTo(8.6, -34.2);
      ctx.lineTo(8.9, -32.2);
      ctx.lineTo(-9.4, -31.4);
      ctx.lineTo(-9.2, -33.4);
      ctx.closePath();
    });
    fill(ctx, d, () => ctx.arc(-9.4, -32.4, 1.3, 0, TAU));
    fill(ctx, c, () => {
      ctx.moveTo(-9.6, -32);
      ctx.lineTo(-13.2, -27.4);
      ctx.lineTo(-11.6, -26.8);
      ctx.lineTo(-9, -31);
      ctx.closePath();
    });
    return;
  }
  fill(ctx, c, () => {
    ctx.moveTo(-8.9, -33.6);
    ctx.quadraticCurveTo(0, -35.4, 8.9, -33.6);
    ctx.lineTo(8.7, -31.6);
    ctx.quadraticCurveTo(0, -33.2, -8.7, -31.6);
    ctx.closePath();
  });
  if (v === "back") {
    fill(ctx, d, () => ctx.arc(0, -33.2, 1.4, 0, TAU));
    for (const s of [-1, 1])
      fill(ctx, c, () => {
        ctx.moveTo(0, -33);
        ctx.lineTo(s * 2.6, -25.6);
        ctx.lineTo(s * 0.8, -25.2);
        ctx.closePath();
      });
  }
}

function goggles(ctx: Ctx, v: QView): void {
  const st = "#3a3a44";
  if (v === "back") {
    line(ctx, st, 1.4, [[-8.8, -30], [8.8, -30]]);
    return;
  }
  if (v === "side") {
    line(ctx, st, 1.2, [[6, -30], [-8.8, -30.6]]);
    fill(ctx, "#8d969f", () => ctx.ellipse(7.2, -29.5, 2, 2.6, 0, 0, TAU));
    fill(ctx, "rgba(160,220,255,0.7)", () => ctx.ellipse(7.8, -29.5, 1.2, 1.9, 0, 0, TAU));
    return;
  }
  line(ctx, st, 1.3, [[-8.8, -29.6], [8.8, -29.6]]);
  for (const x of [-3, 3]) {
    fill(ctx, "#8d969f", () => ctx.ellipse(x, -29.5, 3, 2.6, 0, 0, TAU));
    fill(ctx, "rgba(160,220,255,0.7)", () => ctx.ellipse(x, -29.5, 2.2, 1.9, 0, 0, TAU));
  }
}

function gogglesUp(ctx: Ctx, v: QView, p: NpcPart): void {
  const st = "#3a3a44";
  ctx.save();
  if (p.cap) ctx.translate(0, -1.6); // 戴帽子時架在帽沿上
  if (v === "back") line(ctx, st, 1.3, [[-8.8, -33.6], [8.8, -33.6]]);
  else if (v === "side") {
    line(ctx, st, 1.2, [[6, -34.6], [-9, -33.4]]);
    fill(ctx, "#8d969f", () => ctx.ellipse(6.6, -35.4, 2, 2.2, 0, 0, TAU));
    fill(ctx, "rgba(160,220,255,0.85)", () => ctx.ellipse(7.2, -35.4, 1.1, 1.5, 0, 0, TAU));
  } else {
    line(ctx, st, 1.3, [[-8.8, -34.4], [8.8, -34.4]]);
    for (const x of [-3.2, 3.2]) {
      fill(ctx, "#8d969f", () => ctx.ellipse(x, -35, 2.8, 2.3, 0, 0, TAU));
      fill(ctx, "rgba(160,220,255,0.85)", () => ctx.ellipse(x, -35, 1.9, 1.5, 0, 0, TAU));
    }
  }
  ctx.restore();
}

function partFront(ctx: Ctx, v: QView, p: NpcPart, W: boolean): void {
  switch (p.k) {
    case "apron":
      apron(ctx, v, p);
      break;
    case "gourd": {
      // 斜綁的帶子：正面左肩（畫面右）→ 右腰；背面整顆在背上（挖掉頭）
      if (v === "front") line(ctx, "#8a3a2a", 0.9, [[6.4, -20.8], [-5.6, -10]]);
      else if (v === "side") line(ctx, "#8a3a2a", 0.9, [[-1.6, -20.8], [4.6, -10.6]]);
      else {
        ctx.save();
        headClip(ctx);
        ctx.translate(-3.2, -13.6);
        ctx.rotate(-0.42);
        gourdShape(ctx, p.color ?? "#c8903a");
        ctx.restore();
        line(ctx, "#8a3a2a", 0.9, [[-6.4, -20.8], [5.2, -9.6]]);
      }
      break;
    }
    case "puppet_box": {
      const c = p.color ?? "#8a6a48";
      const d = dk(c);
      if (v === "back") {
        ctx.save();
        headClip(ctx);
        fill(ctx, c, () => rr(ctx, -9.6, -26, 19.2, 21, 1.2));
        fill(ctx, d, () => ctx.rect(-9.6, -26, 19.2, 1.4));
        fill(ctx, "#c0392b", () => ctx.rect(-9.6, -22.6, 19.2, 0.9));
        line(ctx, d, 0.7, [[0, -21.6], [0, -6]]);
        fill(ctx, "#e8bb48", () => ctx.arc(-1.3, -14, 0.7, 0, TAU));
        fill(ctx, "#e8bb48", () => ctx.arc(1.3, -14, 0.7, 0, TAU));
        ctx.restore();
      } else if (v === "front") for (const s of [-1, 1]) line(ctx, "#5a3a22", 1.1, [[s * 4.6, -21], [s * 4.8, -11]]);
      else line(ctx, "#5a3a22", 1.1, [[-0.8, -21], [-0.6, -11]]);
      break;
    }
    case "mailbag": {
      const s = "#6a4a2a";
      if (v === "front") line(ctx, s, 1.3, [[6.2, -20.6], [-6.4, -9.6]]);
      else if (v === "back") {
        line(ctx, s, 1.3, [[-6.2, -20.6], [4.6, -10]]);
        bagShape(ctx, 2.2, -12, p.color);
      } else if (!W) {
        line(ctx, s, 1.3, [[2.6, -20.8], [-3.6, -10.4]]);
        bagShape(ctx, -8.4, -12.2, p.color);
      } else line(ctx, s, 1.3, [[-1.6, -20.8], [4.8, -11]]);
      break;
    }
    case "talismans": {
      // 左腰三張黃符垂下（正面畫面右、背面畫面左；側面朝東在遠側被擋住、朝西在近側）
      const c = p.color ?? "#f2d860";
      const xs = v === "front" ? [2.8, 4.6, 6.4] : v === "back" ? [-6.4, -4.6, -2.8] : W ? [-3.8, -2, -0.2] : null;
      if (!xs) break;
      xs.forEach((x, i) => {
        const L = 5.6 - Math.abs(i - 1) * 0.9;
        fill(ctx, c, () => rr(ctx, x - 0.8, -8.4, 1.6, L, 0.3));
        if (v !== "back") line(ctx, "#c0392b", 0.4, [[x, -7.6], [x, -8.4 + L - 1]]);
      });
      break;
    }
    case "douli":
      douli(ctx, v, p);
      break;
    case "headband":
      headband(ctx, v, p);
      break;
    case "goggles":
      goggles(ctx, v);
      break;
    case "goggles_up":
      gogglesUp(ctx, v, p);
      break;
    default:
      break;
  }
}

/** 白紗面罩（霧行者）：qDoll 畫白兜帽，這裡加半透明面罩（眼睛以下）；背面看不到。不描外框。 */
function gauze(ctx: Ctx, v: QView, p: NpcPart): void {
  if (v === "back") return;
  ctx.save();
  ctx.globalAlpha = 0.78;
  const c = p.color ?? "#f4f6f6";
  if (v === "front")
    fill(ctx, c, () => {
      ctx.moveTo(-6.6, -26.6);
      ctx.lineTo(6.6, -26.6);
      ctx.quadraticCurveTo(6.4, -21.4, 0, -20.6);
      ctx.quadraticCurveTo(-6.4, -21.4, -6.6, -26.6);
      ctx.closePath();
    });
  else
    fill(ctx, c, () => {
      ctx.moveTo(1.6, -26.6);
      ctx.lineTo(9.8, -26.6);
      ctx.quadraticCurveTo(9.4, -22, 4.6, -20.8);
      ctx.lineTo(1.6, -22);
      ctx.closePath();
    });
  ctx.restore();
}

/** 在另一張離屏用同一個畫布座標畫（沒有離屏＝畫在本體上）。 */
function onLayer(ctx: Ctx, target: Ctx | undefined, draw: (c: Ctx) => void): void {
  if (!target || target === ctx) {
    draw(ctx);
    return;
  }
  const m = getM(ctx);
  target.save();
  setM(target, m);
  draw(target);
  target.restore();
}

/** B 層：drawBody 一開始（體型、上下晃、側面前傾之後）畫。 */
export function npcBeforeQ(ctx: Ctx, npc: NpcFrame, view: QView): void {
  for (const p of npc.parts) partBehind(ctx, view, p, npc.ww);
}

/** C 層、劍穗、傀儡線、白紗：drawBody 最後畫。 */
export function npcAfterQ(ctx: Ctx, npc: NpcFrame, view: QView): void {
  if (npc.parts.length === 0) return;
  for (const p of npc.parts) partFront(ctx, view, p, npc.ww);
  const S = view === "side";
  const WW = npc.ww;
  // 劍穗：掛在劍柄尾（武器座標 (0, 2.2)），往下垂；朝西劍在遠側，劍穗也在身體後面
  const ts = npc.parts.find((p) => p.k === "tassel");
  const sw = ts ? npc.wms[npc.unit.gear.main_hand?.kind ?? ""]?.[0] : undefined;
  if (ts && sw) {
    const k = Math.sqrt(Math.abs(sw.a * sw.d - sw.b * sw.c));
    const [x, y] = tp(sw, 0, 2.2);
    ctx.save();
    ctx.setTransform(k, 0, 0, k, x, y);
    if (WW) ctx.globalCompositeOperation = "destination-over";
    const c = ts.color ?? "#c0392b";
    line(ctx, c, 0.6, [[0, 0], [0.4, 2.6]]);
    fill(ctx, "#e8bb48", () => ctx.arc(0.4, 2.8, 0.6, 0, TAU));
    fill(ctx, c, () => {
      ctx.moveTo(-0.6, 3.2);
      ctx.lineTo(1.4, 3.2);
      ctx.lineTo(1.8, 6.6);
      ctx.lineTo(-1, 6.6);
      ctx.closePath();
    });
    ctx.restore();
  }
  // 傀儡線：十字架三個點往下垂的細線（不描外框）。遠側的手（朝西主手）在身體後面（外框之下）
  for (const p of npc.parts.filter((q) => q.k === "strings")) {
    const both = npc.unit.gear.main_hand?.kind === "puppet_strings";
    const m = (npc.wms["puppet_strings"] ?? [])[p.who === "off_hand" && both ? 1 : 0];
    if (!m) continue;
    const far = S && (p.who === "main_hand") === WW;
    const target = far ? LAYERS?.under : LAYERS?.over;
    const k = Math.sqrt(Math.abs(m.a * m.d - m.b * m.c));
    const tops = ([[-4, 0], [4, 0], [0, 3.6]] as const).map(([x, y]) => tp(m, x, y));
    const bot = Math.max(...tops.map((t) => t[1])) + 10 * k;
    const mx = tops.reduce((a, t) => a + t[0], 0) / 3;
    const draw = (c: Ctx): void => {
      c.save();
      c.setTransform(1, 0, 0, 1, 0, 0);
      if (!target && far) c.globalCompositeOperation = "destination-over";
      c.strokeStyle = "rgba(240,236,220,0.9)";
      c.lineWidth = 0.4 * k;
      for (const t of tops) {
        c.beginPath();
        c.moveTo(t[0], t[1]);
        c.lineTo(mx + (t[0] - mx) * 0.4, bot);
        c.stroke();
      }
      fill(c, "#c0392b", () => c.arc(mx, bot + 0.6 * k, 0.7 * k, 0, TAU));
      c.restore();
    };
    draw(target ?? ctx);
  }
  for (const p of npc.parts) if (p.k === "gauze") onLayer(ctx, LAYERS?.over, (c) => gauze(c, view, p));
  const dt = npc.parts.find((p) => p.k === "dantian_qi" || p.k === "dantian_crack");
  if (dt !== undefined) {
    const main = npc.unit.gear.main_hand;
    const wm = S && main ? npc.wms[main.kind]?.[0] : undefined;
    onLayer(ctx, LAYERS?.over, (c) => dantianLayer(c, view, dt.k === "dantian_crack", wm ?? null, main?.broken === true));
  }
}

// ---------- PB-1e：氣海（照 docs/art/sample/bossParts.js 的 BELLY、drawD、extraD） ----------

/** 腹部（本體座標：腳底原點、頭心 −29）；側面往身體內側挪 `DANTIAN_SIDE_DX`（樣張第 2 版 SIDE_DX）。 */
export const BELLY = { x: 0, y: -12.5, rx: 4.2, ry: 3.2 } as const;
export const DANTIAN_SIDE_DX = 0.4;

/** 氣海的中心（本體座標；側面一律朝東畫）。 */
export function bellyAt(view: QView): P2 {
  return [BELLY.x + (view === "side" ? DANTIAN_SIDE_DX : 0), BELLY.y];
}

/** 露出時腹前的淡青氣旋（樣張 drawD 的 qi）。 */
function qiSwirl(c: Ctx, bx: number, by: number): void {
  c.save();
  const g = c.createRadialGradient(bx, by, 0, bx, by, 5.2);
  g.addColorStop(0, "rgba(220,255,250,0.9)");
  g.addColorStop(0.45, "rgba(110,224,208,0.65)");
  g.addColorStop(1, "rgba(110,224,208,0)");
  c.fillStyle = g;
  c.beginPath();
  c.arc(bx, by, 5.2, 0, TAU);
  c.fill();
  c.strokeStyle = "rgba(240,255,252,0.85)";
  c.lineWidth = 0.55;
  c.lineCap = "round";
  c.beginPath();
  c.arc(bx, by, 2.4, -0.4, 2.2);
  c.stroke();
  c.beginPath();
  c.arc(bx, by, 1.2, 2.6, 5.2);
  c.stroke();
  c.restore();
}

/** 破了：三道深青裂痕＋兩側漏出四團淡霧（樣張 drawD 的 broken）。 */
function qiCracks(c: Ctx, bx: number, by: number): void {
  c.save();
  c.globalAlpha = 0.95;
  c.strokeStyle = "#1f3a38";
  c.lineWidth = 0.95;
  c.lineCap = "round";
  c.beginPath();
  for (const [a, l] of [
    [-0.6, 3.6],
    [1.9, 3.0],
    [3.6, 3.3],
  ] as const) {
    c.moveTo(bx, by);
    c.lineTo(bx + Math.cos(a) * l * 0.55, by + Math.sin(a) * l * 0.55 + 0.4);
    c.lineTo(bx + Math.cos(a + 0.25) * l, by + Math.sin(a + 0.25) * l);
  }
  c.stroke();
  c.restore();
  c.save();
  c.fillStyle = "#e6ecec";
  for (const [dx, dy, r, al] of [
    [-5.6, -1.4, 2.4, 0.7],
    [-8.0, -3.6, 1.8, 0.5],
    [5.8, -0.6, 2.2, 0.65],
    [8.2, -2.8, 1.6, 0.45],
  ] as const) {
    c.globalAlpha = al;
    c.beginPath();
    c.ellipse(bx + dx, by + dy, r, r * 0.7, 0, 0, TAU);
    c.fill();
  }
  c.restore();
}

/**
 * 主手武器（刃、護手、柄、握劍的手）在武器座標的範圍，往外放約 0.5（樣張用「拿掉主手武器的那一份相減」做遮罩；
 * 遊戲端照畫法直接給：記下的武器變換＋劍的形狀）。斷劍只算斷口以下。
 */
function weaponArea(c: Ctx, broken: boolean): void {
  c.save();
  if (broken) {
    belowBreak(c, BRK_SIDE_DY);
    c.clip();
  }
  c.beginPath();
  c.moveTo(-1.8, -2);
  c.lineTo(-1.8, -16.5);
  c.lineTo(0, -20);
  c.lineTo(1.8, -16.5);
  c.lineTo(1.8, -2);
  c.closePath();
  c.rect(-3.4, -4.2, 6.8, 2.6);
  c.rect(-1.3, -2, 2.6, 5.4);
  c.moveTo(2.9, 0);
  c.arc(0, 0, 2.9, 0, TAU);
  c.fill();
  c.restore();
}

/** 氣海那一層（在 qStamp 的「外框之上」離屏畫；側面挖掉主手武器＝畫在武器之下）。`wm`＝主手武器的變換（畫布座標）。 */
function dantianLayer(c: Ctx, view: QView, crack: boolean, wm: M6 | null, broken: boolean): void {
  const [bx, by] = bellyAt(view);
  const draw = (g: Ctx): void => (crack ? qiCracks(g, bx, by) : qiSwirl(g, bx, by));
  const cv = c.canvas as HTMLCanvasElement | undefined;
  if (view !== "side" || wm === null || cv === undefined || typeof document === "undefined") {
    draw(c);
    return;
  }
  const tmp = document.createElement("canvas");
  tmp.width = cv.width;
  tmp.height = cv.height;
  const t = tmp.getContext("2d");
  if (t === null) {
    draw(c);
    return;
  }
  setM(t, getM(c));
  draw(t);
  t.globalCompositeOperation = "destination-out";
  setM(t, wm);
  t.fillStyle = "#000";
  weaponArea(t, broken);
  c.save();
  c.setTransform(1, 0, 0, 1, 0, 0);
  c.drawImage(tmp, 0, 0);
  c.restore();
}
