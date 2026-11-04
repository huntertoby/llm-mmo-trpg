// 6N-7：受擊、閃避的變體（受擊 3、閃避 3），以及浮動字從頭頂冒出（美術 PM 6N-6 驗收）。
import { describe, expect, it } from "vitest";
import type { BattleView } from "../api/types";
import { vfxFor } from "../battle/vfx";
import { variantHash } from "./attackVariants";
import { DODGE_VARIANTS, HIT_VARIANTS, REACT_MS, reactFrame, reactVariant, reactVariantKey } from "./reactClips";
import { FLOAT_HEAD_GAP, FLOAT_RISE_MAX, FLOAT_SLOT_STEP, floatBaseY } from "./uiAnim";
import { HUMAN_TOP_Y } from "./unitSprite";

const HERO = "u_hero";
const FOE = "u_foe";

function view(foeStatuses: string[] = []): BattleView {
  return {
    map_id: "bamboo_grove",
    units: [
      { id: HERO, name_zh: "主角", pos: { x: 1, y: 1 }, team: "ally", max_hp: 40, statuses: [] },
      { id: FOE, name_zh: "盜賊", pos: { x: 2, y: 1 }, team: "enemy", max_hp: 40, statuses: foeStatuses.map((status_id) => ({ status_id, remaining: 1 })) },
    ],
    tiles: [],
  } as unknown as BattleView;
}
const hitEv = (seq: number, amount = 4) => [
  { seq, round: 1, type: "attack_rolled", attacker_id: HERO, target_id: FOE, hit: true },
  { seq: seq + 1, round: 1, type: "damage_dealt", target_id: FOE, source_id: HERO, element: "physical", amount, hp_before: 40, hp_after: 40 - amount },
];
const missEv = (seq: number) => [{ seq, round: 1, type: "attack_rolled", attacker_id: HERO, target_id: FOE, hit: false }];
const STEPS = Array.from({ length: 25 }, (_, i) => i / 24);

describe("hit and dodge variants (方案 2.10 第 5 點)", () => {
  it("has 3 hit variants and 3 dodge variants; the first is the 6N-4 clip", () => {
    expect(HIT_VARIANTS.map((v) => v.zh)).toEqual(["後仰", "側彎", "彎腰"]);
    expect(DODGE_VARIANTS.map((v) => v.zh)).toEqual(["側跳", "後跳", "蹲低"]);
    for (const t of STEPS) {
      expect(reactFrame("hit", t, { variant: 0 })).toEqual(reactFrame("hit", t));
      expect(reactFrame("heavy", t, { variant: 0 })).toEqual(reactFrame("heavy", t));
      expect(reactFrame("dodge", t, { variant: 0, side: -1 })).toEqual(reactFrame("dodge", t, { side: -1 }));
    }
  });

  it("the key is battle key : seq : target ID : hit|dodge, through the same finalizer as attacks", () => {
    expect(reactVariantKey("bamboo_grove", 5, FOE, "hit")).toBe("bamboo_grove:5:u_foe:hit");
    for (let seq = 1; seq < 40; seq++) {
      expect(reactVariant("m", seq, FOE, "hit")).toBe(variantHash(`m:${seq}:${FOE}:hit`) % 3);
      expect(reactVariant("m", seq, FOE, "dodge")).toBe(reactVariant("m", seq, FOE, "dodge"));
    }
  });

  it("dev page keys: 8 hits and 8 dodges in a row each show all 3 variants", () => {
    // dev 頁 `#variants` 連續 8 次：閃避的目標 rt_12（seq ＝ n）、受擊的目標 rt_13（damage_dealt seq ＝ n＋1）
    const hits = new Set(Array.from({ length: 8 }, (_, i) => reactVariant("skill_gallery", i + 2, "rt_13", "hit")));
    const dodges = new Set(Array.from({ length: 8 }, (_, i) => reactVariant("skill_gallery", i + 1, "rt_12", "dodge")));
    expect(hits.size).toBe(3);
    expect(dodges.size).toBe(3);
  });

  it("every variant comes up over many keys", () => {
    for (const clip of ["hit", "dodge"] as const) {
      const seen = new Set<number>();
      for (let seq = 1; seq < 60; seq++) seen.add(reactVariant("bamboo_grove", seq, FOE, clip));
      expect(seen.size, clip).toBe(3);
    }
  });

  it("variants keep the length, the flash and the after-image curve (6N-5 enhancements unchanged)", () => {
    expect(REACT_MS.hit).toBe(360);
    expect(REACT_MS.heavy).toBe(440);
    expect(REACT_MS.dodge).toBe(380);
    for (const t of STEPS) {
      for (const k of [1, 2]) {
        expect(reactFrame("hit", t, { variant: k }).flash, `hit ${k} ${t}`).toBe(reactFrame("hit", t).flash);
        expect(reactFrame("heavy", t, { variant: k }).flash, `heavy ${k} ${t}`).toBe(reactFrame("heavy", t).flash);
        expect(reactFrame("dodge", t, { variant: k }).ghost, `dodge ${k} ${t}`).toBe(reactFrame("dodge", t).ghost);
      }
    }
  });

  it("variants start and end standing (no jump into the next clip) and look different in the middle", () => {
    for (const clip of ["hit", "heavy", "dodge"] as const)
      for (const k of [0, 1, 2]) {
        const end = reactFrame(clip, 1, { variant: k });
        expect(end.pose, `${clip} ${k}`).toEqual({});
        expect(Math.abs(end.side) + Math.abs(end.air) + Math.abs(end.rotation), `${clip} ${k}`).toBeLessThan(0.11);
      }
    const mid = (clip: "hit" | "dodge", k: number) => JSON.stringify(reactFrame(clip, 0.3, { variant: k }));
    for (const clip of ["hit", "dodge"] as const) expect(new Set([0, 1, 2].map((k) => mid(clip, k))).size, clip).toBe(3);
    // 後跳往後、蹲低往下沉；側跳往側邊
    expect(reactFrame("dodge", 0.4, { variant: 1 }).back).toBeGreaterThan(8);
    expect(reactFrame("dodge", 0.4, { variant: 2 }).pose.bob ?? 0).toBeGreaterThan(5);
    expect(Math.abs(reactFrame("dodge", 0.4, { variant: 0 }).side)).toBeGreaterThan(8);
  });
});

