// Phase QI-4a：Q 版裝備關鍵字小圓章（keywords.ts）的行為一致測試（規格 docs/phases/PhaseQI-4計畫.md 第 7.1 節 T-A1～T-A7、T-A9）。
// 款式一律用 gearAppearance.json 的 kinds（105 款）、關鍵字用它的 keywords（12 個），不手寫清單；數字照需求 docs/art/Q版小圖示-關鍵字移植需求.md 第 3 節。
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import appearance from "../gearAppearance.json";
import { readSources } from "../../test/sourceScan";
import { fakeCanvasFactory, fakeCtx, type FakeCanvasLog } from "../../test/fakeCanvas";
import { gearQDef, resolveGear, type GearLook } from "../gearIcon";
import { KEYWORD_COLOR } from "../palette";
import { mix, OUT, setQCanvasFactory, type QOpts } from "./core";
import * as K from "./keywords";
import * as QP from "./parts";
import * as QS from "./skills";
import { clearQWeaponDefs } from "./weapons";
import { clearQArmorDefs } from "./armor";

interface Kind { id: string; forms: { id: string }[] }
const LOOKS: GearLook[] = (appearance.kinds as unknown as Kind[]).flatMap((k) => k.forms.map((f) => ({ kind: k.id, form: f.id })));
const KWS = appearance.keywords as string[];
const defOf = (look: GearLook): K.KeywordLook["def"] => gearQDef(look, resolveGear(look)) as unknown as K.KeywordLook["def"];
const fmt = (v: number): string => v.toFixed(3);

const log: FakeCanvasLog = { calls: null };
beforeAll(() => { clearQWeaponDefs(); clearQArmorDefs(); setQCanvasFactory(fakeCanvasFactory(log)); });
afterAll(() => { setQCanvasFactory(null); clearQWeaponDefs(); clearQArmorDefs(); });
/** 跑 fn，回傳 [外層 ctx 的紀錄, 另建畫布（圖樣、halo、外框）的紀錄]。 */
function record(fn: (ctx: CanvasRenderingContext2D) => void): [string[], string[]] {
  const outer: FakeCanvasLog = { calls: [] };
  log.calls = [];
  fn(fakeCtx(outer));
  const inner = log.calls;
  log.calls = null;
  return [outer.calls ?? [], inner];
}
/** 外層與另建畫布都記在同一份紀錄。 */
function sig(fn: (ctx: CanvasRenderingContext2D) => void): string[] {
  log.calls = [];
  fn(fakeCtx(log));
  const out = log.calls;
  log.calls = null;
  return out;
}
const O = (tiny: boolean, small = tiny): QOpts => ({ small, tiny, owPx: 0, badge: false, u: 1 });
/** 樣張 qIconsKeywords.js 的 KC（照抄，只給 T-A1 比對用）。 */
const SAMPLE_KC: Record<string, string> = { ignite: "#ff6a1a", wet: "#4aa8ff", charged: "#fff36b", frozen: "#8fe3ff", prone: "#e0b080", collision: "#ff9a4a", marked: "#d06aff", high_ground: "#ffe9a8", concealed: "#a0a0c8", summon: "#7dffb0", poisoned: "#7ad04a", form: "#e0a35a" };

