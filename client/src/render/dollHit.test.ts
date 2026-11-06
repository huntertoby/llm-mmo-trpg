// Phase 6M-4（併入美術 PM 檢查 docs/archive/art/6A-4d至6M-3六段檢查.md）：人形受擊只閃剪影（像素測試）；沒有代號時不畫黑色小圓。
import { Texture } from "pixi.js";
import { describe, expect, it } from "vitest";
import type { BattleView } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { tile, unit } from "../battle/testFixtures";
import type { ArtTextures } from "./artTextures";
import { humanHit, HUMAN_HIT_MS, knockOffset, quantizeFlash } from "./motionClips";
import { DOLL_H, DOLL_W, renderFigureCanvas } from "./paperdoll";
import { resolveDollT } from "./testDolls";
import { buildUnitSprite, hasSkeleton, Pulses } from "./unitSprite";

const SPEC = resolveDollT({ team: "ally", summon: false, template: "hero_fighter", weaponId: "one_handed_sword" });

/** 假的 DOM 畫布：記錄每張畫布的指令；`getImageData` 回傳 `image(w, h)`，`putImageData` 收下結果。 */
function fakeDom(image: (w: number, h: number) => Uint8ClampedArray) {
  const log: string[] = [];
  const put: Uint8ClampedArray[] = [];
  const canvases: Array<{ id: number; width: number; height: number }> = [];
  const ctx2d = (c: { id: number; width: number; height: number }) =>
    new Proxy({} as Record<string, unknown>, {
      get(t, p: string) {
        if (p in t) return t[p];
        if (p === "getImageData") return () => ({ data: image(c.width, c.height) });
        if (p === "putImageData") return (img: { data: Uint8ClampedArray }) => (put.push(img.data), log.push(`${c.id}.putImageData`));
        return (...a: unknown[]) => void log.push(`${c.id}.${p}(${a.map((x) => (typeof x === "object" && x !== null && "id" in x ? `#${(x as { id: number }).id}` : String(x))).join(",")})`);
      },
      set(t, p: string, v) {
        t[p] = v;
        return true;
      },
    });
  const make = () => {
    const c = { id: canvases.length, width: 0, height: 0, getContext: () => ctx2d(c) };
    canvases.push(c);
    return c;
  };
  return { log, put, canvases, document: { createElement: make } };
}

function withDom<T>(dom: { document: unknown }, run: () => T): T {
  const g = globalThis as { document?: unknown };
  const saved = g.document;
  g.document = dom.document;
  try {
    return run();
  } finally {
    g.document = saved;
  }
}

/** 一張「角色」影像：中間一塊不透明的身體、邊緣半透明，其他透明。 */
function bodyImage(w: number, h: number): Uint8ClampedArray {
  const d = new Uint8ClampedArray(w * h * 4);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const i = (y * w + x) * 4;
      const inside = x > w * 0.4 && x < w * 0.6 && y > h * 0.3 && y < h * 0.9;
      const edge = !inside && x > w * 0.38 && x < w * 0.62 && y > h * 0.28 && y < h * 0.92;
      d.set(inside ? [120, 60, 40, 255] : edge ? [60, 30, 20, 100] : [0, 0, 0, 0], i);
    }
  }
  return d;
}