describe("reactions carry the picked variant", () => {
  it("hits and dodges get a variant from the target's key; the hit moment does not move", () => {
    const at = new Set<number>();
    const kinds = new Set<number>();
    for (let seq = 1; seq <= 40; seq++) {
      const r = vfxFor(hitEv(seq), view(), {}).reactions![0]!;
      expect(r.kind).toBe("hit");
      expect(r.variant).toBe(reactVariant("bamboo_grove", seq + 1, FOE, "hit")); // damage_dealt 的 seq
      at.add(r.atMs);
      kinds.add(r.variant!);
      const d = vfxFor(missEv(seq), view(), {}).reactions![0]!;
      expect(d.kind).toBe("dodge");
      expect(d.variant).toBe(reactVariant("bamboo_grove", seq, FOE, "dodge"));
    }
    expect(at.size).toBe(1);
    expect(kinds.size).toBe(3);
  });

  it("a heavy hit uses the hit variants; a block has none", () => {
    const heavy = vfxFor(hitEv(3, 20), view(), {}).reactions![0]!;
    expect(heavy.kind).toBe("heavy");
    expect(heavy.variant).toBe(reactVariant("bamboo_grove", 4, FOE, "hit"));
    const ev = [{ seq: 3, round: 1, type: "damage_dealt", target_id: FOE, source_id: HERO, element: "physical", amount: 3, hp_before: 40, hp_after: 37, block_permille: 500 }];
    const block = vfxFor(ev, view(), {}).reactions![0]!;
    expect(block.kind).toBe("block");
    expect(block.variant).toBeUndefined();
  });

  for (const s of ["frozen", "stun", "prone", "root"]) {
    it(`a target that cannot move (${s}) still has no dodge clip, whatever the variant would be`, () => {
      for (let seq = 1; seq <= 12; seq++) expect(vfxFor(missEv(seq), view([s]), {}).reactions ?? []).toEqual([]);
    });
  }
});

describe("damage numbers rise from above the head (美術 PM 6N-6 驗收)", () => {
  it("starts just above the unit's top (unitTopY) instead of the body's middle", () => {
    const center = 100;
    const h = 20;
    const y = floatBaseY(center, HUMAN_TOP_Y, h, 0);
    expect(y + h / 2).toBeCloseTo(center + HUMAN_TOP_Y - FLOAT_HEAD_GAP, 6); // 字的下緣在頭頂上方
    expect(y).toBeLessThan(center + HUMAN_TOP_Y);
    // 比 6N-6 以前（格中心往上 0.3 格）高
    expect(y).toBeLessThan(center - 48 * 0.3);
  });

  it("follows taller units, stacks later floats upward, and big floats sit higher by their own height", () => {
    expect(floatBaseY(0, -60, 20, 0)).toBeLessThan(floatBaseY(0, -34, 20, 0));
    expect(floatBaseY(0, -34, 20, 1)).toBe(floatBaseY(0, -34, 20, 0) - FLOAT_SLOT_STEP);
    expect(floatBaseY(0, -34, 30, 0) + 15).toBeCloseTo(floatBaseY(0, -34, 20, 0) + 10, 6);
  });

  it("never rises above the top of the map (first row)", () => {
    const y = floatBaseY(24, -34, 20, 0, -28);
    expect(y - 10 - FLOAT_RISE_MAX).toBeGreaterThanOrEqual(-28 - 1e-9);
    expect(floatBaseY(500, -34, 20, 0, -28)).toBe(500 - 34 - FLOAT_HEAD_GAP - 10);
  });

  it("the standard human top matches unitTopY's formula", () => {
    expect(HUMAN_TOP_Y).toBeLessThan(0);
    expect(HUMAN_TOP_Y).toBeGreaterThan(-48);
  });
});
