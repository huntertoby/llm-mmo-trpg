// Phase QI-2d：Q 版技能圖示補圖（7 個中性道具、第④批 11-12 補圖、改造對象接線）的行為一致測試。
// 規格 docs/phases/PhaseQI-2d計畫.md 第 7.2 節 T-D4～T-D8、T-D11；資料一律用實際內容（skill_icons.json）。
// 基準 fixtures/qi2dBaseline.json：開工前（main 493965a8）用同一套假畫布錄的呼叫紀錄雜湊與改造對象的文字（報告第 4 節）。
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import icons from "../fixtures/skill_icons.json";
import baseline from "../fixtures/qi2dBaseline.json";
import type { SkillIconData } from "../../api/types";
import { drawChip, modifierTargetPart } from "../skillParts";
import { partsOf } from "../skillIcon";
import { mix, setQCanvasFactory, type Ctx, type QOpts } from "./core";
import { clearQWeaponDefs } from "./weapons";
import * as QS from "./skills";
import * as QP from "./parts";
import * as QST from "./status";
import { NO_ART, skillLook, toQParts, type SkillArt } from "./partsAdapter";
import { fakeCanvasFactory, fakeCtx, type FakeCanvasLog } from "../../test/fakeCanvas";

type Icon = SkillIconData & { art?: SkillArt | null };
const FIX = icons as unknown as { skills: Record<string, Icon> };
const IDS = Object.keys(FIX.skills).sort();
const BASE = baseline as unknown as { parts: Record<string, string>; sld: Record<string, string>; main: Record<string, string>; target: Record<string, { applies_to: Record<string, unknown>; label: string; note: string; color: string; cat: string; key: string }> };
const lookOf = (id: string): QS.SkillLook => skillLook(FIX.skills[id] as Icon, FIX.skills[id]?.art ?? NO_ART);
/** 規格第 6 節的 19 招（美術清單 2.4 的資料版）與新值。 */
const NINETEEN: Readonly<Record<string, string>> = {
  skill_trample: "w:boot", skill_prone_kick: "w:boot", skill_gale_kick: "w:boot", skill_leap_slam: "w:boot", skill_prone_mark_strike: "w:boot", skill_heavy_stomp: "w:boot",
  skill_battering_ram: "w:shoulder", skill_bull_rush: "w:shoulder", skill_tiger_charge: "w:shoulder", skill_quake_topple: "w:shoulder",
  skill_oil_flask: "w:flask", skill_splash_flask: "w:flask", skill_smoke_bomb: "w:smoke_bomb", skill_gear_smoke_bomb: "w:smoke_bomb",
  skill_lingering_roar: "w:roar", skill_taunting_roar: "w:roar", skill_wild_roar: "w:roar", skill_venom_gore: "w:fang", skill_slime_glob: "w:slime",
};
/** 基準錄好之後才加的招（沒有開工前的主圖雜湊）：BAL-21b 的熔岩濺落、LW-1 的獨狼示範 3 招。再加新招要列在這裡（依 ID 排序）。 */
const ADDED_AFTER_BASELINE: readonly string[] = [
  "skill_berserker_fury_cleave", // RG-2：荒原狂戰士
  "skill_binding_talisman", // RG-1：瞄準預告的 3 招
  "skill_blood_fury", // KW-2：連擊、怒氣、專注、氣的示範招與利用者
  "skill_breathing_qi",
  "skill_centering",
  "skill_crane_piercing_shot",
  "skill_crumbling_fist",
  "skill_eagle_eye",
  "skill_flowing_cut",
  "skill_fury_slam",
  "skill_grit_teeth",
  "skill_heart_piercer",
  "skill_inch_force",
  "skill_lava_bomb",
  "skill_lava_splash",
  "skill_lone_strider",
  "skill_lone_wolf_pounce",
  "skill_mind_eye_shot",
  "skill_qigong_wave",
  "skill_rift_flicker",
  "skill_shadow_bind",
  "skill_shadow_glide",
  "skill_silent_step",
  "skill_swift_stab",
  "skill_throat_cut",
  "skill_unguarded_shot",
  "skill_war_cry",
];
/** 基準錄好之後內容改過、主圖跟著變的招（DD-3：雙牙拿掉第二段傷害、改成兩下都中才上中毒）。 */
const CONTENT_CHANGED: readonly string[] = ["skill_twin_fang"];
/** 基準錄好之後才加的部件（LW-1 兩個條件、DD-3 與 BS-1 各一個、KW-1 一個條件；沒有開工前的雜湊）。 */
const ADDED_PARTS = ["condition:lone_wolf", "condition:self_lacks_status", "condition:all_strikes_hit", "change:silent_strike", "condition:self_stack_at_least", "condition:self_on_high_ground"];
/** 本段改過的部件（其餘部件的呼叫紀錄必須和開工前相同）。 */
const CHANGED_PARTS = ["effect:redirect_damage", "change:form_upkeep_permille"];
const MODIFIERS = IDS.filter((id) => FIX.skills[id]?.modifier && !ADDED_AFTER_BASELINE.includes(id)); // 基準之後才加的修正技（BS-1 無聲步）沒有開工前的紀錄

