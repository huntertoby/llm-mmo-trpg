// QK-1：樣張 qDoll.js 的 selfTest() 移植（docs/art/QK移植需求.md 第 0.4 節的 8 條），用樣張的人物與顏色（qSample.ts）。
// 像素類用 src/test/vecRaster.ts 的向量點取樣（沒有反鋸齒），放大倍數同樣張（4 倍、原點 (128,220)）。
import { describe, expect, it } from "vitest";
import { hex, vecCanvas } from "../test/vecRaster";
import { ARM_SPREAD_SET, ARMS, S, type M6, type P2, type QPose, type QUnit, type QView } from "./qCore";
import { CLASS_OF, drawQ, KEY } from "./qDoll";
import { SAMPLE_HOOKS as H, SAMPLE_ITEMS as IT, SAMPLE_TEMPLATES as TPL, SAMPLE_WEAPONS, sampleHitPose, sampleUnit } from "./qSample";
import { Q_BOX } from "./qStamp";
import { QW, qWeapon } from "./qWeapons";

interface Got {
  hand: P2;
  tip: P2;
  off: P2 | null;
  m: M6;
  wkey: string;
  hands: Record<string, P2 | boolean>;
}
/** 畫一隻（ctx 已設好變換），回報主手武器（握把、作用端、副手握點）與兩手位置。 */
function probe(u: QUnit, view: QView, west: boolean, P: QPose, ctx = vecCanvas().ctx, k = 1, o: P2 = [0, 0]): Got | null {
  let got: Got | null = null;
  const hands: Record<string, P2 | boolean> = {};
  ctx.setTransform(west ? -k : k, 0, 0, k, o[0], o[1]);
  drawQ(ctx, u, view, H, { ...P, hands, probe: (_k, h, t, _v, off, m, wkey) => (got = { hand: h, tip: t, off, m, wkey, hands }) }, west);
  return got;
}
const REST: QPose = {};
const inBody = ([x, y]: P2): boolean => (Math.abs(x) < 7.5 && y > -21 && y < 0) || Math.hypot(x, y + 29) < 8.5;
const inBox = (g: Got | null): boolean => !!g && Math.abs(g.tip[0]) < Q_BOX.W / 2 - 1 && g.tip[1] > -(Q_BOX.H - Q_BOX.FOOT) + 1 && g.tip[1] < Q_BOX.FOOT - 1;
const QATK = ["greatsword", "spear", "scythe", "gun", "crossbow"];
/** 出招命中格：雙手武器用 Q 版專用關鍵姿勢（atk 1），弓拉滿放箭，其他照 6M 片段命中格。 */
const atkPose = (kind: string): QPose => (kind === "bow" ? sampleHitPose(kind) : QATK.includes(kind) ? { atk: 1, lean: 0.12, hipN: 0.4, hipF: -0.3 } : sampleHitPose(kind));

describe("QK-1 selfTest：13 種武器 × 4 方向", () => {
  it("靜止時作用端不朝後、出招時作用端在手的前方；作用端在畫布內；正面、背面看得到作用端（弩背面被擋）", () => {
    const bad: string[] = [];
    for (const kind of SAMPLE_WEAPONS) {
      for (const west of [false, true]) {
        const s = west ? -1 : 1;
        const g = probe(sampleUnit(kind), "side", west, sampleHitPose(kind));
        const g0 = probe(sampleUnit(kind), "side", west, REST);
        const hit = g && inBox(g) ? (g.tip[0] - g.hand[0]) * s : NaN;
        const rest = g0 && inBox(g0) ? (g0.tip[0] - g0.hand[0]) * s : NaN;
        if (!(hit > 1.5)) bad.push(`${kind} ${west ? "西" : "東"}出招 ${hit.toFixed(2)}`);
        if (!(rest >= -0.5)) bad.push(`${kind} ${west ? "西" : "東"}靜止 ${rest.toFixed(2)}`);
      }
      for (const view of ["front", "back"] as const) {
        const g = probe(sampleUnit(kind), view, false, REST);
        const hid = g ? (kind === "bow" ? false : inBody(g.tip)) : false;
        const ok = g && inBox(g) ? (view === "back" && kind === "crossbow" ? hid : !hid) : false;
        if (!ok) bad.push(`${kind} ${view}`);
      }
    }
    expect(bad).toEqual([]);
  });

  it("Q 版出招關鍵姿勢（雙手劈、長柄刺、弩槍瞄準、弓拉到臉頰）：作用端在手的前方", () => {
    const bad: string[] = [];
    for (const kind of [...QATK, "bow"])
      for (const west of [false, true]) {
        const g = probe(sampleUnit(kind), "side", west, atkPose(kind));
        const d = g ? (g.tip[0] - g.hand[0]) * (west ? -1 : 1) : NaN;
        if (!(d > 1.5) || !inBox(g)) bad.push(`${kind} ${west ? "西" : "東"} ${d.toFixed(2)}`);
      }
    expect(bad).toEqual([]);
  });
});