describe("T-A1 12 個關鍵字的圖樣與色", () => {
  it("12 個都有圖樣、和 gearAppearance.json 的 keywords 同序；色＝KEYWORD_COLOR（和樣張 KC 逐筆相同）", () => {
    expect(KWS).toHaveLength(12);
    /* KW-3：四個層數關鍵字接在後面（裝備不帶；qIconKW3.test.ts） */
    const STACK = ["combo_point", "fury", "focus", "ki"];
    expect(K.KEYS).toEqual([...KWS, ...STACK]);
    expect(Object.keys(KEYWORD_COLOR)).toEqual(K.KEYS);
    for (const kw of KWS) expect(KEYWORD_COLOR[kw], kw).toBe(SAMPLE_KC[kw]);
  });
  it("k 照需求 3.3 表", () => {
    const k = Object.fromEntries(KWS.map((kw) => [kw, K.LIST[kw]!.k]));
    expect(k).toEqual({ ignite: 1.04, wet: 0.85, charged: 1.02, frozen: 1, prone: 0.74, collision: 0.76, marked: 0.85, high_ground: 0.73, concealed: 0.84, summon: 1, poisoned: 0.96, form: 0.94 });
  });
  it("元素 4 個呼叫 skills.ts 的 ELEMENT（縮 0.47、平移 −24、small）；其他 8 個呼叫需求 3.3 表的那個部件（呼叫紀錄逐筆相同）", () => {
    const el = (id: string) => (c: CanvasRenderingContext2D, o: QOpts) => { c.save(); c.scale(0.47, 0.47); c.translate(-24, -24); QS.ELEMENT[id]!.d(c, { ...o, small: true }); c.restore(); };
    const act = (id: string) => (c: CanvasRenderingContext2D, o: QOpts) => QS.ACT[id]!.d(c, o, QS.ACT[id]!.def ?? ["#ffd23f", "#ffffff"]);
    const part = (cat: string, id: string) => (c: CanvasRenderingContext2D, o: QOpts) => QP.entry(cat, id).d(c, o);
    const REF: Record<string, (c: CanvasRenderingContext2D, o: QOpts) => void> = {
      ignite: el("fire"), wet: el("water"), charged: el("lightning"), frozen: el("ice"), prone: act("knockdown"), collision: part("trigger", "on_collision"),
      marked: act("mark"), high_ground: part("condition", "height_advantage"), concealed: part("status", "concealed"), summon: act("summon"), poisoned: part("status", "poison"), form: part("effect", "enter_form"),
    };
    for (const kw of KWS) for (const o of [O(false), O(false, true), ...(kw === "collision" ? [] : [O(true)])]) {
      const a = sig((c) => K.LIST[kw]!.d(c, o)), b = sig((c) => REF[kw]!(c, o));
      expect(a.length, kw).toBeGreaterThan(3);
      expect(a, `${kw} ${JSON.stringify(o)}`).toEqual(b);
    }
  });
  it("glyph：圖樣格 cpx × 4/3、中心 (24,24) 放大 1.8；≤14px 不包外框", () => {
    for (const [cpx, ow] of [[11, false], [14, false], [14.44, true], [24, true]] as const) {
      const calls = sig(() => K.glyph("marked", cpx, 2));
      expect(calls, String(cpx)).toContain("translate(24.000,24.000)");
      expect(calls, String(cpx)).toContain("scale(1.800,1.800)");
      expect(calls.some((s) => s.startsWith("drawImage(canvas") && s.includes(",0.000,0.000)")) && calls.filter((s) => s.startsWith("drawImage(")).length > 1, String(cpx)).toBe(ow);
    }
  });
});

describe("T-A2 圓章大小與位置", () => {
  it("D、far、near 照需求 3.1 第 3 點；真 1 倍 32→13、42→18、48→20、64→27", () => {
    expect([32, 42, 48, 64].map((px) => K.sizeOf(px, 1))).toEqual([13, 18, 20, 27]);
    for (const px of [32, 42, 48, 64]) for (const res of [1, 2]) {
      const D = Math.round(px * 0.42 * res) / res, m = (px * 3.6) / 64, far = Math.round((px - m - D) * res) / res, near = Math.round(m * res) / res;
      expect(K.sizeOf(px, res)).toBe(D);
      expect(K.at("br", px, D, res)).toEqual([far, far]);
      expect(K.at("tl", px, D, res)).toEqual([near, near]);
      expect(K.at("bl", px, D, res)).toEqual([near, far]);
      for (const v of [far, near]) expect(Number.isInteger(Math.round(v * res * 1e6) / 1e6)).toBe(true);
    }
  });
  it("外圓 #16121a（半徑 D/2）→ 內圓 mix(關鍵字色, #191b22, 0.72)（半徑 D/2 − 1 裝置像素）；沒有 stroke", () => {
    for (const kw of KWS) for (const px of [32, 42, 48, 64]) for (const res of [1, 2]) {
      const D = K.sizeOf(px, res), [x0, y0] = K.at("br", px, D, res), cx = x0 + D / 2, cy = y0 + D / 2;
      const [outer] = record((c) => K.paint(c, [kw], px, res));
      const i1 = outer.indexOf(`fillStyle=${OUT}`), i2 = outer.indexOf(`fillStyle=${mix(KEYWORD_COLOR[kw]!, "#191b22", 0.72)}`);
      expect(i1, kw).toBeGreaterThanOrEqual(0);
      expect(i2, kw).toBeGreaterThan(i1);
      expect(outer).toContain(`arc(${fmt(cx)},${fmt(cy)},${fmt(D / 2)},0.000,6.283)`);
      expect(outer).toContain(`arc(${fmt(cx)},${fmt(cy)},${fmt(D / 2 - 1 / res)},0.000,6.283)`);
      expect(outer.filter((s) => s.startsWith("stroke("))).toEqual([]);
    }
  });
});

