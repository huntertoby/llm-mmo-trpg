// 6R-F（前端審查第 4 點）：減少動態時每一類動畫都不播或直接跳到結果；震動開關的預設跟著系統設定。
import { Container, Sprite, Texture } from "pixi.js";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { UnitDraw } from "../battle/drawModel";
import type { StepVfx, VfxCast, VfxReaction, VfxSpecial } from "../battle/vfx";
import { loadShake } from "../battle/vfxPrefs";
import { ArtTextures } from "./artTextures";
import { bodyEffect, reactEffects } from "./reactEffects";
import { reduceEffects, reduceVfx, REDUCED_DROP } from "./reducedMotion";
import { riseEffects, specialEffects, victoryEffects, type ResultHost } from "./resultEffects";
import { BODY_LABEL } from "./unitSprite";
import { castEffects, shakeEffect, type Effect } from "./vfxEffects";

const HERO = "u_hero";
const FOE = "u_foe";

const unit = (id: string, over: Partial<UnitDraw> = {}): UnitDraw => ({
  id, x: 1, y: 1, marker: "A", template: "t", name: "n", team: "ally", fill: 0, hpRatio: 1, shieldRatio: 0,
  active: false, hero: false, downed: false, summon: false, totem: false, remaining: null, revivable: false, bomb: null,
  facing: "east", weaponId: "iron_sword", weaponClass: "melee", ...over,
}) as UnitDraw;

function host(): ResultHost & { rests: string[] } {
  const draws = new Map([HERO, FOE].map((id) => [id, unit(id)]));
  const sprites = new Map<string, Container>();
  for (const id of draws.keys()) {
    const c = new Container();
    const body = new Sprite(Texture.WHITE);
    body.label = BODY_LABEL;
    c.addChild(body);
    sprites.set(id, c);
  }
  const rests: string[] = [];
  return {
    art: new ArtTextures(),
    sprite: (id) => sprites.get(id) ?? null,
    draw: (id) => draws.get(id),
    hold: () => undefined,
    release: () => undefined,
    setTexture: (_id, node, tex) => {
      node.texture = tex;
    },
    restBody: (id) => {
      rests.push(id);
    },
    bounds: () => ({ w: 400, h: 300 }),
    rests,
  };
}

const react = (kind: VfxReaction["kind"], unitId = FOE): VfxReaction => ({ unitId, pos: { x: 2, y: 1 }, kind, atMs: 0, seq: 3, cast: 0 });
const special = (kind: VfxSpecial["kind"], extra: Partial<VfxSpecial> = {}): VfxSpecial => ({ kind, pos: { x: 2, y: 1 }, unitId: FOE, atMs: 0, ...extra });
const cast = (over: Partial<VfxCast> = {}): VfxCast =>
  ({ kind: "slash", element: "physical", from: { x: 1, y: 1 }, to: { x: 2, y: 1 }, tiles: [], path: [], ranged: false, intensity: 1, crit: false, charge: false, legendary: false, chargeMs: 0, startMs: 0, impactMs: 100, ...over }) as VfxCast;
const vfxWith = (specials: VfxSpecial[], reactions: VfxReaction[] = []): StepVfx => ({ casts: [], hits: [], blasts: [], shake: 1, leadMs: 100, reactions, specials });

/** 每一類動畫產生的效果（照 6N-4～6N-8 的產生器）。 */
function everyKind(h: ResultHost): Record<string, Effect[]> {
  return {
    hit: reactEffects(h, react("hit"), 0, 1),
    heavy: reactEffects(h, react("heavy"), 0, 1),
    block: reactEffects(h, react("block"), 0, 1),
    dodge: reactEffects(h, react("dodge"), 0, 1),
    down: reactEffects(h, react("down"), 0, 1),
    rise: riseEffects(h, react("rise", HERO), 0, 1),
    crit: specialEffects(h, vfxWith([special("crit")]), { now: 0, impactMs: 100, scale: 1, shake: true, apply: () => undefined }),
    kill: specialEffects(h, vfxWith([special("kill")]), { now: 0, impactMs: 100, scale: 1, shake: true, apply: () => undefined }),
    blockSpecial: specialEffects(h, vfxWith([special("block", { attackerId: HERO })]), { now: 0, impactMs: 100, scale: 1, shake: true, apply: () => undefined }),
    dodgeSpecial: specialEffects(h, vfxWith([special("dodge")], [react("dodge")]), { now: 0, impactMs: 100, scale: 1, shake: true, apply: () => undefined }),
    boss: specialEffects(h, vfxWith([special("boss")]), { now: 0, impactMs: 100, scale: 1, shake: true, apply: () => undefined }),
    victory: victoryEffects(h, { unitIds: [HERO], seq: 9, battleKey: "m", ms: 500, clipMs: 400 }, 0),
    slash: castEffects(cast(), 0, 100),
    shake: [shakeEffect(2, 0, 100, () => undefined)],
  };
}

