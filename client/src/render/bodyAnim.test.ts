// Phase 6M-3：異形受擊白閃只閃剪影（像素測試）；倒地狀態持續躺著（重畫後也躺著）；動畫只換小人的貼圖，底圈、血條不動。
import { Texture } from "pixi.js";
import { describe, expect, it } from "vitest";
import type { BattleView } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { tile, unit } from "../battle/testFixtures";
import type { ArtTextures } from "./artTextures";
import { creaturePoseAt, creaturePoseKey, quantizeCreaturePose, whiteSilhouette } from "./creaturePose";
import { drawCreature, resolveCreature } from "./inkCreature";
import type { InkPose } from "./inkPose";
import { poseKey, PRONE_POSE, proneBody } from "./motionClips";
import { BODY_LABEL, bodyNodes, bodyTexture, buildUnitSprite, FEET, isProne, Pulses } from "./unitSprite";

describe("6M-3：異形受擊白閃只閃剪影（不能整格變白）", () => {
  /** 16×16 的 RGBA：中間 6×6 是不透明的紅色身體、邊緣一圈半透明，其他透明。 */
  function sample(): Uint8ClampedArray {
    const d = new Uint8ClampedArray(16 * 16 * 4);
    for (let y = 0; y < 16; y++) {
      for (let x = 0; x < 16; x++) {
        const i = (y * 16 + x) * 4;
        const inside = x >= 5 && x < 11 && y >= 5 && y < 11;
        const edge = !inside && x >= 4 && x < 12 && y >= 4 && y < 12;
        d.set(inside ? [200, 40, 30, 255] : edge ? [90, 20, 10, 128] : [0, 0, 0, 0], i);
      }
    }
    return d;
  }

  it("剪影外（透明）的像素維持透明；剪影內變白、不透明度 × flash", () => {
    const src = sample();
    const out = sample();
    whiteSilhouette(out, 0.85);
    let inside = 0;
    for (let i = 0; i < src.length; i += 4) {
      if (src[i + 3] === 0) {
        expect(out[i + 3], `像素 ${i / 4}`).toBe(0); // 剪影外完全不變白
        continue;
      }
      inside += 1;
      expect([out[i], out[i + 1], out[i + 2]]).toEqual([255, 255, 255]);
      expect(out[i + 3]).toBe(Math.round(src[i + 3]! * 0.85));
    }
    expect(inside).toBe(64);
  });

  it("疊回角色上：剪影外的像素和原本一樣（source-over 疊透明像素不改變底圖）", () => {
    const base = sample();
    const top = sample();
    whiteSilhouette(top, 0.85);
    // 照 Canvas source-over（非預乘）把 top 疊到 base
    const over = new Uint8ClampedArray(base.length);
    for (let i = 0; i < base.length; i += 4) {
      const as = top[i + 3]! / 255;
      const ad = base[i + 3]! / 255;
      const ao = as + ad * (1 - as);
      over[i + 3] = Math.round(ao * 255);
      for (let c = 0; c < 3; c++) over[i + c] = ao === 0 ? 0 : Math.round((top[i + c]! * as + base[i + c]! * ad * (1 - as)) / ao);
    }
    let brighter = 0;
    for (let i = 0; i < base.length; i += 4) {
      if (base[i + 3] === 0) {
        expect(over[i + 3]).toBe(0);
        continue;
      }
      if (over[i]! > base[i]!) brighter += 1;
    }
    expect(brighter).toBe(64); // 身體每個像素都被閃白
  });

  it("flash 0：剪影完全透明（不疊任何東西）", () => {
    const out = sample();
    whiteSilhouette(out, 0);
    for (let i = 3; i < out.length; i += 4) expect(out[i]).toBe(0);
  });

  it("閃白用的身體不畫地上的影子（ground ＝ false），也不畫整格的方塊", () => {
    const calls: string[] = [];
    const ctx = new Proxy({} as Record<string, unknown>, {
      get(t, p: string) {
        if (p in t) return t[p];
        return (...a: unknown[]) => void calls.push(`${p}(${a.map((x) => (typeof x === "number" ? x.toFixed(2) : String(x))).join(",")})`);
      },
      set(t, p: string, v) {
        t[p] = v;
        calls.push(`${p}=${String(v)}`);
        return true;
      },
    }) as unknown as CanvasRenderingContext2D;
    const r = resolveCreature({ look: { body: "hound", material: "fur" } });
    drawCreature(ctx, r, { flash: 0.85 }, false);
    const noGround = [...calls];
    calls.length = 0;
    drawCreature(ctx, r, { flash: 0.85 });
    expect(calls.length).toBeGreaterThan(noGround.length); // 有影子時多畫一些
    expect(noGround.some((c) => c.startsWith("fillRect"))).toBe(false);
  });

  it("受擊片段開頭白閃最亮、之後消失；快取鍵含白閃強度", () => {
    const start = quantizeCreaturePose(creaturePoseAt("hit", 0));
    const late = quantizeCreaturePose(creaturePoseAt("hit", 300));
    expect(start.flash).toBeGreaterThan(0.8);
    expect(late.flash ?? 0).toBe(0);
    expect(creaturePoseKey(start)).toContain("flash");
    expect(creaturePoseKey({})).toBe("");
  });
});

