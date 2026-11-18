// AR-SK2：SK-2 三個新原語的演出描述（`sk2Fx.ts`）與接到播放計畫（`playback.ts`）。事件是真引擎跑的（`dev/fixtures/sk2Events.json`）。
import { describe, expect, it } from "vitest";
import type { BattleResponse, BattleView, SkillCard, StepOut, UnitView } from "../api/types";
import fixture from "../dev/fixtures/sk2Events.json";
import { playbackPlan } from "./playback";
import { sk2FxOf, spreadRange, type Sk2Hook, type Sk2Spread } from "./sk2Fx";
import { tile, unit } from "./testFixtures";

type FixtureCase = { events: Record<string, unknown>[] };
const DATA = fixture as unknown as Record<string, FixtureCase>;
const HERO = "unit_0001";

const card = (id: string, effects: string[]): SkillCard => ({ id, shape: "單體", skeleton: "strike", effect_ids: effects, icon: { segments: [{ skeleton: "strike", shape_id: effects.includes("hook") ? "line" : "single", range: 5, effects: effects.map((type) => ({ type })) }] } }) as unknown as SkillCard;
const CARDS = { skill_sk2_hook: card("skill_sk2_hook", ["hook"]), skill_sk2_absorb: card("skill_sk2_absorb", ["absorb_surface", "damage"]), skill_sk2_fire: card("skill_sk2_fire", ["damage"]) };

function view(units: UnitView[], w = 9, h = 7): BattleView {
  const tiles = [];
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) tiles.push(tile(x, y));
  return { team: "ally", map_id: "t", width: w, height: h, tiles, objects: [], units, traps: [], turn_order: [HERO], active_unit: HERO, round: 1, max_rounds: 30, pending: null, source_wells: [], zones: [], runes: [] } as unknown as BattleView;
}
const hero = (): UnitView => unit(HERO, "ally", 1, 3);
const foe = (id: string, x: number, y: number, extra: Partial<UnitView> = {}): UnitView => unit(id, "enemy", x, y, extra);

