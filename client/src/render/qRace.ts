// Q 版 10 族部件（QK-1 第 6 項；照 docs/art/sample/raceArt.js）：體型、尾巴、龍翼與背刺、臉部紋路、耳朵（含獸耳族四種）、角、帽子的避讓。
// 外觀全部由 look 的欄位決定（都選填，不認得的值＝沒有）。頭心一律在 (0,−29)、半寬約 8.5。
import type { Ctx } from "./artDraw";
import { fill, mix, TAU, type QItem, type QLook, type QView } from "./qCore";

const dark = (c: string, t = 0.3): string => mix(c, "#000000", t);

interface Cover {
  top?: boolean;
  side?: boolean;
  hood?: boolean;
  tall?: boolean;
}
/** 頭部裝備遮住哪裡：top＝頭頂、side＝兩側、hood＝兜帽（有耳朵版）、tall＝高帽。 */
export const COVERS: Readonly<Record<string, Cover>> = {
  helmet: { top: true, side: true },
  greathelm: { top: true, side: true },
  horned_helm: { top: true, side: true },
  hood: { top: true, side: true, hood: true },
  cap: { top: true },
  bandana: { top: true },
  crown: {},
  wide_hat: { top: true, tall: true },
  wizard_hat: { top: true, tall: true },
};
const coverOf = (head: QItem | undefined): Cover => (head ? (COVERS[head.kind] ?? { top: true }) : {});

/** 體型（整個人含裝備一起縮放）：stout ×(1.12, 0.88)、tall ×(0.96, 1.1)。 */
export function raceBuild(ctx: Ctx, look: QLook): void {
  if (look.build === "stout") ctx.scale(1.12, 0.88);
  else if (look.build === "tall") ctx.scale(0.96, 1.1);
}

