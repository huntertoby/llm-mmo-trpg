// 開發用：頭目部位小圖示（PB-1c；需求 docs/art/頭目部位-移植需求.md 1.4、2.1、5.1）。開 `client/dev/bossparts-gallery.html`
// （自己的 vite 後 /dev/bossparts-gallery.html?mute=1）。不屬於正式 build。每格都走遊戲端 `render/qIcon/bossParts.ts`（和選單同一張畫布），
// 複製一份貼上、CSS 放大（`image-rendering: pixelated`，最近鄰）。本體＝霧鎖真人小頭像（外觀取 `render/fixtures/unitDolls.json`，
// 和伺服器 `UnitView.doll_look` 同一份內容匯出）。
// 參數：
//   ?px=<顯示邊長,…>   預設 16,20,24,32
//   &res=<1|2,…>      內部解析度（預設 1,2；1＝真 1 倍）
//   &zoom=<k>         放大 k 倍（預設 4）
//   &label=0          不顯示名稱
// 量測（需求 1.4 的單元測試項目，vitest 沒有 Canvas 所以在這裡量）放 `body.dataset.check`（JSON）：
//   每個 (px, res) 的本體：不帶外框的不透明像素外接框（寬高、中心偏移）、alpha 介於 1～254 的像素數、實心 #1d1a22 方眼像素數與左右對稱。
//   外接框檢查（PB-1c 美術驗收）：20px 真 1 倍外接框寬 ≥12、高 ≥15、置中（`bboxOk`，只有 20px × 1 那格有；門檻見 `PORTRAIT_BBOX_MIN`）。
// 畫好後 `body.dataset.ready = "1"`。
import dolls from "../render/fixtures/unitDolls.json";
import { waitForFonts } from "../render/fontLoad";
import { bossPartDef, bossPartIcon, grayIcon, PORTRAIT_BBOX_MIN, portraitBboxOk, type BossDoll } from "../render/qIcon/bossParts";
import { render } from "../render/qIcon/core";

const q = new URLSearchParams(location.search);
const list = (k: string, d: string): string[] => (q.get(k) ?? d).split(",").filter((s) => s !== "");
const PXS = list("px", "16,20,24,32").map(Number);
const RESS = list("res", "1,2").map(Number);
const ZOOM = Number(q.get("zoom") ?? 4);
const LABEL = q.get("label") !== "0";
const IDS: [string, string][] = [
  ["body", "本體（小頭像）"],
  ["whisk", "拂塵"],
  ["dantian", "氣海"],
  ["sword", "長劍"],
  ["back", "從背後"],
];
const DOLL: BossDoll = { template: "sect_mist_lock_master", dollLook: (dolls as Record<string, unknown>)["sect_mist_lock_master"] as BossDoll["dollLook"], weaponId: "one_handed_sword" };

const h = <T extends keyof HTMLElementTagNameMap>(tag: T, props: Partial<HTMLElementTagNameMap[T]> = {}, ...kids: (Node | string)[]): HTMLElementTagNameMap[T] => {
  const e = Object.assign(document.createElement(tag), props);
  e.append(...kids);
  return e;
};

function show(src: HTMLCanvasElement, css: number, zoom: number): HTMLCanvasElement {
  const c = document.createElement("canvas");
  c.width = src.width;
  c.height = src.height;
  c.getContext("2d")?.drawImage(src, 0, 0);
  c.style.width = `${css * zoom}px`;
  c.style.height = `${css * zoom}px`;
  return c;
}

/** 已破壞：灰掉＋紅「×」（同 `ui/PartBar.tsx`）。 */
function broken(src: HTMLCanvasElement, px: number, res: number): HTMLCanvasElement {
  const g = grayIcon(src);
  const x = g.getContext("2d");
  if (x === null) return g;
  x.save();
  x.scale(res, res);
  x.lineCap = "round";
  const k = px / 20;
  for (const [col, lw] of [
    ["#16121a", 3.4],
    ["#ff6a5a", 1.8],
  ] as const) {
    x.strokeStyle = col;
    x.lineWidth = lw;
    x.beginPath();
    x.moveTo(3 * k, 3 * k);
    x.lineTo(17 * k, 17 * k);
    x.moveTo(17 * k, 3 * k);
    x.lineTo(3 * k, 17 * k);
    x.stroke();
  }
  x.restore();
  return g;
}