describe("reduced motion: every kind of animation is dropped or jumps to its result (6R-F)", () => {
  it("each generator tags what it makes", () => {
    const k = everyKind(host());
    const tags = (es: Effect[]) => es.map((e) => e.motion ?? "-");
    expect(tags(k.hit!)).toEqual(["body"]);
    expect(tags(k.heavy!)).toEqual(["body"]);
    expect(tags(k.block!)).toEqual(["body", "fx"]); // 身體 ＋ 火花
    expect(tags(k.dodge!)).toEqual(["body", "fx"]); // 身體 ＋ 殘影
    expect(tags(k.down!)).toEqual(["body"]);
    expect(tags(k.rise!)).toEqual(["fx", "body"]); // 綠光 ＋ 站起來
    expect(tags(k.crit!)).toEqual(["flash"]); // 全畫面閃白
    expect(tags(k.kill!)).toEqual(["shake"]);
    expect(tags(k.blockSpecial!)).toEqual(["fx", "body"]); // 大火花 ＋ 攻擊者被彈開
    expect(tags(k.dodgeSpecial!)).toEqual(["fx"]); // 第二層殘影
    expect(tags(k.boss!)).toEqual(["dim"]); // 四周變暗
    expect(tags(k.victory!)).toEqual(["body", "-"]); // 舉手 ＋「勝利」字樣（字照舊）
    expect(tags(k.slash!)).toEqual(["fx", "-"]); // 弧光 ＋ 命中爆發（爆發照舊）
    expect(tags(k.shake!)).toEqual(["shake"]);
  });

  it("with reduced motion nothing tagged flash / shake / dim / fx is left, and their nodes are destroyed", () => {
    const k = everyKind(host());
    for (const [name, list] of Object.entries(k)) {
      const dropped = list.filter((e) => e.motion !== undefined && REDUCED_DROP.has(e.motion));
      const kept = reduceEffects(list, true);
      expect(kept.some((e) => e.motion !== undefined && REDUCED_DROP.has(e.motion)), name).toBe(false);
      for (const e of dropped) expect(e.node.destroyed, name).toBe(true);
      expect(kept.length, name).toBe(list.length - dropped.length);
    }
  });

  it("body clips (skill, hit, dodge, victory, revive) draw only the last frame once", () => {
    const h = host();
    const seen: number[] = [];
    const body = bodyEffect(h, FOE, 0, 300, (_s, t) => seen.push(t));
    const [kept] = reduceEffects([body], true);
    kept!.update(0);
    kept!.update(0.4);
    kept!.update(0.9);
    expect(seen).toEqual([1]);
    kept!.end?.();
    expect(h.rests).toEqual([FOE]); // 播到時間照舊回到站好
  });

  it("without reduced motion effects pass through unchanged", () => {
    const k = everyKind(host());
    const all = Object.values(k).flat();
    const kept = reduceEffects(all, false);
    expect(kept).toEqual(all);
    expect(kept.every((e, i) => e === all[i])).toBe(true);
  });

  it("reduceVfx: no hit stops and no 6N-8 skill-variant fx layer; damage, hits and timing unchanged", () => {
    const look = { trail: "spiral", burst: "ring", spread: "jet" } as unknown as NonNullable<VfxCast["look"]>;
    const vfx: StepVfx = { ...vfxWith([special("crit")]), casts: [cast({ kind: "projectile", look })], hits: [{ pos: { x: 2, y: 1 }, element: "fire", crit: true, atMs: 100 }], stops: [{ atMs: 100, ms: 100 }] };
    const r = reduceVfx(vfx, true);
    expect(r.stops).toBeUndefined();
    expect(r.casts[0]!.look).toBeUndefined();
    expect(r.casts[0]!.impactMs).toBe(vfx.casts[0]!.impactMs);
    expect(r.hits).toEqual(vfx.hits);
    expect(r.leadMs).toBe(vfx.leadMs);
    expect(reduceVfx(vfx, false)).toBe(vfx);
  });
});

describe("shake toggle default follows prefers-reduced-motion (6R-F)", () => {
  afterEach(() => vi.unstubAllGlobals());

  const stub = (reduce: boolean, saved: string | null) => {
    vi.stubGlobal("window", {
      matchMedia: () => ({ matches: reduce, addEventListener: () => undefined, removeEventListener: () => undefined }),
      localStorage: { getItem: () => saved, setItem: () => undefined },
    });
  };

  it("nothing saved: on unless the system asks for reduced motion", () => {
    stub(false, null);
    expect(loadShake()).toBe(true);
    stub(true, null);
    expect(loadShake()).toBe(false);
  });

  it("a saved choice wins", () => {
    stub(true, "on");
    expect(loadShake()).toBe(true);
    stub(false, "off");
    expect(loadShake()).toBe(false);
  });
});
