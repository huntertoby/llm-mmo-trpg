// Q 版武器（QK-1 第 8 項；照 docs/art/sample/qDoll.js 的武器表 QW，6M-2 規則：握把在原點、作用端朝 −y，角度由手決定）。
// 另含樣張 paperdoll.js 的 drawWeapon／drawWeapon2（盾、書、法球與 QW 沒有的手持物，畫在手的位置；pdHeld）。
import type { Ctx } from "./artDraw";
import { fill, getM, invM, isTowerLike, pz, rr, S, setM, TAU, tp, wc, colors, type P2, type QItem } from "./qCore";
import { shellFront } from "./qMoltenShell";
import { sectShieldFront } from "./qSectShield";
import { QW_HELD } from "./qNpcHeld";

function sword(ctx: Ctx, it: QItem | undefined, L: number, W: number): void {
  const [c] = wc(it, "steel");
  fill(ctx, c, () => {
    ctx.moveTo(-W / 2, -3);
    ctx.lineTo(-W / 2, -L);
    ctx.lineTo(0, -L - 3);
    ctx.lineTo(W / 2, -L);
    ctx.lineTo(W / 2, -3);
    ctx.closePath();
  });
  if (it?.form === "arcane") {
    // 源晶槽：預設藍紫光；有元素時換元素色（Phase 3I-3 的規則照舊，樣張沒寫元素）
    const glow = arcaneGlowColor(it, S.hooks!.tint);
    ctx.save();
    ctx.shadowColor = glow;
    ctx.shadowBlur = 4 + 8 * pz("glow");
    ctx.fillStyle = glow;
    ctx.fillRect(-0.55, -L + 1, 1.1, L - 5);
    ctx.restore();
    ctx.fillStyle = "#e8e2ff";
    for (const ry of [-6.5, -10, -13.5]) ctx.fillRect(-1.1, ry, 2.2, 0.8);
    fill(ctx, "#b08a4a", () => {
      for (let i = 0; i < 12; i++) {
        const a = (i / 12) * TAU;
        const r = i % 2 ? 3.2 : 4.3;
        ctx.lineTo(Math.cos(a) * r, -3 + Math.sin(a) * r * 0.55);
      }
      ctx.closePath();
    });
    fill(ctx, glow, () => ctx.arc(0, -3, 1.2, 0, TAU));
    fill(ctx, "#4a3020", () => ctx.rect(-1, -1.5, 2, 3.5));
    return;
  }
  fill(ctx, "rgba(255,255,255,0.45)", () => ctx.rect(-W / 2 + 0.6, -L, 0.9, L - 4));
  fill(ctx, it?.hilt ?? (W >= 4 ? "#d8b04a" : "#8a6a2a"), () => ctx.roundRect(-4.5, -4, 9, 2, 1)); // 雙手劍：金色護手（第 8 版）
  fill(ctx, "#4a3020", () => ctx.rect(-1, -2, 2, W >= 4 ? 8 : 4)); // 雙手劍握柄長到 +6，兩隻手疊著握
}

export function dagger(ctx: Ctx, it: QItem | undefined): void {
  const [c] = wc(it, "iron");
  fill(ctx, c, () => {
    ctx.moveTo(-1.3, -2);
    ctx.lineTo(0, -10);
    ctx.lineTo(1.3, -2);
    ctx.closePath();
  });
  fill(ctx, "#4a3020", () => ctx.rect(-2.5, -2.5, 5, 1.5));
  fill(ctx, "#4a3020", () => ctx.rect(-0.8, -1, 1.6, 3));
}

/** 魔導劍源晶槽的光色：預設藍紫光；有元素時換元素色。 */
export const arcaneGlowColor = (it: QItem | undefined, tint: (e: string | undefined) => string | undefined): string => (it?.element ? tint(it.element) : undefined) ?? "#9a86ff";
/** 杖頭光點的顏色。 */
export const staffOrbColor = (it: QItem | undefined): string => (it?.element ? STAFF_ORB[it.element] : undefined) ?? it?.glow ?? "#c8bcff";
/** 法球的顏色。 */
export const orbColor = (it: QItem | undefined): string => it?.color ?? "#a898ff";