describe("QK-1 selfTest：雙手武器、手與握把", () => {
  const near = (a: P2 | boolean | undefined, b: P2 | null): boolean => Array.isArray(a) && !!b && Math.hypot(a[0] - b[0], a[1] - b[1]) < 0.6;
  it("雙手武器：正面、背面（與側面靜止）兩隻手都在握把上（主手在原點、副手在副手握點，誤差 < 0.6）", () => {
    const kinds = [...SAMPLE_WEAPONS.filter((k) => CLASS_OF[k] && (KEY()[CLASS_OF[k]!]!.front.og || KEY()[CLASS_OF[k]!]!.front.wh === "off")), "greatsword"];
    const bad: string[] = [];
    for (const kind of kinds) {
      const kk = KEY()[CLASS_OF[kind]!]!;
      for (const [dir, view] of [["south", "front"], ["north", "back"], ["east", "side"]] as const) {
        const g = probe(sampleUnit(kind), view, false, REST);
        const needOff = kind === "bow" || (dir === "north" ? !!kk.back.og : dir === "south" ? !!kk.front.og : true);
        const hold = kind === "bow" ? "off" : "main";
        const sec = hold === "main" ? "off" : "main";
        const ok = !!g && near(g.hands[hold], g.hand) && (!needOff || near(g.hands[sec], g.off));
        if (!ok) bad.push(`${kind} ${dir}`);
      }
    }
    expect(bad).toEqual([]);
  });

  /** 武器單獨畫一次（同一個變換），手心 ±1 單位內要有武器的像素（樣張 gripTest）。 */
  it("手在握把上（像素）：13 種武器＋雙手劍 × 正面、背面、側面", () => {
    const bad: string[] = [];
    const K = 4;
    for (const kind of [...SAMPLE_WEAPONS, "greatsword"]) {
      for (const view of ["front", "back", "side"] as const) {
        const g = probe(sampleUnit(kind), view, false, REST, vecCanvas().ctx, K, [160, 240]);
        if (!g) {
          bad.push(`${kind} ${view} 沒畫`);
          continue;
        }
        const { ctx, at } = vecCanvas();
        ctx.setTransform(g.m.a, g.m.b, g.m.c, g.m.d, g.m.e, g.m.f);
        S.hooks = H;
        QW[g.wkey]!.draw(ctx, qWeapon({ kind })!.item);
        S.hooks = null;
        const touches = (h: P2 | boolean | undefined): boolean =>
          Array.isArray(h) && [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1], [0.7, 0.7], [-0.7, 0.7], [0.7, -0.7], [-0.7, -0.7]].some(([dx, dy]) => at(h[0] + dx! * K, h[1] + dy! * K)[3] > 0);
        const kc = CLASS_OF[kind];
        const kv = kc ? KEY()[kc]![view === "back" ? "back" : view === "side" ? "side" : "front"] : undefined;
        const wOff = kv?.wh === "off" || (kc === "bow" && view === "side");
        const twoKey = kc && KEY()[kc]![view === "back" ? "back" : "front"].og;
        const okM = touches(wOff ? g.hands["off"] : g.hands["main"]);
        const twoHere = twoKey && g.hands["off"] && g.hands["main"] && (view !== "side" || g.hands["offTwo"]);
        const okO = twoHere ? touches(wOff ? g.hands["main"] : g.hands["off"]) : true;
        if (!okM || !okO) bad.push(`${kind} ${view}${okM ? "" : " 主手沒握到"}${okO ? "" : " 副手沒握到"}`);
      }
    }
    expect(bad).toEqual([]);
  });

  it("刃不被手臂蓋住（像素，正面）：雙手劍、長槍、鐮的刃被蓋 ≤ 3%", () => {
    const EDGE: Record<string, number> = { greatsword: -3, spear: -34, scythe: -23 };
    const out: string[] = [];
    for (const kind of ["greatsword", "spear", "scythe"]) {
      const full = vecCanvas();
      const g = probe(sampleUnit(kind), "front", false, REST, full.ctx, 4, [160, 240])!;
      const blade = vecCanvas();
      blade.ctx.setTransform(g.m.a, g.m.b, g.m.c, g.m.d, g.m.e, g.m.f);
      blade.ctx.beginPath();
      blade.ctx.rect(-30, -60, 60, 60 + EDGE[kind]!);
      blade.ctx.clip();
      S.hooks = H;
      QW[g.wkey]!.draw(blade.ctx, qWeapon({ kind })!.item);
      S.hooks = null;
      let n = 0;
      let cov = 0;
      for (let y = 0; y < 320; y += 1)
        for (let x = 0; x < 320; x += 1) {
          const b = blade.at(x + 0.5, y + 0.5);
          if (b[3] < 0.999) continue;
          n++;
          const f = full.at(x + 0.5, y + 0.5);
          if (Math.abs(b[0] - f[0]) + Math.abs(b[1] - f[1]) + Math.abs(b[2] - f[2]) > 30) cov++;
        }
      const pct = n ? (cov / n) * 100 : 100;
      if (!(n > 0 && pct <= 3)) out.push(`${kind} 刃被蓋 ${pct.toFixed(1)}%`);
    }
    expect(out).toEqual([]);
  });
});

