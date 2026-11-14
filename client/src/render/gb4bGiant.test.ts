// GB-4b：3×3 巨型灰燼之心接進戰場（PhaseGB 計畫 8.2；美術移植需求 docs/art/GB巨型頭目-移植需求.md 第 2～5、7 節）。
// 純函式與表：畫法資料（佔格）、z 列與錨點、HUD 位置、部位格狀態 → 標示、破壞演出的格與側、頭頂部位條排序；
// 1 格頭目（霧鎖真人、1 格灰燼之心、碎晶之主）的畫法鍵與輸出不變。實際像素在開發頁 `client/dev/gb4b-giant.html`。
import { describe, expect, it } from "vitest";
import type { Action, BattleView, PartOption, PartView, Pos, UnitView } from "../api/types";
import { classifyActions } from "../battle/actions";
import { buildDrawModel, drawOccupies, isGiantDraw, unitDrawOf, unitRowOf, type UnitDraw } from "../battle/drawModel";
import { giantBreakFxOf, partDraws, stripBars } from "../battle/partStrip";
import { specialsFor } from "../battle/specials";
import { smallView, unit } from "../battle/testFixtures";
import type { TileClickState } from "../battle/tileClick";
import type { StepVfx } from "../battle/vfx";
import { giantMarksOf, markPartsOf, markReasonZh, markWhyOf, meleeOf } from "./battle/partTileMarks";
import { creatureCanvasSize, creatureKey, creatureTop } from "./inkCreature";
import { BOSS_BOX } from "./qBoss";
import { GG, GIANT_ANCHOR_DY, GIANT_BOUNDS, GIANT_CANVAS, GIANT_FEET_TO_ANCHOR } from "./qBossGiant";
import dolls from "./fixtures/unitDolls.json";
import { bossHudDy, creatureOf, FEET, hpBoxOf, isGiantUnit, ringScale } from "./unitSprite";

const T = 48;
const HERO = "unit_0001";
const HEART = "heart";
const P = (x: number, y: number): Pos => ({ x, y });
const tilesOf = (cx: number, cy: number): Pos[] => [-1, 0, 1].flatMap((dy) => [-1, 0, 1].map((dx) => P(cx + dx, cy + dy)));
const st = (s: string) => ({ status_id: s, remaining: 2, source_id: null, amount: null, blast_radius: null, charge_tiles: [], cost_status: false });

function part(id: string, name: string, tiles: Pos[] | null, over: Partial<PartView> = {}): PartView {
  return { id, name_zh: name, hp: 32, max_hp: 32, broken: false, exposed: true, reach: "any", break_lines_zh: [], ...(tiles === null ? {} : { tiles }), ...over };
}

function heart(phase: 1 | 2 | 3, over: Partial<UnitView> = {}, giant = true): UnitView {
  const parts = [
    part("core", "核心", giant ? [P(5, 3)] : null, phase === 1 ? { exposed: false, hp: null, max_hp: null } : {}),
    part("shell_seam", "殼縫", giant ? [P(4, 3), P(6, 3)] : null, giant ? { counts_as_behind: true } : {}),
    part("vent", "熔岩噴口", giant ? [P(4, 2), P(5, 2), P(6, 2)] : null, { reach: "ranged" }),
  ];
  return unit(HEART, "enemy", 5, 3, {
    template_id: "ashen_heart",
    tags: ["boss", "elite"],
    facing: "south",
    doll_look: (dolls as Record<string, unknown>)["ashen_heart"] as UnitView["doll_look"],
    boss_phase: { index: phase, total: 3, name_zh: "x" } as UnitView["boss_phase"],
    statuses: (phase === 1 ? [st("molten_shell")] : []) as unknown as UnitView["statuses"],
    ...(giant ? { footprint: 3, tiles: tilesOf(5, 3) } : {}),
    parts,
    ...over,
  });
}

const viewWith = (units: UnitView[]): BattleView => smallView({ width: 12, height: 12, units });
const drawOf = (u: UnitView, units: UnitView[] = [u]): UnitDraw => unitDrawOf(viewWith(units), u, "", null, HERO);