type TailFn = (ctx: Ctx, look: QLook, view: QView) => void;
const TAIL: Readonly<Record<string, TailFn>> = {
  // 龍尾：根部寬、往末端收尖，背上一排背棘、腹面淺色一道
  dragon: (ctx, look) => {
    const c = look.scaleColor ?? "#a8784a";
    for (const t of [0.22, 0.42, 0.62, 0.8])
      fill(ctx, mix(c, "#ffffff", 0.3), () => {
        const x = 19 * t;
        const y = -16.5 + 15 * t;
        ctx.moveTo(x - 2, y + 1);
        ctx.lineTo(x + 0.4, y - 4.2);
        ctx.lineTo(x + 2.2, y + 1.2);
        ctx.closePath();
      });
    fill(ctx, c, () => {
      ctx.moveTo(0, -17);
      ctx.quadraticCurveTo(13, -15.5, 18.5, -3);
      ctx.lineTo(23, 1.5);
      ctx.lineTo(16.5, 0.6);
      ctx.quadraticCurveTo(9, -4.5, 0, -8);
      ctx.closePath();
    });
    fill(ctx, mix(c, "#f4e6c8", 0.45), () => {
      ctx.moveTo(0, -10);
      ctx.quadraticCurveTo(8.5, -7, 15.5, -0.6);
      ctx.lineTo(16.5, 0.6);
      ctx.quadraticCurveTo(9, -4.5, 0, -8);
      ctx.closePath();
    });
  },
  cat: (ctx, look) => {
    const c = look.tailColor ?? look.hairColor ?? "#5a3a22";
    ctx.strokeStyle = c;
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(0, -12);
    ctx.bezierCurveTo(9, -11, 12, -17, 10, -24);
    ctx.stroke();
    fill(ctx, c, () => ctx.arc(10, -24.2, 1.3, 0, TAU));
  },
  wolf: (ctx, look) => {
    const c = look.tailColor ?? look.hairColor ?? "#7a7a84";
    fill(ctx, c, () => {
      ctx.moveTo(0, -14);
      ctx.quadraticCurveTo(9, -14, 11, -6);
      ctx.quadraticCurveTo(12, 0, 8.5, 2);
      ctx.quadraticCurveTo(7, -5, 0, -9);
      ctx.closePath();
    });
    fill(ctx, mix(c, "#000000", 0.3), () => {
      ctx.moveTo(11.3, -2.5);
      ctx.quadraticCurveTo(12, 0.5, 8.5, 2);
      ctx.quadraticCurveTo(9.5, -0.5, 11.3, -2.5);
      ctx.closePath();
    });
  },
  rabbit: (ctx, look, view) => {
    // QK-6b：不再跟髮色混（橘髮會變桃色）→ 固定米白＋深 20% 描邊
    const c = look.tailColor ?? "#efe6d6";
    const x = view === "back" ? 0 : 6;
    fill(ctx, c, () => ctx.arc(x, -10.5, 2.4, 0, TAU));
    ctx.strokeStyle = dark(c, 0.2);
    ctx.lineWidth = 0.7;
    ctx.beginPath();
    ctx.arc(x, -10.5, 2.4, 0, TAU);
    ctx.stroke();
  },
  fox: (ctx, look) => {
    const c = look.tailColor ?? look.hairColor ?? "#d8762a";
    fill(ctx, c, () => {
      ctx.moveTo(0, -13);
      ctx.quadraticCurveTo(10, -14, 14, -6);
      ctx.quadraticCurveTo(17, 2, 11, 0);
      ctx.quadraticCurveTo(8, -6, 0, -9);
      ctx.closePath();
    });
    fill(ctx, "#f4ece0", () => ctx.ellipse(13.5, -1.5, 3, 2.4, 0.4, 0, TAU));
  },
  scaled: (ctx, look) => {
    const c = look.tailColor ?? dark(look.skin, 0.15);
    fill(ctx, c, () => {
      ctx.moveTo(0, -14);
      ctx.quadraticCurveTo(9, -12, 15, -3);
      ctx.lineTo(17, -1);
      ctx.quadraticCurveTo(8, -6, 0, -9);
      ctx.closePath();
    });
    ctx.strokeStyle = dark(c);
    ctx.lineWidth = 0.8;
    for (const t of [0.3, 0.55, 0.8]) {
      ctx.beginPath();
      ctx.moveTo(15 * t, -13 + 10 * t);
      ctx.lineTo(15 * t + 1.5, -10 + 8 * t);
      ctx.stroke();
    }
  },
  demon: (ctx, look) => {
    const c = look.tailColor ?? dark(look.skin, 0.25);
    ctx.strokeStyle = c;
    ctx.lineWidth = 1.8;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(0, -12);
    ctx.quadraticCurveTo(12, -10, 13, -2);
    ctx.stroke();
    fill(ctx, c, () => {
      ctx.moveTo(13, -2);
      ctx.lineTo(10.5, 1.5);
      ctx.lineTo(13, 4.5);
      ctx.lineTo(15.5, 1.5);
      ctx.closePath();
    });
  },
};

function wings(ctx: Ctx, look: QLook): void {
  if (!look.wings) return;
  const c = look.scaleColor ?? "#a8784a";
  const m = mix(c, "#ffffff", 0.25);
  for (const s of [-1, 1]) {
    fill(ctx, dark(c, 0.15), () => {
      ctx.moveTo(s * 4, -22);
      ctx.lineTo(s * 15, -34);
      ctx.lineTo(s * 16, -22);
      ctx.lineTo(s * 13, -16);
      ctx.lineTo(s * 9, -19);
      ctx.lineTo(s * 6, -15);
      ctx.closePath();
    });
    ctx.strokeStyle = m;
    ctx.lineWidth = 0.9;
    ctx.beginPath();
    ctx.moveTo(s * 5, -21);
    ctx.lineTo(s * 15, -33);
    ctx.moveTo(s * 9, -25);
    ctx.lineTo(s * 13, -16);
    ctx.stroke();
  }
}
function spines(ctx: Ctx, look: QLook): void {
  if (!look.spines) return;
  const c = look.scaleColor ?? "#a8784a";
  for (const [x, y] of [[-5, -24], [0, -25], [5, -24]] as const)
    fill(ctx, mix(c, "#ffffff", 0.2), () => {
      ctx.moveTo(x - 1.8, y + 2);
      ctx.lineTo(x, y - 4);
      ctx.lineTo(x + 1.8, y + 2);
      ctx.closePath();
    });
}
const tailKind = (look: QLook): string | undefined => (look.tail === "fox" && look.beastEars && TAIL[look.beastEars] ? look.beastEars : look.tail);