const log: FakeCanvasLog = { calls: null };
beforeAll(() => { QS.clearQSkillDefs(); clearQWeaponDefs(); QST.clearQStatusMemo(); setQCanvasFactory(fakeCanvasFactory(log)); });
afterAll(() => { setQCanvasFactory(null); QS.clearQSkillDefs(); clearQWeaponDefs(); QST.clearQStatusMemo(); });
/** SHA-256 前 16 碼（WebCrypto；基準用同一個算法錄）。 */
const h = async (s: string): Promise<string> => [...new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s)))].map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 16);
/** 畫兩次（第一次暖快取），回傳第二次的全域呼叫紀錄（含 halo 另建的畫布）。 */
const grab = (fn: () => void): string[] => { log.calls = []; fn(); log.calls = []; fn(); const out = log.calls; log.calls = null; return out; };
const O = (tiny: boolean, owPx: number): QOpts => ({ small: true, tiny, owPx, badge: false, u: 1 });

describe("基準：沒改到的部件與主圖和開工前相同", () => {
  it("全部部件 × 18、30 × res 1、2：除了分擔傷害、形態維持消耗，呼叫紀錄雜湊＝開工前；改造對象 13 個是新的", async () => {
    const seen = new Set<string>();
    for (const [cat, T] of Object.entries(QP.CATS)) for (const id of Object.keys(T ?? {})) for (const px of [18, 30]) for (const res of [1, 2]) {
      const key = `${cat}:${id}|${px}|${res}`, now = await h(grab(() => { if (cat === "card") QP.cardCanvas(id, px, 1, { res }); else QP.chipCanvas(cat, id, px, 1, { res }); }).join("\n"));
      if (cat === "target" || ADDED_PARTS.includes(`${cat}:${id}`)) { expect(BASE.parts[key], key).toBeUndefined(); continue; }
      seen.add(key);
      if (CHANGED_PARTS.includes(`${cat}:${id}`)) expect(now, key).not.toBe(BASE.parts[key]);
      else expect(now, key).toBe(BASE.parts[key]);
    }
    expect([...seen].sort()).toEqual(Object.keys(BASE.parts).sort());
  });
  it("有基準的 402 招主圖 24、40：只有第 6 節 19 招和開工前不同；沒基準的只有之後加的新招", async () => {
    const hasBase = (id: string): boolean => BASE.main[`${id}|24`] !== undefined && BASE.main[`${id}|40`] !== undefined;
    /* 基準錄於 QI-2d 開工前；之後加的招沒有基準，另列並斷言就是預期的新招（不是整批放寬）。 */
    expect(IDS.filter((id) => !hasBase(id))).toEqual([...ADDED_AFTER_BASELINE]);
    const based = IDS.filter(hasBase);
    expect(based.length).toBe(402);
    const changed: string[] = [];
    for (const id of based) for (const px of [24, 40]) { const now = await h(grab(() => QS.canvas(lookOf(id), px, 1, { res: 2 })).join("\n")); if (now !== BASE.main[`${id}|${px}`]) changed.push(id); }
    expect([...new Set(changed)].sort()).toEqual([...Object.keys(NINETEEN), ...CONTENT_CHANGED].sort());
  });
});