describe("畫法資料（drawModel）", () => {
  it("巨型單位帶 footprint、tiles；1 格的單位沒有這兩個鍵", () => {
    const g = drawOf(heart(2));
    expect(g.footprint).toBe(3);
    expect(g.tiles).toEqual(tilesOf(5, 3));
    const one = drawOf(heart(2, {}, false));
    expect("footprint" in one).toBe(false);
    expect("tiles" in one).toBe(false);
    expect(isGiantDraw(g)).toBe(true);
    expect(isGiantDraw(one)).toBe(false);
  });

  it("部位帶 counts_as_behind（只有殼縫）；霧鎖真人的部位沒有這個鍵", () => {
    const g = drawOf(heart(2));
    expect(g.parts?.find((p) => p.id === "shell_seam")?.behind).toBe(true);
    expect(g.parts?.filter((p) => "behind" in p).map((p) => p.id)).toEqual(["shell_seam"]);
    expect(partDraws([part("whisk", "拂塵", null), part("sword", "長劍", null)]).every((p) => !("behind" in p))).toBe(true);
  });

  it("頭頂部位條三條照由北到南：噴口｜殼縫｜核心（霧鎖真人照舊）", () => {
    expect(drawOf(heart(2)).parts?.map((p) => p.id)).toEqual(["vent", "shell_seam", "core"]);
    expect(partDraws([part("sword", "", null), part("whisk", "", null), part("dantian", "", null)]).map((p) => p.id)).toEqual(["whisk", "dantian", "sword"]);
  });

  it("佔格判斷：巨型 9 格都算、1 格只算自己", () => {
    const g = drawOf(heart(2));
    for (const t of tilesOf(5, 3)) expect(drawOccupies(g, t)).toBe(true);
    expect(drawOccupies(g, P(7, 3))).toBe(false);
    expect(drawOccupies(drawOf(heart(2, {}, false)), P(4, 3))).toBe(false);
  });
});

describe("z 列、錨點、HUD", () => {
  it("巨型單位的節點掛南排（中心 y ＋ 1）；1 格掛自己那一排", () => {
    expect(unitRowOf(drawOf(heart(2)))).toBe(4);
    expect(unitRowOf(drawOf(heart(2, {}, false)))).toBe(3);
    // 同列最前（`ringScale > 1` 的頭目規則）
    expect(ringScale(drawOf(heart(2)))).toBeGreaterThan(1);
  });

  it("3×3 灰燼之心走巨型畫法；1 格灰燼之心照 qBoss（畫法鍵不變）", () => {
    const g = drawOf(heart(2));
    const one = drawOf(heart(2, {}, false));
    expect(isGiantUnit(g)).toBe(true);
    expect(isGiantUnit(one)).toBe(false);
    const cr1 = creatureOf(one)!;
    expect(cr1.boss).toEqual({ id: "ah", phase: 2 });
    expect(creatureKey(cr1, "west").endsWith("|ah2|w")).toBe(true);
    expect(creatureCanvasSize(cr1)).toEqual({ w: BOSS_BOX.w, h: BOSS_BOX.h, foot: BOSS_BOX.foot });
    expect(creatureTop(cr1)).toBe(BOSS_BOX.top.ah);
    const cr = creatureOf(g)!;
    expect(cr.boss?.giant).toMatchObject({ phase: 2, shell: 0, broken: {}, fx: null });
    expect(creatureKey(cr, "west")).not.toBe(creatureKey(cr1, "west"));
    expect(creatureCanvasSize(cr)).toEqual({ w: GIANT_CANVAS.w, h: GIANT_CANVAS.h, foot: GIANT_CANVAS.foot });
  });

  it("貼圖錨點：腳底（FEET）往南 GIANT_FEET_TO_ANCHOR ＝ 中心格中心往南 72（南排南緣）", () => {
    expect(FEET + GIANT_FEET_TO_ANCHOR).toBeCloseTo(GIANT_ANCHOR_DY, 9);
    expect(GIANT_ANCHOR_DY).toBe(1.5 * T);
  });

  it("HUD 放在 3×3 外接框頂上（錨點往上約 3.4 格）", () => {
    const g = drawOf(heart(2));
    const hp = hpBoxOf(g)!;
    const bottom = hp.b + bossHudDy(g); // 相對中心格中心
    const fromAnchor = (GIANT_ANCHOR_DY - bottom) / T;
    expect(fromAnchor).toBeGreaterThan(3.33);
    expect(fromAnchor).toBeLessThan(3.6); // HP 條下緣含頭頂部位條（約 3.5 格）
    // 頭頂（含外光）＝ 3.33 格
    expect((GIANT_ANCHOR_DY - (FEET + creatureTop(creatureOf(g)!) * GG)) / T).toBeCloseTo(-GIANT_BOUNDS.y0 / T, 6);
  });
});

// ---- 部位格標示 ----
const opt = (part_id: string, name_zh: string, reason: string | null): PartOption => ({ part_id, name_zh, ok: reason === null, reason_zh: reason });
const attack: Action = { type: "attack", unit_id: HERO, target_id: HEART };

