import { describe, expect, it } from "vitest";
import appearance from "./gearAppearance.json";
import { drawGear, gearIconKey, gearIconCanvas, gearKinds, resolveGear, SMALL_ICON_MAX_PX, type GearLook } from "./gearIcon";

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

function draw(look: GearLook, small = false): string[] {
  const { ctx, calls } = mockCtx();
  drawGear(ctx, look, small);
  return calls;
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

  it("造型 × 形制 × 稀有度 × 大小圖 × 染色", () => {
    for (const k of gearKinds()) {
      for (const form of k.forms.map((f) => f.id)) {
        for (const rarity of RARITIES) {
          for (const small of [false, true]) {
            for (const dye of [undefined, ...appearance.dyes, "nope"]) {
              draw({ kind: k.id, form, rarity, ...(dye !== undefined ? { dye } : {}), keywords: ["ignite", "summon"] }, small);
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
    expect(() => drawGear(ctx, undefined, true, "head")).not.toThrow();
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

describe("小圖與快取鍵", () => {
  const look: GearLook = { kind: "sword", keywords: ["prone"], rarity: "rare" };

  it("小圖不畫關鍵字小圖樣，大圖會畫", () => {
    const plain = draw({ kind: "sword", rarity: "rare" }, true);
    expect(draw(look, true)).toEqual(plain);
    expect(draw(look, false)).not.toEqual(draw({ kind: "sword", rarity: "rare" }, false));
  });
  it("小圖仍保留元素混色", () => {
    const fire = draw({ kind: "sword", keywords: ["ignite"] }, true);
    expect(fire).not.toEqual(draw({ kind: "sword" }, true));
  });
  it("快取鍵包含是否小圖；36px 以下為小圖", () => {
    expect(SMALL_ICON_MAX_PX).toBe(36);
    expect(gearIconKey(look, 32)).not.toBe(gearIconKey(look, 48));
    expect(gearIconKey(look, 36).split("|").at(-2)).toBe("s");
    expect(gearIconKey(look, 37).split("|").at(-2)).toBe("l");
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
  it("成對武器畫兩把（呼叫數遠多於單把）", () => {
    const single = draw({ kind: "dagger", form: "short" }).filter((c) => c.startsWith("save")).length;
    const pair = draw({ kind: "dual_dagger", form: "short" }).filter((c) => c.startsWith("save")).length;
    expect(pair).toBeGreaterThan(single);
    expect(gearKinds().filter((k) => k.paired).map((k) => k.id)).toEqual(["dual_pistol", "dual_dagger"]);
  });
  it("1 個關鍵字兩處都畫，2 個關鍵字各畫一處", () => {
    const base = draw({ kind: "sword" }).length;
    const one = draw({ kind: "sword", keywords: ["marked"] }).length - base;
    const two = draw({ kind: "sword", keywords: ["marked", "marked"] }).length - base;
    expect(one).toBeGreaterThan(0);
    expect(two).toBe(one); // 同一個關鍵字重複兩次＝各畫一處，張數相同
  });
  it("稀有度外框：傳說線寬 3.5、優良以上有角標", () => {
    expect(draw({ rarity: "legendary" })).toContain("lineWidth=3.5");
    expect(draw({ rarity: "common" })).not.toContain("lineWidth=3.5");
    expect(draw({ rarity: "uncommon" }).length).toBeGreaterThan(draw({ rarity: "common" }).length);
  });
  it("確定性：同樣的輸入畫出同樣的呼叫", () => {
    const l: GearLook = { kind: "staff", form: "totem", material: "bone", keywords: ["frozen", "summon"], rarity: "epic" };
    expect(draw(l)).toEqual(draw(l));
  });
});
