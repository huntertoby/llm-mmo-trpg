// BS-2：連續背刺與雙牙的前端。
// 1. 預覽、戰鬥紀錄顯示「背刺・無聲（不會轉身）」「隱蔽出手（不會轉身）」（兩種各自的字＋說明卡）。
// 2.／3. 標灰：伺服器 `skills_off` 的 `effects` → 技能卡第 3 行那幾個效果數字套灰階＋虛線（移植需求 3.7）。
// 4. 數值工坊：全體共用的規則與預算表（`rules`、`budget`）放進敵人與頭目分頁的清單。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { BattleView, PreviewOut, SkillCard, SkillOff } from "../api/types";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { modifierChangePart } from "../render/skillParts";
import { ObjectList } from "../tuning/FieldForm";
import { NoTurnLine } from "../ui/ActionPanel";
import { NoTurnTag } from "../ui/NoTurnTag";
import { SkillCardView } from "../ui/SkillCardView";
import { effectLine } from "../ui/skillCardLines";
import { conditionOffMap } from "./conditionOff";
import { logLines } from "./log";
import { isNoTurnNote, NO_TURN_HINT_ZH, noTurnLabel, noTurnRows, stripNoTurnBracket } from "./noTurn";
import { previewLines } from "./previewText";
import cards from "../ui/fixtures/skillCards.json";
import type { UnitNames } from "./units";

const NAMES: UnitNames = {
  marker: () => "A",
  name: (id) => (id === "u2" ? "盜賊" : "刺客"),
  label: (id) => (id === "u2" ? "A 盜賊" : "B 刺客"),
  team: (id) => (id === "u2" ? "enemy" : "ally"),
};

function preview(over: Partial<PreviewOut>): PreviewOut {
  return {
    hit_permille: 800,
    crit_permille: 100,
    damage: null,
    targets: [],
    healed: [],
    certain: [],
    possible: [],
    notes: [],
    backstab: [],
    cover: null,
    min_events: [],
    max_events: [],
    ...over,
  } as unknown as PreviewOut;
}

const VIEW = { units: [], objects: [] } as unknown as BattleView;

