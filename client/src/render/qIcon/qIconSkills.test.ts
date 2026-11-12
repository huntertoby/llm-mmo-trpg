// Phase QI-2b：Q 版技能主圖（skills.ts）、部件（parts.ts）的行為一致測試——資料一律用實際內容（skill_icons.json、glossary.json）。
// 規格 docs/phases/PhaseQI-2計畫.md 第 7 節 T-B1～T-B7。
// art：一律用 fixture 的 `art`（QI-2a 的 `SkillIcon.art`；QI-2c 刪掉暫時資料 dev/fixtures/qi2bTempArt.json，每一招與隨機 50、工坊示範都必須帶 art）。
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import glossary from "../../battle/fixtures/glossary.json";
import icons from "../fixtures/skill_icons.json";
import type { SkillIconData } from "../../api/types";
import { resolveGear } from "../gearIcon";
import { KNOWN_PARTS } from "../skillParts";
import { partsOf } from "../skillIcon";
import { outlinePx, setQCanvasFactory, type Ctx, type QOpts } from "./core";
import { clearQWeaponDefs, Q_WEAPON_KINDS, qResolve, qWeaponDef } from "./weapons";
import * as QS from "./skills";
import * as QP from "./parts";
import { NO_ART, skillLook, toQParts, type SkillArt } from "./partsAdapter";
import { fakeCanvasFactory, fakeCtx, type FakeCanvasLog } from "../../test/fakeCanvas";

type Icon = SkillIconData & { art?: SkillArt | null };
const FIX = icons as unknown as { skills: Record<string, Icon>; random: Icon[]; workshop: Record<string, Icon[] | Icon> };
const IDS = Object.keys(FIX.skills).sort();
const WORKSHOP: Icon[] = Object.values(FIX.workshop).flatMap((v) => (Array.isArray(v) ? v : [v]));
const ALL_ICONS: Icon[] = [...IDS.map((id) => FIX.skills[id] as Icon), ...FIX.random, ...WORKSHOP];
const artOf = (id: string): SkillArt => FIX.skills[id]?.art ?? NO_ART;
/** 要檢查的全部 art：402 招＋隨機 50＋工坊示範（fixture 都帶 art，T-B1 第一項先確認）。 */
const ARTS: Array<[string, SkillArt]> = [...IDS.map((id): [string, SkillArt] => [id, artOf(id)]), ...[...FIX.random, ...WORKSHOP].map((i, n): [string, SkillArt] => [`extra#${n}`, i.art ?? NO_ART])];
const lookOf = (id: string): QS.SkillLook => skillLook(FIX.skills[id] as Icon, artOf(id));
const has = (t: object, k: string | null | undefined): boolean => k != null && Object.prototype.hasOwnProperty.call(t, k);

const log: FakeCanvasLog = { calls: null };
beforeAll(() => { QS.clearQSkillDefs(); clearQWeaponDefs(); setQCanvasFactory(fakeCanvasFactory(log)); });
afterAll(() => { setQCanvasFactory(null); QS.clearQSkillDefs(); clearQWeaponDefs(); });
const OPTS: QOpts = { small: false, tiny: false, owPx: 0, badge: false, u: 1 };

