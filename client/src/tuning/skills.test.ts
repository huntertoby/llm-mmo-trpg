// 數值工坊開放技能（Phase NW-2b，規格 docs/phases/PhaseNW-2計畫.md 第 8 節 T-B1～T-B5）：純函式、畫面元件
// （renderToStaticMarkup）、非同步流程用假的 API（不連網路）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type {
  TuningBudgetResult,
  TuningCheckResult,
  TuningDiff,
  TuningGroupPreview,
  TuningMapSimResult,
  TuningObjectDetail,
  TuningObjectSummary,
  TuningSimOptions,
  TuningStatus,
} from "../api/types";
import { ApplyDialog, ApplyPanel, applyBlock, DiffView } from "./DraftPanel";
import { FieldForm, inheritedLists } from "./FieldForm";
import { DEFAULT_GROUP_FORM, GroupPanel, GroupPreviewTable, groupRequest } from "./GroupPanel";
import { editKey, editsFromDraft, editsToChanges, localError, newText, setEdit, setListEdit, type Edits } from "./model";
import { MapResultTable, simEstimate, DEFAULT_MAP_FORM } from "./SimPanel";
import { pickerRows, SkillIdsEditor } from "./SkillIdsEditor";
import { BudgetBar, SkillForm } from "./SkillForm";
import {
  applyConfirm,
  budgetGeometry,
  confirmBlock,
  diceStep,
  diceStepProblem,
  editedSkills,
  filterEmpty,
  filterSkills,
  FILTER_ROWS,
  groupProblem,
  mapSimRows,
  matchesFilter,
  mergeGroupRows,
  skillSections,
  verdictClass,
} from "./skillModel";

const html = (el: Parameters<typeof renderToStaticMarkup>[0]) => renderToStaticMarkup(el);

/** `data-path` 那一列的 HTML（到下一列為止）。 */
function rowOf(markup: string, path: string): string {
  const at = markup.indexOf(`data-path="${path}"`);
  expect(at, path).toBeGreaterThan(-1);
  const next = markup.indexOf("data-path=", at + 10);
  return markup.slice(at, next === -1 ? undefined : next);
}

const FIRE = "skills/skill_fire_arrow.yaml";
const LADDER = ["1d4", "1d6", "2d4", "1d8", "1d10", "2d6", "1d12"];

/** 欄位清單故意放一個不存在於白名單的假欄位：表單必須照清單畫，不寫死。 */
const SKILL: TuningObjectDetail = {
  kind: "skill",
  id: "skill_fire_arrow",
  name_zh: "火焰箭矢",
  category: "skill",
  file: FIRE,
  notes_zh: [
    "這招在 2 階以上會依預算比例重算（夾在 70～100%），超出的部分只在 1 階有效",
    "實戰會用升階版（_t<階>）的單位：碎晶之主（shard_lord，3 階）；改 1 階的數字對它們可能沒有影響",
  ],
  skill: { tier: 1, category: "weapon", weapon_req: "ranged", ap_cost: 2, kind: "active", enemy_only: false, has_condition: false, shape: "single", ranged: true, tags: [], single_damage: true, budget_ratio_permille: 788 },
  used_by: [
    { kind: "unit", id: "shard_lord", name_zh: "碎晶之主", where_zh: ["開場"], tier: 3 },
    { kind: "build", id: "build_ranged", name_zh: "遠程", where_zh: [] },
  ],
  fields: [
    { path: "ap_cost", pattern: "ap_cost", label_zh: "AP 消耗", kind: "int", value: 2, limit_min: 1, limit_max: 3, note_zh: "AP" },
    { path: "cost.cooldown", pattern: "cost.cooldown", label_zh: "冷卻（回合）", kind: "int", value: null, default_zh: "沒寫＝沒有冷卻", note_zh: "冷卻" },
    { path: "shape.range", pattern: "shape.range", label_zh: "射程", kind: "range", value: "weapon", readonly_zh: "武器射程：改成數字會改變技能和武器的綁定", note_zh: "射程" },
    { path: "effects[0].multiplier_permille", pattern: "effects[*].multiplier_permille", label_zh: "效果 1（傷害）：武器倍率（‰）", kind: "permille", value: 800, limit_min: 1, limit_max: 10000, note_zh: "倍率" },
    { path: "effects[1].dice", pattern: "effects[*].dice", label_zh: "效果 2（傷害）：骰子", kind: "dice", value: "1d6", note_zh: "骰子" },
    { path: "effects[2].then[0].dice", pattern: "effects[*].then[*].dice", label_zh: "效果 3之後 1（傷害）：骰子", kind: "dice", value: "1d4", note_zh: "骰子" },
    { path: "followup.shape.range", pattern: "followup.shape.range", label_zh: "第二段射程", kind: "range", value: 3, note_zh: "第二段" },
    { path: "zz_fake.value", pattern: "zz_fake.value", label_zh: "測試用假欄位", kind: "int", value: 7, note_zh: "只在測試裡" },
  ],
};

