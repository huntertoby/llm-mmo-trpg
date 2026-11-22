// CR-1b（佇列 (w)，docs/art/CR-1驗收.md）：目標浮動卡避開預覽面板。
import { describe, expect, it } from "vitest";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { avoidPanel, type ScreenRect } from "./hoverCard";

const W = 270;
const GAP = 8;
const rect = (left: number, top: number, w: number, h: number): ScreenRect => ({ left, top, right: left + w, bottom: top + h });

describe("avoidPanel（800 寬）", () => {
  const vis = rect(4, 4, 792, 592);
  const panel = rect(8, 160, 222, 270); // 左上的預覽面板
  const tile = rect(405, 237, 30, 30); // 目標（木樁）

  it("原本擺在目標左邊、蓋到面板 → 改擺目標右邊，位置高度不變", () => {
    const card = { left: tile.left - GAP - W, top: 237, w: W, h: 150 };
    expect(avoidPanel(card, tile, vis, panel, GAP)).toEqual({ left: tile.right + GAP, top: 237, under: false });
  });

  it("右邊放不下 → 目標上方（水平置中、夾進畫面）", () => {
    const right = rect(600, 300, 30, 30);
    const card = { left: right.left - GAP - W, top: 200, w: W, h: 120 };
    const wide = rect(4, 4, 650, 592);
    const narrowPanel = rect(8, 150, 330, 200);
    const out = avoidPanel(card, right, wide, narrowPanel, GAP);
    expect(out).toEqual({ left: 654 - W, top: right.top - GAP - 120, under: false });
  });

  it("右邊、上方都放不下 → 目標下方", () => {
    const t = rect(300, 40, 30, 30);
    const card = { left: t.left - GAP - W, top: 40, w: W, h: 200 };
    const v = rect(4, 4, 500, 592);
    const p = rect(8, 30, 160, 60);
    const out = avoidPanel(card, t, v, p, GAP);
    expect(out.under).toBe(false);
    expect(out.top).toBe(t.bottom + GAP);
    expect(out.left).toBe(Math.min((t.left + t.right - W) / 2, 504 - W));
  });

  it("怎麼擺都會重疊 → 照原位、預覽面板放上層", () => {
    const t = rect(300, 200, 30, 30);
    const card = { left: t.left - GAP - W, top: 200, w: W, h: 400 };
    const v = rect(4, 4, 600, 592);
    const p = rect(8, 4, 300, 592); // 面板佔滿左邊整條
    expect(avoidPanel(card, t, v, p, GAP)).toEqual({ left: card.left, top: 200, under: true });
  });

  it("原本在目標右邊、蓋到面板（面板在右）→ 改擺左邊", () => {
    const t = rect(400, 200, 30, 30);
    const card = { left: t.right + GAP, top: 200, w: W, h: 100 };
    const p = rect(500, 150, 200, 200);
    expect(avoidPanel(card, t, vis, p, GAP)).toEqual({ left: t.left - GAP - W, top: 200, under: false });
  });

  it("沒有面板（沒在選取）時照原位", () => {
    const card = { left: 127, top: 237, w: W, h: 150 };
    expect(avoidPanel(card, tile, vis, null, GAP)).toEqual({ left: 127, top: 237, under: false });
  });
});

describe("avoidPanel（1600 寬）", () => {
  it("面板在戰場外、卡片沒碰到 → 位置不變", () => {
    const vis = rect(470, 70, 680, 625);
    const panel = rect(8, 163, 252, 310);
    const tile = rect(808, 356, 56, 56);
    const card = { left: tile.left - GAP - W, top: 356, w: W, h: 190 };
    expect(avoidPanel(card, tile, vis, panel, GAP)).toEqual({ left: card.left, top: 356, under: false });
  });
});

describe("接線", () => {
  const read = (p: string) => readFile(SRC_DIR, p);
  it("HoverFloat 量面板 `.mode-panel`、BattleScreen 傳目標格；放不下時加 under-panel（z-index 在面板下面）", () => {
    const float = read("ui/HoverFloat.tsx");
    expect(float).toContain('document.querySelector(".mode-panel")');
    expect(float).toContain('el.classList.toggle("under-panel", free.under)');
    expect(read("screens/BattleScreen.tsx")).toContain("tile={tileBox(cardTile, data.model, scale)}");
    expect(read("styles/float-card.css")).toMatch(/\.unit-float\.under-panel \{\s*z-index: 11;/);
  });
});
