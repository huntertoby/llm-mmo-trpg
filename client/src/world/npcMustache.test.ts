// QK-6b（QK-8 待決 4）：頭像配件八字鬍 → 地圖紙娃娃的鬍子樣式。
import { describe, expect, it } from "vitest";
import type { NpcPortrait } from "../api/types";
import { resolveDoll } from "../render/appearance";
import { npcFieldLook, portraitDollLook } from "./npcLook";

const LIU = { look: { skin: "#f1c9a5", hair: "short", hair_color: "#2a1a10" }, gear: { body: { kind: "robe", color: "#8a6a3a" } }, extras: ["cap", "mustache"] } as unknown as NpcPortrait;
const TAVERN = { look: { skin: "#e0b088", hair: "short", hair_color: "#6a4a2a", beard: true, build: "stout" }, gear: { body: { kind: "shirt", color: "#e8dcc0" } }, extras: ["mustache"] } as unknown as NpcPortrait;

const lookOf = (p: NpcPortrait) => {
  const f = npcFieldLook({ id: "x", portrait: p });
  if (f == null) throw new Error("no look");
  return resolveDoll({ template: f.template_id, dollLook: f.doll_look, team: "ally", summon: false, weaponId: "unarmed", weaponClass: "melee" }).look;
};

describe("八字鬍畫在地圖紙娃娃上", () => {
  it("柳掌櫃（無大鬍子）→ beardStyle mustache", () => {
    expect(lookOf(LIU).beardStyle).toBe("mustache");
    expect(lookOf(LIU).beard).toBeFalsy();
  });
  it("酒館老闆已有大鬍子 → 照樣張不另畫八字鬍，大鬍子照舊", () => {
    const l = lookOf(TAVERN);
    expect(l.beard).toBe(true);
    expect(l.beardStyle).toBeUndefined();
  });
  it("頭像本身（mapExtras=false）不加，頭像自己畫配件", () => {
    expect((portraitDollLook(LIU, false) as { custom?: unknown }).custom).toBeUndefined();
  });
});