// Q 版短弓：弧半徑 8.5、張角 ±1.2 → 弓高約 16、弦離弓把 5.4
export const BOW_R = 8.5;
export const BOW_A = 1.2;
export const BOW_EY = BOW_R - Math.cos(BOW_A) * BOW_R;

export interface QWeaponDef {
  len: number;
  hold: { side: number; front: number };
  draw: (c: Ctx, it: QItem | undefined) => void;
}

const STAFF_ORB: Readonly<Record<string, string>> = { fire: "#ff6a1a", water: "#4aa8ff", ice: "#8fe3ff", lightning: "#fff36b", poison: "#7ddc3a", wind: "#7fe0c0", earth: "#b0814a", holy: "#ffd75e", shadow: "#9a6ad8" };

function whipDraw(c: Ctx, it: QItem | undefined): void {
  c.strokeStyle = it?.color ?? "#5e3b1f";
  c.lineWidth = 1.4;
  c.lineCap = "round";
  if (S.POSE && typeof S.POSE.wpn === "number") {
    fill(c, "#4a3020", () => c.roundRect(-1.1, -5, 2.2, 6.5, 0.8));
    // 出招（6M／6N 片段）：鞭身拉直往前抽出去，梢端一點彎
    c.beginPath();
    c.moveTo(0, -5);
    c.quadraticCurveTo(1.2, -15, 0, -24);
    c.stroke();
    c.lineWidth = 0.8;
    c.beginPath();
    c.moveTo(0, -24);
    c.quadraticCurveTo(-1.5, -27, 0.6, -29);
    c.stroke();
    return;
  }
  // 待機（第 7 版）：鞭身從握把頂端垂下來（照畫面的「下」），鞭梢在腳邊小幅甩動
  const m = getM(c);
  const det = m.a * m.d - m.b * m.c || 1;
  const loc = (x: number, y: number): P2 => {
    const v: P2 = [(m.d * x - m.c * y) / det, (-m.b * x + m.a * y) / det];
    const l = Math.hypot(v[0], v[1]) || 1;
    return [v[0] / l, v[1] / l];
  };
  const D = loc(0, 1);
  const N = loc(S.WEST ? -1 : 1, 0);
  const E: P2 = [D[0] * 4.2, D[1] * 4.2];
  const w = Math.sin(pz("lash") * TAU) * 1.6;
  const at = (u: number, v: number): P2 => [E[0] + u * D[0] + v * N[0], E[1] + u * D[1] + v * N[1]];
  c.save();
  c.lineWidth = 2.2;
  c.strokeStyle = "#4a3020";
  c.beginPath();
  c.moveTo(-D[0] * 1.6, -D[1] * 1.6);
  c.lineTo(E[0], E[1]);
  c.stroke();
  c.restore();
  const p1 = at(2, 0.3);
  const p2 = at(4, 0.8 + w * 0.3);
  const p3 = at(5.4, 2.2 + w * 0.6);
  const p4 = at(5.2, 6.5 + w);
  c.beginPath();
  c.moveTo(E[0], E[1]);
  c.bezierCurveTo(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1]);
  c.stroke();
  c.lineWidth = 0.8;
  c.beginPath();
  c.moveTo(p3[0], p3[1]);
  const q = at(5.8, 4.4 + w);
  c.quadraticCurveTo(q[0], q[1], p4[0], p4[1]);
  c.stroke();
}