describe("6M-4：人形受擊白閃只閃剪影（不含地上的影子、不整格變白）", () => {
  it("受擊片段：開頭白閃 0.85、播到 1/4 時消失；往後彈 7 的弧線；仰一下", () => {
    expect(humanHit(0).flash).toBe(0.85);
    expect(humanHit(0.25).flash).toBe(0);
    expect(humanHit(1).flash).toBe(0);
    expect(humanHit(0).knock).toBeCloseTo(0, 9);
    expect(Math.max(...[0.1, 0.2, 0.3, 0.4].map((t) => humanHit(t).knock))).toBeGreaterThan(6.5);
    expect(humanHit(0.25).pose.lean).toBeLessThan(0);
    expect(HUMAN_HIT_MS).toBe(360);
    expect(knockOffset("east", 7)).toEqual({ x: -7, y: 0 });
    expect(knockOffset("west", 7)).toEqual({ x: 7, y: 0 });
    expect(knockOffset("south", 7).y).toBeLessThan(0);
  });

  it("白閃量化到 0.05（快取鍵用）；0 或負數 ＝ 沒有白閃", () => {
    expect(quantizeFlash(0.8333)).toBe(0.85);
    expect(quantizeFlash(0.02)).toBe(0);
    expect(quantizeFlash(0)).toBe(0);
    expect(quantizeFlash(-1)).toBe(0);
    expect(quantizeFlash(3)).toBe(1);
  });

  it("像素：疊回去的剪影只在身體的像素上變白，剪影外完全透明；不透明度 × 白閃", () => {
    const dom = fakeDom(bodyImage);
    withDom(dom, () => renderFigureCanvas(SPEC, "east", false, 2, true, null, 0.85));
    expect(dom.put).toHaveLength(1);
    const out = dom.put[0]!;
    const src = bodyImage(DOLL_W * 2, DOLL_H * 2);
    let body = 0;
    for (let i = 0; i < src.length; i += 4) {
      if (src[i + 3] === 0) {
        expect(out[i + 3], `像素 ${i / 4}`).toBe(0);
        continue;
      }
      body += 1;
      expect([out[i], out[i + 1], out[i + 2]]).toEqual([255, 255, 255]);
      expect(out[i + 3]).toBe(Math.round(src[i + 3]! * 0.85));
    }
    expect(body).toBeGreaterThan(0);
    expect(body).toBeLessThan(src.length / 4 / 4); // 只有身體，不是整格
  });

  it("白閃用的身體另畫一次、不畫地上的影子，以像素對齊疊回（先重設變換）；沒有白閃時只畫一張", () => {
    const dom = fakeDom(bodyImage);
    withDom(dom, () => renderFigureCanvas(SPEC, "east", false, 2, true, null, 0.85));
    const reset = dom.log.indexOf("0.setTransform(1,0,0,1,0,0)");
    expect(reset).toBeGreaterThanOrEqual(0);
    const main = dom.log.slice(0, reset).filter((l) => l.startsWith("0.")).length;
    const flashBody = dom.log.filter((l) => l.startsWith("1.") && l !== "1.putImageData").length;
    expect(flashBody).toBeLessThan(main); // 白閃的身體少畫地上的影子（ground ＝ false）
    expect(dom.log.indexOf("0.drawImage(#1,0,0)")).toBeGreaterThan(reset);
    expect(dom.log.some((l) => l.startsWith("1.fillRect"))).toBe(false);
    const plain = fakeDom(bodyImage);
    withDom(plain, () => renderFigureCanvas(SPEC, "east", false, 2, true, null, 0));
    expect(plain.canvases).toHaveLength(1);
    expect(plain.put).toHaveLength(0);
  });
});

describe("6M-4：戰場沒有代號時不畫黑色小圓", () => {
  const view = (): BattleView =>
    ({ team: "ally", map_id: "m", map_name_zh: "m", width: 2, height: 1, tiles: [tile(0, 0), tile(1, 0)], objects: [], units: [unit("unit_0001", "ally", 0, 0, { template_id: "hero_fighter" })], traps: [], turn_order: ["unit_0001"], active_unit: "unit_0001", round: 1, max_rounds: 9, weather_id: null, weather_name_zh: null, objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null, source_wells: [], zones: [], runes: [] }) as unknown as BattleView;
  const art = { figure: () => Texture.WHITE, creature: () => Texture.WHITE, summon: () => Texture.WHITE, dollFx: () => null } as unknown as ArtTextures;

  it("marker ＝ \"\"：比有代號時少兩個節點（黑圓與字）；有代號時照舊", () => {
    const u: UnitDraw = buildDrawModel(view(), "unit_0001").units[0]!;
    expect(u.marker).not.toBe("");
    const withTag = buildUnitSprite(art, new Pulses(), u).children.length;
    const none = buildUnitSprite(art, new Pulses(), { ...u, marker: "" }).children.length;
    expect(withTag - none).toBe(2);
    expect(hasSkeleton(u)).toBe(true);
  });
});