function marksState(boss: UnitView, options: PartOption[], weapon = "melee", canAct = true): Pick<TileClickState, "view" | "hero" | "canAct" | "copying" | "command" | "mode" | "hurlPick" | "classified" | "partActions"> {
  const hero = unit(HERO, "ally", 3, 3, { weapon_class: weapon });
  const view = viewWith([hero, boss]);
  return { view, hero, canAct, copying: false, command: null, mode: null, hurlPick: null, classified: classifyActions([attack], view, {}), partActions: [{ type: "attack", skill_id: null, target_id: HEART, options }] };
}

describe("部位格狀態 → 標示（partTileMarks）", () => {
  const MELEE = [opt("core", "核心", "呼吸階段才露出"), opt("shell_seam", "殼縫", null), opt("vent", "熔岩噴口", "只有遠程才打得到")];

  it("引擎原因字 → 原因小圖：近戰打噴口、射程、貼著、視線；不認得退回射程", () => {
    expect(markWhyOf("只有遠程才打得到")).toBe("ranged");
    expect(markWhyOf("那一格超出射程")).toBe("range");
    expect(markWhyOf("要貼著那一格才打得到")).toBe("range");
    expect(markWhyOf("看不到那一格")).toBe("sight");
    expect(markWhyOf("其他")).toBe("range");
    expect(markWhyOf(null)).toBeNull();
  });

  it("短字只在格子標示用：打不到照美術定稿、未露出照伺服器字（巨型＝呼吸階段才露出）", () => {
    expect(markReasonZh({ id: "vent", name: "", tiles: [], state: "blocked", reason: "只有遠程才打得到" })).toBe("要遠程攻擊才打得到");
    expect(markReasonZh({ id: "vent", name: "", tiles: [], state: "blocked", reason: "那一格超出射程" })).toBe("射程不夠");
    expect(markReasonZh({ id: "vent", name: "", tiles: [], state: "blocked", reason: "看不到那一格" })).toBe("看不到這一格");
    expect(markReasonZh({ id: "core", name: "", tiles: [], state: "hidden", reason: "呼吸階段才露出" })).toBe("呼吸階段才露出");
    expect(markReasonZh({ id: "core", name: "", tiles: [], state: "hidden", reason: null })).toBe("這個階段還沒露出");
    expect(markReasonZh({ id: "core", name: "", tiles: [], state: "ok", reason: null })).toBeNull();
  });

  it("第 1 階段近戰：核心未露出、殼縫完好、噴口打不到（要遠程）", () => {
    const [d] = giantMarksOf(marksState(heart(1), MELEE), P(5, 2));
    expect(d!.parts).toEqual({ core: { state: "hidden" }, seam: { state: "ok" }, vent: { state: "off", why: "ranged" } });
    expect(d!.melee).toBe(true);
    expect(d!.behind).toBe(true);
    expect(d!.hover).toBeNull(); // 噴口打不到：不亮
    expect(d!.pos).toEqual(P(5, 3));
  });

  it("破掉的部位＝⑦；markPartsOf 不認得的部位略過", () => {
    const parts = markPartsOf([
      { id: "vent", name: "", tiles: [], state: "broken", reason: null },
      { id: "whisk", name: "", tiles: [], state: "ok", reason: null },
    ]);
    expect(parts).toEqual({ vent: { state: "broken" } });
  });

  it("背刺記號只給近戰：遠程攻擊者 melee＝false", () => {
    const ok = [opt("core", "核心", null), opt("shell_seam", "殼縫", null), opt("vent", "熔岩噴口", null)];
    expect(giantMarksOf(marksState(heart(2), ok, "ranged"), P(5, 4))[0]!.melee).toBe(false);
    expect(giantMarksOf(marksState(heart(2), ok, "melee"), P(5, 4))[0]!.melee).toBe(true);
    // 看不出來時：伺服器回了近戰才有的原因 → 近戰
    expect(meleeOf([opt("vent", "", "要貼著那一格才打得到")], { type: "use_skill", unit_id: HERO, skill_id: "x", target_id: HEART } as Action, { weapon_class: "ranged" })).toBe(true);
  });

  it("滑過：打得到的部位格＝那個部位；前殼、未露出＝本體；打不到＝不亮", () => {
    const s = marksState(heart(1), MELEE);
    const hoverAt = (p: Pos) => giantMarksOf(s, p)[0]!.hover;
    expect(hoverAt(P(4, 3))).toBe("seam");
    expect(hoverAt(P(6, 3))).toBe("seam");
    expect(hoverAt(P(5, 4))).toBe("body");
    expect(hoverAt(P(5, 3))).toBe("body"); // 未露出的核心＝打本體
    expect(hoverAt(P(5, 2))).toBeNull(); // 噴口打不到
  });

  it("沒有選取模式時只在滑到它身上才畫（滑到別處、沒滑過＝不畫）", () => {
    const s = marksState(heart(1), MELEE);
    expect(giantMarksOf(s, null)).toEqual([]);
    expect(giantMarksOf(s, P(8, 8))).toEqual([]);
    expect(giantMarksOf(s, P(4, 4))).toHaveLength(1);
  });

  it("只有在選打它的動作時才有：不能行動、沒有部位選項時沒有", () => {
    expect(giantMarksOf(marksState(heart(1), MELEE, "melee", false), P(5, 4))).toEqual([]);
    const s = marksState(heart(1), MELEE);
    expect(giantMarksOf({ ...s, partActions: [] }, P(5, 4))).toEqual([]);
    // 1 格頭目（沒有 tiles）不畫格子標示
    expect(giantMarksOf(marksState(heart(2, {}, false), MELEE), P(5, 3))).toEqual([]);
  });
});