/** 尾巴（含龍翼、背刺）：正面、側面畫在身體後面；背面畫在披風之上。side：側面 1、正面背面 0。 */
export function raceTail(ctx: Ctx, look: QLook, view: QView, side: number): void {
  wings(ctx, look);
  spines(ctx, look);
  const kind = tailKind(look);
  const draw = kind ? TAIL[kind] : undefined;
  if (!draw || !kind) return;
  ctx.save();
  const dir = side === 1 ? -1 : side === -1 ? 1 : view === "back" ? -1 : 1;
  ctx.scale(dir, 1);
  if (kind === "dragon" && view !== "side") ctx.scale(0.74, 1);
  if (view === "back") ctx.translate(0, 2);
  draw(ctx, look, view);
  const ROOT: Record<string, [number, number, string]> = {
    fox: [-11, 2.3, look.tailColor ?? look.hairColor ?? "#d8762a"],
    dragon: [-12.5, 4.6, look.scaleColor ?? "#a8784a"],
    wolf: [-11.5, 2.6, look.tailColor ?? look.hairColor ?? "#7a7a84"],
    scaled: [-11.5, 2.6, look.tailColor ?? dark(look.skin, 0.15)],
  };
  const root = ROOT[kind];
  if (view === "back" && root) fill(ctx, root[2], () => ctx.ellipse(0.4, root[0], root[1] * 0.9, root[1], 0, 0, TAU));
  ctx.restore();
}

