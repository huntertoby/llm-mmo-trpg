// QK-7：武器專屬待機（docs/art/武器待機移植需求.md 第 3 節）：15 種定義、相位確定性與錯開、減少動態、8 格量化、
// 每一格照跑 Q 版武器自測（手在握把上〔像素〕、作用端在畫布內）、疊加層的錨點，以及接上 IdleMotion 的行為。
import { Container, Sprite, Texture } from "pixi.js";
import { describe, expect, it, vi } from "vitest";
import type { BattleView } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { tile, unit } from "../battle/testFixtures";
import { vecCanvas } from "../test/vecRaster";
import { IdleMotion } from "./idleMotion";
import { FRONT_KEYS, WEAPON_IDLE, WEAPON_IDLE_FRAMES, WEAPON_IDLE_KINDS, weaponIdleFrame, weaponIdleKindOf, weaponIdlePhase, type WeaponIdleKind } from "./idleWeapons";
import type { InkPose } from "./inkPose";
import { poseKey } from "./motionClips";
import { S, type M6, type P2, type QPose, type QUnit, type QView } from "./qCore";
import { CLASS_OF, drawQ, KEY } from "./qDoll";
import { SAMPLE_HOOKS as H, SAMPLE_ITEMS as IT, sampleUnit } from "./qSample";
import { Q_BOX } from "./qStamp";
import { QW, qWeapon } from "./qWeapons";
import { BODY_LABEL } from "./unitSprite";
import { glowKindOf, glowShapes, probeGlowAnchor } from "./weaponGlow";
import { texturePose } from "./weaponIdleLayer";

const IDS = ["unit_0001", "unit_0002", "enemy:wolf_pack:0", "enemy:bandit:1", "battle-7:hero_1", "battle-7:hero_2", "battle-7:hero_3", "battle-7:hero_4", "battle-7:hero_5"];
const unitOf = (k: WeaponIdleKind): QUnit => (k === "sword_shield" ? { look: sampleUnit("sword").look, gear: { ...sampleUnit("sword").gear, off_hand: IT.round_shield } } : sampleUnit(k));
const VIEWS: ReadonlyArray<readonly [QView, boolean]> = [
  ["side", false],
  ["side", true],
  ["front", false],
  ["back", false],
];

