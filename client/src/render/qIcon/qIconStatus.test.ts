// Phase QI-3a：Q 版狀態圖樣（status.ts）的行為一致測試——資料一律用名詞表快照 battle/fixtures/glossary.json（118 個狀態），不手寫清單。
// 規格 docs/phases/PhaseQI-3計畫.md 第 7 節 T-A1～T-A8（T-A9「遊戲畫面不變」＝statusIcon.test.ts 不改一字通過＋git diff，見 PhaseQI-3a報告.md）。
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";
import type { Glossary } from "../../api/types";
import glossary from "../../battle/fixtures/glossary.json";
import { setGlossary } from "../../battle/glossary";
import { fakeCanvasFactory, fakeCtx, type FakeCanvasLog } from "../../test/fakeCanvas";
import { paintStatusIcon } from "../statusIcon";
import { setQCanvasFactory, type QOpts } from "./core";
import * as QP from "./parts";
import * as QS from "./skills";
import * as QT from "./status";
import FIT from "./statusFit.json";

const real = glossary as unknown as Glossary;
const IDS = real.statuses.map((s) => s.id);
const FIT_TABLE = (FIT as { fit: Record<string, number> }).fit;
const OPTS: QOpts = { small: false, tiny: false, owPx: 0, badge: false, u: 1 };
/** 名詞表的控制類別（不手寫：從快照讀）。 */
const CLS = Object.fromEntries(real.statuses.flatMap((s) => (s.status_look?.control_group ? [[s.id, s.status_look.control_group]] : []))) as Record<string, string>;

const log: FakeCanvasLog = { calls: null };
beforeAll(() => { setQCanvasFactory(fakeCanvasFactory(log)); QT.clearQStatusMemo(); });
afterAll(() => { setQCanvasFactory(null); QT.clearQStatusMemo(); });
afterEach(() => { setGlossary(real); log.calls = null; });

/** 跑 fn，回傳 [外層 ctx 的紀錄, 另建畫布（glyph、halo、外框）的紀錄]。 */
function record(fn: (ctx: CanvasRenderingContext2D) => void): [string[], string[]] {
  const outer: FakeCanvasLog = { calls: [] };
  log.calls = [];
  fn(fakeCtx(outer));
  const inner = log.calls;
  log.calls = null;
  return [outer.calls ?? [], inner];
}
/** 同一份紀錄（外層＋另建畫布都記在 log）。 */
function sig(fn: (ctx: CanvasRenderingContext2D) => void): string {
  log.calls = [];
  fn(fakeCtx(log));
  const s = (log.calls ?? []).join(";");
  log.calls = null;
  return s;
}
/** 狀態卡（cardCanvas 的構圖：100 單位、框 84、unitPx px/100）與頭頂（headCanvas：框 px−2、unitPx 1）。 */
const card = (id: string | null | undefined, res: number, opt: QT.PaintOpt = {}) => (c: CanvasRenderingContext2D): void => QT.paint(c, id, 50, 50, 84, 20 / 100, res, opt);
const head = (id: string | null | undefined, res: number, opt: QT.PaintOpt = {}) => (c: CanvasRenderingContext2D): void => QT.paint(c, id, 11 / 2, 11 / 2, 11 - 2, 1, res, opt);
const CARD_FRAME = 84 * (20 / 100), HEAD_FRAME = (11 - 2) * 1;

