// Phase QI-1b：Q 版小圖示（防具、飾品）與顯示尺寸（D3）的行為一致測試——用實際內容資料（gearAppearance.json），不手寫清單。
// 規格 docs/phases/PhaseQI-1計畫.md 第 7 節 T2（防具飾品）、T6、T8、T9；另加美術 PM 對 1a 的追加：寶石色不受關鍵字順序影響。
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import appearance from "../gearAppearance.json";
import { GEAR_DYE } from "../artPalette";
import { mix } from "../color";
import { drawGear, fitIconPx, gearIconKey, gearQDef, resolveGear } from "../gearIcon";
import { KEYWORD_COLOR, TINT_KEYWORDS } from "../palette";
import { iconCanvasPx } from "../weaponIcon";
import { iconScaleProblem, iconScaleRows } from "../../dev/layoutSmoke";
import { gemAccent, ICON_RES, setQCanvasFactory } from "./core";
import { clearQArmorDefs, hasQArmorArt, lum, Q_ARMOR_KINDS, qArmorDef, qArmorPalette, qArmorResolve, tone } from "./armor";
import { clearQWeaponDefs, qPalette, qResolve } from "./weapons";
import { fakeCanvasFactory, fakeCtx, type FakeCanvasLog } from "../../test/fakeCanvas";
import { listFiles, readFile, SRC_DIR } from "../../test/sourceScan";

interface KindJson { id: string; slotType: string; zh: string; forms: Array<{ id: string; zh: string; materials?: string[] }>; materials: string[] }
const KINDS = appearance.kinds as unknown as KindJson[];
const ARMOR_TYPES = new Set(["head", "body", "hands", "feet", "ring", "neck"]);
const ARMOR_KINDS = KINDS.filter((k) => ARMOR_TYPES.has(k.slotType));
const armorPal = (look: Parameters<typeof resolveGear>[0]) => qArmorPalette(qArmorResolve(resolveGear(look)));

describe("T2 gearAppearance.json 的防具、飾品每一款都有 Q 版圖樣", () => {
  it("kind × form 都有圖樣、款名與 JSON 一致；總數 44（需求 1.1：防具 18 種 37 款＋飾品 3 種 7 款）", () => {
    let count = 0;
    for (const k of ARMOR_KINDS) {
      expect(hasQArmorArt(k.id), k.id).toBe(true);
      expect(Q_ARMOR_KINDS[k.id]?.slot, k.id).toBe(k.slotType);
      for (const f of k.forms) {
        count += 1;
        expect(Q_ARMOR_KINDS[k.id]?.forms[f.id], `${k.id}/${f.id}`).toBe(f.zh);
        const def = qArmorDef(qArmorResolve(resolveGear({ kind: k.id, form: f.id })));
        expect(def?.meta.r).toMatchObject({ kind: k.id, form: f.id });
        expect(def?.zh).toBe(f.zh);
        expect(gearQDef({ kind: k.id, form: f.id }, resolveGear({ kind: k.id, form: f.id }))?.d).toBe(def?.d); // 裝備格走的就是這一款
      }
    }
    expect(ARMOR_KINDS.length).toBe(21);
    expect(count).toBe(44);
    // 清單兩邊一樣多：Q 版沒有 JSON 以外的種類
    expect(Object.keys(Q_ARMOR_KINDS).sort()).toEqual(ARMOR_KINDS.map((k) => k.id).sort());
  });
  it("沒有 kind 時照欄位預設造型（需求 2.4 第 4 列）；不認得的 kind 照遊戲端退直劍", () => {
    for (const [slot, kind] of [["head", "helmet"], ["body", "mail"], ["hands", "leather_gloves"], ["feet", "boots"], ["neck", "pendant"], ["ring_1", "ring"]] as const) {
      expect(gearQDef({}, resolveGear({}, slot))?.zh, slot).toBe(Q_ARMOR_KINDS[kind]?.forms[resolveGear({ kind }).form]);
    }
    expect(gearQDef({ kind: "???" }, resolveGear({ kind: "???" }, "head"))?.zh).toBe("直劍");
  });
});

