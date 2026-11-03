// Phase 6M-4：待機（呼吸＋小動作）的時間軸、相位錯開與確定性；待機驅動不碰「沒設姿勢」的畫法。
import { Container, Sprite, Texture } from "pixi.js";
import { describe, expect, it } from "vitest";
import type { BattleView } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { tile, unit } from "../battle/testFixtures";
import { BREATH_MS, BREATH_PX, breathAt, breathPhase, breathScale, FIDGET_LEVELS, FIDGET_MS, fidgetAt, fidgetSchedule, idHash, idleFrame } from "./idleClips";
import { IdleMotion } from "./idleMotion";
import type { InkPose } from "./inkPose";
import { BODY_LABEL } from "./unitSprite";

const IDS = ["field_hero", "npc:smith", "npc:elder", "friend:ayu", "unit_0001", "unit_0002", "enemy:wolf_pack:0", "npc:guard_a", "npc:guard_b"];

describe("6M-4：呼吸", () => {
  it("雜湊是確定性的 FNV-1a（固定值，不用內建 hash、不用 Math.random）", () => {
    expect(idHash("")).toBe(2166136261);
    expect(idHash("a")).toBe(0xe40c292c);
    expect(idHash("field_hero")).toBe(idHash("field_hero"));
  });

  it("起伏 0～0.5、週期 1.6 秒；同一個 ID、同一個時間永遠相同", () => {
    for (const id of IDS) {
      for (let ms = 0; ms < BREATH_MS * 2; ms += 37) {
        const b = breathAt(id, ms);
        expect(b).toBeGreaterThanOrEqual(0);
        expect(b).toBeLessThanOrEqual(BREATH_PX + 1e-9);
        expect(breathAt(id, ms + BREATH_MS)).toBeCloseTo(b, 9);
        expect(breathAt(id, ms)).toBe(b);
      }
    }
  });

  it("相位錯開：九個人的相位兩兩不同，同一刻不會全員同步上下", () => {
    const phases = IDS.map(breathPhase);
    expect(new Set(phases).size).toBe(IDS.length);
    const at = IDS.map((id) => breathAt(id, 400));
    expect(Math.max(...at) - Math.min(...at)).toBeGreaterThan(BREATH_PX * 0.5);
  });

  it("縮放以腳底為軸：頭頂位移 ＝ 起伏（倍率 1 ＋ 起伏 ÷ 身高）", () => {
    expect(breathScale("x", 0)).toBeCloseTo(1 + breathAt("x", 0) / 53, 12);
  });
});

describe("6M-4：偶爾的小動作", () => {
  it("每人 7～11 秒一次、每次 1.2 秒，強度量化 4 級；第一次在偏移之後", () => {
    for (const id of IDS) {
      const { every, offset } = fidgetSchedule(id);
      expect(every).toBeGreaterThanOrEqual(7000);
      expect(every).toBeLessThan(11000);
      expect(offset).toBeLessThan(every);
      expect(fidgetAt(id, offset - 1)).toBeNull();
      let on = 0;
      const levels = new Set<number>();
      for (let ms = 0; ms < every * 3 + offset; ms += 10) {
        const f = fidgetAt(id, ms);
        if (f === null) continue;
        on += 10;
        levels.add(f.level);
      }
      expect(on).toBeGreaterThan(FIDGET_MS * 2.5);
      expect(on).toBeLessThanOrEqual(FIDGET_MS * 3);
      for (const l of levels) expect(Number.isInteger(l * FIDGET_LEVELS)).toBe(true);
      expect(levels.size).toBeLessThanOrEqual(FIDGET_LEVELS);
    }
  });

  it("錯開：同一刻做小動作的人不會全員一起", () => {
    for (let ms = 0; ms < 30000; ms += 250) {
      const busy = IDS.filter((id) => fidgetAt(id, ms) !== null).length;
      expect(busy).toBeLessThan(IDS.length);
    }
  });

  it("待機畫面：沒有小動作時姿勢 null（照站好的貼圖）；每人不同的姿勢最多 2 種 × 4 級", () => {
    const keys = new Set<string>();
    for (let ms = 0; ms < 60000; ms += 20) {
      const f = idleFrame("npc:smith", ms);
      if (f.key === "") expect(f.pose).toBeNull();
      else keys.add(f.key);
    }
    expect(keys.size).toBeGreaterThan(0);
    expect(keys.size).toBeLessThanOrEqual(8);
  });
});

