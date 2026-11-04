// Phase 6M-3：走路、跑步、潛行片段的時間軸與週期；高低差走／跳判定；倒地持續躺著的姿勢；貼圖快取鍵的量化。
import { describe, expect, it } from "vitest";
import { RAISE } from "../battle/elevation";
import { TILE_SIZE } from "../battle/geometry";
import { pz } from "./inkPose";
import {
  climbMode,
  SKID_LEAN,
  skidBody,
  stumbleTilt,
  DUST_FROM,
  GAITS,
  gaitPhaseAt,
  gaitPose,
  gaitPoseAt,
  JUMP_BASE,
  JUMP_DOWN,
  legFrame,
  PHASE_STEPS,
  poseKey,
  PRONE_ANGLE,
  PRONE_POSE,
  proneBody,
  quantizePhase,
  quantizePose,
  STEP_RISE_FROM,
  tilePhase,
  type Gait,
} from "./motionClips";

const GAIT_LIST: Gait[] = ["walk", "run", "sneak"];
const close = (a: number, b: number, eps = 1e-9) => Math.abs(a - b) < eps;

describe("6M-3：走路、跑步、潛行片段（時間的純函式）", () => {
  it("規格：格子 48、每級抬高 6", () => {
    expect(TILE_SIZE).toBe(48);
    expect(RAISE).toBe(6);
  });

  it("一步約 0.45 秒；跑步約 1.6 倍速、潛行約 0.6 倍速；一個循環兩步", () => {
    expect(GAITS.walk.stepMs).toBe(450);
    expect(GAITS.walk.stepMs / GAITS.run.stepMs).toBeCloseTo(1.6, 9);
    expect(GAITS.walk.stepMs / GAITS.sneak.stepMs).toBeCloseTo(0.6, 9);
    for (const g of GAIT_LIST) {
      expect(gaitPhaseAt(g, GAITS[g].stepMs)).toBeCloseTo(Math.PI, 9); // 一步 ＝ 半個循環
      // 週期 ＝ 兩步：任何時間加上一個週期，姿勢完全相同
      for (const ms of [0, 37, 120, 333, 777]) {
        const a = gaitPoseAt(g, ms);
        const b = gaitPoseAt(g, ms + 2 * GAITS[g].stepMs);
        for (const k of Object.keys(a) as Array<keyof typeof a>) expect(close(pz(a, k), pz(b, k), 1e-9), `${g} ${ms} ${k}`).toBe(true);
      }
    }
  });

  it("同樣的時間一定得到同樣的姿勢（確定性）", () => {
    for (const g of GAIT_LIST) expect(gaitPoseAt(g, 512)).toEqual(gaitPoseAt(g, 512));
  });

  it("走路：側面髖 ±0.5、手臂反向擺、起伏 1.2；正面背面抬腳 3.2、手擺 1.6", () => {
    const samples = Array.from({ length: 64 }, (_, i) => gaitPose((i / 64) * Math.PI * 2, "walk"));
    const max = (k: Parameters<typeof pz>[1]) => Math.max(...samples.map((p) => pz(p, k)));
    const min = (k: Parameters<typeof pz>[1]) => Math.min(...samples.map((p) => pz(p, k)));
    expect(max("hipN")).toBeCloseTo(0.5, 2);
    expect(min("hipN")).toBeCloseTo(-0.5, 2);
    expect(min("bob")).toBeCloseTo(-1.2, 2);
    expect(max("liftL")).toBeCloseTo(3.2, 2);
    expect(max("armL")).toBeCloseTo(1.6, 2);
    // 手臂和同側的腿反向擺
    const step = gaitPose(Math.PI / 2, "walk");
    expect(pz(step, "hipN")).toBeGreaterThan(0);
    expect(pz(step, "arm")).toBeLessThan(0);
    // 左右腳交替：一個循環內 liftL、liftR 輪流抬起，不會同時抬
    for (const p of samples) expect(pz(p, "liftL") > 0 && pz(p, "liftR") > 0).toBe(false);
  });

  it("跑步：擺幅 0.75、前傾 0.2、手肘彎、起伏 2.2；潛行：擺幅 0.35、蹲低 2.5、前傾 0.3、膝多彎 0.5、半透明", () => {
    const run = gaitPose(Math.PI / 2, "run");
    expect(pz(run, "hipN")).toBeCloseTo(0.75, 9);
    expect(pz(run, "lean")).toBe(0.2);
    expect(pz(run, "elbow")).toBeLessThan(0);
    expect(pz(gaitPose(0, "run"), "bob")).toBeCloseTo(-2.2, 9);
    const sneak = gaitPose(Math.PI / 2, "sneak");
    const walk = gaitPose(Math.PI / 2, "walk");
    expect(pz(sneak, "hipN")).toBeCloseTo(0.35, 9);
    expect(pz(sneak, "lean")).toBe(0.3);
    expect(pz(sneak, "bob") - pz(walk, "bob")).toBeCloseTo(2.5, 9);
    expect(pz(sneak, "kneeN") - pz(walk, "kneeN")).toBeCloseTo(0.5, 9);
    expect(GAITS.sneak.alpha).toBeLessThan(1);
    expect(GAITS.walk.alpha).toBe(1);
    expect(GAITS.run.alpha).toBe(1);
  });

  it("逐格走：一格一步，相位接續（第二格換另一隻腳）", () => {
    expect(tilePhase(0, 0)).toBe(0);
    expect(tilePhase(0, 1)).toBeCloseTo(Math.PI, 9);
    expect(tilePhase(1, 0.5)).toBeCloseTo(1.5 * Math.PI, 9);
    const first = legFrame(0.5, 0, 0, "walk", 0).pose;
    const second = legFrame(0.5, 0, 0, "walk", 1).pose;
    expect(pz(first, "hipN")).toBeGreaterThan(0.4);
    expect(pz(second, "hipN")).toBeLessThan(-0.4);
  });
});