describe("破壞演出（3×3）", () => {
  it("格 → PartFx：0 命中、1 裂開、2 斷開、3 落地（都還蓋著），第 5 格回到伺服器的樣子", () => {
    expect(giantBreakFxOf("vent", 0, 1, false)).toEqual({ part: "vent", k: "flash", frame: 0, side: 1, shed: false });
    expect(giantBreakFxOf("shell_seam", 2, -1, true)).toEqual({ part: "shell_seam", k: "fly", frame: 2, side: -1, shed: true });
    expect(giantBreakFxOf("core", 3, 1, false)?.frame).toBe(3);
    expect(giantBreakFxOf("core", 4, 1, false)).toBeNull();
  });

  it("頭頂部位條：第 4 格（落地）換「×」，之前是空槽", () => {
    const parts = partDraws([part("vent", "", null, { broken: true, hp: 0 })]);
    expect(stripBars(parts, false, giantBreakFxOf("vent", 2, 1, false))[0]).toEqual({ kind: "ok", hp: 0, max: 1 });
    expect(stripBars(parts, false, giantBreakFxOf("vent", 3, 1, false))[0]!.kind).toBe("broken");
  });

  it("殼縫的側照這一步的 hit_tile（西 −1、東 1）；第 1 階段熔殼還在＝殼片飛走", () => {
    const before = viewWith([unit(HERO, "ally", 3, 3), heart(1)]);
    const after = viewWith([unit(HERO, "ally", 3, 3), heart(1, { statuses: [] })]);
    const vfx = { leadMs: 300, hits: [], casts: [], reactions: [] } as unknown as StepVfx;
    const ev = (hit: Pos) => [
      { seq: 1, type: "attack_rolled", target_id: HEART, attacker_id: HERO, hit: true, hit_tile: hit },
      { seq: 2, type: "part_broken", target_id: HEART, part_id: "shell_seam", name_zh: "殼縫", effects: [], applied: true, text: "" },
    ];
    const west = specialsFor(vfx, ev(P(4, 3)), before, after).find((s) => s.kind === "part_break")!;
    expect(west).toMatchObject({ unitId: HEART, partId: "shell_seam", side: -1, shed: true });
    const east = specialsFor(vfx, ev(P(6, 3)), after, after).find((s) => s.kind === "part_break")!;
    expect(east).toMatchObject({ side: 1, shed: false });
  });

  it("1 格頭目的 part_break 不多欄位（PB-1e 不變）", () => {
    const v = viewWith([unit(HERO, "ally", 3, 3), heart(2, {}, false)]);
    const vfx = { leadMs: 300, hits: [], casts: [], reactions: [] } as unknown as StepVfx;
    const s = specialsFor(vfx, [{ seq: 2, type: "part_broken", target_id: HEART, part_id: "vent", name_zh: "熔岩噴口" }], v, v).find((x) => x.kind === "part_break")!;
    expect("side" in s).toBe(false);
    expect("shed" in s).toBe(false);
  });
});

describe("整場畫法資料（buildDrawModel）", () => {
  it("巨型單位照常排序；其他單位的畫法資料不多鍵", () => {
    const m = buildDrawModel(viewWith([unit(HERO, "ally", 3, 3), heart(2)]), HERO);
    const hero = m.units.find((u) => u.id === HERO)!;
    expect("footprint" in hero || "tiles" in hero).toBe(false);
    expect(m.units.find((u) => u.id === HEART)?.footprint).toBe(3);
  });
});
