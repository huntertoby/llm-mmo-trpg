// Phase 6N-9：狀態動作（statusAnim）的觸發條件、時間軸、確定性、定身與冰凍、reduced-motion。
import { Container, Sprite } from "pixi.js";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { UnitDraw } from "../battle/drawModel";
import { idleFrame } from "./idleClips";
import { idleFrameFor, idles } from "./idleMotion";
import { ANIM, arcAt, BODY_H, hasAnimatedStatic, isFrozenLook, LEG_KEYS, lockLegs, POISON_TINT, staticRemainder, statusAnimKinds, statusFrame, STATUS_ANIM_KINDS, type StatusAnimKind } from "./statusAnim";
import { StatusAnimator } from "./statusAnimLayer";
import { bodyEffects } from "./statusIcon";
import { BODY_LABEL } from "./unitSprite";

const ID = "unit_0001";

afterEach(() => vi.restoreAllMocks());

describe("觸發條件（8 種）", () => {
  const cases: Array<[string[], boolean, StatusAnimKind]> = [
    [["burning"], false, "burning"],
    [["frozen"], false, "frozen"],
    [["poison"], false, "poison"],
    [["stun"], false, "stunned"],
    [["root"], false, "rooted"],
    [["concealed"], false, "concealed"],
    [[], true, "wet"],
    [["shielded_charged"], false, "charged"],
  ];
  it.each(cases)("%j（站在水上 %s）→ %s", (ids, onWater, kind) => {
    expect(statusAnimKinds(ids, onWater)).toEqual([kind]);
  });

  it("沒有狀態、不在水上：沒有動作", () => {
    expect(statusAnimKinds([], false)).toEqual([]);
    expect(statusAnimKinds(["weaken", "hasted"], false)).toEqual([]);
  });

  it("冰凍不算暈眩（同 bodyEffects）；全部疊在一起時照固定順序", () => {
    expect(statusAnimKinds(["frozen", "stun"], false)).toEqual(["frozen"]);
    const all = statusAnimKinds(["shielded_charged", "root", "poison", "burning", "concealed", "stun"], true);
    expect(all).toEqual(STATUS_ANIM_KINDS.filter((k) => k !== "frozen"));
  });

  it("8 種都有看得出來的東西（粒子或身體動作）", () => {
    for (const k of STATUS_ANIM_KINDS) {
      let visible = false;
      for (let ms = 0; ms < 4000 && !visible; ms += 20) {
        const f = statusFrame([k], ID, ms);
        visible = f.particles.some((p) => p.alpha > 0.05) || f.body.rot !== 0 || f.body.skewX !== 0 || f.body.alphaMul !== 1 || f.body.tint !== null;
      }
      expect(visible, k).toBe(true);
    }
  });
});