describe("T-D4 分擔傷害的雙環＝狀態「靈魂連結」", () => {
  it("parts.ts 的 EFFECT.redirect_damage 與 status.ts 的 soul_link：tiny（18）與 small（30）、有無外框，呼叫紀錄逐筆相同", () => {
    const soul = QST.NEW["soul_link"] as QST.NewEntry, eff = QP.EFFECT["redirect_damage"] as QP.PartEntry;
    expect(eff.d).toBe(QP.soulRings);
    for (const o of [O(true, 0), O(true, 2), O(false, 0), O(false, 3)]) {
      const a = grab(() => eff.d(fakeCtx(log), o)), b = grab(() => soul.d(fakeCtx(log), o));
      expect(a.length, JSON.stringify(o)).toBeGreaterThan(5);
      expect(a, JSON.stringify(o)).toEqual(b);
    }
  });
});

describe("T-D5 召喚物上限、形態維持消耗照正負", () => {
  const sld = (value: QP.PartOpt["value"], px: number, res: number): string[] => grab(() => QP.chipCanvas("change", "summon_limit_delta", px, 1, { res, value }));
  /** 加號＝直槓＋橫槓（右上 (6.6,−6.4)、k 0.8）；減號只有橫槓。 */
  const VBAR = "roundRect(5.400,-9.920,2.400,7.040,0.640)", HBAR = "roundRect(3.080,-7.600,7.040,2.400,0.640)";
  const sign = (calls: string[]): string => (calls.includes(VBAR) ? "+" : "") + (calls.includes(HBAR) ? "-" : "");
  it("summon_limit_delta：+1 與沒有 value 畫加號（呼叫紀錄＝開工前）；−1 只畫橫槓（少一筆直槓）", async () => {
    for (const px of [18, 30]) for (const res of [1, 2]) {
      expect(await h(sld(1, px, res).join("\n"))).toBe(BASE.sld[`1|${px}|${res}`]);
      expect(await h(sld(undefined, px, res).join("\n"))).toBe(BASE.sld[`undefined|${px}|${res}`]);
      const neg = sld(-1, px, res), pos = sld(1, px, res);
      expect([sign(pos), sign(neg)], `${px} r${res}`).toEqual(["+-", "-"]);
      expect(neg).not.toEqual(pos);
    }
  });
  /** 箭頭畫在 halo 另建的畫布上，所以看全域紀錄。 */
  const upkeep = (value: number): string[] => grab(() => QP.def("change", "form_upkeep_permille", 20, { value }).d(fakeCtx(log), O(false, 0)));
  it("form_upkeep_permille：−500 朝下青色、+500 朝上橘黃；兩者都有右下沙漏", () => {
    const neg = upkeep(-500), pos = upkeep(500);
    expect(neg).toContain("scale(1.000,-1.000)"); expect(neg).toContain("fillStyle=#6ae0ff");
    expect(pos).not.toContain("scale(1.000,-1.000)"); expect(pos).toContain("fillStyle=#ffb23a");
    for (const c of [neg, pos]) { expect(c).toContain("translate(6.400,6.600)"); expect(c).toContain("fillStyle=#8ab8f0"); }
  });
  it("實際內容：skill_summon_elite、skill_summon_swarm、skill_form_mastery 的 changes 照數值畫", () => {
    const changes = (id: string) => FIX.skills[id]?.modifier?.changes ?? [];
    const elite = changes("skill_summon_elite").find((c) => c.key === "summon_limit_delta"), swarm = changes("skill_summon_swarm").find((c) => c.key === "summon_limit_delta"), mastery = changes("skill_form_mastery").find((c) => c.key === "form_upkeep_permille");
    expect(elite && swarm && mastery).toBeTruthy();
    for (const c of [elite, swarm]) {
      const v = c?.value as QP.PartOpt["value"];
      expect(sign(sld(v, 30, 2)), String(v)).toBe(Number(v) < 0 ? "-" : "+-");
    }
    const m = upkeep(Number(mastery?.value));
    expect(m.includes("scale(1.000,-1.000)"), String(mastery?.value)).toBe(Number(mastery?.value) < 0);
  });
});