describe("T-B1 後端代碼前端都畫得出來", () => {
  it("fixture 的 403 招（BAL-21b 加 skill_lava_splash）、隨機 50、工坊示範每一步都帶 art（QI-2c：不再有暫時資料可退）", () => {
    expect(IDS.length).toBe(403);
    for (const id of IDS) expect(FIX.skills[id]?.art, id).toBeTruthy();
    for (const [n, i] of [...FIX.random, ...WORKSHOP].entries()) expect(i.art, `extra#${n}`).toBeTruthy();
  });
  it("每一招的 prop／motion／act／tint／spark 都在 TS 表裡；w: 道具取得到第 1 批的那一款（不是退回）", () => {
    expect(ARTS.length).toBeGreaterThanOrEqual(402);
    for (const [id, a] of ARTS) {
      const [cls, rest = ""] = a.prop.split(":");
      if (cls === "w" && has(QS.THINGS, rest)) { /* QI-2d：中性道具 7 個（第③批紀錄 17.7）走 thing 分支、不是第 1 批武器 */
        expect(QS.def({ prop: a.prop, motion: a.motion, act: a.act }).meta.prop.thing, `${id} ${a.prop}`).toBe(true);
      } else if (cls === "w" && rest !== "kunai") {
        const [kind = "", form] = rest.split("/");
        expect(has(Q_WEAPON_KINDS, kind), `${id} ${a.prop}`).toBe(true);
        if (form !== undefined) expect(has(Q_WEAPON_KINDS[kind]?.forms ?? {}, form), `${id} ${a.prop}`).toBe(true);
        const r = qWeaponDef(qResolve(resolveGear({ kind, form: form ?? null })))?.meta.r;
        expect(r?.kind, `${id} ${a.prop}`).toBe(kind);
        if (form !== undefined) expect(r?.form, `${id} ${a.prop}`).toBe(form);
      } else if (cls === "el") expect(has(QS.ELEMENT, rest), `${id} ${a.prop}`).toBe(true);
      else if (cls === "summon") expect(has(QS.SUMMON, rest), `${id} ${a.prop}`).toBe(true);
      else if (cls === "form") expect(has(QS.FORM, rest), `${id} ${a.prop}`).toBe(true);
      else expect(a.prop === "none" || a.prop === "w:kunai", `${id} ${a.prop}`).toBe(true);
      expect(has(QS.MOTION, a.motion), `${id} motion ${a.motion}`).toBe(true);
      expect(has(QS.ACT, a.act) || a.act === "terrain", `${id} act ${a.act}`).toBe(true);
      if (a.tint != null) expect(has(QS.TINT, a.tint), `${id} tint ${a.tint}`).toBe(true);
      if (a.spark != null) expect(has(QS.TINT, a.spark), `${id} spark ${a.spark}`).toBe(true);
      // def() 認得（沒有退回 hit／aura）
      const m = QS.def(lookOf(IDS.includes(id) ? id : (IDS[0] as string))).meta;
      if (IDS.includes(id)) { expect(m.act, id).toBe(a.act === "terrain" ? "surface" : a.act); expect(m.motion, id).toBe(a.motion); }
    }
  });
});

describe("T-B2 部件代碼齊全", () => {
  it("數量照需求 1.1：骨架 16、效果 51 圖（53 碼）、表面 8、條件 17、代價 6、觸發 22（＋5 暫代）、接續 6、形狀 13、修正 21、元素 9、狀態 32、卡片 22；改造對象 13（QI-2d，第④批紀錄 13.1）", () => {
    const n = (t: object): number => Object.keys(t).length;
    expect([n(QP.SKELETON), n(QP.EFFECT), n(QP.EFFECT) + n(QP.EFFECT_ALIAS), n(QP.SURFACE), n(QP.COND), n(QP.COST), n(QP.TRIG), n(QP.TRIG_ALIAS), n(QP.LINK), n(QP.SHAPE), n(QP.CHANGE), n(QP.ELEMENT), n(QP.STATUS), n(QP.CARD), n(QP.TARGET)])
      .toEqual([16, 51, 53, 8, 17, 6, 22, 5, 6, 13, 21, 9, 32, 22, 13]);
  });
  it("名詞表的狀態、表面、觸發、條件、效果原語與 KNOWN_PARTS 都有 Q 版圖樣或明確退回", () => {
    const known = (cat: string, id: string): void => { const e = QP.entry(cat, id); expect(e.unknown, `${cat}:${id}`).toBeUndefined(); };
    for (const s of glossary.statuses) { const e = QP.entry("status", s.id); expect(e.unknown, s.id).toBeUndefined(); if (!has(QP.STATUS, s.id)) expect(e.live, s.id).toBe(true); }
    for (const s of glossary.surfaces) known("surface", s.id);
    for (const t of glossary.triggers) { known("trigger", t.id); expect(has(QP.TRIG, t.id) || has(QP.TRIG_ALIAS, t.id), t.id).toBe(true); }
    for (const c of glossary.conditions) known("condition", c.id);
    for (const e of glossary.effects) known("effect", e.id);
    for (const id of KNOWN_PARTS.effects) known("effect", id);
    for (const id of KNOWN_PARTS.surfaces) known("surface", id);
    for (const id of KNOWN_PARTS.conditions) known("condition", id);
    for (const id of KNOWN_PARTS.triggers) known("trigger", id);
    for (const id of KNOWN_PARTS.links) known("link", id);
    for (const id of KNOWN_PARTS.costs) known("cost", id);
    // 觸發的 5 個暫代：名詞表有、目前沒有招用到（需求 4.4 第 21 點）
    const used = new Set(ALL_ICONS.map((i) => i.trigger));
    for (const id of Object.keys(QP.TRIG_ALIAS)) expect(used.has(id), id).toBe(false);
  });
});