describe("T-A3 角", () => {
  it("KEY_CORNER 逐列鎖住（樣張原表）", () => {
    expect(K.KEY_CORNER).toEqual({
      axe: ["tl"], "hammer/flail": ["bl"], "scythe/crescent": ["tl"], bow: ["bl"], crossbow: ["bl"], shoes: ["tl"], boots: ["tl"], iron_boots: ["tl"], greaves: ["tl"], pendant: ["tl"], "circlet/bandana": ["bl"],
      cloth_gloves: ["bl"], leather_gloves: ["bl"], gauntlets: ["bl"], "charm/bone": ["bl"], "dual_dagger/short": ["br"], "dual_dagger/stiletto": ["br"], "dual_pistol/flintlock": ["br"], "dual_pistol/revolver": ["br"], "dual_pistol/derringer": ["br"], whip: ["br"], "longgun/sniper": ["br"],
    });
  });
  it("105 款：查 kind/form → kind → 右下；沒有任何一款放右上；例外表的每一列都對到實際的款", () => {
    expect(LOOKS).toHaveLength(107); // RG-5 起鳶盾多兩款（雲紋碑盾、熔殼塔盾）
    const used = new Set<string>();
    for (const look of LOOKS) {
      const c = K.cornersOf({ def: defOf(look) })[0], kf = `${look.kind}/${look.form}`, want = K.KEY_CORNER[kf]?.[0] ?? K.KEY_CORNER[look.kind!]?.[0] ?? "br";
      if (K.KEY_CORNER[kf]) used.add(kf); else if (K.KEY_CORNER[look.kind!]) used.add(look.kind!);
      expect(c, kf).toBe(want);
      expect(["br", "tl", "bl"]).toContain(c);
      expect(K.cornersOf({ kind: look.kind, form: look.form })[0], kf).toBe(want);
    }
    expect([...used].sort()).toEqual(Object.keys(K.KEY_CORNER).sort());
  });
});

/** 外層紀錄裡貼圓章圖樣（blit）的 drawImage。 */
const blits = (outer: string[]): string[] => outer.filter((s) => s.startsWith("drawImage("));
describe("T-A4 只畫一個圓章", () => {
  it("每款 × 1／2／3 個關鍵字：圓章一個、用 keywords[0]；1 個沒有記號；2、3 個記號相同（點色＝keywords[1]）", () => {
    for (const [i, look] of LOOKS.entries()) for (const px of [32, 48]) {
      const a = KWS[i % 12]!, b = KWS[(i + 5) % 12]!, c3 = KWS[(i + 7) % 12]!, opt = { def: defOf(look) };
      const [one] = record((c) => K.paint(c, [a], px, 2, opt)), [two] = record((c) => K.paint(c, [a, b], px, 2, opt)), [three] = record((c) => K.paint(c, [a, b, c3], px, 2, opt));
      expect(blits(one), `${look.kind}`).toHaveLength(1);
      expect(blits(two)).toHaveLength(1);
      expect(one.filter((s) => s.startsWith("roundRect("))).toEqual([]);
      expect(two.filter((s) => s.startsWith("roundRect("))).toHaveLength(2);
      expect(two).toContain(`fillStyle=${mix(KEYWORD_COLOR[a]!, "#191b22", 0.72)}`);
      expect(two).toContain(`fillStyle=${KEYWORD_COLOR[b]}`);
      expect(three).toEqual(two);
      expect(two.slice(0, one.length)).toEqual(one);
    }
  });
});

