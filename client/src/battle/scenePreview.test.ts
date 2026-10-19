import { describe, expect, it } from "vitest";
import type { PreviewOut } from "../api/types";
import { directionText, previewOverlays, sceneLines } from "./scenePreview";
import { previewLines } from "./previewText";
import { smallView } from "./testFixtures";
import { unitNames } from "./units";

// smallView：桶子 obj_0001 (2,2)、木箱 obj_0002 (1,2)；敵人 unit_0003 (2,1)、unit_0004 (2,0)。
const view = smallView();
const names = unitNames(view);
const base = {
  action: { type: "end_turn", unit_id: "unit_0001" },
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

const pierce = {
  route: [[1, 0], [2, 0]],
  objects: [{ object_id: "obj_0002", pos: [1, 0] }],
  behind: ["unit_0004"],
  behind_permille: 700,
};
const topple = {
  object_id: "obj_0001",
  pos: [2, 2],
  direction: [0, -1],
  tiles: [[2, 1], [2, 0]],
  units: ["unit_0003", "unit_0004"],
  rubble: [2, 0],
};
const hurl = { object_id: "obj_0001", kind: "oil_barrel", from_pos: [2, 2], to_pos: [3, 2], outcome: "exploded", placed_pos: null };

// 自身位移（Phase 3D-2）：衝鋒的路線、跳躍的落點、交換的兩格
const dash = { kind: "dash", unit_id: "unit_0001", other_id: "unit_0003", path: [[0, 2], [1, 2], [1, 1]] };
const leap = { kind: "leap", unit_id: "unit_0001", other_id: null, path: [[0, 2], [2, 2]] };
const swap = { kind: "swap", unit_id: "unit_0001", other_id: "unit_0003", path: [[0, 2], [2, 1]] };

describe("bomb and revive overlays (Phase 3D-8b)", () => {
  it("marks the blast area, the carrier with the countdown and the revive tile", () => {
    const p = {
      ...base,
      bombs: [{ unit_id: "unit_0003", rounds: 2, radius: 1, tiles: [[2, 1], [1, 1], [2, 2]] }],
      revives: [{ unit_id: "unit_0002", hp: 6, pos: [0, 1], from_pos: [0, 1] }],
    } as unknown as PreviewOut;
    const overlays = previewOverlays(p, view);
    expect(overlays.filter((o) => o.kind === "bomb_blast").map((o) => [o.pos.x, o.pos.y])).toEqual([
      [2, 1],
      [1, 1],
      [2, 2],
    ]);
    expect(overlays.find((o) => o.kind === "bomb_at")).toMatchObject({ pos: { x: 2, y: 1 }, label: "炸2" });
    expect(overlays.find((o) => o.kind === "revive_at")).toMatchObject({ pos: { x: 0, y: 1 }, label: "復" });
  });

  it("puts the bomb and revive lines into the preview text", () => {
    const p = {
      ...base,
      bombs: [{ unit_id: "unit_0003", rounds: 2, radius: 1, tiles: [[2, 1]] }],
      revives: [{ unit_id: "unit_0002", hp: 6, pos: [0, 1], from_pos: [0, 1] }],
    } as unknown as PreviewOut;
    const lines = previewLines(p, names, view);
    expect(lines.some((l) => l.includes("定時炸彈") && l.includes("2 次環境回合後"))).toBe(true);
    expect(lines.some((l) => l.includes("復活") && l.includes("6 HP"))).toBe(true);
  });
});

describe("previewOverlays", () => {
  it("is empty without scene data (older servers and plain actions)", () => {
    expect(previewOverlays(null, view)).toEqual([]);
    expect(previewOverlays(base, view)).toEqual([]);
  });

  it("marks the pierce route, the pierced objects and the units behind them", () => {
    const marks = previewOverlays({ ...base, pierce } as unknown as PreviewOut, view);
    // 穿過的物件所在格只畫「穿」，不重複畫路線點
    expect(marks.filter((m) => m.kind === "route").map((m) => m.pos)).toEqual([{ x: 2, y: 0 }]);
    expect(marks.filter((m) => m.kind === "pierced")).toEqual([{ pos: { x: 1, y: 0 }, kind: "pierced", label: "穿" }]);
    expect(marks.filter((m) => m.kind === "behind")).toEqual([{ pos: { x: 2, y: 0 }, kind: "behind", label: "70%" }]);
  });

  it("marks the crushed tiles and the rubble of a topple", () => {
    const marks = previewOverlays({ ...base, topples: [topple] } as unknown as PreviewOut, view);
    expect(marks.filter((m) => m.kind === "crush").map((m) => m.pos)).toEqual([{ x: 2, y: 1 }, { x: 2, y: 0 }]);
    expect(marks.find((m) => m.kind === "rubble")).toEqual({ pos: { x: 2, y: 0 }, kind: "rubble", label: "礫" });
    expect(previewOverlays({ ...base, topples: [{ ...topple, rubble: null }] } as unknown as PreviewOut, view).some((m) => m.kind === "rubble")).toBe(false);
  });

  it("marks the lifted object and its landing for a hurl", () => {
    const marks = previewOverlays({ ...base, hurls: [hurl] } as unknown as PreviewOut, view);
    expect(marks).toEqual([
      { pos: { x: 2, y: 2 }, kind: "hurl_from", label: "舉" },
      { pos: { x: 3, y: 2 }, kind: "hurl_to", label: "落" },
    ]);
  });
});

describe("self-movement previews", () => {
  it("marks the dash route and its end tile", () => {
    const marks = previewOverlays({ ...base, moves: [dash] } as unknown as PreviewOut, view);
    expect(marks).toEqual([
      { pos: { x: 1, y: 2 }, kind: "dash_path", label: "" },
      { pos: { x: 1, y: 1 }, kind: "dash_end", label: "衝" },
    ]);
  });

  it("marks nothing for a dash that does not move, the landing for a leap and both tiles of a swap", () => {
    const still = { ...dash, path: [[0, 2]] };
    expect(previewOverlays({ ...base, moves: [still] } as unknown as PreviewOut, view)).toEqual([]);
    expect(previewOverlays({ ...base, moves: [leap] } as unknown as PreviewOut, view)).toEqual([
      { pos: { x: 2, y: 2 }, kind: "leap_to", label: "躍" },
    ]);
    expect(previewOverlays({ ...base, moves: [swap] } as unknown as PreviewOut, view)).toEqual([
      { pos: { x: 0, y: 2 }, kind: "swap", label: "換" },
      { pos: { x: 2, y: 1 }, kind: "swap", label: "換" },
    ]);
  });

  it("explains the dash route, the leap and the swap in the preview lines", () => {
    const [d] = sceneLines({ ...base, moves: [dash] } as unknown as PreviewOut, names, view);
    expect(d).toContain("衝鋒");
    expect(d).toContain("(0, 2)→(1, 2)→(1, 1)");
    expect(d).toContain(names.label("unit_0003"));
    const [l] = sceneLines({ ...base, moves: [leap] } as unknown as PreviewOut, names, view);
    expect(l).toContain("落在 (2, 2)");
    const [s] = sceneLines({ ...base, moves: [swap] } as unknown as PreviewOut, names, view);
    expect(s).toContain("(0, 2)");
    expect(s).toContain("(2, 1)");
    const p = { ...base, moves: [dash] } as unknown as PreviewOut;
    expect(previewLines(p, names, view).some((line) => line.startsWith("衝鋒："))).toBe(true);
  });
});

// 直線衝撞（Phase 3D-2c）：路線 (0,1)→(3,1)，經過敵人 unit_0003 (2,1)，終點 (3,1)
const charge = { kind: "charge", unit_id: "unit_0001", other_id: null, path: [[0, 1], [1, 1], [2, 1], [3, 1]] };
const foe = { unit_id: "unit_0003", hit_permille: 550, crit_permille: 0, damage: null, ally: false, knock_permille: 600, status_chances: [] };

describe("charge-through previews", () => {
  const withCharge = (extra: object = {}) =>
    ({ ...base, action: { type: "use_skill", unit_id: "unit_0001", skill_id: "skill_bull_rush", target_pos: { x: 3, y: 1 } }, moves: [charge], targets: [foe], ...extra }) as unknown as PreviewOut;

  it("marks the route, the enemies it runs through with their hit chance, and the end tile", () => {
    expect(previewOverlays(withCharge(), view)).toEqual([
      { pos: { x: 1, y: 1 }, kind: "dash_path", label: "" },
      { pos: { x: 2, y: 1 }, kind: "charge_hit", label: "55%" },
      { pos: { x: 3, y: 1 }, kind: "dash_end", label: "衝" },
    ]);
  });

  it("does not mark allies as hit and marks nothing for a charge that does not move", () => {
    const ally = { ...foe, ally: true };
    expect(previewOverlays(withCharge({ targets: [ally] }), view).some((m) => m.kind === "charge_hit")).toBe(false);
    expect(previewOverlays(withCharge({ moves: [{ ...charge, path: [[0, 1]] }] }), view)).toEqual([]);
  });

  it("explains the route, the enemies hit with their chance and the knock down", () => {
    const [line] = sceneLines(withCharge(), names, view);
    expect(line).toContain("衝撞");
    expect(line).toContain("(0, 1)→(1, 1)→(2, 1)→(3, 1)");
    expect(line).toContain(`${names.label("unit_0003")}（命中 55%）`);
    expect(line).toContain("撞倒");
    expect(line).not.toContain("被擋住");
    expect(previewLines(withCharge(), names, view).some((l) => l.startsWith("衝撞："))).toBe(true);
  });

  it("says push-aside when there is no knock down, nobody on the way, and when the end was blocked", () => {
    const aside = { ...foe, knock_permille: null };
    expect(sceneLines(withCharge({ targets: [aside] }), names, view)[0]).toContain("推到路徑旁");
    expect(sceneLines(withCharge({ targets: [] }), names, view)[0]).toContain("沿途沒有敵人");
    const blocked = withCharge({ moves: [{ ...charge, path: [[0, 1], [1, 1]] }] });
    const text = sceneLines(blocked, names, view)[0];
    expect(text).toContain("被擋住：選的終點是 (3, 1)，實際停在 (1, 1)");
  });
});

describe("sceneLines", () => {
  it("explains a pierce through an object, with the discounted target behind it", () => {
    const lines = sceneLines({ ...base, pierce } as unknown as PreviewOut, names, view);
    expect(lines).toHaveLength(1);
    expect(lines[0]).toContain("穿透：穿過");
    expect(lines[0]).toContain("(1, 0)");
    expect(lines[0]).toContain("只受 70% 傷害");
    expect(lines[0]).toContain(names.label("unit_0004"));
  });

  it("says a pierce without objects only ignores cover", () => {
    const bare = { ...pierce, objects: [], behind: [] };
    expect(sceneLines({ ...base, pierce: bare } as unknown as PreviewOut, names, view)[0]).toContain("無視半掩護");
  });

  it("explains a topple: direction, crushed tiles and units, rubble", () => {
    const [line] = sceneLines({ ...base, topples: [topple] } as unknown as PreviewOut, names, view);
    expect(line).toContain("往北倒下");
    expect(line).toContain("壓住 (2, 1)、(2, 0)");
    expect(line).toContain(`壓到 ${names.label("unit_0003")}`);
    expect(line).toContain("倒塌物留在 (2, 0)");
  });

  it("explains a hurl and what happens when it lands", () => {
    const [line] = sceneLines({ ...base, hurls: [hurl] } as unknown as PreviewOut, names, view);
    expect(line).toContain("(2, 2) → (3, 2)");
    expect(line).toContain("爆炸");
  });

  it("is part of the preview lines", () => {
    const p = { ...base, topples: [topple] } as unknown as PreviewOut;
    expect(previewLines(p, names, view).some((l) => l.startsWith("推倒："))).toBe(true);
    expect(previewLines(base, names, view).some((l) => l.startsWith("推倒：") || l.startsWith("穿透："))).toBe(false);
  });

  it("names the four directions", () => {
    expect([[1, 0], [-1, 0], [0, 1], [0, -1]].map((d) => directionText(d))).toEqual(["東", "西", "南", "北"]);
  });
});

describe("displacing others (Phase 3D-2b)", () => {
  const teleport = { kind: "teleport", unit_id: "unit_0003", other_id: null, path: [[2, 1], [3, 2]] };
  const check = { unit_id: "unit_0003", success_permille: 500, resist_bonus: 2, lethal: false };
  const lethal = { unit_id: "unit_0003", success_permille: 100, resist_bonus: 10, lethal: true };

  it("marks the unit's tile and the landing of a teleport", () => {
    const marks = previewOverlays({ ...base, moves: [teleport], displace_checks: [check] } as unknown as PreviewOut, view);
    expect(marks).toEqual([
      { pos: { x: 2, y: 1 }, kind: "teleport_from", label: "傳" },
      { pos: { x: 3, y: 2 }, kind: "teleport_to", label: "落" },
    ]);
  });

  it("marks a deadly landing differently", () => {
    const marks = previewOverlays({ ...base, moves: [teleport], displace_checks: [lethal] } as unknown as PreviewOut, view);
    expect(marks[1]).toEqual({ pos: { x: 3, y: 2 }, kind: "teleport_lethal", label: "險" });
  });

  it("shows the success chance and calls out the deadly one", () => {
    const normal = sceneLines({ ...base, moves: [teleport], displace_checks: [check], displace_permille: 500 } as unknown as PreviewOut, names, view);
    expect(normal.some((l) => l.startsWith("傳送："))).toBe(true);
    expect(normal.some((l) => l.includes("成功率 50%") && l.includes("抵抗 +2"))).toBe(true);
    const deadly = sceneLines({ ...base, moves: [teleport], displace_checks: [lethal], displace_permille: 100 } as unknown as PreviewOut, names, view);
    const warn = deadly.find((l) => l.includes("致命地形"));
    expect(warn).toContain("成功率只有 10%");
    expect(warn).toContain("失敗時不會移動");
  });

  it("multiplies the enemy chances for a pair and says allies need no check", () => {
    const second = { unit_id: "unit_0004", success_permille: 600, resist_bonus: 0, lethal: false };
    const swap = { kind: "swap", unit_id: "unit_0003", other_id: "unit_0004", path: [[2, 1], [2, 0]] };
    const lines = sceneLines(
      { ...base, moves: [swap], displace_checks: [{ ...second, unit_id: "unit_0003" }, second], displace_permille: 360 } as unknown as PreviewOut,
      names,
      view,
    );
    expect(lines.some((l) => l.includes("互換成功率：36%"))).toBe(true);
    const friendly = sceneLines({ ...base, moves: [teleport], displace_checks: [], displace_permille: null } as unknown as PreviewOut, names, view);
    expect(friendly).toContain("傳送：友方不需檢定，必定成功");
  });

  it("states the Boss immunity note through the preview lines", () => {
    const p = { ...base, notes: ["單位3 是 Boss：對傳送到致命地形免疫，致命地形不能選為落點"] } as unknown as PreviewOut;
    expect(previewLines(p, names, view).some((l) => l.includes("Boss") && l.includes("致命地形"))).toBe(true);
  });
});