describe("1. 不會轉身的字", () => {
  it("兩種各自的字；和背刺一起時前面加「背刺・」", () => {
    expect(noTurnLabel("silent", true)).toBe("背刺・無聲（不會轉身）");
    expect(noTurnLabel("silent", false)).toBe("無聲（不會轉身）");
    expect(noTurnLabel("concealed", true)).toBe("背刺・隱蔽出手（不會轉身）");
    expect(NO_TURN_HINT_ZH.silent).toContain("匕首");
    expect(NO_TURN_HINT_ZH.concealed).toContain("脫離隱蔽");
  });

  it("預覽：照 no_turn 每個目標一列，伺服器那句不重複；沒有 no_turn 時照舊", () => {
    const p = preview({
      no_turn: ["u2"],
      no_turn_reason: "silent",
      backstab: ["u2"],
      notes: ["背刺 盜賊：命中 +2、暴擊範圍 +1", "背刺・無聲（不會轉身）：盜賊"],
    });
    expect(noTurnRows(p, NAMES)).toEqual([{ text: "背刺・無聲（不會轉身）：A 盜賊", kind: "silent" }]);
    const lines = previewLines(p, NAMES, VIEW);
    expect(lines.filter((l) => l.includes("不會轉身"))).toEqual(["背刺・無聲（不會轉身）：A 盜賊"]);
    expect(lines).toContain("背刺 盜賊：命中 +2、暴擊範圍 +1");
    const plain = preview({ notes: ["背刺 盜賊：命中 +2、暴擊範圍 +1"] });
    expect(noTurnRows(plain, NAMES)).toEqual([]);
    expect(previewLines(plain, NAMES, VIEW)).toContain("背刺 盜賊：命中 +2、暴擊範圍 +1");
    expect(isNoTurnNote("從隱蔽中出手（不會轉身）：盜賊")).toBe(true);
    expect(noTurnRows(preview({ no_turn: ["u2"], no_turn_reason: "concealed" }), NAMES)[0]?.text).toBe("隱蔽出手（不會轉身）：A 盜賊");
  });

  it("預覽列：標籤樣式＋說明卡（種類寫在 data-no-turn）", () => {
    const html = renderToStaticMarkup(createElement("ul", null, createElement(NoTurnLine, { text: "背刺・無聲（不會轉身）：A 盜賊", kind: "silent" })));
    expect(html).toContain('class="preview-no-turn" data-no-turn="silent"');
    expect(html).toContain('class="no-turn-tag"');
    expect(readFile(SRC_DIR, "ui/ActionPanel.tsx")).toContain("noTurn.get(l)");
  });

  it("戰鬥紀錄：attack_rolled.no_turn → 標籤；精簡行拿掉行尾的［…（不會轉身）］，完整文字不動", () => {
    const text = "  B 刺客 從背後攻擊 A 盜賊：d20 15 = 19（需 ≥ 12）→ 命中［背刺・無聲（不會轉身）］";
    const ev = { type: "attack_rolled", seq: 3, round: 1, attacker_id: "u1", target_id: "u2", hit: true, backstab: 2, no_turn: "silent", text };
    const [line] = logLines([{ events: [ev] } as never], NAMES);
    expect(line?.noTurn).toEqual({ kind: "silent", backstab: true });
    expect(line?.text).toBe(text.trim());
    expect(line?.summary).toBe("B 刺客 從背後攻擊 A 盜賊 → 命中");
    const plain = logLines([{ events: [{ ...ev, no_turn: undefined, text: text.replace(/［.*］/, "") }] } as never], NAMES)[0];
    expect(plain?.noTurn).toBeUndefined();
    expect(stripNoTurnBracket("→ 命中［命中 −2：木箱掩護］［隱蔽出手（不會轉身）］")).toBe("→ 命中［命中 −2：木箱掩護］");
  });

  it("紀錄標籤：精簡行與浮動提示都畫；浮動提示不掛說明卡", () => {
    expect(renderToStaticMarkup(createElement(NoTurnTag, { kind: "concealed", backstab: false, hint: false }))).toBe(
      '<span class="no-turn-tag log-no-turn" data-no-turn="concealed" data-testid="no-turn-tag">隱蔽出手（不會轉身）</span>',
    );
    expect(readFile(SRC_DIR, "ui/BattleLog.tsx")).toContain("<NoTurnTag kind={line.noTurn.kind}");
    expect(readFile(SRC_DIR, "ui/BattleLogDock.tsx")).toContain("hint={false}");
    expect(readFile(SRC_DIR, "styles/battle-log.css")).toMatch(/\.no-turn-tag \{[^}]*white-space: nowrap/);
  });
});

const stat = (index: number, category: string, label: string, over: object = {}) => ({ index, type: category === "status" ? "apply_status" : "damage", category, label, unit: null, weapon: category === "damage", ...over });

function card(effects: object[]): SkillCard {
  const base = cards.skill_gale_kick as unknown as SkillCard;
  return {
    ...base,
    name_zh: "無人掩護",
    effects: effects.map((_, i) => `效果 ${i}`),
    modifiers: [],
    formula_lines: [],
    stats: { ...base.stats, effects, scaling_attrs: [] },
  } as unknown as SkillCard;
}

