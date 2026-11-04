// 事件卡與情境判定的墨線小圖示（Phase 6C-ART3；樣張 docs/art/sample/story-icons.html、attr-icons.html，
// 需求 docs/art/Phase6剩餘美術移植需求.md 第 4 節）。
// 每個圖示畫在 48×48 的框裡（inkStyle 的 ink、stroke）；外圈是深底加圖示色的圓環。
// 依大小畫成離屏圖、轉成圖片網址快取（和 portrait.ts 同做法）；沒有 DOM 時回傳 null。
import { TAU, type Ctx } from "./artDraw";
import { ellPts, ink, stroke, type Pt } from "./inkStyle";
import type { AttrKey, SolutionIcon } from "../world/narration";

/** 墨線色（樣張的 K）。 */
const K = "#2b1e16";
/** 圓環裡的深底。 */
export const CHIP_BG = "#2a241e";
/** d20 平常的顏色、大成功（金）、大失敗（灰）。 */
export const D20_COLOR = { normal: "#f2e6c8", crit: "#ffe08a", fumble: "#c8c0b8" } as const;
/** 64px 以上才寫點數（需求：64 寫點數，28 以下不寫字）。 */
export const D20_TEXT_MIN = 29;

type Draw = (c: Ctx) => void;

const glowOn = (c: Ctx, col: string, b: number): void => {
  c.shadowColor = col;
  c.shadowBlur = b;
};

const disc = (c: Ctx, x: number, y: number, r: number, col: string): void => {
  c.fillStyle = col;
  c.beginPath();
  c.arc(x, y, r, 0, TAU);
  c.fill();
};

const shine = (c: Ctx, x: number, y: number, rx: number, ry: number, rot: number, col: string): void => {
  c.fillStyle = col;
  c.beginPath();
  c.ellipse(x, y, rx, ry, rot, 0, TAU);
  c.fill();
};

// ---------------- 選項 8 種 ----------------