/** 臉：紋路、鬍子、獠牙（背面不畫）。遊戲資料的龍鱗 `dragonscale` 畫成 Q 版龍裔的「少量鱗」（dragonQ）。 */
export function raceFace(ctx: Ctx, look: QLook, view: QView, side: number, west = false): void {
  if (view === "back") return;
  const ex = side * 2.6;
  const pattern = look.pattern === "dragonscale" ? "dragonQ" : look.pattern;
  if (pattern === "scales") {
    fill(ctx, dark(look.skin, 0.22), () => {
      for (const [x, y] of [[-6, -25], [-4.5, -23.5], [5.5, -25], [4, -23.5], [-1, -35], [1.5, -35.5]] as const) {
        ctx.moveTo(ex + x + 1.1, y);
        ctx.arc(ex + x, y, 1.1, 0, Math.PI);
      }
    });
  } else if (pattern === "marks") {
    ctx.strokeStyle = look.markColor ?? "#2a8ac8";
    ctx.lineWidth = 1.1;
    for (const s of [-1, 1]) {
      ctx.beginPath();
      ctx.moveTo(ex + s * 4, -27);
      ctx.quadraticCurveTo(ex + s * 6, -25, ex + s * 5, -23);
      ctx.stroke();
    }
    ctx.beginPath();
    ctx.moveTo(ex - 1.5, -35);
    ctx.lineTo(ex, -33);
    ctx.lineTo(ex + 1.5, -35);
    ctx.stroke();
  } else if (pattern === "circuit") {
    // 晶能義體人：左半邊臉的金屬片（正面在畫面右；朝西在近側才看得到）
    const s = side === -1 ? -1 : 1;
    if (view !== "side" || west) {
      fill(ctx, "#9aa4b0", () => {
        ctx.arc(0, -29, 8.5, s > 0 ? -Math.PI / 2 : Math.PI / 2, s > 0 ? Math.PI / 2 : Math.PI * 1.5);
        ctx.closePath();
      });
      ctx.save();
      ctx.strokeStyle = "#4ae0d0";
      ctx.lineWidth = 0.9;
      ctx.shadowColor = "#4ae0d0";
      ctx.shadowBlur = 2;
      ctx.beginPath();
      ctx.moveTo(s * 1, -36);
      ctx.lineTo(s * 4, -33);
      ctx.lineTo(s * 4, -25);
      ctx.lineTo(s * 7, -23);
      ctx.stroke();
      fill(ctx, "#4ae0d0", () => ctx.arc(ex + s * 2.9, -28.5, 1.5, 0, TAU));
      ctx.restore();
    }
  }
  if (pattern === "dragonQ") {
    const c = look.scaleColor ?? "#a8784a";
    const dia = (x: number, y: number, r: number): void => {
      ctx.moveTo(x, y - r * 1.25);
      ctx.lineTo(x + r, y);
      ctx.lineTo(x, y + r * 1.25);
      ctx.lineTo(x - r, y);
      ctx.closePath();
    };
    const pts: ReadonlyArray<readonly [number, number, number]> = view === "side" ? [[2.2, -31.8, 1.1], [0.6, -34.4, 1.0]] : [[-6, -31.4, 1.1], [-4.7, -34.2, 1.0], [6, -31.4, 1.1], [4.7, -34.2, 1.0]];
    fill(ctx, c, () => {
      for (const [x, y, r] of pts) dia(x, y, r);
    });
    fill(ctx, c, () => dia(view === "side" ? 5.2 : 0, -35.6, 1.1));
    ctx.strokeStyle = dark(look.skin, 0.4);
    ctx.lineWidth = 0.9;
    ctx.lineCap = "round";
    for (const [x, ok] of [[ex + 2.9, side === 0 || side === 1], [ex - 2.9, side === 0 || side === -1]] as const)
      if (ok) {
        const o = x > ex ? 1 : -1;
        ctx.beginPath();
        ctx.moveTo(x - o * 1.4, -31.6);
        ctx.lineTo(x + o * 1.3, -31);
        ctx.stroke();
      }
  }
  if (look.ridge && pattern !== "dragonQ") {
    const c = look.scaleColor ?? "#a8784a";
    for (const y of [-35.5, -33, -30.5])
      fill(ctx, c, () => {
        ctx.moveTo(ex - 1.3, y + 1.2);
        ctx.lineTo(ex, y - 1.2);
        ctx.lineTo(ex + 1.3, y + 1.2);
        ctx.closePath();
      });
  }
  if (look.slitEyes) {
    // QK-1c（美術 PM 決定 2）：琥珀色（look.eyes，樣張 #9a4a12）、不發光；金色發光像貓
    const amber = look.eyes ?? "#9a4a12";
    for (const [x, ok] of [[ex + 2.9, side === 0 || side === 1], [ex - 2.9, side === 0 || side === -1]] as const)
      if (ok) {
        fill(ctx, amber, () => ctx.ellipse(x, -28.5, 1.5, 1.9, 0, 0, TAU));
        fill(ctx, "#1d1a22", () => ctx.rect(x - 0.35, -30.2, 0.7, 3.4));
      }
  }
  if (look.tusks)
    for (const s of view === "side" ? [1] : [-1, 1])
      fill(ctx, "#f4ecd8", () => {
        ctx.moveTo(ex + s * 2.5, -24);
        ctx.lineTo(ex + s * 3.4, -27);
        ctx.lineTo(ex + s * 4, -24);
        ctx.closePath();
      });
  if (look.beard) {
    const c = look.hairColor ?? "#8a4a22";
    fill(ctx, c, () => {
      ctx.moveTo(ex - 7, -27);
      ctx.quadraticCurveTo(ex - 7, -18, ex, -16);
      ctx.quadraticCurveTo(ex + 7, -18, ex + 7, -27);
      ctx.quadraticCurveTo(ex, -23, ex - 7, -27);
    });
    fill(ctx, dark(c), () => ctx.rect(ex - 2, -25.5, 4, 1)); // 嘴
  }
}