describe("T-A5 記號（點版）", () => {
  it("邊長：真 1 倍 32／42／48→7、64→11；2 倍 32→11、42→15、48→17、64→23", () => {
    expect([32, 42, 48, 64].map((px) => K.moreSize(K.sizeOf(px, 1), 1))).toEqual([7, 7, 7, 11]);
    expect([32, 42, 48, 64].map((px) => K.moreSize(K.sizeOf(px, 2), 2))).toEqual([11, 15, 17, 23]);
  });
  it("方向：手套 3 種右；卷軸匣、寬簷帽左；右下且斜放左；其餘照角（右下、左下上，左上下）", () => {
    for (const look of LOOKS) {
      const opt = { def: defOf(look) }, c = K.cornersOf(opt)[0]!, d = K.moreDirOf(c, opt), kf = `${look.kind}/${look.form}`;
      const want = ["cloth_gloves", "leather_gloves", "gauntlets"].includes(look.kind!) ? [1, 0] : kf === "tome/scroll" || kf === "hat/wide" ? [-1, 0] : c === "br" && K.isDiag(opt) ? [-1, 0] : c === "tl" ? [0, 1] : [0, -1];
      expect(d, kf).toEqual(want);
    }
    expect(LOOKS.filter((l) => K.isDiag({ def: defOf(l) })).length).toBeGreaterThan(10);
    expect(K.isDiag({ kind: "longgun", form: "flintlock" })).toBe(true);
    expect(K.isDiag({ kind: "shotgun", form: "x" })).toBe(true);
  });
  it("位置：中心離圓心 D/2 + w/2 − 2/res，左上對齊裝置像素並夾在 [snap(m), snap(px − m) − w]", () => {
    for (const look of LOOKS) for (const px of [32, 42, 48, 64]) for (const res of [1, 2]) {
      const opt = { def: defOf(look) }, c = K.cornersOf(opt)[0]!, D = K.sizeOf(px, res), [x0, y0] = K.at(c, px, D, res), b = K.moreBox(c, x0, y0, D, px, res, opt);
      const snap = (v: number) => Math.round(v * res) / res, m = (px * 3.6) / 64, [dx, dy] = K.moreDirOf(c, opt), r = D / 2 + b.w / 2 - 2 / res;
      const clamp = (v: number) => Math.min(Math.max(v, snap(m)), snap(px - m) - b.w);
      expect(b.x).toBe(clamp(snap(x0 + D / 2 + dx * r - b.w / 2)));
      expect(b.y).toBe(clamp(snap(y0 + D / 2 + dy * r - b.w / 2)));
      expect(Math.abs(b.x * res - Math.round(b.x * res))).toBeLessThan(1e-9);
      expect(b.x).toBeGreaterThanOrEqual(snap(m) - 1e-9);
      expect(b.y + b.w).toBeLessThanOrEqual(snap(px - m) + 1e-9);
    }
  });
  it("畫法：外框色圓牌 → 內縮 1 裝置像素 #191b22 → 點（原色；不認得米白）；G ≤ 4 方點（真 1 倍 3×3），否則圓", () => {
    const [o1] = record((c) => K.more(c, "br", 18, 18, 13, 32, 1, "marked"));
    expect(o1).toEqual(["save()", `fillStyle=${OUT}`, "beginPath()", "roundRect(21.000,13.000,7.000,7.000,3.500)", "fill()", "fillStyle=#191b22", "beginPath()", "roundRect(22.000,14.000,5.000,5.000,2.500)", "fill()", `fillStyle=${KEYWORD_COLOR["marked"]}`, "fillRect(23.000,15.000,3.000,3.000)", "restore()"]);
    const [o2] = record((c) => K.more(c, "br", 18, 18, 13, 32, 1, "no_such_kw"));
    expect(o2).toContain(`fillStyle=${K.MORE_CREAM}`);
    const [o3] = record((c) => K.more(c, "br", 35, 35, 27, 64, 2, "wet"));
    expect(o3.some((s) => s.startsWith("arc("))).toBe(true);
    expect(o3.some((s) => s.startsWith("fillRect("))).toBe(false);
  });
});