describe("T-A1 名詞表 118 個都有 Q 版圖樣", () => {
  it("每個 entry(id) 都不是 null；來源：沿用 40（STATUS 32＋聖輝／暗影貳～伍 8）、借用 4、新畫 74（手畫 39＋紋章 35）", () => {
    expect(IDS.length).toBe(118);
    const es = IDS.map((id) => [id, QT.entry(id)] as const);
    for (const [id, e] of es) expect(e, id).not.toBeNull();
    const kinds = (k: string, family?: string | null): number => es.filter(([, e]) => e?.kind === k && (family === undefined || (e.family ?? null) === family)).length;
    expect([kinds("b4"), kinds("borrow"), kinds("new"), kinds("new", null), kinds("new", "element_stance")]).toEqual([40, 4, 74, 39, 35]);
    expect(es.filter(([id, e]) => e?.kind === "b4" && Object.prototype.hasOwnProperty.call(QP.STATUS, id)).length).toBe(32);
    expect(es.filter(([, e]) => e?.kind === "borrow").map(([id]) => id).sort()).toEqual(["revealed", "shielded", "time_bomb", "undying"]);
  });
  it("借用的 4 個呼叫 parts.ts／skills.ts 那一份（假畫布呼叫紀錄和直接呼叫該部件相同）", () => {
    const same: [string, (c: CanvasRenderingContext2D) => void][] = [
      ["revealed", (c) => QP.entry("effect", "reveal").d(c, OPTS)],
      ["time_bomb", (c) => QP.entry("effect", "delayed_damage").d(c, OPTS)],
      ["undying", (c) => QP.entry("effect", "cheat_death").d(c, OPTS)],
      ["shielded", (c) => QS.ACT.shield.d(c, OPTS, QS.ACT.shield.def as QS.Tint)],
    ];
    for (const [id, direct] of same) {
      const ours = sig((c) => QT.entry(id)!.d(c, OPTS));
      expect(ours.length, id).toBeGreaterThan(20);
      expect(ours, id).toBe(sig(direct));
    }
    // 沿用的 32 個＝第 4 批 STATUS 那一份
    for (const id of Object.keys(QP.STATUS)) expect(sig((c) => QT.entry(id)!.d(c, OPTS)), id).toBe(sig((c) => QP.STATUS[id]!.d(c, OPTS)));
  });
});

describe("T-A2 元素架勢各級同圖、同一個 stancePlate", () => {
  it("9 元素 × 5 級：同元素 5 級的 def 呼叫紀錄相同、level 1～5；聖輝、暗影 2～5 級和 1 級同圖", () => {
    expect(QT.ELEMENTS.length).toBe(9);
    for (const el of QT.ELEMENTS) {
      const ids = [1, 2, 3, 4, 5].map((n) => `stance_${el}_${n}`);
      for (const id of ids) expect(IDS, id).toContain(id);
      const sigs = ids.map((id) => sig((c) => QT.def(id, 20).d(c, OPTS)));
      for (const s of sigs) expect(s).toBe(sigs[0]);
      // 聖輝、暗影的壹級就是第 4 批 STATUS 那一個（entry 先查 STATUS，和樣張相同，所以沒有 level）；3b 的角落級數看 ID 樣式，不看 level
      expect(ids.map((id) => QT.entry(id)?.level)).toEqual(el === "holy" || el === "shadow" ? [undefined, 2, 3, 4, 5] : [1, 2, 3, 4, 5]);
    }
    for (const el of ["holy", "shadow"]) expect(sig((c) => QT.entry(`stance_${el}_3`)!.d(c, OPTS))).toBe(sig((c) => QP.STATUS[`stance_${el}_1`]!.d(c, { ...OPTS })));
  });
  it("姿態 9 個與元素架勢 45 個的第一筆都是 stancePlate 的六角臂章（parts.ts 的 hexPts(10.6)）", () => {
    const P = QP.hexPts(10.6).map(([x, y], i) => `${i ? "lineTo" : "moveTo"}(${x.toFixed(3)},${y.toFixed(3)})`).join(";");
    const stances = IDS.filter((id) => id.startsWith("stance_"));
    expect(stances.length).toBe(9 + 45);
    for (const id of stances) expect(sig((c) => QT.entry(id)!.d(c, OPTS)).startsWith(`beginPath();${P};closePath()`), id).toBe(true);
  });
});

