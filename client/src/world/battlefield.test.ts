import { describe, expect, it } from "vitest";
import type { WorldEncounterView, WorldView } from "../api/types";
import { TILE_SIZE } from "../battle/geometry";
import { battleFrame, battlefieldLine } from "./battlefield";
import { followCamera, frameCamera, tileViewRect } from "./camera";

const rect = { field_map: "ferry_steps", x: 4, y: 3, width: 12, height: 12 };
const grid = { width: 24, height: 18, tiles: Array.from({ length: 24 * 18 }, () => ({ height: 0 })) };
const STAGE = { width: 1008, height: 556 };

function view(encounter: Partial<WorldEncounterView> | null, mapId = "ferry_steps"): WorldView {
  return { encounter: encounter as WorldEncounterView | null, field: { map_id: mapId } } as unknown as WorldView;
}

describe("battleFrame", () => {
  it("框住目前這張實地地圖上切出的戰場", () => {
    expect(battleFrame(view({ battlefield: rect }))).toEqual({ x: 4, y: 3, width: 12, height: 12 });
  });

  it("沒有遭遇、退回模板、或戰場不在這張圖上：跟隨主角", () => {
    expect(battleFrame(view(null))).toBeNull();
    expect(battleFrame(view({ battlefield: null, battlefield_fallback_zh: "站位放不下" }))).toBeNull();
    expect(battleFrame(view({ battlefield: rect }, "mist_ferry"))).toBeNull();
  });

  it("frameCamera 把 12×12 戰場（四周各半格）整個放進畫面", () => {
    const frame = battleFrame(view({ battlefield: rect }))!;
    const cam = frameCamera(STAGE, grid, frame);
    expect(cam.scale).toBeGreaterThanOrEqual(0.5);
    expect(cam.scale).toBeLessThanOrEqual(1);
    expect(cam.scale * (12 + 1) * TILE_SIZE).toBeLessThanOrEqual(STAGE.height + 0.01);
    const tl = tileViewRect(grid, { x: frame.x, y: frame.y }, cam);
    const br = tileViewRect(grid, { x: frame.x + 11, y: frame.y + 11 }, cam);
    expect(tl.left).toBeGreaterThanOrEqual(0);
    expect(tl.top).toBeGreaterThanOrEqual(0);
    expect(br.left + br.width).toBeLessThanOrEqual(STAGE.width + 0.01);
    expect(br.top + br.height).toBeLessThanOrEqual(STAGE.height + 0.01);
  });

  it("遭遇結束（battlefield 不見）：鏡頭回到跟隨", () => {
    const after = battleFrame(view(null));
    expect(after).toBeNull();
    const cam = followCamera(STAGE, grid, { x: 10, y: 9 });
    expect(cam.scale).toBe(1);
  });
});

describe("battlefieldLine", () => {
  it("說明就地開打或退回模板的原因", () => {
    expect(battlefieldLine({ battlefield: rect } as WorldEncounterView)).toContain("就地開打（12×12");
    expect(battlefieldLine({ battlefield: null, battlefield_fallback_zh: "站位放不下" } as WorldEncounterView)).toBe(
      "改用這裡原本的戰場：站位放不下",
    );
    expect(battlefieldLine({ battlefield: null } as WorldEncounterView)).toBeNull();
  });
});
