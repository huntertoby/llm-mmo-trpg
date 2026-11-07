// 6R-2（#137）：外觀選項（races.yaml 的 look_options）、快速組合、換種族保留規則、外觀選單與主城改外觀。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { WorldView } from "../api/types";
import { resolveDoll, withLookChoice } from "../render/appearance";
import { LookChangeLine, lookChangeAction } from "../world/LookChange";
import { LookPicker, lookAfterRace, pickValue, shownValue } from "./LookPicker";
import { LOOK_OPTIONS, PRESETS, applyPreset, lookBody, lookForRace, parseLookOptions, randomLook } from "./lookOptions";

describe("外觀選項（6R-2，#137）", () => {
  it("10 族都有清單；限制照美術表", () => {
    expect(Object.keys(LOOK_OPTIONS).length).toBe(10);
    expect(LOOK_OPTIONS.scalefolk?.hair).toEqual(["none"]);
    expect(LOOK_OPTIONS.elf?.beard).toEqual(["none"]);
    expect(LOOK_OPTIONS.dwarf?.beard[0]).toBe("full");
    expect(LOOK_OPTIONS.dwarf?.beard).toContain("none");
    expect(LOOK_OPTIONS.fox?.beastEars).toEqual(["fox", "cat", "wolf", "rabbit"]);
    expect(LOOK_OPTIONS.human?.eyes.length).toBe(6);
    expect(LOOK_OPTIONS.scalefolk?.eyes).toContain("#103030");
    expect(parseLookOptions(":::")).toEqual({});
  });

  it("快速組合：粗獷／柔和，種族不開放的那項略過，不存性別", () => {
    const elf = LOOK_OPTIONS.elf;
    expect(applyPreset({}, PRESETS.rugged, LOOK_OPTIONS.human)).toEqual(PRESETS.rugged);
    const soft = applyPreset({ skin: "#efd2b8" }, PRESETS.soft, elf);
    expect(soft).toEqual({ ...PRESETS.soft, skin: "#efd2b8" });
    expect(applyPreset({}, PRESETS.rugged, elf).beard).toBeUndefined(); // 精靈沒有鬍渣
    for (const p of Object.values(PRESETS)) expect(Object.keys(p)).not.toContain("gender");
  });

  it("隨機：同一個種子同一組、都在種族範圍內、柔和不配鬍子", () => {
    const opts = LOOK_OPTIONS.dwarf;
    const a = randomLook("s-1", opts);
    expect(randomLook("s-1", opts)).toEqual(a);
    for (let i = 0; i < 30; i++) {
      const r = randomLook(`s-${i}`, opts);
      expect(lookForRace(r, opts)).toEqual(r);
      if (r.lashes === true) expect(r.beard ?? "none").toBe("none");
    }
  });

  it("換種族：新種族也有的保留，沒有的清掉", () => {
    const choice = { face: "oval", hair: "twin", beard: "goatee", skin: "#d9a47a" } as const;
    expect(lookAfterRace(choice, "elf")).toEqual({ face: "oval", hair: "twin" });
    expect(lookAfterRace(choice, "scalefolk")).toEqual({ face: "oval" });
  });

  it("送出的 look 去掉空值；全空＝種族預設", () => {
    expect(lookBody({})).toBeNull();
    expect(lookBody({ hair: null, face: "heart" })).toEqual({ face: "heart" });
    expect(lookChangeAction({})).toEqual({ kind: "change_look" });
    expect(lookChangeAction({ hair: "bob" })).toEqual({ kind: "change_look", look: { hair: "bob" } });
  });

  it("沒選的列顯示種族預設；點一下換值", () => {
    expect(shownValue("beard", {}, LOOK_OPTIONS.dwarf)).toBe("full");
    expect(shownValue("hair", {}, LOOK_OPTIONS.scalefolk)).toBe("none");
    expect(shownValue("face", {}, LOOK_OPTIONS.human)).toBe("round");
    expect(pickValue({}, "beard", "none")).toEqual({ beard: "none" });
  });

  it("紙娃娃：選的外觀疊在種族外觀之後（QK-6 起新髮型照值畫）", () => {
    const base = { skin: "#000000", hair: "short" as const, beard: true };
    const look = withLookChoice(base, { skin: "#d9a47a", hair: "ponytail", beard: "none", eyes: "#3a5aa8" });
    expect(look).toEqual({ skin: "#d9a47a", hair: "ponytail", eyes: "#3a5aa8" });
    const spec = resolveDoll({
      template: "hero",
      dollLook: { skin: "#f1c9a5", skull: false, beard: false, affixes: [], traits: [], gear: {}, custom: { hair_color: "#b33a3a" } },
      team: "ally",
      summon: false,
      raceLook: LOOK_OPTIONS.human?.raceLook,
    });
    expect(spec.look.hairColor).toBe("#b33a3a");
    expect(spec.look.skin).toBe("#f1c9a5");
  });

  it("外觀選單：種族不開放的列不出現；獸耳只有獸耳族", () => {
    const fox = renderToStaticMarkup(createElement(LookPicker, { race: "fox", choice: {}, onChoice: () => undefined }));
    expect(fox).toContain("粗獷");
    expect(fox).toContain("柔和");
    expect(fox).toContain("獸耳");
    expect(fox).not.toContain('data-testid="look-beard"');
    const human = renderToStaticMarkup(createElement(LookPicker, { race: "human", choice: {}, onChoice: () => undefined }));
    expect(human).not.toContain('data-testid="look-ears"');
    expect(human).toContain("八字鬍");
    expect(renderToStaticMarkup(createElement(LookPicker, { race: "", choice: {}, onChoice: () => undefined }))).toBe("");
  });

  it("主城改外觀：不在主城時灰掉並顯示原因", () => {
    const character = (over: Partial<WorldView["character"]>): WorldView["character"] => ({ race: "human", look: null, look_change_zh: null, character_id: "c1", ...over }) as WorldView["character"];
    const away = renderToStaticMarkup(createElement(LookChangeLine, { character: character({ look_change_zh: "只有在主城能改外觀" }), busy: false, onAct: () => undefined }));
    expect(away).toContain("只有在主城能改外觀");
    expect(away).toMatch(/<button[^>]*disabled/);
    const home = renderToStaticMarkup(createElement(LookChangeLine, { character: character({}), busy: false, onAct: () => undefined }));
    expect(home).toContain("主城隨時免費");
    expect(home).not.toMatch(/<button[^>]*disabled/);
  });
});