export const SOLUTION_ART: Readonly<Record<SolutionIcon, { ring: string; draw: Draw }>> = {
  combat: {
    ring: "#d0503a",
    draw(c) {
      for (const [s, k] of [
        [1, "a"],
        [-1, "b"],
      ] as const) {
        c.save();
        c.translate(24, 24);
        c.scale(s, 1);
        c.rotate(-0.78);
        ink(c, "bl" + k, [[-3, -20], [0, -23], [3, -20], [3, 8], [-3, 8]], "#dfe6ee", { w: 0.8, sharp: true });
        ink(c, "gd" + k, [[-9, 8], [9, 8], [9, 12], [-9, 12]], "#c8903a", { w: 0.7, shade: false });
        ink(c, "hd" + k, [[-2, 12], [2, 12], [2, 20], [-2, 20]], "#6a4028", { w: 0.6, shade: false });
        c.restore();
      }
    },
  },
  persuade: {
    ring: "#e8bb48",
    draw(c) {
      ink(c, "bub", [[6, 10], [42, 10], [42, 32], [22, 32], [12, 40], [14, 32], [6, 32]], "#f2e6c8", { w: 0.9 });
      ink(c, "hrt", [[24, 29], [16, 21], [16, 16], [20, 13], [24, 16], [28, 13], [32, 16], [32, 21]], "#e05a6a", { w: 0.6, shade: false });
    },
  },
  sneak: {
    ring: "#8a7ab8",
    draw(c) {
      ink(c, "hood", [[24, 4], [38, 14], [42, 40], [6, 40], [10, 14]], "#4a3e62", { w: 0.9 });
      ink(c, "face", [[24, 16], [33, 22], [33, 34], [15, 34], [15, 22]], "#1c1712", { w: 0.5, shade: false });
      c.save();
      glowOn(c, "#c8b8ff", 6);
      disc(c, 20, 26, 1.8, "#e8e0ff");
      disc(c, 28, 26, 1.8, "#e8e0ff");
      c.restore();
    },
  },
  investigate: {
    ring: "#4ab0d0",
    draw(c) {
      ink(c, "hdl", [[29, 31], [33, 27], [44, 38], [40, 42]], "#6a4028", { w: 0.8, shade: false });
      ink(c, "ring", ellPts(20, 20, 13, 13, 18), "#c8903a", { w: 0.9, shade: false });
      ink(c, "lens", ellPts(20, 20, 9.5, 9.5, 16), "#bfe4f2", { w: 0.5, shade: false });
      shine(c, 16, 16, 3, 4.5, -0.6, "rgba(255,255,255,0.7)");
    },
  },
  force: {
    ring: "#e07a4a",
    draw(c) {
      const imp: readonly (readonly [Pt, Pt])[] = [
        [[6, 8], [12, 14]],
        [[24, 3], [24, 10]],
        [[42, 8], [36, 14]],
      ];
      for (const [a, b] of imp) stroke(c, "imp" + a[0], [a, b], 1.4, "#ffcf6a");
      ink(c, "fist", [[10, 20], [38, 20], [40, 30], [36, 42], [14, 42], [10, 34]], "#e8b890", { w: 0.9 });
      for (const x of [17, 24, 31]) stroke(c, "kn" + x, [[x, 20], [x, 28]], 0.8, "#8a5a3a");
      ink(c, "thumb", [[12, 30], [26, 30], [26, 34], [12, 35]], "#f0c8a0", { w: 0.6, shade: false });
    },
  },
  chance: {
    ring: "#6aa84a",
    draw(c) {
      stroke(c, "stem", [[24, 26], [28, 36], [34, 42]], 1.2, "#3a6a2a");
      const dirs: readonly Pt[] = [[0, -1], [1, 0], [0, 1], [-1, 0]];
      dirs.forEach(([dx, dy], i) => ink(c, "lf" + i, ellPts(24 + dx * 8, 22 + dy * 8, 7, 7, 14), "#7ac85a", { w: 0.7 }));
      c.save();
      glowOn(c, "#fff4a0", 8);
      ink(c, "sp", [[40, 4], [42, 9], [47, 11], [42, 13], [40, 18], [38, 13], [33, 11], [38, 9]], "#fff4c0", { w: 0.4, shade: false });
      c.restore();
    },
  },
  leave: {
    ring: "#9a8e7c",
    draw(c) {
      ink(c, "door", [[8, 6], [26, 6], [26, 42], [8, 42]], "#5a3e28", { w: 0.9 });
      ink(c, "open", [[8, 6], [18, 10], [18, 44], [8, 42]], "#8a5a3a", { w: 0.7 });
      disc(c, 16, 26, 1.6, "#e8bb48");
      ink(c, "arr", [[24, 21], [34, 21], [34, 15], [44, 24], [34, 33], [34, 27], [24, 27]], "#f2e6c8", { w: 0.8, shade: false });
    },
  },
  trade: {
    ring: "#e8bb48",
    draw(c) {
      ink(c, "bag", [[16, 12], [32, 12], [28, 18], [40, 30], [38, 42], [10, 42], [8, 30], [20, 18]], "#b08a5a", { w: 0.9 });
      stroke(c, "tie", [[18, 17], [30, 17]], 1.2, "#6a4028");
      for (const [x, y] of [
        [30, 38],
        [37, 34],
      ] as const) {
        ink(c, "cn" + x, ellPts(x, y, 6, 6, 14), "#ffd23a", { w: 0.7, shade: false });
        stroke(c, "cm" + x, [[x, y - 3], [x, y + 3]], 0.8, "#a8781a");
      }
    },
  },
};

// ---------------- 其他 4 種（＋事件線，樣張沒有，照同一套畫法補） ----------------

export type MiscIcon = "clue" | "model_off" | "narrator" | "info" | "thread";

