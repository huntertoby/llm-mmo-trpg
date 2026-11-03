// Phase 6C-8：形態、召喚物、倒地的人受擊改成剪影白閃（同一張圖 brightness(0) invert(1) 再畫一次）——像素測試與畫法測試。
import { Container, Sprite, Texture } from "pixi.js";
import { describe, expect, it } from "vitest";
import type { BattleView } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { tile, unit } from "../battle/testFixtures";
import type { ArtTextures } from "./artTextures";
import { drawForm } from "./inkForm";
import { clearFlash, FLASH_LABEL, overlayFlash, whiteCanvas } from "./silhouetteFlash";
import { renderSummonCanvas, resolveSummonLook } from "./summonArt";
import { BODY_LABEL, flashTexture, hasSkeleton, overlayFlashKind } from "./unitSprite";

const W = 16;
/** 16×16 的 RGBA：中間 6×6 是不透明的身體、外面一圈半透明邊；腳下一排（y＝13）是地上的影子（只在 `withShadow` 時有）。 */
function pixels(withShadow: boolean): Uint8ClampedArray {
  const d = new Uint8ClampedArray(W * W * 4);
  for (let y = 0; y < W; y++) {
    for (let x = 0; x < W; x++) {
      const i = (y * W + x) * 4;
      const inside = x >= 5 && x < 11 && y >= 5 && y < 11;
      const edge = !inside && x >= 4 && x < 12 && y >= 4 && y < 12;
      const shadow = withShadow && y === 13 && x >= 3 && x < 13;
      d.set(inside ? [120, 60, 200, 255] : edge ? [60, 30, 100, 128] : shadow ? [43, 30, 22, 128] : [0, 0, 0, 0], i);
    }
  }
  return d;
}

/** 假的畫布：`getImageData` 回傳 `data`，`putImageData` 寫回。 */
function fakeCanvas(data: Uint8ClampedArray): { canvas: HTMLCanvasElement; out: () => Uint8ClampedArray } {
  let stored = data;
  const ctx = {
    getImageData: () => ({ data: new Uint8ClampedArray(stored) }),
    putImageData: (img: { data: Uint8ClampedArray }) => {
      stored = img.data;
    },
  };
  const canvas = { width: W, height: W, getContext: () => ctx } as unknown as HTMLCanvasElement;
  return { canvas, out: () => stored };
}

/** Canvas／Pixi 的 source-over（非預乘）：把 `top`（再乘 `alpha`）疊到 `base`。 */
function over(base: Uint8ClampedArray, top: Uint8ClampedArray, alpha: number): Uint8ClampedArray {
  const out = new Uint8ClampedArray(base.length);
  for (let i = 0; i < base.length; i += 4) {
    const as = (top[i + 3]! / 255) * alpha;
    const ad = base[i + 3]! / 255;
    const ao = as + ad * (1 - as);
    out[i + 3] = Math.round(ao * 255);
    for (let c = 0; c < 3; c++) out[i + c] = ao === 0 ? 0 : Math.round((top[i + c]! * as + base[i + c]! * ad * (1 - as)) / ao);
  }
  return out;
}

