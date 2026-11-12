import { afterAll, beforeAll, describe, expect, it } from "vitest";
import appearance from "./gearAppearance.json";
import { drawGear, gearIconKey, gearIconCanvas, gearKinds, KEYWORD_CHIP_MIN_PX, resolveGear, type GearLook } from "./gearIcon";
import { setQCanvasFactory } from "./qIcon/core";
import { clearQWeaponDefs } from "./qIcon/weapons";
import { fakeCanvasFactory, type FakeCanvasLog } from "../test/fakeCanvas";

/** QI-1a：武器、副手改畫 Q 版圖樣，圖樣畫在另建的畫布上；這裡用假畫布把那些呼叫記進 `sub`，`draw()` 回傳外層＋圖樣畫布的呼叫。 */
const sub: FakeCanvasLog = { calls: null };
function useFakeQCanvas(): void {
  beforeAll(() => {
    clearQWeaponDefs();
    setQCanvasFactory(fakeCanvasFactory(sub));
  });
  afterAll(() => {
    setQCanvasFactory(null);
    clearQWeaponDefs();
    sub.calls = null;
  });
}

/** 記錄所有呼叫的假 Canvas 2D：任何方法都可以呼叫、任何屬性都可以設定。 */
function mockCtx(): { ctx: CanvasRenderingContext2D; calls: string[] } {
  const calls: string[] = [];
  const store: Record<string, unknown> = {};
  const ctx = new Proxy(store, {
    get(target, prop: string) {
      if (prop in target) return target[prop];
      return (...args: unknown[]) => {
        calls.push(`${prop}(${args.map((a) => (typeof a === "number" ? a.toFixed(2) : typeof a === "string" ? a : typeof a)).join(",")})`);
        if (prop === "createLinearGradient" || prop === "createRadialGradient") return { addColorStop: () => undefined };
        return undefined;
      };
    },
    set(target, prop: string, value) {
      target[prop] = value;
      calls.push(`${prop}=${String(value)}`);
      return true;
    },
  }) as unknown as CanvasRenderingContext2D;
  return { ctx, calls };
}

/** QI-4b：`drawGear` 第 3 參數從 `small`（不畫舊 motif）改成 `chips`（畫關鍵字層），預設 true。 */
function draw(look: GearLook, chips = true): string[] {
  const { ctx, calls } = mockCtx();
  const inner: string[] = [];
  sub.calls = inner;
  drawGear(ctx, look, chips);
  sub.calls = null;
  return [...calls, ...inner];
}

const KEYWORDS = appearance.keywords;
const MATERIALS = [...appearance.materials, "unobtainium", undefined];
const KEYWORD_SETS: string[][] = [[], ...KEYWORDS.map((k) => [k]), [KEYWORDS[0] as string, KEYWORDS[4] as string], ["nope"], ["nope", "ignite", "wet"]];
const RARITIES = [...appearance.rarities, "mythic"];

describe("全組合不丟例外", () => {
  it("造型 × 形制（含不認得）× 材質（含不認得）× 關鍵字（無、各 1 個、2 個、不認得）", () => {
    let count = 0;
    for (const k of gearKinds()) {
      for (const form of [...k.forms.map((f) => f.id), "nope"]) {
        for (const material of MATERIALS) {
          for (const keywords of KEYWORD_SETS) {
            draw({ kind: k.id, form, ...(material !== undefined ? { material } : {}), keywords, dye: "red" });
            count += 1;
          }
        }
      }
    }
    expect(count).toBeGreaterThan(20000);
  });

  it("造型 × 形制 × 稀有度 × 畫不畫關鍵字層 × 染色", () => {
    for (const k of gearKinds()) {
      for (const form of k.forms.map((f) => f.id)) {
        for (const rarity of RARITIES) {
          for (const chips of [true, false]) {
            for (const dye of [undefined, ...appearance.dyes, "nope"]) {
              draw({ kind: k.id, form, rarity, ...(dye !== undefined ? { dye } : {}), keywords: ["ignite", "summon"] }, chips);
            }
          }
        }
      }
    }
  });

  it("不認得的造型、空物件、null 都畫得出來", () => {
    expect(() => draw({ kind: "???" })).not.toThrow();
    expect(() => draw({})).not.toThrow();
    const { ctx } = mockCtx();
    expect(() => drawGear(ctx, null)).not.toThrow();
    expect(() => drawGear(ctx, undefined, false, "head")).not.toThrow();
  });

  it("每個造型至少有一個形制，預設材質在允許內", () => {
    expect(gearKinds().length).toBe(42);
    for (const k of gearKinds()) {
      expect(k.forms.length).toBeGreaterThan(0);
      for (const f of k.forms) {
        const r = resolveGear({ kind: k.id, form: f.id });
        expect(r.form).toBe(f.id);
        expect(f.materials ?? k.materials).toContain(r.material);
      }
    }
  });
});

