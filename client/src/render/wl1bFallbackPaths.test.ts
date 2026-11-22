// WL-1 b 第 2 項：每條路都走得到退回畫法、不會壞（美術 PM 裁定 docs/art/WL-1b退回圖示.md：沿用現行畫法）。
// - 狀態圖示：`qIcon/status.ts` 的 `paintUnknown`（框＋名稱第一個字；沒有名稱畫「?」）。
// - 骨架徽章、其他部件圓片：`qIcon/parts.ts` 的 `entry()` 找不到 → Q 版扁平問號（`unknown: true`）。
// 不認得的 id、沒有名稱、空字串、null、undefined 都要畫得出來：不丟錯，也不能整格空白（至少有底／框，加上圖樣或字）。
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import type { Glossary, SkillIconData } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { setGlossary } from "../battle/glossary";
import { fakeCanvasFactory, fakeCtx, type FakeCanvasLog } from "../test/fakeCanvas";
import { setQCanvasFactory, type QOpts } from "./qIcon/core";
import * as QP from "./qIcon/parts";
import { clearQSkillDefs } from "./qIcon/skills";
import * as QT from "./qIcon/status";
import { clearQWeaponDefs } from "./qIcon/weapons";
import { assemblyFormula, paintSkillIcon, statusIconTile, statusTile, tileCanvas } from "./skillIcon";
import { statusIconCanvas } from "./statusIcon";

const real = glossary as unknown as Glossary;
const log: FakeCanvasLog = { calls: [] };

beforeAll(() => {
  clearQSkillDefs();
  clearQWeaponDefs();
  setQCanvasFactory(fakeCanvasFactory(log));
});
afterAll(() => {
  setQCanvasFactory(null);
  clearQSkillDefs();
  clearQWeaponDefs();
});
afterEach(() => setGlossary(real));

/** 外層畫布的呼叫（另建的圖樣畫布也記在同一份 log，先清空再畫）。 */
function drawn(fn: (ctx: CanvasRenderingContext2D) => void): string[] {
  log.calls = [];
  const ctx = fakeCtx(log);
  fn(ctx);
  return log.calls;
}

/** 名詞表裡有、但沒有名稱（空字串）的狀態；增益框。 */
const NAMELESS = "dev_nameless_status";
function withNameless(): void {
  const base = real.statuses[0]!;
  setGlossary({ ...real, statuses: [...real.statuses, { ...base, id: NAMELESS, name_zh: "" }] } as unknown as Glossary);
}

const BAD_IDS: readonly (string | null | undefined)[] = ["brand_new_thing", "", null, undefined];

describe("WL-1 b：狀態圖示走 paintUnknown", () => {
  it("不認得、沒有名稱、空字串、null、undefined：有框（fill＋stroke）、中間有一個字", () => {
    withNameless();
    for (const id of [...BAD_IDS, NAMELESS]) {
      for (const size of [16.8, 9]) {
        let calls: string[] = [];
        expect(() => (calls = drawn((ctx) => QT.paint(ctx, id, 10, 10, size, 1, 1))), String(id)).not.toThrow();
        expect(calls.some((c) => c.startsWith("fill(")), String(id)).toBe(true);
        expect(calls.some((c) => c.startsWith("stroke(")), String(id)).toBe(true);
        const text = calls.filter((c) => c.startsWith("fillText("));
        expect(text, String(id)).toHaveLength(1);
        const ch = text[0]!.slice("fillText(".length).split(",")[0];
        expect(ch, String(id)).not.toBe("");
      }
    }
  });

  it("沒有名稱的畫「?」；名詞表沒有的也畫「?」（WL-1 c：名稱退回「未知狀態」，不畫「未」也不畫 id 的第一個字）", () => {
    withNameless();
    const first = (id: string | null | undefined): string => drawn((ctx) => QT.paint(ctx, id, 10, 10, 16.8)).find((c) => c.startsWith("fillText("))!.split("(")[1]!.split(",")[0]!;
    expect(first("")).toBe("?");
    expect(first(null)).toBe("?");
    expect(first(undefined)).toBe("?");
    expect(first(NAMELESS)).toBe("?");
    expect(first("brand_new_thing")).toBe("?");
  });

  it("狀態卡、頭頂、組裝列的狀態圓片都畫得出來", () => {
    withNameless();
    for (const id of ["brand_new_thing", "", NAMELESS]) {
      expect(() => QT.cardCanvas(id, 20, 1, { res: 1 }), id).not.toThrow();
      expect(() => QT.headCanvas(id, 11, 1, { res: 1 }), id).not.toThrow();
      expect(() => statusIconCanvas(id, 20, 1), id).not.toThrow();
      expect(() => tileCanvas(statusIconTile(id), 20, 1), id).not.toThrow();
      // 狀態的部件圓片（組裝列）：不認得的畫 Q 版扁平問號（WL-1c；`skillParts.ts` 的 hooks.status）
      const calls = drawn((ctx) => statusTile(id).draw(ctx, 0.3, 1));
      expect(calls.some((c) => c.startsWith("fill(")), id).toBe(true);
      expect(calls.some((c) => c.startsWith("drawImage(")), id).toBe(true);
    }
  });

  it("WL-1c：組裝列狀態圓片的掛鉤，不認得的狀態畫的和其他類別的 Q 版問號一模一樣；認得的不是問號", () => {
    withNameless();
    const opts: QOpts = { small: false, tiny: false, owPx: 0, badge: false, u: 1 };
    const mark = drawn((ctx) => QP.unknownMark(ctx, opts));
    expect(mark.length).toBeGreaterThan(0);
    expect(drawn((ctx) => QP.entry("skeleton", "brand_new_thing").d(ctx, opts, undefined as never, {}))).toEqual(mark);
    for (const id of ["brand_new_thing", ""]) expect(drawn((ctx) => QP.hooks.status!(ctx, opts, id)), id).toEqual(mark);
    expect(drawn((ctx) => QP.hooks.status!(ctx, opts, "burning"))).not.toEqual(mark);
  });
});