export const MISC_ART: Readonly<Record<MiscIcon, { ring: string; draw: Draw }>> = {
  clue: {
    ring: "#e8bb48",
    draw(c) {
      ink(c, "note", [[8, 8], [36, 6], [40, 40], [12, 42]], "#f2e6c8", { w: 0.9 });
      for (const y of [16, 22, 28]) stroke(c, "ln" + y, [[14, y], [32, y - 1]], 0.7, "#9a8a70");
      c.save();
      glowOn(c, "#ffd23a", 8);
      ink(c, "spot", ellPts(30, 34, 5, 5, 12), "#ffd23a", { w: 0.5, shade: false });
      c.restore();
    },
  },
  model_off: {
    ring: "#9a8e7c",
    draw(c) {
      ink(c, "base", [[12, 36], [36, 36], [40, 44], [8, 44]], "#6a4028", { w: 0.8, shade: false });
      ink(c, "ball", ellPts(24, 22, 14, 14, 18), "#7a8098", { w: 0.9 });
      stroke(c, "crk", [[18, 12], [23, 19], [20, 24], [26, 31]], 1, K);
      shine(c, 18, 16, 3, 5, -0.6, "rgba(255,255,255,0.35)");
    },
  },
  narrator: {
    ring: "#a898ff",
    draw(c) {
      ink(c, "book", [[6, 26], [24, 30], [42, 26], [42, 42], [24, 46], [6, 42]], "#f2e6c8", { w: 0.8 });
      stroke(c, "sp", [[24, 30], [24, 46]], 0.8, K);
      c.save();
      c.translate(26, 20);
      c.rotate(0.6);
      ink(c, "qf", [[0, -18], [6, -10], [4, 6], [0, 12], [-4, 6], [-6, -10]], "#c8bcff", { w: 0.7 });
      stroke(c, "qs", [[0, -14], [0, 16]], 0.8, K);
      c.restore();
    },
  },
  info: {
    ring: "#4ab0d0",
    draw(c) {
      ink(c, "disc", ellPts(24, 24, 17, 17, 18), "#bfe4f2", { w: 0.9 });
      disc(c, 24, 15, 2.8, K);
      ink(c, "stem", [[21, 21], [27, 21], [27, 35], [21, 35]], K, { w: 0.5, shade: false });
    },
  },
  thread: {
    ring: "#e8bb48",
    draw(c) {
      stroke(c, "th", [[8, 34], [16, 18], [24, 30], [32, 16], [40, 12]], 2.2, "#e8bb48");
      disc(c, 8, 34, 2.4, "#f2e6c8");
      disc(c, 40, 12, 2.4, "#f2e6c8");
    },
  },
};

// ---------------- 六屬性（attr-icons.html） ----------------

