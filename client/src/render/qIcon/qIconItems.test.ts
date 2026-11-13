// Phase QI-7：物品的 Q 版小圖示（第⑥批，`qIcon/items.ts`）、快取（`render/itemIcon.ts`）與 `legacy48.ts` 的 `ART.item`。
// 需求 docs/art/Q版小圖示-物品移植需求.md；和樣張逐像素（指紋）比對在開發頁 `item-gallery.html?set=hash`（報告第 4 節），這裡鎖住清單、框與資料一致性。
import { parse } from "yaml";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import itemsYaml from "../../../../content/world/items.yaml?raw";
import { fakeCanvasFactory, fakeCtx, type FakeCanvasLog } from "../../test/fakeCanvas";
import { GEAR_RARITY } from "../artPalette";
import { clearItemIconCache, gainItemIconId, hasItemIcon, itemIconCanvas, itemIconKey } from "../itemIcon";
import { ICON_RES, outlinePx, setQCanvasFactory } from "./core";
import * as QI from "./items";
import { ART } from "./legacy48";

const log: FakeCanvasLog = { calls: null };
beforeAll(() => setQCanvasFactory(fakeCanvasFactory(log)));
afterAll(() => {
  setQCanvasFactory(null);
  clearItemIconCache();
  log.calls = null;
});
function outer(fn: (c: CanvasRenderingContext2D) => void): string[] {
  const own: FakeCanvasLog = { calls: [] };
  fn(fakeCtx(own));
  return own.calls ?? [];
}
function inner(fn: () => void): string[] {
  log.calls = [];
  try {
    fn();
    return log.calls;
  } finally {
    log.calls = null;
  }
}

interface Item { id: string; kind: string; color?: string; rare?: boolean }
const CONTENT = (parse(itemsYaml) as { items: Item[] }).items;
const n3 = (v: number): string => v.toFixed(3);

describe("T1 清單（需求第 2 節：37 個）", () => {
  it("37 個：藥與草 4、投擲瓶 5、補給 1、通用材料 5、雲嶺 8、荒原 6、染料 6、通用 2", () => {
    const n = (g: QI.ItemGroup) => QI.list(g).length;
    expect(QI.list().length).toBe(37);
    expect([n("potion"), n("throw"), n("supply"), n("mat"), n("cloud"), n("ashen"), n("dye"), n("gain")]).toEqual([4, 5, 1, 5, 8, 6, 6, 2]);
  });
  it("content/world/items.yaml 的 35 個都有圖示（表裡沒有的＝0）；類別和 kind 對得上", () => {
    expect(CONTENT.length).toBe(35);
    expect(CONTENT.filter((i) => QI.ICON[i.id] === undefined).map((i) => i.id)).toEqual([]);
    const catOf: Record<string, readonly string[]> = { consumable: ["consumable", "throwable"], material: ["material"], dye: ["dye"], supply: ["supply"] };
    for (const i of CONTENT) expect(catOf[i.kind], i.id).toContain(QI.ICON[i.id]!.cat);
  });
  it("染料六色＝items.yaml 的 color；稀有四個＝items.yaml 的 rare，且一律品質 3（美術 PM 決定）", () => {
    for (const i of CONTENT.filter((x) => x.kind === "dye")) expect(QI.ICON[i.id]!.color, i.id).toBe(i.color);
    const rare = CONTENT.filter((i) => i.rare === true).map((i) => i.id).sort();
    expect(QI.list().filter((e) => e.entry.rare === true).map((e) => e.id).sort()).toEqual(rare);
    for (const id of rare) expect(QI.ICON[id]!.tier, id).toBe(3);
    for (const e of QI.list().filter((x) => x.entry.cat === "material")) expect(e.entry.tier, e.id).toBeDefined();
  });
  it("同題材直接呼叫前幾批（src）；ART.item 四款搬進 legacy48", () => {
    const src = (id: string) => QI.ICON[id]?.src;
    expect([src("item_hp_potion_small"), src("item_mana_potion"), src("item_fire_flask"), src("item_fine_material"), src("item_supplies"), src("gain_gear")]).toEqual([
      "style:item.item_hp_potion_small",
      "style:item.item_mana_potion",
      "style:item.item_fire_flask",
      "style:item.item_fine_material",
      "b7:ration",
      "b4:skeleton.strike",
    ]);
    expect(Object.keys(ART.item)).toEqual(["item_hp_potion_small", "item_mana_potion", "item_fire_flask", "item_fine_material"]);
    expect(ART.item.item_fire_flask.pre).toBeTypeOf("function");
  });
  it("用到的大小：物品 42／32／28／24，通用只有 28；飛行比例：霧晶 0.77、熔心晶 0.82、其他 0.8", () => {
    for (const { id, entry } of QI.list()) expect([...entry.sizes], id).toEqual(entry.grp === "gain" ? [28] : [42, 32, 28, 24]);
    expect(QI.glyphPx("item_mist_crystal", 28)).toBeCloseTo(28 * 0.77, 9);
    expect(QI.glyphPx("item_molten_heart", 28)).toBeCloseTo(28 * 0.82, 9);
    expect(QI.glyphPx("item_essence", 28)).toBeCloseTo(22.4, 9);
    expect(QI.glyphPx("item_essence", 42)).toBeCloseTo(36.12, 9);
  });
});