describe("T6 畫布尺寸＝顯示尺寸 × 內部解析度（D3）", () => {
  it("iconCanvasPx 對 20、24、28、32、40、42、48、64 都等於 css × ICON_RES", () => {
    expect(ICON_RES).toBe(2);
    for (const css of [20, 24, 28, 32, 40, 42, 48, 64]) expect(iconCanvasPx(css), String(css)).toBe(css * ICON_RES);
  });
  it("身上裝備格：內容寬 42～52（含小數）回傳整數且 ≤ 48", () => {
    for (let w = 42; w <= 52; w += 0.25) {
      const px = fitIconPx(w);
      expect(Number.isInteger(px), String(w)).toBe(true);
      expect(px).toBeLessThanOrEqual(48);
      expect(px).toBe(Math.min(48, Math.floor(w - 4)));
    }
    expect(fitIconPx(52)).toBe(48);
    expect(fitIconPx(44.67)).toBe(40);
  });
  it("styles/ 沒有任何規則再設定 .gear-icon／.weapon-icon 的 width／height", () => {
    const styles = new URL("styles/", SRC_DIR);
    const files = listFiles(styles, (p) => p.endsWith(".css"));
    expect(files.length).toBeGreaterThan(5);
    const bad: string[] = [];
    for (const path of files) {
      const css = readFile(styles, path).replace(/\/\*[\s\S]*?\*\//g, "");
      for (const m of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) {
        const selectors = (m[1] ?? "").split(",").map((s) => s.trim());
        const targetsIcon = selectors.some((s) => /\.(gear|weapon)-icon(?![\w-])[^\s>+~]*$/.test(s));
        if (targetsIcon && /(^|[;{\s])(width|height)\s*:/.test(m[2] ?? "")) bad.push(`${path}: ${selectors.join(", ")}`);
      }
    }
    expect(bad).toEqual([]);
  });
  it("元件直接畫在顯示尺寸：背包格 42、套組 40、身上裝備格 fit；GearIcon／WeaponIcon 的畫布寬高用 iconCanvasPx", () => {
    const src = (p: string): string => readFile(SRC_DIR, p);
    expect(src("world/BagScreen.tsx")).toContain("size={42}");
    expect(src("world/BagScreen.tsx").match(/<GearIcon [^>]*\bfit\b/g)?.length).toBe(2);
    expect(src("world/RangeClassPick.tsx")).toMatch(/<GearIcon [^>]*size=\{40\}/);
    expect(src("ui/GearIcon.tsx")).toContain("iconCanvasPx(px)");
    expect(src("ui/WeaponIcon.tsx")).toContain("iconCanvasPx(size)");
  });
  it("iconScaleProblem：整數、相等通過；被縮放、小數不通過", () => {
    expect(iconScaleProblem({ name: "a", cssW: 42, cssH: 42, canvasW: 84, canvasH: 84 })).toBeNull();
    expect(iconScaleProblem({ name: "b", cssW: 40, cssH: 40, canvasW: 96, canvasH: 96 })).toMatch(/被 CSS 縮放/);
    expect(iconScaleProblem({ name: "c", cssW: 44.67, cssH: 44.67, canvasW: 96, canvasH: 96 })).toMatch(/不是整數/);
    expect(iconScaleProblem({ name: "d", cssW: 48, cssH: 47, canvasW: 96, canvasH: 96 })).toMatch(/被 CSS 縮放/);
    expect(iconScaleRows([])[0]?.pass).toBe(false);
    expect(iconScaleRows([{ name: "a", cssW: 32, cssH: 32, canvasW: 64, canvasH: 64 }])[0]?.pass).toBe(true);
  });
});

describe("T8 換色 tone()：照顏色判斷、不照染色名稱（需求 3.3 第 17～19 點）", () => {
  it("長袍（布）× 遊戲端染色表：紅 #db4545、藍 #4571db、紫 #8551c0、黑主色 #474a51；L ≥ 105 的不換；褐混 15% 白", () => {
    // 黑：需求 3.3 第 17 點與規格 T8 寫 #474a51；#33363d 混 10% 白的藍版是 61 + 194 × 0.1 = 80.4 → 0x50，樣張的 mix 與共用 color.ts 的 mix 都得 #474a50（需求的末位是筆誤，報告「待 PM 決定」）
    const want: Record<string, string> = { red: "#db4545", blue: "#4571db", purple: "#8551c0", black: "#474a50" };
    for (const dye of appearance.dyes) {
      const base = GEAR_DYE[dye] as string;
      const P = armorPal({ kind: "robe", dye });
      if (want[dye] !== undefined) expect(P.a, dye).toBe(want[dye]);
      else if (lum(base) >= 105) { expect(tone(base), dye).toBe("ok"); expect(P.a, dye).toBe(base); }
      else { expect(tone(base), dye).toBe("dull"); expect(P.a, dye).toBe(mix(base, "#ffffff", 0.15)); }
      expect(P.d, dye).toBe(mix(P.a, "#000000", 0.35)); // 暗色＝換亮之後的主色混黑 35%
    }
    expect(["green", "white", "gold"].map((d) => tone(GEAR_DYE[d] as string))).toEqual(["ok", "ok", "ok"]);
    expect(["red", "blue", "purple"].map((d) => tone(GEAR_DYE[d] as string))).toEqual(["vivid", "vivid", "vivid"]);
    expect(tone(GEAR_DYE["brown"] as string)).toBe("dull");
  });
  it("黑染：meta.tone === black、滾邊用未染布的米灰；兜帽混 17%", () => {
    const def = qArmorDef(qArmorResolve(resolveGear({ kind: "robe", dye: "black" })));
    expect(def?.meta.tone).toBe("black");
    expect(armorPal({ kind: "robe", dye: "black" }).t).toBe(mix("#8a8f99", "#ffe6b8", 0.42));
    expect(armorPal({ kind: "hood", dye: "black" }).a).toBe(mix("#33363d", "#ffffff", 0.17));
  });
  it("兜帽另亮一階：主色亮度 < 118 時 vivid 再乘 1.09、其餘混 15% 白；未染的皮兜帽也換亮（lifted）", () => {
    const red = armorPal({ kind: "robe", dye: "red" }).a;
    const hoodRed = armorPal({ kind: "hood", dye: "red" }).a;
    expect(lum(red)).toBeLessThan(118);
    expect(hoodRed).not.toBe(red);
    expect(lum(hoodRed)).toBeGreaterThan(lum(red));
    const leather = qArmorDef(qArmorResolve(resolveGear({ kind: "hood", material: "leather" })));
    expect(leather?.meta.lifted).toBe(true);
    expect(qArmorDef(qArmorResolve(resolveGear({ kind: "robe" })))?.meta.lifted).toBe(false);
  });
  it("元素混色：防具 25%／15%、飾品 40%／25%、晶石直接換色", () => {
    const fire = KEYWORD_COLOR["ignite"] as string;
    expect(armorPal({ kind: "plate", material: "steel", keywords: ["ignite"] }).a).toBe(mix("#a9b6c6", fire, 0.25));
    expect(armorPal({ kind: "ring", material: "gold", keywords: ["ignite"] }).a).toBe(mix("#e8bb48", fire, 0.4));
    expect(armorPal({ kind: "ring", material: "crystal", keywords: ["ignite"] }).a).toBe(fire);
  });
});

describe("寶石色：有元素關鍵字用元素色、沒有才用其他關鍵字的色，不受關鍵字順序影響（美術 PM 對 1a 的追加）", () => {
  const ids = Object.keys(KEYWORD_COLOR);
  it("表格", () => {
    const C = (k: string): string => KEYWORD_COLOR[k] as string;
    const rows: Array<[string[], string, string]> = [
      [[], "gold", "#e04060"],
      [[], "crystal", "#b8a8ff"],
      [["prone"], "gold", C("prone")],
      [["ignite"], "gold", C("ignite")],
      [["prone", "ignite"], "gold", C("ignite")],
      [["ignite", "prone"], "gold", C("ignite")],
      [["marked", "frozen"], "crystal", C("frozen")],
      [["summon", "prone"], "gold", C("prone")],
      [["prone", "summon"], "gold", C("prone")],
      [["frozen", "wet"], "gold", C("wet")],
      [["wet", "frozen"], "gold", C("wet")],
    ];
    for (const [kw, material, want] of rows) expect(gemAccent(kw, material), `${kw.join("+")}/${material}`).toBe(want);
  });
  it("12 個關鍵字的每一對：兩種順序的寶石色相同（gemAccent、武器副手 qPalette、防具飾品 qArmorPalette 都一樣）；有元素時是元素色", () => {
    for (const a of ids) {
      for (const b of ids) {
        if (a === b) continue;
        const ab = gemAccent([a, b], "gold");
        expect(gemAccent([b, a], "gold"), `${a}+${b}`).toBe(ab);
        if (TINT_KEYWORDS.has(a) || TINT_KEYWORDS.has(b)) expect([a, b].filter((k) => TINT_KEYWORDS.has(k)).map((k) => KEYWORD_COLOR[k]), `${a}+${b}`).toContain(ab);
        expect(qPalette(qResolve(resolveGear({ kind: "tome", keywords: [a, b] }))).accent, `tome ${a}+${b}`).toBe(qPalette(qResolve(resolveGear({ kind: "tome", keywords: [b, a] }))).accent);
        expect(armorPal({ kind: "ring", form: "gem", keywords: [a, b] }).accent, `ring ${a}+${b}`).toBe(armorPal({ kind: "ring", form: "gem", keywords: [b, a] }).accent);
      }
    }
  });
});

describe("T9 防具飾品：確定性與不丟例外（假畫布）", () => {
  const log: FakeCanvasLog = { calls: null };
  beforeAll(() => {
    clearQWeaponDefs();
    clearQArmorDefs();
    setQCanvasFactory(fakeCanvasFactory(log));
  });
  afterAll(() => {
    setQCanvasFactory(null);
    clearQWeaponDefs();
    clearQArmorDefs();
  });
  const record = (fn: () => void): string[] => {
    const calls: string[] = [];
    log.calls = calls;
    fn();
    log.calls = null;
    return calls;
  };

  it("每款 × 材質（含不認得）× 染色 × 關鍵字（無、1、2、不認得）× 稀有度 × 尺寸（32、48）畫兩次呼叫紀錄相同", () => {
    const KEYWORD_SETS: string[][] = [[], ["ignite"], ["charged", "marked"], ["nope"]];
    const seen = new Set<string>();
    let combos = 0;
    for (const k of ARMOR_KINDS) {
      for (const f of k.forms) {
        for (const material of [...appearance.materials, "unobtainium"]) {
          for (const dye of [null, "black", "red"]) {
            for (const keywords of KEYWORD_SETS) {
              for (const rarity of ["common", "legendary", "mythic"]) {
                const look = { kind: k.id, form: f.id, material, dye, keywords, rarity };
                const key = gearIconKey(look, 48);
                if (seen.has(key)) continue;
                seen.add(key);
                for (const px of [32, 48]) {
                  const gear = (): void => drawGear(fakeCtx(log, px * 2, px * 2), look, px <= 36, undefined, px, 2);
                  const once = record(gear);
                  expect(once.length).toBeGreaterThan(0);
                  expect(record(gear)).toEqual(once);
                }
                combos += 1;
              }
            }
          }
        }
      }
    }
    expect(combos).toBeGreaterThan(44 * 4 * 2);
  });
  it("規則 6（美術 PM 驗收 1a）：戰錘、釘頭錘的錘柄在圖示是 #a06a36（亮一階），連枷照舊 #6a4420", () => {
    const fills = (form: string): string[] => record(() => drawGear(fakeCtx(log, 64, 64), { kind: "hammer", form, material: "iron" }, true, undefined, 32, 2)).filter((c) => c.startsWith("fillStyle="));
    for (const form of ["warhammer", "mace"]) {
      expect(fills(form), form).toContain("fillStyle=#a06a36");
      expect(fills(form), form).not.toContain("fillStyle=#6a4420");
    }
    expect(fills("flail")).toContain("fillStyle=#6a4420");
  });
  it("小圖仍保留元素混色；>36px 畫關鍵字小圖樣", () => {
    const at = (look: Parameters<typeof resolveGear>[0], px: number): string[] => record(() => drawGear(fakeCtx(log, px * 2, px * 2), look, px <= 36, undefined, px, 2));
    expect(at({ kind: "plate", keywords: ["ignite"] }, 32)).not.toEqual(at({ kind: "plate" }, 32));
    expect(at({ kind: "plate", keywords: ["marked"] }, 32)).toEqual(at({ kind: "plate" }, 32)); // 非元素關鍵字、小圖：板甲沒有寶石，畫面一樣
    expect(at({ kind: "plate", keywords: ["marked"] }, 48)).not.toEqual(at({ kind: "plate" }, 48));
  });
});