describe("T-A3 框底色", () => {
  it("硬控 #d4ac20、移動 #2f78c8、心智 #8a4ccc；纏繞與其餘 111 個只填深底；順序 深底 → 類別底色 → 框線 → 圖樣", () => {
    const want: Record<string, string> = { stun: "#d4ac20", frozen: "#d4ac20", slow: "#2f78c8", root: "#2f78c8", taunted: "#8a4ccc", feared: "#8a4ccc", silenced: "#8a4ccc" };
    expect(Object.keys(CLS).sort()).toEqual(Object.keys(want).sort());
    let plain = 0;
    for (const id of IDS) for (const f of [card, head]) for (const res of [1, 2]) {
      const [outer] = record(f(id, res));
      const fills = outer.filter((c) => c.startsWith("fillStyle="));
      const at = (c: string): number => outer.indexOf(c);
      expect(fills[0], id).toBe("fillStyle=rgba(12,12,16,0.88)");
      if (want[id]) expect(fills, id).toEqual(["fillStyle=rgba(12,12,16,0.88)", `fillStyle=${want[id]}`]);
      else expect(fills.length, id).toBe(1);
      const lastFill = outer.lastIndexOf("fill()"), stroke = at("stroke()"), img = outer.findIndex((c) => c.startsWith("drawImage("));
      expect(lastFill < stroke && stroke < img, id).toBe(true);
      if (!want[id] && f === card && res === 2) plain++;
    }
    expect(plain).toBe(111);
    expect(want["entangled"]).toBeUndefined();
  });
});