// ---- 追蹤變換的假畫布：每個 5 個參數的 drawImage 都要「不縮放、左上角在整數裝置像素」 ----
interface Blit { w: number; dw: number; x: number; y: number }
function trackingFactory(out: Blit[]): (w: number, h: number) => HTMLCanvasElement {
  return (w, h) => {
    const cv: Record<string, unknown> = { width: w, height: h };
    let m = [1, 0, 0, 1, 0, 0];
    const stack: number[][] = [];
    const ctx: Record<string, unknown> = { canvas: cv };
    const api: Record<string, (...a: number[]) => unknown> = {
      save: () => { stack.push([...m]); },
      restore: () => { m = stack.pop() ?? [1, 0, 0, 1, 0, 0]; },
      scale: (sx, sy) => { m = [m[0]! * sx, m[1]! * sx, m[2]! * sy, m[3]! * sy, m[4]!, m[5]!]; },
      translate: (tx, ty) => { m = [m[0]!, m[1]!, m[2]!, m[3]!, m[4]! + m[0]! * tx + m[2]! * ty, m[5]! + m[1]! * tx + m[3]! * ty]; },
      setTransform: (a, b, c, d, e, f) => { m = [a, b, c, d, e, f]; },
      rotate: (r) => { const [a, b, c, d] = m as [number, number, number, number]; const cs = Math.cos(r), sn = Math.sin(r); m = [a * cs + c * sn, b * cs + d * sn, c * cs - a * sn, d * cs - b * sn, m[4]!, m[5]!]; },
      getTransform: () => ({ a: m[0], b: m[1], c: m[2], d: m[3], e: m[4], f: m[5] }),
      getImageData: () => ({ data: new Uint8ClampedArray(0) }),
      createRadialGradient: () => ({ addColorStop: () => undefined }),
      createLinearGradient: () => ({ addColorStop: () => undefined }),
    };
    const proxy = new Proxy(ctx, {
      get(t, p: string) {
        if (p in t) return t[p];
        if (p === "drawImage") return (img: { width: number }, ...a: number[]) => { if (a.length === 4 && Math.abs(m[1]!) < 1e-9) out.push({ w: img.width, dw: a[2]! * m[0]!, x: m[4]! + a[0]! * m[0]!, y: m[5]! + a[1]! * m[3]! }); };
        return api[p] ?? (() => undefined);
      },
      set(t, p: string, v: unknown) { t[p] = v; return true; },
    });
    cv.getContext = () => proxy;
    return cv as unknown as HTMLCanvasElement;
  };
}
const isInt = (v: number): boolean => Math.abs(v - Math.round(v)) < 1e-6;