/** 本段前 `modifierTargetPart` 的分支（照 2c 合併後的程式：all_skills → all_attacks／actions 含 attack → skill_tags 第一個 → 其他 actions → 預設）＋各分支該畫的圖。 */
function oldBranch(a: Record<string, unknown>): string {
  const actions = Array.isArray(a["actions"]) ? (a["actions"] as unknown[]) : [], tags = Array.isArray(a["skill_tags"]) ? (a["skill_tags"] as unknown[]).map(String) : [];
  if (a["all_skills"] === true) return "all_skills";
  if (a["all_attacks"] === true || actions.includes("attack")) return a["all_attacks"] === true ? "all_attacks" : "attack";
  if (tags.length > 0) return QP.TARGET_TAG[tags[0] as string] ?? "tag_other";
  if (actions.length > 0) return "actions";
  return "default";
}
describe("T-D6 targetOf 判斷順序", () => {
  const SYN: Array<[Record<string, unknown>, string]> = [
    [{ all_skills: true, all_attacks: true }, "all_skills"], [{ all_attacks: true, skill_tags: ["push"] }, "all_attacks"], [{ actions: ["move", "attack"], skill_tags: ["heal"] }, "attack"],
    [{ skill_tags: ["push", "heal"], actions: ["move"] }, "tag_push"], [{ skill_tags: ["heal"] }, "tag_heal"], [{ skill_tags: ["control"] }, "tag_control"], [{ skill_tags: ["ranged"] }, "tag_ranged"],
    [{ skill_tags: ["shout"] }, "tag_shout"], [{ skill_tags: ["area"] }, "tag_area"], [{ skill_tags: ["summon"] }, "tag_summon"], [{ skill_tags: ["mystery"] }, "tag_other"],
    [{ actions: ["move"] }, "actions"], [{}, "default"], [{ weapon_skills: true }, "default"],
  ];
  it("13 個代碼各一組合成的 applies_to（含 weapon_skills: true → default）", () => {
    expect(new Set(SYN.map(([, t]) => t))).toEqual(new Set(Object.keys(QP.TARGET)));
    for (const [a, want] of SYN) { expect(QP.targetOf(a), JSON.stringify(a)).toBe(want); expect(oldBranch(a), JSON.stringify(a)).toBe(want); }
    expect(QP.targetOf(null)).toBe("default"); expect(QP.targetOf(undefined)).toBe("default");
  });
  it("skill_icons.json 全部修正技的實際 applies_to：和本段前的分支一致；點名四招", () => {
    expect(MODIFIERS.length).toBeGreaterThan(10);
    for (const id of MODIFIERS) { const a = FIX.skills[id]?.modifier?.applies_to as Record<string, unknown>; expect(QP.targetOf(a), id).toBe(oldBranch(a)); }
    const t = (id: string): string => QP.targetOf(FIX.skills[id]?.modifier?.applies_to as Record<string, unknown>);
    expect([t("skill_heavy_stomp"), t("skill_lingering_roar"), t("skill_summon_elite"), t("skill_summon_swarm")]).toEqual(["tag_push", "tag_shout", "tag_summon", "tag_summon"]);
  });
});

describe("T-D7 改造對象接上了、文字沒動", () => {
  it("全部修正技：label、note、color、cat、key 和開工前逐字相同；有 Q 版參照 target:targetOf(…)", () => {
    expect(Object.keys(BASE.target).sort()).toEqual(MODIFIERS);
    for (const id of MODIFIERS) {
      const a = FIX.skills[id]?.modifier?.applies_to as Record<string, unknown>, p = modifierTargetPart(a), b = BASE.target[id];
      expect(a, id).toEqual(b?.applies_to);
      expect({ label: p.label, note: p.note, color: p.color, cat: p.cat, key: p.key }, id).toEqual({ label: b?.label, note: b?.note, color: b?.color, cat: b?.cat, key: b?.key });
      expect(p.q, id).toEqual({ cat: "target", id: QP.targetOf(a) });
    }
  });
  it("組裝列方塊（drawChip 給 unitPx）的呼叫紀錄＝QP.chip(\"target\", targetOf(…))（白環 #ffffff、半徑 42）", () => {
    for (const id of MODIFIERS) for (const [u, res] of [[0.3, 2], [0.18, 1], [0.18, 2]] as const) {
      const p = modifierTargetPart(FIX.skills[id]?.modifier?.applies_to as Record<string, unknown>);
      const a = grab(() => drawChip(fakeCtx(log), p, 50, 50, 42, { ring: "#ffffff", unitPx: u, res }));
      const b = grab(() => QP.chip(fakeCtx(log), "target", QP.targetOf(FIX.skills[id]?.modifier?.applies_to as Record<string, unknown>), 50, 50, 42, { ring: "#ffffff", unitPx: u, res }));
      expect(a, id).toEqual(b);
      expect(a, id).toContain("strokeStyle=#ffffff");
    }
  });
});