describe("QK-1 selfTest：背面", () => {
  const K = 4;
  const O: P2 = [128, 220];
  it("背面披風在最上層（頭除外）：圖層順序＋肩甲、主手、盾和披風重疊處是披風的顏色", () => {
    const bad: string[] = [];
    for (const u of [TPL.hero_fighter, TPL.bandit_boss] as QUnit[]) {
      const { ctx, at } = vecCanvas();
      const layers: string[] = [];
      ctx.setTransform(K, 0, 0, K, O[0], O[1]);
      drawQ(ctx, u, "back", H, { layers });
      const ix = (n: string): number => layers.indexOf(n);
      const ci = ix("cloak");
      const order = ci > 0 && ["weapon", "body", "arms"].every((n) => ix(n) >= 0 && ix(n) < ci) && ix("shield") < ci && ix("head") > ci;
      if (!order) bad.push(`順序 ${layers.join(">")}`);
      const want = H.colors(u.gear.cloak!)[0].toLowerCase();
      const pts: Array<[string, P2]> = [["左肩甲", [-6, -19.5]], ["右肩甲", [6, -19.5]], ["主手", [8.2, -9.5]]];
      if (u.gear.off_hand) pts.push(["盾", [-7, -12]]);
      for (const [n, [x, y]] of pts) {
        const c = hex(at(O[0] + x * K + 0.5, O[1] + y * K + 0.5));
        if (c !== want) bad.push(`${n} ${c}`);
      }
    }
    expect(bad).toEqual([]);
  });

  it("背面手被身體擋住：拿在身體前方的手，手心和周圍 4 點（半徑 1.2）都不是手的顏色", () => {
    const bad: string[] = [];
    const cases: Array<[string, QUnit]> = [
      ["法師", TPL.hero_mage],
      ["劍盾", TPL.hero_fighter],
      ["弓手", { look: TPL.hero_archer.look, gear: { ...TPL.hero_archer.gear, back: { slot: "back", kind: "none" } } }],
      ["盜賊", TPL.bandit],
      ["鳶盾", TPL.bandit_shieldbearer],
      ["頭目", TPL.bandit_boss],
      ["雙手劍", sampleUnit("greatsword")],
      ["弩", sampleUnit("crossbow")],
      ["火槍", sampleUnit("gun")],
    ];
    for (const [zh, u] of cases) {
      const { ctx, at } = vecCanvas();
      const hands: Record<string, P2 | boolean> = {};
      ctx.setTransform(K, 0, 0, K, O[0], O[1]);
      drawQ(ctx, u, "back", H, { hands });
      const hc = (u.gear.hands && u.gear.hands.kind !== "bracers" ? H.colors(u.gear.hands)[0] : u.look.skin).toLowerCase();
      const kq = qWeapon(u.gear.main_hand);
      for (const who of ["main", "off"] as const) {
        const h = hands[who];
        if (!Array.isArray(h)) {
          bad.push(`${zh} ${who} 沒畫`);
          continue;
        }
        const front = who === "main" ? !!kq && !!CLASS_OF[kq.kind] && !["staff", "bow"].includes(kq.kind) && !u.gear.off_hand : !!u.gear.off_hand && !String(u.gear.off_hand.kind).startsWith("shield");
        if (!front) continue;
        const n = [[0, 0], [1.2, 0], [-1.2, 0], [0, 1.2], [0, -1.2]].filter(([dx, dy]) => hex(at(h[0] + dx! * K, h[1] + dy! * K)) === hc).length;
        if (n) bad.push(`${zh} ${who} 露出 ${n}/5`);
      }
    }
    expect(bad).toEqual([]);
  });

  it("背面副手：持盾的前臂與手看得到（≥ 4 單位²）、有披風時披風在最上層；拿書只露一點拳頭（0.2～2 單位²）", () => {
    const bad: string[] = [];
    const cases: Array<[string, QUnit]> = [
      ["劍盾（圓盾）", TPL.hero_fighter],
      ["鳶盾", TPL.bandit_shieldbearer],
      ["法師（書）", TPL.hero_mage],
      ["聖盾", { look: TPL.hero_fighter.look, gear: { ...TPL.hero_fighter.gear, off_hand: IT.holy_shield, cloak: undefined } }],
      ["塔盾", { look: TPL.bandit.look, gear: { ...TPL.bandit.gear, off_hand: { slot: "off_hand", kind: "shield_kite", form: "tower", material: "wood", color: "#6a4a2e" } } }],
      ["劍盾（無披風）", { look: TPL.hero_fighter.look, gear: { ...TPL.hero_fighter.gear, cloak: undefined } }],
    ];
    for (const [zh, u] of cases) {
      const { ctx, at } = vecCanvas();
      const hands: Record<string, P2 | boolean> = {};
      ctx.setTransform(K, 0, 0, K, O[0], O[1]);
      drawQ(ctx, u, "back", H, { tintOff: "#ff00ff", hands });
      const sh = String(u.gear.off_hand?.kind).startsWith("shield");
      const y0 = sh ? 0 : Math.round(O[1] - 16 * K);
      const hb = !sh && Array.isArray(hands["off"]) ? (hands["off"] as P2) : null;
      let n = 0;
      for (let py = y0; py < 256; py++)
        for (let px = 0; px < 256; px++) {
          if (hb && Math.hypot(px - hb[0], py - hb[1]) > 2.6 * K) continue;
          if (hex(at(px + 0.5, py + 0.5)) === "#ff00ff") n++;
        }
      const area = n / (K * K);
      if (sh && u.gear.cloak) continue;
      if (sh && area < 4) bad.push(`${zh} 前臂與手露出 ${area.toFixed(1)}`);
      if (!sh && !(area >= 0.2 && area <= 2)) bad.push(`${zh} 拳頭露出 ${area.toFixed(1)}`);
    }
    expect(bad).toEqual([]);
  });
});