describe("T-B3 貼圖對齊整數裝置像素", () => {
  const out: Blit[] = [];
  beforeAll(() => { QS.clearQSkillDefs(); clearQWeaponDefs(); setQCanvasFactory(trackingFactory(out)); });
  afterAll(() => { QS.clearQSkillDefs(); clearQWeaponDefs(); setQCanvasFactory(fakeCanvasFactory(log)); });
  const ok = (label: string): void => {
    expect(out.length, label).toBeGreaterThan(0);
    for (const b of out) { expect(b.dw, `${label} 縮放`).toBeCloseTo(b.w, 6); expect(isInt(b.x) && isInt(b.y), `${label} @${b.x},${b.y}`).toBe(true); }
    out.length = 0;
  };
  const sample = ["skill_shadow_backstab", "skill_fire_bolt", "skill_form_bear", "skill_twin_fang", "skill_spark_chain"];
  it("主圖 24、28、40 × 五種框形 × res 1、2；組裝 48、56（mid）、96（full）", () => {
    for (const kind of ["active", "reaction", "passive", "stance", "modifier"]) for (const id of sample) for (const res of [1, 2]) {
      for (const px of [24, 28, 40]) { const c = trackingFactory(out)(Math.round(px * res), Math.round(px * res)), x = c.getContext("2d") as Ctx; x.scale(res, res); QS.paint(x, { ...lookOf(id), kind }, px, res); ok(`${id} ${kind} ${px} r${res}`); }
      const icon = FIX.skills[id] as Icon;
      for (const [px, level] of [[48, "mid"], [56, "mid"], [96, "full"]] as const) { const c = trackingFactory(out)(Math.round(px * res), Math.round(px * res)), x = c.getContext("2d") as Ctx; x.scale(res, res); QP.paintIcon(x, toQParts(icon, partsOf(icon)), { ...lookOf(id), kind }, px, res, { level }); ok(`${id} ${kind} ${level}${px} r${res}`); }
    }
  });
  it("圓片 18、20、22、26、30；卡片小圖 13、16、18", () => {
    for (const res of [1, 2]) {
      for (const px of [18, 20, 22, 26, 30]) for (const [cat, id] of [["skeleton", "strike"], ["effect", "push"], ["status", "burning"], ["condition", "target_hp_below"], ["shape", "cone"], ["change", "cooldown_delta"], ["element", "fire"], ["trigger", "on_hit"]] as const) { QP.chipCanvas(cat, id, px, 1, { res }); ok(`${cat}:${id} ${px} r${res}`); }
      for (const px of [13, 16, 18]) for (const id of Object.keys(QP.CARD)) { QP.cardCanvas(id, px, 1, { res }); ok(`card:${id} ${px} r${res}`); }
    }
  });
});

describe("T-B4 外框規則", () => {
  /** 包外框時 dilate 第一筆位移 ＝ 外框裝置像素；沒有外框時沒有「位移不是 0」的 3 個參數 drawImage（halo 的原圖貼回是 (0,0)）。 */
  const firstDilate = (calls: string[]): number | null => { const c = calls.find((s) => /^drawImage\(canvas\(\d+x\d+\),-?[\d.]+,-?[\d.]+\)$/.test(s) && Number(s.split(",")[1]) !== 0); return c === undefined ? null : Number(c.split(",")[1]); };
  it("主圖的外框用整個圖示邊長算 outlinePx(size)", () => {
    for (const size of [24, 28, 40, 56]) for (const res of [1, 2]) {
      QS.clearQSkillDefs(); log.calls = [];
      QS.paint(fakeCtx(log), lookOf("skill_fire_bolt"), size, res);
      expect(firstDilate(log.calls), `${size} r${res}`).toBeCloseTo(outlinePx(size) * res, 3);
    }
    log.calls = null;
  });
  it("圓片、徽章、卡片小圖：圖樣 ≤14px 不包外框，其餘 outlinePx(圖樣px)", () => {
    for (const cpx of [10, 12, 14, 15, 18, 24]) { log.calls = []; QP.glyph("effect", "push", cpx, 2); const d = firstDilate(log.calls); if (cpx <= 14) expect(d, String(cpx)).toBeNull(); else expect(d, String(cpx)).toBeCloseTo(outlinePx(cpx) * 2, 3); }
    log.calls = [];
    QP.cardCanvas("ap", 16, 1, { res: 2 }); // 卡片圖樣 min(14, 16×0.84) ＝ 13.44 → 不包外框
    expect(firstDilate(log.calls)).toBeNull();
    log.calls = null;
  });
  it("def(cat, id, 圖樣px) 的 small／tiny 依圖樣 px（18px 組裝列圓片：半徑 42 單位 → 圖樣 18×0.42×1.56＝11.79px → tiny）", () => {
    const seen: QOpts[] = [];
    const e = QP.entry("effect", "push"), orig = e.d;
    e.d = (c, o, T, opt) => { seen.push(o); orig(c, o, T, opt); };
    try {
      for (const cpx of [18 * 0.42 * 1.56, 14, 15, 24, 25]) QP.def("effect", "push", cpx).d(fakeCtx({ calls: null }), OPTS);
    } finally { e.d = orig; }
    expect(seen.map((o) => [o.small, o.tiny])).toEqual([[true, true], [true, true], [true, false], [true, false], [false, false]]);
  });
});

