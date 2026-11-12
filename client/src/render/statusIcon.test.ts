// Phase 3-36a：狀態圖示、頭頂狀態列排序／排版、身上特效。
// QI-3b（T-B8）：狀態框裡換 Q 版圖樣（`qIcon/status.ts`），改寫的斷言逐條見 docs/phases/PhaseQI-3b報告.md 第 3 節（不放寬）。
import { afterEach, describe, expect, it } from "vitest";
import { fakeCanvasFactory, fakeCtx as qFakeCtx, type FakeCanvasLog } from "../test/fakeCanvas";
import { setQCanvasFactory } from "./qIcon/core";
import * as QT from "./qIcon/status";
import type { Glossary } from "../api/types";
import glossary from "../battle/fixtures/glossary.json";
import { setGlossary } from "../battle/glossary";
import {
  bodyEffects,
  bodyOver,
  bodyUnder,
  effectsKey,
  FRAME_COLOR,
  GLYPH,
  glyphColor,
  paintStatusIcon,
  polarityOf,
  sortStatuses,
  statusRowLayout,
} from "./statusIcon";

const real = glossary as unknown as Glossary;
afterEach(() => {
  setGlossary(real);
  setQCanvasFactory(null);
});

/** 掛上 Q 版假畫布（圖樣真的畫出來），回傳記錄外層與圖樣畫布的 log。 */
function withQCanvas(): FakeCanvasLog {
  const log: FakeCanvasLog = { calls: [] };
  setQCanvasFactory(fakeCanvasFactory(log));
  return log;
}