function sideEar(ctx: Ctx, look: QLook, s: number, kind: string): void {
  const c = look.skin;
  if (kind === "pointed")
    fill(ctx, c, () => {
      ctx.moveTo(s * 7.5, -31);
      ctx.lineTo(s * 15, -36);
      ctx.lineTo(s * 8, -27);
      ctx.closePath();
    });
  else {
    fill(ctx, mix(c, "#9fe6ff", 0.25), () => {
      ctx.moveTo(s * 7.5, -32);
      ctx.lineTo(s * 14, -36);
      ctx.lineTo(s * 15, -31);
      ctx.lineTo(s * 13, -27);
      ctx.lineTo(s * 8, -27);
      ctx.closePath();
    });
    ctx.strokeStyle = dark(c, 0.35);
    ctx.lineWidth = 0.7;
    for (const [x, y] of [[14, -35], [14.6, -31], [13, -27.5]] as const) {
      ctx.beginPath();
      ctx.moveTo(s * 8, -29.5);
      ctx.lineTo(s * x, y);
      ctx.stroke();
    }
  }
}

/** 獸耳族的四種耳朵：狐、貓、狼、兔；花色跟著髮色。側面兩耳一前一後（s −1 是後耳）。 */
function beastEar(ctx: Ctx, look: QLook, s: number, color: string | undefined, view: QView = "front"): void {
  const c = color ?? look.earColor ?? look.hairColor ?? "#d8762a";
  const kind = look.beastEars ?? "fox";
  const inner = "#f2c8b0";
  const sd = view === "side";
  const back = view === "back";
  const X = (x: number): number => (sd ? (s > 0 ? x - 4.5 : x - 8.6) : s * x);
  const dy = sd && s < 0 ? 1 : 0;
  const tri = (pts: ReadonlyArray<readonly [number, number]>, col: string): void =>
    fill(ctx, col, () => {
      pts.forEach(([x, y], i) => (i ? ctx.lineTo(X(x), y + dy) : ctx.moveTo(X(x), y + dy)));
      ctx.closePath();
    });
  const showInner = !color && !back && !(sd && s < 0);
  if (kind === "cat") {
    tri([[2.8, -35.5], [5.4, -41.6], [8.4, -34.2]], c);
    if (showInner) tri([[4, -35.6], [5.4, -39.6], [7.1, -35]], inner);
    return;
  }
  if (kind === "wolf") {
    // QK-6b：直立、窄高；外緣一條寬深邊；內側灰（與狐耳區分）
    tri([[4, -36], [5.9, -47], [7.7, -34.8]], c);
    tri([[5.9, -47], [7.7, -34.8], [6.2, -35.3], [5.5, -43.8]], mix(c, "#000000", 0.38));
    if (showInner) tri([[4.8, -36], [5.5, -42.6], [6, -35.6]], "#a9a9b2");
    return;
  }
  if (kind === "rabbit") {
    fill(ctx, c, () => ctx.ellipse(X(4.2), -43 + dy, 2.2, 7.6, sd ? -0.25 : s * 0.12, 0, TAU));
    if (showInner) fill(ctx, inner, () => ctx.ellipse(X(4.2), -42.4 + dy, 1.1, 5.6, sd ? -0.25 : s * 0.12, 0, TAU));
    return;
  }
  tri([[2.5, -36], [6.5, -45], [8.5, -34]], c);
  if (showInner) tri([[4, -36], [6.3, -42], [7.3, -35.5]], inner);
}