describe("T-B5 修正內容的箭頭照數值正負（signArrow）", () => {
  /** 箭頭畫在 halo 另建的畫布上，所以記全域假畫布的呼叫。 */
  const down = (key: string, value: unknown): boolean => { log.calls = []; QP.def("change", key, 20, { value: value as QP.PartOpt["value"] }).d(fakeCtx(log), OPTS); const hit = log.calls.includes("scale(1.000,-1.000)"); log.calls = null; return hit; };
  /** 樣張用 `up(…)`（右上箭頭照正負）的 10 個鍵（QI-2d 加 form_upkeep_permille，第④批紀錄 13.1 E）；其餘鍵右上是固定的小圖（沙漏、紅心…），不隨數值翻。
   *  召喚物上限 summon_limit_delta 不是箭頭，是照正負換加號／減號（T-D5 另測）。 */
  const SIGNED = ["damage_permille", "hit_bonus", "cooldown_delta", "area_delta", "push_distance_delta", "ap_delta", "range_delta", "heal_permille", "form_upkeep_permille", "form_entry_permille"];
  it("哪些鍵有正負箭頭（樣張 CHANGE 用 up() 的鍵）", () => {
    expect(Object.keys(QP.CHANGE).filter((k) => down(k, -1))).toEqual(SIGNED);
  });
  it("實際修正技的 changes：有箭頭的鍵負數朝下（青色）、其餘朝上（橘黃）；沒有箭頭的鍵不翻", () => {
    let n = 0;
    for (const id of IDS) for (const ch of FIX.skills[id]?.modifier?.changes ?? []) {
      n += 1;
      expect(down(ch.key, ch.value), `${id} ${ch.key}=${String(ch.value)}`).toBe(SIGNED.includes(ch.key) && typeof ch.value === "number" && ch.value < 0);
    }
    expect(n).toBeGreaterThan(10);
  });
  it("點名：冷卻 −1、AP −1 朝下；傷害 +150‰、命中 +1、範圍 +1、推距 +1、沒有數值 朝上", () => {
    expect([down("cooldown_delta", -1), down("ap_delta", -1)]).toEqual([true, true]);
    expect([down("damage_permille", 150), down("hit_bonus", 1), down("area_delta", 1), down("push_distance_delta", 1), down("area_delta", undefined)]).toEqual([false, false, false, false, false]);
  });
});

describe("T-B6 paintIcon 三級（partsOf 轉出的部件）", () => {
  const arcs = (id: string, level: string): string[] => {
    const icon = FIX.skills[id] as Icon, l: FakeCanvasLog = { calls: [] };
    QP.paintIcon(fakeCtx(l), toQParts(icon, partsOf(icon)), lookOf(id), level === "full" ? 96 : 56, 2, { level });
    return (l.calls ?? []).filter((s) => (s.startsWith("arc(") && !s.startsWith("arc(50.000,5")) || s.startsWith("strokeStyle=#7fd8ff")); /* 框（圓框）與元素底的圓不算 */
  };
  const at = (x: number, y: number, r: number): string => `arc(${x.toFixed(3)},${y.toFixed(3)},${r.toFixed(3)},0.000,6.283)`;
  const passive = IDS.find((id) => FIX.skills[id]?.kind === "passive" && FIX.skills[id]?.trigger) as string;
  const reaction = IDS.find((id) => FIX.skills[id]?.kind === "reaction" && FIX.skills[id]?.trigger) as string;
  const linked = IDS.find((id) => FIX.skills[id]?.link && (FIX.skills[id]?.segments.length ?? 0) > 1) as string;
  it("main 只有主圖與框（沒有任何圓片）", () => {
    for (const id of [passive, reaction, linked, "skill_fire_bolt"]) { const a = arcs(id, "main"); expect(a.filter((s) => s !== at(50, 51, 36)), id).toEqual([]); }
  });
  it("mid：右下徽章 (83,83) r15；被動／反應左上觸發 (17,17) r15；沒有其他圓片", () => {
    for (const id of [passive, reaction]) expect(arcs(id, "mid").filter((s) => s !== at(50, 51, 36)), id).toEqual([at(17, 17, 15), at(83, 83, 15)]);
    expect(arcs("skill_fire_bolt", "mid").filter((s) => s !== at(50, 51, 36))).toEqual([at(83, 83, 15)]);
  });
  it("full：觸發 (15,15) r12.5、元素片讓到 (12,39) r8；接續青環在效果列；徽章 (86,86) r11", () => {
    const p = arcs(passive, "full");
    expect(p).toContain(at(15, 15, 12.5));
    if ((FIX.skills[passive]?.elements[0] ?? "physical") !== "physical") expect(p).toContain(at(12, 39, 8));
    expect(p).toContain(at(86, 86, 11));
    expect(arcs(linked, "full")).toContain("strokeStyle=#7fd8ff");
  });
  it("瞬步背刺、狂野之刃、燧石飛刃（物理）沒有元素片；有元素沒觸發的元素片在 (15,15) r11", () => {
    for (const id of ["skill_shadow_backstab", "skill_wild_blade", "skill_oil_spark_throw"]) { const a = arcs(id, "full"); expect(a, id).not.toContain(at(15, 15, 11)); expect(a, id).not.toContain(at(12, 39, 8)); }
    expect(arcs("skill_fire_bolt", "full")).toContain(at(15, 15, 11));
  });
});