describe("T2 框線色、類別底色（需求第 4 節第 1 點）", () => {
  it("材料＝GEAR_RARITY 的 common／rare／epic；其他一律褐金 #8a6a3a（不是 common 的灰）", () => {
    expect(QI.rimOf("item_coarse_material")).toBe(GEAR_RARITY["common"]);
    expect(QI.rimOf("item_fine_material")).toBe(GEAR_RARITY["rare"]);
    expect(QI.rimOf("item_superior_material")).toBe(GEAR_RARITY["epic"]);
    expect(QI.rimOf("item_living_bone")).toBe(GEAR_RARITY["epic"]);
    for (const id of ["item_hp_potion_small", "item_fire_flask", "item_supplies", "item_dye_snow"]) expect(QI.rimOf(id), id).toBe("#8a6a3a");
    expect(QI.NEUTRAL_RIM).not.toBe(GEAR_RARITY["common"]);
  });
  it("後端 rare＝true 的材料一律 epic；非材料不受 rare 影響", () => {
    expect(QI.rimOf("item_wolf_fang", { rare: true })).toBe(GEAR_RARITY["epic"]);
    expect(QI.rimOf("item_wolf_fang", { rare: false })).toBe(GEAR_RARITY["common"]);
    expect(QI.rimOf("item_hp_potion_small", { rare: true })).toBe("#8a6a3a");
  });
  it("類別底色照 itemIcons.js 的 CAT（消耗品綠、投擲瓶藍、補給褐、材料灰、染料紫），漸層到 #1a1612", () => {
    expect(QI.ITEM_CAT_BG).toEqual({ consumable: "#2a3a30", throwable: "#2a3040", supply: "#3a3020", material: "#2e2a26", dye: "#30283a" });
    const calls = outer((c) => QI.bagFrame(c, "item_water_flask", 42));
    expect(calls).toContain(`roundRect(0.000,0.000,42.000,42.000,${n3(42 * 0.16)})`);
    expect(calls).toContain("stop(0.000,#2a3040)");
    expect(calls).toContain("stop(1.000,#1a1612)");
    expect(calls).toContain(`lineWidth=${n3(Math.max(1.5, 42 * 0.035))}`);
    expect(calls).toContain("strokeStyle=#8a6a3a");
    expect(outer((c) => QI.bagFrame(c, "item_dye_jade", 24))).toContain("lineWidth=1.500");
  });
});

describe("T3 染料顏色從後端來（開發 PM 定第 5 節第 1 點 (a)）", () => {
  it("表裡沒有的染料 id 有 color 就畫 dyeArt；沒有 color 的未知 id 沒有圖示", () => {
    expect(hasItemIcon("item_dye_new")).toBe(false);
    expect(hasItemIcon("item_dye_new", "#123456")).toBe(true);
    expect(QI.entryOf("item_dye_new", { color: "#123456" })).toMatchObject({ cat: "dye", color: "#123456", frame: "bag" });
    expect(QI.rimOf("item_dye_new", { color: "#123456" })).toBe("#8a6a3a");
    expect(QI.entryOf("item_ghost")).toBeNull();
  });
  it("表裡的染料：後端給的 color 優先（不同色就是另一張圖）", () => {
    expect(QI.entryOf("item_dye_ink")!.color).toBe("#2B2B2B");
    expect(QI.entryOf("item_dye_ink", { color: "#000000" })!.color).toBe("#000000");
    expect(QI.entryOf("item_dye_ink", { color: "#2B2B2B" })).toBe(QI.ICON["item_dye_ink"]);
  });
});

