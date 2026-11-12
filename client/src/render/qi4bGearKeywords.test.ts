// Phase QI-4b：裝備圖示接上 Q 版關鍵字小圓章、說明框列關鍵字（規格 docs/phases/PhaseQI-4計畫.md 第 7.2 節 T-B1～T-B5、T-B7）。
// 款式用 gearAppearance.json 的 kinds（105 款）、關鍵字用它的 keywords（12 個），不手寫清單。
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import appearance from "./gearAppearance.json";
import { fakeCanvasFactory, fakeCtx, type FakeCanvasLog } from "../test/fakeCanvas";
import { readSources } from "../test/sourceScan";
import { drawGear, gearIconKey, gearQDef, KEYWORD_CHIP_MIN_PX, resolveGear, type GearLook } from "./gearIcon";
import { setQCanvasFactory } from "./qIcon/core";
import * as KW from "./qIcon/keywords";
import { clearQWeaponDefs } from "./qIcon/weapons";
import { clearQArmorDefs } from "./qIcon/armor";
import { gearKeywordLine, keywordName, withKeywordLine } from "../gear/gearKeywords";
import { itemTipLines } from "../run/gearOffer";
import type { GearItemInfo } from "../api/types";

interface Kind { id: string; forms: { id: string }[] }
const LOOKS: GearLook[] = (appearance.kinds as unknown as Kind[]).flatMap((k) => k.forms.map((f) => ({ kind: k.id, form: f.id })));
const KWS = appearance.keywords as string[];
/** 兩個關鍵字的組合，輪流配給 105 款（12 個關鍵字都會當第一個與第二個）。 */
const PAIRS: readonly (readonly [string, string])[] = KWS.map((k, i) => [k, KWS[(i + 5) % KWS.length] as string] as const);

const log: FakeCanvasLog = { calls: null };
beforeAll(() => { clearQWeaponDefs(); clearQArmorDefs(); setQCanvasFactory(fakeCanvasFactory(log)); });
afterAll(() => { setQCanvasFactory(null); clearQWeaponDefs(); clearQArmorDefs(); log.calls = null; });

/** 外層與另建畫布都記在同一份紀錄（畫兩次取第二次：第一次會量圓章縮放、建圖樣快取）。 */
function sig(fn: (ctx: CanvasRenderingContext2D) => void): string[] {
  fn(fakeCtx({ calls: null }));
  log.calls = [];
  fn(fakeCtx(log));
  const out = log.calls;
  log.calls = null;
  return out;
}
const gear = (look: GearLook, chips: boolean, px: number, res: number) => (ctx: CanvasRenderingContext2D) => {
  ctx.scale((px * res) / 64, (px * res) / 64);
  drawGear(ctx, look, chips, undefined, px, res);
};
/** 直接呼叫 `keywords.paint`（ctx 在 64 格座標，換成 CSS px 座標再畫；同 `drawQ` 的換算）。 */
const direct = (look: GearLook, px: number, res: number) => (ctx: CanvasRenderingContext2D) => {
  ctx.scale((px * res) / 64, (px * res) / 64);
  const r = resolveGear(look);
  ctx.save();
  ctx.scale(64 / px, 64 / px);
  KW.paint(ctx, r.keywords, px, res, { def: gearQDef(look, r) });
  ctx.restore();
};

