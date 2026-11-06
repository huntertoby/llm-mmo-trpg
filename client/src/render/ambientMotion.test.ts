// Phase 6N-10：NPC 小動作、環境動態、傷害數字的時間軸——確定性、錯開、量化（貼圖數有限）、減少動態。
import { Container, Sprite, Texture } from "pixi.js";
import { describe, expect, it } from "vitest";
import type { BattleView } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { tile, unit } from "../battle/testFixtures";
import { flagFrame, flagWave, flickerAt, FLAG_FRAMES, mistAt, mistCount, ripplesAt, swayAt, SWAY_LEAN, SWAY_SWING } from "./ambientAnim";
import { windOf, windStrength } from "./ambientModel";
import { AmbientLayer } from "./ambientLayer";
import { idleFrame } from "./idleClips";
import { IdleMotion } from "./idleMotion";
import type { InkPose } from "./inkPose";
import { npcFidgetAt, npcFidgetPick, npcIdleFrame, npcSchedule, NPC_FIDGETS, ROLE_FIDGETS, type NpcRole } from "./npcFidgets";
import { floatFrame, POP_SPAN } from "./uiAnim";
import { BODY_LABEL } from "./unitSprite";

const NPCS = ["npc_granny_du", "npc_shopkeeper_liu", "npc_smith_shi", "npc_daoist_qingya", "npc_acolyte_xiaolian", "npc_hunter_ayue"];