const field = (path: string) => SKILL.fields.find((f) => f.path === path)!;

const BUDGET = (verdict: TuningBudgetResult["verdict"], ratio: number, extra: Partial<TuningBudgetResult> = {}): TuningBudgetResult => ({
  skill_id: "skill_fire_arrow",
  ratio_permille: ratio,
  ratio_text: `${(ratio / 10).toFixed(1)}%`,
  min_ratio_permille: 700,
  max_ratio_permille: 1000,
  verdict,
  verdict_zh: { ok: "合格", over: "超出預算", weak: "過弱", error: "算不出來" }[verdict],
  known_exception: false,
  ...extra,
});

const STATUS: TuningStatus = { can_write: true, reason_zh: null, restart_needed: false, restart_note_zh: "", draft_default: "current", drafts: [], sim_running: null };
const OK: TuningCheckResult = { ok: true, superseded: false, seconds: 1, field_errors: [], page_errors: [] };

const skillForm = (edits: Edits, budget: TuningBudgetResult | null = BUDGET("ok", 788), confirmed = false) =>
  html(createElement(SkillForm, { detail: SKILL, edits, check: null, budget, budgetLoading: false, ladder: LADDER, confirmed, onConfirm: () => {}, onEdit: () => {}, onDrop: () => {} }));

describe("T-B1 技能表單由欄位清單產生；效果分組標題；骰子 ±1 級只在骰子欄位", () => {
  it("每個欄位一列（含假欄位）；依區塊分組，效果標題寫原語中文名", () => {
    const m = skillForm({});
    for (const f of SKILL.fields) rowOf(m, f.path);
    const titles = skillSections(SKILL.fields).map((s) => s.title);
    expect(titles).toEqual(["消耗與冷卻", "形狀與射程", "效果 1（傷害）", "效果 2（傷害）", "效果 3", "第二段", "其他（暴擊、條件、觸發、陷阱）"]);
    for (const t of titles) expect(m).toContain(t);
    // 效果區塊裡的欄位名拿掉「效果 N（原語）：」前綴；巢狀的保留完整標籤
    expect(rowOf(m, "effects[0].multiplier_permille")).toContain("武器倍率（‰）");
    expect(rowOf(m, "effects[0].multiplier_permille")).not.toContain("效果 1（傷害）：");
    expect(rowOf(m, "effects[2].then[0].dice")).toContain("效果 3之後 1（傷害）：骰子");
    expect(rowOf(m, "zz_fake.value")).toContain("測試用假欄位");
  });

  it("「−1 級／＋1 級」只在骰子欄位；唯讀的武器射程只顯示原因、沒有輸入框；允許範圍顯示", () => {
    const m = skillForm({});
    for (const f of SKILL.fields) {
      const r = rowOf(m, f.path);
      expect(r.includes("−1 級"), f.path).toBe(f.kind === "dice");
      expect(r.includes("＋1 級"), f.path).toBe(f.kind === "dice");
    }
    expect(rowOf(m, "shape.range")).toContain("唯讀：武器射程");
    expect(rowOf(m, "shape.range")).not.toContain("<input");
    expect(rowOf(m, "ap_cost")).toContain("允許 1～3");
  });

  it("骰子階梯：走一級、到頂／到底與不在階梯上不能按（同後端 _dice_step）", () => {
    expect(diceStep(LADDER, "1d6", 1)).toBe("2d4");
    expect(diceStep(LADDER, "1d6", -1)).toBe("1d4");
    expect(diceStep(LADDER, "1d12", 1)).toBeNull();
    expect(diceStep(LADDER, "3d3", 1)).toBeNull();
    expect(diceStepProblem(LADDER, "1d4", -1)).toContain("最弱");
    expect(diceStepProblem(LADDER, "1d12", 1)).toContain("最強");
    expect(diceStepProblem(LADDER, "3d3", 1)).toContain("不在骰子階梯上");
    expect(diceStepProblem(null, "1d6", 1)).toContain("讀不到");
    // 第一列骰子的 −1 級可按、最弱的那列（1d4）不可按
    const m = skillForm({});
    expect(rowOf(m, "effects[1].dice")).toMatch(/<button[^>]*data-step="-1"/);
    expect(rowOf(m, "effects[2].then[0].dice")).toMatch(/<button[^>]*disabled=""[^>]*data-step="-1"/);
  });

  it("骰子轉型：全形、大寫 D 收；寫法不對中文原因；改動單送骰子字串", () => {
    let edits: Edits = setEdit({}, SKILL, field("effects[1].dice"), "２Ｄ４");
    expect(editsToChanges(edits)).toEqual([{ file: FIRE, path: "effects[1].dice", old: "1d6", new: "2d4" }]);
    expect(newText(edits[editKey(FIRE, "effects[1].dice")]!)).toBe("2d4");
    expect(setEdit({}, SKILL, field("effects[1].dice"), "1D6")).toEqual({}); // 等於現值不算改過
    edits = setEdit({}, SKILL, field("effects[1].dice"), "2x6");
    expect(localError(edits[editKey(FIRE, "effects[1].dice")])).toContain("顆數d面數");
    expect(rowOf(skillForm(edits), "effects[1].dice")).toContain("顆數d面數");
    // 草稿 ↔ 改動：骰子與清單來回不變
    const view = {
      name: "current",
      changes: [
        { file: FIRE, path: "effects[1].dice", old: "1d6", new: "2d4", object_id: "skill_fire_arrow", label_zh: "骰子" },
        { file: "units/ashen_heart.yaml", path: "phases[1].skills", old: ["skill_a", "skill_b"], new: ["skill_a"], object_id: "ashen_heart", label_zh: "第 2 階段技能" },
        { file: "units/ashen_heart.yaml", path: "phases[2].skills", old: ["skill_c"], new: null, object_id: "ashen_heart", label_zh: "第 3 階段技能" },
      ],
    };
    expect(editsToChanges(editsFromDraft(view))).toEqual(view.changes.map(({ file, path, old, new: n }) => ({ file, path, old, new: n })));
  });

  it("R2 唯讀提示與使用這招的單位（升階版標出）", () => {
    const m = skillForm({});
    expect(m).toContain("這招在 2 階以上會依預算比例重算（夾在 70～100%），超出的部分只在 1 階有效");
    expect(m).toContain('data-testid="retier-note"');
    expect(m).toContain("碎晶之主");
    expect(m).toContain("3 階（用升階版）");
    expect(m).toContain("模擬用 build 英雄");
  });
});