describe("時間軸", () => {
  it("暈眩：星星 1.25 秒轉一圈，身體左右搖 ±0.07", () => {
    const a = statusFrame(["stunned"], ID, 0).particles.filter((p) => p.tex === "star");
    const b = statusFrame(["stunned"], ID, ANIM.starTurnMs).particles.filter((p) => p.tex === "star");
    expect(a).toHaveLength(3);
    a.forEach((p, i) => {
      expect(b[i]!.x).toBeCloseTo(p.x, 6);
      expect(b[i]!.y).toBeCloseTo(p.y, 6);
    });
    let max = 0;
    for (let ms = 0; ms < ANIM.swayMs; ms += 5) max = Math.max(max, Math.abs(statusFrame(["stunned"], ID, ms).body.rot));
    expect(max).toBeGreaterThan(0.065);
    expect(max).toBeLessThanOrEqual(ANIM.sway + 1e-9);
  });

  it("燃燒：3 個火苗，形狀 4 張輪播；冒煙每 1.6 秒一次、0.9 秒內", () => {
    const frames = new Set<string>();
    let smokeMs = 0;
    for (let ms = 0; ms < ANIM.smokeEveryMs; ms += 10) {
      const f = statusFrame(["burning"], ID, ms);
      const flames = f.particles.filter((p) => p.tex.startsWith("flame"));
      expect(flames).toHaveLength(3);
      for (const p of flames) frames.add(p.tex);
      if (f.particles.some((p) => p.tex === "smoke")) smokeMs += 10;
    }
    expect([...frames].sort()).toEqual(["flame0", "flame1", "flame2", "flame3"]);
    expect(smokeMs).toBeGreaterThan(ANIM.smokeMs - 30);
    expect(smokeMs).toBeLessThanOrEqual(ANIM.smokeMs + 10);
  });

  it("中毒：泡泡從頭頂往上冒，臉色偏綠", () => {
    const f = statusFrame(["poison"], ID, 300);
    expect(f.body.tint).toBe(POISON_TINT);
    for (const p of f.particles) expect(p.y).toBeLessThan(-BODY_H);
  });

  it("帶電：偶爾閃（每個週期 140ms），同一個 ID、同一次閃的位置固定", () => {
    let on = 0;
    const total = 20000;
    for (let ms = 0; ms < total; ms += 10) if (arcAt(ID, ms) !== null) on += 10;
    expect(on / total).toBeGreaterThan(ANIM.arcMs / (ANIM.arcMinMs + ANIM.arcSpanMs) - 0.02);
    expect(on / total).toBeLessThan(ANIM.arcMs / ANIM.arcMinMs + 0.02);
  });

  it("潮濕：水滴往下掉（y 遞增），掉完就不見", () => {
    const ys: number[] = [];
    for (let ms = 0; ms < ANIM.dropMs; ms += 20) {
      const d = statusFrame(["wet"], ID, ms).particles;
      if (d.length > 0) ys.push(d[0]!.y);
    }
    expect(ys.length).toBeGreaterThan(5);
    expect(Math.max(...ys)).toBeLessThanOrEqual(-2 + 1e-9);
  });

  it("冰凍：反光每 2.4 秒掃過一次；身體完全不動", () => {
    let glint = 0;
    for (let ms = 0; ms < ANIM.glintEveryMs; ms += 10) {
      const f = statusFrame(["frozen"], ID, ms);
      expect(f.body).toEqual({ rot: 0, skewX: 0, alphaMul: 1, tint: null });
      if (f.particles.length > 0) glint += 10;
    }
    expect(glint).toBeGreaterThan(ANIM.glintMs - 30);
    expect(glint).toBeLessThanOrEqual(ANIM.glintMs + 10);
  });

  it("隱身：透明度在 0.64～1 倍之間閃、輕微扭曲", () => {
    for (let ms = 0; ms < 3000; ms += 37) {
      const b = statusFrame(["concealed"], ID, ms).body;
      expect(b.alphaMul).toBeGreaterThanOrEqual(0.64 - 1e-9);
      expect(b.alphaMul).toBeLessThanOrEqual(1 + 1e-9);
      expect(Math.abs(b.skewX)).toBeLessThanOrEqual(0.05 + 1e-9);
    }
  });
});

describe("確定性", () => {
  const all = STATUS_ANIM_KINDS.filter((k) => k !== "frozen");
  it("同一個 ID、同一個時間 → 同一個畫面；不用 Math.random、不讀時鐘", () => {
    const rnd = vi.spyOn(Math, "random");
    const now = vi.spyOn(Date, "now");
    const perf = vi.spyOn(performance, "now");
    for (let ms = 0; ms < 5000; ms += 97) expect(statusFrame(all, ID, ms)).toEqual(statusFrame(all, ID, ms));
    expect(rnd).not.toHaveBeenCalled();
    expect(now).not.toHaveBeenCalled();
    expect(perf).not.toHaveBeenCalled();
  });

  it("不同的人相位錯開", () => {
    const a = statusFrame(["stunned"], "unit_0001", 500);
    const b = statusFrame(["stunned"], "unit_0002", 500);
    expect(a.particles.map((p) => p.x)).not.toEqual(b.particles.map((p) => p.x));
  });
});