describe("WL-1 b：骨架徽章、部件圓片走 Q 版問號", () => {
  it("每一類部件：不認得的 id、空字串都回問號（unknown），圓片有底、有色環、有圖樣", () => {
    for (const cat of Object.keys(QP.CATS).filter((c) => c !== "status")) {
      for (const id of ["brand_new_thing", ""]) {
        expect(QP.entry(cat, id).unknown, `${cat}:${id}`).toBe(true);
        const calls = drawn((ctx) => QP.chip(ctx, cat, id, 50, 50, 42, { res: 1 }));
        expect(calls.some((c) => c.startsWith("arc(")), `${cat}:${id}`).toBe(true);
        expect(calls.some((c) => c.startsWith("stroke(")), `${cat}:${id}`).toBe(true);
        expect(calls.some((c) => c.startsWith("drawImage(")), `${cat}:${id}`).toBe(true);
        expect(() => QP.chipCanvas(cat, id, 30, 1, { res: 1 })).not.toThrow();
      }
    }
  });

  const icon = (skeleton: string | null, rarity = "common"): SkillIconData =>
    ({
      kind: "active",
      rarity,
      elements: [],
      weapon_req: "any",
      segments: [{ skeleton, shape_id: "single", range: 3, elements: [], effects: [{ type: "damage" }] }],
      link: null,
      condition: null,
      costs: [],
      cost_values: {},
      trigger: null,
      modifier: null,
      partial: false,
    }) as unknown as SkillIconData;

  it("技能小圖的骨架徽章：不認得的骨架畫得出來（mid／full、兩種稀有度），比沒有骨架多畫一個徽章", () => {
    for (const rarity of ["common", "epic"]) {
      for (const [level, size] of [["mid", 56], ["full", 96]] as const) {
        let unknown: string[] = [];
        expect(() => (unknown = drawn((ctx) => paintSkillIcon(ctx, icon("brand_new_skeleton", rarity), level, size, 1)))).not.toThrow();
        const none = drawn((ctx) => paintSkillIcon(ctx, icon(null, rarity), level, size, 1));
        const known = drawn((ctx) => paintSkillIcon(ctx, icon("strike", rarity), level, size, 1));
        expect(unknown.filter((c) => c.startsWith("drawImage(")).length, `${rarity}/${level}`).toBe(known.filter((c) => c.startsWith("drawImage(")).length);
        expect(unknown.filter((c) => c.startsWith("arc(")).length, `${rarity}/${level}`).toBeGreaterThan(none.filter((c) => c.startsWith("arc(")).length);
      }
    }
    // 空字串的骨架：後端 `_text` 把空字串當沒有骨架（`None`），徽章照「沒有骨架」不畫（現行）；畫得出來、不丟錯
    expect(() => drawn((ctx) => paintSkillIcon(ctx, icon(""), "full", 96, 1))).not.toThrow();
  });

  it("組裝列的骨架格：不認得、空字串都畫問號、名稱不是英文 id", () => {
    for (const skeleton of ["brand_new_skeleton", ""]) {
      const tile = assemblyFormula(icon(skeleton)).rows[0]!.find((t) => t.cat === "骨架")!;
      expect(tile.label).toBe("未知骨架");
      const calls = drawn((ctx) => tile.draw(ctx, 0.3, 1));
      expect(calls.some((c) => c.startsWith("arc(")), skeleton).toBe(true);
      expect(calls.some((c) => c.startsWith("drawImage(")), skeleton).toBe(true);
      expect(() => tileCanvas(tile, 30, 1)).not.toThrow();
    }
  });

  it("沒有骨架（null）時組裝列不放骨架格，其他部件照畫", () => {
    const f = assemblyFormula(icon(null));
    expect(f.rows[0]!.map((t) => t.cat)).toEqual(["形狀", "效果（核心）"]);
  });
});
