// PB-1c：頭目部位小圖示（docs/art/頭目部位-移植需求.md 1.4、2.1）。
// vitest 沒有 Canvas：頭像的像素步驟（門檻、方眼、鬍子暗面）拆成純函式測；實際畫出來的像素（外接框、半透明、方眼數）
// 在開發頁 `client/dev/bossparts-gallery.html` 的 `body.dataset.check` 量（報告附結果）。
import { afterEach, describe, expect, it } from "vitest";
import { fakeCanvasFactory } from "../../test/fakeCanvas";
import { setQCanvasFactory } from "./core";
import {
  alphaThreshold,
  bossPartIcon,
  bossPartIconKey,
  clearBossPartIcons,
  eyeBoxes,
  paintEyes,
  PORTRAIT,
  portraitDeviceMap,
  shadeBeardEdge,
} from "./bossParts";

/** 紙娃娃座標的左眼矩形 → 裝置像素的兩塊方眼（同 `portraitGlyph` 的算法）。 */
function eyesAt(px: number, res: number) {
  const m = portraitDeviceMap(px, res);
  const to = (x: number, y: number) => ({ x: m.a * x + m.e, y: m.d * y + m.f });
  const S = Math.max(4, Math.round(px * res));
  return { S, boxes: eyeBoxes(to(PORTRAIT.eyeX - PORTRAIT.eyeW / 2, PORTRAIT.eyeY), to(PORTRAIT.eyeX + PORTRAIT.eyeW / 2, PORTRAIT.eyeY + PORTRAIT.eyeH), S) };
}

describe("本體小頭像（1.4）", () => {
  it("20px 真 1 倍：兩塊 2×2 方眼、共 8 px、對中線對稱", () => {
    const { S, boxes } = eyesAt(20, 1);
    expect(boxes.map((b) => [b.w, b.h])).toEqual([
      [2, 2],
      [2, 2],
    ]);
    expect(boxes.reduce((n, b) => n + b.w * b.h, 0)).toBe(8);
    const [l, r] = boxes;
    expect(l!.x + l!.w / 2 + (r!.x + r!.w / 2)).toBe(S); // 對中線鏡像
    expect(l!.y).toBe(r!.y);
    expect(r!.x).toBeGreaterThan(l!.x + l!.w - 1); // 兩塊分開
  });

  it("24px 是 2×3、20px 2 倍內部解析度是 3×4（需求 1.4 第 5 點）", () => {
    expect(eyesAt(24, 1).boxes[0]).toMatchObject({ w: 2, h: 3 });
    expect(eyesAt(20, 2).boxes[0]).toMatchObject({ w: 3, h: 4 });
  });

  it("方眼填實心 #1d1a22、alpha 255", () => {
    const W = 6;
    const d = new Uint8ClampedArray(W * W * 4);
    paintEyes(d, W, [{ x: 1, y: 2, w: 2, h: 2 }]);
    const at = (x: number, y: number) => Array.from(d.slice((y * W + x) * 4, (y * W + x) * 4 + 4));
    expect(at(1, 2)).toEqual([0x1d, 0x1a, 0x22, 255]);
    expect(at(2, 3)).toEqual([0x1d, 0x1a, 0x22, 255]);
    expect(at(3, 3)).toEqual([0, 0, 0, 0]);
  });

  it("alpha 門檻之後沒有 1～254 的像素（≤32px 第 4 步）", () => {
    const d = new Uint8ClampedArray(256 * 4);
    for (let i = 0; i < 256; i++) d[i * 4 + 3] = i;
    alphaThreshold(d);
    const alphas = new Set(Array.from({ length: 256 }, (_, i) => d[i * 4 + 3]));
    expect([...alphas].sort((a, b) => a! - b!)).toEqual([0, 255]);
    expect(d[127 * 4 + 3]).toBe(0);
    expect(d[128 * 4 + 3]).toBe(255);
  });

  it("鬍子下緣暗面：鬍子裡、正下方不在鬍子裡但不透明的那一格改 #bbbbbb", () => {
    const W = 3;
    const H = 3;
    const d = new Uint8ClampedArray(W * H * 4).fill(255);
    const beard = (x: number, y: number) => y <= 1 && x === 1;
    shadeBeardEdge(d, W, H, beard, 0);
    const rgb = (x: number, y: number) => Array.from(d.slice((y * W + x) * 4, (y * W + x) * 4 + 3));
    expect(rgb(1, 1)).toEqual([0xbb, 0xbb, 0xbb]);
    expect(rgb(1, 0)).toEqual([255, 255, 255]); // 正下方還在鬍子裡
    expect(rgb(0, 1)).toEqual([255, 255, 255]); // 不在鬍子裡
    shadeBeardEdge(d.fill(255), W, H, beard, 2); // y0 以上不處理
    expect(rgb(1, 1)).toEqual([255, 255, 255]);
  });

  it("20px：裁切框寬佔顯示邊長 75%（15px ≥ 14）、水平置中", () => {
    const m = portraitDeviceMap(20, 1);
    const [bx, , bw] = PORTRAIT.box;
    const left = m.a * bx + m.e;
    const right = m.a * (bx + bw) + m.e;
    expect(right - left).toBeCloseTo(15, 6);
    expect((left + right) / 2).toBeCloseTo(10, 6);
  });
});

describe("部位圖示（2.1）", () => {
  afterEach(() => {
    setQCanvasFactory(null);
    clearBossPartIcons();
  });

  it("沒有畫布時回傳 null", () => {
    expect(bossPartIcon("whisk", 20, 2)).toBeNull();
  });

  it("拂塵、氣海、長劍、從背後、本體（沒有外觀時米白人形）都畫得出來：畫布＝顯示 × 解析度", () => {
    setQCanvasFactory(fakeCanvasFactory({ calls: null }));
    for (const id of ["whisk", "dantian", "sword", "back", "body"]) {
      const cv = bossPartIcon(id, 20, 2);
      expect(cv, id).not.toBeNull();
      expect(cv!.width).toBe(40);
    }
    expect(bossPartIcon("back", 16, 2)!.width).toBe(32);
  });

  it("快取鍵：只有本體看頭目外觀", () => {
    const doll = { template: "sect_mist_lock_master", dollLook: null, weaponId: "one_handed_sword" };
    expect(bossPartIconKey("whisk", 20, 2, doll)).toBe(bossPartIconKey("whisk", 20, 2));
    expect(bossPartIconKey("body", 20, 2, doll)).not.toBe(bossPartIconKey("body", 20, 2));
  });
});
