// QK-6：外觀選項（DollLook.custom）→ Q 版外觀欄位的對照與疊加順序。
import { describe, expect, it } from "vitest";
import type { Look } from "./appearance";
import { resolveDoll, withLookChoice } from "./appearance";
import { applyLookChoice, qFrameScale } from "./qLook";
import { qUnitOf } from "./qSpec";

const BASE: Look = { skin: "#f1c9a5", hair: "short", hairColor: "#6a3d1e" };

describe("QK-6 外觀選項對照", () => {
  it("沒選任何項＝種族預設原樣（預設值不寫欄位）", () => {
    expect(applyLookChoice(BASE, {})).toEqual(BASE);
    expect(applyLookChoice(BASE, { face: "round", eye_style: "square", lashes: false })).toEqual(BASE);
  });

  it("臉型、眼睛、睫毛、體型、獸耳照樣張欄位", () => {
    const l = applyLookChoice(BASE, { face: "heart", eye_style: "big", lashes: true, frame: "slim", beast_ears: "rabbit" });
    expect(l).toMatchObject({ face: "heart", eyeStyle: "big", lashes: true, frame: "slim", beastEars: "rabbit" });
  });

  it("新髮型照值（齊肩、馬尾、雙馬尾、刺蝟），矮人光頭、髮髻", () => {
    for (const h of ["bob", "ponytail", "twin", "spiky", "none", "bun"]) expect(applyLookChoice(BASE, { hair: h }).hair).toBe(h);
    expect(applyLookChoice(BASE, { hair: "mohawk" }).hair).toBe("short");
  });

  it("鬍子：stubble→短鬍渣、八字、山羊、大鬍子、none 拿掉種族鬍子", () => {
    const dwarf: Look = { ...BASE, beard: true };
    expect(applyLookChoice(dwarf, { beard: "stubble" })).toMatchObject({ beardStyle: "short" });
    expect(applyLookChoice(dwarf, { beard: "stubble" }).beard).toBeUndefined();
    expect(applyLookChoice(BASE, { beard: "mustache" }).beardStyle).toBe("mustache");
    expect(applyLookChoice(BASE, { beard: "goatee" }).beardStyle).toBe("goatee");
    expect(applyLookChoice(BASE, { beard: "full" })).toMatchObject({ beard: true, beardStyle: "full" });
    const none = applyLookChoice(dwarf, { beard: "none" });
    expect(none.beard).toBeUndefined();
    expect(none.beardStyle).toBeUndefined();
  });

  it("疊在種族外觀之後，傳到 Q 版小人", () => {
    const spec = resolveDoll({
      template: "bandit",
      dollLook: { skin: "#a8724c", skull: false, beard: false, affixes: [], traits: [], gear: {}, hair: "short", custom: { hair: "spiky", beard: "goatee" } },
      team: "enemy",
      summon: false,
    });
    const u = qUnitOf(spec);
    expect(u.look.hair).toBe("spiky");
    expect(u.look.beardStyle).toBe("goatee");
    expect(withLookChoice({ ...BASE, beastEars: "fox" }, { beast_ears: "wolf", skin: "#d9a47a" })).toMatchObject({ beastEars: "wolf", skin: "#d9a47a" });
  });

  it("體型縮放同 qDoll.js", () => {
    expect(qFrameScale("slim")).toEqual([0.92, 1.02]);
    expect(qFrameScale("broad")).toEqual([1.08, 0.98]);
    expect(qFrameScale(undefined)).toEqual([1, 1]);
  });
});