function bowDraw(c: Ctx, it: QItem | undefined): void {
  const [k] = wc(it, "wood");
  const BP = S.BOWP;
  const pull = BP && BP.pull != null ? BP.pull : typeof S.POSE?.pull === "number" ? S.POSE.pull : 0;
  const ex = Math.sin(BOW_A) * BOW_R;
  const ey = BOW_EY;
  const st = (): void => {
    if (S.BOWM) {
      c.save();
      setM(c, S.BOWM);
      c.stroke();
      c.restore();
    } else c.stroke();
  };
  c.strokeStyle = "#e8e8e8";
  c.lineWidth = 0.8;
  c.beginPath();
  c.moveTo(-ex, ey);
  c.lineTo(0, ey + pull);
  c.lineTo(ex, ey);
  st();
  c.strokeStyle = k;
  c.lineWidth = 2.2;
  c.lineCap = "round";
  c.beginPath();
  c.arc(0, BOW_R, BOW_R, -Math.PI / 2 - BOW_A, -Math.PI / 2 + BOW_A);
  st();
  fill(c, "#4a3020", () => c.roundRect(-1.6, -1.6, 3.2, 3.2, 0.8)); // 弓把（皮纏）
  if (!(BP && BP.noArrow) && (pull > 0.5 || pz("nock") > 0 || (BP && BP.nock))) {
    c.strokeStyle = "#c8a070";
    c.lineWidth = 0.9;
    c.beginPath();
    c.moveTo(0, ey + pull);
    c.lineTo(0, -6);
    st();
    if (S.BOWM) {
      // 斜看的弓：箭頭在畫面座標畫（不跟著壓扁）
      const m = getM(c);
      const inv = invM(S.BOWM);
      const P = (x: number, y: number): P2 => {
        const q = tp(m, x, y);
        return tp(inv, q[0], q[1]);
      };
      const a0 = P(0, ey);
      const a1 = P(0, -8);
      const l = Math.hypot(a1[0] - a0[0], a1[1] - a0[1]) || 1;
      const ux = (a1[0] - a0[0]) / l;
      const uy = (a1[1] - a0[1]) / l;
      c.save();
      setM(c, S.BOWM);
      fill(c, "#c3ccd6", () => {
        c.moveTo(a1[0] - ux * 2.4 - uy * 1.2, a1[1] - uy * 2.4 + ux * 1.2);
        c.lineTo(a1[0], a1[1]);
        c.lineTo(a1[0] - ux * 2.4 + uy * 1.2, a1[1] - uy * 2.4 - ux * 1.2);
        c.closePath();
      });
      c.restore();
    } else
      fill(c, "#c3ccd6", () => {
        c.moveTo(-1.2, -5.6);
        c.lineTo(0, -8);
        c.lineTo(1.2, -5.6);
        c.closePath();
      });
  }
}