export const ATTR_ART: Readonly<Record<AttrKey, { ring: string; draw: Draw }>> = {
  str: {
    ring: "#e07a4a",
    draw(c) {
      ink(c, "arm", [[10, 34], [14, 22], [20, 14], [28, 12], [32, 18], [28, 22], [24, 22], [22, 30], [30, 30], [38, 34], [36, 40], [12, 40]], "#e8b890", { w: 0.9 });
      stroke(c, "arm-m", [[20, 22], [26, 26]], 0.8, "#8a5a3a");
    },
  },
  dex: {
    ring: "#6ac0a0",
    draw(c) {
      c.save();
      c.translate(24, 24);
      c.rotate(-0.7);
      ink(c, "fe", [[0, -18], [7, -8], [6, 8], [0, 16], [-6, 8], [-7, -8]], "#c8f0e0", { w: 0.8 });
      stroke(c, "fe-q", [[0, -16], [0, 20]], 0.8, K);
      c.restore();
      stroke(c, "wind", [[8, 34], [16, 32]], 1, "#6ac0a0");
      stroke(c, "wind2", [[10, 40], [20, 38]], 1, "#6ac0a0");
    },
  },
  con: {
    ring: "#d04a5a",
    draw(c) {
      ink(c, "heart", [[24, 40], [10, 26], [10, 16], [17, 11], [24, 16], [31, 11], [38, 16], [38, 26]], "#e04a5a", { w: 0.9 });
      shine(c, 16, 18, 3, 4, -0.4, "rgba(255,255,255,0.4)");
    },
  },
  int: {
    ring: "#7a8aff",
    draw(c) {
      ink(c, "book", [[9, 14], [24, 18], [39, 14], [39, 38], [24, 42], [9, 38]], "#f2e6c8", { w: 0.9 });
      stroke(c, "spine", [[24, 18], [24, 42]], 0.9, K);
      c.save();
      glowOn(c, "#a898ff", 6);
      ink(c, "star", [[24, 4], [26, 10], [32, 10], [27, 13], [29, 19], [24, 15], [19, 19], [21, 13], [16, 10], [22, 10]], "#c8bcff", { shade: false, w: 0.5 });
      c.restore();
    },
  },
  wis: {
    ring: "#4ab0d0",
    draw(c) {
      ink(c, "eye", [[6, 24], [16, 15], [24, 13], [32, 15], [42, 24], [32, 33], [24, 35], [16, 33]], "#f2f0e8", { w: 0.9 });
      ink(c, "iris", ellPts(24, 24, 7, 7, 14), "#4ab0d0", { shade: false, w: 0.7 });
      disc(c, 24, 24, 3, "#1c1712");
      disc(c, 22, 22, 1.4, "#fff");
    },
  },
  wil: {
    ring: "#e8bb48",
    draw(c) {
      c.save();
      glowOn(c, "#ffd23a", 8);
      ink(c, "flame", [[24, 6], [32, 18], [34, 30], [28, 40], [20, 40], [14, 30], [16, 18], [20, 22]], "#ffb030", { shade: false, w: 0.9 });
      ink(c, "flame-in", [[24, 20], [28, 30], [24, 37], [20, 30]], "#fff4c0", { shade: false, w: 0.5 });
      c.restore();
    },
  },
};

// ---------------- d20 ----------------

/** d20：六角外形加中央三角面；`n` 給了才寫點數（呼叫端依大小決定）。 */
export function drawD20(c: Ctx, n: number | string | undefined, col: string = D20_COLOR.normal): void {
  const P = (a: number, r: number): Pt => [24 + Math.cos(a) * r, 24 + Math.sin(a) * r];
  const hex = [0, 1, 2, 3, 4, 5].map((i) => P(-Math.PI / 2 + (i * TAU) / 6, 21));
  ink(c, "hex", hex, col, { w: 0.9, sharp: true });
  const tri = [P(-Math.PI / 2, 12), P(Math.PI / 6, 12), P((5 * Math.PI) / 6, 12)];
  ink(c, "tri", tri, "#fff8e8", { w: 0.6, sharp: true, shade: false });
  const to = [0, 0, 1, 1, 2, 2] as const;
  for (let i = 0; i < 6; i++) stroke(c, "e" + i, [hex[i]!, tri[to[i]!]!], 0.6, K);
  if (n !== undefined) {
    c.font = `bold ${D20_FONT_PX}px Georgia, serif`;
    c.textAlign = "center";
    // 6Q-1：點數先描一圈淺色（約字高 0.2 倍寬，三角面的邊線不再穿過字），再寫深色字；綠骰、紅骰同一個畫法
    c.lineJoin = "round";
    c.lineWidth = D20_HALO_W * 2; // 描邊一半在字外，所以字外那一圈 ＝ D20_HALO_W
    c.strokeStyle = D20_HALO;
    c.strokeText(String(n), 24, 29);
    c.fillStyle = K;
    c.fillText(String(n), 24, 29);
    c.textAlign = "left";
  }
}

/** d20 點數的字高（px，48 格的畫布座標）。 */
export const D20_FONT_PX = 14;
/** 點數外圈的顏色（6Q-1，和三角面同色）。 */
export const D20_HALO = "#fff8e8";
/**
 * 點數外圈露在字外的寬度（6Q-1；6N-4 改細，美術 PM 6Q-1 驗收第 1 點：描邊線寬從 5.6 改成 3.5，露在字外 1.75）。
 * 描邊一半在字外，所以 `lineWidth ＝ D20_HALO_W × 2 ＝ 3.5`。
 */
