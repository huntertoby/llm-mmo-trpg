import { describe, expect, it } from "vitest";
import type { PreviewOut } from "../api/types";
import { buildDrawModel } from "./drawModel";
import { previewOverlays } from "./scenePreview";
import { previewLines } from "./previewText";
import { auraTiles, remainingRounds, summonKind, summonLine, summonLines, summonsOf } from "./summons";
import { smallView, unit } from "./testFixtures";
import { unitNames } from "./units";

// 第 2 輪：骷髏（到第 3 輪結束）、圖騰（光環半徑 1，到第 2 輪結束）、已消失的召喚物。
function summonView() {
  const base = smallView({ round: 2 });
  const skeleton = unit("unit_0006", "ally", 1, 0, { owner_id: "unit_0001", summon_expires_round: 3, name_zh: "骷髏戰士1" });
  const totem = unit("unit_0007", "ally", 0, 1, {
    owner_id: "unit_0001",
    summon_expires_round: 2,
    name_zh: "戰意圖騰1",
    totem_radius: 1,
  });
  const gone = unit("unit_0008", "ally", 3, 2, { owner_id: "unit_0001", dismissed: true });
  return { ...base, units: [...base.units, skeleton, totem, gone] };
}

const emptyPreview = {
  action: { type: "use_skill", unit_id: "unit_0001", skill_id: "skill_raise_skeleton" },
  hit_permille: null,
  crit_permille: null,
  damage: null,
  affected_tiles: [],
  affected_units: [],
  certain: [],
  possible: [],
  cover: null,
  notes: [],
  targets: [],
  healed: [],
  min_events: [],
  max_events: [],
} as unknown as PreviewOut;

const summonPreview = (over: object = {}) =>
  ({
    ...emptyPreview,
    summons: [
      {
        unit_id: "unit_0009",
        template_id: "summon_skeleton_warrior",
        name_zh: "骷髏戰士",
        pos: [2, 2],
        expires_round: 4,
        max_hp: 20,
        totem_radius: null,
        replaces: [],
        ...over,
      },
    ],
  }) as unknown as PreviewOut;

describe("summons (Phase 3D-4b)", () => {
  const view = summonView();

  it("counts the remaining rounds including the current one", () => {
    const skeleton = view.units.find((u) => u.id === "unit_0006")!;
    const hero = view.units.find((u) => u.id === "unit_0001")!;
    expect(remainingRounds(view, skeleton)).toBe(2); // 第 2、3 輪
    expect(remainingRounds(view, hero)).toBeNull();
    expect(summonLine(view, skeleton)).toBe("骷髏戰士1　HP 10/20　剩 2 輪（第 3 輪結束時消失）");
  });

  it("lists the owner's living summons for the HUD (dismissed ones are left out)", () => {
    expect(summonsOf(view, "unit_0001").map((u) => u.id)).toEqual(["unit_0006", "unit_0007"]);
    expect(summonKind(view.units.find((u) => u.id === "unit_0007")!)).toBe("圖騰");
    expect(summonKind(view.units.find((u) => u.id === "unit_0006")!)).toBe("召喚物");
    expect(summonKind(view.units.find((u) => u.id === "unit_0003")!)).toBeNull();
  });

  it("marks summons with digits instead of team letters", () => {
    const names = unitNames(view);
    expect(names.marker("unit_0006")).toBe("1");
    expect(names.marker("unit_0007")).toBe("2");
    expect(names.marker("unit_0003")).toBe("a"); // 敵方的字母不受召喚物影響
  });

  it("draws summons as a distinct shape with remaining rounds and the totem aura", () => {
    const model = buildDrawModel(view, "unit_0001");
    const skeleton = model.units.find((u) => u.id === "unit_0006")!;
    const totem = model.units.find((u) => u.id === "unit_0007")!;
    const hero = model.units.find((u) => u.id === "unit_0001")!;
    expect(skeleton).toMatchObject({ summon: true, totem: false, remaining: 2, marker: "1" });
    expect(totem).toMatchObject({ summon: true, totem: true, remaining: 1 });
    expect(hero).toMatchObject({ summon: false, totem: false, remaining: null });
    expect(model.units.find((u) => u.id === "unit_0008")).toBeUndefined();
    // 圖騰在 (0, 1)，半徑 1：自己、上、下、右（網格 4×3 內）
    expect(model.auras.map((a) => `${a.x},${a.y}`).sort()).toEqual(["0,0", "0,1", "0,2", "1,1"]);
  });

  it("computes aura tiles inside the board only", () => {
    expect(auraTiles({ x: 0, y: 0 }, 2, view).map((t) => `${t.x},${t.y}`).sort()).toEqual([
      "0,0",
      "0,1",
      "0,2",
      "1,0",
      "1,1",
      "2,0",
    ]);
  });

  it("shows the summon position in the skill preview", () => {
    const overlays = previewOverlays(summonPreview(), view);
    expect(overlays).toEqual([{ pos: { x: 2, y: 2 }, kind: "summon_at", label: "召" }]);
    const lines = previewLines(summonPreview(), unitNames(view), view);
    expect(lines.some((l) => l.includes("召喚：骷髏戰士（HP 20）出現在 (2, 2)") && l.includes("第 4 輪"))).toBe(true);
  });

  it("shows the totem aura range and the summon that will vanish over the limit", () => {
    const p = summonPreview({ totem_radius: 1, name_zh: "戰意圖騰", replaces: ["unit_0006"] });
    const overlays = previewOverlays(p, view);
    expect(overlays.filter((o) => o.kind === "summon_aura").map((o) => `${o.pos.x},${o.pos.y}`).sort()).toEqual([
      "1,2",
      "2,1",
      "2,2",
      "3,2",
    ]);
    expect(overlays).toContainEqual({ pos: { x: 2, y: 2 }, kind: "summon_at", label: "圖" });
    expect(overlays).toContainEqual({ pos: { x: 1, y: 0 }, kind: "summon_gone", label: "消" });
    const lines = summonLines(p, unitNames(view));
    expect(lines[0]).toContain("圖騰不移動、不攻擊");
    expect(lines[1]).toContain("上限");
    expect(lines[1]).toContain("骷髏戰士1");
  });
});
