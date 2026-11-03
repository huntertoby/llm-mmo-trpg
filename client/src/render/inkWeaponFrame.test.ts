// Phase 6M-2：武器朝向單元測試（需求 docs/art/動畫移植需求.md 第 1 節第 4 點；照樣張 anim.js 頁首的自測 selfTest）。
// 1. 每種武器在朝東、朝西出招的瞬間，作用端都在手的前方：(tip.x − hand.x) × 朝向 > 0。
// 2. 正面、背面：手到作用端的距離約等於武器長度（握在柄上）。
// 3. 統一座標：握把在原點、作用端在 (0, -len)；記下的作用端真的落在畫出來的輪廓上、握把在手上。
// 4. KNOWN_KINDS 的主手、副手武器 kind 全部有統一座標（新增 kind 沒補就失敗）。
import { describe, expect, it } from "vitest";
import { KNOWN_KINDS, type DollSpec, type GearItem } from "./appearance";
import { drawInkWeapon } from "./inkGear";
import { drawInkFigure, type InkHooks } from "./inkDoll";
import { drawInkOffhand } from "./inkOffhand";
import type { InkPose } from "./inkPose";
import { drawSectHeld } from "./inkSect";
import type { Pt, View } from "./inkStyle";
import { holdOf, weaponFrame, weaponTip, type HoldView, type WeaponPoseOpt } from "./inkWeaponFrame";
import { drawInkWeaponMore } from "./inkWeapons";
import { itemColors } from "./paperdoll";
import { resolveDollT } from "./testDolls";

type M = [number, number, number, number, number, number];