export const D20_HALO_W = 1.75;

/** d20 該不該寫字：只有大圖（29px 以上）才寫。 */
export const d20ShowsValue = (size: number): boolean => size >= D20_TEXT_MIN;

/** 擲骰用的那顆的顏色：自然 20 金、自然 1 灰，其他照結果色。 */
export function usedDieColor(face: number, outcomeColor: string): string {
  if (face === 20) return D20_COLOR.crit;
  if (face === 1) return D20_COLOR.fumble;
  return outcomeColor;
}

// ---------------- 圓環與離屏快取 ----------------

/** 畫一個圓環小圖示（左上角在原點、大小 s）：深底＋圖示色圓環，圖示縮到圓裡。 */
export function drawChip(c: Ctx, s: number, ring: string | null, fn: Draw): void {
  c.save();
  if (ring !== null) {
    c.beginPath();
    c.arc(s / 2, s / 2, s / 2, 0, TAU);
    c.fillStyle = CHIP_BG;
    c.fill();
    c.lineWidth = Math.max(1.2, s * 0.06);
    c.strokeStyle = ring;
    c.stroke();
    c.beginPath();
    c.arc(s / 2, s / 2, s / 2 - 1, 0, TAU);
    c.clip();
  }
  c.scale(s / 48, s / 48);
  fn(c);
  c.restore();
}

export type StoryIconSpec =
  | { kind: "solution"; icon: SolutionIcon }
  | { kind: "misc"; icon: MiscIcon }
  | { kind: "attr"; attr: AttrKey }
  | { kind: "d20"; value?: number | string; color?: string };

/** 畫一個圖示到 ctx（左上角在原點、大小 size）。 */
export function drawStoryIcon(c: Ctx, spec: StoryIconSpec, size: number): void {
  switch (spec.kind) {
    case "solution":
      drawChip(c, size, SOLUTION_ART[spec.icon].ring, SOLUTION_ART[spec.icon].draw);
      return;
    case "misc":
      drawChip(c, size, MISC_ART[spec.icon].ring, MISC_ART[spec.icon].draw);
      return;
    case "attr":
      drawChip(c, size, ATTR_ART[spec.attr].ring, ATTR_ART[spec.attr].draw);
      return;
    case "d20": {
      const v = d20ShowsValue(size) ? spec.value : undefined;
      drawChip(c, size, null, (cc) => drawD20(cc, v, spec.color ?? D20_COLOR.normal));
      return;
    }
  }
}

/** 快取鍵（種類、圖示、大小、d20 的點數與顏色；小 d20 不寫字，點數不進鍵）。 */
export function storyIconKey(spec: StoryIconSpec, size: number): string {
  switch (spec.kind) {
    case "solution":
    case "misc":
      return `${spec.kind}|${spec.icon}|${size}`;
    case "attr":
      return `attr|${spec.attr}|${size}`;
    case "d20":
      return `d20|${d20ShowsValue(size) ? String(spec.value ?? "") : ""}|${spec.color ?? D20_COLOR.normal}|${size}`;
  }
}

const cache = new Map<string, string>();

/** 圖示的圖片網址（離屏畫好快取；沒有 DOM 時為 `null`）。 */
export function storyIconUrl(spec: StoryIconSpec, size: number, dpr = 2): string | null {
  if (typeof document === "undefined") return null;
  const key = `${storyIconKey(spec, size)}|${dpr}`;
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  const c = document.createElement("canvas");
  c.width = Math.ceil(size * dpr);
  c.height = Math.ceil(size * dpr);
  const ctx = c.getContext("2d");
  if (ctx === null) return null;
  ctx.scale(dpr, dpr);
  drawStoryIcon(ctx, spec, size);
  const url = c.toDataURL("image/png");
  cache.set(key, url);
  return url;
}

/** 快取裡的張數（測試用）。 */
export const storyIconCacheSize = (): number => cache.size;
