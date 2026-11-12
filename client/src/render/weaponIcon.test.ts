// Phase 3T-4b：武器小圖示的斜放角度。QI-1a 起換成 Q 版圖樣：方向畫在畫法裡，改看 Q 版 `def` 的 `meta.diag`（斜放）與小圖樣位置。
import { describe, expect, it } from "vitest";
import { SPOTS } from "./qIcon/weapons";
import { weaponIconDef } from "./weaponIcon";

const meta = (kind: string, form?: string) => {
  const def = weaponIconDef({ kind, ...(form !== undefined ? { form } : {}) });
  if (def === null) throw new Error(`no Q art for ${kind}`);
  return def.meta;
};

describe("武器小圖示斜放", () => {
  it("長條武器一律 45° 斜放（握把左下、作用端右上）；長槍、霰彈槍、弩也斜放（槍口朝右上），小圖樣用槍那一組位置", () => {
    for (const kind of ["sword", "axe", "hammer", "staff", "bow", "scythe", "whip", "spear", "dagger", "greatsword"]) {
      expect(meta(kind).diag).toBe(true);
      expect(meta(kind).spots).toEqual(SPOTS.diag);
    }
    for (const kind of ["shotgun", "longgun", "crossbow"]) expect(meta(kind).diag).toBe(true);
    for (const kind of ["shotgun", "longgun", "pistol", "dual_pistol"]) expect(meta(kind).spots).toEqual(SPOTS.gun);
  });

  it("手槍（只斜 −0.42）、拳套（鐵拳、爪直立）、盾、書、法器珠不算斜放；拳刃是 45° 斜放（3T-4c → QI-1a）", () => {
    expect(meta("pistol").diag).toBe(false);
    expect(meta("fist", "knuckle").diag).toBe(false);
    expect(meta("fist", "claw").diag).toBe(false);
    expect(meta("fist", "katar").diag).toBe(true);
    expect(meta("fist", "katar").spots).toEqual(SPOTS.diag);
    for (const kind of ["round_shield", "kite_shield", "tome", "orb"]) {
      expect(meta(kind).diag).toBe(false);
      expect(meta(kind).spots).toEqual(SPOTS.block);
    }
  });
});
