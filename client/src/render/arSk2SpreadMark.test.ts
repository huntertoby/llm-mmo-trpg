// AR-SK2 移植需求第 6 項：狀態框的「會擴散」記號（B 案）、狀態列只在帶 contagious 的狀態疊記號、浮字統一成「擴散」。
import { describe, expect, it } from "vitest";
import type { BattleView, StatusView } from "../api/types";
import { buildDrawModel } from "../battle/drawModel";
import { feedbackFor, WORD_SPREAD } from "../battle/feedback";
import { smallView, unit } from "../battle/testFixtures";
import { spreadMark, SPORE_HEAD } from "./spreadMark";

interface Arc {
  x: number;
  y: number;
  r: number;
}

/** 記 arc（換回 ctx 單位）的假 ctx；變換只有縮放 k（裝置像素對齊用）。 */
function fakeCtx(k: number, out: Arc[]): CanvasRenderingContext2D {
  const m = { a: k, b: 0, c: 0, d: k, e: 0, f: 0, inverse: () => ({ a: 1 / k, b: 0, c: 0, d: 1 / k, e: 0, f: 0 }) };
  const noop = () => undefined;
  return new Proxy({} as Record<string, unknown>, {
    get: (_t, p) => (p === "getTransform" ? () => m : p === "arc" ? (x: number, y: number, r: number) => out.push({ x, y, r }) : noop),
    set: () => true,
  }) as unknown as CanvasRenderingContext2D;
}

/** 框（減益方框）的外緣：頂邊外緣離框心 half（線寬 max(1.5, 框邊長×0.09)）。 */
const half = (size: number, unitPx: number): number => 0.45 * size + Math.max(1.5, size * unitPx * 0.09) / unitPx / 2;

describe("AR-SK2 會擴散記號（B 案：框頂右段上方一顆孢子＋往右上跳的小點）", () => {
  for (const [name, size, unitPx, res] of [
    ["頭頂 11（框 9）", 9, 1, 2],
    ["頭頂 11 真 1 倍", 9, 1, 1],
    ["狀態卡 20（框 84 單位）", 84, 0.2, 2],
  ] as const) {
    it(`${name}：全部在框頂外緣之上（框線一個像素都不蓋）、孢子在框的右半`, () => {
      const arcs: Arc[] = [];
      spreadMark(fakeCtx(res * unitPx, arcs), size, unitPx, res, unitPx < 1 ? 49 : undefined);
      expect(arcs.length).toBe(4); // 小點、孢子各一圈外框＋本色
      const top = -Math.min(half(size, unitPx), unitPx < 1 ? 49 : Infinity);
      for (const a of arcs) expect(a.y + a.r, JSON.stringify(a)).toBeLessThanOrEqual(top + 1e-9);
      const spore = arcs[3] as Arc;
      expect(spore.x).toBeGreaterThan(0);
      const headSize = size * unitPx < SPORE_HEAD;
      expect(spore.r * unitPx).toBeCloseTo(headSize ? 1.5 : 2.2, 6);
    });
  }
});

describe("AR-SK2 狀態列只在帶 contagious 的狀態疊記號", () => {
  it("drawModel：帶 contagious 的狀態進 spreadIds；沒有時不多一個鍵", () => {
    const st = (id: string, contagious?: boolean): StatusView => ({ status_id: id, remaining: 2, source_id: null, amount: null, charge_tiles: [], cost_status: false, ...(contagious === undefined ? {} : { contagious }) }) as StatusView;
    const view = smallView({ units: [unit("a", "enemy", 0, 0, { statuses: [st("burning", true), st("poison")] }), unit("b", "enemy", 1, 0, { statuses: [st("bleed")] })] });
    const m = buildDrawModel(view, "x");
    expect(m.units.find((u) => u.id === "a")?.spreadIds).toEqual(["burning"]);
    expect("spreadIds" in (m.units.find((u) => u.id === "b") ?? {})).toBe(false);
  });

  it("浮字：標成會擴散、傳過去的那一刻都是「擴散」（取代「會傳染」）", () => {
    const view = { units: [unit("a", "enemy", 1, 1), unit("b", "enemy", 2, 1)] } as unknown as BattleView;
    const items = feedbackFor(
      [
        { seq: 1, round: 1, type: "contagion_marked", target_id: "a", status_ids: ["burning"] },
        { seq: 2, round: 1, type: "disease_spread", from_id: "a", to_id: "b", status_ids: ["burning"] },
      ],
      view,
    );
    const words = items.map((i) => (i as { text?: string }).text);
    expect(words).toEqual([WORD_SPREAD, WORD_SPREAD]);
    expect(WORD_SPREAD).toBe("擴散");
  });
});
