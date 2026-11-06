// 6F-18（美術 PM 驗收 6F-17：docs/archive/art/6F-17檢查.md，只換外觀與顯示）：
// 1. 格子上有單位站著（沒倒下）時不畫「▲N」（所有寬度都一樣）；空格照舊；浮動卡與目標說明寫「高地 ▲N」。
//    6F-17 的角標（heightTag.ts）拿掉。6F-16／6F-17 的 NUM_CLASH、ROW_CLASH（「▲N」和徽章、狀態列擠在一起）重新算 → 0。
// 2. 狀態列不因為徽章收起來：狀態 2 個以內不收成只留「+N」，每個圖示都整個看得到；3 個以上照 6F-17。
// 3. 徽章的數字放回 6F-16 的位置（圓外、緊貼自己的圓），不放進圓裡（蓄力的靶心要看得到）。
// 4. 「+N」描邊加 1px。
// 照收（不改壞）：三角形 40% 上限、HP 條不被蓋（fix6f15）、「+N」不超出地圖（fix6f16）、徽章不蓋狀態圖示與「+N」（這裡）。
import { CanvasTextMetrics, Container, Text, Texture, Graphics } from "pixi.js";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import { type BattleView, type Facing, type PreviewOut } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { heightNote } from "../battle/elevation";
import { previewLines, targetHeightLines } from "../battle/previewText";
import { smallView, tile, unit } from "../battle/testFixtures";
import { unitNames } from "../battle/units";
import { type ArtTextures } from "../render/artTextures";
import { heightBadgeText } from "../render/artSpecs";
import { badgeShapes, FIRM_HP_FIRST, FIRM_STEPS, NUM_CORNERS, numberAt, PLUS_ONLY_MODES, STATUS_BADGE_R, badgeScales, OVER_MODES, STATUS_BADGE_LINE, STATUS_BADGE_STROKE, ONE_ICON_MODES } from "../render/badgeLayout";
import { markedTileFree } from "../render/heightMark";
import { applyMarkScale, BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, INFUSED_BADGE_LABEL, statusRowOf, unitMarksOf } from "../render/minMark";
import { circleHitsBox, PLUS_ONLY_MIN_STATUSES, type Box, PLUS_CAP_BAR, PLUS_CAP_EDGE, PLUS_CAP_FILL, PLUS_CAP_FONT, PLUS_NUM_SEP_PX, plusCapsuleWidth, ROW_PLUS_OVERFLOW_MAX, type MapEdge, CAP_NARROW, CAP_WIDE, capGeom, PLUS_CAP_DIGIT_W, PLUS_CAP_LINE, PLUS_CAP_PLUS, PLUS_CAP_PLUS_NARROW } from "../render/rowLayout";
import { badgeLayoutOf, buildUnitSprite, Pulses, rowModeOf, rowShapesOf, PLUS_CAP_LABEL, rowPlusTexts } from "../render/unitSprite";
import { readSources, stripTsComments, readFile, SRC_DIR } from "../test/sourceScan";
import { UnitInfo } from "./UnitInfo";
import { avoidRect } from "./hoverCard";
import { sortStatuses, statusRank } from "../render/statusIcon";
import { revealScrollTop } from "./ActionPanel";

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
 * 6F-20（美術 PM 6F-19 檢查決定 X）：放得下「1 個圖示＋『+1』」的退回這一種（`ONE_ICON_X`，只有 1600 寬朝北）；其餘 8 種
 * 1 個圖示＋膠囊比 2 個圖示還寬，一樣放不下，照舊只留「+2」（見 Phase6F-20報告「待 PM 決定」）。
 */
const ONE_ICON_X: string[] = ["1600 north charge+2"];
const LAST_RESORT: string[] = ["1040 east charge+2", "1040 west charge+2", "1040 north charge+2", "1040 south charge+2", "800 east charge+2", "800 west charge+2", "800 north charge+2", "800 south charge+2"];

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
    expect(r).toContain("registerMark(node, { base: HEIGHT_BADGE_FONT, min: MIN_HEIGHT_BADGE_FONT_PX }, [num], corner ?"); // 6F-22b：北邊的人 HUD 在高台之上時改放左下角
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
    const oneIcon: string[] = [];
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
            // 6F-20（決定 X）：1 個圖示＋「+1」膠囊
            const one = rowOf(c).icons.length === 1 && rowOf(c).nums.length > 0 && visibleIcons(alone) === 2;
            if (collapsed) lastResort.push(tag);
            else if (one) oneIcon.push(tag);
            else expect(visibleIcons(c), tag).toBe(visibleIcons(alone));
          }
        }
    expect(lastResort).toEqual(LAST_RESORT);
    expect(oneIcon).toEqual(ONE_ICON_X);
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