describe("T-B2 預算比例條：合格／超出／過弱；超出時寫回停用、勾「我確定」後啟用；變奏分列", () => {
  it("三態的文字與顏色 class", () => {
    for (const [v, ratio, word] of [
      ["ok", 900, "合格"],
      ["over", 1124, "超出預算"],
      ["weak", 650, "過弱"],
    ] as const) {
      const m = html(createElement(BudgetBar, { budget: BUDGET(v, ratio), loading: false, confirmed: false, onConfirm: () => {} }));
      expect(m).toContain(`data-verdict="${v}"`);
      expect(m).toContain(verdictClass(v));
      expect(m).toContain(word);
      expect(m).toContain(`${(ratio / 10).toFixed(1)}%`);
      expect(m).toContain("合格區間 70.0%～100.0%");
      expect(m.includes("我確定")).toBe(v !== "ok");
    }
    expect(verdictClass("ok")).toBe("tn-v-ok");
    expect(verdictClass("over")).toBe("tn-v-over");
    expect(verdictClass("weak")).toBe("tn-v-weak");
    // 已在例外清單的招不必再勾（PM 裁定 3）
    expect(html(createElement(BudgetBar, { budget: BUDGET("over", 1124, { known_exception: true }), loading: false, confirmed: false, onConfirm: () => {} }))).not.toContain("我確定");
  });

  it("比例條的位置：0～150% 刻度、合格區間底色、超出刻度標「＋」", () => {
    const g = budgetGeometry(750, 700, 1000);
    expect(g.at).toBeCloseTo(50);
    expect(g.bandLeft).toBeCloseTo((700 / 1500) * 100);
    expect(g.bandWidth).toBeCloseTo(20);
    expect(g.clipped).toBe(false);
    expect(budgetGeometry(2000, 700, 1000)).toMatchObject({ at: 100, clipped: true });
  });

  it("變奏、複合兩段分列；violations 紅字在頁首", () => {
    const b = BUDGET("ok", 900, {
      variants: [{ id: "v1", name_zh: "雨中", ratio_permille: 1050, ratio_text: "105.0%", verdict: "over" }],
      segments: [{ label: "第一段", points: "12.0" }, { label: "第二段", points: "8.0" }],
      violations: [{ rule: "variant.v1.budget.over", message_zh: "變奏「雨中」超出預算" }],
    });
    const m = skillForm({}, b);
    expect(m).toContain("變奏「雨中」");
    expect(m).toContain("105.0%");
    expect(m).toContain("第一段：12.0 點");
    expect(m).toContain("第二段：8.0 點");
    expect(m.indexOf('data-testid="budget-violations"')).toBeLessThan(m.indexOf('data-testid="budget-bar"'));
    expect(m).toContain("變奏「雨中」超出預算");
  });

  it("超出：寫回停用並寫原因；勾「我確定」→ 啟用；寫回帶的確認清單恰好是驗證回的那幾招", () => {
    const check: TuningCheckResult = {
      ...OK,
      needs_confirm_budget: [{ skill_id: "skill_fire_arrow", name_zh: "火焰箭矢", ratio_permille: 1124, ratio_text: "112.4%", verdict: "over", message_zh: "火焰箭矢 預算 112.4% 超出合格區間" }],
    };
    const none = new Set<string>();
    const block = confirmBlock(check, none, none);
    expect(block).toContain("「火焰箭矢」預算 112.4% 超出合格區間");
    expect(block).toContain("勾「我確定」");
    expect(applyBlock(STATUS, 1, check, false, false, block)).toBe(block);
    const panel = html(createElement(ApplyPanel, { status: STATUS, count: 1, check, checking: false, busy: false, diff: null, applied: null, confirm: block, onDiff: () => {}, onApply: () => {} }));
    expect(panel).toMatch(/<button[^>]*disabled=""[^>]*data-testid="tuning-apply"/);
    const ok = new Set(["skill_fire_arrow"]);
    expect(confirmBlock(check, ok, none)).toBeNull();
    const enabled = html(createElement(ApplyPanel, { status: STATUS, count: 1, check, checking: false, busy: false, diff: null, applied: null, confirm: confirmBlock(check, ok, none), onDiff: () => {}, onApply: () => {} }));
    expect(enabled).not.toMatch(/<button[^>]*disabled=""[^>]*data-testid="tuning-apply"/);
    expect(applyConfirm(check)).toEqual({ confirm_budget: ["skill_fire_arrow"], confirm_min_moves: [] });
    // 表單上的勾選框
    expect(skillForm({}, BUDGET("over", 1124), true)).toMatch(/data-testid="confirm-budget" checked=""/);
  });
});