describe("6M-3：高低差（差一級用走的、兩級以上用跳的）", () => {
  it("走／跳判定", () => {
    expect(climbMode(0, 0)).toBe("walk");
    expect(climbMode(0, 1)).toBe("walk");
    expect(climbMode(2, 1)).toBe("walk");
    expect(climbMode(0, 2)).toBe("jump");
    expect(climbMode(3, 1)).toBe("jump");
    expect(climbMode(1, 4)).toBe("jump");
  });

  it("同高：腳底高度不變、不離地", () => {
    for (const u of [0, 0.3, 0.7, 1]) {
      const f = legFrame(u, 1, 1);
      expect(f.mode).toBe("walk");
      expect(f.lift).toBe(RAISE);
      expect(f.air).toBe(0);
    }
  });

  it("上一級：前半段抬腳（髖、膝多抬），後半段身體才升 6，腳踩在格子上", () => {
    expect(legFrame(0, 0, 1).lift).toBe(0);
    expect(legFrame(STEP_RISE_FROM, 0, 1).lift).toBe(0);
    expect(legFrame(1, 0, 1).lift).toBeCloseTo(RAISE, 9);
    const mid = legFrame(0.7, 0, 1).lift;
    expect(mid).toBeGreaterThan(0);
    expect(mid).toBeLessThan(RAISE);
    const up = legFrame(0.3, 0, 1).pose;
    const flat = legFrame(0.3, 0, 0).pose;
    expect(pz(up, "hipN") - pz(flat, "hipN")).toBeGreaterThan(0.25);
    expect(pz(up, "kneeN") - pz(flat, "kneeN")).toBeGreaterThan(0.45);
    expect(legFrame(0.5, 0, 1).air).toBe(0);
  });

  it("下一級：後半段身體降 6，落地時起伏多 1", () => {
    expect(legFrame(0.2, 1, 0).lift).toBe(RAISE);
    expect(legFrame(1, 1, 0).lift).toBeCloseTo(0, 9);
    const land = legFrame(0.875, 1, 0, "walk", 0).pose;
    const flat = legFrame(0.875, 0, 0, "walk", 0).pose;
    expect(pz(land, "bob") - pz(flat, "bob")).toBeCloseTo(1, 1);
  });

  it("兩級以上：跳躍拋物線高度 14＋級差×6，往下跳 0.7 倍；落地揚塵；終點踩在高台上", () => {
    const up = legFrame(0.5, 0, 2);
    expect(up.mode).toBe("jump");
    expect(up.air).toBeCloseTo(JUMP_BASE + 2 * RAISE, 9);
    expect(legFrame(0.5, 0, 3).air).toBeCloseTo(JUMP_BASE + 3 * RAISE, 9);
    expect(legFrame(0.5, 2, 0).air).toBeCloseTo((JUMP_BASE + 2 * RAISE) * JUMP_DOWN, 9);
    expect(legFrame(0, 0, 2).air).toBe(0);
    expect(legFrame(1, 0, 2).air).toBeCloseTo(0, 9);
    expect(legFrame(1, 0, 2).lift).toBeCloseTo(2 * RAISE, 9);
    expect(legFrame(0.5, 0, 2).dust).toBe(0);
    expect(legFrame(DUST_FROM + 0.05, 0, 2).dust).toBeGreaterThan(0);
    expect(legFrame(DUST_FROM + 0.05, 0, 1).dust).toBe(0); // 走上去不揚塵
    // 跳的時候收腿
    expect(pz(up.pose, "kneeN")).toBeGreaterThan(1);
  });
});