function fakeCtx(): { ctx: CanvasRenderingContext2D; calls: string[]; props: Record<string, unknown> } {
  const calls: string[] = [];
  const props: Record<string, unknown> = {};
  const ctx = new Proxy(props, {
    get(_t, name: string) {
      if (name in props) return props[name];
      if (name === "createRadialGradient" || name === "createLinearGradient") return () => ({ addColorStop: () => undefined });
      return (..._args: unknown[]) => {
        calls.push(name);
      };
    },
    set(_t, name: string, value) {
      props[name] = value;
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  return { ctx, calls, props };
}

const STATUS_IDS = real.statuses.map((s) => s.id);

describe("118 個狀態", () => {
  it("每個狀態都有 status_look、Q 版圖樣（舊 GLYPH 也還在，給部件圓片），且畫得出來、圖樣貼進框裡", () => {
    expect(STATUS_IDS.length).toBe(118);
    for (const id of STATUS_IDS) {
      const entry = real.statuses.find((s) => s.id === id);
      expect(entry?.status_look, id).toBeTruthy();
      expect(QT.entry(id), id).not.toBeNull(); // QI-3b：狀態框用的 Q 版圖樣
      expect(GLYPH[id], id).toBeDefined(); // 舊圖樣：部件圓片 32 種以外（hooks.status）、召喚物頭頂還在用
      const { ctx, calls } = fakeCtx();
      expect(() => paintStatusIcon(ctx, id, 10, 10, 14)).not.toThrow();
      expect(calls.length).toBeGreaterThan(5);
      withQCanvas();
      const outer: FakeCanvasLog = { calls: [] };
      paintStatusIcon(qFakeCtx(outer), id, 10, 10, 14);
      expect(outer.calls?.filter((c) => c.startsWith("drawImage(canvas(")).length, id).toBe(1); // Q 版圖樣 blit 一次
      expect(outer.calls?.some((c) => c.startsWith("fillText")), id).toBe(false); // 不走「第一個字」
    }
  });

  it("外框依 polarity：增益圓、減益方、中性六角（姿態是中性）", () => {
    const shape = (id: string): string => {
      const { ctx, calls } = fakeCtx();
      paintStatusIcon(ctx, id, 0, 0, 26);
      const first = calls.find((c) => c === "arc" || c === "roundRect" || c === "lineTo");
      return first === "arc" ? "round" : first === "roundRect" ? "square" : "hex";
    };
    for (const s of real.statuses) {
      const pol = s.status_look?.polarity;
      const got = shape(s.id);
      if (pol === "buff") expect(got, s.id).toBe("round");
      else if (pol === "debuff") expect(got, s.id).toBe("square");
      else expect(got, s.id).toBe("hex");
    }
    expect(polarityOf("stance_fury")).toBe("neutral");
    expect(polarityOf("stance_bulwark")).toBe("neutral");
  });

  it("四組原本重複的圖樣已分開（舊 GLYPH 與 Q 版 def 都分開）", () => {
    const sig = (id: string): string => {
      const { ctx, calls } = fakeCtx();
      GLYPH[id]?.(ctx);
      return calls.join(",");
    };
    /** Q 版圖樣定義的呼叫紀錄（狀態卡 16.8 × 0.74 的圖樣大小；含 halo 另建畫布的紀錄）。 */
    const qsig = (id: string): string => {
      const log = withQCanvas();
      QT.def(id, 12.4).d(qFakeCtx(log), { ow: 0, owPx: 0 } as never);
      return (log.calls ?? []).join(";");
    };
    for (const [a, b] of [
      ["revealed", "overwatch"],
      ["defending", "guarded"],
      ["guarded", "shielded"],
      ["defending", "shielded"],
      ["empowered", "rallied"],
      ["stance_fury", "stance_bulwark"],
    ] as const)
      expect(qsig(a), `Q ${a} vs ${b}`).not.toBe(qsig(b));
    for (const [a, b] of [
      ["revealed", "overwatch"],
      ["defending", "guarded"],
      ["guarded", "shielded"],
      ["defending", "shielded"],
      ["empowered", "rallied"],
      ["stance_fury", "stance_bulwark"],
    ] as const)
      expect(sig(a), `${a} vs ${b}`).not.toBe(sig(b));
  });

  it("框的底色（QI-3b）：硬控 #d4ac20、移動 #2f78c8、心智 #8a4ccc，其餘（含纏繞）只填深底；框裡不再用 glyphColor", () => {
    const want: Record<string, string> = { stun: "#d4ac20", frozen: "#d4ac20", slow: "#2f78c8", root: "#2f78c8", taunted: "#8a4ccc", feared: "#8a4ccc", silenced: "#8a4ccc" };
    for (const id of STATUS_IDS) {
      withQCanvas();
      const outer: FakeCanvasLog = { calls: [] };
      paintStatusIcon(qFakeCtx(outer), id, 50, 50, 84, 0.2, 2);
      const fills = (outer.calls ?? []).filter((c) => c.startsWith("fillStyle=")).map((c) => c.slice(10));
      expect(fills, id).toEqual(want[id] === undefined ? ["rgba(12,12,16,0.88)"] : ["rgba(12,12,16,0.88)", want[id]]);
      const strokes = (outer.calls ?? []).filter((c) => c.startsWith("strokeStyle=")).map((c) => c.slice(12));
      expect(strokes, id).toEqual([FRAME_COLOR[polarityOf(id)]]);
      expect([...fills, ...strokes].includes(glyphColor(id)) && !Object.values(FRAME_COLOR).includes(glyphColor(id)), id).toBe(false);
    }
    expect(want["entangled"]).toBeUndefined();
  });

  it("圖樣顏色（部件圓片用，狀態框不再用）：硬控黃、移動控制藍、心智控制紫、持續傷害用元素色", () => {
    expect(glyphColor("stun")).toBe("#ffd84a");
    expect(glyphColor("frozen")).toBe("#ffd84a");
    expect(glyphColor("slow")).toBe("#6ac8ff");
    expect(glyphColor("root")).toBe("#6ac8ff");
    expect(glyphColor("feared")).toBe("#c890ff");
    expect(glyphColor("burning")).toBe("#ff6a1a");
    expect(glyphColor("poison")).toBe("#7ddc3a");
    expect(glyphColor("shielded")).toBe("#8ac8ff");
    expect(glyphColor("weaken")).toBe("#ff8a8a"); // 其餘依 polarity
  });
});

describe("不認得的狀態", () => {
  it("不認得的 ID、polarity、空字串、null 都畫得出來、不丟例外", () => {
    const withLook = (id: string, polarity: string): void => {
      setGlossary({ ...real, statuses: [...real.statuses, { id, name_zh: "新奇狀態", description_zh: null, tags: [], rules_zh: [], status_look: { polarity, control_group: null, dot_element: null, skip_turn: false, removed_by_element: [], absorbs_damage: false, prevents_move: false } }] });
    };
    for (const id of ["brand_new", "", "zzz_未知"]) {
      const { ctx } = fakeCtx();
      expect(() => paintStatusIcon(ctx, id, 0, 0, 14)).not.toThrow();
    }
    expect(() => paintStatusIcon(fakeCtx().ctx, null, 0, 0, 14)).not.toThrow();
    expect(() => paintStatusIcon(fakeCtx().ctx, undefined, 0, 0, 14)).not.toThrow();
    for (const pol of ["weird", "", "BUFF"]) {
      withLook("odd_status", pol);
      expect(polarityOf("odd_status")).toBe("neutral");
      expect(() => paintStatusIcon(fakeCtx().ctx, "odd_status", 0, 0, 14)).not.toThrow();
    }
    withLook("new_buff", "buff");
    expect(polarityOf("new_buff")).toBe("buff");
    expect(glyphColor("new_buff")).toBe("#7dffb0");
    // QI-3b：不認得的增益只填深底（沒有類別），框線用增益色
    const outer: FakeCanvasLog = { calls: [] };
    paintStatusIcon(qFakeCtx(outer), "new_buff", 0, 0, 14);
    expect((outer.calls ?? []).filter((c) => c.startsWith("fillStyle="))).toEqual(["fillStyle=rgba(12,12,16,0.88)", "fillStyle=#f2e6c8"]);
    expect(polarityOf("brand_new")).toBe("neutral"); // 沒有資料
  });

  it("不認得的狀態在中間畫名稱第一個字", () => {
    setGlossary({ ...real, statuses: [...real.statuses, { id: "brand_new", name_zh: "全新", description_zh: null, tags: [], rules_zh: [], status_look: null }] });
    const { ctx, calls } = fakeCtx();
    paintStatusIcon(ctx, "brand_new", 0, 0, 26);
    expect(calls).toContain("fillText");
    // QI-3b：字色米白 #f2e6c8、寫的是名稱第一個字
    const outer: FakeCanvasLog = { calls: [] };
    paintStatusIcon(qFakeCtx(outer), "brand_new", 0, 0, 26);
    const i = (outer.calls ?? []).findIndex((c) => c.startsWith("fillText("));
    expect(outer.calls?.[i]).toMatch(/^fillText\(全,/);
    expect((outer.calls ?? []).slice(0, i).filter((c) => c.startsWith("fillStyle=")).pop()).toBe("fillStyle=#f2e6c8");
  });
});

describe("頭頂狀態列", () => {
  it("排序：硬控 → 移動／心智控制 → 持續傷害 → 其他減益 → 增益 → 中性，與輸入順序無關", () => {
    const expected = ["frozen", "stun", "root", "slow", "feared", "silenced", "taunted", "burning", "poison", "bleed"];
    const ids = [...STATUS_IDS];
    const sorted = sortStatuses(ids);
    expect(sorted.slice(0, expected.length).sort()).toEqual([...expected].sort());
    expect(sorted.indexOf("stun")).toBeLessThan(sorted.indexOf("slow"));
    expect(sorted.indexOf("slow")).toBeLessThan(sorted.indexOf("poison"));
    expect(sorted.indexOf("poison")).toBeLessThan(sorted.indexOf("weaken"));
    expect(sorted.indexOf("weaken")).toBeLessThan(sorted.indexOf("hasted"));
    expect(sorted.indexOf("hasted")).toBeLessThan(sorted.indexOf("stance_fury"));
    for (let seed = 1; seed <= 5; seed++) {
      const shuffled = [...ids].sort((a, b) => ((a.length * seed + a.charCodeAt(1)) % 7) - ((b.length * seed + b.charCodeAt(1)) % 7) || (a < b ? 1 : -1));
      expect(sortStatuses(shuffled)).toEqual(sorted);
    }
    expect(sortStatuses(["stun", "stun", "poison"])).toEqual(["stun", "poison"]); // 去重
  });

  it("0 個、1 個、3 個、4 個、33 個狀態的排版", () => {
    expect(statusRowLayout([])).toEqual([]);
    expect(statusRowLayout(["stun"])).toHaveLength(1);
    expect(statusRowLayout(["stun", "poison", "burning"]).map((i) => i.kind)).toEqual(["icon", "icon", "icon"]);
    const four = statusRowLayout(["stun", "poison", "burning", "slow"]);
    expect(four.map((i) => i.kind)).toEqual(["icon", "icon", "more"]);
    expect(four[2]).toMatchObject({ kind: "more", extra: 2 });
    const many = Array.from({ length: 33 }, (_, i) => `status_${String(i).padStart(2, "0")}`);
    const layout = statusRowLayout(many);
    expect(layout).toHaveLength(3);
    expect(layout[2]).toMatchObject({ kind: "more", extra: 31 });
    // 置中：左右對稱
    expect(layout[0]?.x).toBeCloseTo(-(layout[2]?.x ?? 0));
    expect(statusRowLayout(["a", "b", "c"], 2).map((i) => i.kind)).toEqual(["icon", "more"]);
  });

  it("33 個狀態同時存在也畫得出來", () => {
    for (const item of statusRowLayout(STATUS_IDS)) {
      if (item.kind === "icon") expect(() => paintStatusIcon(fakeCtx().ctx, item.id, 0, 0, 14)).not.toThrow();
    }
  });
});

describe("身上特效（依欄位，不寫死 ID）", () => {
  it("冰凍＝冰塊、暈眩＝星星、護盾＝泡泡、定身＝藤蔓、持續傷害＝元素粒子", () => {
    expect(bodyEffects(["frozen"])).toMatchObject({ frozen: true, stunned: false });
    expect(bodyEffects(["stun"])).toMatchObject({ frozen: false, stunned: true });
    expect(bodyEffects(["frozen", "stun"])).toMatchObject({ frozen: true, stunned: false }); // 冰塊優先
    expect(bodyEffects(["shielded"]).absorb).toBe(true);
    expect(bodyEffects(["root"]).noMove).toBe(true);
    expect(bodyEffects(["burning", "poison", "bleed"]).dots).toHaveLength(2);
    expect(bodyEffects(["poison", "burning"]).dots).toEqual(bodyEffects(["burning", "poison"]).dots); // 與輸入順序無關
    expect(bodyEffects(["weaken", "hasted", "unknown_id"])).toEqual({ frozen: false, stunned: false, absorb: false, noMove: false, dots: [] });
    expect(bodyEffects([])).toEqual({ frozen: false, stunned: false, absorb: false, noMove: false, dots: [] });
  });

  it("新狀態只要 glossary 欄位對就有特效", () => {
    setGlossary({
      ...real,
      statuses: [
        ...real.statuses,
        { id: "petrified", name_zh: "石化", description_zh: null, tags: [], rules_zh: [], status_look: { polarity: "debuff", control_group: "hard", dot_element: null, skip_turn: true, removed_by_element: ["fire"], absorbs_damage: false, prevents_move: false } },
      ],
    });
    expect(bodyEffects(["petrified"]).frozen).toBe(true);
  });

  it("特效畫得出來、快取鍵只看有哪幾類", () => {
    const all = bodyEffects(["frozen", "shielded", "root", "burning", "poison"]);
    const { ctx, calls } = fakeCtx();
    expect(() => bodyUnder(ctx, all, 40, 70)).not.toThrow();
    expect(() => bodyOver(ctx, all, 40, 70, 1.2)).not.toThrow();
    expect(calls.length).toBeGreaterThan(10);
    expect(effectsKey(bodyEffects(["burning"]))).toBe(effectsKey(bodyEffects(["burning"])));
    expect(effectsKey(bodyEffects(["burning"]))).not.toBe(effectsKey(bodyEffects(["poison"])));
    expect(effectsKey(bodyEffects(["weaken"]))).toBe(effectsKey(bodyEffects([])));
    for (const id of STATUS_IDS) expect(() => bodyOver(fakeCtx().ctx, bodyEffects([id]), 40, 70)).not.toThrow();
  });

  it("外框色表三種極性齊全", () => {
    expect(Object.keys(FRAME_COLOR).sort()).toEqual(["buff", "debuff", "neutral"]);
  });
});