describe("6N-10：NPC 小動作", () => {
  it("每種身分 3～4 種小動作；鐵匠有搥打、掌櫃有擦桌子，一般 NPC 沒有職業動作", () => {
    for (const role of ["smith", "keeper", "town"] as NpcRole[]) {
      const kinds = new Set(ROLE_FIDGETS[role]);
      expect(kinds.size).toBeGreaterThanOrEqual(3);
      expect(kinds.size).toBeLessThanOrEqual(4);
    }
    expect(ROLE_FIDGETS.smith).toContain("hammer");
    expect(ROLE_FIDGETS.keeper).toContain("wipe");
    expect(ROLE_FIDGETS.town).not.toContain("hammer");
    expect(ROLE_FIDGETS.town).not.toContain("wipe");
  });

  it("挑哪一種用「地圖 ID:單位 ID:序號」的雜湊：同樣的輸入永遠一樣，換地圖可以不同", () => {
    for (const id of NPCS) {
      for (let n = 1; n < 20; n++) expect(npcFidgetPick("mist_ferry", id, "smith", n)).toBe(npcFidgetPick("mist_ferry", id, "smith", n));
    }
    const a = Array.from({ length: 30 }, (_, n) => npcFidgetPick("mist_ferry", "npc_smith_shi", "smith", n + 1));
    const b = Array.from({ length: 30 }, (_, n) => npcFidgetPick("mist_ferry_smithy", "npc_smith_shi", "smith", n + 1));
    expect(a).not.toEqual(b);
    // 30 次裡每一種都輪得到
    expect(new Set(a).size).toBe(new Set(ROLE_FIDGETS.smith).size);
  });

  it("每人 4～7 秒一次、錯開；同一刻不會全員一起動", () => {
    for (const id of NPCS) {
      const { every, offset } = npcSchedule(id);
      expect(every).toBeGreaterThanOrEqual(4000);
      expect(every).toBeLessThan(7000);
      expect(offset).toBeLessThan(every);
      expect(npcFidgetAt("m", id, "town", offset - 1)).toBeNull();
    }
    const schedules = new Set(NPCS.map((id) => npcSchedule(id).every));
    expect(schedules.size).toBeGreaterThan(1);
    for (let ms = 0; ms < 40000; ms += 200) {
      const busy = NPCS.filter((id) => npcFidgetAt("m", id, "keeper", ms) !== null).length;
      expect(busy).toBeLessThan(NPCS.length);
    }
  });

  it("搥打是循環：一次之內在舉高與搥下之間來回 3 趟；強度、來回都量化（每人貼圖有限）", () => {
    const keys = new Set<string>();
    let swings = 0;
    let last = -1;
    for (let ms = 0; ms < 120000; ms += 10) {
      const f = npcFidgetAt("mist_ferry_smithy", "npc_smith_shi", "smith", ms);
      if (f === null) {
        last = -1;
        continue;
      }
      keys.add(npcIdleFrame("mist_ferry_smithy", "npc_smith_shi", "smith", ms).key);
      if (f.id === "hammer" && f.swing === 1 && last !== 1) swings += 1;
      last = f.id === "hammer" ? f.swing : -1;
    }
    expect(swings).toBeGreaterThanOrEqual(3);
    expect(keys.size).toBeLessThanOrEqual(30);
    for (const k of keys) expect(k.startsWith("n:")).toBe(true);
  });

  it("姿勢是純函式：同一刻兩次算出來一模一樣；沒在動時 pose ＝ null（照站好的貼圖）", () => {
    for (let ms = 0; ms < 30000; ms += 33) {
      const a = npcIdleFrame("mist_ferry", "npc_shopkeeper_liu", "keeper", ms);
      const b = npcIdleFrame("mist_ferry", "npc_shopkeeper_liu", "keeper", ms);
      expect(a).toEqual(b);
      if (a.key === "") expect(a.pose).toBeNull();
      // 呼吸照 6M-4
      expect(a.scaleY).toBe(idleFrame("npc_shopkeeper_liu", ms).scaleY);
    }
    for (const def of Object.values(NPC_FIDGETS)) expect(def.ms).toBeLessThan(4000);
  });

  it("待機驅動：場景裡有身分的 NPC 用職業小動作，其他人照 6M-4；減少動態時全員站好、不呼吸", () => {
    const motion = new IdleMotion();
    motion.scene = { key: "mist_ferry_smithy", roles: { npc_smith_shi: "smith" }, fires: [] };
    const mk = (id: string) => {
      const c = new Container();
      const body = new Sprite(Texture.EMPTY);
      body.label = BODY_LABEL;
      c.addChild(body);
      return [id, c] as const;
    };
    const units = new Map([mk("npc_smith_shi"), mk("field_hero")]);
    const real = buildDrawModel(
      { team: "ally", map_id: "m", map_name_zh: "m", width: 2, height: 1, tiles: [tile(0, 0), tile(1, 0)], objects: [], units: [unit("unit_0001", "ally", 0, 0, { template_id: "hero_fighter" })], traps: [], turn_order: ["unit_0001"], active_unit: "unit_0001", round: 1, max_rounds: 9, weather_id: null, weather_name_zh: null, objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null, source_wells: [], zones: [], runes: [] } as unknown as BattleView,
      "unit_0001",
    ).units[0]!;
    const draws = new Map<string, UnitDraw>([...units.keys()].map((id) => [id, { ...real, id, statusIds: [] }]));
    const seen = new Map<string, Set<string>>();
    const set = (id: string, _s: Container, pose: InkPose | null) => {
      if (pose === null) return;
      const s = seen.get(id) ?? new Set();
      s.add(JSON.stringify(pose));
      seen.set(id, s);
    };
    for (let t = 0; t < 60000; t += 50) motion.tick(50, units, draws, set);
    motion.reduced = true;
    motion.clock = 0;
    const before = seen.get("npc_smith_shi")?.size ?? 0;
    // 鐵匠的姿勢比主角多（搥打是兩個姿勢來回），主角照 6M-4 只有張望、伸懶腰
    expect(before).toBeGreaterThan(seen.get("field_hero")?.size ?? 0);
    expect(seen.get("field_hero")?.size ?? 0).toBeGreaterThan(0);
    for (let t = 0; t < 20000; t += 50) motion.tick(50, units, draws, set);
    expect(seen.get("npc_smith_shi")?.size ?? 0).toBe(before);
    expect(units.get("npc_smith_shi")!.children[0]!.scale.y).toBe(1);
  });
});