describe("6C-8：白色剪影（brightness(0) invert(1)）像素測試", () => {
  it("whiteCanvas：身體像素變白、不透明度不變；透明的像素維持透明", () => {
    const src = pixels(false);
    const { canvas, out } = fakeCanvas(src);
    expect(whiteCanvas(canvas)).toBe(canvas);
    const res = out();
    let body = 0;
    for (let i = 0; i < src.length; i += 4) {
      if (src[i + 3] === 0) {
        expect(res[i + 3], `像素 ${i / 4}`).toBe(0);
        continue;
      }
      body += 1;
      expect([res[i], res[i + 1], res[i + 2], res[i + 3]]).toEqual([255, 255, 255, src[i + 3]]);
    }
    expect(body).toBe(64);
    expect(whiteCanvas(null)).toBeNull();
  });

  it("疊回小人上：只有剪影變白，地上的影子與剪影外完全不變（不整格變白）", () => {
    const base = pixels(true); // 小人本來的貼圖（含地上影子）
    const { canvas, out } = fakeCanvas(pixels(false)); // 白閃用：同一張圖不含地上影子
    whiteCanvas(canvas);
    const lit = over(base, out(), 0.85);
    let whiter = 0;
    let same = 0;
    for (let y = 0; y < W; y++) {
      for (let x = 0; x < W; x++) {
        const i = (y * W + x) * 4;
        const isBody = x >= 4 && x < 12 && y >= 4 && y < 12;
        if (isBody) {
          expect(lit[i]!).toBeGreaterThan(base[i]!);
          whiter += 1;
        } else {
          expect([...lit.slice(i, i + 4)], `像素 (${x},${y})`).toEqual([...base.slice(i, i + 4)]);
          same += 1;
        }
      }
    }
    expect(whiter).toBe(64);
    expect(same).toBe(W * W - 64); // 影子（y＝13）也在不變的這一邊
  });
});

describe("6C-8：白閃用的身體不畫地上的影子", () => {
  function recorder(): { ctx: CanvasRenderingContext2D; calls: string[] } {
    const calls: string[] = [];
    const ctx = new Proxy({} as Record<string, unknown>, {
      get(t, p: string) {
        if (p in t) return t[p];
        if (p === "getImageData") return () => ({ data: new Uint8ClampedArray(16) });
        if (p === "createLinearGradient" || p === "createRadialGradient") return () => ({ addColorStop: () => undefined });
        return (...a: unknown[]) => void calls.push(`${p}(${a.map((x) => (typeof x === "number" ? x.toFixed(2) : String(x))).join(",")})`);
      },
      set(t, p: string, v) {
        t[p] = v;
        calls.push(`${p}=${String(v)}`);
        return true;
      },
    }) as unknown as CanvasRenderingContext2D;
    return { ctx, calls };
  }
  const SHADOW = "strokeStyle=rgba(43,30,22,0.5)"; // inkStyle.shadow() 的短斜線

  it("形態：ground ＝ false 時少畫影子，其他筆畫相同", () => {
    const a = recorder();
    drawForm(a.ctx, "bear", "#a04030", null, "east", false);
    const b = recorder();
    drawForm(b.ctx, "bear", "#a04030", null, "east", false, false);
    expect(a.calls).toContain(SHADOW);
    expect(b.calls).not.toContain(SHADOW);
    expect(b.calls.length).toBeLessThan(a.calls.length);
    expect(b.calls.some((c) => c.startsWith("fillRect"))).toBe(false);
  });

  it("非人形召喚物：ground ＝ false 時不畫地面（影子）", () => {
    const run = (ground: boolean) => {
      const recorders: string[][] = [];
      const g = globalThis as { document?: unknown };
      const saved = g.document;
      g.document = {
        createElement: () => {
          const r = recorder();
          recorders.push(r.calls);
          return { width: 0, height: 0, getContext: () => r.ctx };
        },
      };
      try {
        renderSummonCanvas(resolveSummonLook({ body: "beast", variant: "wolf" }), "east", null, 2, ground);
      } finally {
        g.document = saved;
      }
      return recorders.flat();
    };
    const withGround = run(true);
    const noGround = run(false);
    expect(withGround).toContain(SHADOW);
    expect(noGround).not.toContain(SHADOW);
  });
});

