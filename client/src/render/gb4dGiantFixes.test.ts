// GB-4d：巨型頭目演出小修（美術 GB-4c 待決 5、6；docs/art/GB-4b驗收.md 末節）。
// 5：第 2 階段熔心吸氣播吸氣變體 `inhale`（吸氣火星往核心收＋核心蓄力光），不畫熔岩柱；第 1、3 階段與 1 格灰燼之心照舊。
// 6：800 寬噴口破的黑煙，煙頂壓在頭頂 HUD 下緣以下 ≥ 2 畫面 px；1600 照舊。
import { describe, expect, it } from "vitest";
import type { PartView, Pos, UnitView } from "../api/types";
import { unitDrawOf, type UnitDraw } from "../battle/drawModel";
import { smallView, unit } from "../battle/testFixtures";
import dolls from "./fixtures/unitDolls.json";
import { giantHudLowY, giantSmokeCeil, SMOKE_HUD_GAP_PX } from "./partBreakFx";
import { bossClipOf, bossPlan } from "./qBoss";
import { GG, GIANT_ANCHOR_DY, giantBreakFx, giantClipOf, giantLookOf, giantStateFor, INHALE_KF, smokeRise, smokeY, type GiantState } from "./qBossGiant";
import { bossHudDy, hpBoxOf } from "./unitSprite";

const P = (x: number, y: number): Pos => ({ x, y });
const tilesOf = (cx: number, cy: number): Pos[] => [-1, 0, 1].flatMap((dy) => [-1, 0, 1].map((dx) => P(cx + dx, cy + dy)));
const part = (id: string, name: string, tiles: Pos[], over: Partial<PartView> = {}): PartView => ({ id, name_zh: name, hp: 32, max_hp: 32, broken: false, exposed: true, reach: "any", break_lines_zh: [], tiles, ...over });

function heartDraw(over: Partial<UnitView> = {}): UnitDraw {
  const u = unit("heart", "enemy", 5, 3, {
    template_id: "ashen_heart",
    tags: ["boss", "elite"],
    facing: "south",
    doll_look: (dolls as Record<string, unknown>)["ashen_heart"] as UnitView["doll_look"],
    boss_phase: { index: 2, total: 3, name_zh: "x" } as UnitView["boss_phase"],
    footprint: 3,
    tiles: tilesOf(5, 3),
    parts: [part("core", "核心", [P(5, 3)]), part("shell_seam", "殼縫", [P(4, 3), P(6, 3)]), part("vent", "熔岩噴口", [P(4, 2), P(5, 2), P(6, 2)], { broken: true, hp: 0 })],
    ...over,
  });
  return unitDrawOf(smallView({ width: 12, height: 12, units: [u] }), u, "", null, "unit_0001");
}

describe("待決 5：第 2 階段熔心吸氣＝吸氣變體，不畫熔岩柱", () => {
  const p2 = giantLookOf({ phase: 2, statusIds: [] });
  const p1 = giantLookOf({ phase: 1, statusIds: ["molten_shell"] });
  const p3 = giantLookOf({ phase: 3, statusIds: [] });

  it("片段對應：只有第 2 階段的範圍片段換成 inhale", () => {
    expect(giantClipOf(p2, "atk:@area")).toBe("inhale");
    expect(giantClipOf(p1, "atk:@area")).toBe("spout");
    expect(giantClipOf(p3, "atk:@area")).toBe("spout");
    for (const c of ["atk:@cast", "hit", "death", "idle", "move"]) expect(giantClipOf(p2, c)).toBe(bossClipOf({ id: "ah", phase: 2 }, c));
  });

  it("整段沒有熔岩柱；吸氣火星整段都在、蓄力光越吸越亮；時間軸同 spout", () => {
    let maxCharge = 0;
    for (let i = 0; i <= 20; i++) {
      const u = i / 20;
      const { st } = giantStateFor(p2, { clip: "atk:@area", u });
      expect(st.spout ?? 0).toBe(0);
      expect(st.t).toBe((bossPlan("ah", "spout", u, { phase: 2 }).st as { t: number }).t);
      if (u >= 0.15 && u <= 0.8) expect(st.inhale).toBeGreaterThan(0.9);
      maxCharge = Math.max(maxCharge, st.charge ?? 0);
    }
    expect(maxCharge).toBeCloseTo(1, 6);
    expect(giantStateFor(p2, { clip: "atk:@area", u: 0.3 }).st.charge!).toBeLessThan(giantStateFor(p2, { clip: "atk:@area", u: 0.75 }).st.charge!);
    expect(INHALE_KF.inhale[0]).toEqual([0, 0]);
  });

  it("減少動態：不吸、不蓄力（同 spout 的規矩）", () => {
    const { st } = giantStateFor(p2, { clip: "atk:@area", u: 0.6, reduce: true });
    expect([st.inhale, st.charge, st.spout]).toEqual([undefined, undefined, undefined]);
  });

  it("第 1、3 階段照舊噴熔岩柱（參數同 qBoss 灰燼之心 spout）", () => {
    for (const look of [p1, p3]) {
      const { st } = giantStateFor(look, { clip: "atk:@area", u: 0.6 });
      const ref = bossPlan("ah", "spout", 0.6, { phase: look.phase }).st as { inhale: number; spout: number };
      expect([st.inhale, st.spout]).toEqual([ref.inhale, ref.spout]);
      expect(st.spout).toBeGreaterThan(0.5);
    }
  });
});