describe("T-B1 接線：關鍵字層＝直接呼叫 keywords.paint", () => {
  it("105 款 × 32／40／42／48／64 × res 1、2：chips 畫的＝不畫的＋keywords.paint（關鍵字層排在最後）", () => {
    let n = 0;
    LOOKS.forEach((base, i) => {
      const look: GearLook = { ...base, keywords: [...(PAIRS[i % PAIRS.length] as readonly string[])], rarity: "rare" };
      for (const px of [32, 40, 42, 48, 64]) for (const res of [1, 2]) {
        const withChips = sig(gear(look, true, px, res));
        const without = sig(gear(look, false, px, res));
        const layer = sig(direct(look, px, res)).slice(1); // 去掉 direct 開頭那一筆 scale（gear 的紀錄也有，在 without 裡）
        expect(withChips, `${look.kind}/${look.form} ${px} ${res}`).toEqual([...without, ...layer]);
        expect(layer.length).toBeGreaterThan(4);
        n += 1;
      }
    });
    expect(n).toBe(105 * 5 * 2);
  });
  it("沒有關鍵字時 chips 不多畫任何東西", () => {
    for (const look of LOOKS.slice(0, 20)) expect(sig(gear(look, true, 48, 2))).toEqual(sig(gear(look, false, 48, 2)));
  });
  it("gearIconCanvas 照 px ≥ 32 決定畫不畫（20、31 不畫；32 起畫）", () => {
    expect(KEYWORD_CHIP_MIN_PX).toBe(32);
    const src = readSources().find(([p]) => p.replace(/\\/g, "/").endsWith("render/gearIcon.ts"))?.[1] ?? "";
    expect(src).toContain("drawGear(ctx, look, px >= KEYWORD_CHIP_MIN_PX, slot, px, res);");
    for (const px of [20, 31]) expect(px >= KEYWORD_CHIP_MIN_PX).toBe(false);
    for (const px of [32, 39, 40, 42, 48, 64]) expect(px >= KEYWORD_CHIP_MIN_PX).toBe(true);
  });
  it("圓章只有一個（keywords[0]），點色＝keywords[1]：和 keywords.paint 的單一圓章一致", () => {
    const look: GearLook = { kind: "sword", keywords: ["ignite", "wet"] };
    const calls = sig(gear(look, true, 48, 2));
    const bg = KW.bgOf("ignite");
    expect(calls.filter((c) => c === `fillStyle=${bg}`).length).toBe(1);
    expect(calls.filter((c) => c === `fillStyle=${KW.bgOf("wet")}`).length).toBe(0);
  });
});

describe("T-B2 快取鍵", () => {
  it("少一欄、含 px；32 與 36 不同鍵；同輸入同字串", () => {
    const look: GearLook = { kind: "axe", form: "battle", keywords: ["wet"] };
    const k = gearIconKey(look, 36);
    expect(k.split("|")).toHaveLength(10);
    expect(k.split("|").slice(-2)).toEqual(["36", "2"]);
    expect(gearIconKey(look, 32)).not.toBe(k);
    expect(gearIconKey({ keywords: ["wet"], form: "battle", kind: "axe" }, 36)).toBe(k);
  });
});

describe("T-B3 舊畫法拿掉", () => {
  const src = readSources();
  it("gearIcon.ts 沒有 motif／motifs／SMALL_ICON_MAX_PX", () => {
    const text = src.find(([p]) => p.replace(/\\/g, "/").endsWith("render/gearIcon.ts"))?.[1] ?? "";
    expect(text.length).toBeGreaterThan(500);
    expect(text).not.toMatch(/(function|const)\s+motifs?\b|\bmotifs?\(ctx/); // 檔頭註解提到「motif()／motifs() 已拿掉」，只擋定義與呼叫
    expect(text).not.toMatch(/SMALL_ICON_MAX_PX/);
  });
  it("全專案沒有從 gearIcon import 它們", () => {
    const bad = src.filter(([, t]) => /import\s*\{[^}]*\b(motif|motifs|SMALL_ICON_MAX_PX)\b[^}]*\}\s*from\s*"[^"]*gearIcon"/.test(t)).map(([p]) => p);
    expect(bad).toEqual([]);
  });
});

const item = (keywords: string[], affixes: string[] = [], kind = "sword"): GearItemInfo =>
  ({ id: "x", name_zh: "測試", appearance: { kind, keywords, rarity: "common" }, affixes: affixes.map((text_zh) => ({ text_zh })), offhand_traits_zh: [] }) as unknown as GearItemInfo;

