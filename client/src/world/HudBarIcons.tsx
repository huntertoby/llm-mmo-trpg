// HUD 功能列的 8 個定稿圖示（Phase 6A-4f；docs/art/HUD功能列圖示.md、docs/art/sample/hudIcons.js）：
// I 背包、K 技能、G 成長、J 任務、Y 影子、N 留言、R 潛行（#120 21.4 取代趕路）、M 地圖。
// 照樣張的 C 手繪墨線移植成 48×48 的 SVG：同一套「抖動＋二次曲線圓滑」的外形（`ink`／`stroke`，種子由名字決定，
// 每次畫都一樣）、深色墨線雙描、暗面斜線（只畫在填色區塊裡）。全部程式繪製，不載圖檔。
import { useId, type ReactElement, type ReactNode } from "react";

export type HudBarKey = "I" | "K" | "G" | "J" | "Y" | "N" | "R" | "M";

type Pt = readonly [number, number];

const INK = "#2b1e16";
/** 潛行圖示的淺色圓底（6F-7）。 */
export const SNEAK_MOON = "#d4dbef";
const TAU = Math.PI * 2;

function seedOf(s: string): number {
  let h = 2166136261;
  for (const ch of s) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
  return h >>> 0;
}

function rng(seed: number): () => number {
  let s = seed >>> 0;
  return () => (s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296;
}

function wobble(pts: readonly Pt[], r: () => number, amt: number): Pt[] {
  return pts.map(([x, y]) => [x + (r() - 0.5) * amt, y + (r() - 0.5) * amt] as const);
}

const f = (n: number): string => (Math.round(n * 100) / 100).toString();
const mid = (a: Pt, b: Pt): Pt => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];

/** 樣張 `smooth()` 的 SVG 版：頂點當控制點、邊的中點當端點的二次曲線。 */
export function smoothPath(pts: readonly Pt[], closed = true): string {
  const n = pts.length;
  if (n === 0) return "";
  if (!closed) {
    const first = pts[0] as Pt;
    let d = `M${f(first[0])} ${f(first[1])}`;
    for (let i = 1; i < n - 1; i++) {
      const p = pts[i] as Pt;
      const m = mid(p, pts[i + 1] as Pt);
      d += `Q${f(p[0])} ${f(p[1])} ${f(m[0])} ${f(m[1])}`;
    }
    const last = pts[n - 1] as Pt;
    return `${d}L${f(last[0])} ${f(last[1])}`;
  }
  const m0 = mid(pts[n - 1] as Pt, pts[0] as Pt);
  let d = `M${f(m0[0])} ${f(m0[1])}`;
  for (let i = 0; i < n; i++) {
    const p = pts[i] as Pt;
    const m = mid(p, pts[(i + 1) % n] as Pt);
    d += `Q${f(p[0])} ${f(p[1])} ${f(m[0])} ${f(m[1])}`;
  }
  return `${d}Z`;
}

function ellPts(cx: number, cy: number, rx: number, ry: number, n = 18): Pt[] {
  return Array.from({ length: n }, (_, i) => [cx + Math.cos((i / n) * TAU) * rx, cy + Math.sin((i / n) * TAU) * ry] as const);
}

interface InkOpt {
  w?: number;
  shade?: boolean;
}

/** 填色區塊：淡淡的錯位底色＋暗面斜線＋雙描墨線（樣張的 `ink`）。 */
function Ink({ k, pts, color, opt = {}, clip }: { k: string; pts: readonly Pt[]; color: string; opt?: InkOpt; clip: string }) {
  const r = rng(seedOf(k));
  const fill = smoothPath(wobble(pts, r, 0.7));
  let hatch: ReactNode = null;
  if (opt.shade !== false) {
    const xs = pts.map((p) => p[0]);
    const ys = pts.map((p) => p[1]);
    const x0 = Math.min(...xs);
    const x1 = Math.max(...xs);
    const y0 = Math.min(...ys);
    const y1 = Math.max(...ys);
    const w = x1 - x0;
    const h = y1 - y0;
    if (w > 3 && h > 3) {
      let d = "";
      for (let x = x0 + w * 0.6; x < x1 + h; x += 1.3) d += `M${f(x)} ${f(y0)}L${f(x - h * 0.9)} ${f(y1)}`;
      const id = `${clip}-${k}`;
      hatch = (
        <>
          <clipPath id={id}>
            <path d={smoothPath(pts)} />
          </clipPath>
          <path d={d} clipPath={`url(#${id})`} stroke="rgba(43,30,22,0.42)" strokeWidth={0.35} fill="none" />
        </>
      );
    }
  }
  const lw = opt.w ?? 0.85;
  const line1 = smoothPath(wobble(pts, r, 0.5));
  const line2 = smoothPath(wobble(pts, r, 0.85));
  return (
    <g data-part={k}>
      <path d={fill} transform="translate(0.45 0.35)" fill={color} fillOpacity={0.94} stroke="rgba(0,0,0,0.55)" strokeOpacity={0.35} strokeWidth={0.9} />
      {hatch}
      <g fill="none" stroke={INK} strokeLinejoin="round" strokeLinecap="round">
        <path d={line1} strokeWidth={lw} />
        <path d={line2} strokeWidth={lw * 0.45} />
      </g>
    </g>
  );
}