/** 武器表（QW）：len＝握把到作用端；hold＝預設握法（側面相對手臂、正面絕對角度）。 */
export const QW: Readonly<Record<string, QWeaponDef>> = {
  ...QW_HELD, // QK-8：修士手持物（拂塵、符紙、傀儡線），qNpcHeld.ts
  sword: { len: 19, hold: { side: 0.75, front: -0.12 }, draw: (c, it) => sword(c, it, 16, 2.6) },
  greatsword: { len: 27, hold: { side: 0.75, front: -0.25 }, draw: (c, it) => sword(c, it, 24, 4) },
  // 拄劍（關鍵姿勢）用的雙手劍：側面劍身 14、正面背面 11.7，劍尖落在地面線
  greatsword_k: { len: 17, hold: { side: 0.75, front: -0.25 }, draw: (c, it) => sword(c, it, 14, 4) },
  greatsword_kf: { len: 14.7, hold: { side: 0.75, front: -0.25 }, draw: (c, it) => sword(c, it, 11.7, 4) },
  arcane_blade: { len: 19, hold: { side: 0.75, front: -0.12 }, draw: (c, it) => sword(c, { ...(it ?? { kind: "sword" }), form: "arcane" }, 16, 2.6) },
  saber: {
    len: 19,
    hold: { side: 0.75, front: -0.12 },
    draw: (c, it) => {
      const [k] = wc(it, "steel");
      fill(c, k, () => {
        c.moveTo(-1.3, -3);
        c.quadraticCurveTo(-2.2, -12, 0.6, -19);
        c.lineTo(1.9, -18.4);
        c.quadraticCurveTo(0.6, -11, 1.3, -3);
        c.closePath();
      });
      fill(c, "rgba(255,255,255,0.45)", () => {
        c.moveTo(-0.6, -4);
        c.quadraticCurveTo(-1.3, -11, 0.4, -16.5);
        c.lineTo(0.8, -16.3);
        c.quadraticCurveTo(-0.3, -11, 0.2, -4);
        c.closePath();
      });
      fill(c, "#8a6a2a", () => c.ellipse(0, -3, 3.4, 1.4, 0, 0, TAU));
      fill(c, "#3a2a1a", () => c.rect(-1, -2, 2, 4.2));
    },
  },
  dagger: { len: 10, hold: { side: 0.75, front: -0.6 }, draw: dagger },
  paired: { len: 10, hold: { side: 0.75, front: -0.45 }, draw: dagger }, // 成對武器：一手一把（第二把在副手）
  axe: {
    len: 18,
    hold: { side: 0.75, front: -0.3 },
    draw: (c, it) => {
      const [k] = wc(it, "iron");
      fill(c, "#6a4420", () => c.rect(-1, -18, 2, 20));
      fill(c, k, () => {
        c.moveTo(1, -17);
        c.quadraticCurveTo(9, -18, 8, -10);
        c.lineTo(1, -12);
        c.closePath();
      });
    },
  },
  hammer: {
    len: 22,
    hold: { side: 0.75, front: -0.25 },
    draw: (c, it) => {
      const [k, d] = wc(it, "iron");
      fill(c, "#6a4420", () => c.rect(-1, -18, 2, 21));
      if (it?.form === "mace") fill(c, k, () => c.arc(0, -19, 4, 0, TAU));
      else fill(c, k, () => c.roundRect(-5.5, -22, 11, 6, 1.2));
      fill(c, d, () => c.rect(-5.5, -19.5, 11, 1));
    },
  },
  spear: {
    len: 42,
    hold: { side: 0.15, front: 0 },
    draw: (c, it) => {
      const [k] = wc(it, "steel");
      fill(c, "#6a4420", () => c.rect(-0.9, -34, 1.8, 45)); // 槍桿到 +11，後手握在 +8
      fill(c, k, () => {
        c.moveTo(0, -42);
        c.lineTo(2.4, -34);
        c.lineTo(-2.4, -34);
        c.closePath();
      });
      fill(c, "#8a6a2a", () => c.rect(-1.6, -34.5, 3.2, 1.4));
    },
  },
  scythe: {
    len: 26,
    hold: { side: 0.6, front: -0.15 },
    draw: (c, it) => {
      const [k] = wc(it, "steel");
      fill(c, "#6a4420", () => c.rect(-1, -26, 2, 35)); // 柄到 +9，後手握在 +6
      fill(c, k, () => {
        c.moveTo(0, -26);
        c.quadraticCurveTo(12, -28, 14, -18);
        c.quadraticCurveTo(8, -23, 0, -23);
        c.closePath();
      });
    },
  },
  whip: { len: 18, hold: { side: 0.75, front: -0.25 }, draw: whipDraw },
  gauntlet: {
    len: 4,
    hold: { side: 1.0, front: 0 },
    draw: (c, it) => {
      // 拳套戴在手上（arm 畫拳套本體）；這裡只畫和手重疊的拳面，拳刃、爪從指節往前伸
      const [k] = wc(it, "steel");
      fill(c, k, () => c.arc(0, 0, 2.9, 0, TAU));
      if (it?.form === "katar" || it?.form === "claw")
        fill(c, k, () => {
          c.moveTo(-1.2, -2.6);
          c.lineTo(0, -9);
          c.lineTo(1.2, -2.6);
          c.closePath();
        });
    },
  },
  staff: {
    len: 32,
    hold: { side: 0, front: 0 },
    draw: (c, it) => {
      const orb = staffOrbColor(it);
      fill(c, "#6a4420", () => c.rect(-1.1, -30, 2.2, 39)); // 杖身到 +9，下手握在 +6
      const g = pz("glow");
      if (!(pz("glowLayer") > 0)) {
        // QK-7：待機時光暈由疊加層畫（weaponGlow.ts）
        c.save();
        c.globalAlpha = 0.35 + 0.35 * g;
        fill(c, orb, () => c.arc(0, -32, 6.5 + 2 * g, 0, TAU));
        c.restore();
      }
      fill(c, orb, () => c.arc(0, -32, 3.6, 0, TAU));
      fill(c, "rgba(255,255,255,0.8)", () => c.arc(-1.2, -33.2, 1.1, 0, TAU));
    },
  },
  orb: {
    len: 6,
    hold: { side: 0.6, front: 0 },
    draw: (c, it) => {
      const orb = orbColor(it);
      const g = pz("glow");
      const oy = -3.4 + pz("orbY");
      c.save();
      c.globalAlpha = 0.35 + 0.35 * g;
      fill(c, orb, () => c.arc(0, oy, 6 + 2 * g, 0, TAU));
      c.restore();
      fill(c, orb, () => c.arc(0, oy, 3.6, 0, TAU));
      fill(c, "rgba(255,255,255,0.8)", () => c.arc(-1.2, oy - 1.2, 1.1, 0, TAU));
    },
  },
  // 弓：弓把在原點（持弓手包住它），弓臂往 ±x 彎、弓背朝 −y（＝箭的方向），弦在 +y
  bow: { len: 4, hold: { side: Math.PI / 2, front: -Math.PI / 2 }, draw: bowDraw },
  crossbow: {
    len: 14,
    hold: { side: 2.2, front: Math.PI },
    draw: (c, it) => {
      const [k] = wc(it, "iron");
      fill(c, "#7a5232", () => c.roundRect(-1.3, -12, 2.6, 16, 1));
      c.strokeStyle = "rgba(240,240,240,0.85)";
      c.lineWidth = 0.7;
      c.beginPath();
      c.moveTo(-8, -8);
      c.lineTo(0, -5.5);
      c.lineTo(8, -8);
      c.stroke();
      c.strokeStyle = k;
      c.lineWidth = 2;
      c.lineCap = "round";
      c.beginPath();
      c.moveTo(-8, -8);
      c.quadraticCurveTo(0, -13.5, 8, -8);
      c.stroke();
      c.strokeStyle = "#c8a070";
      c.lineWidth = 0.9;
      c.beginPath();
      c.moveTo(0, -5.5);
      c.lineTo(0, -14);
      c.stroke();
    },
  },
  gun: {
    len: 17,
    hold: { side: 2.3, front: Math.PI },
    draw: (c, it) => {
      const form = it?.form ?? "rifle";
      const L = ({ pistol: 7, rifle: 17, shotgun: 15, energy: 12 } as Record<string, number>)[form] ?? 17;
      const [k, d] = wc(it, "iron");
      if (form === "rifle" || form === "shotgun") fill(c, "#7a5232", () => c.roundRect(-1.8, 0, 3.6, 6.5, 1));
      fill(c, "#3a2a1c", () => c.roundRect(-1.2, -1, 2.4, 4, 0.8));
      fill(c, form === "energy" ? "#e8edf2" : k, () => c.roundRect(-1.3, -L, form === "shotgun" ? 3.2 : 2.6, L + 1, 1));
      fill(c, d, () => c.rect(-1.5, -L * 0.55, 3, 1.1));
    },
  },
};