/** 追蹤變換矩陣的假畫布：記下所有路徑頂點與邊（畫布座標，剪裁中的不記）；`getTransform` 回傳目前矩陣。 */
function tracker(): { ctx: CanvasRenderingContext2D; pts: Pt[]; segs: Array<[Pt, Pt]> } {
  let m: M = [1, 0, 0, 1, 0, 0];
  const stack: M[] = [];
  const pts: Pt[] = [];
  const segs: Array<[Pt, Pt]> = [];
  let last: Pt | null = null;
  let clipAt: number | null = null; // 剪裁中的陰影斜線不算輪廓（實際畫布會被剪掉）
  const mul = (n: M): void => {
    const [a, b, c, d, e, f] = m;
    m = [a * n[0] + c * n[1], b * n[0] + d * n[1], a * n[2] + c * n[3], b * n[2] + d * n[3], a * n[4] + c * n[5] + e, b * n[4] + d * n[5] + f];
  };
  const add = (x: number, y: number, seg = true): void => {
    if (clipAt !== null) return;
    const p: Pt = [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];
    if (seg && last !== null) segs.push([last, p]);
    last = p;
    pts.push(p);
  };
  const api: Record<string, (...a: number[]) => unknown> = {
    save: () => void stack.push([...m]),
    restore: () => {
      m = stack.pop() ?? m;
      if (clipAt !== null && stack.length < clipAt) clipAt = null;
    },
    clip: () => {
      clipAt = stack.length;
    },
    translate: (x, y) => mul([1, 0, 0, 1, x, y]),
    rotate: (r) => mul([Math.cos(r), Math.sin(r), -Math.sin(r), Math.cos(r), 0, 0]),
    scale: (x, y) => mul([x, 0, 0, y, 0, 0]),
    getTransform: () => ({ a: m[0], b: m[1], c: m[2], d: m[3], e: m[4], f: m[5] }),
    beginPath: () => {
      last = null;
    },
    moveTo: (x, y) => add(x, y, false),
    lineTo: (x, y) => add(x, y),
    quadraticCurveTo: (cx, cy, x, y) => {
      // 控制點也記下（尖角被圓滑化時，尖端在控制點上）
      const keep = last;
      add(cx, cy, false);
      last = keep;
      add(x, y);
    },
    bezierCurveTo: (_a, _b, _c, _d, x, y) => add(x, y),
    arc: (x, y) => add(x, y, false),
    ellipse: (x, y) => add(x, y, false),
  };
  const props: Record<string, unknown> = {};
  const ctx = new Proxy(props, {
    get(target, prop: string) {
      if (prop in api) return api[prop];
      if (prop in target) return target[prop];
      return () => undefined;
    },
    set(target, prop: string, value) {
      target[prop] = value;
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  return { ctx, pts, segs };
}

const W = (kind: string, form?: string, extra: Partial<GearItem> = {}): GearItem => ({ kind, ...(form === undefined ? {} : { form }), material: kind === "bow" || kind === "staff" ? "wood" : "steel", ...extra });

/** 每個 kind 的形制（沒列的 kind 只測預設形制）。 */
const FORMS: Readonly<Record<string, readonly string[]>> = {
  sword: ["curved", "broad", "arcane"],
  greatsword: ["zhanma", "serrated"],
  dagger: ["kris"],
  hammer: ["mace", "flail", "warhammer"],
  fist: ["knuckle", "katar", "claw"],
  spear: ["halberd", "trident"],
  staff: ["long", "totem", "scepter", "wand"],
  whip: ["chain", "bladed"],
  crossbow: ["light", "heavy", "repeater"],
  longgun: ["flintlock", "hunting", "sniper"],
  pistol: ["flintlock", "revolver", "derringer"],
  shotgun: ["blunderbuss", "double", "pump"],
  orb: ["ball", "floating"],
};
const NOT_WEAPON = new Set(["shield_round", "shield_kite", "tome"]);
const weaponKinds = (): string[] => [...new Set([...KNOWN_KINDS.main_hand, ...KNOWN_KINDS.off_hand])].filter((k) => !NOT_WEAPON.has(k)).sort();
const ALL: GearItem[] = weaponKinds().flatMap((k) => [W(k), ...(FORMS[k] ?? []).map((f) => W(k, f))]);
const label = (it: GearItem): string => [it.kind, it.form].filter((x) => x !== undefined).join("・");

/** 樣張 anim.js 的出招片段最後一格（命中瞬間）：揮砍、突刺、射擊、施法。 */
const SLASH: InkPose = { arm: 0.15, wpn: 1.85, lean: 0.18, hipN: 0.45, hipF: -0.3 };
const THRUST: InkPose = { arm: -1.0, wpn: 2.57, lean: 0.2, hipN: 0.5, hipF: -0.35 };
const RELEASE: InkPose = { arm: -1.3, wpn: 2.87, lean: 0 };
const CAST: InkPose = { arm: -1.2, wpn: 2.4, lean: 0.12 };
const HIT_POSE: Readonly<Record<string, InkPose>> = {
  spear: THRUST,
  fist: THRUST,
  bow: RELEASE,
  crossbow: RELEASE,
  pistol: RELEASE,
  shotgun: RELEASE,
  longgun: RELEASE,
  staff: CAST,
  talisman: CAST,
  puppet_cross: CAST,
};
const hitPose = (it: GearItem): InkPose => HIT_POSE[it.kind] ?? SLASH;

const BASE = resolveDollT({ team: "ally", summon: false, template: "hero_fighter", weaponId: "one_handed_sword" });
/** 法球只能拿在副手（主手給一把劍）；成對武器兩手都給。 */
const specOf = (it: GearItem, pair = false): DollSpec => {
  const off = it.kind === "orb" || pair ? it : undefined;
  return { ...BASE, gear: { ...BASE.gear, main_hand: it.kind === "orb" ? W("sword") : it, off_hand: off } };
};

interface Probe {
  slot: "main" | "off";
  hand: Pt;
  tip: Pt;
}
function probeFigure(spec: DollSpec, view: View, west: boolean, pose: InkPose | null): Probe[] {
  const { ctx } = tracker();
  const out: Probe[] = [];
  const hooks: InkHooks = { colors: itemColors, probe: (slot, hand, tip) => out.push({ slot, hand, tip }) };
  if (west) ctx.scale(-1, 1);
  drawInkFigure(ctx, spec, view, hooks, true, pose);
  return out;
}
const slotOf = (it: GearItem): "main" | "off" => (it.kind === "orb" ? "off" : "main");
const pick = (ps: Probe[], slot: "main" | "off", what = ""): Probe => {
  const p = ps.find((x) => x.slot === slot);
  if (p === undefined) throw new Error(`${what} 沒有回報 ${slot}`);
  return p;
};

/** 單獨畫一件手持物（側面、沒鏡像），回傳輪廓頂點與回報的手、作用端。 */
function drawAlone(it: GearItem, o: HoldView & WeaponPoseOpt & { mirror: boolean; far: boolean }): { pts: Pt[]; segs: Array<[Pt, Pt]>; hand: Pt; tip: Pt } {
  const { ctx, pts, segs } = tracker();
  let hand: Pt = [NaN, NaN];
  let tip: Pt = [NaN, NaN];
  const opt = { ...o, probe: (h: Pt, t: Pt) => ((hand = h), (tip = t)) };
  const drawn =
    drawSectHeld(ctx, it, "t", 0, 0, opt) ||
    drawInkOffhand(ctx, it, 0, 0, o.side, itemColors, opt) ||
    drawInkWeapon(ctx, it, "t", 0, 0, opt, itemColors) ||
    drawInkWeaponMore(ctx, it, "t", 0, 0, opt, itemColors);
  expect(drawn, label(it)).toBe(true);
  return { pts, segs, hand, tip };
}
const dist = (a: Pt, b: Pt): number => Math.hypot(a[0] - b[0], a[1] - b[1]);
/** 點到線段的距離。 */
function segDist(p: Pt, [a, b]: [Pt, Pt]): number {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const l2 = dx * dx + dy * dy;
  const t = l2 === 0 ? 0 : Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2));
  return dist(p, [a[0] + t * dx, a[1] + t * dy]);
}
/** 點離輪廓（頂點或邊）的最近距離。 */
const nearest = (p: Pt, pts: Pt[], segs: Array<[Pt, Pt]>): number => Math.min(...pts.map((q) => dist(p, q)), ...segs.map((s) => segDist(p, s)));

describe("6M-2：武器統一座標（握把在原點、作用端朝 -y）", () => {
  it("KNOWN_KINDS 的武器 kind 全部有作用端（新增 kind 要在 inkWeaponFrame.ts 補上）", () => {
    for (const k of weaponKinds()) for (const side of [true, false]) expect(weaponTip(W(k), { side }), k).toBeDefined();
    for (const k of NOT_WEAPON) expect(weaponTip(W(k), { side: true })).toBeUndefined();
  });

  it("統一座標下作用端正好在 (0, -len)；作用端落在輪廓上、握把在手上、作用端是離握把最遠的一端", () => {
    // 弓（箭的方向）與法球（球心）是點狀作用端，不比最遠距離
    const pointLike = new Set(["bow", "orb", "talisman"]);
    for (const it of ALL) {
      const f = weaponFrame(it, { side: true })!;
      const { pts, segs, hand, tip } = drawAlone(it, { mirror: false, side: true, far: false, wpn: 0 });
      const name = label(it);
      // 圖騰杖側面沿用現有畫法往前挪 2px（手在 (2,0)），其他武器的握把都在手上
      const shift = it.kind === "staff" && it.form === "totem" ? 2 : 0;
      expect(dist(hand, [shift, 0]), name).toBeLessThan(1e-9);
      if (it.kind !== "orb") {
        // 法球不旋轉（副手不吃 wpn），其他武器給 wpn ＝ 0 時作用端朝正上方
        expect(tip[0] - hand[0], name).toBeCloseTo(0, 9);
        expect(tip[1] - hand[1], name).toBeCloseTo(-f.len, 9);
      }
      const near = nearest(tip, pts, segs);
      expect(near, `${name} 作用端離輪廓 ${near.toFixed(2)}`).toBeLessThan(3);
      const grip = nearest(hand, pts, segs);
      expect(grip, `${name} 握把離輪廓 ${grip.toFixed(2)}`).toBeLessThan(3);
      if (!pointLike.has(it.kind)) {
        const far = Math.max(...pts.map((p) => dist(p, hand)));
        expect(f.len / far, `${name} 作用端 ${f.len.toFixed(1)}／最遠 ${far.toFixed(1)}`).toBeGreaterThan(0.8);
      }
    }
  });

  it("朝東、朝西出招的瞬間，作用端都在手的前方", () => {
    const rows: string[] = [];
    for (const it of ALL) {
      for (const west of [false, true]) {
        const pose = it.kind === "orb" ? CAST : hitPose(it);
        const p = pick(probeFigure(specOf(it), "side", west, pose), slotOf(it));
        const ahead = (p.tip[0] - p.hand[0]) * (west ? -1 : 1);
        if (!(ahead > 1)) rows.push(`${label(it)} ${west ? "西" : "東"} ${ahead.toFixed(2)}`);
      }
    }
    expect(rows).toEqual([]);
  });

  it("沒設姿勢、站好（REST）時，側面作用端也不朝後（槍口、刃尖不朝後）", () => {
    const rows: string[] = [];
    for (const it of ALL) {
      for (const pose of [null, {}]) {
        const p = pick(probeFigure(specOf(it), "side", false, pose), slotOf(it));
        // 傀儡線往下垂、弓的箭朝後（現有外觀，報告待決）以外，作用端都在手的前方或正上方
        if (it.kind === "puppet_cross" || it.kind === "bow") continue;
        if (p.tip[0] - p.hand[0] < -0.5) rows.push(`${label(it)} ${pose === null ? "null" : "REST"} ${(p.tip[0] - p.hand[0]).toFixed(2)}`);
      }
    }
    expect(rows).toEqual([]);
  });

  it("正面、背面：手到作用端的距離約等於武器長度", () => {
    for (const it of ALL) {
      for (const view of ["front", "back"] as const) {
        for (const pose of [null, {}]) {
          const p = pick(probeFigure(specOf(it), view, false, pose), slotOf(it), `${label(it)} ${view}`);
          const len = weaponFrame(it, { side: false, back: view === "back" })!.len;
          expect(dist(p.hand, p.tip) / len, `${label(it)} ${view}`).toBeCloseTo(1, 6);
        }
      }
    }
  });

  it("成對武器：主手出招時作用端在前；副手（遠側手）站好時也不朝後", () => {
    for (const it of [W("dagger"), W("dagger", "kris"), W("sword"), W("axe"), W("pistol", "revolver"), W("hammer", "mace"), W("whip", "chain"), W("fist", "claw")]) {
      for (const west of [false, true]) {
        const ps = probeFigure(specOf(it, true), "side", west, hitPose(it));
        const dir = west ? -1 : 1;
        expect((pick(ps, "main").tip[0] - pick(ps, "main").hand[0]) * dir, label(it)).toBeGreaterThan(1);
        const off = pick(probeFigure(specOf(it, true), "side", west, {}), "off");
        expect((off.tip[0] - off.hand[0]) * dir, `${label(it)} 副手`).toBeGreaterThan(0);
      }
    }
  });

  it("預設握法：給 wpn ＝ holdOf 時和沒給畫得一樣（側面）", () => {
    const { ctx } = tracker();
    for (const it of ALL) {
      if (it.kind === "orb") continue;
      const hold = holdOf(ctx, it, { side: true })!;
      const a = drawAlone(it, { mirror: false, side: true, far: false });
      const b = drawAlone(it, { mirror: false, side: true, far: false, wpn: hold });
      expect(b.tip[0], label(it)).toBeCloseTo(a.tip[0], 9);
      expect(b.tip[1], label(it)).toBeCloseTo(a.tip[1], 9);
    }
  });

  it("弓弦 pull：弦中點往後拉，> 0.5 時搭箭（作用端方向不變）", () => {
    const bow = W("bow");
    const a = drawAlone(bow, { mirror: false, side: true, far: false, wpn: 0 });
    const b = drawAlone(bow, { mirror: false, side: true, far: false, wpn: 0, pull: 6 });
    expect(b.tip).toEqual(a.tip);
    // 統一座標下弦在 +y：拉開後最低點往下 6；箭頭在 -11
    const maxY = (ps: Pt[]): number => Math.max(...ps.map((p) => p[1]));
    expect(maxY(b.pts) - maxY(a.pts)).toBeGreaterThan(5);
    expect(Math.min(...b.pts.map((p) => p[1]))).toBeLessThan(-10.9);
    expect(b.pts.length).toBeGreaterThan(a.pts.length);
  });
});