describe("6C-8：哪些單位疊白色剪影、哪些照舊", () => {
  const view = (over: Partial<ReturnType<typeof unit>>): BattleView =>
    ({ team: "ally", map_id: "m", map_name_zh: "m", width: 2, height: 1, tiles: [tile(0, 0), tile(1, 0)], objects: [], units: [unit("unit_0001", "ally", 0, 0, over)], traps: [], turn_order: ["unit_0001"], active_unit: "unit_0001", round: 1, max_rounds: 9, weather_id: null, weather_name_zh: null, objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null, source_wells: [], zones: [], runes: [] }) as unknown as BattleView;
  const draw = (over: Partial<ReturnType<typeof unit>>): UnitDraw => buildDrawModel(view(over), "unit_0001").units[0]!;
  const prone = [{ status_id: "prone", remaining: 1, source_id: null, amount: null, charge_tiles: [], cost_status: false }] as unknown as ReturnType<typeof unit>["statuses"];
  const wolf = { owner_id: "unit_0009", summon_look: { body: "beast", variant: "wolf", element: null, size: "medium", trait: null } } as never;
  const form = { form_id: "bear", name_zh: "熊", category: "physical", look: "form_bear", element: null, natural_weapon_zh: "", effects_zh: [], upkeep_zh: "" } as unknown as ReturnType<typeof unit>["form"];

  it("形態、召喚物、倒下、倒地狀態 → 疊剪影；站著的紙娃娃（6M-4 骨架片段）→ 不疊", () => {
    expect(overlayFlashKind(draw({ form }))).toBe("form");
    expect(overlayFlashKind(draw(wolf))).toBe("summon");
    expect(overlayFlashKind(draw({ hp: 0, downed: true } as never))).toBe("downed");
    expect(overlayFlashKind(draw({ statuses: prone }))).toBe("downed");
    const standing = draw({ template_id: "hero_fighter" });
    expect(overlayFlashKind(standing)).toBeNull();
    expect(hasSkeleton(standing)).toBe(true);
  });

  it("flashTexture 照種類要對的白色剪影貼圖（不含影子的那一組）", () => {
    const asked: string[] = [];
    const art = {
      formFlash: (id: string) => (asked.push(`form:${id}`), Texture.WHITE),
      summonFlash: () => (asked.push("summon"), Texture.WHITE),
      figureFlash: (_s: unknown, _f: unknown, downed: boolean, pose: unknown) => (asked.push(`figure:${downed}:${pose === null ? "stand" : "lie"}`), Texture.WHITE),
    } as unknown as ArtTextures;
    flashTexture(art, draw({ form }));
    flashTexture(art, draw(wolf));
    flashTexture(art, draw({ hp: 0, downed: true } as never));
    flashTexture(art, draw({ statuses: prone }));
    expect(flashTexture(art, draw({ template_id: "hero_fighter" }))).toBeNull();
    expect(asked).toEqual(["form:bear", "summon", "figure:true:stand", "figure:false:lie"]);
  });

  it("overlayFlash：疊在小人正後面、跟小人同錨點縮放位置旋轉；不透明度＝白閃強度；結束時拿掉", () => {
    const unitNode = new Container();
    const ring = new Sprite(Texture.EMPTY);
    const body = new Sprite(Texture.EMPTY);
    body.label = BODY_LABEL;
    body.anchor.set(0.5, 0.9);
    body.scale.set(0.4, 0.4);
    body.position.set(0, 11);
    body.rotation = 1.2;
    const bar = new Sprite(Texture.EMPTY);
    unitNode.addChild(ring, body, bar);
    const top = overlayFlash(body, Texture.WHITE, 0.85)!;
    expect(unitNode.getChildIndex(top)).toBe(unitNode.getChildIndex(body) + 1);
    expect([top.anchor.x, top.anchor.y, top.scale.x, top.position.y, top.rotation]).toEqual([0.5, 0.9, 0.4, 11, 1.2]);
    expect(top.alpha).toBeCloseTo(0.85);
    expect(overlayFlash(body, Texture.WHITE, 0)).toBe(top); // 同一個節點，只換不透明度
    expect(top.visible).toBe(false);
    clearFlash(unitNode);
    expect(unitNode.children.some((n) => n.label === FLASH_LABEL)).toBe(false);
    expect(unitNode.children).toHaveLength(3);
  });
});
