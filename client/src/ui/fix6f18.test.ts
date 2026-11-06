// 6F-18（美術 PM 驗收 6F-17：docs/archive/art/6F-17檢查.md，只換外觀與顯示）：
// 1. 格子上有單位站著（沒倒下）時不畫「▲N」（所有寬度都一樣）；空格照舊；浮動卡與目標說明寫「高地 ▲N」。
//    6F-17 的角標（heightTag.ts）拿掉。6F-16／6F-17 的 NUM_CLASH、ROW_CLASH（「▲N」和徽章、狀態列擠在一起）重新算 → 0。
// 2. 狀態列不因為徽章收起來：狀態 2 個以內不收成只留「+N」，每個圖示都整個看得到；3 個以上照 6F-17。
// 3. 徽章的數字放回 6F-16 的位置（圓外、緊貼自己的圓），不放進圓裡（蓄力的靶心要看得到）。
// 4. 「+N」描邊加 1px。
// 照收（不改壞）：三角形 40% 上限、HP 條不被蓋（fix6f15）、「+N」不超出地圖（fix6f16）、徽章不蓋狀態圖示與「+N」（這裡）。
import { CanvasTextMetrics, Container, Text, Texture } from "pixi.js";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import type { BattleView, Facing, PreviewOut } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { heightNote } from "../battle/elevation";
import { previewLines, targetHeightLines } from "../battle/previewText";
import { smallView, tile, unit } from "../battle/testFixtures";
import { unitNames } from "../battle/units";
import type { ArtTextures } from "../render/artTextures";
import { heightBadgeText } from "../render/artSpecs";
import { badgeShapes, FIRM_HP_FIRST, FIRM_STEPS, NUM_CORNERS, numberAt, PLUS_ONLY_MODES, STATUS_BADGE_R } from "../render/badgeLayout";
import { markedTileFree } from "../render/heightMark";
import { applyMarkScale, BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, INFUSED_BADGE_LABEL, statusRowOf, unitMarksOf } from "../render/minMark";
import { circleHitsBox, PLUS_ONLY_MIN_STATUSES, type Box } from "../render/rowLayout";
import { badgeLayoutOf, buildUnitSprite, Pulses, rowModeOf, rowShapesOf } from "../render/unitSprite";
import { readSources, stripTsComments } from "../test/sourceScan";
import { UnitInfo } from "./UnitInfo";

const sources = Object.fromEntries(readSources().map(([p, t]) => [p, stripTsComments(t, p)]));
/** 實機量到的地圖縮放：1600×900、1040×624、800×600（開闊平原）。 */
const S1600 = 1.275;
const S1040 = 0.796;
const S800 = 0.646;
const SIZES = [S1600, S1040, S800];
const FACINGS: readonly Facing[] = ["east", "west", "north", "south"];
const sizeName = (s: number) => (s === S1600 ? "1600" : s === S1040 ? "1040" : "800");

beforeAll(() => {
  vi.spyOn(CanvasTextMetrics, "measureText").mockImplementation((text: string, style) => {
    const fs = Number((style as { fontSize: number }).fontSize);
    return { width: fs * 0.62 * text.length + 2, height: fs * 1.2 } as unknown as CanvasTextMetrics;
  });
});
afterAll(() => vi.restoreAllMocks());

const view = (): BattleView =>
  ({ team: "ally", map_id: "m", map_name_zh: "m", width: 2, height: 1, tiles: [tile(0, 0), tile(1, 0)], objects: [], units: [unit("unit_0001", "ally", 0, 0, { template_id: "hero_fighter" })], traps: [], turn_order: ["unit_0001"], active_unit: "unit_0001", round: 1, max_rounds: 9, weather_id: null, weather_name_zh: null, objective: { kind: "eliminate", tiles: [], rounds: null }, ended: false, winner: null, end_reason: null, pending: null, source_wells: [], zones: [], runes: [] }) as unknown as BattleView;
const art = { figure: () => Texture.WHITE, creature: () => Texture.WHITE, summon: () => Texture.WHITE, dollFx: () => null } as unknown as ArtTextures;
const BASE: UnitDraw = { ...buildDrawModel(view(), "unit_0001").units[0]!, bomb: null, charge: null, infused: false, statusIds: [], marker: "", facing: "south" };

