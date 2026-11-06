// 6R-F（前端審查第 7、8 點）：變體一律用 variantHash 挑（不再 `seedOf % n`）；反應合併時變體、閃避方向跟著升級。
import { describe, expect, it } from "vitest";
import { variantHash } from "../render/attackVariants";
import { seedOf } from "../render/inkStyle";
import { npcFidgetPick, ROLE_FIDGETS } from "../render/npcFidgets";
import { arcAt } from "../render/statusAnim";
import { readSources, stripTsComments } from "../test/sourceScan";
import { upgradeReact, type ReactKind } from "./vfx";
import { type BattleResponse, type BattleView, type StepOut } from "../api/types";
import { playbackPlan } from "./playback";
import { attackFamilyInView, weaponClassInView } from "./viewGrip";

type R = { kind: ReactKind; seq: number; side?: 1 | -1; variant?: number };

describe("upgradeReact (6R-F; shared by addReact and the last-moment merge)", () => {
  it("upgrades kind, seq, variant and side together", () => {
    const old: R = { kind: "dodge", seq: 2, side: 1, variant: 0 };
    upgradeReact(old, { kind: "down", seq: 7, side: -1, variant: 2 });
    expect(old).toEqual({ kind: "down", seq: 7, side: -1, variant: 2 });
  });

  it("a stronger reaction without side/variant clears the old ones (they belonged to the weaker event)", () => {
    const old: R = { kind: "dodge", seq: 2, side: -1, variant: 3 };
    upgradeReact(old, { kind: "block", seq: 4 });
    expect(old).toEqual({ kind: "block", seq: 4 });
  });

  it("never downgrades", () => {
    const old: R = { kind: "down", seq: 7, variant: 1 };
    upgradeReact(old, { kind: "hit", seq: 9, side: 1, variant: 4 });
    expect(old).toEqual({ kind: "down", seq: 7, variant: 1 });
  });
});

describe("variant picks use variantHash, never seedOf % n (6R-F)", () => {
  it("NPC fidgets: the pick is variantHash of scene:id:n", () => {
    for (let n = 1; n < 40; n++) {
      const list = ROLE_FIDGETS.town;
      expect(npcFidgetPick("town_a", "npc_1", "town", n)).toBe(list[variantHash(`town_a:npc_1:${n}`) % list.length]);
    }
  });

  it("NPC fidgets: consecutive picks are not locked to a rotation (same pick two apart ≈ 1/3 for 3 kinds)", () => {
    let same = 0;
    let total = 0;
    for (let u = 0; u < 20; u++) {
      const picks = Array.from({ length: 60 }, (_, n) => npcFidgetPick("town_a", `npc_${u}`, "town", n + 1));
      for (let i = 2; i < picks.length; i++) {
        total += 1;
        if (picks[i] === picks[i - 2]) same += 1;
      }
    }
    expect(same / total).toBeGreaterThan(0.2);
    expect(same / total).toBeLessThan(0.47);
  });

  it("charged status arcs pick their shape with variantHash", () => {
    let found = 0;
    for (let ms = 0; ms < 20000 && found < 5; ms += 7) {
      const p = arcAt("u_x", ms);
      if (p === null) continue;
      found += 1;
      expect(["arc0", "arc1", "arc2"]).toContain(p.tex);
    }
    expect(found).toBeGreaterThan(0);
  });

  it("no client source picks a variant with `seedOf(...) % n` (value-noise uses like phases/offsets are not picks)", () => {
    // 會挑「第幾個變體」的寫法：`list[seedOf(...) % list.length]`、`` `name${seedOf(...) % n}` ``
    const bad = /\[\s*seedOf\([^)]*\)\s*%|\$\{\s*seedOf\([^)]*\)\s*%|seedOf\([^)]*\)\s*%\s*\w+\.length/;
    const hits = readSources()
      .filter(([path, code]) => bad.test(stripTsComments(code, path)))
      .map(([path]) => path);
    expect(hits).toEqual([]);
    expect(seedOf("x")).not.toBe(variantHash("x")); // 兩個雜湊真的不同
  }, 30_000); // 掃描全部原始碼並剖析註解：完整平行跑時會超過預設 5 秒
});