// --- 原 fix6f19.test.ts ---
describe("原 fix6f19.test.ts", () => {
// 6F-19（美術 PM 驗收 6F-18：docs/archive/art/6F-18檢查.md，只換外觀與顯示）：
// 1. 「+N」改成膠囊（狀態列的深藍底、金色細框、白字；「+」用矩形畫，800 寬筆畫至少 2px），和徽章的黑底白字數字分開。
//    徽章的數字和膠囊的外框之間至少隔畫面上 3px、不相碰（不再要求斜對角）；徽章的圓也不碰膠囊。
// 2. A（LAST_RESORT）：徽章放不好時先讓狀態列超出格子（最多 6，不超出地圖），還是放不下才只留「+N」膠囊。
// 3. B（PLUS_COVERED）：膠囊往遠離徽章的一側移（可以超出格子最多 6），徽章不蓋到膠囊。
// 4. D1：精簡列 2 個狀態不畫「1 個圖示＋『+1』」，改畫 2 個圖示。
// 5. 小修：正下方的數字緊貼圓不重疊；浮動卡避開縮放列。
// 照收（不改壞）：三角形 40% 上限、HP 條不被蓋（fix6f15）、「+N」不超出地圖（fix6f16）、徽章不蓋狀態圖示、
// 有人站的格子不畫 ▲N、2 個以內每個圖示都看得到（fix6f18）、數字在圓外緊貼自己的圓（fix6f16、fix6f18）。

const sources = Object.fromEntries(readSources().map(([p, t]) => [p, stripTsComments(t, p)]));
const T = 48;
/** 實機量到的地圖縮放：1600×900、1040×624、800×600（開闊平原）。 */
const S1600 = 1.275;
const S1040 = 0.796;
const S800 = 0.646;
const SIZES = [S1600, S1040, S800];
const FACINGS: readonly Facing[] = ["east", "west", "north", "south"];
const sizeName = (s: number) => (s === S1600 ? "1600" : s === S1040 ? "1040" : "800");
const EDGES: Array<[string, MapEdge]> = [
  ["", { left: false, right: false }],
  [" 最左欄", { left: true, right: false }],
  [" 最右欄", { left: false, right: true }],
];

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

function sprite(u: UnitDraw, s: number, edge?: MapEdge): Container {
  const c = buildUnitSprite(art, new Pulses(), u, [], edge === undefined ? {} : { edge });
  for (const n of unitMarksOf(c)) applyMarkScale(n, s, s);
  return c;
}
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
function rowOf(c: Container): { icons: Box[]; cap: Box | null; all: Box[] } {
  const row = statusRowOf(c);
  if (row === null) return { icons: [], cap: null, all: [] };
  const sh = rowShapesOf(row)!;
  return { icons: sh.boxes.filter((b) => b !== sh.cap), cap: sh.cap, all: [...sh.boxes] };
}
/** 兩個方框之間的距離（左右或上下分開的那一邊；重疊時 ≤ 0）。 */
const sepOf = (a: Box, b: Box) => Math.max(b.l - a.r, a.l - b.r, b.t - a.b, a.t - b.b);

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
  ["bomb+3", { bomb: 2, statusIds: ["time_bomb", "burning", "slow", "defending"] }],
  ["infused+3", { infused: true, statusIds: ["burning", "slow", "defending"] }],
];
const ROW_ONLY: Array<[string, Partial<UnitDraw>]> = [
  ["row1", { statusIds: ["defending"] }],
  ["row2", { statusIds: ["defending", "slow"] }],
  ["row3", { statusIds: ["burning", "slow", "defending"] }],
];
const rowCount = (u: UnitDraw) => (u.statusIds ?? []).filter((id) => id !== "time_bomb" && id !== "charging").length;

/**
 * 6F-18 的 `PLUS_COVERED`（徽章蓋到「+N」）：6F-19 起膠囊每一層都避開（B），這幾種現在都不蓋到、數字隔 3px 以上。
 */
const PLUS_COVERED_6F18 = ["1040 east charge+2", "1040 south charge+2", "800 west charge+2", "800 west charge+3", "800 south charge+2"];

describe("6F-19 第 1 項：「+N」膠囊", () => {
  it("膠囊：深藍底（狀態列的 --ui-navy）、金色細框、白字；「+」用兩條矩形畫；徽章的數字照舊黑底白字加黑描邊", () => {
    expect(PLUS_CAP_FILL).toBe(0x1e2236);
    expect(PLUS_CAP_EDGE).toBe(0xc8a868);
    const s = sources["render/unitSprite.ts"]!;
    expect(s).toContain(".roundRect(e, e, w - 2 * e, h - 2 * e, (h - 2 * e) / 2)");
    expect(s).toContain(".fill({ color: PLUS_CAP_FILL, alpha: PLUS_CAP_FILL_ALPHA })");
    expect(s).toContain(".stroke({ width: PLUS_CAP_LINE, color: PLUS_CAP_EDGE });");
    expect(s).toContain("g.rect(cx - geom.plus / 2, cy - PLUS_CAP_BAR / 2, geom.plus, PLUS_CAP_BAR)"); // 6F-20：「+」的長度照縮放
    expect(s).toContain("const text = label(digits, PLUS_CAP_FONT, 0xffffff, true);");
    // 徽章的數字維持原樣（黑描邊）
    expect(s).toContain("num.style.stroke = { color: 0x000000, width: STATUS_BADGE_STROKE };");
    expect(STATUS_BADGE_STROKE).toBe(3);
    // 6F-17、6F-18 的描邊字與暈拿掉
    for (const gone of ["PLUS_HALO", "ROW_PLUS_STROKE_EXTRA", "function plusText(", "function moreTag("]) expect(s, gone).not.toContain(gone);
  });

  it("三種「+N」（1600 寬角標、精簡列、只留「+N」）都是膠囊：節點裡有底（Graphics）和白色數字，看得到的「+N」照狀態數", () => {
    const cases: Array<[number, Partial<UnitDraw>, string]> = [
      [S1600, { statusIds: ["burning", "slow", "defending"] }, "+1"], // 角標
      [S1040, { statusIds: ["burning", "slow", "defending"], facing: "south" }, "+2"], // 精簡列
      [S800, { statusIds: ["burning", "slow", "defending"], facing: "north" }, "+3"], // 只留「+N」
    ];
    for (const [s, load, want] of cases) {
      const row = statusRowOf(sprite({ ...BASE, ...load } as UnitDraw, s))!;
      expect(rowPlusTexts(row), sizeName(s)).toEqual([want]);
      const cap = row.children.find((n) => n.label === PLUS_CAP_LABEL && n.visible)!;
      expect(cap.children.some((n) => n instanceof Graphics)).toBe(true);
      const t = cap.children.find((n): n is Text => n instanceof Text)!;
      expect(t.style.fill).toBe(0xffffff);
      expect(t.style.fontSize).toBe(PLUS_CAP_FONT);
      expect(t.text).toBe(want.slice(1));
    }
  });

  it("「+」的筆畫在畫面上至少 2px（三種寬度；800 寬最細）", () => {
    for (const s of SIZES)
      for (const [, load] of [...ROW_ONLY, ...LOADS]) {
        const row = statusRowOf(sprite({ ...BASE, facing: "north", ...load } as UnitDraw, s));
        if (row === null) continue;
        // 畫面上的粗細 ＝ 本地座標 × 整排的倍率 × 地圖縮放
        expect(PLUS_CAP_BAR * row.scale.x * s, sizeName(s)).toBeGreaterThanOrEqual(2);
      }
    // 整排的倍率下限 10 ÷ 9（registerMark 的 base 9、min 10）：任何縮放都至少 2px
    expect(PLUS_CAP_BAR * (10 / 9)).toBeGreaterThanOrEqual(2);
    // 膠囊大小照位數算（確定性）
    expect(plusCapsuleWidth(12)).toBeGreaterThan(plusCapsuleWidth(3));
  });

  it("所有寬度 × 朝向 × 徽章組合（含最左、最右欄）：徽章的圓不碰膠囊、數字和膠囊的外框隔畫面上 3px 以上", { timeout: 300_000 }, () => {
    let checked = 0;
    for (const s of SIZES)
      for (const facing of FACINGS)
        for (const [edgeName, edge] of EDGES)
          for (const [name, load] of LOADS) {
            const c = sprite({ ...BASE, facing, ...load } as UnitDraw, s, edge);
            const { cap } = rowOf(c);
            if (cap === null) continue;
            for (const b of badgesOf(c)) {
              const tag = `${sizeName(s)} ${facing}${edgeName} ${name} ${b.kind}`;
              expect(circleHitsBox(b.circle, cap), `${tag} 圓碰到膠囊`).toBe(false);
              if (b.box !== null) expect(sepOf(b.box, cap) * s, `${tag} 數字和膠囊`).toBeGreaterThanOrEqual(PLUS_NUM_SEP_PX - 1e-6);
              checked++;
            }
          }
    expect(PLUS_NUM_SEP_PX).toBe(3);
    expect(checked).toBeGreaterThan(80);
  });
});

describe("6F-19 第 2、3 項：放不好時狀態列超出格子一點（A、B）", () => {
  it("所有寬度 × 朝向 × 組合（含最左、最右欄）：狀態列（圖示與膠囊）超出格子最多 6，不超出地圖；不碰朝向三角形", { timeout: 300_000 }, () => {
    let over = 0;
    for (const s of SIZES)
      for (const facing of FACINGS)
        for (const [edgeName, edge] of EDGES)
          for (const [name, load] of [...LOADS, ...ROW_ONLY]) {
            const c = sprite({ ...BASE, facing, ...load } as UnitDraw, s, edge);
            const { all } = rowOf(c);
            const tag = `${sizeName(s)} ${facing}${edgeName} ${name}`;
            for (const b of all) {
              expect(b.l, tag).toBeGreaterThanOrEqual((edge.left ? -T / 2 : -T / 2 - ROW_PLUS_OVERFLOW_MAX) - 1e-6);
              expect(b.r, tag).toBeLessThanOrEqual((edge.right ? T / 2 : T / 2 + ROW_PLUS_OVERFLOW_MAX) + 1e-6);
            }
            const row = statusRowOf(c);
            if (row !== null && OVER_MODES.includes(rowModeOf(row)!)) over++;
          }
    expect(ROW_PLUS_OVERFLOW_MAX).toBe(6);
    expect(over).toBeGreaterThan(0); // 有用到（例如 800 寬朝西 3 個狀態＋蓄力）
  });

  it("B：6F-18 的 PLUS_COVERED 5 種：徽章不蓋到膠囊，膠囊在徽章的另一側", () => {
    for (const key of PLUS_COVERED_6F18) {
      const [w, facing, name] = key.split(" ") as [string, Facing, string];
      const s = w === "1040" ? S1040 : S800;
      const load = LOADS.find(([n]) => n === name)![1];
      const c = sprite({ ...BASE, facing, ...load } as UnitDraw, s);
      const { cap } = rowOf(c);
      expect(cap, key).not.toBeNull();
      for (const b of badgesOf(c)) {
        expect(circleHitsBox(b.circle, cap!), key).toBe(false);
        if (b.box !== null) expect(sepOf(b.box, cap!) * s, key).toBeGreaterThanOrEqual(PLUS_NUM_SEP_PX - 1e-6);
        // 膠囊的中心和徽章在不同側（離開徽章）
        const capX = (cap!.l + cap!.r) / 2;
        expect(Math.sign(capX - b.lay.at.x), key).not.toBe(0);
        expect(Math.abs(capX - b.lay.at.x), key).toBeGreaterThan(b.circle.r);
      }
    }
  });

  it("A：800 寬朝西 3 個狀態＋蓄力：膠囊往右移、超出格子不到 6（徽章在左邊）", () => {
    const c = sprite({ ...BASE, facing: "west", charge: 1, statusIds: ["burning", "slow", "defending", "charging"] } as UnitDraw, S800);
    const row = statusRowOf(c)!;
    expect(rowModeOf(row)).toBe("over-r");
    const { cap } = rowOf(c);
    expect(cap!.r).toBeGreaterThan(T / 2);
    expect(cap!.r).toBeLessThanOrEqual(T / 2 + ROW_PLUS_OVERFLOW_MAX);
    for (const b of badgesOf(c)) expect(b.lay.at.x).toBeLessThan(cap!.l);
  });
});

describe("6F-19 第 4 項：精簡列 2 個狀態畫 2 個圖示（D1）", () => {
  it("所有寬度 × 朝向 × 組合：2 個狀態時不會是「1 個圖示＋『+1』」", { timeout: 300_000 }, () => {
    for (const s of SIZES)
      for (const facing of FACINGS)
        for (const [name, load] of [...LOADS, ...ROW_ONLY]) {
          const u = { ...BASE, facing, ...load } as UnitDraw;
          if (rowCount(u) !== 2) continue;
          const c = sprite(u, s);
          const { icons, cap } = rowOf(c);
          const tag = `${sizeName(s)} ${facing} ${name}`;
          // 6F-20（美術 PM 6F-19 檢查決定 X）：有徽章、又放不下 2 個圖示時的明文例外（`fix6f20`）
          if (tag === "1600 north charge+2") continue;
          expect(icons.length === 1 && cap !== null, tag).toBe(false);
          // 2 個圖示時不重疊（每個都整個看得到）
          if (icons.length === 2) expect(icons[0]!.r, tag).toBeLessThanOrEqual(icons[1]!.l + 1e-6);
        }
  });

  it("沒有徽章時：1040、800 寬 4 個朝向都是 2 個圖示（6F-18 是 1 個圖示＋「+1」或只留「+2」）", () => {
    for (const s of [S1040, S800])
      for (const facing of FACINGS) {
        const c = sprite({ ...BASE, facing, statusIds: ["defending", "slow"] } as UnitDraw, s);
        expect(rowOf(c).icons, `${sizeName(s)} ${facing}`).toHaveLength(2);
        expect(rowPlusTexts(statusRowOf(c)!), `${sizeName(s)} ${facing}`).toEqual([]);
      }
  });

  it("2 個狀態＋蓄力在 1040、800 寬：2 個圖示和蓄力徽章放不進同一格時，超出格子也放不下才只留「+2」（A；見報告待決）", () => {
    for (const s of [S1040, S800])
      for (const facing of FACINGS) {
        const c = sprite({ ...BASE, facing, charge: 1, statusIds: ["slow", "defending", "charging"] } as UnitDraw, s);
        const row = statusRowOf(c)!;
        const icons = rowOf(c).icons.length;
        const tag = `${sizeName(s)} ${facing}`;
        expect(icons === 2 || (icons === 0 && [...PLUS_ONLY_MODES, ...OVER_MODES].includes(rowModeOf(row)!)), tag).toBe(true);
        if (icons === 0) expect(rowPlusTexts(row), tag).toEqual(["+2"]);
      }
  });
});

describe("6F-19 小修", () => {
  it("正下方的數字（1040 寬「1」壓到紫圈外緣）：三種寬度都是數字（含黑描邊）的上緣剛好貼著圓的外緣，不重疊也不離開", () => {
    for (const s of SIZES) {
      const sc = badgeScales("charge", s);
      const { circle, box } = badgeShapes("charge", { x: 0, y: 0 }, sc, 1, "b");
      expect(box!.t, sizeName(s)).toBeCloseTo(circle.r, 9);
      expect(numberAt("b", sc).y * sc.ki, sizeName(s)).toBeGreaterThan(9.5); // 6F-18 是 9.5
    }
    // 1040、800 寬數字另外放大（kn > 1），所以比 1600 寬往下多
    expect(numberAt("b", badgeScales("charge", S1040)).y).toBeGreaterThan(numberAt("b", badgeScales("charge", S1600)).y);
    // 右下、左下照 6F-16（美術 PM 驗收過）
    for (const corner of ["br", "bl"] as const) expect(Math.hypot(numberAt(corner).x, numberAt(corner).y), corner).toBeLessThanOrEqual(STATUS_BADGE_R + STATUS_BADGE_LINE / 2 + 1);
    expect(NUM_CORNERS).toContain("b");
  });

  it("浮動卡避開縮放列：碰到時往上推；上面放不下改放左邊；都放不下時縮短最大高度；沒碰到照原位", () => {
    const vis = { left: 4, top: 4, right: 796, bottom: 596 };
    const zoom = { left: 600, top: 370, right: 790, bottom: 398 };
    // 800 寬 6f18_5_float_800：卡片下緣（約 395）蓋到縮放列
    expect(avoidRect({ left: 420, top: 185, w: 260, h: 210 }, vis, zoom)).toEqual({ left: 420, top: 370 - 4 - 210 });
    // 沒碰到
    expect(avoidRect({ left: 100, top: 185, w: 260, h: 150 }, vis, zoom)).toEqual({ left: 100, top: 185 });
    // 上面放不下 → 左邊
    expect(avoidRect({ left: 620, top: 20, w: 150, h: 500 }, vis, zoom)).toEqual({ left: 600 - 4 - 150, top: 20 });
    // 都放不下 → 縮短
    expect(avoidRect({ left: 20, top: 20, w: 780, h: 500 }, vis, { ...zoom, left: 10 })).toEqual({ left: 20, top: 4, maxH: 370 - 4 - 4 });
    expect(avoidRect({ left: 420, top: 185, w: 260, h: 210 }, vis, null)).toEqual({ left: 420, top: 185 });
    const h = sources["ui/HoverFloat.tsx"]!;
    expect(h).toContain('document.querySelector(".zoom-controls")');
    expect(h).toContain("avoidRect(");
  });
});

describe("6F-19：單一目標的預覽也寫「高地 ▲N」", () => {
  it("普攻這類單一目標的預覽 `targets` 是空的，目標在 `affected_units`：照樣寫；施放者自己不寫；同一個單位只寫一次", () => {
    const v = smallView({ units: [unit("unit_0001", "ally", 1, 0), unit("unit_0003", "enemy", 1, 0)] });
    const names = unitNames(v);
    const p = { targets: [], affected_units: ["unit_0003", "unit_0003", "unit_0001"], action: { type: "attack", unit_id: "unit_0001" } } as unknown as PreviewOut;
    expect(targetHeightLines(p, names, v)).toEqual([`${names.label("unit_0003")}：高地 ▲2`]);
    expect(targetHeightLines({ ...p, affected_units: [] }, names, v)).toEqual([]);
  });
});

describe("6F-19 的檔案：不新增 Math.random、不用原生 title=", () => {
  it("掃原始碼", () => {
    for (const f of ["render/badgeLayout.ts", "render/unitSprite.ts", "render/rowLayout.ts", "ui/UnitInfo.tsx", "ui/HoverFloat.tsx", "ui/hoverCard.ts"]) {
      const text = sources[f];
      expect(text, f).toBeDefined();
      expect(text, f).not.toContain("Math.random");
      expect(text, f).not.toMatch(/<[a-z][\w-]*\s[^>]*\btitle=/);
    }
  });
});
});