function sprite(u: UnitDraw, s: number): Container {
  const c = buildUnitSprite(art, new Pulses(), u, []);
  for (const n of unitMarksOf(c)) applyMarkScale(n, s, s);
  return c;
}
/** 兩個數字的方框左右、上下都至少隔 `sep`（只在斜對角，6F-16）。 */
const boxHit = (a: Box, b: Box, gap = 0) => a.l < b.r + gap - 1e-9 && b.l < a.r + gap - 1e-9 && a.t < b.b + gap - 1e-9 && b.t < a.b + gap - 1e-9;
const KIND = { [BOMB_BADGE_LABEL]: "bomb", [CHARGE_BADGE_LABEL]: "charge", [INFUSED_BADGE_LABEL]: "infused" } as const;
function badgesOf(c: Container) {
  return unitMarksOf(c)
    .filter((n) => n.label in KIND)
    .map((n) => {
      const lay = badgeLayoutOf(n)!;
      const kind = KIND[n.label as keyof typeof KIND];
      return { kind, lay, ...badgeShapes(kind, lay.at, lay.sc, 1, lay.corner) };
    });
}
/** 狀態列畫出來的形狀：`icons` 圖示，`nums` 「+N」膠囊（6F-19：角標、精簡列、只留「+N」都是膠囊 `cap`）。 */
function rowOf(c: Container): { all: Box[]; icons: Box[]; nums: Box[] } {
  const row = statusRowOf(c);
  if (row === null) return { all: [], icons: [], nums: [] };
  const sh = rowShapesOf(row)!;
  const nums = sh.cap === null ? [] : [sh.cap];
  return { all: [...sh.boxes], nums, icons: sh.boxes.filter((b) => b !== sh.cap) };
}
/** 看得到的圖示數（測試環境沒有貼圖：照狀態列畫出來的圖示形狀算）。 */
const visibleIcons = (c: Container) => rowOf(c).icons.length;

/** 徽章的組合（6F-15～6F-17 同）＋只有狀態列的。 */
const LOADS: Array<[string, Partial<UnitDraw>]> = [
  ["charge", { charge: 1, statusIds: ["charging"] }],
  ["bomb", { bomb: 2, statusIds: ["time_bomb"] }],
  ["infused", { infused: true }],
  ["charge+defending", { charge: 1, statusIds: ["defending", "charging"] }],
  ["bomb+defending", { bomb: 2, statusIds: ["time_bomb", "defending"] }],
  ["charge+2", { charge: 1, statusIds: ["slow", "defending", "charging"] }],
  ["charge+3", { charge: 1, statusIds: ["burning", "slow", "defending", "charging"] }],
  ["all", { bomb: 2, charge: 1, infused: true, statusIds: ["time_bomb", "charging"] }],
  ["all+defending", { bomb: 2, charge: 1, infused: true, statusIds: ["time_bomb", "charging", "defending"] }],
];
const ROW_ONLY: Array<[string, Partial<UnitDraw>]> = [
  ["row1", { statusIds: ["defending"] }],
  ["row2", { statusIds: ["defending", "slow"] }],
  ["row3", { statusIds: ["burning", "slow", "defending"] }],
];
/** 狀態列的狀態數（炸彈、蓄力有自己的徽章，不算）。 */
const rowCount = (u: UnitDraw) => (u.statusIds ?? []).filter((id) => id !== "time_bomb" && id !== "charging").length;

/**
 * 狀態 2 個以內、為了徽章只留「+N」的組合：徽章在任何顯示方式都放不下（格子裡沒有不碰臉、狀態圖示的位置），最後的手段
 * （`RowControl.lastResort`；見 Phase6F-18報告「待 PM 決定」）。
 * 6F-19：先讓圖示超出格子（最多 6，美術 PM 6F-18 檢查 A）還是放不下才用。精簡列 2 個狀態改畫 2 個圖示（D1）以後，
 * 1040、800 寬「2 個狀態＋蓄力」的 2 個圖示和蓄力徽章放不進同一格（見 Phase6F-19報告「待 PM 決定」），清單照 `fix6f19` 的 `LAST_RESORT`。
 */
const LAST_RESORT: string[] = ["1600 north charge+2", "1040 east charge+2", "1040 west charge+2", "1040 north charge+2", "1040 south charge+2", "800 east charge+2", "800 west charge+2", "800 north charge+2", "800 south charge+2"];