describe("QK-7：15 種待機的定義與相位", () => {
  it("15 種都有定義；循環長度照樣張（鞭、拳套 1.2 秒，其他 2.4 秒）", () => {
    expect(WEAPON_IDLE_KINDS.length).toBe(15);
    expect(new Set(WEAPON_IDLE_KINDS).size).toBe(15);
    for (const k of WEAPON_IDLE_KINDS) {
      expect(WEAPON_IDLE[k].ms).toBe(k === "whip" || k === "gauntlet" ? 1200 : 2400);
      for (let j = 0; j < 8; j++) for (const v of Object.values(WEAPON_IDLE[k].core(j / 8))) expect(Number.isFinite(v)).toBe(true);
    }
  });

  it("相位是 FNV-1a 的 `${id}:weaponIdle`（固定值）；同一個 ID、同一個時鐘永遠同一格，全程不呼叫 Math.random", () => {
    const rnd = vi.spyOn(Math, "random");
    expect(weaponIdlePhase("battle-7:hero_1")).toBe(weaponIdlePhase("battle-7:hero_1"));
    for (const k of WEAPON_IDLE_KINDS)
      for (const id of IDS)
        for (let ms = 0; ms < 5000; ms += 97) {
          const a = weaponIdleFrame(k, id, ms);
          expect(weaponIdleFrame(k, id, ms)).toEqual(a);
          expect(weaponIdleFrame(k, id, ms + WEAPON_IDLE[k].ms).frame).toBe(a.frame); // 一個循環後回到同一格
        }
    expect(rnd).not.toHaveBeenCalled();
    rnd.mockRestore();
  });

  it("不同 ID 的相位不同（同一隊錯開）：9 個 ID 兩兩不同，同一刻不會全員同一格", () => {
    const ph = IDS.map(weaponIdlePhase);
    expect(new Set(ph).size).toBe(IDS.length);
    const frames = IDS.map((id) => weaponIdleFrame("sword_shield", id, 1000).frame);
    expect(new Set(frames).size).toBeGreaterThan(2);
  });

  it("減少動態：姿勢等於站好（空姿勢、光不脈動）", () => {
    for (const k of WEAPON_IDLE_KINDS)
      for (const ms of [0, 333, 1200, 2399]) {
        const f = weaponIdleFrame(k, "unit_0001", ms, { reduce: true });
        expect(f.pose).toEqual({});
        expect(poseKey(texturePose(f.pose, null))).toBe("");
      }
  });

  it("8 格量化：每種 × 每個朝向，一個循環內的貼圖鍵最多 8 個；法杖、魔導劍的光不量化（不進貼圖鍵），法球的光與浮沉跟著 8 格", () => {
    for (const k of WEAPON_IDLE_KINDS)
      for (const [view] of VIEWS) {
        const keys = new Set<string>();
        const glows = new Set<number>();
        for (let ms = 0; ms < WEAPON_IDLE[k].ms; ms += 7) {
          const gk = glowKindOf(k, view);
          const f = weaponIdleFrame(k, "unit_0002", ms, { breath: false, view, live: gk !== null });
          keys.add(poseKey(texturePose(f.pose, gk)));
          if (f.pose.glow !== undefined) glows.add(f.pose.glow);
          if (view !== "side") for (const key of Object.keys(f.pose)) expect(FRONT_KEYS).toContain(key);
        }
        expect(keys.size, `${k} ${view}`).toBeLessThanOrEqual(WEAPON_IDLE_FRAMES);
        if (glowKindOf(k, view) !== null) expect(glows.size, `${k} glow`).toBeGreaterThan(WEAPON_IDLE_FRAMES * 4);
        else expect(glows.size, `${k} glow`).toBeLessThanOrEqual(WEAPON_IDLE_FRAMES);
      }
  });

  it("選待機：主手武器的種類；單手揮砍＋盾 → 劍盾；匕首、斧、鎚 → 劍；空手、Q 版不會畫的手持物 → 不晃", () => {
    for (const k of WEAPON_IDLE_KINDS) expect(weaponIdleKindOf(unitOf(k))).toBe(k);
    const base = sampleUnit("sword");
    const withMain = (main: QUnit["gear"]["main_hand"], off?: QUnit["gear"]["off_hand"]): QUnit => ({ look: base.look, gear: { ...base.gear, main_hand: main, off_hand: off } });
    expect(weaponIdleKindOf(withMain({ kind: "axe" }))).toBe("sword");
    expect(weaponIdleKindOf(withMain({ kind: "hammer" }, IT.kite_shield))).toBe("sword_shield");
    expect(weaponIdleKindOf(withMain({ kind: "fist" }))).toBe("gauntlet");
    expect(weaponIdleKindOf(withMain({ kind: "longgun" }))).toBe("gun");
    expect(weaponIdleKindOf(withMain({ kind: "sword", form: "arcane" }))).toBe("arcane_blade");
    expect(weaponIdleKindOf(withMain({ kind: "staff" }, IT.tome))).toBe("staff");
    expect(weaponIdleKindOf(withMain(undefined))).toBeNull();
    expect(weaponIdleKindOf(withMain({ kind: "whisk" }))).toBeNull();
  });
});

interface Got {
  hand: P2;
  tip: P2;
  m: M6;
  wkey: string;
  hands: Record<string, P2 | boolean>;
}
function probe(u: QUnit, view: QView, west: boolean, P: QPose, k = 1, o: P2 = [0, 0]): Got | null {
  let got: Got | null = null;
  const hands: Record<string, P2 | boolean> = {};
  const { ctx } = vecCanvas();
  ctx.setTransform(west ? -k : k, 0, 0, k, o[0], o[1]);
  drawQ(ctx, u, view, H, { ...P, hands, probe: (_k, h, t, _v, _off, m, wkey) => (got ??= { hand: h, tip: t, m, wkey, hands }) }, west);
  return got;
}
const inBox = (p: P2): boolean => Math.abs(p[0]) < Q_BOX.W / 2 - 1 && p[1] > -(Q_BOX.H - Q_BOX.FOOT) + 1 && p[1] < Q_BOX.FOOT - 1;

