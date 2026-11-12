// VFX-1：某一段「只給自己」（沒有命中、增益只落在施放者、施放者不在格子裡）時，特效改畫成施放者身上的光環。
// 美術 PM 的窄規則（docs/art/QI-4b與BAL-21b驗收.md 2.2 (a)）；任一條件不成立時和改之前逐字相同。
import { describe, expect, it } from "vitest";
import type { BattleView, Pos, SkillCard } from "../api/types";
import { aimOf, vfxFor, type VfxCards } from "./vfx";
import { skillTimeline } from "./skillSequence";
import { SUPPORT_VFX_KEY } from "./vfxPalette";

const BOSS = "c_heart";
const HERO = "u_hero";
const MATE = "u_mate";
const SPLASH = "skill_lava_splash";
const P = (x: number, y: number): Pos => ({ x, y });
const square = (c: Pos): Pos[] => [-1, 0, 1].flatMap((dy) => [-1, 0, 1].map((dx) => P(c.x + dx, c.y + dy)));

/** 和 `dev/skillGallery.ts` 的 BAL-21b 卡同一份結構（API 的 `icon.segments`）。 */
const SPLASH_CARD = {
  id: SPLASH,
  name_zh: "熔岩濺落",
  shape: "方陣",
  skeleton: "aura",
  timing: "delayed",
  effect_ids: ["shield"],
  stats: { range: 4 },
  icon: { segments: [{ skeleton: "aura", shape_id: "square3", range: 4, effects: [{ type: "shield" }] }, { skeleton: "area", shape_id: "square3", range: 0, effects: [{ type: "damage" }, { type: "create_surface" }] }] },
} as unknown as SkillCard;
const CARDS: VfxCards = { [SPLASH]: SPLASH_CARD };

function view(units: Record<string, Pos>): BattleView {
  return { map_id: "vfx1", units: Object.entries(units).map(([id, pos]) => ({ id, pos, max_hp: 100, hp: 100, statuses: [] })) } as unknown as BattleView;
}

const BOSS_AT = P(7, 2);
const SPOT = P(3, 2);
const UNITS = { [BOSS]: BOSS_AT, [HERO]: P(3, 2), [MATE]: P(2, 3) };

const used = (tiles: Pos[], skill = SPLASH, unit = BOSS) => ({ seq: 1, round: 1, type: "skill_used", unit_id: unit, skill_id: skill, name_zh: "熔岩濺落", ap: 2, mana: 6, mana_after: 40, tiles });
const cooldown = { seq: 2, round: 1, type: "skill_cooldown_changed", unit_id: BOSS, skill_id: SPLASH, remaining: 2 };
const shield = (unit = BOSS) => ({ seq: 3, round: 1, type: "shield_gained", unit_id: unit, source_id: BOSS, amount: 3, total: 3, rolls: [3] });
const charged = (tiles: Pos[], pos = SPOT) => ({ seq: 4, round: 1, type: "followup_charged", unit_id: BOSS, skill_id: SPLASH, name_zh: "熔岩濺落", release: "next_turn", pos, tiles, direction: null, anchored: true });

/** 熔岩濺落施放回合（引擎實際的事件順序：施放 → 冷卻 → 自己的護盾 → 蓄力預告）。 */
function castTurn(spot = SPOT, extra: Record<string, unknown>[] = []): Record<string, unknown>[] {
  const sq = square(spot);
  return [used(sq), cooldown, shield(), ...extra, charged(sq, spot)];
}