describe("6F-18 第 1 項：有人站的格子不畫「▲N」", () => {
  it("markedTileFree：站著的人那一格不畫；倒下的人、別格的人照空格畫", () => {
    const units = [
      { x: 1, y: 0, downed: false },
      { x: 2, y: 0, downed: true },
    ];
    expect(markedTileFree(units, { x: 1, y: 0 })).toBe(false);
    expect(markedTileFree(units, { x: 2, y: 0 })).toBe(true);
    expect(markedTileFree(units, { x: 0, y: 0 })).toBe(true);
    expect(markedTileFree([], { x: 1, y: 0 })).toBe(true);
  });

  it("接線：繪製器只在空格畫「▲N」（原本的底、10px 以上），不再移動或縮成角標；角標的程式拿掉", () => {
    const r = sources["render/BattleRenderer.ts"]!;
    expect(r).toContain("if (text === null || !markedTileFree(model.units, t)) continue;");
    expect(r).toContain("registerMark(node, { base: HEIGHT_BADGE_FONT, min: MIN_HEIGHT_BADGE_FONT_PX }, [num]);");
    expect(r).toContain("const bg = HEIGHT_MARK_BG;");
    for (const gone of ["heightTagScale", "HEIGHT_TAG_BG", "heightMarkDropOf", "heightMarkShiftOf", "rescaleHeightMark", "heightDigits"]) expect(r, gone).not.toContain(gone);
    expect(sources["render/heightTag.ts"]).toBeUndefined();
    const u = sources["render/unitSprite.ts"]!;
    for (const gone of ["pickTag", "heightDigits", "standingMarkOf", "markDrops", "rowAfter", "keepBoxes"]) expect(u, gone).not.toContain(gone);
    const b = sources["render/badgeLayout.ts"]!;
    for (const gone of ["keepBoxes", "keepInk", "NUM_CORNERS_ABOVE", "NUM_CENTER"]) expect(b, gone).not.toContain(gone);
  });

  it("NUM_CLASH、ROW_CLASH 重新算：有「▲N」的格子上站著人時一律不畫，和「▲N」擠在一起的組合是 0", () => {
    // 6F-17 的清單（1040、800 寬身上有徽章又有狀態列、站在 ▲N 上）：那一格現在不畫「▲N」，沒有可以擠的東西
    const clash: string[] = [];
    for (const facing of FACINGS)
      for (const [name, load] of [...LOADS, ...ROW_ONLY]) {
        const v = { ...view(), tiles: [tile(0, 0, { height: 1 }), tile(1, 0)] } as BattleView;
        const model = buildDrawModel(v, "unit_0001");
        const t = model.tiles.find((x) => x.x === 0 && x.y === 0)!;
        expect(heightBadgeText(model, t), name).toBe("1"); // 這一格本來有「▲1」
        const units = model.units.map((x) => ({ ...x, facing, ...load }));
        if (markedTileFree(units, t)) clash.push(`${facing} ${name}`);
        // 倒下的人躺著：照空格畫
        expect(markedTileFree(units.map((x) => ({ ...x, downed: true })), t)).toBe(true);
      }
    expect(clash).toEqual([]);
  });

  it("「高地 ▲N」：高度 > 0 才寫", () => {
    expect(heightNote(2)).toBe("高地 ▲2");
    expect(heightNote(1)).toBe("高地 ▲1");
    expect(heightNote(0)).toBeNull();
    expect(heightNote(-1)).toBeNull();
  });

  it("單位浮動卡：站在高地時標題列寫「高地 ▲N」；平地不寫（6F-19：精簡版也寫）", () => {
    const v = smallView();
    const names = unitNames(v);
    const onHill = { ...v.units[0]!, pos: { x: 1, y: 0 } }; // smallView 的 (1,0) 高度 2
    const html = renderToStaticMarkup(createElement(UnitInfo, { unit: onHill, names, heroId: "unit_0001", skills: {}, view: v }));
    expect(html).toContain('<span class="unit-height">高地 ▲2</span>');
    const flat = renderToStaticMarkup(createElement(UnitInfo, { unit: v.units[0]!, names, heroId: "unit_0001", skills: {}, view: v }));
    expect(flat).not.toContain("unit-height");
    const compact = renderToStaticMarkup(createElement(UnitInfo, { unit: onHill, names, heroId: "unit_0001", skills: {}, view: v, compact: true }));
    expect(compact).toContain('<span class="unit-height">高地 ▲2</span>'); // 6F-19（美術 PM 6F-18 檢查 D3）
  });

  it("目標說明：目標站在高地時寫「名字：高地 ▲N」，同一個單位只寫一次，平地不寫", () => {
    const v = smallView({ units: [unit("unit_0001", "ally", 0, 0), unit("unit_0003", "enemy", 1, 0), unit("unit_0004", "enemy", 2, 1)] });
    const names = unitNames(v);
    const t = (id: string) => ({ unit_id: id, hit_permille: 800, damage: null, ally: false, status_chances: [], knock_permille: null });
    const p = { targets: [t("unit_0003"), t("unit_0003"), t("unit_0004")] } as unknown as PreviewOut;
    expect(targetHeightLines(p, names, v)).toEqual([`${names.label("unit_0003")}：高地 ▲2`]);
    const full = { action: { type: "end_turn", unit_id: "unit_0001" }, hit_permille: 800, crit_permille: null, damage: null, certain: [], possible: [], cover: null, notes: [], targets: [t("unit_0003")], healed: [], min_events: [], max_events: [] } as unknown as PreviewOut;
    expect(previewLines(full, names, v)).toContain(`${names.label("unit_0003")}：高地 ▲2`);
  });
});