describe("6M-3：倒地（prone）持續躺著", () => {
  it("t ＝ 0 站著、t ＝ 1 躺著；往東走往西倒（逆時針）、往西走往東倒、南北往東側倒", () => {
    expect(proneBody(0, "east").rotation).toBe(-0);
    expect(proneBody(1, "east").rotation).toBeCloseTo(-PRONE_ANGLE, 9);
    expect(proneBody(1, "west").rotation).toBeCloseTo(PRONE_ANGLE, 9);
    expect(proneBody(1, "south").rotation).toBeCloseTo(PRONE_ANGLE, 9);
    expect(proneBody(1, "north").rotation).toBeCloseTo(PRONE_ANGLE, 9);
    expect(proneBody(1, "east").x).toBeGreaterThan(0); // 腳往前溜
    expect(proneBody(1, "west").x).toBeLessThan(0);
  });

  it("躺著的骨架姿勢：最後一格就是 PRONE_POSE（量化後），從走路姿勢內插過去", () => {
    expect(proneBody(1, "east").pose).toEqual(quantizePose(PRONE_POSE));
    const walking = gaitPose(Math.PI / 2);
    expect(poseKey(proneBody(0, "east", walking).pose)).toBe(poseKey(walking));
  });
});

describe("6M-3：貼圖快取（姿勢量化後放進快取鍵）", () => {
  it("相位量化到每循環 16 級；一個循環最多 16 種走路姿勢", () => {
    expect(PHASE_STEPS).toBe(16);
    const keys = new Set<string>();
    for (let i = 0; i < 400; i++) keys.add(poseKey(gaitPose(quantizePhase((i / 400) * Math.PI * 2))));
    expect(keys.size).toBeLessThanOrEqual(16);
    expect(keys.size).toBeGreaterThan(8);
  });

  it("量化到 0.02；鍵固定欄位順序、0 不寫、沒有 -0", () => {
    expect(quantizePose({ hipN: 0.501, bob: -0.0001 })).toEqual({ hipN: 0.5, bob: 0 });
    expect(poseKey({ hipN: 0.501, bob: -0.0001 })).toBe("hipN0.5");
    expect(poseKey({ bob: 1, hipN: 0.2 })).toBe(poseKey({ hipN: 0.2, bob: 1 }));
    expect(poseKey({})).toBe("");
  });

  it("逐格走一整格（任意時間取樣）用到的貼圖數有上限：每格最多 8 張", () => {
    for (const g of GAIT_LIST) {
      const keys = new Set<string>();
      for (let i = 0; i <= 120; i++) keys.add(poseKey(legFrame(i / 120, 0, 0, g, 0).pose));
      expect(keys.size, g).toBeLessThanOrEqual(9);
    }
  });
});

describe("冰面滑行與踉蹌（#123）", () => {
  it("滑行往面向的反方向仰（同倒地方向），姿勢固定", () => {
    expect(skidBody("east").rotation).toBeCloseTo(-SKID_LEAN);
    expect(skidBody("west").rotation).toBeCloseTo(SKID_LEAN);
    expect(skidBody("south").pose).toEqual(skidBody("north").pose);
  });

  it("踉蹌：開始與結束回正，中間左右晃", () => {
    expect(stumbleTilt(0)).toBeCloseTo(0);
    expect(stumbleTilt(1)).toBeCloseTo(0);
    expect(Math.abs(stumbleTilt(0.125))).toBeGreaterThan(0.05);
  });
});
