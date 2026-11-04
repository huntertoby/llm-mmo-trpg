// RT-1 區域主題點綴：`content/ui/region_themes.yaml` 的前端結構檢查、各區挑選、退回 hub、四角飾件、CSS 變數與畫面堆疊。
import { describe, expect, it } from "vitest";
import { CORNER_AT, CORNER_KINDS, cornerLayers, cornerShapes, cornerSvg } from "./regionCorners";
import { currentTheme, FALLBACK_THEME, parseRegionThemes, pushRegion, REGION_THEMES, regionThemeFor, themeCssVars, worldRegion } from "./regionTheme";

const OK = `
plaques:
  crystal: {top: "#2a2a5a", bottom: "#1a1a3a"}
themes:
  hub: {accent: "#a898ff", corner: filigree, plaque: crystal, portrait_ring: "#a898ff", ink: "#22305a", seal: "#7a5ad0"}
`;

describe("region_themes.yaml（build 時匯入）", () => {
  it("內建的表沒有錯誤，七區（含 hub、capital）都在", () => {
    expect(REGION_THEMES.errors).toEqual([]);
    expect(Object.keys(REGION_THEMES.themes).sort()).toEqual(["arcane_hub", "ashen_waste", "capital", "cloud_ridge", "crystal_crown", "frost_tide", "hub"]);
  });

  it("六種飾件都有區用到", () => {
    expect(new Set(Object.values(REGION_THEMES.themes).map((t) => t.corner))).toEqual(new Set(CORNER_KINDS));
  });

  it.each([
    ["cloud_ridge", "cloud", "jade", "#6aa84a"],
    ["ashen_waste", "rivet", "iron", "#ff6a1a"],
    ["capital", "filigree", "crystal", "#a898ff"],
    ["crystal_crown", "shard", "marble", "#8ab0ff"],
    ["arcane_hub", "gear", "brass", "#4ad0c8"],
    ["frost_tide", "shell", "sea", "#6ac0e8"],
  ])("%s：飾件 %s、標題牌 %s、強調色與頭像框 %s", (region, corner, plaque, accent) => {
    const t = regionThemeFor(region);
    expect([t.id, t.corner, t.plaque, t.accent, t.portrait_ring]).toEqual([region, corner, plaque, accent, accent]);
    expect(t.plaqueColors).toEqual(REGION_THEMES.plaques[plaque]);
  });

  it.each([null, undefined, "", "nowhere"])("拿不到區域（%s）時用 hub", (region) => {
    const t = regionThemeFor(region);
    expect(t.id).toBe(FALLBACK_THEME);
    expect(t.corner).toBe("filigree");
  });

  it("RT-3 的欄位：墨色、封蠟三區不同；荒原火星、主城紫晶光、雲嶺沒有", () => {
    const [cloud, ashen, capital] = ["cloud_ridge", "ashen_waste", "capital"].map((r) => regionThemeFor(r));
    expect(new Set([cloud?.ink, ashen?.ink, capital?.ink]).size).toBe(3);
    expect(new Set([cloud?.seal, ashen?.seal, capital?.seal]).size).toBe(3);
    expect([cloud?.wait_fx, ashen?.wait_fx, capital?.wait_fx]).toEqual(["none", "ember", "crystal"]);
  });
});

describe("結構檢查（壞掉的那筆略過、退回 hub）", () => {
  it("正確的範例沒有錯誤", () => {
    expect(parseRegionThemes(OK).errors).toEqual([]);
  });

  it.each([
    ['corner: filigree', 'corner: dragon', "未知的 corner"],
    ['accent: "#a898ff"', 'accent: "purple"', "accent 必須是 #rrggbb"],
    ['portrait_ring: "#a898ff"', 'portrait_ring: "#abc"', "portrait_ring 必須是 #rrggbb"],
    ["plaque: crystal", "plaque: gold", "未知的 plaque"],
    ['seal: "#7a5ad0"', 'seal: "#7a5ad0", wait_fx: fireworks', "未知的 wait_fx"],
    ['seal: "#7a5ad0"', 'seal: "#7a5ad0", glow: "#ffffff"', "未知欄位 glow"],
    [', seal: "#7a5ad0"', "", "seal 必須是 #rrggbb"],
  ])("把 %s 改成 %s → %s", (from, to, msg) => {
    const t = parseRegionThemes(OK.replace(from, to));
    expect(t.errors.join("\n")).toContain(msg);
    expect(t.themes.hub).toBeUndefined();
    expect(regionThemeFor("hub", t).corner).toBe("filigree"); // 整份壞掉時的最後退路
  });

  it("標題牌顏色不對、沒有 hub、YAML 壞掉都會報", () => {
    expect(parseRegionThemes(OK.replace('bottom: "#1a1a3a"', 'bottom: "blue"')).errors.join()).toContain("plaques.crystal：bottom");
    expect(parseRegionThemes(OK.replace("  hub:", "  capital:")).errors.join()).toContain("缺少 hub 主題");
    expect(parseRegionThemes("themes: [").errors[0]).toContain("YAML 格式錯誤");
  });
});