/** 記錄黑煙（`#2c272b`）每個圓的上緣；其他呼叫一律吃掉（vitest 沒有 Canvas，`layer` 直接畫在這個 ctx 上）。 */
function smokeTops(st: GiantState, board: number, ceil?: number): number[] {
  const tops: number[] = [];
  const stack: Array<[number, number]> = [];
  let off: [number, number] = [0, 0];
  const rec: Record<string, unknown> = { fillStyle: "", strokeStyle: "", globalAlpha: 1, lineWidth: 1, font: "" };
  const ctx = new Proxy(rec, {
    get(t, k: string) {
      if (k === "getTransform") return undefined;
      if (k in t) return t[k];
      if (k === "save") return () => stack.push([...off]);
      if (k === "restore") return () => (off = stack.pop() ?? [0, 0]);
      if (k === "translate") return (x: number, y: number) => (off = [off[0] + x, off[1] + y]);
      if (k === "arc")
        return (_x: number, y: number, r: number) => {
          if (t.fillStyle === "#2c272b") tops.push(off[1] + y - r);
        };
      return () => undefined;
    },
    set(t, k: string, v) {
      t[k] = v;
      return true;
    },
  });
  giantBreakFx(ctx as never, st, board, ceil);
  return tops;
}

describe("待決 6：800 噴口破的黑煙壓在頭頂 HUD 下緣以下", () => {
  const d = heartDraw();
  const vent = (k: number): GiantState => ({ phase: 2, fx: { part: "vent", k, side: 1 } });

  it("HUD 下緣：至少是 HP 條＋部位條的下緣；800 部位條加高、比 1600 低", () => {
    const hp = hpBoxOf(d)!;
    expect(giantHudLowY(d, 1.308)!).toBeGreaterThanOrEqual(hp.b + bossHudDy(d));
    expect(giantHudLowY(d, 0.531)!).toBeGreaterThan(giantHudLowY(d, 1.308)!);
    expect(giantHudLowY({ ...d, noBar: true }, 0.531)).toBeNull();
  });

  it("只 800 壓（1600 照舊 undefined）；上限＝HUD 下緣往下 2 畫面 px（換回錨點座標）", () => {
    expect(giantSmokeCeil(d, 1.308)).toBeUndefined();
    expect(giantSmokeCeil(d, 1)).toBeUndefined();
    const c = giantSmokeCeil(d, 0.531)!;
    expect(c).toBeCloseTo(giantHudLowY(d, 0.531)! - GIANT_ANCHOR_DY + SMOKE_HUD_GAP_PX / 0.531, 9);
  });

  it("800 第 3、4 格：原本煙頂高過上限（會碰 HUD）；壓了以後每團煙（含外框）都在上限以下", () => {
    const c = giantSmokeCeil(d, 0.531)!;
    expect(Math.min(...smokeTops(vent(3), 0.531))).toBeLessThan(c); // 修之前會碰到
    for (const k of [2, 3]) {
      const tops = smokeTops(vent(k), 0.531, c);
      expect(tops.length).toBeGreaterThan(0);
      expect(Math.min(...tops) - 0.6 * GG).toBeGreaterThanOrEqual(c - 1e-9);
    }
  });

  it("1600 不給上限＝和以前一模一樣；smokeY 只往下推", () => {
    expect(smokeTops(vent(3), 1.308, giantSmokeCeil(d, 1.308))).toEqual(smokeTops(vent(3), 1.308));
    expect(smokeY(-150, 10, undefined)).toBe(-150);
    expect(smokeY(-150, 10, -200)).toBe(-150);
    expect(smokeY(-190, 10, -170)).toBeCloseTo(-170 + smokeRise(10), 9);
  });
});