describe("T-A6 撞擊簡化形", () => {
  const SIMPLE = ["fillStyle=#8c8474", "roundRect(0.800,-10.400,9.600,20.800,1.600)", "fillStyle=#ece6d6", "rect(0.800,-9.400,2.000,18.800)", "fillStyle=#ffd23f", "fillStyle=#ffffff"];
  it("cpx ≤ 14（圓章 13、18）畫牆＋七角星、不呼叫 on_collision；cpx > 14 呼叫 on_collision", () => {
    const tiny = sig((c) => K.collision(c, O(true)));
    for (const s of SIMPLE) expect(tiny).toContain(s);
    expect(tiny).not.toEqual(sig((c) => QP.entry("trigger", "on_collision").d(c, O(true))));
    expect(sig((c) => K.collision(c, O(false)))).toEqual(sig((c) => QP.entry("trigger", "on_collision").d(c, O(false))));
    for (const res of [1, 2]) for (const [D, simple] of [[13, true], [18, true], [27, false]] as const) {
      const cpx = (D - 2 / res) * 0.76, calls = sig(() => K.glyph("collision", cpx, res));
      expect(cpx <= 14, `${D} r${res}`).toBe(simple);
      expect(calls.includes("roundRect(0.800,-10.400,9.600,20.800,1.600)"), `${D} r${res}`).toBe(simple);
    }
  });
});

describe("T-A7 貼圖對齊、不丟例外", () => {
  it("105 款 × 兩個關鍵字 × 32／42／48／64 × res 1、2：blit 左上 × res 是整數、只有 5 個參數的 drawImage", () => {
    for (const [i, look] of LOOKS.entries()) for (const px of [32, 42, 48, 64]) for (const res of [1, 2]) {
      const kws = [KWS[i % 12]!, KWS[(i + 3) % 12]!], [outer] = record((c) => K.paint(c, kws, px, res, { def: defOf(look) }));
      for (const s of blits(outer)) {
        const a = s.slice(10, -1).split(",");
        expect(a, s).toHaveLength(5);
        for (const v of [Number(a[1]), Number(a[2])]) expect(Math.abs(v * res - Math.round(v * res)), s).toBeLessThan(0.002);
      }
    }
  });
  it("不認得的關鍵字、空陣列、null 不丟例外、不畫；不認得的第二個只當沒有", () => {
    for (const kws of [["nope"], [], null, undefined]) { const [o, i] = record((c) => K.paint(c, kws as string[] | null, 32, 2)); expect(o).toEqual([]); expect(i).toEqual([]); }
    expect(record((c) => K.paint(c, ["ignite", "nope"], 32, 2))[0]).toEqual(record((c) => K.paint(c, ["ignite"], 32, 2))[0]);
    expect(record((c) => K.chip(c, "nope", 0, 0, 13, 1))[0]).toEqual([]);
  });
  it("chipCanvas：畫布 round(px × res)，沒有畫布時回 null", () => {
    const cv = K.chipCanvas("ignite", 13, 2);
    expect(cv?.width).toBe(26);
    setQCanvasFactory(null);
    try { expect(K.chipCanvas("ignite", 13, 2)).toBeNull(); } finally { setQCanvasFactory(fakeCanvasFactory(log)); }
  });
});

describe("T-A9 接線（QI-4b 起：gearIcon.ts 接上 keywords.ts；4a 時鎖「不接線」）", () => {
  it("gearIcon.ts 用 keywords.ts、GearIcon.tsx 只經 gearIcon.ts", () => {
    const src = readSources();
    const textOf = (f: string): string => src.find(([p]) => p.replace(/\\/g, "/").endsWith(f))?.[1] ?? "";
    expect(textOf("render/gearIcon.ts")).toMatch(/from "\.\/qIcon\/keywords"/);
    const ui = textOf("ui/GearIcon.tsx");
    expect(ui.length).toBeGreaterThan(100);
    expect(ui).not.toMatch(/qIcon\/keywords/);
  });
});
