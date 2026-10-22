// 技能部件圖示庫（Phase 3-17）：效果原語、狀態、表面、條件、代價、觸發與反應時機、複合接續記號、
// 修正的對象與改變內容。每個部件畫在以 (0, 0) 為中心、半徑約 10 的範圍內，顏色由呼叫端（`chip`）給。
// 技能圖示、組裝列、工坊選項、表面說明共用這一份；不認得的部件有預設：狀態畫「名稱第一個字」，
// 其他畫「?」，永遠畫得出來（不丟例外）。
import { statusName, surfaceName } from "../battle/glossary";
import { elementGlyph, ELEMENT_ICON, starPath, type Ctx } from "./skillGlyphs";

const TAU = Math.PI * 2;

export type PartCategory = "effect" | "condition" | "cost" | "trigger" | "link" | "target" | "change";

/** 一個部件：顏色、畫法與說明文字。 */
export interface Part {
  cat: PartCategory;
  /** 部件的穩定鍵（快取、測試用）。 */
  key: string;
  color: string;
  draw(ctx: Ctx): void;
  label: string;
  /** 部件在圖示上的位置或意義（組裝列的浮動說明）。 */
  note: string;
}

// ---- 小工具 ----

function arrow(ctx: Ctx, x0: number, y0: number, x1: number, y1: number, head = 4): void {
  const a = Math.atan2(y1 - y0, x1 - x0);
  ctx.beginPath();
  ctx.moveTo(x0, y0);
  ctx.lineTo(x1, y1);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(x1 + Math.cos(a), y1 + Math.sin(a));
  ctx.lineTo(x1 - Math.cos(a - 0.6) * head, y1 - Math.sin(a - 0.6) * head);
  ctx.lineTo(x1 - Math.cos(a + 0.6) * head, y1 - Math.sin(a + 0.6) * head);
  ctx.closePath();
  ctx.fill();
}
function dot(ctx: Ctx, x: number, y: number, r: number): void {
  ctx.beginPath();
  ctx.arc(x, y, r, 0, TAU);
  ctx.fill();
}
function ring(ctx: Ctx, x: number, y: number, r: number): void {
  ctx.beginPath();
  ctx.arc(x, y, r, 0, TAU);
  ctx.stroke();
}
/** 符文：菱形外框，裡面一個小菱形（`filled` 時填滿）。 */
function runeMark(ctx: Ctx, x: number, y: number, k = 1, filled = false): void {
  const r = 8 * k;
  ctx.beginPath();
  ctx.moveTo(x, y - r);
  ctx.lineTo(x + r, y);
  ctx.lineTo(x, y + r);
  ctx.lineTo(x - r, y);
  ctx.closePath();
  ctx.stroke();
  const s = 3.6 * k;
  ctx.beginPath();
  ctx.moveTo(x, y - s);
  ctx.lineTo(x + s, y);
  ctx.lineTo(x, y + s);
  ctx.lineTo(x - s, y);
  ctx.closePath();
  if (filled) ctx.fill();
  else ctx.stroke();
}
function person(ctx: Ctx, x: number, y: number, k = 1): void {
  dot(ctx, x, y - 5 * k, 2.6 * k);
  ctx.beginPath();
  ctx.moveTo(x - 4.5 * k, y + 5 * k);
  ctx.quadraticCurveTo(x - 4.5 * k, y - 1.5 * k, x, y - 1.5 * k);
  ctx.quadraticCurveTo(x + 4.5 * k, y - 1.5 * k, x + 4.5 * k, y + 5 * k);
  ctx.closePath();
  ctx.fill();
}
function shieldPath(ctx: Ctx, k = 1): void {
  ctx.beginPath();
  ctx.moveTo(0, -9 * k);
  ctx.lineTo(7.5 * k, -6 * k);
  ctx.lineTo(7 * k, 2 * k);
  ctx.lineTo(0, 9 * k);
  ctx.lineTo(-7 * k, 2 * k);
  ctx.lineTo(-7.5 * k, -6 * k);
  ctx.closePath();
}
function heart(ctx: Ctx, k = 1): void {
  ctx.beginPath();
  ctx.moveTo(0, 8 * k);
  ctx.bezierCurveTo(-11 * k, 0, -6 * k, -10 * k, 0, -4 * k);
  ctx.bezierCurveTo(6 * k, -10 * k, 11 * k, 0, 0, 8 * k);
  ctx.closePath();
}
function drop(ctx: Ctx, x: number, y: number, k = 1): void {
  ctx.beginPath();
  ctx.moveTo(x, y - 8 * k);
  ctx.bezierCurveTo(x + 6.5 * k, y, x + 5.5 * k, y + 6 * k, x, y + 6 * k);
  ctx.bezierCurveTo(x - 5.5 * k, y + 6 * k, x - 6.5 * k, y, x, y - 8 * k);
  ctx.fill();
}
function hourglass(ctx: Ctx): void {
  ctx.beginPath();
  ctx.moveTo(-6, -8);
  ctx.lineTo(6, -8);
  ctx.lineTo(0, 0);
  ctx.lineTo(6, 8);
  ctx.lineTo(-6, 8);
  ctx.lineTo(0, 0);
  ctx.closePath();
  ctx.fill();
}
function text(ctx: Ctx, s: string, size = 11): void {
  ctx.font = `800 ${size}px "Noto Sans TC","Microsoft JhengHei",sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(s, 0, 0.5);
}
function eye(ctx: Ctx, slashed: boolean): void {
  ctx.beginPath();
  ctx.moveTo(-9, 0);
  ctx.quadraticCurveTo(0, -9, 9, 0);
  ctx.quadraticCurveTo(0, 9, -9, 0);
  ctx.stroke();
  dot(ctx, 0, 0, 2.6);
  if (slashed) {
    ctx.beginPath();
    ctx.moveTo(-8, 7);
    ctx.lineTo(8, -7);
    ctx.stroke();
  }
}
function footprints(ctx: Ctx): void {
  for (const [x, y, r] of [
    [-4, 4, -0.3],
    [3, -3, 0.3],
  ] as const) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(r);
    ctx.beginPath();
    ctx.ellipse(0, 0, 2.6, 4, 0, 0, TAU);
    ctx.fill();
    dot(ctx, 0, -5.5, 1.3);
    ctx.restore();
  }
}
function chevrons(ctx: Ctx, dir: "right" | "up"): void {
  for (const o of [-4, 2]) {
    ctx.beginPath();
    if (dir === "right") {
      ctx.moveTo(o - 2, -6);
      ctx.lineTo(o + 4, 0);
      ctx.lineTo(o - 2, 6);
    } else {
      ctx.moveTo(-6, -o + 2);
      ctx.lineTo(0, -o - 4);
      ctx.lineTo(6, -o + 2);
    }
    ctx.stroke();
  }
}
function dice(ctx: Ctx): void {
  ctx.beginPath();
  ctx.roundRect(-7.5, -7.5, 15, 15, 3);
  ctx.stroke();
  for (const [x, y] of [
    [-3.5, -3.5],
    [3.5, 3.5],
    [0, 0],
    [3.5, -3.5],
    [-3.5, 3.5],
  ] as const)
    dot(ctx, x, y, 1.4);
}
function card(ctx: Ctx, x: number, y: number): void {
  ctx.beginPath();
  ctx.roundRect(x - 4.5, y - 6.5, 9, 13, 1.5);
  ctx.fill();
}
function star(ctx: Ctx, n: number, ro: number, ri: number): void {
  starPath(ctx, 0, 0, n, ro, ri);
  ctx.fill();
}
function plus(ctx: Ctx, x: number, y: number): void {
  ctx.fillRect(x - 1, y - 3.5, 2, 7);
  ctx.fillRect(x - 3.5, y - 1, 7, 2);
}
function ghost(ctx: Ctx, alpha: number, draw: () => void): void {
  const before = ctx.globalAlpha;
  ctx.globalAlpha = before * alpha;
  draw();
  ctx.globalAlpha = before;
}

type Draw = (ctx: Ctx) => void;

// ---- 狀態（顏色：負面偏紅紫、正面偏綠金藍）----

const bleedGlyph: Draw = (c) => {
  drop(c, -3, -1, 0.75);
  drop(c, 4, 3, 0.6);
};

const STATUS: Readonly<Record<string, readonly [string, Draw]>> = {
  burning: ["#ff8a2a", (c) => elementGlyph(c, "fire", 0, 0, 0.95, c.fillStyle as string)],
  frozen: ["#9fe6ff", (c) => elementGlyph(c, "ice", 0, 0, 0.95, c.fillStyle as string)],
  poison: ["#8fdc4a", (c) => elementGlyph(c, "poison", 0, 0, 0.95, c.fillStyle as string)],
  bleed: ["#ff5a5a", bleedGlyph],
  root: [
    "#b8d07a",
    (c) => {
      c.beginPath();
      c.moveTo(0, -8);
      c.lineTo(0, 4);
      c.moveTo(0, 4);
      c.lineTo(-6, 8);
      c.moveTo(0, 4);
      c.lineTo(6, 8);
      c.moveTo(0, 0);
      c.lineTo(-5, 3);
      c.stroke();
    },
  ],
  slow: [
    "#a8b4ff",
    (c) => {
      ring(c, 0, 0, 8);
      c.beginPath();
      c.moveTo(0, -5);
      c.lineTo(0, 0);
      c.lineTo(3.5, 3);
      c.stroke();
    },
  ],
  stun: [
    "#ffe14d",
    (c) => {
      for (const [x, y] of [
        [-5, -3],
        [5, -3],
        [0, 5],
      ] as const) {
        c.save();
        c.translate(x, y);
        star(c, 5, 4, 1.7);
        c.restore();
      }
    },
  ],
  prone: [
    "#e0c49a",
    (c) => {
      dot(c, -7, 2, 2.6);
      c.fillRect(-4, 0, 12, 4.5);
    },
  ],
  blinded: ["#c8c8d8", (c) => eye(c, true)],
  vulnerable: [
    "#ff6a6a",
    (c) => {
      shieldPath(c);
      c.stroke();
      c.beginPath();
      c.moveTo(-2, -8);
      c.lineTo(2, -2);
      c.lineTo(-2, 2);
      c.lineTo(1, 8);
      c.stroke();
    },
  ],
  armor_broken: [
    "#d8a060",
    (c) => {
      shieldPath(c);
      c.stroke();
      arrow(c, 0, -5, 0, 6, 3.2);
    },
  ],
  weaken: [
    "#e09a9a",
    (c) => {
      c.beginPath();
      c.moveTo(-6, -7);
      c.lineTo(4, 3);
      c.stroke();
      arrow(c, 6, -6, 6, 6, 3.5);
    },
  ],
  feared: ["#c890ff", (c) => text(c, "!", 15)],
  taunted: [
    "#ff7a4a",
    (c) => {
      ring(c, 0, 0, 7.5);
      ring(c, 0, 0, 3.5);
      dot(c, 0, 0, 1.4);
    },
  ],
  silenced: [
    "#d0a0ff",
    (c) => {
      c.beginPath();
      c.roundRect(-8, -7, 16, 11, 4);
      c.moveTo(-3, 4);
      c.lineTo(-5, 8);
      c.lineTo(1, 4);
      c.stroke();
      c.beginPath();
      c.moveTo(-4, -4);
      c.lineTo(4, 2);
      c.moveTo(4, -4);
      c.lineTo(-4, 2);
      c.stroke();
    },
  ],
  marked: [
    "#ff5a5a",
    (c) => {
      ring(c, 0, 0, 7);
      c.beginPath();
      c.moveTo(-10, 0);
      c.lineTo(-4, 0);
      c.moveTo(4, 0);
      c.lineTo(10, 0);
      c.moveTo(0, -10);
      c.lineTo(0, -4);
      c.moveTo(0, 4);
      c.lineTo(0, 10);
      c.stroke();
    },
  ],
  concealed: [
    "#a0a8b8",
    (c) => {
      ghost(c, 0.55, () => person(c, 0, 0, 1.4));
      c.beginPath();
      c.arc(0, 0, 9, -2.4, -0.7);
      c.stroke();
    },
  ],
  revealed: ["#ffd04a", (c) => eye(c, false)],
  hasted: ["#7dffb0", (c) => chevrons(c, "right")],
  empowered: ["#ffb03a", (c) => chevrons(c, "up")],
  rallied: ["#ff6a4a", (c) => chevrons(c, "up")],
  guarded: [
    "#7fc0ff",
    (c) => {
      shieldPath(c);
      c.fill();
    },
  ],
  shielded: [
    "#8fd0ff",
    (c) => {
      shieldPath(c);
      c.fill();
    },
  ],
  defending: [
    "#7fc0ff",
    (c) => {
      shieldPath(c);
      c.stroke();
    },
  ],
  regenerating: [
    "#7cf29a",
    (c) => {
      ring(c, 0, 0, 8.5);
      c.fillRect(-1.5, -5, 3, 10);
      c.fillRect(-5, -1.5, 10, 3);
    },
  ],
  overwatch: ["#ffd04a", (c) => eye(c, false)],
  undying: [
    "#ff7a7a",
    (c) => {
      heart(c);
      c.fill();
    },
  ],
  soul_link: [
    "#d8b8ff",
    (c) => {
      ring(c, -4, 0, 5);
      ring(c, 4, 0, 5);
    },
  ],
  time_bomb: ["#ffb03a", hourglass],
  charging: [
    "#ffd04a",
    (c) => {
      ring(c, 0, 0, 8);
      dot(c, 0, 0, 3.5);
    },
  ],
};

const STANCE_COLOR = "#ffd04a";
const UNKNOWN_COLOR = "#d8d8e0";

/** 狀態圖示（`stance_*` 為六角，不認得的狀態畫名稱第一個字）。 */
export function statusGlyph(ctx: Ctx, id: string | null | undefined): void {
  const known = id == null ? undefined : STATUS[id];
  if (known !== undefined) {
    known[1](ctx);
    return;
  }
  if (id?.startsWith("stance_") === true) {
    ctx.beginPath();
    for (let i = 0; i < 6; i++) ctx.lineTo(Math.cos((i / 6) * TAU) * 8, Math.sin((i / 6) * TAU) * 8);
    ctx.closePath();
    ctx.stroke();
    return;
  }
  const name = id == null || id === "" ? "?" : statusName(id);
  text(ctx, [...name][0] ?? "?", 12);
}

export function statusColor(id: string | null | undefined): string {
  if (id == null) return UNKNOWN_COLOR;
  return STATUS[id]?.[0] ?? (id.startsWith("stance_") ? STANCE_COLOR : UNKNOWN_COLOR);
}

// ---- 表面：落在地上的一滴，顏色是表面色 ----

const SURFACE_COLOR: Readonly<Record<string, string>> = {
  fire: "#ff7a1a",
  ice: "#cdeeff",
  oil: "#5a4a30",
  water: "#4a9af0",
  holy: "#ffe58a",
  darkness: "#8a5ad0",
  smoke: "#c0c0c8",
  poison: "#86d84a",
};
export const surfaceColor = (id: string | null | undefined): string => (id == null ? "#c8c8c8" : (SURFACE_COLOR[id] ?? "#c8c8c8"));

export function surfaceGlyph(ctx: Ctx, id: string | null | undefined): void {
  ctx.save();
  ctx.fillStyle = surfaceColor(id);
  drop(ctx, 0, -2, 0.9);
  ctx.globalAlpha = 0.85;
  ctx.beginPath();
  ctx.ellipse(0, 7, 9, 2.6, 0, 0, TAU);
  ctx.fill();
  ctx.restore();
}

// ---- 效果原語 ----

const stackDots: Draw = (c) => {
  for (let i = 0; i < 3; i++) dot(c, -6 + i * 6, 3, 2.4);
};

const EFFECT: Record<string, readonly [string, Draw]> = {
  damage: ["#ffffff", (c) => star(c, 8, 9.5, 4)],
  heal: [
    "#7cf29a",
    (c) => {
      c.fillRect(-2.5, -8, 5, 16);
      c.fillRect(-8, -2.5, 16, 5);
    },
  ],
  shield: [
    "#8fd0ff",
    (c) => {
      shieldPath(c);
      c.fill();
    },
  ],
  cleanse: ["#bfffe8", (c) => star(c, 4, 9, 2.4)],
  push: [
    "#ffffff",
    (c) => {
      dot(c, -6, 0, 3.4);
      arrow(c, -1, 0, 9, 0, 4.5);
    },
  ],
  pull: [
    "#ffffff",
    (c) => {
      dot(c, -7, 0, 3.4);
      arrow(c, 9, 0, -1, 0, 4.5);
    },
  ],
  knock_prone: ["#e0c49a", (c) => (STATUS["prone"] as readonly [string, Draw])[1](c)],
  teleport: [
    "#d8b8ff",
    (c) => {
      c.setLineDash([2.5, 2]);
      ring(c, -3, 2, 6);
      c.setLineDash([]);
      dot(c, 5, -4, 3.2);
    },
  ],
  dash: [
    "#ffffff",
    (c) => {
      c.beginPath();
      c.moveTo(-9, -4);
      c.lineTo(-1, -4);
      c.moveTo(-9, 4);
      c.lineTo(-1, 4);
      c.stroke();
      arrow(c, -3, 0, 9, 0, 4.5);
    },
  ],
  charge_through: [
    "#ffffff",
    (c) => {
      c.fillRect(-1.5, -9, 3, 18);
      arrow(c, -9, 0, 9, 0, 4.5);
    },
  ],
  shadowstep: [
    "#c8a0ff",
    (c) => {
      c.beginPath();
      c.arc(-2, 0, 7, 0.6, TAU - 0.6);
      c.stroke();
      arrow(c, 0, 0, 9, 0, 4);
    },
  ],
  leap: [
    "#ffffff",
    (c) => {
      c.beginPath();
      c.moveTo(-9, 6);
      c.quadraticCurveTo(0, -14, 7, 4);
      c.stroke();
      arrow(c, 5, 0, 8, 6, 4);
    },
  ],
  swap: [
    "#ffffff",
    (c) => {
      arrow(c, -8, -3, 8, -3, 3.5);
      arrow(c, 8, 3, -8, 3, 3.5);
    },
  ],
  apply_status: ["#ffffff", (c) => ring(c, 0, 0, 7)],
  create_surface: ["#ffffff", (c) => surfaceGlyph(c, null)],
  destroy_object: [
    "#e0c49a",
    (c) => {
      c.strokeRect(-7, -7, 14, 14);
      c.beginPath();
      c.moveTo(-2, -7);
      c.lineTo(1, -1);
      c.lineTo(-2, 3);
      c.lineTo(1, 7);
      c.stroke();
    },
  ],
  create_obstacle: [
    "#d8c0a0",
    (c) => {
      for (let r = 0; r < 3; r++) for (let i = 0; i < 2; i++) c.fillRect(-8 + i * 8 + (r % 2) * 4 - (r % 2 === 1 && i === 1 ? 4 : 0), -7 + r * 5, 7, 4);
    },
  ],
  raise_terrain: [
    "#e0c49a",
    (c) => {
      c.fillRect(-8, 2, 16, 6);
      arrow(c, 0, 1, 0, -9, 4);
    },
  ],
  lower_terrain: [
    "#e0c49a",
    (c) => {
      c.fillRect(-8, 2, 16, 6);
      arrow(c, 0, -9, 0, 0, 4);
    },
  ],
  intercept: [
    "#8fd0ff",
    (c) => {
      person(c, -3, 1, 1.1);
      c.save();
      c.translate(5, 0);
      shieldPath(c, 0.6);
      c.fill();
      c.restore();
    },
  ],
  add_stack: [
    "#ffd04a",
    (c) => {
      stackDots(c);
      c.fillRect(-1, -9, 2, 7);
      c.fillRect(-3.5, -6.5, 7, 2);
    },
  ],
  consume_stack: [
    "#ffd04a",
    (c) => {
      stackDots(c);
      c.fillRect(-3.5, -6.5, 7, 2);
    },
  ],
  consume_status: [
    "#ffb03a",
    (c) => {
      star(c, 6, 9, 4.5);
      c.save();
      c.fillStyle = "#1a1420";
      dot(c, 0, 0, 2.6);
      c.restore();
    },
  ],
  place_trap: [
    "#e0e0e0",
    (c) => {
      for (const [b, t] of [
        [-2, -8],
        [2, 8],
      ] as const) {
        c.beginPath();
        c.moveTo(-8, b);
        for (let i = 0; i < 4; i++) {
          c.lineTo(-8 + i * 4 + 2, t * 0.6 + b * 0.4);
          c.lineTo(-8 + (i + 1) * 4, b);
        }
        c.closePath();
        c.fill();
      }
    },
  ],
  grant_ap: [
    "#ffe14d",
    (c) => {
      ring(c, -2, 0, 6.5);
      text(c, "+", 12);
    },
  ],
  reset_cooldown: [
    "#a8e0ff",
    (c) => {
      c.beginPath();
      c.arc(0, 0, 7.5, -1.2, 4.2);
      c.stroke();
      arrow(c, -6.5, -4, -3.5, -8, 3.5);
    },
  ],
  cheat_death: [
    "#ff7a7a",
    (c) => {
      heart(c);
      c.fill();
    },
  ],
  redirect_damage: [
    "#ffffff",
    (c) => {
      c.beginPath();
      c.moveTo(-8, 7);
      c.lineTo(0, -1);
      c.stroke();
      arrow(c, 0, -1, 8, 7, 4);
    },
  ],
  copy_skill: [
    "#d8c8ff",
    (c) => {
      ghost(c, 0.6, () => card(c, -3, -2));
      card(c, 3, 2);
    },
  ],
  extra_reaction: [
    "#8fd0ff",
    (c) => {
      shieldPath(c, 0.9);
      c.stroke();
      elementGlyph(c, "lightning", 0, 0, 0.55, c.fillStyle as string);
    },
  ],
  hurl_object: [
    "#e0b080",
    (c) => {
      c.fillRect(-9, 1, 7, 7);
      c.beginPath();
      c.moveTo(-5, 0);
      c.quadraticCurveTo(0, -12, 7, 2);
      c.stroke();
      arrow(c, 5, -2, 8, 4, 3.5);
    },
  ],
  topple: [
    "#c8c0b0",
    (c) => {
      c.save();
      c.rotate(0.6);
      c.fillRect(-2.5, -9, 5, 16);
      c.restore();
      c.fillRect(-9, 7, 18, 2);
    },
  ],
  restore_resource: [
    "#c89cff",
    (c) => {
      c.beginPath();
      c.moveTo(-2, -8);
      c.lineTo(4, -2);
      c.lineTo(-2, 4);
      c.lineTo(-8, -2);
      c.closePath();
      c.fill();
      c.fillRect(4, 2, 2, 7);
      c.fillRect(1.5, 4.5, 7, 2);
    },
  ],
  steal_buff: [
    "#c8a0ff",
    (c) => {
      c.beginPath();
      c.moveTo(-8, 6);
      c.lineTo(-8, -2);
      c.quadraticCurveTo(-8, -8, -2, -8);
      c.lineTo(6, -8);
      c.stroke();
      chevrons(c, "up");
    },
  ],
  dispel: [
    "#d8d0ff",
    (c) => {
      c.beginPath();
      c.moveTo(-7, -7);
      c.lineTo(7, 7);
      c.moveTo(7, -7);
      c.lineTo(-7, 7);
      c.stroke();
    },
  ],
  reveal: ["#ffffff", (c) => eye(c, false)],
  revive: [
    "#ffd75e",
    (c) => {
      heart(c);
      c.fill();
      c.save();
      c.fillStyle = "#1a1420";
      c.fillRect(-1.2, -4, 2.4, 8);
      c.fillRect(-4, -1.2, 8, 2.4);
      c.restore();
    },
  ],
  delayed_damage: [
    "#ffb03a",
    (c) => {
      c.save();
      c.scale(0.75, 0.75);
      c.translate(-4, 0);
      hourglass(c);
      c.restore();
      c.save();
      c.translate(5, -3);
      star(c, 6, 5, 2.4);
      c.restore();
    },
  ],
  summon: [
    "#8ff0e2",
    (c) => {
      person(c, -2, 1, 1.25);
      plus(c, 6, -5);
    },
  ],
  zone: [
    "#ffd04a",
    (c) => {
      c.setLineDash([3, 2]);
      ring(c, 0, 0, 8);
      c.setLineDash([]);
      dot(c, 0, 0, 2.5);
    },
  ],
  rule_change: [
    "#ffd75e",
    (c) => {
      c.beginPath();
      c.roundRect(-7, -8, 14, 16, 2);
      c.stroke();
      c.fillRect(-4, -4, 8, 1.6);
      c.fillRect(-4, 0, 8, 1.6);
      c.fillRect(-4, 4, 5, 1.6);
    },
  ],
  gamble: ["#ffffff", dice],
  grant_skill: [
    "#d8c8ff",
    (c) => {
      card(c, -2, 1);
      plus(c, 6, -5);
    },
  ],
  // 3-24c 獻祭召喚物：召喚物的人影向外迸出四道光
  sacrifice_summon: [
    "#ff9f6b",
    (c) => {
      person(c, 0, 1, 0.9);
      arrow(c, 0, -6, 0, -10.5, 3);
      arrow(c, -6, 0, -10.5, 0, 3);
      arrow(c, 6, 0, 10.5, 0, 3);
    },
  ],
  // 3-23 刻印：留下符文（菱形紋）、引爆符文（菱形向外迸出四道光）
  inscribe: ["#ffe08a", (c) => runeMark(c, 0, 0, 1.1, true)],
  detonate_runes: [
    "#ffb36b",
    (c) => {
      runeMark(c, 0, 0, 0.6, true);
      arrow(c, 0, -5, 0, -10, 3);
      arrow(c, 0, 5, 0, 10, 3);
      arrow(c, -5, 0, -10, 0, 3);
      arrow(c, 5, 0, 10, 0, 3);
    },
  ],
};
// 傳送他人、任意兩者互換：和互換位置同一個圖示
EFFECT["teleport_target"] = EFFECT["swap"] as readonly [string, Draw];
EFFECT["swap_any"] = EFFECT["swap"] as readonly [string, Draw];

/** 效果原語的中文名（`content/skill_primitives.yaml`；不認得的顯示代碼）。 */
export const EFFECT_NAMES: Readonly<Record<string, string>> = {
  damage: "傷害",
  heal: "治療",
  shield: "護盾",
  cleanse: "淨化",
  push: "推擊",
  pull: "拉扯",
  knock_prone: "擊倒",
  teleport: "傳送",
  dash: "衝鋒",
  charge_through: "直線衝撞",
  shadowstep: "瞬步",
  leap: "跳躍",
  swap: "交換位置",
  teleport_target: "傳送他人",
  swap_any: "任意兩者互換",
  apply_status: "施加狀態",
  create_surface: "產生表面",
  destroy_object: "摧毀物件",
  create_obstacle: "產生障礙",
  raise_terrain: "隆起地形",
  lower_terrain: "下陷地形",
  intercept: "替隊友擋攻擊",
  add_stack: "累積層數",
  consume_stack: "消耗層數",
  consume_status: "消耗狀態",
  place_trap: "放置陷阱",
  grant_ap: "給予行動點",
  reset_cooldown: "重置冷卻",
  cheat_death: "免死",
  redirect_damage: "分擔傷害",
  copy_skill: "複製技能",
  extra_reaction: "額外反應",
  hurl_object: "投擲物件",
  topple: "推倒",
  restore_resource: "回復資源",
  steal_buff: "奪取增益",
  dispel: "驅散",
  reveal: "揭露",
  revive: "復活",
  delayed_damage: "定時炸彈",
  summon: "召喚",
  zone: "持續區域",
  rule_change: "規則改變",
  gamble: "賭注",
  grant_skill: "暫時獲得技能",
  inscribe: "刻印",
  detonate_runes: "引爆符文",
  sacrifice_summon: "獻祭召喚物",
};

/** 效果的描述資料（技能圖示 `icon.segments[].effects[]` 的一項）。 */
export interface EffectLike {
  type: string;
  status?: string | null;
  surface?: string | null;
}

/** 效果原語 → 部件（附加狀態與產生表面用各自的圖示）。 */
export function effectPart(e: EffectLike): Part {
  if (e.type === "apply_status" && e.status != null && e.status !== "") {
    const id = e.status;
    return { cat: "effect", key: `status:${id}`, color: statusColor(id), draw: (c) => statusGlyph(c, id), label: statusName(id), note: "附加狀態" };
  }
  if (e.type === "create_surface" && e.surface != null && e.surface !== "") {
    const id = e.surface;
    return {
      cat: "effect",
      key: `surface:${id}`,
      color: surfaceColor(id),
      draw: (c) => surfaceGlyph(c, id),
      label: `${surfaceName(id)}表面`,
      note: "產生表面",
    };
  }
  const g = EFFECT[e.type];
  return {
    cat: "effect",
    key: e.type,
    color: g?.[0] ?? UNKNOWN_COLOR,
    draw: g?.[1] ?? ((c) => text(c, "?", 13)),
    label: EFFECT_NAMES[e.type] ?? e.type,
    note: "效果原語",
  };
}

// ---- 條件 ----

function halfHeart(c: Ctx, k: number): void {
  heart(c, k);
  c.stroke();
  c.save();
  c.beginPath();
  c.rect(-10, 1, 20, 10);
  c.clip();
  heart(c, k);
  c.fill();
  c.restore();
}

const COND: Readonly<Record<string, Draw>> = {
  height_advantage: (c) => {
    c.beginPath();
    c.moveTo(-9, 8);
    c.lineTo(0, -4);
    c.lineTo(9, 8);
    c.closePath();
    c.fill();
    dot(c, 0, -7.5, 2.6);
  },
  target_hp_below: (c) => halfHeart(c, 1),
  self_hp_below: (c) => {
    halfHeart(c, 0.85);
    person(c, 7, -5, 0.5);
  },
  target_has_status: (c) => {
    ring(c, -2, 1, 6);
    text(c, "?", 9);
  },
  target_on_surface: (c) => {
    drop(c, -2, 0, 0.75);
    c.save();
    c.translate(6, -5);
    text(c, "?", 9);
    c.restore();
  },
  from_behind: (c) => {
    person(c, 3, 0, 1.1);
    arrow(c, -9, 0, -3, 0, 3.5);
  },
  flanked: (c) => {
    dot(c, 0, 0, 3);
    arrow(c, -9, 0, -4.5, 0, 3.5);
    arrow(c, 9, 0, 4.5, 0, 3.5);
  },
  target_isolated: (c) => {
    c.setLineDash([2.5, 2]);
    ring(c, 0, 0, 8);
    c.setLineDash([]);
    dot(c, 0, 0, 3);
  },
  moved_this_turn: footprints,
  first_round: (c) => text(c, "1", 14),
  cast_tag_this_turn: (c) => {
    card(c, -3, 0);
    arrow(c, 1, 0, 9, 0, 3.5);
  },
  self_concealed: (c) => (STATUS["concealed"] as readonly [string, Draw])[1](c),
  on_own_rune: (c) => {
    runeMark(c, -2, 1, 0.95, true);
    c.save();
    c.translate(6.5, -5.5);
    text(c, "?", 8);
    c.restore();
  },
  adjacent_ally: (c) => {
    person(c, -4, 1, 0.85);
    person(c, 4, 1, 0.85);
  },
  target_collided: (c) => {
    person(c, -3, 1, 0.9);
    c.fillRect(4, -8, 3, 16);
    arrow(c, -9, -7, -4, -7, 3);
  },
};

export const CONDITION_NAMES: Readonly<Record<string, string>> = {
  target_hp_below: "目標血量低於",
  self_hp_below: "自身血量低於",
  height_advantage: "居高臨下",
  target_on_surface: "目標站在表面上",
  target_has_status: "目標帶有狀態",
  moved_this_turn: "本回合移動過",
  adjacent_ally: "身旁有友方",
  target_isolated: "目標落單",
  first_round: "第一輪",
  cast_tag_this_turn: "本回合施放過同類技能",
  flanked: "夾擊",
  from_behind: "背刺",
  self_concealed: "潛行偷襲",
  on_own_rune: "目標站在自己的符文上",
  target_collided: "目標本回合受過撞擊",
};

const CONDITION_COLOR = "#ffe9a8";

/** 條件 → 部件；`target_has_status` 帶狀態時畫該狀態圖示加問號。 */
export function conditionPart(id: string | null | undefined, status?: string | null): Part | null {
  if (id == null || id === "") return null;
  let draw: Draw = COND[id] ?? ((c) => text(c, "?", 13));
  if (id === "target_has_status" && status != null && status !== "") {
    draw = (c) => {
      c.save();
      c.scale(0.85, 0.85);
      statusGlyph(c, status);
      c.restore();
      c.save();
      c.translate(6.5, 5.5);
      text(c, "?", 8);
      c.restore();
    };
  }
  return { cat: "condition", key: id === "target_has_status" && status != null && status !== "" ? `${id}:${status}` : id, color: CONDITION_COLOR, draw, label: CONDITION_NAMES[id] ?? id, note: "條件" };
}

// ---- 代價 ----

export type CostId = "source" | "gamble" | "self" | "stacks" | "once" | "delay";
const COST_LABEL: Readonly<Record<CostId, string>> = {
  source: "源力",
  gamble: "賭注",
  self: "自身代價（失手自傷等）",
  stacks: "消耗層數",
  once: "每場一次",
  delay: "延遲",
};
const COST_ART: Readonly<Record<CostId, readonly [string, Draw]>> = {
  source: [
    "#c89cff",
    (x) => {
      x.beginPath();
      x.moveTo(0, -9);
      x.lineTo(7, 0);
      x.lineTo(0, 9);
      x.lineTo(-7, 0);
      x.closePath();
      x.fill();
    },
  ],
  gamble: ["#ffffff", dice],
  self: [
    "#ff6a6a",
    (x) => {
      heart(x);
      x.fill();
      x.save();
      x.strokeStyle = "#1a1420";
      x.lineWidth = 1.6;
      x.beginPath();
      x.moveTo(-1, -4);
      x.lineTo(2, 0);
      x.lineTo(-1, 3);
      x.stroke();
      x.restore();
    },
  ],
  stacks: ["#ffd04a", (EFFECT["consume_stack"] as readonly [string, Draw])[1]],
  once: [
    "#ffd75e",
    (x) => {
      ring(x, 0, 0, 8.5);
      text(x, "1", 11);
    },
  ],
  delay: ["#a8e0ff", hourglass],
};

/** 帶數值時的名稱（Phase 3-18a）：源力 2、消耗層數 3、每場一次、延遲 1 回合。 */
function costLabel(id: string, value: number | undefined): string {
  const base = COST_LABEL[id as CostId] ?? id;
  if (value === undefined) return base;
  if (id === "delay") return `${base} ${value} 回合`;
  if (id === "once") return value === 1 ? base : `每場 ${value} 次`;
  return `${base} ${value}`;
}

/** 特殊代價 → 部件（`value` 是代價的數值，沒有就不寫）；不認得的代價畫「?」。 */
export function costPart(id: string, value?: number): Part {
  const art = COST_ART[id as CostId];
  return {
    cat: "cost",
    key: id,
    color: art?.[0] ?? "#d8d8e0",
    draw: art?.[1] ?? ((x) => text(x, "?", 13)),
    label: costLabel(id, value),
    note: "特殊代價",
  };
}

// ---- 觸發（被動）與反應時機（反應技）的主圖 ----

const TRIG: Readonly<Record<string, Draw>> = {
  on_hit: (EFFECT["damage"] as readonly [string, Draw])[1],
  on_kill: (c) => {
    dot(c, 0, -2, 7);
    c.fillRect(-4, 2, 8, 6);
    c.save();
    c.fillStyle = "#1a1420";
    dot(c, -2.8, -2, 2);
    dot(c, 2.8, -2, 2);
    c.restore();
  },
  on_crit: (c) => star(c, 4, 10, 2.6),
  on_natural_20: (c) => {
    c.beginPath();
    for (let i = 0; i < 6; i++) c.lineTo(Math.cos((i / 6) * TAU - Math.PI / 2) * 9.5, Math.sin((i / 6) * TAU - Math.PI / 2) * 9.5);
    c.closePath();
    c.stroke();
    text(c, "20", 8);
  },
  on_move: footprints,
  on_damaged: (STATUS["vulnerable"] as readonly [string, Draw])[1],
  on_status_applied: (c) => {
    ring(c, 0, 0, 8);
    dot(c, 0, 0, 3);
  },
  on_cast_tag: (c) => card(c, 0, 0),
  on_collision: (c) => {
    arrow(c, -9, 0, -2, 0, 3.5);
    arrow(c, 9, 0, 2, 0, 3.5);
  },
  on_turn_start: (c) => {
    c.beginPath();
    c.arc(0, 4, 7, Math.PI, 0);
    c.fill();
    c.fillRect(-10, 4, 20, 1.8);
    arrow(c, 0, -2, 0, -9, 3);
  },
  on_turn_end: (c) => {
    c.beginPath();
    c.arc(0, 4, 7, Math.PI, 0);
    c.fill();
    c.fillRect(-10, 4, 20, 1.8);
    arrow(c, 0, -10, 0, -3, 3);
  },
  on_enter_surface: (c) => drop(c, 0, 0, 0.9),
  on_summon_downed: (c) => {
    ring(c, 0, -2, 6);
    dot(c, 0, -2, 2.4);
    arrow(c, 0, 5, 0, 10, 3);
  },
  every_n_hits: (c) => {
    for (let i = 0; i < 3; i++) dot(c, -6 + i * 6, 0, 2.6);
  },
  enemy_enters_adjacent: (c) => {
    ring(c, 2, 0, 6);
    arrow(c, -10, 0, -3, 0, 3.5);
  },
  enemy_leaves_adjacent: (c) => {
    ring(c, -2, 0, 6);
    arrow(c, 2, 0, 10, 0, 3.5);
  },
  hit_by_spell: (c) => {
    shieldPath(c);
    c.stroke();
    c.save();
    c.scale(0.5, 0.5);
    star(c, 5, 9, 4);
    c.restore();
  },
  hit_by_attack: (c) => {
    shieldPath(c);
    c.stroke();
    c.beginPath();
    c.moveTo(-9, -9);
    c.lineTo(-2, -2);
    c.stroke();
  },
  hit_by_melee: (c) => {
    shieldPath(c);
    c.stroke();
    c.beginPath();
    c.moveTo(-9, -9);
    c.lineTo(-2, -2);
    c.moveTo(-9, -4);
    c.lineTo(-5, -8);
    c.stroke();
  },
  ally_targeted: (c) => {
    person(c, 0, 1, 1.1);
    ghost(c, 0.9, () => (STATUS["marked"] as readonly [string, Draw])[1](c));
  },
  ally_downed: (STATUS["prone"] as readonly [string, Draw])[1],
  ally_hit_adjacent: (c) => {
    person(c, -4, 1, 0.9);
    c.save();
    c.translate(5, -3);
    star(c, 6, 5, 2.2);
    c.restore();
  },
};

/** 觸發時機（被動，`content/skill_triggers.yaml`）與反應時機（反應技）的中文名。 */
export const TRIGGER_NAMES: Readonly<Record<string, string>> = {
  on_hit: "命中時",
  on_crit: "暴擊時",
  on_natural_20: "擲出自然 20 時",
  on_kill: "擊倒時",
  on_damaged: "受傷時",
  on_turn_start: "回合開始時",
  on_turn_end: "回合結束時",
  on_move: "移動後",
  every_n_hits: "每命中 n 次",
  on_cast_tag: "施放帶標籤的技能後",
  on_status_applied: "施加狀態後",
  on_collision: "造成撞擊後",
  on_enter_surface: "敵人進入你的表面時",
  on_summon_downed: "召喚物倒下時",
  enemy_enters_adjacent: "敵人靠近時",
  enemy_leaves_adjacent: "敵人離開時",
  hit_by_spell: "被法術擊中時",
  hit_by_attack: "被攻擊時",
  hit_by_melee: "被近戰擊中時",
  ally_targeted: "隊友被瞄準時",
  ally_downed: "隊友倒下時",
  ally_hit_adjacent: "身旁隊友受擊時",
};

export function triggerPart(id: string | null | undefined, isReaction: boolean): Part | null {
  if (id == null || id === "") return null;
  return {
    cat: "trigger",
    key: id,
    color: "#ffffff",
    draw: TRIG[id] ?? ((c) => text(c, "?", 13)),
    label: TRIGGER_NAMES[id] ?? id,
    note: isReaction ? "反應時機" : "觸發時機",
  };
}

// ---- 複合技能的接續記號 ----

const LINK: Readonly<Record<string, readonly [string, Draw]>> = {
  after_action: ["接著做", (c) => arrow(c, -7, 0, 7, 0, 5)],
  on_hit: [
    "命中才觸發",
    (c) => {
      c.beginPath();
      c.moveTo(-7, 0);
      c.lineTo(-2, 5);
      c.lineTo(7, -6);
      c.stroke();
    },
  ],
  on_kill: ["擊殺才觸發", (TRIG["on_kill"] as Draw)],
  delayed: ["延遲觸發", hourglass],
  after_move: [
    "移動後觸發",
    (c) => {
      c.save();
      c.scale(0.85, 0.85);
      footprints(c);
      c.restore();
    },
  ],
  after_gather: [
    "聚集後觸發",
    (c) => {
      arrow(c, -9, 0, -3, 0, 3);
      arrow(c, 9, 0, 3, 0, 3);
    },
  ],
};

/** 接續記號；不認得的種類當成「接著做」。 */
export function linkPart(when: string | null | undefined): Part {
  const id = when ?? "after_action";
  const l = LINK[id] ?? (LINK["after_action"] as readonly [string, Draw]);
  return { cat: "link", key: id, color: "#ffffff", draw: l[1], label: l[0], note: "接續" };
}

// ---- 修正：被改造的對象、改變的內容 ----

const TAG_TARGET: Readonly<Record<string, string>> = { push: "push", heal: "heal", control: "apply_status", ranged: "dash", shout: "damage", area: "damage" };
const TAG_NAMES: Readonly<Record<string, string>> = { push: "推擊", heal: "治療", control: "控制", ranged: "遠程", shout: "吼叫", area: "範圍" };

const rangedGlyph: Draw = (c) => {
  c.beginPath();
  c.arc(-4, 0, 9, -1.1, 1.1);
  c.stroke();
  arrow(c, -6, 0, 9, 0, 3.5);
};

/** `applies_to`（只含有填的欄位）→ 被改造對象的部件。 */
export function modifierTargetPart(applies: Readonly<Record<string, unknown>> | null | undefined): Part {
  const a = applies ?? {};
  let draw: Draw = (EFFECT["damage"] as readonly [string, Draw])[1];
  let label = "所有技能";
  const actions = Array.isArray(a["actions"]) ? (a["actions"] as unknown[]) : [];
  const tags = Array.isArray(a["skill_tags"]) ? (a["skill_tags"] as unknown[]).map(String) : [];
  const swordGlyph: Draw = (c) => {
    c.beginPath();
    c.moveTo(-7, 7);
    c.lineTo(7, -7);
    c.moveTo(-7, 2);
    c.lineTo(-2, 7);
    c.stroke();
  };
  if (a["all_skills"] === true) {
    draw = (c) => {
      ghost(c, 0.6, () => card(c, -3, -2));
      card(c, 3, 2);
    };
  } else if (a["all_attacks"] === true || actions.includes("attack")) {
    draw = swordGlyph;
    label = a["all_attacks"] === true ? "所有攻擊" : "普通攻擊";
  } else if (tags.length > 0) {
    const t = tags[0] as string;
    draw = t === "ranged" ? rangedGlyph : (EFFECT[TAG_TARGET[t] ?? "damage"] ?? (EFFECT["damage"] as readonly [string, Draw]))[1];
    label = `${tags.map((x) => TAG_NAMES[x] ?? x).join("／")}技能`;
  } else if (actions.length > 0) {
    draw = swordGlyph;
    label = actions.map(String).join("／");
  }
  return { cat: "target", key: "target", color: "#ffffff", draw, label, note: "被改造的對象" };
}

const ELEMENT_FALLBACK = "#ffffff";

/** `on_hit_effects` 的一項（原始效果或後端給的 `type[:status]`）→ `type[:status]`。 */
function effectId(raw: unknown): string {
  if (typeof raw === "string") return raw;
  const e = (typeof raw === "object" && raw !== null ? raw : {}) as Record<string, unknown>;
  const type = typeof e["type"] === "string" ? e["type"] : "?";
  return typeof e["status"] === "string" && e["status"] !== "" ? `${type}:${e["status"]}` : type;
}

function effectLikeOf(id: string): EffectLike {
  const [type = "?", status] = id.split(":");
  return status === undefined ? { type } : { type, status };
}

/** 修正的改變內容（一個鍵一個部件）。 */
export function modifierChangePart(key: string, value: unknown, partIds: readonly string[] = []): Part {
  let draw: Draw;
  let label: string;
  let color = "#ffe14d";
  const num = typeof value === "number" ? value : 0;
  const signed = num > 0 ? `+${num}` : `${num}`;
  switch (key) {
    case "add_element": {
      const el = String(value);
      color = ELEMENT_ICON[el]?.accent ?? ELEMENT_FALLBACK;
      draw = (c) => {
        elementGlyph(c, el, -1, 1, 0.75, color);
        c.save();
        c.fillStyle = "#ffffff";
        plus(c, 6, -6);
        c.restore();
      };
      label = `加上${ELEMENT_ICON[el]?.name ?? el}元素`;
      break;
    }
    case "damage_permille":
      draw = (c) => {
        c.save();
        c.translate(-2, 2);
        c.scale(0.7, 0.7);
        star(c, 8, 9.5, 4);
        c.restore();
        arrow(c, 6, 6, 6, -8, 3.5);
      };
      label = `傷害 ${num > 0 ? "+" : ""}${num / 10}%`;
      break;
    case "hit_bonus":
      draw = (c) => {
        ring(c, 0, 0, 7);
        dot(c, 0, 0, 2.2);
        plus(c, 7, -7);
      };
      label = `命中 ${signed}`;
      break;
    case "cooldown_delta":
      draw = (c) => {
        ring(c, -2, 1, 7);
        c.beginPath();
        c.moveTo(-2, -3);
        c.lineTo(-2, 1);
        c.lineTo(1, 3);
        c.stroke();
        c.fillRect(4, -9, 6, 2);
      };
      label = `冷卻 ${signed}`;
      break;
    case "area_delta":
      draw = (c) => {
        arrow(c, -2, -2, -9, -9, 3.5);
        arrow(c, 2, 2, 9, 9, 3.5);
        c.strokeRect(-4, -4, 8, 8);
      };
      label = `範圍 ${signed}`;
      break;
    case "push_distance_delta":
      draw = (EFFECT["push"] as readonly [string, Draw])[1];
      label = `推距 ${signed}`;
      break;
    case "ap_delta":
      draw = (c) => {
        ring(c, -2, 0, 6.5);
        c.fillRect(4, -9, 6, 2);
      };
      label = `AP ${signed}`;
      break;
    case "range_delta":
      draw = rangedGlyph;
      label = `射程 ${signed}`;
      break;
    case "add_tags": {
      const tags = partIds.length > 0 ? partIds : Array.isArray(value) ? value.map(String) : [];
      const first = tags[0] ?? "";
      const base = first === "ranged" ? rangedGlyph : (EFFECT[TAG_TARGET[first] ?? ""] ?? (EFFECT["damage"] as readonly [string, Draw]))[1];
      draw = (c) => {
        c.save();
        c.scale(0.85, 0.85);
        base(c);
        c.restore();
        plus(c, 6.5, -6.5);
      };
      label = tags.length === 0 ? "加上標籤" : `加上標籤：${tags.map((t) => TAG_NAMES[t] ?? t).join("／")}`;
      break;
    }
    case "on_hit_effects": {
      const ids = partIds.length > 0 ? partIds : Array.isArray(value) ? value.map((v) => effectId(v)) : [];
      const first = ids[0];
      const part = first === undefined ? null : effectPart(effectLikeOf(first));
      draw = (c) => {
        if (part !== null) {
          c.save();
          c.scale(0.85, 0.85);
          part.draw(c);
          c.restore();
        }
        c.save();
        c.translate(6.5, -6.5);
        text(c, "命", 7);
        c.restore();
      };
      label = ids.length === 0 ? "命中後效果" : `命中後：${ids.map((i) => effectPart(effectLikeOf(i)).label).join("／")}`;
      break;
    }
    case "shape_to":
      draw = (c) => {
        c.beginPath();
        c.moveTo(-9, 6);
        c.lineTo(9, -6);
        c.stroke();
      };
      label = `形狀改為 ${String(value)}`;
      break;
    case "allow_self_target":
      draw = (c) => {
        person(c, 0, 1, 1.2);
        ring(c, 0, 0, 9.5);
      };
      label = "可以對自己用";
      break;
    case "grant_pierce":
      draw = (c) => {
        c.fillRect(-1.5, -9, 3, 18);
        arrow(c, -9, 0, 9, 0, 4);
      };
      label = "穿透";
      break;
    case "heal_permille":
    case "summon_hp_permille":
    case "summon_attack_dice": {
      // 治療量與召喚物數值（Phase 3-24b1）：治療或召喚的圖示加一個小標記
      const base = (EFFECT[key === "heal_permille" ? "heal" : "summon"] as readonly [string, Draw])[1];
      draw = (c) => {
        c.save();
        c.scale(0.85, 0.85);
        base(c);
        c.restore();
        if (key === "summon_attack_dice") {
          c.save();
          c.translate(6.5, -6.5);
          text(c, "骰", 7);
          c.restore();
        } else {
          plus(c, 6.5, -6.5);
        }
      };
      if (key === "heal_permille") label = `治療量 ${num > 0 ? "+" : ""}${num / 10}%`;
      else if (key === "summon_hp_permille") label = `召喚物 HP +${num / 10}%`;
      else label = `召喚物攻擊 +${num} 骰`;
      break;
    }
    default:
      draw = (c) => text(c, "?", 13);
      label = key;
  }
  return { cat: "change", key, color, draw, label, note: "改變的內容" };
}

// ---- 部件小圓片 ----

export interface ChipOptions {
  /** 外圈顏色；`false` 不畫外圈。 */
  ring?: string | false;
  bg?: string;
}

/** 在 (x, y) 畫一個部件小圓片：深色底＋外圈＋圖示。 */
export function drawChip(ctx: Ctx, part: Part, x: number, y: number, r: number, opts: ChipOptions = {}): void {
  ctx.save();
  ctx.translate(x, y);
  ctx.fillStyle = opts.bg ?? "rgba(10,12,18,0.85)";
  ctx.beginPath();
  ctx.arc(0, 0, r, 0, TAU);
  ctx.fill();
  if (opts.ring !== false) {
    ctx.strokeStyle = opts.ring ?? "rgba(255,255,255,0.35)";
    ctx.lineWidth = Math.max(1, r * 0.12);
    ctx.stroke();
  }
  const k = (r * 0.78) / 10;
  ctx.scale(k, k);
  ctx.fillStyle = part.color;
  ctx.strokeStyle = part.color;
  ctx.lineWidth = 2.2;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  part.draw(ctx);
  ctx.restore();
}

/** 有專屬圖示的部件代碼（其他走預設圖；測試用來對照 `content/` 檢查有沒有漏）。 */
export const KNOWN_PARTS = {
  effects: Object.keys(EFFECT),
  statuses: Object.keys(STATUS),
  surfaces: Object.keys(SURFACE_COLOR),
  conditions: Object.keys(COND),
  triggers: Object.keys(TRIG),
  links: Object.keys(LINK),
  costs: Object.keys(COST_ART),
} as const;