describe("四角飾件（18×18，程式繪製）", () => {
  const c = { accent: "#ff6a1a", seal: "#b8432f" };

  it("六種畫法彼此不同，都只用 SVG 形狀", () => {
    const shapes = CORNER_KINDS.map((k) => cornerShapes(k, c));
    expect(new Set(shapes).size).toBe(6);
    for (const s of shapes) expect(s).toMatch(/^<(path|circle|g|rect)/);
  });

  it("強調色與封蠟色會用上（雲嶺的朱紅點、荒原的餘燼）", () => {
    expect(cornerShapes("cloud", c)).toContain(c.seal);
    expect(cornerShapes("rivet", c)).toContain(c.accent);
    expect(cornerShapes("filigree", c)).toContain(c.accent);
  });

  it("四角是左上的鏡射；背景圖層有四層、各 18px", () => {
    expect(cornerSvg("rivet", c, "tl")).toContain("scale(1 1)");
    expect(cornerSvg("rivet", c, "tr")).toContain("translate(18 0) scale(-1 1)");
    expect(cornerSvg("rivet", c, "bl")).toContain("translate(0 18) scale(1 -1)");
    expect(cornerSvg("rivet", c, "br")).toContain("translate(18 18) scale(-1 -1)");
    const layers = cornerLayers("rivet", c);
    expect(layers.split("data:image/svg+xml").length - 1).toBe(CORNER_AT.length);
    expect(layers.match(/18px 18px no-repeat/g)).toHaveLength(4);
    expect(layers).toContain("right 2px bottom 2px");
  });
});

describe("目前區域與 CSS 變數", () => {
  it("大世界：實地地圖的 region，沒有時用區域圖的；都沒有＝null（→ hub）", () => {
    expect(worldRegion({ field: { region: "ashen_waste" }, map: { region: "cloud_ridge" } })).toBe("ashen_waste");
    expect(worldRegion({ field: { region: "capital" } })).toBe("capital");
    expect(worldRegion({ field: null, map: { region: "cloud_ridge" } })).toBe("cloud_ridge");
    expect(worldRegion({})).toBeNull();
  });

  it("主題 → --rt-* 變數（強調色、頭像框、墨、封蠟、標題牌兩色、四角）", () => {
    const v = themeCssVars(regionThemeFor("cloud_ridge"));
    expect(v["--rt-accent"]).toBe("#6aa84a");
    expect(v["--rt-ring"]).toBe("#6aa84a");
    expect(v["--rt-ink"]).toBe("#1c1712");
    expect(v["--rt-seal"]).toBe("#b8432f");
    expect([v["--rt-plaque-top"], v["--rt-plaque-bottom"]]).toEqual(["#2f4a3a", "#1f3428"]);
    expect(v["--rt-corners"]).toBe(cornerLayers("cloud", regionThemeFor("cloud_ridge")));
  });

  it("畫面堆疊：大世界（荒原）裡開戰鬥（雲嶺）時用戰鬥的，戰鬥結束退回荒原，都離開退回 hub", () => {
    expect(currentTheme().id).toBe("hub");
    const world = pushRegion("ashen_waste");
    expect(currentTheme().id).toBe("ashen_waste");
    const battle = pushRegion("cloud_ridge");
    expect(currentTheme().id).toBe("cloud_ridge");
    world.set("capital"); // 下層換區域不影響上層
    expect(currentTheme().id).toBe("cloud_ridge");
    battle.pop();
    expect(currentTheme().id).toBe("capital");
    battle.set(null); // 已移除的不影響
    world.set(null);
    expect(currentTheme().id).toBe("hub");
    world.pop();
    expect(currentTheme().id).toBe("hub");
  });
});