describe("QK-7：每一格照跑 Q 版武器自測", () => {
  it("15 種 × 8 格 × 朝東、朝西、正面、背面：作用端在畫布內；手在握把上（像素，手心 ±1 單位內有武器）", () => {
    const bad: string[] = [];
    const K = 4;
    const O: P2 = [160, 240];
    for (const kind of WEAPON_IDLE_KINDS) {
      const u = unitOf(kind);
      for (const [view, west] of VIEWS) {
        for (let j = 0; j < WEAPON_IDLE_FRAMES; j++) {
          const ms = ((j + 0.5) / WEAPON_IDLE_FRAMES - weaponIdlePhase("t") + 1) * WEAPON_IDLE[kind].ms;
          const f = weaponIdleFrame(kind, "t", ms, { view });
          expect(f.frame).toBe(j);
          const tag = `${kind} ${view}${west ? "西" : ""} 第${j + 1}格`;
          const g0 = probe(u, view, west, f.pose);
          if (!g0) {
            if (kind !== "bow") bad.push(`${tag} 沒畫`); // 弓的握法另走 bowStill（不經 mainWeapon），樣張 selfTest 也不量弓的作用端
            continue;
          }
          if (!inBox(g0.tip) || !inBox(g0.hand)) bad.push(`${tag} 作用端出界 ${g0.tip.map((v) => v.toFixed(1)).join(",")}`);
          if (west) continue; // 像素檢查照樣張 gripTest：只量朝東、正面、背面
          const g = probe(u, view, false, f.pose, K, O)!;
          const { ctx, at } = vecCanvas();
          ctx.setTransform(g.m.a, g.m.b, g.m.c, g.m.d, g.m.e, g.m.f);
          S.hooks = H;
          S.POSE = f.pose;
          QW[g.wkey]!.draw(ctx, qWeapon(u.gear.main_hand)!.item);
          S.POSE = null;
          S.hooks = null;
          const touches = (h: P2 | boolean | undefined): boolean =>
            Array.isArray(h) && [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1], [0.7, 0.7], [-0.7, 0.7], [0.7, -0.7], [-0.7, -0.7]].some(([dx, dy]) => at(h[0] + dx! * K, h[1] + dy! * K)[3] > 0);
          const kc = CLASS_OF[qWeapon(u.gear.main_hand)!.kind];
          const kv = kc ? KEY()[kc]![view === "back" ? "back" : view === "side" ? "side" : "front"] : undefined;
          const wOff = kv?.wh === "off" || (kc === "bow" && view === "side");
          if (!touches(wOff ? g.hands["off"] : g.hands["main"])) bad.push(`${tag} 主手沒握到`);
        }
      }
    }
    expect(bad).toEqual([]);
  });

  it("疊加層：法杖（四面）、魔導劍（背面除外）每一格都量得到錨點、光在畫布內；杖頭光在作用端", () => {
    const bad: string[] = [];
    for (const kind of ["staff", "arcane_blade", "orb"] as const) {
      for (const [view, west] of VIEWS) {
        const gk = glowKindOf(kind, view);
        if (gk === null) {
          expect(kind === "orb" || view === "back", `${kind} ${view}`).toBe(true);
          continue;
        }
        for (let j = 0; j < WEAPON_IDLE_FRAMES; j++) {
          const f = weaponIdleFrame(kind, "t", (j / WEAPON_IDLE_FRAMES) * WEAPON_IDLE[kind].ms, { view, breath: false });
          const tex = texturePose(f.pose, gk) as QPose;
          const a = probeGlowAnchor(vecCanvas().ctx, unitOf(kind), view, west, H, tex, gk);
          const tag = `${kind} ${view}${west ? "西" : ""} ${j}`;
          if (a === null) {
            bad.push(`${tag} 沒有錨點`);
            continue;
          }
          for (const s of glowShapes(a, f.pose.glow ?? 0)) {
            const pts: P2[] = s.circle ? [[s.circle[0], s.circle[1]]] : [];
            for (let i = 0; s.poly && i + 1 < s.poly.length; i += 2) pts.push([s.poly[i]!, s.poly[i + 1]!]);
            if (!pts.every(inBox)) bad.push(`${tag} 出界`);
          }
          const g = probe(unitOf(kind), view, west, tex)!;
          const head = glowShapes(a, 1).find((x) => x.circle && x.alpha === 1)?.circle;
          if (kind === "staff" && (!head || Math.hypot(head[0] - g.tip[0], head[1] - g.tip[1]) > 1)) bad.push(`${tag} 杖頭光不在作用端`);
        }
      }
    }
    expect(bad).toEqual([]);
  });
});