describe("VFX-1：三個條件都成立 → 光環畫在施放者身上", () => {
  it("熔岩濺落施放回合：選 3×3 在玩家身上，特效＝頭目身上的支援色光環", () => {
    const v = vfxFor(castTurn(), view(UNITS), CARDS);
    expect(v.casts).toHaveLength(1);
    const c = v.casts[0]!;
    expect(c.kind).toBe("aura");
    expect(c.from).toEqual(BOSS_AT);
    expect(c.to).toEqual(BOSS_AT);
    expect(c.tiles).toEqual([BOSS_AT]);
    expect(c.element).toBe(SUPPORT_VFX_KEY);
    expect(c.aim).toEqual(SPOT);
    expect(v.hits).toEqual([]);
  });

  it("時間、蓄力、配色和改之前（範圍）相同；身體瞄準的格子＝改之前的 to", () => {
    const after = vfxFor(castTurn(), view(UNITS), CARDS).casts[0]!;
    // 改之前的樣子：同一招、同一片格子但施放者站在格子裡（第三個條件不成立 → 照舊畫範圍）
    const inside = vfxFor(castTurn(P(6, 2)), view(UNITS), CARDS).casts[0]!;
    expect(inside.kind).toBe("area");
    expect(after.impactMs - after.startMs).toBe(inside.impactMs - inside.startMs);
    expect([after.chargeMs, after.charge, after.legendary, after.element]).toEqual([inside.chargeMs, inside.charge, inside.legendary, inside.element]);
    expect(aimOf(after)).toEqual(SPOT);
    expect(aimOf(inside)).toEqual(inside.to);
  });

  it("身體片段和改之前逐字相同（skillTimeline 的朝向、片段用 aim）", () => {
    const v = vfxFor(castTurn(), view(UNITS), CARDS);
    const now = skillTimeline(castTurn(), view(UNITS), CARDS, v, () => "bare", () => null)!;
    // 改之前的特效描述：同一段畫成選的 3×3（area、to＝選的格子）
    const { aim: _aim, ...c } = v.casts[0]!;
    const old = { ...v, casts: [{ ...c, kind: "area" as const, to: SPOT, tiles: square(SPOT), path: [BOSS_AT, SPOT], ranged: true }] };
    const was = skillTimeline(castTurn(), view(UNITS), CARDS, old, () => "bare", () => null)!;
    expect(now.rows.length).toBeGreaterThan(0);
    expect(now.rows).toEqual(was.rows);
    for (const r of now.rows) expect(r.target).toEqual(SPOT);
    expect(now.vfx.casts[0]!.kind).toBe("aura");
    expect(now.vfx.casts[0]!.from).toEqual(BOSS_AT);
  });
});

describe("VFX-1：任一條件不成立 → 維持原樣（範圍畫在選的格子）", () => {
  const areaAt = (events: Record<string, unknown>[], units: Record<string, Pos> = UNITS) => {
    const c = vfxFor(events, view(units), CARDS).casts[0]!;
    expect(c.kind).toBe("area");
    expect(c.aim).toBeUndefined();
    return c;
  };

  it("(a) 這一段有命中（傷害）", () => {
    const c = areaAt(castTurn(SPOT, [{ seq: 5, round: 1, type: "damage_dealt", target_id: HERO, source_id: BOSS, element: "fire", amount: 4, crit: false }]));
    expect(c.tiles).toHaveLength(9);
  });

  it("(a) 這一段有命中判定（沒打中也算）", () => {
    areaAt(castTurn(SPOT, [{ seq: 5, round: 1, type: "attack_rolled", attacker_id: BOSS, target_id: HERO, hit: false }]));
  });

  it("(a) 這一段碰到地面（造表面）", () => {
    areaAt(castTurn(SPOT, [{ seq: 5, round: 1, type: "surface_changed", pos: SPOT, before: "none", after: "fire", remaining: 2, cause: "effect" }]));
  });

  it("(b) 護盾給了別人", () => {
    const sq = square(SPOT);
    areaAt([used(sq), cooldown, shield(HERO), charged(sq)]);
  });

  it("(b) 自己的護盾＋別人的狀態", () => {
    areaAt(castTurn(SPOT, [{ seq: 5, round: 1, type: "status_applied", target_id: MATE, status_id: "slow", duration: 2, refreshed: false, source_id: BOSS }]));
  });

  it("(b) 沒有任何增益落地（只有施放與預告）", () => {
    const sq = square(SPOT);
    areaAt([used(sq), cooldown, charged(sq)]);
  });

  it("(c) 施放者站在那片格子裡", () => {
    const c = areaAt(castTurn(P(6, 2)));
    expect(c.tiles).toHaveLength(9);
  });

  it("形狀本來就是自身：照舊（光環在施放者身上、沒有 aim）", () => {
    const cards: VfxCards = { skill_self: { id: "skill_self", shape: "自身", skeleton: "aura" } as unknown as SkillCard };
    const c = vfxFor([used([BOSS_AT], "skill_self"), shield()], view(UNITS), cards).casts[0]!;
    expect(c.kind).toBe("aura");
    expect(c.aim).toBeUndefined();
  });

  it("一般攻擊：照舊", () => {
    const v = vfxFor([{ seq: 1, round: 1, type: "attack_rolled", attacker_id: BOSS, target_id: HERO, hit: true }], view({ [BOSS]: P(4, 2), [HERO]: P(3, 2) }), {});
    expect(v.casts[0]!.kind).toBe("slash");
    expect(v.casts[0]!.aim).toBeUndefined();
  });
});