/** 線條（樣張的 `stroke`）；`dash` 為虛線。 */
function Line({ k, pts, w = 0.7, color = INK, dash }: { k: string; pts: readonly Pt[]; w?: number; color?: string; dash?: string }) {
  const d = smoothPath(wobble(pts, rng(seedOf(k)), 0.35), false);
  return <path data-part={k} d={d} fill="none" stroke={color} strokeWidth={w} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={dash} />;
}

const Dot = ({ x, y, r, color }: { x: number; y: number; r: number; color: string }) => <circle cx={x} cy={y} r={r} fill={color} />;

type Draw = (clip: string) => ReactElement;

const ICONS: Record<HudBarKey, { zh: string; draw: Draw }> = {
  I: {
    zh: "背包",
    draw: (c) => (
      <>
        <Ink clip={c} k="bag" pts={[[11, 20], [37, 20], [40, 40], [8, 40]]} color="#a06a36" opt={{ w: 1 }} />
        <Ink clip={c} k="bag-flap" pts={[[12, 20], [36, 20], [34, 29], [14, 29]]} color="#8a5a30" opt={{ w: 0.8 }} />
        <Line k="bag-handle" pts={[[17, 20], [18, 11], [30, 11], [31, 20]]} w={1.8} color="#5a3a1e" />
        <Ink clip={c} k="bag-clasp" pts={[[21, 26], [27, 26], [27, 32], [21, 32]]} color="#e8bb48" opt={{ shade: false, w: 0.6 }} />
      </>
    ),
  },
  K: {
    zh: "技能",
    draw: (c) => (
      <>
        <Ink clip={c} k="book" pts={[[9, 10], [39, 10], [39, 40], [9, 40]]} color="#5a3a9a" opt={{ w: 1 }} />
        <Ink clip={c} k="book-pages" pts={[[12, 10], [16, 10], [16, 40], [12, 40]]} color="#f2e6c8" opt={{ shade: false, w: 0.6 }} />
        <g style={{ filter: "drop-shadow(0 0 3px #a898ff)" }}>
          <Ink clip={c} k="book-gem" pts={[[27, 18], [33, 25], [27, 32], [21, 25]]} color="#c8bcff" opt={{ shade: false, w: 0.7 }} />
        </g>
      </>
    ),
  },
  G: {
    zh: "成長",
    draw: (c) => (
      <>
        <Line k="grow-stem" pts={[[24, 42], [24, 14]]} w={2.6} color="#4f8a3a" />
        <Ink clip={c} k="grow-l" pts={[[24, 30], [12, 24], [10, 16], [20, 20]]} color="#6aa84a" opt={{ w: 0.8 }} />
        <Ink clip={c} k="grow-r" pts={[[24, 24], [36, 18], [38, 10], [28, 14]]} color="#6aa84a" opt={{ w: 0.8 }} />
        <Ink clip={c} k="grow-arrow" pts={[[24, 4], [31, 13], [27, 13], [27, 18], [21, 18], [21, 13], [17, 13]]} color="#ffd23a" opt={{ shade: false, w: 0.7 }} />
      </>
    ),
  },
  J: {
    zh: "任務",
    draw: (c) => (
      <>
        <Ink clip={c} k="scroll" pts={[[12, 12], [36, 12], [36, 38], [12, 38]]} color="#f2e6c8" opt={{ w: 0.9 }} />
        <Ink clip={c} k="scroll-t" pts={[[9, 8], [39, 8], [39, 13], [9, 13]]} color="#8a2f20" opt={{ shade: false, w: 0.7 }} />
        <Ink clip={c} k="scroll-b" pts={[[9, 37], [39, 37], [39, 42], [9, 42]]} color="#8a2f20" opt={{ shade: false, w: 0.7 }} />
        {[19, 25, 31].map((y) => (
          <Line key={y} k={`scroll-l${y}`} pts={[[16, y], [30, y]]} w={0.8} color="#8a7a5a" />
        ))}
        <Ink clip={c} k="scroll-bang" pts={[[30, 16], [34, 16], [33, 26], [31, 26]]} color="#c83a2a" opt={{ shade: false, w: 0.5 }} />
      </>
    ),
  },
  Y: {
    zh: "影子",
    draw: (c) => (
      <>
        <Ink clip={c} k="sh-head" pts={ellPts(24, 16, 7, 7, 14)} color="#3a3450" opt={{ w: 0.9 }} />
        <Ink clip={c} k="sh-body" pts={[[12, 42], [14, 28], [24, 24], [34, 28], [36, 42]]} color="#3a3450" opt={{ w: 0.9 }} />
        <Line k="sh-ghost" pts={[[34, 14], [40, 10], [44, 16], [42, 26]]} w={1} color="#a898ff" dash="2 2" />
        <Dot x={21} y={16} r={1.2} color="#c8bcff" />
        <Dot x={27} y={16} r={1.2} color="#c8bcff" />
      </>
    ),
  },
  N: {
    zh: "留言",
    draw: (c) => (
      <>
        <Ink clip={c} k="note" pts={[[8, 10], [40, 10], [40, 32], [22, 32], [14, 40], [15, 32], [8, 32]]} color="#f2e6c8" opt={{ w: 0.9 }} />
        {[17, 23].map((y) => (
          <Line key={y} k={`note-l${y}`} pts={[[13, y], [35, y]]} w={0.8} color="#8a7a5a" />
        ))}
        <Ink clip={c} k="note-pin" pts={ellPts(36, 12, 3, 3, 10)} color="#c83a2a" opt={{ shade: false, w: 0.5 }} />
      </>
    ),
  },
  R: {
    zh: "潛行",
    draw: (c) => (
      <>
        {/* 6F-7（美術 PM 驗收小修 5）：深色兜帽放在深色按鈕底上看不見，墊一個淺色的月光圓底（停用、整條變淡時也看得出形狀） */}
        <circle className="sneak-moon" cx={24} cy={22} r={19} fill={SNEAK_MOON} stroke="#8a94b8" strokeWidth={1} />
        <Ink clip={c} k="sneak-hood" pts={[[14, 22], [18, 10], [30, 8], [38, 18], [36, 30], [24, 26]]} color="#3a3a44" opt={{ w: 0.9 }} />
        <Ink clip={c} k="sneak-face" pts={[[22, 18], [32, 16], [33, 24], [24, 25]]} color="#1a1a20" opt={{ shade: false, w: 0.5 }} />
        <Dot x={26} y={20} r={1.1} color="#c8f0ff" />
        <Dot x={30} y={20} r={1.1} color="#c8f0ff" />
        <Line k="sneak-trail" pts={[[8, 40], [18, 36], [28, 40], [40, 36]]} w={1.2} color="#8a8aa8" dash="3 3" />
      </>
    ),
  },
  M: {
    zh: "地圖",
    draw: (c) => (
      <>
        <Ink clip={c} k="map" pts={[[6, 12], [18, 8], [30, 12], [42, 8], [42, 38], [30, 42], [18, 38], [6, 42]]} color="#e8dcb8" opt={{ w: 0.9 }} />
        <Line k="map-f1" pts={[[18, 8], [18, 38]]} w={0.7} color="#8a7a5a" />
        <Line k="map-f2" pts={[[30, 12], [30, 42]]} w={0.7} color="#8a7a5a" />
        <Line k="map-route" pts={[[10, 34], [16, 26], [24, 28], [34, 18]]} w={1} color="#8a6a3a" />
        <g style={{ filter: "drop-shadow(0 0 2px #5ac8f0)" }}>
          <Dot x={34} y={18} r={3} color="#5aa0ff" />
        </g>
      </>
    ),
  },
};

/** 樣張的順序：I K G J Y N R M。 */
export const HUD_BAR_ORDER: readonly HudBarKey[] = ["I", "K", "G", "J", "Y", "N", "R", "M"];

export function hudBarName(key: HudBarKey): string {
  return ICONS[key].zh;
}

/** 功能列的定稿圖示（48×48 畫布，依 `size` 縮放）。 */
export function HudBarIcon({ k, size = 25 }: { k: HudBarKey; size?: number }) {
  const clip = `hudbar${useId().replace(/:/g, "")}`;
  return (
    <svg className="hud-icon hud-bar-icon" viewBox="0 0 48 48" width={size} height={size} aria-hidden="true" data-bar-icon={k}>
      {ICONS[k].draw(clip)}
    </svg>
  );
}