describe("T-A4 外框與頭頂形", () => {
  const hasOutline = (inner: string[]): boolean => inner.includes("globalCompositeOperation=source-in");
  const glyphSide = (outer: string[]): number => Number(/drawImage\(canvas\((\d+)x/.exec(outer.find((c) => c.startsWith("drawImage(")) ?? "")?.[1]);
  it("狀態卡（框 16.8）：染底的 7 個包 1 裝置像素外框（ow＝1/res），不染底的不包（圖樣 ≤ 14px）", () => {
    for (const id of IDS) for (const res of [1, 2]) {
      const [outer, inner] = record(card(id, res));
      expect(hasOutline(inner), `${id} res ${res}`).toBe(id in CLS);
      if (id in CLS) expect(inner, id).toContain("drawImage(canvas(" + glyphSide(outer) + "x" + glyphSide(outer) + "),1.000,0.000)"); // dilate 的第一筆位移＝1 裝置像素
      expect(CARD_FRAME * QT.GLYPH_K * QT.fitK(id, CARD_FRAME)).toBeLessThanOrEqual(14);
    }
  });
  it("頭頂（框 9）：染底的不包外框、inset＝1/res（圖樣大小照表上 inset 那一筆）、暈眩／沉默／嘲諷走 HEAD_TINT，其他 4 個原本的形", () => {
    const tintCol: Record<string, string> = { stun: "fillStyle=#fbf3dc", silenced: "fillStyle=#f0e2ff", taunted: "quadraticCurveTo(4.600,4.600,10.000,4.600)" };
    for (const id of Object.keys(CLS)) for (const res of [1, 2]) {
      const [outer, inner] = record(head(id, res));
      expect(hasOutline(inner), id).toBe(false);
      const key = QT.fitKey(id, HEAD_FRAME, 1 / res);
      expect(FIT_TABLE[key], key).toBeDefined();
      expect(glyphSide(outer), key).toBe(Math.max(4, Math.round(HEAD_FRAME * QT.GLYPH_K * FIT_TABLE[key]! * QP.BOX * res)));
      expect(sig((c) => QT.def(id, 6, true).d(c, OPTS)) === sig((c) => QT.def(id, 6, false).d(c, OPTS)), id).toBe(!(id in tintCol));
      if (tintCol[id]) { expect(inner, id).toContain(tintCol[id]); expect(record(card(id, res))[1], id).not.toContain(tintCol[id]); }
    }
  });
  it("tint: false：不染、不內縮、不包外框、不換頭頂形", () => {
    for (const id of Object.keys(CLS)) for (const res of [1, 2]) {
      const [co, ci] = record(card(id, res, { tint: false }));
      expect(co.filter((c) => c.startsWith("fillStyle=")), id).toEqual(["fillStyle=rgba(12,12,16,0.88)"]);
      expect(hasOutline(ci), id).toBe(false);
      const [ho, hi] = record(head(id, res, { tint: false }));
      expect(glyphSide(ho), id).toBe(Math.max(4, Math.round(HEAD_FRAME * QT.GLYPH_K * FIT_TABLE[QT.fitKey(id, HEAD_FRAME, 0)]! * QP.BOX * res)));
      for (const c of ["fillStyle=#fbf3dc", "fillStyle=#f0e2ff", "quadraticCurveTo(4.600,4.600,10.000,4.600)"]) expect(hi, id).not.toContain(c);
    }
  });
});

describe("T-A5 貼圖對齊整數裝置像素", () => {
  const pick = (pol: string): string => IDS.find((id) => real.statuses.find((s) => s.id === id)?.status_look?.polarity === pol && !(id in CLS))!;
  const cases = [pick("buff"), pick("debuff"), pick("neutral"), "stun", "brand_new_status"];
  it("框 16.8（unitPx 0.2）、9（unitPx 1）、開發頁 52 × res 1、2 × 五類：左上角 × unitPx × res 是整數、貼圖不縮放", () => {
    const layouts: [string, number, (id: string, res: number) => (c: CanvasRenderingContext2D) => void][] = [
      ["card", 20 / 100, (id, res) => card(id, res)],
      ["head", 1, (id, res) => head(id, res)],
      ["52", 1, (id, res) => (c) => QT.paint(c, id, 26, 26, 50, 1, res)],
    ];
    let n = 0;
    for (const [name, unitPx, f] of layouts) for (const res of [1, 2]) for (const id of cases) {
      const [outer] = record(f(id, res));
      const imgs = outer.filter((c) => c.startsWith("drawImage("));
      if (id === "brand_new_status") { expect(imgs, name).toEqual([]); expect(outer.some((c) => c.startsWith("fillText(")), name).toBe(true); continue; }
      expect(imgs.length, `${name} ${id}`).toBe(1);
      const m = /^drawImage\(canvas\((\d+)x(\d+)\),([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+)\)$/.exec(imgs[0]!)!;
      const [W, x, y, w] = [Number(m[1]), Number(m[3]), Number(m[4]), Number(m[5])], k = unitPx * res;
      expect(Math.abs(x * k - Math.round(x * k)), `${name} ${id} x`).toBeLessThan(2e-3);
      expect(Math.abs(y * k - Math.round(y * k)), `${name} ${id} y`).toBeLessThan(2e-3);
      expect(Math.abs(w * k - W), `${name} ${id} 不縮放`).toBeLessThan(2e-3);
      n++;
    }
    expect(n).toBe(3 * 2 * 4);
  });
});

describe("T-A6 fitK 表", () => {
  it("涵蓋名詞表全部 × {16.8, 9} × res {1, 2} 用到的 inset；值在 [0.7, 1]（內縮的 [0.4, 1]）且是 0.02 的整數倍", () => {
    let n = 0;
    for (const id of IDS) for (const frame of [CARD_FRAME, HEAD_FRAME]) for (const res of [1, 2]) {
      const inset = QT.tintInset(frame, res, QT.clsOf(id)), v = FIT_TABLE[QT.fitKey(id, frame, inset)];
      expect(v, QT.fitKey(id, frame, inset)).toBeDefined();
      expect(v!, id).toBeLessThanOrEqual(1);
      expect(v!, id).toBeGreaterThanOrEqual(inset > 0 ? 0.4 : 0.7);
      expect(Math.abs(v! * 50 - Math.round(v! * 50)), id).toBeLessThan(1e-9);
      n++;
    }
    expect(n).toBe(118 * 2 * 2);
    // 頭頂染底的 7 個 × 2 種 inset＋全部 × 2 種框的 inset 0（含 tint=0 對照）
    expect(Object.keys(FIT_TABLE).length).toBe(118 * 2 + 7 * 2);
    expect(QT.fitTableSize()).toBe(250);
  });
  it("表上的鍵回表值、不量（不呼叫 getImageData）；表上沒有的鍵在沒有 Path2D 時回 1、不丟例外", () => {
    log.calls = [];
    for (const key of Object.keys(FIT_TABLE)) { const [id, size, inset] = key.split("|"); expect(QT.fitK(id!, Number(size), Number(inset)), key).toBe(FIT_TABLE[key]); }
    expect(log.calls).toEqual([]);
    expect(QT.fitK("stun", 50)).toBe(1);
    expect(QT.fitK("brand_new_status", 16.8)).toBe(1);
    expect(log.calls.some((c) => c.startsWith("getImageData"))).toBe(false);
  });
});

describe("T-A7 框線寬", () => {
  it("max(1.5, 框 CSS px × 0.09) / unitPx：狀態卡 20 是 7.56 單位、頭頂 11 是 1.5 px，和現行 paintStatusIcon 相同", () => {
    const lw = (calls: string[]): string | undefined => calls.find((c) => c.startsWith("lineWidth="));
    for (const id of ["stun", "hasted", "concealed"]) {
      const [c1] = record(card(id, 2)), [h1] = record(head(id, 2));
      expect(lw(c1)).toBe("lineWidth=7.560");
      expect(lw(h1)).toBe("lineWidth=1.500");
      expect(lw(record((c) => paintStatusIcon(c, id, 50, 50, 84))[0])).toBe("lineWidth=7.560");
      expect(lw(record((c) => paintStatusIcon(c, id, 5.5, 5.5, 9))[0])).toBe("lineWidth=1.500");
    }
  });
});

describe("T-A8 不認得、不丟例外", () => {
  it("brand_new_status、空字串、null、不認得的極性：畫名稱第一個字（字色 #f2e6c8）或「?」", () => {
    setGlossary({ ...real, statuses: [...real.statuses, { id: "odd_status", name_zh: "怪異", description_zh: null, tags: [], rules_zh: [], status_look: { polarity: "weird", control_group: "hard", dot_element: null, skip_turn: false, removed_by_element: [], absorbs_damage: false, prevents_move: false } }] } as unknown as Glossary);
    const text = (id: string | null | undefined): string => { const [o] = record(card(id, 2)); const i = o.findIndex((c) => c.startsWith("fillText(")); expect(o[i - 4], String(id)).toBe("fillStyle=#f2e6c8"); return o[i]!; };
    expect(text("brand_new_status")).toBe("fillText(b,0.000,1.000)");
    expect(text("")).toBe("fillText(?,0.000,1.000)");
    expect(text(null)).toBe("fillText(?,0.000,1.000)");
    expect(text(undefined)).toBe("fillText(?,0.000,1.000)");
    expect(text("odd_status")).toBe("fillText(怪,0.000,1.000)");
    // 不認得的極性退 neutral（六角），有類別照類別染底
    const [o] = record(card("odd_status", 2));
    expect(o.filter((c) => c.startsWith("fillStyle=")).slice(0, 2)).toEqual(["fillStyle=rgba(12,12,16,0.88)", "fillStyle=#d4ac20"]);
    expect(o.filter((c) => c.startsWith("lineTo(")).length).toBe(6);
  });
  it("全部 × 尺寸 × res 畫兩次（先暖快取）呼叫紀錄相同；不丟例外", () => {
    for (const id of [...IDS, "brand_new_status", "", null]) for (const f of [card, head]) for (const res of [1, 2]) {
      const a = sig(f(id, res)), b = sig(f(id, res));
      expect(a, String(id)).toBe(b);
    }
  });
  it("沒有畫布時 glyph 回 null、paint 只畫框不丟例外、headCanvas／cardCanvas 回 null", () => {
    setQCanvasFactory(null);
    try {
      expect(QT.glyph("stun", 12)).toBeNull();
      expect(QT.headCanvas("stun", 11)).toBeNull();
      expect(QT.cardCanvas("stun", 20)).toBeNull();
      const [o] = record(card("stun", 2));
      expect(o.some((c) => c.startsWith("drawImage("))).toBe(false);
      expect(o).toContain("stroke()");
    } finally { setQCanvasFactory(fakeCanvasFactory(log)); }
  });
});