describe("T4 框的種類、飛行圓、外框與貼圖（需求第 4 節第 2～5 點）", () => {
  it("frameOf：28＝飛行圓、其他大小＝背包框；通用永遠飛行圓；opt.frame 優先", () => {
    expect(QI.frameOf("item_essence", 28)).toBe("fly");
    for (const px of [42, 32, 24]) expect(QI.frameOf("item_essence", px)).toBe("bag");
    expect(QI.frameOf("gain_item", 42)).toBe("fly");
    expect(QI.frameOf("item_essence", 28, { frame: "bag" })).toBe("bag");
    expect(QI.frameOf("item_essence", 42, { frame: "fly" })).toBe("fly");
  });
  it("飛行圓：照 GainIcon（深底 #2a2018、r 13/28、金邊 #e8bb48 線寬 1.6/28），圖樣裁在 r 12.2/28；物品圓直徑 26，和裝備的 32 不同（第 8 點選 (a)）", () => {
    const calls = outer((c) => QI.paint(c, "item_wolf_fang", 28, 2));
    expect(calls).toContain("arc(14.000,14.000,13.000,0.000,6.283)");
    expect(calls).toContain("fillStyle=#2a2018");
    expect(calls).toContain("strokeStyle=#e8bb48");
    expect(calls).toContain("lineWidth=1.600");
    expect(calls).toContain("arc(14.000,14.000,12.200,0.000,6.283)");
    expect(calls.indexOf("clip()")).toBeLessThan(calls.findIndex((s) => s.startsWith("drawImage(")));
    expect(QI.FLY_R * 2 * 28).toBeCloseTo(26, 9);
  });
  it("外框照顯示大小（24→1.2、28→1.4、32／42→1.6）；24、28 的圖樣是 small（≤24px）", () => {
    for (const [px, ow] of [[24, 1.2], [28, 1.4], [32, 1.6], [42, 1.6]] as const) expect(outlinePx(px)).toBeCloseTo(ow, 9);
    const smallOf = (px: number): boolean => QI.glyphPx("item_essence", px) <= 24;
    expect([24, 28, 32, 42].map(smallOf)).toEqual([true, true, false, false]);
  });
  it("圖樣照原尺寸貼到整數裝置像素（blit）：42 的背包框，圖樣 36.12 → 畫布 72、貼在 (3,3)", () => {
    const calls = outer((c) => QI.paint(c, "item_essence", 42, 2));
    expect(calls.find((s) => s.startsWith("drawImage("))).toBe("drawImage(canvas(72x72),3.000,3.000,36.000,36.000)");
  });
  it("canvas：邊長＝顯示 × res", () => {
    for (const [px, res] of [[42, 2], [24, 1], [28, 2]] as const) expect(QI.canvas("item_cinnabar", px, res).width).toBe(px * res);
  });
});

describe("T5 快取與飛行圖示 id（render/itemIcon.ts）", () => {
  it("同鍵共用一張；鍵含大小、res、框、染料色、稀有；表裡沒有回 null", () => {
    const a = itemIconCanvas("item_cinnabar", 24, ICON_RES, { frame: "bag" });
    expect(itemIconCanvas("item_cinnabar", 24, ICON_RES, { frame: "bag" })).toBe(a);
    expect(itemIconCanvas("item_cinnabar", 24, ICON_RES, { frame: "bag", rare: true })).not.toBe(a);
    expect(itemIconKey("x", 24, 2, { frame: "fly", color: "#fff", rare: false })).toBe("x|24|2|fly|#fff|false");
    expect(itemIconCanvas("item_ghost", 24)).toBeNull();
    expect(inner(() => itemIconCanvas("item_cinnabar", 24, ICON_RES, { frame: "bag" }))).toEqual([]);
  });
  it("飛行：表裡有的物品畫自己的、其他物品 gain_item、裝備 gain_gear", () => {
    expect(gainItemIconId("item_living_bone", false)).toBe("item_living_bone");
    expect(gainItemIconId("item_ghost", false)).toBe("gain_item");
    expect(gainItemIconId("item_dye_new", false, "#abcdef")).toBe("item_dye_new");
    expect(gainItemIconId("g_sword", true)).toBe("gain_gear");
  });
});