describe("2.／3. 卡片上帶條件的效果數字標灰", () => {
  const shot = card([stat(0, "damage", "×1"), stat(1, "damage", "×0.6"), stat(2, "status", "2", { unit: "回合", name_zh: "隱蔽" })]);

  it("skills_off 的 effects → 對照；空的不帶欄位（LW-2 的比對不變）", () => {
    const off: SkillOff[] = [
      { skill_id: "skill_unguarded_shot", conditions: ["lone_wolf"], whole: false, reason_zh: "x", effects: [1, 2] },
      { skill_id: "skill_silent_step", conditions: ["silent_strike"], whole: true, reason_zh: "要拿匕首類", effects: [] },
    ];
    expect(conditionOffMap(off)).toEqual({
      skill_unguarded_shot: { reason: "x", whole: false, effects: [1, 2] },
      skill_silent_step: { reason: "要拿匕首類", whole: true },
    });
  });

  it("effectLine：只有不發動的效果帶 off；沒給時和以前一樣", () => {
    expect(effectLine(shot).items.map((i) => i.off)).toEqual([undefined, undefined, undefined]);
    expect(effectLine(shot, new Set([1, 2])).items.map((i) => i.off ?? false)).toEqual([false, true, true]);
  });

  it("相同的效果一段標灰、一段沒有時不合併成「2 擊」（孤狼撲擊）", () => {
    const pounce = card([stat(0, "damage", "×1"), stat(1, "damage", "×1")]);
    expect(effectLine(pounce).items).toHaveLength(1);
    const split = effectLine(pounce, new Set([1])).items;
    expect(split.map((i) => [i.label, i.off ?? false])).toEqual([["×1", false], ["×1", true]]);
  });

  it("卡片：那幾個效果數字多 cond-off，其餘逐字不變；CSS 灰階＋虛線、字不淡", () => {
    const plain = renderToStaticMarkup(createElement(SkillCardView, { card: shot, compact: true }));
    const off = renderToStaticMarkup(createElement(SkillCardView, { card: shot, compact: true, offEffects: [1, 2] }));
    expect(off.match(/skill-eff eff-\w+ cond-off/g)).toHaveLength(2);
    expect(off.replaceAll(" cond-off", "")).toBe(plain);
    const css = readFile(SRC_DIR, "styles/skill-bar.css");
    expect(css).toMatch(/\.skill-eff\.cond-off \{[^}]*border: 1px dashed #8a8398/);
    expect(css).toMatch(/\.skill-eff\.cond-off > canvas \{\s*filter: grayscale\(1\) brightness\(0\.8\)/);
    expect(css).not.toMatch(/\.skill-eff\.cond-off[^{]*\{[^}]*opacity/);
    const bar = readFile(SRC_DIR, "ui/SkillBar.tsx");
    expect(bar.match(/offEffects=\{b\.conditionOff\?\.effects\}/g)).toHaveLength(2);
  });
});

describe("組裝算式的無聲標籤", () => {
  it("修正內容 silent_strike 有中文名（不再顯示代碼），Q 版圖樣照代碼", () => {
    const part = modifierChangePart("silent_strike", true);
    expect(part.label).toBe("無聲"); // 組裝列字欄窄（「無聲（目標不轉身）」會被截成「無聲（…」）
    expect(part.q).toMatchObject({ cat: "change", id: "silent_strike" });
  });
});

describe("4. 數值工坊：規則與預算表", () => {
  it("清單多一組「規則與預算（全體共用）」；畫面讀 rules、budget 兩類", () => {
    const objects = [
      { kind: "rules", id: "core", name_zh: "核心戰鬥規則（全體共用）", category: "rules", file: "rules/core.yaml" },
      { kind: "budget", id: "skill_budget", name_zh: "技能預算表（全體共用）", category: "rules", file: "skill_budget.yaml" },
    ] as never;
    const html = renderToStaticMarkup(createElement(ObjectList, { objects, selected: null, query: "", edits: {}, onQuery: () => undefined, onSelect: () => undefined }));
    expect(html).toContain("規則與預算（全體共用）（2）");
    expect(html).toContain('data-object="core"');
    expect(html).toContain('data-object="skill_budget"');
    const screen = readFile(SRC_DIR, "screens/TuningScreen.tsx");
    expect(screen).toContain('tapi.tuningObjects("rules")');
    expect(screen).toContain('tapi.tuningObjects("budget")');
  });
});