describe("T-B7 確定性與不丟例外", () => {
  it("全部招 × 24、40 × res 1、2：畫兩次（先暖快取）呼叫紀錄相同", () => {
    for (const id of IDS) for (const px of [24, 40]) for (const res of [1, 2]) {
      const draw = (): string => { const l: FakeCanvasLog = { calls: [] }; log.calls = l.calls; QS.paint(fakeCtx(l), lookOf(id), px, res); log.calls = null; return (l.calls ?? []).join(";"); };
      draw();
      expect(draw(), `${id} ${px} r${res}`).toBe(draw());
    }
  });
  it("全部部件 × 18、30 畫兩次相同", () => {
    for (const [cat, list] of Object.entries(QP.list())) for (const e of list) for (const px of [18, 30]) {
      const draw = (): string => { const l: FakeCanvasLog = { calls: [] }; log.calls = l.calls; if (cat === "card") QP.cardCanvas(e.id, px, 1, { res: 2 }); else QP.chipCanvas(cat, e.id, px, 1, { res: 2 }); log.calls = null; return (l.calls ?? []).join(";"); };
      draw();
      expect(draw(), `${cat}:${e.id} ${px}`).toBe(draw());
    }
  });
  it("不認得的代碼、缺欄位不丟例外", () => {
    const bad: QS.SkillLook[] = [{}, { prop: "w:banana", motion: "x", act: "y", tint: "z", el: "q", el2: "r", spark: "s", kind: "k", rarity: "u" }, { prop: "summon:nope" }, { prop: "form:nope" }, { prop: "el:nope" }, { prop: "zzz" }, { prop: "w:" }, { act: "terrain" }];
    for (const look of bad) expect(() => QS.paint(fakeCtx({ calls: null }), look, 40, 2), JSON.stringify(look)).not.toThrow();
    expect(QS.def({ prop: "w:banana" }).meta.prop.kind).toBe("banana");
    expect(QS.def({ prop: "summon:nope" }).meta.prop.zh).toBe(QS.SUMMON.spirit.zh);
    expect(QS.def({ prop: "form:nope" }).meta.prop.zh).toBe(QS.FORM.bear.zh);
    expect(QS.def({ prop: "el:nope" }).meta.prop.zh).toBe(QS.ELEMENT.arcane.zh);
    for (const [cat, id] of [["effect", "zzz"], ["status", "zzz"], ["trigger", "zzz"], ["condition", "target_has_status:zzz"], ["shape", "zzz"], ["card", "zzz"], ["nope", "zzz"]] as const) expect(() => QP.chipCanvas(cat, id, 18, 1, { res: 2 })).not.toThrow();
    for (const icon of ALL_ICONS) expect(() => QP.paintIcon(fakeCtx({ calls: null }), toQParts(icon, partsOf(icon)), skillLook(icon, icon.art), 96, 2, { level: "full" })).not.toThrow();
  });
});