const ALIAS: Readonly<Record<string, string>> = { fist: "gauntlet", longgun: "gun", shotgun: "gun", pistol: "gun", dual_dagger: "paired", puppet_cross: "puppet_strings" };
const GUN_FORM: Readonly<Record<string, string>> = { longgun: "rifle", shotgun: "shotgun", pistol: "pistol" };

export interface QWeaponRef {
  W: QWeaponDef;
  item: QItem;
  kind: string;
  key: string;
}

/** 手持物 → 武器表的項目（不在表內＝null，退回 pdHeld）。 */
export function qWeapon(it: QItem | null | undefined): QWeaponRef | null {
  if (!it) return null;
  let kind = ALIAS[it.kind] ?? it.kind;
  if (kind === "sword" && it.form === "arcane") kind = "arcane_blade";
  const W = QW[kind];
  if (!W) return null;
  const gf = GUN_FORM[it.kind];
  const item: QItem = ALIAS[it.kind] === "gun" && gf !== undefined ? { ...it, form: gf } : it;
  return { W, item, kind, key: kind };
}

/** 掛在手上：在主手手掌 hand 畫武器，a＝武器的世界角度。short：雙手劍用拄劍長度；offL：副手握點（自測用）；mg：主手握在武器座標 (0,mg)；M：自訂 2×2 變換。 */
export function mainWeapon(ctx: Ctx, it: QItem | null | undefined, hand: readonly number[], a: number, view: string, short: boolean | "f" = false, offL: readonly number[] | null = null, mg = 0, M: readonly number[] | null = null): void {
  const q0 = qWeapon(it);
  const q = q0 && short && q0.kind === "greatsword" ? { ...q0, W: short === "f" ? QW["greatsword_kf"]! : QW["greatsword_k"]!, key: short === "f" ? "greatsword_kf" : "greatsword_k" } : q0;
  const hx = hand[0] ?? 0;
  const hy = hand[1] ?? 0;
  if (!q) {
    if (it) pdHeld(ctx, it, hx, view !== "back");
    return;
  }
  ctx.save();
  ctx.translate(hx, hy);
  if (M) ctx.transform(M[0] ?? 1, M[1] ?? 0, M[2] ?? 0, M[3] ?? 1, 0, 0);
  else ctx.rotate(a);
  if (mg) ctx.translate(0, -mg);
  q.W.draw(ctx, q.item);
  const probe = S.POSE?.probe;
  if (probe) {
    const m = getM(ctx);
    probe(q.kind, tp(m, 0, 0), tp(m, 0, -q.W.len), view, offL ? tp(m, offL[0] ?? 0, offL[1] ?? 0) : null, m, q.key);
  }
  ctx.restore();
}