describe("6F-18 第 2 項：狀態列不因為徽章收起來", () => {
  it("所有寬度 × 朝向 × 組合：狀態 2 個以內一律不只留「+N」，看得到的圖示數照不擠時的排法；3 個以上才可以只留「+N」", { timeout: 300_000 }, () => {
    expect(PLUS_ONLY_MIN_STATUSES).toBe(3);
    const lastResort: string[] = [];
    for (const s of SIZES)
      for (const facing of FACINGS)
        for (const [name, load] of [...LOADS, ...ROW_ONLY]) {
          const u = { ...BASE, facing, ...load } as UnitDraw;
          const n = rowCount(u);
          if (n === 0) continue;
          const c = sprite(u, s);
          const tag = `${sizeName(s)} ${facing} ${name}`;
          if (n <= 2) {
            // 沒有徽章時的排法（朝向三角形擋住時原本就只留「+N」，6F-14 起照收）
            const alone = sprite({ ...u, bomb: null, charge: null, infused: false, statusIds: (u.statusIds ?? []).filter((id) => id !== "time_bomb" && id !== "charging") } as UnitDraw, s);
            // 6F-19：只留「+N」也可以平移（`over-r`／`over-l`，超出格子一點），照「沒有圖示、只有膠囊」算
            const plusOnly = (x: Container) => rowOf(x).icons.length === 0 && rowOf(x).nums.length > 0;
            const collapsed = plusOnly(c) && !plusOnly(alone) && visibleIcons(alone) > 0;
            if (collapsed) lastResort.push(tag);
            else expect(visibleIcons(c), tag).toBe(visibleIcons(alone));
          }
        }
    expect(lastResort).toEqual(LAST_RESORT);
  });

  it("美術 PM 指定的情境：800、1040 寬朝北與朝東、蓄力＋防禦的弓手：防禦圖示整個看得到（徽章不蓋、狀態列不收）", () => {
    for (const s of SIZES)
      for (const facing of ["north", "east"] as const) {
        const u = { ...BASE, facing, charge: 1, statusIds: ["defending", "charging"] } as UnitDraw;
        const c = sprite(u, s);
        const tag = `${sizeName(s)} ${facing}`;
        expect(visibleIcons(c), tag).toBe(1);
        const row = rowOf(c);
        expect(row.icons.length, tag).toBe(1);
        for (const b of badgesOf(c)) {
          for (const r of row.all) expect(circleHitsBox(b.circle, r) || (b.box !== null && boxHit(b.box, r)), tag).toBe(false);
          expect(b.lay.firm, tag).toBeLessThan(FIRM_HP_FIRST); // 朝北：圓可以蓋到三角形（6F-15 照收）
        }
      }
  });

  it("所有寬度 × 朝向 × 組合：徽章的圓與數字都不碰狀態圖示，每顆徽章都放得下（6F-19：「+N」膠囊見 fix6f19）", { timeout: 300_000 }, () => {
    let checked = 0;
    for (const s of SIZES)
      for (const facing of FACINGS)
        for (const [name, load] of LOADS) {
          const u = { ...BASE, facing, ...load } as UnitDraw;
          const c = sprite(u, s);
          const row = rowOf(c);
          for (const b of badgesOf(c)) {
            const tag = `${sizeName(s)} ${facing} ${name} ${b.kind}`;
            expect(b.lay.firm, `${tag} 放不下`).toBeLessThan(FIRM_STEPS.length);
            for (const r of row.icons) {
              expect(circleHitsBox(b.circle, r), `${tag} 圓`).toBe(false);
              if (b.box !== null) expect(boxHit(b.box, r), `${tag} 數字`).toBe(false);
            }
            if (row.icons.length > 0) checked++;
          }
        }
    expect(checked).toBeGreaterThan(40);
  });

  it("1600 寬 3 個狀態加蓄力：放不下時狀態列只留「+N」（6F-17 照收）；朝北現在放得下，圖示照舊", () => {
    const plusOnly: Facing[] = [];
    for (const facing of FACINGS) {
      const u = { ...BASE, facing, charge: 1, statusIds: ["burning", "slow", "defending", "charging"] } as UnitDraw;
      const row = statusRowOf(sprite(u, S1600))!;
      if (PLUS_ONLY_MODES.includes(rowModeOf(row)!)) plusOnly.push(facing);
    }
    expect(plusOnly).toEqual(["east", "west", "south"]);
  });

  it("效能：最擠的情況一個單位不到 0.5 秒（3 次取最快）", { timeout: 120_000 }, () => {
    let worst = 0;
    for (const s of SIZES)
      for (const facing of FACINGS)
        for (const [, load] of [...LOADS, ...ROW_ONLY]) {
          const u = { ...BASE, facing, ...load } as UnitDraw;
          let best = Infinity;
          for (let i = 0; i < 3; i++) {
            const t0 = performance.now();
            sprite(u, s);
            best = Math.min(best, performance.now() - t0);
          }
          worst = Math.max(worst, best);
        }
    expect(worst).toBeLessThan(500);
  });

  it("確定性：同一個單位排兩次結果一樣", () => {
    const u = { ...BASE, facing: "north" as const, charge: 1, statusIds: ["defending", "charging"] } as UnitDraw;
    for (const s of SIZES) {
      const a = sprite(u, s);
      const b = sprite(u, s);
      expect(badgesOf(a).map((x) => x.lay)).toEqual(badgesOf(b).map((x) => x.lay));
      const texts = (c: Container) => statusRowOf(c)!.children.filter((n): n is Text => n instanceof Text && n.visible).map((t) => t.text);
      expect(texts(a)).toEqual(texts(b));
    }
  });
});

