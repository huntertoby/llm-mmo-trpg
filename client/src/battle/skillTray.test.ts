import { afterEach, describe, expect, it, vi } from "vitest";
import type { SkillCard } from "../api/types";
import {
  actionHintText,
  isMinorSkill,
  loadSidePref,
  minorGlyph,
  saveSideCollapsed,
  sideCollapsed,
  splitSkills,
  togglePopup,
} from "./skillTray";
import type { SkillButton } from "./targeting";

function button(skillId: string): SkillButton {
  return { skillId, name: skillId, costs: [], cooldown: 0, actions: [], disabledReason: null };
}

function card(kind_id: string): SkillCard {
  return { kind_id } as unknown as SkillCard;
}

describe("splitSkills", () => {
  it("keeps actives in the main row and moves passives, reactions, stances and modifiers to the minor icons", () => {
    const buttons = ["a", "p", "b", "r", "s", "m", "unknown"].map(button);
    const cards = {
      a: card("active"),
      p: card("passive"),
      b: card("active"),
      r: card("reaction"),
      s: card("stance"),
      m: card("modifier"),
    };
    const { main, minor } = splitSkills(buttons, cards);
    expect(main.map((b) => b.skillId)).toEqual(["a", "b", "unknown"]);
    expect(minor.map((b) => b.skillId)).toEqual(["p", "r", "s", "m"]);
  });

  it("treats a skill whose card is not loaded yet as active", () => {
    expect(isMinorSkill(undefined)).toBe(false);
    expect(isMinorSkill(card("passive"))).toBe(true);
  });

  it("uses the first character of the name as the icon", () => {
    expect(minorGlyph("鐵壁姿態")).toBe("鐵");
    expect(minorGlyph("  ")).toBe("？");
  });
});

describe("togglePopup", () => {
  it("opens, switches and closes (only one open at a time)", () => {
    expect(togglePopup(null, "legend")).toBe("legend");
    expect(togglePopup("legend", "orders")).toBe("orders");
    expect(togglePopup("orders", "orders")).toBeNull();
  });
});

describe("actionHintText", () => {
  const base = { copying: false, canAct: true, ended: false, moveCount: 5, attackCount: 2 };
  it("describes the current state", () => {
    expect(actionHintText(base)).toContain("（5 格）");
    expect(actionHintText({ ...base, canAct: false })).toBe("等待中……");
    expect(actionHintText({ ...base, copying: true })).toContain("Esc 放棄");
    expect(actionHintText({ ...base, ended: true })).toBe("戰鬥結束。");
  });

  it("tells the player the summons can still be switched when only End Turn is left (3-32b)", () => {
    const idle = { ...base, moveCount: 0, attackCount: 0, summonIdle: true };
    expect(actionHintText(idle)).toContain("召喚物");
    expect(actionHintText(idle)).toContain("結束回合");
    expect(actionHintText({ ...idle, canAct: false })).toBe("等待中……");
  });
});

describe("side panel preference", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function stubStorage(store: Map<string, string>, broken = false) {
    vi.stubGlobal("window", {
      localStorage: {
        getItem: (k: string) => {
          if (broken) throw new Error("blocked");
          return store.get(k) ?? null;
        },
        setItem: (k: string, v: string) => {
          if (broken) throw new Error("blocked");
          store.set(k, v);
        },
      },
    });
  }

  it("defaults to collapsed only on a narrow window, then follows the saved choice", () => {
    const store = new Map<string, string>();
    stubStorage(store);
    expect(sideCollapsed(loadSidePref(), false)).toBe(false);
    expect(sideCollapsed(loadSidePref(), true)).toBe(true);
    saveSideCollapsed(true);
    expect(sideCollapsed(loadSidePref(), false)).toBe(true);
    saveSideCollapsed(false);
    expect(sideCollapsed(loadSidePref(), true)).toBe(false);
  });

  it("survives a blocked localStorage", () => {
    stubStorage(new Map(), true);
    expect(() => saveSideCollapsed(true)).not.toThrow();
    expect(sideCollapsed(loadSidePref(), true)).toBe(true);
    expect(sideCollapsed(loadSidePref(), false)).toBe(false);
  });
});