/** 副手的匕首：在手的座標系裡畫，角度相對手臂。 */
export function offDagger(ctx: Ctx, it: QItem | undefined, hand: P2, a: number): void {
  ctx.save();
  ctx.translate(hand[0], hand[1]);
  ctx.rotate(a);
  dagger(ctx, it);
  ctx.restore();
}

// ---------- 雙手武器：副手握點 off、正面角度 front、會伸出去的點 pts、刃與柄的分界 edge ----------
export interface TwoDef {
  off: readonly number[] | "string";
  front: number;
  edge?: number;
}
export const TWO: Readonly<Record<string, TwoDef>> = {
  greatsword: { off: [0, 4], front: -0.85, edge: -3 },
  spear: { off: [0, 8], front: -0.75, edge: -34 },
  scythe: { off: [0, 6], front: -0.75, edge: -23 },
  staff: { off: [0, 6], front: -0.75 },
  bow: { off: "string", front: -Math.PI / 2 },
  crossbow: { off: [0, -6], front: Math.PI - 0.8 },
  gun: { off: [0, -8], front: Math.PI - 0.85 },
};

// ---------- 樣張 paperdoll.js 的 drawWeapon／drawWeapon2：盾、書、法球與 QW 沒有的手持物（在手的 x、y −9.5）----------
const GUN_PD: Readonly<Record<string, string>> = { longgun: "rifle", shotgun: "shotgun", pistol: "pistol" };
const PD2 = new Set(["crossbow", "fist", "scythe", "whip", "hammer", "spear", "orb"]);