// --- 原 viewGrip6rf.test.ts ---
describe("原 viewGrip6rf.test.ts", () => {
// 6R-F（前端審查第 5 點）：普攻的武器類別、變體表列從這一步開始前的畫面（before）的裝備算，不讀繪製器。
// 重播、觀戰、重新整理（同一份事件、同一份 before）都挑到同一個變體。

const HERO = "u_hero";
const FOE = "u_foe";

function view(heroWeapon: string, heroClass = "melee"): BattleView {
  const u = (id: string, x: number, team: string, weapon: string, cls: string) => ({
    id, template_id: "t", name_zh: id, team, pos: { x, y: 1 }, hp: 30, max_hp: 30, shield: 0, downed: false, revivable: false, owner_id: null, totem_radius: null,
    statuses: [], tags: [], facing: team === "ally" ? "east" : "west", weapon_id: weapon, weapon_class: cls, equipment: [],
  });
  return {
    map_id: "m_grip", team: "ally", round: 1, width: 6, height: 3, tiles: [], objects: [], traps: [], zones: [], runes: [], source_wells: [],
    units: [u(HERO, 1, "ally", heroWeapon, heroClass), u(FOE, 2, "enemy", "fangs", "melee")],
  } as unknown as BattleView;
}

const attackStep = (after: BattleView, seq: number): StepOut =>
  ({
    actor_id: HERO,
    step: { type: "attack" },
    events: [
      { seq, round: 1, type: "attack_rolled", attacker_id: HERO, target_id: FOE, hit: true },
      { seq: seq + 1, round: 1, type: "damage_dealt", source_id: HERO, target_id: FOE, amount: 3, hp_before: 30, hp_after: 27, crit: false },
    ],
    view: after,
  }) as unknown as StepOut;

const arcsOf = (res: BattleResponse) =>
  playbackPlan(res, HERO, "normal", {}, new Set(), weaponClassInView, attackFamilyInView).frames.map((f) => ({ arcs: f.vfx?.casts.map((c) => c.arc ?? null), rows: f.skill?.map((r) => r.clip) }));

describe("weapon class and attack family from the before view (6R-F)", () => {
  it("pure functions of the view's gear", () => {
    const sword = view("one_handed_sword");
    expect(weaponClassInView(HERO, sword)).toBe(weaponClassInView(HERO, view("one_handed_sword")));
    expect(attackFamilyInView(HERO, sword)).toBe("sword");
    expect(attackFamilyInView(HERO, view("greatsword"))).toBe("heavy");
    expect(weaponClassInView("nobody", sword)).toBe("bare");
    expect(attackFamilyInView("nobody", sword)).toBeNull();
  });

  it("uses the gear in `before`, not the view after the step (or whatever the renderer last drew)", () => {
    const before = view("greatsword");
    const after = view("one_handed_sword"); // 這一步之後換了武器（或繪製器畫著別的）
    const res = { steps: [attackStep(after, 1)], view: after, initial_view: before } as unknown as BattleResponse;
    const plan = playbackPlan(res, HERO, "normal", {}, new Set(), weaponClassInView, attackFamilyInView);
    const viaBefore = playbackPlan(res, HERO, "normal", {}, new Set(), (id) => weaponClassInView(id, before), (id) => attackFamilyInView(id, before));
    expect(plan.frames[0]!.vfx).toEqual(viaBefore.frames[0]!.vfx);
    expect(plan.frames[0]!.skill).toEqual(viaBefore.frames[0]!.skill);
    // 拿 after 的裝備會挑到別的表列（大劍 → 斧錘雙手；單手劍 → 劍）：證明真的看的是 before
    const viaAfter = playbackPlan(res, HERO, "normal", {}, new Set(), (id) => weaponClassInView(id, after), (id) => attackFamilyInView(id, after));
    expect(viaAfter.frames[0]!.vfx!.casts[0]!.arc).not.toEqual(plan.frames[0]!.vfx!.casts[0]!.arc);
  });

  it("replay, spectate and refresh pick the same variant (same events, same before)", () => {
    const v = view("one_handed_sword");
    const res = { steps: [attackStep(v, 1), attackStep(v, 5), attackStep(v, 9)], view: v, initial_view: v } as unknown as BattleResponse;
    const first = arcsOf(res);
    // 重播：同一份回應再算一次
    expect(arcsOf(res)).toEqual(first);
    // 重新整理／觀戰：只收到後兩步（第二步開始前的畫面一樣）
    const later = arcsOf({ steps: res.steps.slice(1), view: v, initial_view: v } as unknown as BattleResponse);
    expect(later).toEqual(first.slice(1));
    expect(first.some((f) => (f.arcs ?? []).some((a) => a !== null))).toBe(true); // 真的有挑到普攻變體
  });
});
});
