// QK-4：Q 版異形動畫（docs/art/sample/qCreatureAnim.js 的移植）。
// 確定性、數值有限、攻擊與受擊回到原樣、倒下停在最後一格、循環相位由 id 決定、減少動態、作用端（非飛向目標的特效、整隻位移）在畫布內。
import { describe, expect, it } from "vitest";
import type { QPartPose } from "./creaturePose";
import { CREATURE_FOOT_Y, CREATURE_H, CREATURE_W, RIG, RIG_KEYS, creaturePalette, drawCreature, resolveCreature, rigKey } from "./inkCreature";
import { BODY_ANIM, attackClipFor, creatureClipInfo, creatureClips, creatureFrameU, qCreaturePartPose, quantizeClipU, type AnimSubject, type AttackType } from "./qCreatureAnim";

const SPEC: Readonly<Record<string, { body: string; variant?: string; material: string }>> = Object.fromEntries(
  RIG_KEYS.map((k) => [k, k === "bird" || k === "bat" ? { body: "flyer", variant: k, material: "magma" } : k === "beetle" || k === "spider" ? { body: "crawler", variant: k, material: "magma" } : { body: k, material: "magma" }]),
);
const subject = (key: string): AnimSubject => {
  const r = resolveCreature({ look: SPEC[key]! });
  const P = creaturePalette(r);
  return { key: rigKey(r), element: r.element, mat: P.mat, base: P.base, accent: P.accent };
};
const framesOf = (key: string, clip: string): number[] => {
  const info = creatureClipInfo(key, clip)!;
  return info.loop ? Array.from({ length: 8 }, (_, f) => f / 8) : Array.from({ length: info.n }, (_, f) => f / (info.n - 1));
};
function allNumbers(p: QPartPose): number[] {
  const out: number[] = [p.flash, p.alpha, p.shadow];
  for (const xf of [p.root, ...Object.values(p.parts)]) for (const [k, v] of Object.entries(xf)) out.push(...(k === "pivot" ? (v as number[]) : [v as number]));
  for (const f of p.fx) for (const v of Object.values(f)) if (typeof v === "number") out.push(v);
  return out;
}