/** 畫一件手持物在 (x, −9.5)，front＝正面朝向（側面、背面的鏡像握法）。不認得的 kind 不畫（QK-3 補）。 */
export function pdHeld(ctx: Ctx, it0: QItem, x: number, front: boolean): void {
  let it = it0;
  const gf = GUN_PD[it.kind];
  if (gf !== undefined) it = { ...it, kind: "gun", form: gf };
  if (PD2.has(it.kind) || isTowerLike(it)) {
    pdHeld2(ctx, it, x, front);
    return;
  }
  const [c, d] = colors(it);
  ctx.save();
  ctx.translate(x, -9.5);
  switch (it.kind) {
    case "sword":
    case "greatsword": {
      const L = it.kind === "greatsword" ? 24 : 16;
      const W = it.kind === "greatsword" ? 4 : 2.6;
      ctx.rotate(front ? -0.25 : 0.25);
      fill(ctx, c, () => {
        ctx.moveTo(-W / 2, -3);
        ctx.lineTo(-W / 2, -L);
        ctx.lineTo(0, -L - 3);
        ctx.lineTo(W / 2, -L);
        ctx.lineTo(W / 2, -3);
        ctx.closePath();
      });
      fill(ctx, "rgba(255,255,255,0.45)", () => ctx.rect(-W / 2 + 0.6, -L, 0.9, L - 4));
      fill(ctx, it.hilt ?? "#8a6a2a", () => rr(ctx, -4.5, -4, 9, 2, 1));
      fill(ctx, "#4a3020", () => ctx.rect(-1, -2, 2, 4));
      break;
    }
    case "dagger":
      ctx.rotate(front ? -0.6 : 0.6);
      fill(ctx, c, () => {
        ctx.moveTo(-1.3, -2);
        ctx.lineTo(0, -10);
        ctx.lineTo(1.3, -2);
        ctx.closePath();
      });
      fill(ctx, "#4a3020", () => ctx.rect(-2.5, -2.5, 5, 1.5));
      break;
    case "axe":
      ctx.rotate(front ? -0.3 : 0.3);
      fill(ctx, "#6a4420", () => ctx.rect(-1, -18, 2, 20));
      fill(ctx, c, () => {
        ctx.moveTo(1, -17);
        ctx.quadraticCurveTo(9, -18, 8, -10);
        ctx.lineTo(1, -12);
        ctx.closePath();
      });
      break;
    case "gun": {
      const L = ({ pistol: 7, rifle: 17, shotgun: 15, energy: 12 } as Record<string, number>)[it.form ?? ""] ?? 7;
      ctx.rotate(front ? 0.35 : -0.35);
      const s = front ? -1 : 1;
      fill(ctx, "#3a2a1c", () => rr(ctx, -1.2, -1, 2.4, 5, 0.8));
      if (it.form === "rifle" || it.form === "shotgun") fill(ctx, it.form === "shotgun" ? "#7a5232" : d, () => rr(ctx, s > 0 ? -6 : 1, -3, 5, 3, 1));
      fill(ctx, c, () => rr(ctx, s > 0 ? -1 : -L, -3.2, L + 1, it.form === "shotgun" ? 3.2 : 2.6, 1));
      break;
    }
    case "shield_round":
      fill(ctx, d, () => ctx.arc(0, -4, 7.5, 0, TAU));
      fill(ctx, c, () => ctx.arc(0, -4, 6, 0, TAU));
      fill(ctx, it.trim ?? "#e8bb48", () => ctx.arc(0, -4, 2, 0, TAU));
      break;
    case "shield_kite":
      fill(ctx, d, () => {
        ctx.moveTo(-7, -13);
        ctx.lineTo(7, -13);
        ctx.lineTo(6.5, -2);
        ctx.lineTo(0, 6);
        ctx.lineTo(-6.5, -2);
        ctx.closePath();
      });
      fill(ctx, c, () => {
        ctx.moveTo(-5.5, -11.5);
        ctx.lineTo(5.5, -11.5);
        ctx.lineTo(5, -2.5);
        ctx.lineTo(0, 3.8);
        ctx.lineTo(-5, -2.5);
        ctx.closePath();
      });
      fill(ctx, it.trim ?? "#e8e0c8", () => ctx.rect(-0.9, -11, 1.8, 13));
      fill(ctx, it.trim ?? "#e8e0c8", () => ctx.rect(-5, -7, 10, 1.8));
      break;
    case "tome":
      fill(ctx, c, () => rr(ctx, -4.5, -6, 9, 8, 1));
      fill(ctx, "#f2ead6", () => ctx.rect(-3.5, -5.5, 7, 1.2));
      fill(ctx, it.trim ?? "#e8bb48", () => ctx.arc(0, -2, 1.6, 0, TAU));
      break;
    default:
      break;
  }
  ctx.restore();
}