describe("QK-1：正面、背面輪廓不比手臂規則 A（第 15～16 版的張開角度）寬", () => {
  /** 剪影最左、最右（單位）：0.25 單位一格掃描。 */
  function extent(u: QUnit, view: QView): [number, number] {
    const { ctx, at } = vecCanvas();
    ctx.setTransform(4, 0, 0, 4, 128, 220);
    drawQ(ctx, u, view, H, null);
    let lo = Infinity;
    let hi = -Infinity;
    for (let py = 220 - 60 * 4; py < 220 + 4 * 4; py += 2)
      for (let px = 0; px < 256; px += 1)
        if (at(px + 0.5, py + 0.5)[3] > 0) {
          lo = Math.min(lo, (px - 128) / 4);
          hi = Math.max(hi, (px - 128) / 4);
        }
    return [lo, hi];
  }
  // 空手、拳套不比：E 的空手用「最小可見縫」ea 0.09（2026-11-06 使用者定案：「ea0.09不錯」），A 的空手是直垂（0），定案本來就寬 1.5 單位
  it("12 種持武器＋雙手劍、劍盾、杖書 × 正面、背面：E 的寬度 ≤ A", () => {
    const units: Array<[string, QUnit]> = [...[...SAMPLE_WEAPONS.filter((k) => k !== "gauntlet"), "greatsword"].map((k): [string, QUnit] => [k, sampleUnit(k)]), ["劍盾", { look: TPL.hero_fighter.look, gear: { ...TPL.hero_fighter.gear, cloak: undefined } }], ["杖書", TPL.hero_mage]];
    const bad: string[] = [];
    for (const [zh, u] of units)
      for (const view of ["front", "back"] as const) {
        ARMS.cur = ARM_SPREAD_SET.A;
        const a = extent(u, view);
        ARMS.cur = ARM_SPREAD_SET.E;
        const e = extent(u, view);
        if (e[1] - e[0] > a[1] - a[0] + 0.26) bad.push(`${zh} ${view} E ${(e[1] - e[0]).toFixed(2)} > A ${(a[1] - a[0]).toFixed(2)}`);
      }
    ARMS.cur = ARM_SPREAD_SET.E;
    expect(bad).toEqual([]);
  });
});