describe("6N-10：環境動態", () => {
  it("風向、風力照場景鍵定（同一張圖永遠一樣）；有風的天氣擺得大", () => {
    expect(windOf("mist_ferry")).toBe(windOf("mist_ferry"));
    expect([1, -1]).toContain(windOf("x"));
    const keys = ["a", "b", "c", "d", "e", "f", "g", "h"].map(windOf);
    expect(new Set(keys).size).toBe(2);
    expect(windStrength("k", "blizzard")).toBeCloseTo(windStrength("k", "") + 0.4, 9);
  });

  it("草叢擺動：往下風傾、來回擺；幅度有上限；每叢相位不同", () => {
    const max = 1.4 * (SWAY_LEAN + SWAY_SWING) + 1e-9;
    let sum = 0;
    for (let ms = 0; ms < 2600 * 4; ms += 20) {
      const s = swayAt("m:3,4", ms, 1, 1);
      expect(Math.abs(s)).toBeLessThanOrEqual(max);
      sum += s;
      expect(swayAt("m:3,4", ms, -1, 1)).toBeCloseTo(-s, 12);
    }
    expect(sum).toBeGreaterThan(0); // 平均往下風
    expect(swayAt("m:3,4", 500, 1, 1)).not.toBe(swayAt("m:9,4", 500, 1, 1));
  });

  it("酒旗量化成 4 格（全圖共用 4 張貼圖）；旗桿那一邊不動", () => {
    const frames = new Set<number>();
    for (let ms = 0; ms < 5000; ms += 7) frames.add(flagFrame("f", ms, 0.8));
    expect([...frames].sort()).toEqual([0, 1, 2, 3]);
    for (let f = 0; f < FLAG_FRAMES; f++) expect(flagWave(f, 0)).toBeCloseTo(0, 12);
  });

  it("營火閃動、光暈呼吸：確定性、範圍合理；燈籠閃得輕", () => {
    for (let ms = 0; ms < 4000; ms += 13) {
      const a = flickerAt("fire", ms);
      expect(a).toEqual(flickerAt("fire", ms));
      expect(a.sy).toBeGreaterThan(0.8);
      expect(a.sy).toBeLessThan(1.2);
      expect(a.glow).toBeGreaterThan(0.25);
      expect(a.glow).toBeLessThan(0.75);
      const s = flickerAt("fire", ms, true);
      expect(Math.abs(s.sy - 1)).toBeLessThanOrEqual(Math.abs(a.sy - 1) + 1e-9);
    }
  });

  it("水波兩圈錯開半個週期；薄霧順著風漂、出圖從另一邊回來", () => {
    const [a, b] = ripplesAt("r", 700);
    expect(a!.scale).not.toBeCloseTo(b!.scale, 3);
    expect(mistCount(24, 18)).toBe(9);
    expect(mistCount(4, 4)).toBe(3);
    const x0 = mistAt("mist_ferry", 0, 0, 1, 24, 18).x;
    const x1 = mistAt("mist_ferry", 0, 1000, 1, 24, 18).x;
    const back = mistAt("mist_ferry", 0, 1000, -1, 24, 18).x;
    expect(x1 - x0).toBeGreaterThan(0);
    expect(back - x0).toBeLessThan(0);
    for (let ms = 0; ms < 600000; ms += 5000) {
      const w = mistAt("mist_ferry", 3, ms, 1, 24, 18);
      expect(w.x).toBeGreaterThanOrEqual(-2);
      expect(w.x).toBeLessThan(26);
    }
  });

  it("圖層：沒有 DOM 時不建節點也不壞；草叢以底邊為軸；減少動態時 tick 不動", () => {
    const layer = new AmbientLayer();
    layer.begin({ region: "cloud_ridge", look: "", width: 4, height: 4, tiles: [], objects: [], units: [], traps: [], auras: [], zones: [], runes: [], wells: [], markers: [] });
    const node = new Container();
    const sprite = new Sprite(Texture.EMPTY);
    node.addChild(sprite);
    layer.object(node, { x: 1, y: 1, kind: "grass", floor: false } as never);
    layer.object(new Container(), { x: 2, y: 1, kind: "crate", floor: false } as never);
    expect(layer.counts.grass).toBe(1);
    expect(sprite.anchor.y).toBe(1);
    layer.tick(500);
    const s1 = sprite.skew.x;
    expect(s1).not.toBe(0);
    layer.reduced = true;
    layer.tick(800);
    expect(sprite.skew.x).toBe(s1);
  });
});

describe("6N-10：傷害數字彈一下再淡出", () => {
  it("一開始小、彈過頭再落回；最後 30% 淡出；暴擊比較大", () => {
    expect(floatFrame(0, false).scale).toBeCloseTo(0.6, 9);
    let peak = 0;
    for (let p = 0; p <= POP_SPAN; p += 0.005) peak = Math.max(peak, floatFrame(p, false).scale);
    expect(peak).toBeGreaterThan(1.03);
    expect(floatFrame(0.5, false).scale).toBe(1);
    expect(floatFrame(0.5, true).scale).toBeGreaterThan(1);
    expect(floatFrame(0.6, false).alpha).toBe(1);
    expect(floatFrame(0.85, false).alpha).toBeCloseTo(0.5, 9);
    expect(floatFrame(1, false).alpha).toBeCloseTo(0, 9);
    expect(floatFrame(1, true).rise).toBeGreaterThan(floatFrame(1, false).rise);
  });

  it("減少動態：直接顯示（不彈、不飄、不淡），到時間收掉", () => {
    for (const p of [0, 0.1, 0.5, 0.9]) expect(floatFrame(p, false, true)).toEqual({ alpha: 1, rise: 0, scale: 1 });
    expect(floatFrame(1, false, true).alpha).toBe(0);
  });
});
