// RG-4 開發頁：熔殼甲兵的熔殼大盾（特徵 molten_shield）和樣張逐像素比對。
//   樣張 docs/art/sample/rgUnits.js 的 SHELL.a.draw vs 遊戲端 inkCreature.ts 的 TRAITS.molten_shield.draw，
//   同一個座標系（腳底 (0,0)、朝東）× 縮放 1、2、4 × DPR 1、2 × 朝東／朝西 × 錨點整數／小數，差異像素數輸出到 <pre id="out">。
// 網址：/dev/rg4-shell-gallery.html（本頁不出聲）。
import rgUnitsSrc from "../../../docs/art/sample/rgUnits.js?raw";
import { TRAITS, type FxInfo, type Palette } from "../render/inkCreature";

type SampleDraw = (ctx: CanvasRenderingContext2D, a: unknown, P: { base: string }) => void;

function loadSample(): SampleDraw {
  const s = document.createElement("script");
  s.textContent = rgUnitsSrc;
  document.head.appendChild(s);
  const RG = (window as unknown as { RGUnits: { SHELL: { a: { draw: SampleDraw } } } }).RGUnits;
  return RG.SHELL.a.draw;
}

function canvas(w: number, h: number): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  return c;
}

function diffPx(a: HTMLCanvasElement, b: HTMLCanvasElement): number {
  const A = a.getContext("2d")!.getImageData(0, 0, a.width, a.height).data;
  const B = b.getContext("2d")!.getImageData(0, 0, b.width, b.height).data;
  let n = 0;
  for (let i = 0; i < A.length; i += 4) if (A[i] !== B[i] || A[i + 1] !== B[i + 1] || A[i + 2] !== B[i + 2] || A[i + 3] !== B[i + 3]) n++;
  return n;
}

function paint(draw: (ctx: CanvasRenderingContext2D) => void, k: number, dpr: number, west: boolean, ox: number): HTMLCanvasElement {
  const W = 48 * k;
  const H = 40 * k;
  const c = canvas(Math.round(W * dpr), Math.round(H * dpr));
  const g = c.getContext("2d")!;
  g.scale(dpr, dpr);
  g.translate(W / 2 + ox, H - 4 + ox);
  if (west) g.scale(-1, 1);
  g.scale(k, k);
  g.translate(-23, 0);
  draw(g);
  return c;
}

const sample = loadSample();
const game = TRAITS["molten_shield"]!.draw;
const P = { base: "#4a3631" };
const lines: string[] = [];
let total = 0;
const row = document.createElement("div");
row.className = "row";
for (const k of [1, 2, 4])
  for (const dpr of [1, 2])
    for (const west of [false, true])
      for (const ox of [0, 0.37]) {
        const a = paint((g) => sample(g, {}, P), k, dpr, west, ox);
        const b = paint((g) => game(g, {} as FxInfo, P as unknown as Palette), k, dpr, west, ox);
        const d = diffPx(a, b);
        total += d;
        lines.push(`k=${k} dpr=${dpr} ${west ? "west" : "east"} ox=${ox}: diff=${d}`);
        if (ox === 0 && dpr === 1) row.append(a, b);
      }
document.body.append(row);
const pre = document.createElement("pre");
pre.id = "out";
pre.textContent = [...lines, `total diff=${total}`].join("\n");
document.body.append(pre);
