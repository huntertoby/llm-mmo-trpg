// LW-2：本場條件不成立的標灰（06 6.37「提示與標灰」）。純函式、技能列的 class 與無障礙名、說明卡第一行、接線。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { SkillOff } from "../api/types";
import { readFile, SRC_DIR } from "../test/sourceScan";
import { ConditionOffNote } from "../ui/ConditionOffNote";
import { SkillBar } from "../ui/SkillBar";
import { conditionOffClass, conditionOffLabel, conditionOffLine, conditionOffMap, OFF_PART_ZH, OFF_WHOLE_ZH, withConditionOff } from "./conditionOff";
import type { SkillButton } from "./targeting";

const REASON = "開戰時身邊有隊友，獨狼本場不成立";
const OFF: SkillOff[] = [
  { skill_id: "skill_lone_strider", conditions: ["lone_wolf"], whole: true, reason_zh: REASON },
  { skill_id: "skill_unguarded_shot", conditions: ["lone_wolf"], whole: false, reason_zh: REASON },
];

function button(skillId: string, over: Partial<SkillButton> = {}): SkillButton {
  return { skillId, name: skillId === "skill_unguarded_shot" ? "無人掩護" : "隱匿射擊", costs: ["AP 2"], cooldown: 0, actions: [], disabledReason: null, ...over };
}

describe("conditionOff 純函式", () => {
  it("清單 → 對照；沒有欄位（舊回應）＝空", () => {
    expect(conditionOffMap(OFF)).toEqual({
      skill_lone_strider: { reason: REASON, whole: true },
      skill_unguarded_shot: { reason: REASON, whole: false },
    });
    expect(conditionOffMap(undefined)).toEqual({});
    expect(conditionOffMap(null)).toEqual({});
  });
  it("只套到有標灰的按鈕，其他欄位不動（能不能按照舊看 disabledReason）", () => {
    const [shot, other] = withConditionOff([button("skill_unguarded_shot"), button("skill_veiled_shot")], conditionOffMap(OFF));
    expect(shot).toMatchObject({ disabledReason: null, conditionOff: { reason: REASON, whole: false } });
    expect(other!.conditionOff).toBeUndefined();
  });
  it("class、說明卡第一行、無障礙名", () => {
    expect(conditionOffClass(null)).toBe("");
    expect(conditionOffClass({ reason: REASON, whole: false })).toBe(" cond-off");
    expect(conditionOffLine({ reason: REASON, whole: false })).toBe(`本場不成立：${REASON}（${OFF_PART_ZH}）`);
    expect(conditionOffLine({ reason: REASON, whole: true })).toBe(`本場不成立：${REASON}（${OFF_WHOLE_ZH}）`);
    expect(conditionOffLabel("無人掩護", undefined)).toBe("無人掩護");
    expect(conditionOffLabel("無人掩護", { reason: REASON, whole: false })).toBe(`無人掩護（本場不成立：${REASON}）`);
  });
});

describe("技能列與說明卡", () => {
  const noop = () => undefined;
  const props = (buttons: SkillButton[]) => ({ basic: [], buttons, cards: {}, selectedKey: null, enabled: true, hint: "", onPickMode: noop, onSelect: noop });
  it("標灰的技能鈕多 cond-off 與無障礙名；沒標灰的不變；仍可按（不加 blocked）", () => {
    const plain = renderToStaticMarkup(createElement(SkillBar, props([button("skill_unguarded_shot")])));
    const off = renderToStaticMarkup(createElement(SkillBar, props(withConditionOff([button("skill_unguarded_shot")], conditionOffMap(OFF)))));
    expect(plain).not.toContain("cond-off");
    expect(off).toMatch(/class="skill-button cond-off"/);
    expect(off).toContain(`aria-label="無人掩護（本場不成立：${REASON}）"`);
    expect(off).not.toContain("blocked");
    expect(off.replace(/ cond-off/, "").replace(` aria-label="無人掩護（本場不成立：${REASON}）"`, "")).toBe(plain);
  });
  it("說明卡第一行（主動技與被動小圖示共用 ConditionOffNote）", () => {
    expect(renderToStaticMarkup(createElement(ConditionOffNote, { mark: null }))).toBe("");
    expect(renderToStaticMarkup(createElement(ConditionOffNote, { mark: { reason: REASON, whole: true } }))).toBe(
      `<div class="skill-card-reason cond-off-note" data-testid="cond-off-note">本場不成立：${REASON}（${OFF_WHOLE_ZH}）</div>`,
    );
    const bar = readFile(SRC_DIR, "ui/SkillBar.tsx");
    expect(bar.match(/<ConditionOffNote mark=\{b\.conditionOff\} \/>/g)?.length).toBe(2);
  });
  it("接線：useBattleData 用伺服器的 skills_off 套到技能鈕；CSS 有 cond-off", () => {
    expect(readFile(SRC_DIR, "screens/battle/useBattleData.ts")).toContain("conditionOffMap(response.skills_off)");
    const css = readFile(SRC_DIR, "styles/skill-bar.css");
    expect(css).toContain(".skill-button.cond-off");
    expect(css).toContain(".skill-mini.cond-off");
  });
});