describe("冰凍不呼吸、定身腳不動", () => {
  const draw = (statusIds: string[]): UnitDraw => ({ id: ID, downed: false, statusIds }) as unknown as UnitDraw;

  it("冰凍（含任何「跳過回合、火能解除」的狀態）不待機", () => {
    expect(isFrozenLook(["frozen"])).toBe(true);
    expect(idles(draw(["frozen"]))).toBe(false);
    expect(idles(draw(["stun"]))).toBe(true);
  });

  it("定身時小動作拿掉腿與起伏，上半身照舊", () => {
    let fidgets = 0;
    for (let ms = 0; ms < 30000; ms += 50) {
      const f = idleFrameFor(draw(["root"]), ms);
      if (f.pose === null) continue;
      fidgets += 1;
      for (const k of LEG_KEYS) expect(f.pose[k] ?? 0).toBe(0);
      expect(f.key.endsWith("|rooted")).toBe(true);
    }
    expect(fidgets).toBeGreaterThan(0);
    // 沒定身時照舊
    for (let ms = 0; ms < 30000; ms += 50) expect(idleFrameFor(draw([]), ms)).toEqual(idleFrame(ID, ms));
  });

  it("lockLegs 只拿掉腿的欄位", () => {
    expect(lockLegs({ arm: 1, liftR: 2, bob: -1, lean: 0.1 })).toEqual({ arm: 1, lean: 0.1 });
  });
});

describe("靜態特效的替換", () => {
  it("暈眩的星星、火與毒的腳邊粒子改由動畫畫；其他（流血的血滴）照舊", () => {
    const e = bodyEffects(["stun", "burning", "bleed"]);
    expect(hasAnimatedStatic(e)).toBe(true);
    const r = staticRemainder(e);
    expect(r.stunned).toBe(false);
    expect(r.dots).toEqual(e.dots.filter((d) => d !== "fire"));
    expect(hasAnimatedStatic(bodyEffects(["frozen", "shielded"]))).toBe(false);
  });
});

describe("驅動（StatusAnimator）", () => {
  function unitSprite(): { c: Container; body: Sprite } {
    const c = new Container();
    const body = new Sprite();
    body.label = BODY_LABEL;
    c.addChild(body);
    return { c, body };
  }

  it("暈眩：身體以腳底為軸搖；正在播別的動畫（held）時不動身體", () => {
    const a = new StatusAnimator();
    const { c, body } = unitSprite();
    const draws = new Map([[ID, { id: ID, downed: false, statusIds: ["stun"] } as unknown as UnitDraw]]);
    a.reset(new Set());
    a.tick(300, new Map([[ID, c]]), draws, () => false);
    expect(body.rotation).toBeCloseTo(statusFrame(["stunned"], ID, 300).body.rot, 6);
    const before = body.rotation;
    a.tick(200, new Map([[ID, c]]), draws, () => true);
    expect(body.rotation).toBe(before);
  });

  it("reduced-motion：關掉後身體回原位、tick 不再動", () => {
    const a = new StatusAnimator();
    const { c, body } = unitSprite();
    const draws = new Map([[ID, { id: ID, downed: false, statusIds: ["concealed"] } as unknown as UnitDraw]]);
    body.alpha = 0.55;
    a.reset(new Set());
    a.tick(250, new Map([[ID, c]]), draws, () => false);
    expect(body.alpha).not.toBeCloseTo(0.55, 4);
    a.setEnabled(false);
    expect(body.alpha).toBeCloseTo(0.55, 6);
    expect(body.skew.x).toBe(0);
    expect(a.tick(400, new Map([[ID, c]]), draws, () => false)).toBe(0);
    expect(body.alpha).toBeCloseTo(0.55, 6);
  });

  it("站在水上的人算潮濕；倒下的人沒有動作", () => {
    const a = new StatusAnimator();
    const { c } = unitSprite();
    a.reset(new Set([ID]));
    a.tick(16, new Map([[ID, c]]), new Map([[ID, { id: ID, downed: false, statusIds: [] } as unknown as UnitDraw]]), () => false);
    expect(a.stats().units).toBe(1);
    const b = new StatusAnimator();
    b.reset(new Set());
    b.tick(16, new Map([[ID, unitSprite().c]]), new Map([[ID, { id: ID, downed: true, statusIds: ["burning"] } as unknown as UnitDraw]]), () => false);
    expect(b.stats().units).toBe(0);
  });
});