// --- 原 fix6f20.test.ts ---
describe("原 fix6f20.test.ts", () => {
// 6F-20（美術 PM 驗收 6F-19：docs/art/6F-19檢查.md 第 2、3 節，只換外觀與顯示）：
// X. 「2 個狀態＋蓄力」放不下 2 個圖示時退回「1 個圖示＋『+1』膠囊」（D1 的明文例外），留下的圖示照「控制 > 減益 > 增益」，
//    膠囊和徽章的數字隔畫面上 ≥ 3px。放不下 1 個圖示＋膠囊的（1 個圖示＋膠囊比 2 個圖示寬）照舊只留「+2」。
// Y. 膠囊裡的「+」從 5 加長到 6.5（粗細不變，數字往右）；800 寬只加到 6，膠囊總寬不變。

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
function rowOf(c: Container): { icons: Box[]; cap: Box | null } {
  const row = statusRowOf(c);
  if (row === null) return { icons: [], cap: null };
  const sh = rowShapesOf(row)!;
  return { icons: sh.boxes.filter((b) => b !== sh.cap), cap: sh.cap };
}
const sepOf = (a: Box, b: Box) => Math.max(b.l - a.r, a.l - b.r, b.t - a.b, a.t - b.b);
const boxHit = (a: Box, b: Box) => a.l < b.r - 1e-9 && b.l < a.r - 1e-9 && a.t < b.b - 1e-9 && b.t < a.b - 1e-9;
const CHARGE2: Partial<UnitDraw> = { charge: 1, statusIds: ["slow", "defending", "charging"] };

/** 決定 X 的 9 種（6F-19 的 LAST_RESORT）。 */
const NINE = ["1600 north", "1040 east", "1040 west", "1040 north", "1040 south", "800 east", "800 west", "800 north", "800 south"];
/** 其中放得下「1 個圖示＋『+1』」的（其餘 8 種見報告待決：1 個圖示＋膠囊比 2 個圖示寬）。 */
const ONE_ICON_OK = ["1600 north"];

describe("6F-20 決定 X：放不下 2 個圖示時退回「1 個圖示＋『+1』」", () => {
  it("9 種：放得下的是 1 個圖示＋「+1」膠囊（one-*），其餘照舊只留「+2」；有 1 個圖示時膠囊和徽章的數字隔 ≥ 3px、圓不碰圖示和膠囊", () => {
    const one: string[] = [];
    for (const key of NINE) {
      const [w, facing] = key.split(" ") as [string, Facing];
      const s = w === "1600" ? S1600 : w === "1040" ? S1040 : S800;
      const c = sprite({ ...BASE, facing, ...CHARGE2 } as UnitDraw, s);
      const row = statusRowOf(c)!;
      const { icons, cap } = rowOf(c);
      expect(cap, key).not.toBeNull();
      if (icons.length === 1) {
        one.push(key);
        expect(ONE_ICON_MODES.includes(rowModeOf(row)!) || OVER_MODES.includes(rowModeOf(row)!), key).toBe(true);
        expect(rowPlusTexts(row), key).toEqual(["+1"]);
        for (const b of badgesOf(c)) {
          expect(circleHitsBox(b.circle, cap!), key).toBe(false);
          expect(circleHitsBox(b.circle, icons[0]!), key).toBe(false);
          if (b.box !== null) {
            expect(sepOf(b.box, cap!) * s, key).toBeGreaterThanOrEqual(PLUS_NUM_SEP_PX - 1e-6);
            expect(boxHit(b.box, icons[0]!), key).toBe(false);
          }
        }
      } else {
        expect(icons, key).toHaveLength(0);
        expect([...PLUS_ONLY_MODES, ...OVER_MODES].includes(rowModeOf(row)!), key).toBe(true);
        expect(rowPlusTexts(row), key).toEqual(["+2"]);
      }
    }
    expect(one).toEqual(ONE_ICON_OK);
  });

  it("只限有徽章的 2 個狀態：沒有徽章時、3 個狀態時都不會出現 one-*", () => {
    for (const s of SIZES)
      for (const facing of FACINGS)
        for (const load of [{ statusIds: ["slow", "defending"] }, { charge: 1, statusIds: ["burning", "slow", "defending", "charging"] }, { charge: 1, statusIds: ["defending", "charging"] }]) {
          const row = statusRowOf(sprite({ ...BASE, facing, ...load } as UnitDraw, s))!;
          expect(ONE_ICON_MODES.includes(rowModeOf(row)!), `${sizeName(s)} ${facing}`).toBe(false);
        }
  });

  it("留下的圖示：控制 > 減益 > 增益（狀態列照 `sortStatuses` 排，1 個圖示時畫第 1 個）；和輸入順序無關", () => {
    expect(statusRank("slow")).toBeLessThan(statusRank("vulnerable")); // 控制 < 減益
    expect(statusRank("vulnerable")).toBeLessThan(statusRank("defending")); // 減益 < 增益
    expect(sortStatuses(["defending", "slow"])[0]).toBe("slow");
    expect(sortStatuses(["defending", "vulnerable"])[0]).toBe("vulnerable");
    expect(sortStatuses(["vulnerable", "slow"])[0]).toBe("slow");
    const u = sources["render/unitSprite.ts"]!;
    expect(u).toContain("const ids = sortStatuses((u.statusIds ?? []).filter((id) => id !== TIME_BOMB && id !== CHARGING));");
    expect(u).toContain("const n = lay.compact ? 1 : shown.length;");
    // 實際畫：1600 寬朝北、輸入順序反過來，排法一樣
    const a = rowOf(sprite({ ...BASE, facing: "north", charge: 1, statusIds: ["defending", "slow", "charging"] } as UnitDraw, S1600));
    const b = rowOf(sprite({ ...BASE, facing: "north", ...CHARGE2 } as UnitDraw, S1600));
    expect(a).toEqual(b);
  });
});

describe("6F-20 決定 Y：膠囊裡的「+」加長", () => {
  it("1600、1040 寬 6.5、800 寬 6；粗細不變；800 寬膠囊總寬和 6F-19 一樣", () => {
    expect(PLUS_CAP_PLUS).toBe(6.5);
    expect(PLUS_CAP_PLUS_NARROW).toBe(6);
    expect(PLUS_CAP_BAR).toBe(1.85);
    expect(capGeom(S1600)).toBe(CAP_WIDE);
    expect(capGeom(S1040)).toBe(CAP_WIDE);
    expect(capGeom(S800)).toBe(CAP_NARROW);
    // 6F-19：2 × 0.7 + 5 + 0.4 + 數字 + 金框
    const w619 = (d: number) => 2 * 0.7 + 5 + 0.4 + PLUS_CAP_DIGIT_W * d + PLUS_CAP_LINE;
    for (const n of [1, 3, 12]) {
      expect(plusCapsuleWidth(n, CAP_NARROW)).toBeCloseTo(w619(String(n).length), 9);
      expect(plusCapsuleWidth(n, CAP_WIDE)).toBeCloseTo(w619(String(n).length) + 1.5, 9);
    }
  });

  it("實際畫的膠囊：數字跟著往右（1600、1040 比 6F-19 右移 1.5；800 寬 + 6、數字和 6F-19 同位置）", () => {
    const e = PLUS_CAP_LINE / 2;
    for (const [s, facing, geom] of [
      [S1600, "south", CAP_WIDE],
      [S1040, "south", CAP_WIDE],
      [S800, "north", CAP_NARROW],
    ] as const) {
      const row = statusRowOf(sprite({ ...BASE, facing, statusIds: ["burning", "slow", "defending"] } as UnitDraw, s))!;
      const cap = row.children.find((n) => n.label === PLUS_CAP_LABEL && n.visible)!;
      expect(cap.children.some((n) => n instanceof Graphics)).toBe(true);
      const t = cap.children.find((n): n is Text => n instanceof Text)!;
      expect(t.position.x, sizeName(s)).toBeCloseTo(e + geom.pad + geom.plus + geom.sep + (PLUS_CAP_DIGIT_W * t.text.length) / 2, 9);
    }
  });

  it("「+」畫面上的長度：800 寬 ≥ 6.6px（6F-19 約 5.6px）；粗細照舊 ≥ 2px", () => {
    for (const s of SIZES) {
      const row = statusRowOf(sprite({ ...BASE, facing: "north", statusIds: ["burning", "slow", "defending"] } as UnitDraw, s))!;
      const k = row.scale.x * s;
      expect(capGeom(s).plus * k, sizeName(s)).toBeGreaterThanOrEqual(6.6);
      expect(PLUS_CAP_BAR * k, sizeName(s)).toBeGreaterThanOrEqual(2);
    }
  });
});

describe("6F-20 順手修", () => {
  it("預覽框被技能列切到（6f19_1_preview_800）：選取面板放不下時捲到預覽框的下緣看得到，不捲過預覽框的上緣", () => {
    const view = { top: 161, bottom: 395 };
    // 6f19_1_preview_800：預覽框 [277, 429]，下面 34px 看不到 → 往下捲 34
    expect(revealScrollTop(0, view, { top: 277, bottom: 429 })).toBe(34);
    // 已經看得到：不動
    expect(revealScrollTop(12, view, { top: 200, bottom: 390 })).toBe(12);
    // 預覽框比面板高：最多捲到預覽框的上緣貼著面板上緣
    expect(revealScrollTop(0, view, { top: 300, bottom: 700 })).toBe(139);
    const a = sources["ui/ActionPanel.tsx"]!;
    expect(a).toContain("panel.scrollTop = revealScrollTop(");
    expect(a).toContain('<div ref={panelRef} className="panel mode-panel" aria-label="選取">');
  });

  it("浮動卡最下面的提示列：左右下有框線、下面兩角圓角；上一塊下面兩角不圓、不畫下框（接成同一張卡）", () => {
    const css = readFile(SRC_DIR, "styles/float-card.css");
    const bar = css.slice(css.indexOf(".unit-float .tile-pin-bar {"));
    const rule = bar.slice(0, bar.indexOf("}"));
    expect(rule).toContain("border: 1px solid var(--panel-border);");
    expect(rule).toContain("border-radius: 0 0 6px 6px;");
    expect(css).toMatch(/\.unit-float > :nth-last-child\(2\) \{\s*border-bottom: none;\s*border-bottom-left-radius: 0;\s*border-bottom-right-radius: 0;/);
    // 提示列是卡片最後一個子元素（`:nth-last-child(2)` 才是它上面那一塊）
    const h = sources["ui/HoverFloat.tsx"]!;
    expect(h.indexOf('<div className="tile-pin-bar">')).toBeGreaterThan(h.indexOf("{children}"));
  });
});

describe("6F-20 的檔案：不新增 Math.random、不用原生 title=", () => {
  it("掃原始碼", () => {
    for (const f of ["render/badgeLayout.ts", "render/unitSprite.ts", "render/rowLayout.ts", "ui/ActionPanel.tsx"]) {
      const text = sources[f];
      expect(text, f).toBeDefined();
      expect(text, f).not.toContain("Math.random");
      expect(text, f).not.toMatch(/<[a-z][\w-]*\s[^>]*\btitle=/);
    }
  });
});
});