function pdHeld2(ctx: Ctx, it: QItem, x: number, front: boolean): void {
  const [c, d] = colors(it);
  ctx.save();
  ctx.translate(x, -9.5);
  switch (it.kind) {
    case "crossbow": {
      ctx.rotate(front ? 0.35 : -0.35);
      fill(ctx, "#7a5232", () => rr(ctx, front ? -12 : 0, -3, 12, 2.6, 1));
      const tip = front ? -10 : 10;
      ctx.strokeStyle = c;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(tip, -9);
      ctx.quadraticCurveTo(tip + (front ? -2 : 2), -2, tip, 5);
      ctx.stroke();
      ctx.strokeStyle = "rgba(240,240,240,0.8)";
      ctx.lineWidth = 0.7;
      ctx.beginPath();
      ctx.moveTo(tip, -9);
      ctx.lineTo(tip + (front ? 3 : -3), -2);
      ctx.lineTo(tip, 5);
      ctx.stroke();
      break;
    }
    case "fist":
      fill(ctx, c, () => rr(ctx, -2.5, -3, 5, 5, 1.5));
      break;
    case "scythe":
      ctx.rotate(front ? -0.15 : 0.15);
      fill(ctx, "#6a4420", () => ctx.rect(-1, -26, 2, 30));
      fill(ctx, c, () => {
        ctx.moveTo(0, -26);
        ctx.quadraticCurveTo(front ? 12 : -12, -28, front ? 14 : -14, -18);
        ctx.quadraticCurveTo(front ? 8 : -8, -23, 0, -23);
        ctx.closePath();
      });
      break;
    case "hammer":
      ctx.rotate(front ? -0.25 : 0.25);
      fill(ctx, "#6a4420", () => ctx.rect(-1, -18, 2, 21));
      if (it.form === "mace") fill(ctx, c, () => ctx.arc(0, -19, 4, 0, TAU));
      else fill(ctx, c, () => rr(ctx, -5.5, -22, 11, 6, 1.2));
      fill(ctx, d, () => ctx.rect(-5.5, -19.5, 11, 1));
      break;
    case "spear":
      fill(ctx, "#6a4420", () => ctx.rect(-0.9, -34, 1.8, 40));
      fill(ctx, c, () => {
        ctx.moveTo(0, -42);
        ctx.lineTo(2.4, -34);
        ctx.lineTo(-2.4, -34);
        ctx.closePath();
      });
      break;
    case "orb": {
      const orb = (it.element ? S.hooks!.tint(it.element) : undefined) ?? c;
      ctx.fillStyle = orb;
      ctx.globalAlpha = 0.35;
      ctx.beginPath();
      ctx.arc(0, -6, 6, 0, TAU);
      ctx.fill();
      ctx.globalAlpha = 1;
      fill(ctx, orb, () => ctx.arc(0, -6, 3.6, 0, TAU));
      fill(ctx, "rgba(255,255,255,0.8)", () => ctx.arc(-1.2, -7.2, 1.1, 0, TAU));
      break;
    }
    case "shield_kite":
      // 雲紋碑盾（RG-4 持盾弟子；RG-5 起玩家也能用）：照樣張 rgUnits.js front()，錨點同塔盾
      if (it.form === "sect_great") {
        sectShieldFront(ctx, it);
        break;
      }
      // 熔殼塔盾（RG-5，玩家形制）：照樣張 rgPlayerShield.js shellFront()，錨點同塔盾
      if (it.form === "molten_shell") {
        shellFront(ctx, it);
        break;
      }
      // 塔盾：長方形大盾
      fill(ctx, d, () => rr(ctx, -7.5, -16, 15, 21, 2));
      fill(ctx, c, () => rr(ctx, -6, -14.5, 12, 18, 1.5));
      fill(ctx, "#e8e0c8", () => ctx.rect(-0.9, -14, 1.8, 17));
      break;
    case "whip":
      fill(ctx, "#4a3020", () => ctx.rect(-1, -4, 2, 5));
      ctx.strokeStyle = c;
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      ctx.moveTo(0, -4);
      ctx.bezierCurveTo(front ? -8 : 8, -8, front ? -4 : 4, 6, front ? -12 : 12, 8);
      ctx.stroke();
      break;
    default:
      break;
  }
  ctx.restore();
}