describe("6M-3：倒地狀態持續躺著、動畫只動小人", () => {
  const view = (over: Partial<ReturnType<typeof unit>>): BattleView =>
    ({ team: "ally", map_id: "m", map_name_zh: "m", width: 2, height: 1, tiles: [tile(0, 0), tile(1, 0)], objects: [], units: [unit("unit_0001", "ally", 0, 0, over)], traps: [], turn_order: ["unit_0001"], active_unit: "unit_0001", round: 1, max_rounds: 9, weather_id: null, weather_name_zh: null, objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null, source_wells: [], zones: [], runes: [] }) as unknown as BattleView;
  const unitDraw = (over: Partial<ReturnType<typeof unit>>): UnitDraw => buildDrawModel(view(over), "unit_0001").units[0]!;
  const prone = [{ status_id: "prone", remaining: 1, source_id: null, amount: null, charge_tiles: [], cost_status: false }] as unknown as ReturnType<typeof unit>["statuses"];

  function fakeArt(): { art: ArtTextures; poses: Array<InkPose | null> } {
    const poses: Array<InkPose | null> = [];
    const art = {
      figure: (_s: unknown, _f: unknown, _d: unknown, pose: InkPose | null = null) => (poses.push(pose), Texture.WHITE),
      creature: () => Texture.WHITE,
      summon: () => Texture.WHITE,
      dollFx: () => null,
    } as unknown as ArtTextures;
    return { art, poses };
  }

  it("沒有倒地狀態：小人站著、沒給姿勢（快照不變）", () => {
    const { art, poses } = fakeArt();
    const u = unitDraw({ template_id: "hero_fighter", facing: "east" });
    expect(isProne(u)).toBe(false);
    const c = buildUnitSprite(art, new Pulses(), u);
    const body = c.children.find((n) => n.label === BODY_LABEL)!;
    expect(body.rotation).toBe(0);
    expect(body.y).toBe(FEET);
    expect(poses).toEqual([null]);
  });

  it("倒地狀態：重畫場景時小人照滑倒最後一格躺著（骨架躺著的姿勢、以腳底為軸轉倒），底圈與血條不轉", () => {
    for (const facing of ["east", "west", "south", "north"] as const) {
      const { art, poses } = fakeArt();
      const u = unitDraw({ template_id: "hero_fighter", facing, statuses: prone });
      expect(isProne(u)).toBe(true);
      const c = buildUnitSprite(art, new Pulses(), u);
      const lie = proneBody(1, facing);
      const body = c.children.find((n) => n.label === BODY_LABEL)!;
      expect(body.rotation, facing).toBeCloseTo(lie.rotation, 9);
      expect(body.x, facing).toBeCloseTo(lie.x, 9);
      expect(body.y, facing).toBeCloseTo(FEET + lie.y, 9);
      expect(poseKey(poses[0]!)).toBe(poseKey(PRONE_POSE));
      for (const n of c.children) if (!bodyNodes(c).includes(n)) expect(n.rotation, `${facing} ${n.label}`).toBe(0);
    }
  });

  it("HP 歸零的倒下（downed）照舊橫躺貼圖，不套倒地狀態", () => {
    const { art, poses } = fakeArt();
    const u = unitDraw({ template_id: "hero_fighter", facing: "east", statuses: prone, hp: 0, downed: true });
    expect(u.downed).toBe(true);
    expect(isProne(u)).toBe(false);
    bodyTexture(art, u, {});
    expect(poses).toEqual([null]); // 照舊的倒下貼圖（drawFigurePose 的 downed），不給躺著的骨架姿勢
  });

  it("動畫的貼圖：紙娃娃照給的姿勢；倒地狀態沒給姿勢時照躺著的姿勢", () => {
    const { art, poses } = fakeArt();
    const walking: InkPose = { hipN: 0.5 };
    bodyTexture(art, unitDraw({ template_id: "hero_fighter" }), { pose: walking });
    bodyTexture(art, unitDraw({ template_id: "hero_fighter", statuses: prone }), {});
    bodyTexture(art, unitDraw({ template_id: "hero_fighter" }), {});
    expect(poses[0]).toEqual(walking);
    expect(poseKey(poses[1]!)).toBe(poseKey(PRONE_POSE));
    expect(poses[2]).toBeNull();
  });
});