describe("T-D8 新道具", () => {
  const P = (prop: string, motion: string, act: string, extra: Partial<QS.SkillLook> = {}): QS.SkillDef => QS.def({ prop, motion, act, ...extra });
  it("7 個 THINGS 都在；def 走 thing 分支（不是直劍退回）", () => {
    expect(Object.keys(QS.THINGS).sort()).toEqual(["boot", "fang", "flask", "roar", "shoulder", "slime", "smoke_bomb"]);
    for (const id of Object.keys(QS.THINGS)) { const m = P(`w:${id}`, "swing", "push").meta.prop; expect(m.thing, id).toBe(true); expect(m.kind, id).toBe(id); expect(m.zh, id).toBe(QS.THINGS[id]?.zh); }
    expect(P("w:sword", "swing", "push").meta.prop.thing).toBeUndefined();
    expect(QS.list().props.filter((p) => p.group === "中性").map((p) => p.key)).toEqual(Object.keys(QS.THINGS).map((k) => `w:${k}`));
  });
  /** 射出的彗尾（非武器、非飛出道具）的終點 (1.5, 46.5)。 */
  const tail = (d: QS.SkillDef): boolean => grab(() => d.pre(fakeCtx(log), O(false, 0))).some((s) => s === "lineTo(1.500,46.500)" || s === "moveTo(1.500,46.500)");
  it("info().weapon 為 false（射出照元素道具拖彗尾）；黏液射出沒有彗尾（noTail）", () => {
    expect(tail(P("w:flask", "shot", "hit"))).toBe(true);
    expect(tail(P("el:earth", "shot", "slow"))).toBe(true);
    expect(tail(P("w:bow", "shot", "hit"))).toBe(false);
    expect(tail(P("w:slime", "shot", "slow"))).toBe(false);
    expect(tail(QS.def(lookOf("skill_slime_glob")))).toBe(false);
  });
  it("瓶配地面效果：記號換液體色（earth＝琥珀）；其他道具不換", () => {
    expect(P("w:flask", "area", "surface", { tint: "earth" }).meta.tintPair).toEqual(["#f0b030", "#fff0b0"]);
    expect(QS.def(lookOf("skill_oil_flask")).meta.tintPair).toEqual(["#f0b030", "#fff0b0"]);
    expect(P("w:boot", "area", "surface", { tint: "earth" }).meta.tintPair).toEqual(QS.TINT.earth);
  });
  it("肩撞配衝刺：dashV([dim, soft])、markK 0.72；靴配衝刺照舊米黃＋白", () => {
    const d = P("w:shoulder", "place", "dash", { el: "physical" }), EB = QS.BASE.physical, dim = mix(EB[1], EB[2], 0.22), soft = mix(EB[1], EB[2], 0.55);
    expect(d.meta.markK(O(false, 0))).toBe(0.72);
    const calls = grab(() => d.meta.drawMark(fakeCtx(log), O(false, 0)));
    expect(calls).toContain(`fillStyle=${dim}`); expect(calls).toContain(`fillStyle=${soft}`); expect(calls).not.toContain("fillStyle=#ffe9a8");
    const boot = grab(() => P("w:boot", "place", "dash", { el: "physical" }).meta.drawMark(fakeCtx(log), O(false, 0)));
    expect(boot).toContain("fillStyle=#ffe9a8");
  });
});