const summary = (id: string, name: string, facets: Partial<NonNullable<TuningObjectSummary["skill"]>> = {}): TuningObjectSummary => ({
  kind: "skill",
  id,
  name_zh: name,
  category: "skill",
  file: `skills/${id}.yaml`,
  skill: { tier: 1, category: "weapon", weapon_req: "ranged", ap_cost: 2, kind: "active", enemy_only: false, has_condition: false, shape: "single", ranged: true, tags: [], single_damage: true, budget_ratio_permille: 800, ...facets },
});

const SKILLS: TuningObjectSummary[] = [
  summary("skill_fire_arrow", "火焰箭矢"),
  summary("skill_pinpoint_shot", "點射", { ap_cost: 1, budget_ratio_permille: 936 }),
  summary("skill_cleave", "劈砍", { weapon_req: "melee", ranged: false, shape: "arc", single_damage: false }),
  summary("skill_ember_breath", "餘燼吐息", { category: "spell", weapon_req: "focus", enemy_only: true, tier: 2 }),
  summary("skill_heal", "治療", { category: "spell", weapon_req: "focus", has_condition: true, kind: "active", single_damage: false }),
];

describe("T-B3 分組面板：上限 100、沒條件不能預覽、跳過原因、放進草稿後差異頁逐招逐欄", () => {
  it("篩選：和後端 _matches 同一套；清單搜尋；篩選列含規格 B1 的條件", () => {
    expect(filterEmpty({})).toBe(true);
    expect(filterEmpty({ tier: [], enemy_only: null })).toBe(true);
    expect(filterSkills(SKILLS, "", { tier: [1], category: ["weapon"], ranged: true }).map((o) => o.id)).toEqual(["skill_fire_arrow", "skill_pinpoint_shot"]);
    expect(filterSkills(SKILLS, "", { ap_cost: [1], single_damage: true }).map((o) => o.id)).toEqual(["skill_pinpoint_shot"]);
    expect(filterSkills(SKILLS, "吐息", {}).map((o) => o.id)).toEqual(["skill_ember_breath"]);
    expect(matchesFilter(SKILLS[3]!.skill!, { enemy_only: false })).toBe(false);
    expect(matchesFilter(SKILLS[4]!.skill!, { has_condition: true })).toBe(true);
    const labels = FILTER_ROWS.flatMap((r) => r.choices.map((c) => c.label));
    for (const l of ["1 階", "武器技", "法術", "近戰", "遠程", "1 AP", "主動", "被動", "敵人專用", "有條件"]) expect(labels).toContain(l);
  });

  it("不能預覽的原因：沒條件、超過 100 招、N 不是整數", () => {
    expect(groupProblem(true, {}, [], 0, "1")).toContain("不提供「全部技能」");
    expect(groupProblem(false, { tier: [1] }, [], 0, "1")).toContain("至少選一個");
    expect(groupProblem(true, { tier: [1] }, [], 122, "1")).toContain("一次最多 100 招（現在 122 招）");
    expect(groupProblem(false, {}, Array.from({ length: 101 }, (_, i) => `skill_${i}`), 0, "1")).toContain("101 招");
    expect(groupProblem(true, { tier: [1] }, [], 77, "1.5")).toContain("整數");
    expect(groupProblem(true, { tier: [1] }, [], 77, "-1")).toBeNull();
    const m = html(createElement(GroupPanel, { form: DEFAULT_GROUP_FORM, filter: {}, filterLabel: "", filterCount: 0, manual: [], preview: null, error: null, busy: false, onForm: () => {}, onPreview: () => {}, onAdd: () => {} }));
    expect(m).toMatch(/<button[^>]*disabled=""[^>]*data-testid="group-preview"/);
    expect(m).toContain("不提供「全部技能」");
    expect(m).not.toContain("全域倍率</");
  });

  it("送出的 body：篩選或手動勾選擇一", () => {
    expect(groupRequest(DEFAULT_GROUP_FORM, { tier: [1] }, ["skill_x"])).toEqual({ filter: { tier: [1] }, target: "damage_base", op: { kind: "ladder", value: 1 } });
    expect(groupRequest({ ...DEFAULT_GROUP_FORM, useFilter: false, op: "scale_permille", valueText: "1100" }, { tier: [1] }, ["skill_x"])).toEqual({
      skills: ["skill_x"],
      target: "damage_base",
      op: { kind: "scale_permille", value: 1100 },
    });
  });

  const PREVIEW: TuningGroupPreview = {
    count: 3,
    max_skills: 100,
    rows: [
      { skill_id: "skill_fire_arrow", name_zh: "火焰箭矢", changes: [{ file: FIRE, path: "effects[0].multiplier_permille", old: 800, new: 900 }], before_ratio_permille: 788, after_ratio_permille: 860, verdict: "ok" },
      {
        skill_id: "skill_pinpoint_shot",
        name_zh: "點射",
        changes: [
          { file: "skills/skill_pinpoint_shot.yaml", path: "effects[0].dice", old: "1d6", new: "2d4" },
          { file: "skills/skill_pinpoint_shot.yaml", path: "effects[1].dice", old: "1d4", new: "1d6" },
        ],
        before_ratio_permille: 936,
        after_ratio_permille: 1012,
        verdict: "over",
      },
      { skill_id: "skill_rain", name_zh: "箭雨", changes: [], before_ratio_permille: 900, after_ratio_permille: 900, verdict: "skipped", skipped_reason_zh: "骰子不能乘倍率，請改用 ±級" },
    ],
  };

  it("預覽表：逐招前後值、前後預算比例、判定、跳過原因", () => {
    const m = html(createElement(GroupPreviewTable, { preview: PREVIEW }));
    expect(m).toContain("78.8% → 86.0%");
    expect(m).toContain("93.6% → 101.2%");
    expect(m).toContain("超出預算");
    expect(m).toContain("跳過：骰子不能乘倍率，請改用 ±級");
    expect(m).toContain("1d6 → <b>2d4</b>");
  });

  it("放進草稿：跳過的不放；其餘逐招逐欄進改動單 → 差異頁逐列", () => {
    const edits = mergeGroupRows({}, PREVIEW.rows);
    const changes = editsToChanges(edits);
    expect(changes.map((c) => `${c.file}|${c.path}`)).toEqual([
      "skills/skill_fire_arrow.yaml|effects[0].multiplier_permille",
      "skills/skill_pinpoint_shot.yaml|effects[0].dice",
      "skills/skill_pinpoint_shot.yaml|effects[1].dice",
    ]);
    expect(changes[1]!.new).toBe("2d4");
    expect(editedSkills(edits)).toEqual(["skill_fire_arrow", "skill_pinpoint_shot"]);
    const diff: TuningDiff = { rows: changes.map((c) => ({ object_id: c.file, object_name_zh: c.file, file: c.file, path: c.path, label_zh: c.path, old: c.old, new: c.new })), text: "" };
    const m = html(createElement(DiffView, { diff }));
    for (const c of changes) expect(m).toContain(c.path);
  });
});