describe("QK-7：接上 IdleMotion", () => {
  const view = { team: "ally", map_id: "m", map_name_zh: "m", width: 4, height: 1, tiles: [tile(0, 0), tile(1, 0), tile(2, 0), tile(3, 0)], objects: [], units: [unit("unit_0001", "ally", 0, 0, { template_id: "hero_fighter" })], traps: [], turn_order: ["unit_0001"], active_unit: "unit_0001", round: 1, max_rounds: 9, weather_id: null, weather_name_zh: null, objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null, source_wells: [], zones: [], runes: [] } as unknown as BattleView;
  const real = buildDrawModel(view, "unit_0001").units[0]!;
  function scene(n: number, active = false) {
    const units = new Map<string, Container>();
    const draws = new Map<string, UnitDraw>();
    for (let i = 0; i < n; i++) {
      const c = new Container();
      const body = new Sprite(Texture.WHITE);
      body.label = BODY_LABEL;
      body.scale.set(0.5, 0.5);
      c.addChild(body);
      const id = `battle-7:hero_${i + 1}`;
      units.set(id, c);
      draws.set(id, { ...real, id, x: i, facing: "east", active, statusIds: [] });
    }
    return { units, draws };
  }

  it("沒輪到行動的人：一個循環內每人換貼圖的姿勢最多 8 種；同一時鐘兩次跑出同樣的貼圖序列", () => {
    const run = (): Map<string, string[]> => {
      const s = scene(3);
      const m = new IdleMotion();
      const seen = new Map<string, string[]>();
      for (let ms = 0; ms < 2400; ms += 16) m.tick(16, s.units, s.draws, (id, _s, p) => seen.set(id, [...(seen.get(id) ?? []), p === null ? "" : poseKey(p)]));
      return seen;
    };
    const a = run();
    expect(a.size).toBe(3);
    for (const [id, all] of a) {
      const ks = all.filter((k) => !k.includes("armL")); // 6M-4 的小動作（張望、伸懶腰）照舊，播時武器待機暫停
      expect(ks.every((k) => k.includes("wpn")), `${id} ${ks.join(" / ")}`).toBe(true); // hero_fighter：單手劍
      expect(new Set(ks).size, id).toBeLessThanOrEqual(WEAPON_IDLE_FRAMES);
      expect(ks.length, id).toBeGreaterThanOrEqual(4);
      expect(ks.every((k) => k !== ""), id).toBe(true);
    }
    expect(run()).toEqual(a);
  });

  it("輪到行動的人照現行（不播武器待機）；減少動態、關掉待機時一律站好", () => {
    const act = scene(2, true);
    const m = new IdleMotion();
    const calls: Array<InkPose | null> = [];
    for (let ms = 0; ms < 2400; ms += 16) m.tick(16, act.units, act.draws, (_id, _s, p) => calls.push(p));
    expect(calls.every((p) => p === null || !("wpn" in p || "shieldUp" in p))).toBe(true);

    for (const mode of ["reduced", "disabled"] as const) {
      const s = scene(2);
      const r = new IdleMotion();
      const got: Array<InkPose | null> = [];
      for (let ms = 0; ms < 600; ms += 16) r.tick(16, s.units, s.draws, () => undefined);
      if (mode === "reduced") r.reduced = true;
      else r.enabled = false;
      for (let ms = 0; ms < 2400; ms += 16) r.tick(16, s.units, s.draws, (_id, _s, p) => got.push(p));
      expect(got.length, mode).toBe(2); // 每人換回站好一次，之後不再動
      expect(got.every((p) => p === null)).toBe(true);
    }
  });
});
