// QK-5：正面、背面五類出招（qAnimFB）——關鍵幀照樣張、插值連續、作用端在畫布內、手在握把上、確定性、接到技能時間軸。
import { describe, expect, it } from "vitest";
import type { BattleView, Pos } from "../api/types";
import { skillTimeline } from "../battle/skillSequence";
import { vfxFor } from "../battle/vfx";
import { FB_CLIPS, FB_KINDS, fbFrameAt, fbHands, fbKindFor, fbKindIndex, fbTimeOf, fbTip, type FbView } from "./qAnimFB";
import type { P2, QPose, QUnit } from "./qCore";
import { drawQ } from "./qDoll";
import { SAMPLE_HOOKS, sampleUnit } from "./qSample";

const VIEWS: readonly FbView[] = ["front", "back"];
const UNIT: Record<string, QUnit> = {
  sword: sampleUnit("sword"),
  spear: sampleUnit("spear"),
  bow: sampleUnit("bow"),
  staff: { ...sampleUnit("staff"), gear: { ...sampleUnit("staff").gear, main_hand: { kind: "staff", element: "fire" } } },
  gauntlet: sampleUnit("gauntlet"),
};

function record(u: QUnit, view: FbView, pose: QPose): { calls: string; probes: Array<{ kind: string; hand: P2; tip: P2 }> } {
  const calls: string[] = [];
  const probes: Array<{ kind: string; hand: P2; tip: P2 }> = [];
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(t, p: string) {
      if (p in t) return t[p];
      if (p === "getTransform") return () => ({ a: 1, b: 0, c: 0, d: 1, e: 0, f: 0 });
      return (...a: unknown[]) => void calls.push(`${p}(${a.map((x) => (typeof x === "number" ? x.toFixed(4) : String(x))).join(",")})`);
    },
    set(t, p: string, v) {
      t[p] = v;
      calls.push(`${p}=${String(v)}`);
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  drawQ(ctx, u, view, SAMPLE_HOOKS, { ...pose, probe: (kind, hand, tip) => void probes.push({ kind, hand, tip }) });
  return { calls: calls.join("\n"), probes };
}

describe("QK-5 正面、背面五類出招", () => {
  it("五類 × 正背各 7 個關鍵幀；背面前傾起手到命中 0.05～0.12、預備與回位 0", () => {
    for (const k of FB_KINDS)
      for (const v of VIEWS) {
        expect(FB_CLIPS[k][v]).toHaveLength(7);
        const lean = FB_CLIPS[k][v].map((f) => f.lean ?? 0);
        if (v === "front") expect(lean.every((x) => x === 0)).toBe(true);
        else {
          expect(lean[0]).toBe(0);
          expect(lean[6]).toBe(0);
          expect(lean[4]).toBeGreaterThanOrEqual(0.08);
          expect(Math.max(...lean)).toBeLessThanOrEqual(0.12);
        }
      }
  });

  it("插值：整數時間＝關鍵幀，中間的手連續（相鄰取樣的手移動 ≤ 兩幀差）", () => {
    for (const k of FB_KINDS)
      for (const v of VIEWS) {
        for (let i = 0; i < 7; i++) expect(fbFrameAt(k, v, i)).toBe(FB_CLIPS[k][v][i]);
        for (let i = 0; i < 6; i++) {
          const a = fbHands(FB_CLIPS[k][v][i]!, v).m.hand;
          const b = fbHands(FB_CLIPS[k][v][i + 1]!, v).m.hand;
          const span = Math.hypot(b[0] - a[0], b[1] - a[1]);
          let prev = a;
          for (let s = 1; s <= 8; s++) {
            const h = fbHands(fbFrameAt(k, v, i + s / 8), v).m.hand;
            expect(Number.isFinite(h[0]) && Number.isFinite(h[1])).toBe(true);
            expect(Math.hypot(h[0] - prev[0], h[1] - prev[1])).toBeLessThanOrEqual(span + 3);
            prev = h;
          }
        }
      }
  });

  it("每 0.25 幀：作用端在畫布內（Q_BOX：x ±64、y −98～+14），主手武器有畫", () => {
    for (const k of FB_KINDS)
      for (const v of VIEWS)
        for (let u = 0; u <= 6; u += 0.25) {
          const fr = fbFrameAt(k, v, u);
          const tip = fbTip(k, v, fr, UNIT[k]!.gear.main_hand);
          expect(Math.abs(tip[0]), `${k} ${v} ${u}`).toBeLessThanOrEqual(64);
          expect(tip[1], `${k} ${v} ${u}`).toBeGreaterThanOrEqual(-98);
          expect(tip[1], `${k} ${v} ${u}`).toBeLessThanOrEqual(14);
          const { probes } = record(UNIT[k]!, v, { fbk: fbKindIndex(k), fbt: u });
          // 劍、杖的武器有畫出來（握把在主手的位置另由並排圖逐格對；這裡的假畫布沒有變換矩陣）
          if ((k === "sword" || k === "staff") && fr.ops.some((o) => o.t === "w")) expect(probes.some((q) => q.kind === k), `${k} ${v} ${u}`).toBe(true);
          if (k === "bow") expect(probes.some((q) => q.kind === "bow")).toBe(true);
        }
  });

  it("確定性：同一格畫兩次指令流相同；正面背面不是鏡像（指令流不同）", () => {
    for (const k of FB_KINDS) {
      const a = record(UNIT[k]!, "front", { fbk: fbKindIndex(k), fbt: 3.5 }).calls;
      expect(record(UNIT[k]!, "front", { fbk: fbKindIndex(k), fbt: 3.5 }).calls).toBe(a);
      expect(record(UNIT[k]!, "back", { fbk: fbKindIndex(k), fbt: 3.5 }).calls).not.toBe(a);
    }
  });

  it("沒給 fbk 時畫法不變（側面也不吃）", () => {
    const u = UNIT["sword"]!;
    expect(record(u, "front", {}).calls).toBe(record(u, "front", { fbt: 3 }).calls);
  });

  it("武器種類 × 施放方式 → 類別；片段時間 → 關鍵幀時間（命中＝4）", () => {
    expect(fbKindFor("blade", "melee")).toBe("sword");
    expect(fbKindFor("arcane", "melee")).toBe("sword");
    expect(fbKindFor("spear", "melee")).toBe("spear");
    expect(fbKindFor("bare", "melee")).toBe("gauntlet");
    expect(fbKindFor("fist", "melee")).toBe("gauntlet");
    expect(fbKindFor("bow", "ranged")).toBe("bow");
    expect(fbKindFor("staff", "ranged")).toBe("staff");
    expect(fbKindFor("pair", "melee")).toBeNull();
    expect(fbKindFor("blade", "self")).toBeNull();
    expect(fbTimeOf({ kind: "sword", part: "windup" }, 0)).toBe(0);
    expect(fbTimeOf({ kind: "sword", part: "windup" }, 1)).toBe(2);
    expect(fbTimeOf({ kind: "sword", part: "strike", hitAt: 0.625 }, 0.625)).toBe(4);
    expect(fbTimeOf({ kind: "sword", part: "strike", hitAt: 0.625 }, 1)).toBe(6);
    expect(fbTimeOf({ kind: "sword", part: "recover" }, 0.2)).toBe(6);
    expect(fbTimeOf({ kind: "sword", part: "recover" }, 0.9)).toBeNull();
  });

  it("技能時間軸：近戰劍普攻的蓄力、出招、收勢帶 fb；遠程劍不帶", () => {
    const at = (x: number, y: number): Pos => ({ x, y });
    const v = { units: [{ id: "h", pos: at(2, 2), team: "ally" }, { id: "f", pos: at(2, 3), team: "enemy" }], tiles: [] } as unknown as BattleView;
    const ev = [
      { seq: 1, round: 1, type: "attack_rolled", attacker_id: "h", target_id: "f", hit: true },
      { seq: 2, round: 1, type: "damage_dealt", target_id: "f", source_id: "h", element: "physical", amount: 5 },
    ];
    const tl = skillTimeline(ev, v, {}, vfxFor(ev, v, {}), () => "blade", () => null)!;
    expect(tl.rows.map((r) => r.fb?.part)).toEqual(["windup", "strike", "recover"]);
    expect(tl.rows.every((r) => r.fb?.kind === "sword")).toBe(true);
    const bow = skillTimeline(ev, v, {}, vfxFor(ev, v, {}), () => "bow", () => null)!;
    expect(bow.rows.every((r) => r.fb === undefined)).toBe(true); // 弓的近身（用弓身敲）照舊
  });
});