/** 耳朵（phase "over"＝帽子之後畫）。 */
export function raceEars(ctx: Ctx, look: QLook, view: QView, side: number, head: QItem | undefined, phase: "under" | "over"): void {
  const kind = look.ears;
  if (!kind || kind === "none" || phase !== "over") return;
  const cov = coverOf(head);
  if (kind === "pointed" || kind === "fin") {
    if (cov.hood) return;
    const sides = side === 0 || view === "back" ? [-1, 1] : [-side];
    for (const s of sides) sideEar(ctx, look, s, kind);
    return;
  }
  if (kind === "beast") {
    if (cov.hood) {
      for (const s of [-1, 1]) beastEar(ctx, look, s * 0.9, head?.color ?? "#5a4a3a");
      return;
    }
    if (cov.top && !["cap", "bandana"].includes(head?.kind ?? "")) return;
    for (const s of [-1, 1]) beastEar(ctx, look, s, undefined, view === "side" && side ? "side" : view);
  }
}

/** 頭部裝備在有角時的調整：角盔改成一般頭盔、小帽變窄夾在兩角之間、寬帽與巫師帽抬高。 */
export function raceHat(ctx: Ctx, look: QLook, head: QItem | undefined, draw: (it: QItem) => void): void {
  if (!head) return;
  const horned = look.horns && look.horns !== "none";
  if (!horned) {
    draw(head);
    return;
  }
  if (head.kind === "horned_helm") {
    draw({ ...head, kind: "helmet" });
    return;
  }
  ctx.save();
  if (["cap", "bandana", "crown"].includes(head.kind)) {
    ctx.translate(0, -29);
    ctx.scale(0.8, 1);
    ctx.translate(0, 29);
  } else if (COVERS[head.kind]?.tall) ctx.translate(0, -5);
  draw(head);
  ctx.restore();
}

/** 角：永遠在最上層。 */
export function raceHorns(ctx: Ctx, look: QLook, view: QView): void {
  const kind = look.horns;
  if (!kind || kind === "none") return;
  const c = look.hornColor ?? "#efe6cc";
  for (const s of [-1, 1]) {
    if (kind === "dragon") {
      // 龍角：象牙色、兩對往後掃（不往上豎）；側面從額頭往後掃過頭頂，兩道深色環紋
      if (view === "side") {
        if (s > 0) continue;
        fill(ctx, c, () => {
          ctx.moveTo(3.8, -35.2);
          ctx.quadraticCurveTo(-3, -43.5, -13, -40.5);
          ctx.quadraticCurveTo(-5, -39.2, 0.2, -33.2);
          ctx.closePath();
        });
        fill(ctx, c, () => {
          ctx.moveTo(-1.5, -32.5);
          ctx.quadraticCurveTo(-6.5, -35.5, -11, -33);
          ctx.quadraticCurveTo(-6.5, -32.6, -2.5, -30.3);
          ctx.closePath();
        });
        ctx.strokeStyle = dark(c, 0.28);
        ctx.lineWidth = 0.7;
        for (const [x0, y0, x1, y1] of [[-2.5, -40.2, -1.2, -37.4], [-7, -41.3, -6.2, -39]] as const) {
          ctx.beginPath();
          ctx.moveTo(x0, y0);
          ctx.lineTo(x1, y1);
          ctx.stroke();
        }
        continue;
      }
      fill(ctx, c, () => {
        ctx.moveTo(s * 4, -36);
        ctx.quadraticCurveTo(s * 10, -41.5, s * 15.5, -38.5);
        ctx.quadraticCurveTo(s * 10.5, -37.5, s * 7.6, -33.4);
        ctx.closePath();
      });
      fill(ctx, c, () => {
        ctx.moveTo(s * 7.4, -31.6);
        ctx.quadraticCurveTo(s * 11.2, -33.6, s * 13.6, -30.6);
        ctx.quadraticCurveTo(s * 10.6, -30.6, s * 8.2, -29.4);
        ctx.closePath();
      });
      ctx.strokeStyle = dark(c, 0.28);
      ctx.lineWidth = 0.7;
      for (const [x0, y0, x1, y1] of [[8.4, -39.4, 8.8, -36.4], [11.8, -39.9, 11.6, -37.4]] as const) {
        ctx.beginPath();
        ctx.moveTo(s * x0, y0);
        ctx.lineTo(s * x1, y1);
        ctx.stroke();
      }
      continue;
    }
    if (view === "side") {
      // 側面：近側一支從頭頂往上、往後捲；遠側那支在後面、顏色深一點
      if (s > 0) continue;
      const big = kind !== "small";
      const horn = (dx: number, dy: number): void => {
        ctx.moveTo(3.2 + dx, -36.2 + dy);
        if (big) {
          ctx.quadraticCurveTo(5.5 + dx, -47 + dy, -6.5 + dx, -47.5 + dy);
          ctx.quadraticCurveTo(0.8 + dx, -44 + dy, -0.6 + dx, -37.4 + dy);
        } else {
          ctx.quadraticCurveTo(4.6 + dx, -42 + dy, 0.5 + dx, -44 + dy);
          ctx.quadraticCurveTo(2 + dx, -40.5 + dy, 0 + dx, -37 + dy);
        }
        ctx.closePath();
      };
      fill(ctx, dark(c, 0.25), () => horn(-3.2, 0.8));
      fill(ctx, c, () => horn(0, 0));
      continue;
    }
    if (kind === "small")
      fill(ctx, c, () => {
        ctx.moveTo(s * 3.5, -36);
        ctx.quadraticCurveTo(s * 6, -42, s * 9.5, -43);
        ctx.quadraticCurveTo(s * 7, -39, s * 6.5, -35.5);
        ctx.closePath();
      });
    else
      fill(ctx, c, () => {
        ctx.moveTo(s * 5, -35);
        ctx.quadraticCurveTo(s * 14, -38, s * 12, -47);
        ctx.quadraticCurveTo(s * 10.5, -41, s * 7.5, -38.5);
        ctx.quadraticCurveTo(s * 7, -36, s * 7, -33);
        ctx.closePath();
      });
  }
}