describe("VFX-1：區域型的 fire_wall、war_hymn 不受影響", () => {
  const CASTER = "unit_0001";
  const ALLY = "unit_0002";
  const units = { [CASTER]: P(5, 5), [ALLY]: P(4, 6) };

  it("fire_wall（錐形、移動的火牆區域）：照舊是錐形", () => {
    const tiles = [P(4, 3), P(5, 3), P(6, 3), P(5, 4)];
    const card = { id: "skill_fire_wall", shape: "錐形（大小 2）", skeleton: "control", icon: { segments: [{ skeleton: "control", shape_id: "cone", range: null, effects: [{ type: "zone", surface: "fire" }] }] } } as unknown as SkillCard;
    const events = [
      { seq: 12, round: 1, type: "skill_used", unit_id: CASTER, skill_id: "skill_fire_wall", tiles },
      { seq: 13, round: 1, type: "skill_cooldown_changed", unit_id: CASTER, skill_id: "skill_fire_wall", remaining: 4 },
      { seq: 14, round: 1, type: "zone_created", zone_id: 1, owner_id: CASTER, skill_id: "skill_fire_wall", anchor: "moving", when: "both", affects: "enemies", cells: tiles, expires_round: 4, direction: "north", speed: 1, surface: "fire" },
      ...tiles.map((pos, i) => ({ seq: 15 + i, round: 1, type: "surface_changed", pos, before: "none", after: "fire", remaining: 2, cause: "zone" })),
    ];
    const c = vfxFor(events, view(units), { skill_fire_wall: card }).casts[0]!;
    expect(c.kind).toBe("cone");
    expect(c.tiles).toEqual(tiles);
    expect(c.aim).toBeUndefined();
  });

  it("war_hymn（跟著施放者的光環區域，只有自己在範圍裡）：照舊", () => {
    const tiles = [P(5, 3), P(4, 4), P(5, 4), P(6, 4), P(3, 5), P(4, 5), P(5, 5), P(6, 5), P(7, 5), P(4, 6), P(5, 6), P(6, 6), P(5, 7)];
    const card = { id: "skill_war_hymn", shape: "範圍光環（半徑 2）", skeleton: "aura", icon: { segments: [{ skeleton: "aura", shape_id: "allies_in_radius", range: null, effects: [{ type: "zone" }] }] } } as unknown as SkillCard;
    const events = [
      { seq: 9, round: 1, type: "skill_used", unit_id: CASTER, skill_id: "skill_war_hymn", tiles },
      { seq: 10, round: 1, type: "skill_cooldown_changed", unit_id: CASTER, skill_id: "skill_war_hymn", remaining: 3 },
      { seq: 11, round: 1, type: "zone_created", zone_id: 1, owner_id: CASTER, skill_id: "skill_war_hymn", anchor: "caster", when: "both", affects: "allies", cells: tiles, expires_round: 5, direction: null, speed: 0, surface: null },
      { seq: 12, round: 1, type: "zone_triggered", zone_id: 1, owner_id: CASTER, skill_id: "skill_war_hymn", unit_id: CASTER, cause: "enter", trigger_depth: 1 },
      { seq: 13, round: 1, type: "status_applied", target_id: CASTER, status_id: "empowered", duration: 1, refreshed: false, source_id: CASTER },
    ];
    const c = vfxFor(events, view({ [CASTER]: P(5, 5) }), { skill_war_hymn: card }).casts[0]!;
    expect(c.kind).toBe("aura");
    expect(c.tiles).toEqual(tiles);
    expect(c.aim).toBeUndefined();
  });
});
