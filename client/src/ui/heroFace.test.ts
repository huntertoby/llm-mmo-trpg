// QK-2b（docs/art/QK-2檢查.md 小修 2）：主角頭像改 Q 版——我的角色清單、HUD 主角卡（探索、戰鬥）都用主角自己的外觀
// （種族特徵、外觀選項 `DollLook.custom`、裝備），框色＝出身區；不再是沒有外框的通用人臉。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { FieldHeroView, UnitView } from "../api/types";
import { unit } from "../battle/testFixtures";
import { resolveDoll } from "../render/appearance";
import { PORTRAIT_REGION, specFigure } from "../render/portrait";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { LOOK_OPTIONS } from "../run/lookOptions";
import { HeroCard } from "./HeroCard";
import { fieldHeroInput, heroFaceKey, heroRing, unitHeroInput } from "./heroFace";

const DRAGON = LOOK_OPTIONS["dragonkin"]!.raceLook as Record<string, unknown>;

const LOOK: FieldHeroView = {
  template_id: "hero",
  doll_look: {
    skin: "#f1c9a5",
    skull: false,
    beard: false,
    affixes: [],
    traits: [],
    gear: { body: { kind: "shirt", material: "cloth" } },
    custom: { hair: "ponytail", eye_style: "big" },
  } as unknown as FieldHeroView["doll_look"],
  weapon_id: "sword",
  weapon_class: "melee",
  race_look: DRAGON as FieldHeroView["race_look"],
  equipment: [],
};

describe("外觀 → 頭像要畫的人", () => {
  it("伺服器的外觀（FieldHeroView）照用：範本、doll_look、種族外觀、武器、裝備；沒有外觀為 null", () => {
    const input = fieldHeroInput(LOOK)!;
    expect(input).toMatchObject({ template: "hero", team: "ally", summon: false, weaponId: "sword", weaponClass: "melee" });
    expect(input.raceLook).toBe(DRAGON);
    expect(fieldHeroInput(null)).toBeNull();
    expect(fieldHeroInput(undefined)).toBeNull();
  });

  it("龍裔有角（種族特徵）；外觀選項（custom 的馬尾、大眼）照畫；不畫武器", () => {
    const fig = specFigure(resolveDoll(fieldHeroInput(LOOK)!));
    expect(fig.unit.look.horns).toBe("dragon");
    expect(fig.unit.look.hair).toBe("ponytail");
    expect(fig.unit.look.eyeStyle).toBe("big");
    expect(fig.unit.gear.main_hand).toBeUndefined();
    const plain = specFigure(resolveDoll(fieldHeroInput({ ...LOOK, race_look: null })!));
    expect(plain.unit.look.horns).toBeUndefined();
  });

  it("戰鬥的主角單位：doll_look、裝備、種族外觀（UnitView.race.look）同戰場小人", () => {
    const u = { ...unit("unit_0001", "ally", 0, 0), template_id: "hero", doll_look: LOOK.doll_look, race: { look: DRAGON } } as unknown as UnitView;
    const input = unitHeroInput(u);
    expect(input.team).toBe("ally");
    expect(input.raceLook).toBe(DRAGON);
    expect(specFigure(resolveDoll(input)).unit.look.horns).toBe("dragon");
  });

  it("快取鍵跟著外觀、區域、大小變", () => {
    const a = fieldHeroInput(LOOK)!;
    const b = fieldHeroInput({ ...LOOK, race_look: null })!;
    expect(heroFaceKey(a, "cloud_ridge", 40, 2)).not.toBe(heroFaceKey(b, "cloud_ridge", 40, 2));
    expect(heroFaceKey(a, "cloud_ridge", 40, 2)).not.toBe(heroFaceKey(a, "capital", 40, 2));
    expect(heroFaceKey(a, "cloud_ridge", 40, 2)).not.toBe(heroFaceKey(a, "cloud_ridge", 62, 2));
  });
});

describe("框色＝出身區", () => {
  it("五區與主城照 PORTRAIT_REGION；沒有出身或不認得＝傭兵金", () => {
    for (const r of ["cloud_ridge", "ashen_waste", "crystal_crown", "arcane_hub", "frost_tide", "capital"]) expect(heroRing(r)).toBe(PORTRAIT_REGION[r]![0]);
    expect(heroRing("capital")).toBe("#a898ff");
    expect(heroRing(null)).toBe("#c8a868");
    expect(heroRing("nowhere")).toBe("#c8a868");
  });

  it("主角卡有外觀時畫 Q 版頭像（不是通用臉），data-ring 是出身區的框色、不跟目前區域", () => {
    const html = renderToStaticMarkup(createElement(HeroCard, { where: "world", bars: null, hero: fieldHeroInput(LOOK), realm: "ashen_waste" }));
    expect(html).toContain('<div class="hero-card-face"><span class="hero-face"');
    expect(html).toContain('data-ring="#ff6a1a"');
    expect(html).not.toContain("hud-portrait");
    expect(html).toContain("width:62px");
  });
});

describe("三處都接上（原始碼掃描）", () => {
  it("我的角色清單：每列用 HeroFace（伺服器的 hero_look、origin_realm），不再寫死通用臉", () => {
    const src = readFile(SRC_DIR, "world/WorldCharacterPicker.tsx");
    expect(src).toContain("fieldHeroInput(c.hero_look)");
    expect(src).toContain("<HeroFace input={input} realm={c.origin_realm ?? null} size={40}");
    expect(src).toMatch(/<span className="entry-char-face">\s*<CharFace c=\{c\} \/>/);
  });

  it("探索 HUD 主角卡：外觀＋出身區；戰鬥 HUD 主角卡：主角單位＋BattleScreen 帶進來的出身區", () => {
    expect(readFile(SRC_DIR, "world/WorldHud.tsx")).toMatch(/hero=\{fieldHeroInput\(c\.hero_look \?\? view\.field\?\.hero\)\}\s*realm=\{c\.origin_realm \?\? null\}/);
    expect(readFile(SRC_DIR, "ui/Hud.tsx")).toMatch(/hero=\{unitHeroInput\(hero\)\}\s*realm=\{heroOrigin\}/);
    expect(readFile(SRC_DIR, "screens/BattleScreen.tsx")).toContain("heroOrigin={heroOrigin}");
    expect(readFile(SRC_DIR, "screens/WorldScreen.tsx")).toContain("view?.character.origin_realm");
    expect(readFile(SRC_DIR, "screens/RunScreen.tsx")).toContain("heroOrigin={run.hero.origin_realm ?? null}");
  });
});