describe("resolveGear 預設", () => {
  it("不認得的造型退回劍；不認得的形制退回第一個", () => {
    expect(resolveGear({ kind: "???" }).kind).toBe("sword");
    expect(resolveGear({ kind: "sword", form: "???" }).form).toBe("straight");
  });
  it("布頭盔退回鐵；材質不合退回預設", () => {
    expect(resolveGear({ kind: "helmet", material: "cloth" }).material).toBe("iron");
    expect(resolveGear({ kind: "robe", material: "gold" }).material).toBe("cloth");
  });
  it("金屬染色無效，布與皮有效", () => {
    expect(resolveGear({ kind: "mail", material: "steel", dye: "red" }).dye).toBeNull();
    expect(resolveGear({ kind: "robe", dye: "red" }).dye).toBe("red");
    expect(resolveGear({ kind: "boots", dye: "black" }).dye).toBe("black");
    expect(resolveGear({ kind: "robe", dye: "pink" }).dye).toBeNull();
  });
  it("頭冠預設金、頭巾預設布；臂環預設銅、皮臂甲預設皮", () => {
    expect(resolveGear({ kind: "circlet", form: "crown" }).material).toBe("gold");
    expect(resolveGear({ kind: "circlet", form: "bandana" }).material).toBe("cloth");
    expect(resolveGear({ kind: "bracers", form: "ring" }).material).toBe("copper");
    expect(resolveGear({ kind: "bracers", form: "leather" }).material).toBe("leather");
    expect(resolveGear({ kind: "circlet", form: "bandana", material: "gold" }).material).toBe("cloth");
  });
  it("關鍵字跳過不認得的、最多 2 個；稀有度與風格退回 common", () => {
    expect(resolveGear({ keywords: ["nope", "ignite", "wet", "prone"] }).keywords).toEqual(["ignite", "wet"]);
    expect(resolveGear({ rarity: "mythic", style: "eastern" })).toMatchObject({ rarity: "common", style: "common" });
  });
  it("沒有 kind 時依欄位退回預設造型", () => {
    expect(resolveGear({}, "head").kind).toBe("helmet");
    expect(resolveGear({}, "ring_2").kind).toBe("ring");
    expect(resolveGear({ kind: "???" }, "head").kind).toBe("sword");
  });
});