describe("6F-18 第 3 項：徽章的數字在圓外、緊貼自己的圓", () => {
  it("數字只放在右下、左下、正下方（6F-16 的位置），不放進圓裡；所有組合實際排出來都是", () => {
    expect([...NUM_CORNERS]).toEqual(["br", "bl", "b"]);
    for (const corner of NUM_CORNERS) expect(Math.hypot(numberAt(corner).x, numberAt(corner).y)).toBeGreaterThan(STATUS_BADGE_R * 0.7);
    for (const s of SIZES)
      for (const facing of FACINGS)
        for (const [name, load] of LOADS)
          for (const b of badgesOf(sprite({ ...BASE, facing, ...load } as UnitDraw, s))) expect(NUM_CORNERS, `${sizeName(s)} ${facing} ${name}`).toContain(b.lay.corner);
  });
});

// 6F-18 第 4 項（「+N」描邊加 1px）：6F-19 起「+N」改成膠囊（美術 PM 6F-18 檢查第 2 節），描邊與暈拿掉，改由 fix6f19 鎖住。

describe("6F-18 的檔案：不新增 Math.random、不用原生 title=", () => {
  it("掃原始碼", () => {
    for (const f of ["render/badgeLayout.ts", "render/heightMark.ts", "render/unitSprite.ts", "render/BattleRenderer.ts", "render/rowLayout.ts", "battle/elevation.ts", "battle/previewText.ts", "ui/UnitInfo.tsx"]) {
      const text = sources[f];
      expect(text, f).toBeDefined();
      expect(text, f).not.toContain("Math.random");
      expect(text, f).not.toMatch(/<[a-z][\w-]*\s[^>]*\btitle=/);
    }
  });
});