const UNIT: TuningObjectDetail = {
  kind: "unit",
  id: "ashen_heart",
  name_zh: "灰燼之心",
  category: "boss",
  file: "units/ashen_heart.yaml",
  fields: [
    { path: "skills", pattern: "skills", label_zh: "技能（開場）", kind: "skill_ids", value: ["skill_ember_breath", "skill_heal"], note_zh: "招式組" },
    { path: "phases[1].skills", pattern: "phases[*].skills", label_zh: "第 2 階段「呼吸」技能", kind: "skill_ids", value: ["skill_ember_breath", "skill_heal", "skill_fire_arrow"], note_zh: "招式組" },
    { path: "phases[2].skills", pattern: "phases[*].skills", label_zh: "第 3 階段「怒火」技能", kind: "skill_ids", value: null, default_zh: "沒寫＝沿用上一階段", note_zh: "招式組" },
  ],
  unit_skills: { weapon_zh: "火焰法杖（法器）", slots_zh: "主動 4、被動 2、反應 1、姿態 1", problems: { skill_fire_arrow: "技能「火焰箭矢」需要遠程，但單位的武器是法器", skill_cleave: "技能「劈砍」需要近戰，但單位的武器是法器" } },
};

describe("T-B4 招式組：不相容灰掉、敵人專用標記、下限警告與勾選", () => {
  it("加招清單：已裝與武器不相容的灰掉並寫原因、排在後面；敵人專用標記", () => {
    const { rows } = pickerRows(SKILLS, ["skill_ember_breath"], UNIT.unit_skills!, "");
    const by = new Map(rows.map((r) => [r.id, r] as const));
    expect(by.get("skill_fire_arrow")!.disabled).toContain("需要遠程");
    expect(by.get("skill_cleave")!.disabled).toContain("需要近戰");
    expect(by.get("skill_ember_breath")!.disabled).toBe("已經裝了");
    expect(by.get("skill_ember_breath")!.enemyOnly).toBe(true);
    expect(by.get("skill_heal")!.disabled).toBeNull();
    expect(rows.findIndex((r) => r.disabled !== null)).toBeGreaterThan(rows.findIndex((r) => r.id === "skill_heal"));
    expect(pickerRows(SKILLS, [], null, "治療").rows.map((r) => r.id)).toEqual(["skill_heal"]);
  });

  it("目前的招式：中文名、敵人專用、不相容的紅字、排序與移除鈕；沿用上一階段", () => {
    const m = html(createElement(FieldForm, { detail: UNIT, edits: {}, check: null, skills: SKILLS, onList: () => {}, onEdit: () => {}, onDrop: () => {} }));
    const opening = rowOf(m, "skills");
    expect(opening).toContain("餘燼吐息");
    expect(opening).toContain("敵人專用");
    expect(opening).toContain("移除餘燼吐息");
    expect(opening).not.toContain("改回沿用上一階段"); // 開場不能沿用
    expect(opening).toContain("火焰法杖（法器）");
    const p2 = rowOf(m, "phases[1].skills");
    expect(p2).toContain("需要遠程，但單位的武器是法器");
    expect(p2).toContain("改回沿用上一階段");
    const p3 = rowOf(m, "phases[2].skills");
    expect(p3).toContain("沿用上一階段：餘燼吐息、治療、火焰箭矢");
    expect(p3).toContain("改成這一階段自己的招式");
  });

  it("改動：拿掉一招、改回沿用（刪鍵）、等於現值不算改過；沿用鏈依欄位順序", () => {
    const p2 = UNIT.fields[1]!;
    let edits = setListEdit({}, UNIT, p2, ["skill_ember_breath", "skill_heal"]);
    expect(editsToChanges(edits)).toEqual([{ file: UNIT.file, path: "phases[1].skills", old: p2.value, new: ["skill_ember_breath", "skill_heal"] }]);
    expect(setListEdit(edits, UNIT, p2, [...(p2.value as string[])])).toEqual({});
    edits = setListEdit(edits, UNIT, UNIT.fields[2]!, ["skill_heal"]);
    edits = setListEdit(edits, UNIT, UNIT.fields[2]!, null);
    expect(edits[editKey(UNIT.file, "phases[2].skills")]).toBeUndefined(); // 本來就沒寫
    edits = setListEdit(edits, UNIT, p2, null);
    expect(editsToChanges(edits)).toEqual([{ file: UNIT.file, path: "phases[1].skills", old: p2.value, new: null }]);
    expect(newText(edits[editKey(UNIT.file, "phases[1].skills")]!)).toBe("沒寫（沿用上一階段）");
    const inherit = inheritedLists(UNIT.fields, edits, UNIT.file);
    expect(inherit.get("phases[2].skills")).toEqual(["skill_ember_breath", "skill_heal"]); // 第 2 階段改成沿用 → 往上找開場
    const m = html(createElement(SkillIdsEditor, { label: "x", list: null, inherit: ["skill_heal"], skills: SKILLS, picker: null, onChange: () => {} }));
    expect(m).toContain("沿用上一階段：治療");
  });

  it("#149 下限：寫回停用直到勾「我確定」；確認視窗列出並可勾", () => {
    const check: TuningCheckResult = { ...OK, needs_confirm_min_moves: [{ unit_id: "ashen_heart", name_zh: "灰燼之心", shortfalls: ["ashen_heart/breath=2"], message_zh: "灰燼之心 第 2 階段只剩 2 招（頭目每階段至少 3 招）" }] };
    const none = new Set<string>();
    expect(confirmBlock(check, none, none)).toContain("「灰燼之心」低於 #149 的招數下限");
    expect(confirmBlock(check, none, new Set(["ashen_heart"]))).toBeNull();
    expect(applyConfirm(check)).toEqual({ confirm_budget: [], confirm_min_moves: ["ashen_heart"] });
    const diff: TuningDiff = { rows: [{ object_id: "ashen_heart", object_name_zh: "灰燼之心", file: UNIT.file, path: "phases[1].skills", label_zh: "第 2 階段「呼吸」技能", old: ["a", "b", "c"], new: ["a", "b"] }], text: "" };
    const m = html(createElement(ApplyDialog, { diff, busy: false, error: null, check, onConfirm: () => {}, onCancel: () => {} }));
    expect(m).toContain("#149 例外");
    expect(m).toContain("我確定：灰燼之心 第 2 階段只剩 2 招");
    expect(m).toMatch(/<button[^>]*disabled=""[^>]*>確定寫回/);
    const ok = html(createElement(ApplyDialog, { diff, busy: false, error: null, check, movesOk: new Set(["ashen_heart"]), onConfirm: () => {}, onCancel: () => {} }));
    expect(ok).not.toMatch(/<button[^>]*disabled=""[^>]*>確定寫回/);
    expect(m).toContain("a、b、c");
  });
});

