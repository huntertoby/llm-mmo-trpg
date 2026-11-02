// UI-T1 試玩小修的回歸測試。
import { describe, expect, it } from "vitest";
import { DOLL_SCALE, SUMMON_FOOT_Y, SUMMON_SCALE } from "../render/paperdoll";
import { UNIT_HEADROOM } from "./elevation";
import { feedbackFor } from "./feedback";
import { TILE_SIZE } from "./geometry";

describe("畫布上方預留單位頭頂（最上排頭被切）", () => {
  it("UNIT_HEADROOM 蓋得住紙娃娃尖帽與非人形召喚物畫布頂", () => {
    const T = TILE_SIZE;
    const feetBelowTileTop = T / 2 + T * 0.23; // unitSprite 的 feet ＝ 格子中心下方 0.23 格
    const dollHeadTop = 70 * (T / 52) * DOLL_SCALE; // paperdoll：C 畫風頭頂最高約 −70（尖帽）
    const summonTop = SUMMON_FOOT_Y * (T / 52) * SUMMON_SCALE;
    expect(UNIT_HEADROOM).toBeGreaterThanOrEqual(dollHeadTop - feetBelowTileTop);
    expect(UNIT_HEADROOM).toBeGreaterThanOrEqual(summonTop - feetBelowTileTop);
  });
});
import { skeletonLabel } from "./source";
import { smallView } from "./testFixtures";

describe("跑步的地圖回饋字樣", () => {
  it("unit_ran 在跑的人頭上跳「跑步 移動＋N」", () => {
    const items = feedbackFor([{ type: "unit_ran", unit_id: "unit_0001", bonus: 3, move_points: 6 }], smallView());
    expect(items).toEqual([{ kind: "float", pos: { x: 0, y: 0 }, text: "跑步 移動＋3", tone: "good", big: false, slot: 0 }]);
  });
});

describe("skeletonLabel（技能卡標題不重複種類字樣）", () => {
  it("骨架名與種類相同或以種類開頭時不顯示", () => {
    expect(skeletonLabel({ kind: "被動", skeleton_zh: "被動" })).toBe("");
    expect(skeletonLabel({ kind: "姿態", skeleton_zh: "姿態" })).toBe("");
    expect(skeletonLabel({ kind: "修正", skeleton_zh: "修正" })).toBe("");
    expect(skeletonLabel({ kind: "反應", skeleton_zh: "反應技" })).toBe("");
  });

  it("主動技能的骨架名照常顯示", () => {
    expect(skeletonLabel({ kind: "主動", skeleton_zh: "單體打擊" })).toBe("單體打擊");
    expect(skeletonLabel({ kind: "主動", skeleton_zh: "" })).toBe("");  });
});
