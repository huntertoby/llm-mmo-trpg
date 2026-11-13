// RG-6：單挑插圖支援非劍的主手（docs/art/RG樣張.md 9.9.1～9.9.5）。畫法本身由開發頁和樣張逐像素比（node 沒有畫布）；這裡鎖分組表與接線。
import { describe, expect, it } from "vitest";
import { crossGroup, FACE, FACE_KIND, GROUP_POSE, HERO_POSE, PROP, propOf, silGroup } from "../render/duelArt";
import { gearKinds } from "../render/gearResolve";
import { BEAST_CLAW } from "../render/qIcon/beastClaw";
import { mainKindOf, mainWeaponOf } from "./duelArtPlan";

const LOOK = { template_id: "hero", doll_look: null, weapon_id: "one_handed_sword", weapon_class: "melee", race_look: null, equipment: [] };

describe("grouping tables (9.9.1)", () => {
  it("silhouette groups: bow / aim / staff, everything else held", () => {
    expect(silGroup("bow")).toBe("bow");
    for (const k of ["crossbow", "longgun", "shotgun", "pistol", "dual_pistol"]) expect(silGroup(k)).toBe("aim");
    expect(silGroup("staff")).toBe("staff");
    for (const k of ["sword", "greatsword", "spear", "axe", "hammer", "scythe", "whip", "dagger", "dual_dagger", "fist", "future_kind", null, undefined]) expect(silGroup(k)).toBe("held");
  });
  it("cross groups: head / gun / open / block, everything else blade", () => {
    for (const k of ["axe", "hammer", "scythe", "staff"]) expect(crossGroup(k)).toBe("head");
    for (const k of ["longgun", "shotgun"]) expect(crossGroup(k)).toBe("gun");
    for (const k of ["bow", "crossbow", "whip"]) expect(crossGroup(k)).toBe("open");
    for (const k of ["fist", "dagger", "dual_dagger", "pistol", "dual_pistol"]) expect(crossGroup(k)).toBe("block");
    for (const k of ["sword", "greatsword", "spear", "future_kind", null]) expect(crossGroup(k)).toBe("blade");
  });
  it("every main-hand kind falls into a group; every prop-silhouette kind has a PROP entry", () => {
    const kinds = gearKinds().map((k) => k.id);
    for (const k of ["bow", "crossbow", "longgun", "shotgun", "pistol", "dual_pistol", "staff"]) expect(kinds).toContain(k);
    for (const k of kinds) if (silGroup(k) !== "held") expect(PROP[k], k).toBeDefined();
  });
  it("sword is untouched: no FACE row, held pose is HERO_POSE", () => {
    expect(FACE["blade"]).toBeUndefined();
    expect(FACE_KIND["sword"]).toBeUndefined();
    expect(GROUP_POSE["held"]).toBeUndefined();
    expect(HERO_POSE).toEqual({ arm: -0.5, wpn: 1.2, lean: 0.05 });
  });
  it("whip has no humanoid row (crosses like the sword), bow and crossbow do (D-1)", () => {
    expect(FACE_KIND["whip"]?.man).toBeUndefined();
    expect(FACE["open"]?.man).toBeDefined();
  });
});

describe("hero main-hand kind (9.9.5 #1)", () => {
  it("equipment look first, else the weapon id", () => {
    expect(mainKindOf(mainWeaponOf({ ...LOOK, equipment: [{ slot: "main_hand", appearance: { kind: "bow", form: "short", material: "wood" } }] } as never))).toEqual({ kind: "bow", form: "short", material: "wood", element: null });
    expect(mainKindOf(mainWeaponOf(LOOK as never))?.kind).toBe("sword");
    expect(mainKindOf({ kind: BEAST_CLAW })).toBeNull();
  });
});

describe("prop icon (9.9.5 #6)", () => {
  it("dual pistols resolve a pistol icon through resolveGear (not the paired icon)", () => {
    const p = propOf({ kind: "dual_pistol", form: "flintlock", material: "steel" }, null);
    expect(p.kind).toBe("dual_pistol");
    expect(p.def).not.toBeNull();
  });
});