describe("T-B5 說明框", () => {
  it("keywordNames 12 個都有名稱，內容為準（高處、召喚物）", () => {
    expect(Object.keys(appearance.keywordNames)).toEqual(KWS);
    expect(keywordName("high_ground")).toBe("高處");
    expect(keywordName("summon")).toBe("召喚物");
    expect(keywordName("nope")).toBe("nope");
  });
  it("gearKeywordLine：0／1／2 個、不認得、元素關鍵字", () => {
    expect(gearKeywordLine({ kind: "sword" })).toBeNull();
    expect(gearKeywordLine(null)).toBeNull();
    expect(gearKeywordLine({ keywords: ["ignite"] })).toBe("關鍵字：點燃");
    expect(gearKeywordLine({ keywords: ["ignite", "wet"] })).toBe("關鍵字：點燃、潮濕");
    expect(gearKeywordLine({ keywords: ["nope", "marked"] })).toBe("關鍵字：標記");
    expect(gearKeywordLine({ keywords: ["nope"] })).toBeNull();
    expect(gearKeywordLine({ element: "fire", keywords: ["marked", "prone"] })).toBe("關鍵字：點燃、標記"); // 元素關鍵字在前、最多 2 個（同圖示）
    expect(gearKeywordLine({ keywords: ["summon", "high_ground", "form"] })).toBe("關鍵字：召喚物、高處");
  });
  it("withKeywordLine：沒有關鍵字時原樣回傳", () => {
    const lines = [{ text: "a", note: null }];
    expect(withKeywordLine(lines, { kind: "sword" })).toBe(lines);
    expect(withKeywordLine(lines, { keywords: ["wet"] })).toEqual([...lines, { text: "關鍵字：潮濕", note: null }]);
  });
  it("itemTipLines：詞條行之後多一行；沒有詞條時「（沒有詞條）」再接；沒有關鍵字時和改前逐字相同", () => {
    expect(itemTipLines(item([], ["攻擊 +1"]))).toEqual([{ text: "攻擊 +1", note: null }]);
    expect(itemTipLines(item([]))).toEqual([{ text: "（沒有詞條）", note: null }]);
    expect(itemTipLines(item(["ignite"], ["攻擊 +1"]))).toEqual([{ text: "攻擊 +1", note: null }, { text: "關鍵字：點燃", note: null }]);
    expect(itemTipLines(item(["charged", "marked"]))).toEqual([{ text: "（沒有詞條）", note: null }, { text: "關鍵字：帶電、標記", note: null }]);
  });
  it("呼叫處都接上（原始碼掃描）：GearCardView 卡本體與比較列、背包身上裝備格、跑團主角面板、HeroGearPanel、UnitInfo", () => {
    const src = readSources();
    const textOf = (f: string): string => src.find(([p]) => p.replace(/\\/g, "/").endsWith(f))?.[1] ?? "";
    const card = textOf("ui/gear/GearCardView.tsx");
    expect(card).toContain('data-testid="gear-card-keywords"');
    expect(card).toContain("gearKeywordLine(item.appearance, cand.slot)");
    expect(card).toContain("itemTipLines(current, cand.slot)");
    expect(textOf("world/BagScreen.tsx")).toContain("itemTipLines(entry.item, entry.slot)");
    expect(textOf("run/RunHeroPanel.tsx")).toContain("itemTipLines(item, slot)");
    for (const f of ["ui/gear/HeroGearPanel.tsx", "ui/UnitInfo.tsx"]) expect(textOf(f), f).toContain("withKeywordLine(tipLines(e.affixes), e.appearance, e.slot)");
  });
});

describe("T-B7 不動的確認", () => {
  it("框、稀有度、主圖、寶石色：chips 的紀錄以「不畫關鍵字層」的紀錄開頭（關鍵字層只加在最後）", () => {
    for (const look of LOOKS.filter((_, i) => i % 7 === 0)) {
      const l: GearLook = { ...look, keywords: ["frozen", "marked"], rarity: "legendary" };
      const a = sig(gear(l, true, 48, 2));
      const b = sig(gear(l, false, 48, 2));
      expect(a.slice(0, b.length)).toEqual(b);
    }
  });
});