describe("關鍵字層與快取鍵", () => {
  useFakeQCanvas();
  const look: GearLook = { kind: "sword", keywords: ["prone"], rarity: "rare" };

  it("chips = false 不畫關鍵字層，chips = true 會畫（QI-4b：取代「小圖不畫、大圖會畫」）", () => {
    const plain = draw({ kind: "sword", rarity: "rare" }, false);
    expect(draw(look, false)).toEqual(plain);
    expect(draw(look, true)).not.toEqual(draw({ kind: "sword", rarity: "rare" }, true));
  });
  it("不畫關鍵字層時仍保留元素混色", () => {
    const fire = draw({ kind: "sword", keywords: ["ignite"] }, false);
    expect(fire).not.toEqual(draw({ kind: "sword" }, false));
  });
  it("32px 以上畫圓章；快取鍵含 px、不再有「是否小圖」那一欄（QI-4b；鍵尾＝px、內部解析度）", () => {
    expect(KEYWORD_CHIP_MIN_PX).toBe(32);
    expect(gearIconKey(look, 32)).not.toBe(gearIconKey(look, 48));
    expect(gearIconKey(look, 32)).not.toBe(gearIconKey(look, 36));
    expect(gearIconKey(look, 36).split("|")).toHaveLength(10);
    expect(gearIconKey(look, 36).split("|").at(-2)).toBe("36");
    expect(gearIconKey(look, 36).split("|").at(-1)).toBe("2");
    expect(gearIconKey(look, 36).split("|")).not.toContain("s");
    expect(gearIconKey(look, 37).split("|")).not.toContain("l");
  });
  it("快取鍵穩定：不依賴屬性順序，不認得的值與預設值同鍵", () => {
    const a = gearIconKey({ kind: "axe", form: "battle", material: "iron", rarity: "epic", keywords: ["wet"] }, 64);
    const b = gearIconKey({ keywords: ["wet"], rarity: "epic", material: "iron", form: "battle", kind: "axe" }, 64);
    expect(a).toBe(b);
    expect(gearIconKey({ kind: "???" }, 64)).toBe(gearIconKey({}, 64));
    expect(gearIconKey({ kind: "robe", material: "gold" }, 64)).toBe(gearIconKey({ kind: "robe" }, 64));
  });
  it("沒有 DOM 時圖示畫布為 null", () => {
    expect(gearIconCanvas(look, 32)).toBeNull();
  });
});

describe("特殊規則", () => {
  useFakeQCanvas();
  it("成對武器畫兩把（Q 版圖樣：刃的多邊形呼叫數是單把的兩倍以上）", () => {
    // 短刀的刃是 poly(P.a, 3 點, 0.4)：lineWidth=0.800 只出現在刃（磨圓的粗線）；成對＝後面那把＋前面那把（halo 另畫一次），單把畫一次
    const blade = (calls: string[]): number => calls.filter((c) => c === "lineWidth=0.800").length;
    const single = blade(draw({ kind: "dagger", form: "short" }));
    const pair = blade(draw({ kind: "dual_dagger", form: "short" }));
    expect(single).toBeGreaterThan(0);
    expect(pair).toBeGreaterThanOrEqual(single * 2);
    expect(gearKinds().filter((k) => k.paired).map((k) => k.id)).toEqual(["dual_pistol", "dual_dagger"]);
  });
  it("只畫一個圓章：1 個關鍵字沒有記號，2 個多一個點版記號（QI-4b：取代「1 個兩處、2 個各一處」）", () => {
    const base = draw({ kind: "sword" }).length;
    const one = draw({ kind: "sword", keywords: ["marked"] }).length - base;
    const two = draw({ kind: "sword", keywords: ["marked", "ignite"] }).length - base;
    expect(one).toBeGreaterThan(0);
    expect(two).toBeGreaterThan(one); // 多的是記號（圓章仍只有一個，qi4bGearKeywords.test.ts 逐筆比）
  });
  it("稀有度外框：傳說線寬 3.5、優良以上有角標", () => {
    expect(draw({ rarity: "legendary" })).toContain("lineWidth=3.5");
    expect(draw({ rarity: "common" })).not.toContain("lineWidth=3.5");
    expect(draw({ rarity: "uncommon" }).length).toBeGreaterThan(draw({ rarity: "common" }).length);
  });
  it("確定性：同樣的輸入畫出同樣的呼叫", () => {
    const l: GearLook = { kind: "staff", form: "totem", material: "bone", keywords: ["frozen", "summon"], rarity: "epic" };
    draw(l); // QI-1a：第一次會量一次圓章縮放（Q 版 def 的快取），之後走快取；比較的是之後兩次
    expect(draw(l)).toEqual(draw(l));
  });
});