describe("AR-SK2 演出描述（sk2FxOf）", () => {
  it("吸收表面：格子、表面、收益照 surface_absorbed", () => {
    const v = view([hero(), foe("unit_0002", 5, 3)]);
    expect(sk2FxOf(DATA.absorb!.events, v, v, CARDS)).toEqual([{ kind: "absorb", casterId: HERO, tile: { x: 1, y: 3 }, surface: "ice", gain: "element", element: "ice" }]);
  });

  it("疾病擴散：範圍格照單位距離（量到最近佔格）、被選中那格、倒下那一刻", () => {
    const before = view([hero(), foe("unit_0002", 5, 3), foe("unit_0003", 5, 4)]);
    const after = view([hero(), foe("unit_0002", 5, 3, { downed: true }), foe("unit_0003", 5, 4)]);
    const fx = sk2FxOf(DATA.contagion!.events, before, after, CARDS, (id) => (id === "unit_0002" ? 420 : 0));
    expect(fx).toHaveLength(1);
    const s = fx[0] as Sk2Spread;
    expect(s).toMatchObject({ kind: "spread", fromId: "unit_0002", toId: "unit_0003", from: { x: 5, y: 3 }, to: { x: 5, y: 4 }, statusId: "burning", chosen: { x: 5, y: 4 }, atMs: 420 });
    expect(s.range).toEqual([{ x: 5, y: 2 }, { x: 4, y: 3 }, { x: 6, y: 3 }, { x: 5, y: 4 }]);
  });

  it("疾病擴散的範圍：巨型單位量到最近佔格（3×3 外圍一圈 12 格，不含自己佔的 9 格與斜角）", () => {
    const giant = foe("g", 4, 3, { footprint: 3, tiles: [3, 4, 5].flatMap((x) => [2, 3, 4].map((y) => ({ x, y }))) } as Partial<UnitView>);
    const r = spreadRange(giant, { width: 9, height: 7 });
    expect(r).toHaveLength(12);
    expect(r.some((p) => p.x === 2 && p.y === 1)).toBe(false);
    expect(r.some((p) => p.x === 4 && p.y === 1)).toBe(true);
  });

  it("鉤：一般拉回、熔岩前煞住（停在不相鄰、沒有撞擊）、巨型頭目拉不動", () => {
    const v = (x: number) => view([hero(), foe("unit_0002", x, 3), foe("unit_0003", 6, 3)]);
    const pull = sk2FxOf(DATA.hook!.events, v(5), v(2), CARDS)[0] as Sk2Hook;
    expect(pull).toMatchObject({ kind: "hook", casterId: HERO, targetId: "unit_0002", from: { x: 5, y: 3 }, to: { x: 2, y: 3 }, mode: "pull", hazard: null });
    const lava = sk2FxOf(DATA.hook_lava!.events, v(5), v(4), CARDS)[0] as Sk2Hook;
    expect(lava).toMatchObject({ mode: "brake", from: { x: 5, y: 3 }, to: { x: 4, y: 3 }, hazard: { x: 3, y: 3 } });
    const g = view([hero(), foe("unit_0002", 5, 3, { footprint: 3, tiles: [4, 5, 6].flatMap((x) => [2, 3, 4].map((y) => ({ x, y }))) } as Partial<UnitView>)]);
    const giant = sk2FxOf(DATA.hook_giant!.events, g, g, CARDS)[0] as Sk2Hook;
    expect(giant).toMatchObject({ mode: "immovable", hookTile: { x: 4, y: 3 }, from: { x: 5, y: 3 }, to: { x: 5, y: 3 } });
  });

  it("技能卡沒有 hook 原語時，同樣的拉扯事件不算鉤", () => {
    const v = view([hero(), foe("unit_0002", 5, 3), foe("unit_0003", 6, 3)]);
    expect(sk2FxOf(DATA.hook!.events, v, v, { skill_sk2_hook: card("skill_sk2_hook", ["pull"]) })).toEqual([]);
  });

  it("同樣的輸入得到同樣的描述（不讀時鐘、不用亂數）", () => {
    const v = view([hero(), foe("unit_0002", 5, 3), foe("unit_0003", 6, 3)]);
    expect(sk2FxOf(DATA.hook!.events, v, v, CARDS)).toEqual(sk2FxOf(DATA.hook!.events, v, v, CARDS));
  });
});

describe("AR-SK2 接到播放計畫", () => {
  it("鉤：特效帶 sk2（鎖鏈換掉施放者發出的那一段、拉的時間）；略過時沒有特效", () => {
    const before = view([hero(), foe("unit_0002", 5, 3), foe("unit_0003", 6, 3)]);
    const after = view([hero(), foe("unit_0002", 2, 3), foe("unit_0003", 6, 3)]);
    const step = { actor_id: HERO, events: DATA.hook!.events, view: after, step: { type: "use_skill" } } as unknown as StepOut;
    const res = { steps: [step], initial_view: before, view: after } as unknown as BattleResponse;
    const plan = playbackPlan(res, HERO, "normal", CARDS);
    const sk2 = plan.frames[0]?.vfx?.sk2 ?? [];
    expect(sk2).toHaveLength(1);
    const h = sk2[0] as Sk2Hook;
    expect(h.castIndex).toBe(0);
    expect(h.pullAtMs).toBe(plan.frames[0]?.vfx?.leadMs);
    expect(playbackPlan(res, HERO, "skip", CARDS).frames[0]?.vfx).toBeNull();
  });

  it("慢速播放時 sk2 的時間不跟著縮放（繪製器自己乘倍率）", () => {
    const before = view([hero(), foe("unit_0002", 5, 3)]);
    const step = { actor_id: HERO, events: DATA.absorb!.events, view: before, step: { type: "use_skill" } } as unknown as StepOut;
    const res = { steps: [step], initial_view: before, view: before } as unknown as BattleResponse;
    const a = playbackPlan(res, HERO, "normal", CARDS).frames[0]?.vfx?.sk2;
    const b = playbackPlan(res, HERO, "slow", CARDS).frames[0]?.vfx?.sk2;
    expect(a).toBeDefined();
    expect(b).toEqual(a);
  });
});