const MAP_RESULT: TuningMapSimResult = {
  maps: ["bandit_lair"],
  battles: 24,
  before: {
    n: 24,
    wins: 7,
    rounds: 200,
    allies: 72,
    downed: 30,
    small: true,
    skills: [
      { skill: "skill_fire_arrow", team: "ally", casts: 62, turns: 100, battles: 24, small: false },
      { skill: "skill_fire_arrow", team: "enemy", casts: 19, turns: 73, battles: 24, small: false },
    ],
    maps: [{ build: "bandit_lair", n: 24, wins: 7 }],
  },
  after: {
    n: 24,
    wins: 8,
    rounds: 190,
    allies: 72,
    downed: 28,
    small: true,
    skills: [
      { skill: "skill_fire_arrow", team: "ally", casts: 76, turns: 95, battles: 24, small: false },
      { skill: "skill_fire_arrow", team: "enemy", casts: 20, turns: 69, battles: 24, small: false },
    ],
    maps: [{ build: "bandit_lair", n: 24, wins: 8 }],
  },
  flips: { won_to_lost: 2, lost_to_won: 3 },
  before_cached: false,
};

const OPTIONS: TuningSimOptions = {
  bosses: [],
  builds: [{ id: "build_ranged", name_zh: "遠程" }],
  default_seeds: 3,
  max_battles: 160,
  workers: 4,
  seconds_per_battle: 1.775,
  maps: [{ id: "bandit_lair", name_zh: "盜賊巢穴" }],
  map_default_seeds: 24,
  map_seconds_per_battle: 0.8,
};

