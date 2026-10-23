// Phase 3I-4：雙匕首、霰彈槍、手槍、雙手槍——武器外觀表（glossary）、紙娃娃主手與副手、武器小圖示。
import { describe, expect, it } from "vitest";
import { weaponLookEntry } from "../battle/glossary";
import { resolveDollT } from "./testDolls";
import { isDiagonal, weaponIconItem } from "./weaponIcon";

const base = { team: "ally", summon: false } as const;
const look = (id: string) => resolveDollT({ ...base, template: "hero_fighter", weaponId: id }).gear;

describe("第二批其他武器的外觀（Phase 3I-4）", () => {
  it("外觀表有自己的 kind／form／material，握法與資料一致", () => {
    expect(weaponLookEntry("dual_dagger")).toMatchObject({ look: { kind: "dual_dagger", form: "short", material: "iron" }, two_handed: false });
    expect(weaponLookEntry("shotgun")).toMatchObject({ look: { kind: "shotgun", form: "double" }, two_handed: true });
    expect(weaponLookEntry("pistol")).toMatchObject({ look: { kind: "pistol", form: "revolver" }, two_handed: false });
    expect(weaponLookEntry("dual_pistol")).toMatchObject({ look: { kind: "dual_pistol", form: "revolver" }, two_handed: false });
  });

  it("成對武器的紙娃娃：主手、副手各一把；霰彈槍雙手副手留空；手槍單手", () => {
    const dagger = look("dual_dagger");
    expect(dagger.main_hand).toMatchObject({ kind: "dagger" });
    expect(dagger.off_hand).toMatchObject({ kind: "dagger" });
    const pistols = look("dual_pistol");
    expect(pistols.main_hand).toMatchObject({ kind: "pistol" });
    expect(pistols.off_hand).toMatchObject({ kind: "pistol" });
    expect(look("shotgun").main_hand).toMatchObject({ kind: "shotgun" });
    expect(look("shotgun").off_hand).toBeUndefined();
    expect(look("pistol").main_hand).toMatchObject({ kind: "pistol" });
  });

  it("武器小圖示：成對武器畫成單把的造型（雙匕首斜放如匕首）", () => {
    expect(weaponIconItem("dual_dagger", "melee")).toMatchObject({ kind: "dagger" });
    expect(isDiagonal(weaponIconItem("dual_dagger", "melee").kind)).toBe(true);
    expect(weaponIconItem("dual_pistol", "ranged")).toMatchObject({ kind: "pistol" });
    expect(weaponIconItem("shotgun", "ranged")).toMatchObject({ kind: "shotgun" });
  });
});
