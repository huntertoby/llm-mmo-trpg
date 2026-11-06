// 6F-20（美術 PM 驗收 6F-19：docs/art/6F-19檢查.md 第 2、3 節，只換外觀與顯示）：
// X. 「2 個狀態＋蓄力」放不下 2 個圖示時退回「1 個圖示＋『+1』膠囊」（D1 的明文例外），留下的圖示照「控制 > 減益 > 增益」，
//    膠囊和徽章的數字隔畫面上 ≥ 3px。放不下 1 個圖示＋膠囊的（1 個圖示＋膠囊比 2 個圖示寬）照舊只留「+2」。
// Y. 膠囊裡的「+」從 5 加長到 6.5（粗細不變，數字往右）；800 寬只加到 6，膠囊總寬不變。
import { CanvasTextMetrics, Container, Graphics, Text, Texture } from "pixi.js";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import type { BattleView, Facing } from "../api/types";
import { buildDrawModel, type UnitDraw } from "../battle/drawModel";
import { tile, unit } from "../battle/testFixtures";
import type { ArtTextures } from "../render/artTextures";
import { badgeShapes, ONE_ICON_MODES, OVER_MODES, PLUS_ONLY_MODES } from "../render/badgeLayout";
import { applyMarkScale, BOMB_BADGE_LABEL, CHARGE_BADGE_LABEL, INFUSED_BADGE_LABEL, statusRowOf, unitMarksOf } from "../render/minMark";
import {
  CAP_NARROW,
  CAP_WIDE,
  capGeom,
  circleHitsBox,
  PLUS_CAP_BAR,
  PLUS_CAP_DIGIT_W,
  PLUS_CAP_LINE,
  PLUS_CAP_PLUS,
  PLUS_CAP_PLUS_NARROW,
  PLUS_NUM_SEP_PX,
  plusCapsuleWidth,
  type Box,
} from "../render/rowLayout";
import { sortStatuses, statusRank } from "../render/statusIcon";
import { badgeLayoutOf, buildUnitSprite, PLUS_CAP_LABEL, Pulses, rowModeOf, rowPlusTexts, rowShapesOf } from "../render/unitSprite";
import { readFile, readSources, SRC_DIR, stripTsComments } from "../test/sourceScan";
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