describe("T-B5 地圖戰的單招施放率（分子分母、樣本小）；寫回確認視窗列附帶改動", () => {
  it("施放率列：我方／敵方分開、分子＝施放次數、分母＝裝了這招的單位的行動回合；每場平均次數", () => {
    const rows = mapSimRows(MAP_RESULT, (id) => (id === "skill_fire_arrow" ? "火焰箭矢" : id), (id) => `M:${id}`);
    const ally = rows.find((r) => r.group === "「火焰箭矢」（我方）" && r.label.startsWith("每回合施放率"))!;
    expect([ally.before.frac, ally.after.frac]).toEqual(["62/100", "76/95"]);
    expect([ally.before.text, ally.after.text]).toEqual(["62%", "80%"]);
    const enemy = rows.find((r) => r.group === "「火焰箭矢」（敵方）" && r.label.startsWith("每回合施放率"))!;
    expect(enemy.before.frac).toBe("19/73");
    const avg = rows.find((r) => r.group === "「火焰箭矢」（我方）" && r.label === "每場平均次數")!;
    expect(avg.before.text).toBe("2.6");
    expect(rows.find((r) => r.label === "我方勝率")!.before.small).toBe(true);
    expect(rows.find((r) => r.group === "各地圖勝率")!.label).toBe("M:bandit_lair");
  });

  it("結果表與「沒人用」提示；估時用地圖戰的每場秒數", () => {
    const m = html(createElement(MapResultTable, { result: MAP_RESULT, probes: ["skill_fire_arrow", "skill_nobody"], skillName: (id: string) => id, mapName: (id: string) => id }));
    expect(m).toContain("（62/100）");
    expect(m).toContain("改前贏→改後輸 2 場、改前輸→改後贏 3 場");
    expect(m).toContain("skill_nobody：改前改後都沒有人用");
    expect(m).toContain("裝到 build");
    const est = simEstimate(OPTIONS, { boss: "", builds: [], seedsText: "3", scenario: "map", map: { ...DEFAULT_MAP_FORM, maps: ["bandit_lair"], seedsText: "24" } }, ["skill_fire_arrow"]);
    expect(est.problem).toBeNull();
    expect(est.text).toContain("24 場");
    expect(est.text).toContain("5～10 秒"); // 24 × 0.8 ÷ 4 ＝ 4.8 → 5；沒快取 ×2
    expect(simEstimate(OPTIONS, { boss: "", builds: [], seedsText: "3", scenario: "map", map: { ...DEFAULT_MAP_FORM, maps: [], seedsText: "24" } }, []).problem).toContain("至少選一張地圖");
    expect(simEstimate(OPTIONS, { boss: "", builds: [], seedsText: "3", scenario: "map", map: { ...DEFAULT_MAP_FORM, maps: ["bandit_lair"], seedsText: "24" } }, []).problem).toContain("受測招");
    expect(simEstimate(OPTIONS, { boss: "", builds: [], seedsText: "3", scenario: "map", map: { ...DEFAULT_MAP_FORM, maps: ["bandit_lair"], seedsText: "161" } }, ["x"]).problem).toContain("一次最多 160 場");
  });

  it("差異頁與確認視窗列附帶改動（例外清單登記／移除）與預算例外勾選", () => {
    const diff: TuningDiff = {
      rows: [{ object_id: "skill_fire_arrow", object_name_zh: "火焰箭矢", file: FIRE, path: "effects[0].multiplier_permille", label_zh: "效果 1（傷害）：武器倍率（‰）", old: 800, new: 1300 }],
      text: "",
      side_changes: [
        { file: "skill_budget.yaml", action: "exception_add", skill_id: "skill_fire_arrow", text_zh: "例外清單加入 skill_fire_arrow（比例 128.3%）" },
        { file: "skill_budget.yaml", action: "exception_remove", skill_id: "skill_summon_elite", text_zh: "例外清單移除 skill_summon_elite（回到合格區間）" },
      ],
    };
    const d = html(createElement(DiffView, { diff }));
    expect(d).toContain('data-testid="side-changes"');
    expect(d).toContain("登記例外");
    expect(d).toContain("移除例外");
    expect(d).toContain("skill_summon_elite");
    const check: TuningCheckResult = {
      ...OK,
      side_changes: diff.side_changes,
      needs_confirm_budget: [{ skill_id: "skill_fire_arrow", name_zh: "火焰箭矢", ratio_permille: 1283, ratio_text: "128.3%", verdict: "over", message_zh: "火焰箭矢 預算 128.3% 超出合格區間" }],
    };
    const m = html(createElement(ApplyDialog, { diff, busy: false, error: null, check, onConfirm: () => {}, onCancel: () => {} }));
    for (const s of ["附帶改動", "例外清單加入 skill_fire_arrow", "例外清單移除 skill_summon_elite", "預算例外", "我確定：火焰箭矢 預算 128.3%", "要重開伺服器"]) expect(m).toContain(s);
    expect(m).toMatch(/<button[^>]*disabled=""[^>]*>確定寫回/);
    expect(m).toContain('role="dialog"');
  });
});