describe("6M-4：待機驅動", () => {
  const real = buildDrawModel(
    { team: "ally", map_id: "m", map_name_zh: "m", width: 2, height: 1, tiles: [tile(0, 0), tile(1, 0)], objects: [], units: [unit("unit_0001", "ally", 0, 0, { template_id: "hero_fighter" })], traps: [], turn_order: ["unit_0001"], active_unit: "unit_0001", round: 1, max_rounds: 9, weather_id: null, weather_name_zh: null, objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null, source_wells: [], zones: [], runes: [] } as unknown as BattleView,
    "unit_0001",
  ).units[0]!;
  function scene(n: number) {
    const units = new Map<string, Container>();
    const draws = new Map<string, UnitDraw>();
    for (let i = 0; i < n; i++) {
      const c = new Container();
      const body = new Sprite(Texture.WHITE);
      body.label = BODY_LABEL;
      body.scale.set(0.5, 0.5);
      c.addChild(body);
      const id = `npc:${i}`;
      units.set(id, c);
      draws.set(id, { ...real, id, x: i, statusIds: [] });
    }
    return { units, draws };
  }
  const bodyOf = (c: Container) => c.children[0] as Sprite;

  it("站著的人只改垂直縮放（腳底為軸），水平不變；同樣的時間得到同樣的畫面", () => {
    const a = scene(4);
    const b = scene(4);
    const ma = new IdleMotion();
    const mb = new IdleMotion();
    for (let i = 0; i < 50; i++) {
      ma.tick(16, a.units, a.draws, () => undefined);
      mb.tick(16, b.units, b.draws, () => undefined);
    }
    for (const [id, c] of a.units) {
      expect(bodyOf(c).scale.x).toBe(0.5);
      expect(bodyOf(c).scale.y).toBeCloseTo(0.5 * breathScale(id, 800), 12);
      expect(bodyOf(c).scale.y).toBe(bodyOf(b.units.get(id)!).scale.y);
    }
  });

  it("移動中（hold）不套用，放開才恢復；hold 時縮放回到原本", () => {
    const s = scene(1);
    const m = new IdleMotion();
    m.tick(300, s.units, s.draws, () => undefined);
    const c = s.units.get("npc:0")!;
    m.hold("npc:0", c);
    expect(bodyOf(c).scale.y).toBe(0.5);
    m.hold("npc:0", c);
    m.release("npc:0");
    m.tick(300, s.units, s.draws, () => undefined);
    expect(bodyOf(c).scale.y).toBe(0.5); // 還有一段在播
    m.release("npc:0");
    m.tick(300, s.units, s.draws, () => undefined);
    expect(bodyOf(c).scale.y).toBeCloseTo(0.5 * breathScale("npc:0", 900), 12);
  });

  it("倒地、冰凍不呼吸；關掉待機時全員站好（小動作換回站好的貼圖）", () => {
    const s = scene(3);
    s.draws.set("npc:1", { ...s.draws.get("npc:1")!, statusIds: ["prone"] });
    s.draws.set("npc:2", { ...s.draws.get("npc:2")!, statusIds: ["frozen"] });
    const m = new IdleMotion();
    m.tick(500, s.units, s.draws, () => undefined);
    expect(bodyOf(s.units.get("npc:1")!).scale.y).toBe(0.5);
    expect(bodyOf(s.units.get("npc:2")!).scale.y).toBe(0.5);
    m.enabled = false;
    m.tick(16, s.units, s.draws, () => undefined);
    expect(bodyOf(s.units.get("npc:0")!).scale.y).toBe(0.5);
  });

  it("小動作只在姿勢變了才換貼圖（每人每次小動作最多 2×4 次），放下時換回 null", () => {
    const s = scene(1);
    const m = new IdleMotion();
    const calls: Array<InkPose | null> = [];
    const { every, offset } = fidgetSchedule("npc:0");
    let frames = 0;
    for (let ms = 0; ms < offset + every + FIDGET_MS + 100; ms += 16) {
      m.tick(16, s.units, s.draws, (_id, _s, p) => calls.push(p));
      frames += 1;
    }
    expect(frames).toBeGreaterThan(400);
    expect(calls.length).toBeGreaterThan(0);
    expect(calls.length).toBeLessThanOrEqual(2 * (2 * FIDGET_LEVELS));
    expect(calls[calls.length - 1]).toBeNull();
  });
});
