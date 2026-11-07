// QK-4b：四足獸倒下閉眼 ×、熊與野豬側倒、傀儡崩塌斷成 3 塊、鳥落地收翅待機與起飛／落地過場、戰場站好的鳥是落地姿勢。
import { describe, expect, it } from "vitest";
import { perchAt, PERCH_MS, quantizeCreaturePose, creaturePoseKey } from "./creaturePose";
import { creaturePalette, creaturePerches, drawCreature, resolveCreature, rigKey } from "./inkCreature";
import { BIRD_PERCH_DY, PERCHERS, qCreaturePartPose, type AnimSubject } from "./qCreatureAnim";

const subj = (body: string, variant?: string): AnimSubject => {
  const r = resolveCreature({ look: { body, material: "fur", ...(variant ? { variant } : {}) } });
  const P = creaturePalette(r);
  return { key: rigKey(r), element: r.element, mat: P.mat, base: P.base, accent: P.accent };
};
const stream = (draw: (c: CanvasRenderingContext2D) => void): string => {
  const out: string[] = [];
  const ctx = new Proxy({} as Record<string, unknown>, {
    get: (t, p: string) => (p in t ? t[p] : (...a: unknown[]) => void out.push(`${p}(${a.map(String).join(",")})`)),
    set: (t, p: string, v) => ((t[p] = v), out.push(`${p}=${String(v)}`), true),
  }) as unknown as CanvasRenderingContext2D;
  draw(ctx);
  return out.join(";");
};

describe("QK-4b：倒下", () => {
  it("犬狼、野豬、熊、豹、蜥蜴倒下後段閉眼（×），開頭睜眼", () => {
    for (const b of ["hound", "boar", "bear", "feline", "lizard"]) {
      const s = subj(b);
      expect(qCreaturePartPose(s, "death", 0)!.eyeShut).toBeUndefined();
      expect(qCreaturePartPose(s, "death", 1)!.eyeShut).toBe(true);
    }
  });
  it("閉眼的格畫 × 不畫方眼高光（白色方塊）", () => {
    const r = resolveCreature({ look: { body: "bear", material: "fur" } });
    const open = stream((c) => drawCreature(c, r, { clip: "death", u: 0 }));
    const shut = stream((c) => drawCreature(c, r, { clip: "death", u: 1 }));
    expect(open).toContain("roundRect");
    expect(shut).toContain("lineCap=round");
  });
  it("熊、野豬側倒：四腳往前後攤開（前腳負、後腳正），身體落地", () => {
    for (const b of ["bear", "boar"]) {
      const p = qCreaturePartPose(subj(b), "death", 1)!;
      expect(p.parts["FN"]!.rot!).toBeLessThan(-0.8);
      expect(p.parts["BN"]!.rot!).toBeGreaterThan(0.8);
      expect(p.root.dy!).toBeGreaterThan(5);
    }
  });
  it("傀儡崩塌：軀幹斷成 3 塊、頭滾到一旁（往後、轉一圈多）、手臂落地", () => {
    const p = qCreaturePartPose(subj("golem"), "death", 1)!;
    expect(p.split?.["body"]).toHaveLength(3);
    expect(p.parts["head"]!.dx!).toBeLessThan(-10);
    expect(Math.abs(p.parts["head"]!.rot!)).toBeGreaterThan(Math.PI * 2);
    expect(p.parts["armN"]!.dy!).toBeGreaterThan(20);
    const r = resolveCreature({ look: { body: "golem", material: "stone" } });
    const s = stream((c) => drawCreature(c, r, { clip: "death", u: 1 }));
    expect(s.split("clip()").length - 1).toBeGreaterThanOrEqual(3);
    expect(qCreaturePartPose(subj("golem"), "death", 0)!.split?.["body"]!.every((q) => (q.dx ?? 0) === 0 && (q.dy ?? 0) === 0)).toBe(true);
  });
});

describe("QK-4b：鳥待機與起飛／落地", () => {
  const bird = subj("flyer", "bird");
  it("待機落地（比移動的飛行姿勢低）、收翅（sy 負）；第 6～7 格抖翅", () => {
    const f = (u: number) => qCreaturePartPose(bird, "idle", u)!;
    expect(f(0).root.dy!).toBeCloseTo(BIRD_PERCH_DY, 5);
    expect(f(0).parts["wingN"]!.sy!).toBeLessThan(0);
    const rest = f(0).parts["wingN"]!.rot!;
    expect(f(5 / 8).parts["wingN"]!.rot!).toBeGreaterThan(rest + 0.3);
    expect(f(1 / 8).parts["wingN"]!.rot!).toBeCloseTo(rest, 5);
    const fly = qCreaturePartPose(bird, "move", 0)!;
    expect(f(0).root.dy! - (fly.root.dy ?? 0)).toBeGreaterThan(BIRD_PERCH_DY - 0.01);
  });
  it("perchAt：開頭、結尾 4 格過場（1→0.75→0.5→0.25→0），中間 0", () => {
    expect(perchAt(0, 5000)).toBe(1);
    expect(perchAt(PERCH_MS * 0.3, 5000)).toBe(0.75);
    expect(perchAt(PERCH_MS * 0.6, 5000)).toBe(0.5);
    expect(perchAt(PERCH_MS * 0.9, 5000)).toBe(0.25);
    expect(perchAt(PERCH_MS, 5000)).toBe(0);
    expect(perchAt(2000, 2000)).toBe(0);
    expect(perchAt(5000, 0)).toBe(1);
    expect(perchAt(5000, PERCH_MS * 0.5)).toBe(0.5);
  });
  it("移動片段 perch 內插：1＝待機第 0 格、0＝飛行；中間介於兩者；只有鳥", () => {
    const sit = qCreaturePartPose(bird, "idle", 0)!;
    const fly = qCreaturePartPose(bird, "move", 0.25)!;
    const full = qCreaturePartPose(bird, "move", 0.25, false, 1)!;
    expect(full.root.dy!).toBeCloseTo(sit.root.dy!, 5);
    expect(full.parts["wingN"]!.sy!).toBeCloseTo(sit.parts["wingN"]!.sy!, 5);
    const half = qCreaturePartPose(bird, "move", 0.25, false, 0.5)!;
    expect(half.root.dy!).toBeCloseTo(((fly.root.dy ?? 0) + sit.root.dy!) / 2, 5);
    expect(PERCHERS.has("bird")).toBe(true);
    const hound = subj("hound");
    expect(qCreaturePartPose(hound, "move", 0.25, false, 1)).toEqual(qCreaturePartPose(hound, "move", 0.25));
  });
  it("perch 進快取鍵與量化；只有鳥 creaturePerches", () => {
    expect(creaturePoseKey({ clip: "move", u: 0.25, perch: 0.5 })).toContain("perch0.5");
    expect(quantizeCreaturePose({ clip: "move", u: 0.25, perch: 0.5 }).perch).toBe(0.5);
    expect(quantizeCreaturePose({ clip: "move", u: 0.25, perch: 0 }).perch).toBeUndefined();
    expect(creaturePerches(resolveCreature({ look: { body: "flyer", variant: "bird", material: "fur" } }))).toBe(true);
    expect(creaturePerches(resolveCreature({ look: { body: "flyer", variant: "bat", material: "fur" } }))).toBe(false);
  });
});