describe("QK-4：Q 版異形動畫片段", () => {
  it("16 款身形、40 個攻擊片段（QK-4 的 35 個＋CB-3 第二種近戰 5 個）；每款都有待機、移動、受擊、倒下", () => {
    expect(RIG_KEYS).toHaveLength(16);
    expect(Object.keys(BODY_ANIM).sort()).toEqual([...RIG_KEYS].sort());
    const atk = RIG_KEYS.reduce((n, k) => n + Object.keys(BODY_ANIM[k]!.attacks).length, 0);
    expect(atk).toBe(40);
    for (const k of RIG_KEYS) {
      const cs = creatureClips(k);
      expect(cs.slice(0, 2)).toEqual(["idle", "move"]);
      expect(cs.slice(-2)).toEqual(["hit", "death"]);
      expect(Object.keys(RIG[k]!.pivots)).toContain("body");
    }
  });

  it("確定性、數值都是有限數字（每款 × 每個片段 × 每一格）", () => {
    for (const k of RIG_KEYS)
      for (const clip of creatureClips(k))
        for (const u of framesOf(k, clip)) {
          const a = qCreaturePartPose(subject(k), clip, u)!;
          expect(qCreaturePartPose(subject(k), clip, u)).toEqual(a);
          for (const v of allNumbers(a)) expect(Number.isFinite(v), `${k} ${clip} ${u}`).toBe(true);
        }
  });

  it("攻擊、受擊播完回到原樣（最後一格整隻沒有位移、白閃）；倒下停在最後一格", () => {
    for (const k of RIG_KEYS) {
      for (const clip of creatureClips(k).filter((c) => c.startsWith("atk:") || c === "hit")) {
        const end = qCreaturePartPose(subject(k), clip, 1)!;
        expect(Math.abs(end.root.dx ?? 0), `${k} ${clip}`).toBeLessThan(0.01);
        expect(Math.abs(end.root.rot ?? 0), `${k} ${clip}`).toBeLessThan(0.01);
        expect(end.flash).toBe(0);
      }
      expect(creatureFrameU(k, "death", 5000)).toBe(1);
      expect(creatureFrameU(k, "death", 1000)).toBe(1);
      expect(qCreaturePartPose(subject(k), "hit", 0)!.flash).toBeGreaterThan(0.8);
    }
  });

  it("循環片段：一圈 8 格，相位由 id 雜湊決定（同 id 同格、不同 id 錯開）", () => {
    expect(creatureFrameU("hound", "idle", 0, "u1")).toBe(creatureFrameU("hound", "idle", 0, "u1"));
    const us = new Set(["a", "b", "c", "d", "e", "f", "g", "h"].map((id) => creatureFrameU("hound", "idle", 0, id)));
    expect(us.size).toBeGreaterThan(2);
    expect(creatureFrameU("hound", "idle", 2200, "u1")).toBe(creatureFrameU("hound", "idle", 0, "u1"));
    expect(quantizeClipU("hound", "move", 0.99)).toBe(7 / 8);
    expect(creatureFrameU("hound", "dance", 0)).toBeNull();
    expect(qCreaturePartPose(subject("hound"), "dance", 0)).toBeNull();
  });

  it("減少動態：待機、移動站好（null）；受擊只白閃；倒下直接最後一格；攻擊只往前推（特效照放）", () => {
    for (const k of RIG_KEYS) {
      expect(qCreaturePartPose(subject(k), "idle", 0.5, true)).toBeNull();
      expect(qCreaturePartPose(subject(k), "move", 0.5, true)).toBeNull();
      const hit = qCreaturePartPose(subject(k), "hit", 0, true)!;
      expect(hit.flash).toBeGreaterThan(0);
      expect(hit.parts).toEqual({});
      const d0 = qCreaturePartPose(subject(k), "death", 0, true)!;
      const last = qCreaturePartPose(subject(k), "death", 1)!;
      expect({ ...d0, fx: [] }).toEqual({ ...last, fx: [] });
      for (const clip of creatureClips(k).filter((c) => c.startsWith("atk:"))) {
        const p = qCreaturePartPose(subject(k), clip, 0.5, true)!;
        expect(Object.keys(p.parts)).toEqual([]);
        expect(Math.abs(p.root.dx ?? 0)).toBeLessThanOrEqual(2);
      }
    }
  });

  it("依動作類型挑攻擊：每款每種類型都挑得到一個（沒有就退回普攻）", () => {
    const types: AttackType[] = ["melee", "melee2", "charge", "breath", "cast", "area", "summon", "blink"];
    for (const k of RIG_KEYS) for (const t of types) expect(creatureClips(k)).toContain(attackClipFor(k, t));
    expect(attackClipFor("bear", "area")).toBe("atk:quake");
    expect(attackClipFor("hound", "cast")).toBe("atk:cast");
    expect(attackClipFor("feline", "charge")).toBe("atk:pounce");
    expect(attackClipFor("boar", "breath")).toBe("atk:breath");
    expect(attackClipFor("lizard", "summon")).toBe("atk:summon");
    expect(attackClipFor("wraith", "blink")).toBe("atk:blink");
  });

  it("作用端在畫布內：貼圖裡畫的特效與整隻位移不超出異形畫布（large 1.25）", () => {
    const halfW = CREATURE_W / 2 / 1.25;
    const up = CREATURE_FOOT_Y / 1.25;
    const down = (CREATURE_H - CREATURE_FOOT_Y) / 1.25;
    for (const k of RIG_KEYS)
      for (const clip of creatureClips(k))
        for (const u of framesOf(k, clip)) {
          const p = qCreaturePartPose(subject(k), clip, u)!;
          expect(Math.abs(p.root.dx ?? 0)).toBeLessThan(20);
          for (const f of p.fx) {
            if (f.ranged === true) continue;
            const reach = Math.abs(f.x ?? 0) + Math.max(f.r ?? 0, f.rx ?? 0, (f.max ?? 0) + (f.spread ?? 0));
            expect(reach, `${k} ${clip} ${u} ${f.k}`).toBeLessThan(halfW);
            expect(f.y ?? 0, `${k} ${clip} ${u} ${f.k}`).toBeGreaterThan(-up);
            expect(f.y ?? 0).toBeLessThan(down);
          }
        }
  });

  it("畫得出每一格（沒有 DOM：直接平塗），同一格兩次指令流相同", () => {
    const stream = (draw: (c: CanvasRenderingContext2D) => void): string => {
      const out: string[] = [];
      const ctx = new Proxy({} as Record<string, unknown>, {
        get: (t, p: string) => (p in t ? t[p] : (...a: unknown[]) => void out.push(`${p}(${a.map(String).join(",")})`)),
        set: (t, p: string, v) => ((t[p] = v), out.push(`${p}=${String(v)}`), true),
      }) as unknown as CanvasRenderingContext2D;
      draw(ctx);
      return out.join(";");
    };
    for (const k of RIG_KEYS) {
      const r = resolveCreature({ look: SPEC[k]!, elite: true, affixes: ["berserk", "mirror"] });
      for (const clip of creatureClips(k)) {
        const pose = { clip, u: 0.5 };
        const a = stream((c) => drawCreature(c, r, pose));
        expect(a.length).toBeGreaterThan(100);
        expect(stream((c) => drawCreature(c, r, pose))).toBe(a);
      }
      // 攻擊類型的引用（atk:@type）也畫得出來
      expect(stream((c) => drawCreature(c, r, { clip: "atk:@area", u: 0.5 })).length).toBeGreaterThan(100);
    }
  });
});