interface Check {
  px: number;
  res: number;
  bboxW: number;
  bboxH: number;
  centerDx: number;
  semi: number;
  eyePx: number;
  eyeMirror: boolean;
  /** 20px 真 1 倍：外接框寬 ≥12、高 ≥15、置中（PB-1c 驗收）。其他大小不檢查。 */
  bboxOk?: boolean;
}

function measure(px: number, res: number): Check | null {
  const bare = render(bossPartDef("body", DOLL), px, res, { ow: 0 });
  const full = bossPartIcon("body", px, res, DOLL);
  if (bare === null || full === null) return null;
  const S = bare.width;
  const a = bare.getContext("2d")?.getImageData(0, 0, S, S).data;
  const f = full.getContext("2d")?.getImageData(0, 0, S, S).data;
  if (a === undefined || f === undefined) return null;
  let x0 = S;
  let y0 = S;
  let x1 = -1;
  let y1 = -1;
  let semi = 0;
  const eyes: [number, number][] = [];
  for (let y = 0; y < S; y++)
    for (let x = 0; x < S; x++) {
      const i = (y * S + x) * 4;
      const al = a[i + 3] ?? 0;
      if (al > 0) {
        x0 = Math.min(x0, x);
        y0 = Math.min(y0, y);
        x1 = Math.max(x1, x);
        y1 = Math.max(y1, y);
      }
      if (al > 0 && al < 255) semi++;
      if (f[i] === 0x1d && f[i + 1] === 0x1a && f[i + 2] === 0x22 && f[i + 3] === 255) eyes.push([x, y]);
    }
  const mirror = eyes.every(([x, y]) => eyes.some(([u, v]) => v === y && u === S - 1 - x));
  const bboxW = (x1 - x0 + 1) / res;
  const bboxH = (y1 - y0 + 1) / res;
  const centerDx = (x0 + x1 + 1) / 2 / res - px / 2;
  const gate = px === PORTRAIT_BBOX_MIN.px && res === PORTRAIT_BBOX_MIN.res ? { bboxOk: portraitBboxOk(bboxW, bboxH, centerDx) } : {};
  return { px, res, bboxW, bboxH, centerDx, semi, eyePx: eyes.length, eyeMirror: mirror, ...gate };
}

async function main(): Promise<void> {
  await waitForFonts();
  document.body.append(h("h2", { textContent: "頭目部位小圖示（PB-1c）：每列＝一個圖示；每格＝顯示邊長 × 內部解析度，左真 1 倍、右最近鄰放大" }));
  for (const [id, zh] of IDS) {
    const row = h("div", { className: "row" });
    for (const px of PXS)
      for (const res of RESS) {
        const cv = bossPartIcon(id, px, res, id === "body" ? DOLL : null);
        if (cv === null) continue;
        const icons = h("div", { className: "icons" }, show(cv, px, 1), show(cv, px, ZOOM));
        if (id !== "body" && id !== "back") icons.append(show(grayIcon(cv), px, ZOOM), show(broken(cv, px, res), px, ZOOM));
        row.append(h("div", { className: "cell" }, icons, ...(LABEL ? [h("div", { className: "label", textContent: `${zh} ${px}px × ${res}` })] : [])));
      }
    document.body.append(row);
  }
  const checks = PXS.flatMap((px) => RESS.map((res) => measure(px, res))).filter((c): c is Check => c !== null);
  document.body.dataset.check = JSON.stringify(checks);
  document.body.append(h("pre", { className: "out", textContent: checks.map((c) => JSON.stringify(c)).join("\n") }));
  document.body.dataset.ready = "1";
}

void main();