/** 10 族（樣張 RACES；畫廊與自測用，遊戲的種族外觀來自後端）。 */
export const Q_RACES: ReadonlyArray<readonly [string, string, QLook]> = [
  ["human", "人類", { skin: "#f1c9a5", hair: "short", hairColor: "#6a3d1e" }],
  ["elf", "精靈", { skin: "#f6e0cc", hair: "long", hairColor: "#e8e0c8", ears: "pointed", build: "tall" }],
  ["fox", "狐族", { skin: "#f1d0b0", hair: "short", hairColor: "#d8762a", ears: "beast", tail: "fox" }],
  ["dragonkin", "龍裔", { skin: "#d8a878", hair: "short", hairColor: "#3a2418", horns: "dragon", hornColor: "#efe6cc", pattern: "dragonQ", scaleColor: "#a8784a", tail: "dragon", eyes: "#9a4a12", slitEyes: true }], // QK-1b：豎瞳要畫（使用者 11-04 定案「…粗尾巴、豎瞳」；樣張第 7 版拿掉是樣張的錯）
  ["dwarf", "矮人", { skin: "#e8b890", hair: "short", hairColor: "#a8481e", beard: true, build: "stout" }],
  ["cyborg", "晶能義體人", { skin: "#e6c4a4", hair: "short", hairColor: "#2a2a34", pattern: "circuit" }],
  ["orc", "獸人", { skin: "#86a060", hair: "short", hairColor: "#1e1a14", tusks: true, build: "tall" }],
  ["fiend", "角魔", { skin: "#b07a7a", hair: "long", hairColor: "#1e1418", horns: "curved", hornColor: "#3a2a2a", tail: "demon" }],
  ["scalefolk", "鱗族", { skin: "#78b4aa", ears: "fin", pattern: "scales", eyes: "#103030" }],
  ["seafolk", "海民", { skin: "#b07a52", hair: "long", hairColor: "#2a8a9a", pattern: "marks", markColor: "#3aa8e0" }],
];
