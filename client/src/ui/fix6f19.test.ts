// 6F-19（美術 PM 驗收 6F-18：docs/archive/art/6F-18檢查.md，只換外觀與顯示）：
// 1. 「+N」改成膠囊（狀態列的深藍底、金色細框、白字；「+」用矩形畫，800 寬筆畫至少 2px），和徽章的黑底白字數字分開。
//    徽章的數字和膠囊的外框之間至少隔畫面上 3px、不相碰（不再要求斜對角）；徽章的圓也不碰膠囊。
// 2. A（LAST_RESORT）：徽章放不好時先讓狀態列超出格子（最多 6，不超出地圖），還是放不下才只留「+N」膠囊。
// 3. B（PLUS_COVERED）：膠囊往遠離徽章的一側移（可以超出格子最多 6），徽章不蓋到膠囊。
// 4. D1：精簡列 2 個狀態不畫「1 個圖示＋『+1』」，改畫 2 個圖示。
// 5. 小修：正下方的數字緊貼圓不重疊；浮動卡避開縮放列。
// 照收（不改壞）：三角形 40% 上限、HP 條不被蓋（fix6f15）、「+N」不超出地圖（fix6f16）、徽章不蓋狀態圖示、
// 有人站的格子不畫 ▲N、2 個以內每個圖示都看得到（fix6f18）、數字在圓外緊貼自己的圓（fix6f16、fix6f18）。
import { CanvasTextMetrics, Container, Graphics, Text, Texture } from "pixi.js";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import type { BattleView, Facing, PreviewOut } from "../api/types";
import { targetHeightLines } from "../battle/previewText";
import { smallView } from "../battle/testFixtures";
import { unitNames } from "../battle/units";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { tile, unit } from "../battle/testFixtures";
import type { ArtTextures } from "../render/artTextures";
import { badgeScales, badgeShapes, NUM_CORNERS, numberAt, OVER_MODES, PLUS_ONLY_MODES, STATUS_BADGE_LINE, STATUS_BADGE_R, STATUS_BADGE_STROKE } from "../render/badgeLayout";
import { applyMarkScale, BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, INFUSED_BADGE_LABEL, statusRowOf, unitMarksOf } from "../render/minMark";
import {
  circleHitsBox,
  PLUS_CAP_BAR,
  PLUS_CAP_EDGE,
  PLUS_CAP_FILL,
  PLUS_CAP_FONT,
  PLUS_NUM_SEP_PX,
  plusCapsuleWidth,
  ROW_PLUS_OVERFLOW_MAX,
  type Box,
  type MapEdge,
} from "../render/rowLayout";
import { badgeLayoutOf, buildUnitSprite, PLUS_CAP_LABEL, Pulses, rowModeOf, rowPlusTexts, rowShapesOf } from "../render/unitSprite";
import { readSources, stripTsComments } from "../test/sourceScan";
import { avoidRect } from "./hoverCard";

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
    expect(s).toContain("g.rect(cx - PLUS_CAP_PLUS / 2, cy - PLUS_CAP_BAR / 2, PLUS_CAP_PLUS, PLUS_CAP_BAR)");
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