// ---- T-D11：追蹤變換的假畫布（同 qIconSkills.test.ts T-B3）：5 個參數的 drawImage 都要不縮放、左上角在整數裝置像素 ----
interface Blit { w: number; dw: number; x: number; y: number }
function trackingFactory(out: Blit[]): (w: number, h: number) => HTMLCanvasElement {
  return (w, hh) => {
    const cv: Record<string, unknown> = { width: w, height: hh };
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

describe("T-D11 對齊、確定性、不丟例外", () => {
  const out: Blit[] = [];
  const ok = (label: string): void => {
    expect(out.length, label).toBeGreaterThan(0);
    for (const b of out) { expect(b.dw, `${label} 縮放`).toBeCloseTo(b.w, 6); expect(isInt(b.x) && isInt(b.y), `${label} @${b.x},${b.y}`).toBe(true); }
    out.length = 0;
  };
  const PARTS: Array<[string, string, QP.PartOpt]> = [
    ...Object.keys(QP.TARGET).map((id): [string, string, QP.PartOpt] => ["target", id, {}]),
    ["effect", "redirect_damage", {}], ["change", "form_upkeep_permille", { value: -500 }], ["change", "form_upkeep_permille", { value: 500 }], ["change", "summon_limit_delta", { value: -1 }], ["change", "summon_limit_delta", { value: 1 }],
  ];
  it("19 招 × main 24／28／40、mid 48／56、full 96 × res 1、2；13 個改造對象＋4 個改過的部件 × 18／30 × res 1、2：貼圖不縮放、左上角在整數裝置像素", () => {
    QS.clearQSkillDefs(); clearQWeaponDefs(); setQCanvasFactory(trackingFactory(out));
    try {
      for (const id of Object.keys(NINETEEN)) for (const res of [1, 2]) {
        for (const px of [24, 28, 40]) { const c = trackingFactory(out)(Math.round(px * res), Math.round(px * res)), x = c.getContext("2d") as Ctx; x.scale(res, res); QS.paint(x, lookOf(id), px, res); ok(`${id} main${px} r${res}`); }
        const icon = FIX.skills[id] as Icon;
        for (const [px, level] of [[48, "mid"], [56, "mid"], [96, "full"]] as const) { const c = trackingFactory(out)(Math.round(px * res), Math.round(px * res)), x = c.getContext("2d") as Ctx; x.scale(res, res); QP.paintIcon(x, toQParts(icon, partsOf(icon)), lookOf(id), px, res, { level }); ok(`${id} ${level}${px} r${res}`); }
      }
      for (const [cat, id, opt] of PARTS) for (const px of [18, 30]) for (const res of [1, 2]) { QP.chipCanvas(cat, id, px, 1, { ...opt, res }); ok(`${cat}:${id} ${String(opt.value)} ${px} r${res}`); }
    } finally { QS.clearQSkillDefs(); clearQWeaponDefs(); setQCanvasFactory(fakeCanvasFactory(log)); }
  });
  it("畫兩次呼叫紀錄相同；不丟例外", () => {
    for (const id of Object.keys(NINETEEN)) for (const res of [1, 2]) {
      for (const px of [24, 28, 40]) { const a = grab(() => QS.canvas(lookOf(id), px, 1, { res })), b = grab(() => QS.canvas(lookOf(id), px, 1, { res })); expect(a, `${id} ${px}`).toEqual(b); expect(a.length).toBeGreaterThan(10); }
      const icon = FIX.skills[id] as Icon;
      for (const [px, level] of [[48, "mid"], [56, "mid"], [96, "full"]] as const) { const a = grab(() => QP.canvas(toQParts(icon, partsOf(icon)), lookOf(id), px, 1, { res, level })), b = grab(() => QP.canvas(toQParts(icon, partsOf(icon)), lookOf(id), px, 1, { res, level })); expect(a, `${id} ${level}${px}`).toEqual(b); }
    }
    for (const [cat, id, opt] of PARTS) for (const px of [18, 30]) for (const res of [1, 2]) { const a = grab(() => QP.chipCanvas(cat, id, px, 1, { ...opt, res })), b = grab(() => QP.chipCanvas(cat, id, px, 1, { ...opt, res })); expect(a, `${cat}:${id}`).toEqual(b); expect(a.length).toBeGreaterThan(5); }
  });
});
