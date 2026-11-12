// 數值工坊的 1 階比值（Phase NW-2c C3，規格 docs/phases/PhaseNW-2計畫.md 5.7、T11、T12、D4）、分組預覽的結構違規
// （NW-2b 待決 5）、頭目部位欄位按部位分組（PB-1n 待決 2）：純函式與畫面元件（renderToStaticMarkup）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { TuningFieldView, TuningGroupPreview, TuningObjectDetail, TuningRatioPlan, TuningRatioSimResult, TuningRatioSummary, TuningSimJob, TuningSimOptions, TuningSkillRatio } from "../api/types";
import { FieldForm } from "./FieldForm";
import { GroupPreviewTable } from "./GroupPanel";
import { fieldBlocks } from "./model";
import { cellChanged, DEFAULT_RATIO_FORM, lineText, ratioEstimate, ratioResultNotes, ratioSeedsProblem, ratioSkillsOf } from "./ratioModel";
import { RatioBox, RatioResultTable } from "./RatioView";
import { SimPanel, simEstimate } from "./SimPanel";

const html = (el: Parameters<typeof renderToStaticMarkup>[0]) => renderToStaticMarkup(el);

function summary(over: Partial<TuningRatioSummary> = {}): TuningRatioSummary {
  return {
    plain: "0.74～0.78",
    plain_tot: "—",
    on: "—",
    on_tot: "—",
    dual: "—",
    bound: "—",
    category_zh: "無條件",
    lines: [{ key: "arrow", label_zh: "1 AP 箭類（直接）", threshold: 0.6, value: 0.78, ok: true, tentative: true }],
    seeds: 50,
    source: "workshop",
    source_zh: "工坊量測（50 種子）",
    stale: false,
    ...over,
  };
}

const PLAN: TuningRatioPlan = { requested: ["skill_fire_arrow"], skills: ["skill_fire_arrow"], skipped: [], jobs: 6, groups: 6, seeds: 50, work: 300, max_work: 40000, seconds: 0.7, problem_zh: null };

const OPTIONS: TuningSimOptions = {
  bosses: [],
  builds: [],
  default_seeds: 3,
  max_battles: 160,
  workers: 4,
  seconds_per_battle: 1.775,
  maps: [],
  map_default_seeds: 24,
  map_seconds_per_battle: 0.8,
  ratio_default_seeds: 50,
  ratio_max_work: 40000,
  ratio_battles_per_second: 450,
};

describe("C3 技能表單的比值區：目前值、參考線、上次量測", () => {
  it("沒有資料或不適用：顯示原因", () => {
    const none: TuningSkillRatio = { skill_id: "skill_fire_bolt", applicable: false, reason_zh: "比值只量 1 階主動武器技（非敵人專用）；這招不適用" };
    expect(html(createElement(RatioBox, { ratio: none, loading: false }))).toContain("這招不適用");
    expect(html(createElement(RatioBox, { ratio: null, loading: true }))).toContain("讀取中");
  });

  it("目前值六格、參考線（建議，未定案另標）、來源；內容已變標黃；上次量測並列", () => {
    const view: TuningSkillRatio = {
      skill_id: "skill_fire_arrow",
      applicable: true,
      current: summary({ stale: true, source: "baseline", source_zh: "匯入的基準（250 種子）：內容已變，僅供參考" }),
      previous: summary({ plain: "0.60～0.65", source_zh: "工坊量測（50 種子）：當時的內容和現在不同" }),
    };
    const out = html(createElement(RatioBox, { ratio: view, loading: false }));
    for (const label of ["直接", "含持續", "成立 直接", "成立 含持續", "雙匕首", "綁定武器"]) expect(out).toContain(`<th>${label}</th>`);
    expect(out).toContain("0.74～0.78");
    expect(out).toContain("1 AP 箭類（直接） ≥ 0.60：0.78 達標");
    expect(out).toContain("建議，未定案");
    expect(out).toMatch(/class="small tn-warn"[^>]*>來源：匯入的基準（250 種子）：內容已變，僅供參考/);
    expect(out).toContain("上次（工坊量測（50 種子）：當時的內容和現在不同）：直接 0.60～0.65");
    expect(out).toContain("不擋寫回");
  });

  it("參考線文字：低於、沒有值", () => {
    expect(lineText({ key: "plain", label_zh: "無條件單體（直接）", threshold: 0.9, value: 0.89, ok: false, tentative: false })).toBe("無條件單體（直接） ≥ 0.90：0.89 低於");
    expect(lineText({ key: "on", label_zh: "條件成立（直接）", threshold: 1.1, value: null, ok: null, tentative: false })).toBe("條件成立（直接） ≥ 1.10：沒有值");
  });
});

describe("C2 比值情境：規模估時（T11）與結果並排", () => {
  it("要量的招：沒選＝草稿改到的；種子 1～250", () => {
    expect(ratioSkillsOf(DEFAULT_RATIO_FORM, ["skill_a"])).toEqual(["skill_a"]);
    expect(ratioSkillsOf({ skills: ["skill_b"], seedsText: "5" }, ["skill_a"])).toEqual(["skill_b"]);
    expect(ratioSeedsProblem("0")).not.toBeNull();
    expect(ratioSeedsProblem("251")).not.toBeNull();
    expect(ratioSeedsProblem("x")).not.toBeNull();
    expect(ratioSeedsProblem(" 250 ")).toBeNull();
  });

  it("「N 組 × M 種子、預估 X 秒」；後端的上限問題原樣顯示；沒有招不能開始", () => {
    const ok = ratioEstimate(PLAN, DEFAULT_RATIO_FORM, ["skill_fire_arrow"]);
    expect(ok.problem).toBeNull();
    expect(ok.text).toContain("6 組 × 50 種子");
    expect(ok.text).toContain("預估約 1 秒～1 秒");
    const big = ratioEstimate({ ...PLAN, problem_zh: "一次最多 40,000 組×種子" }, DEFAULT_RATIO_FORM, ["skill_fire_arrow"]);
    expect(big.problem).toContain("40,000");
    expect(ratioEstimate(PLAN, DEFAULT_RATIO_FORM, []).problem).toContain("至少要有一招");
    expect(ratioEstimate(null, DEFAULT_RATIO_FORM, ["skill_fire_arrow"]).problem).toContain("正在算規模");
    expect(simEstimate(OPTIONS, { boss: "", builds: [], seedsText: "3", scenario: "ratio", ratio: DEFAULT_RATIO_FORM }, ["skill_fire_arrow"], PLAN).text).toContain("6 組 × 50 種子");
  });

  const RESULT: TuningRatioSimResult = {
    skills: [
      {
        skill_id: "skill_fire_arrow",
        name_zh: "火焰箭矢",
        before: summary({ source_zh: "改前", lines: [{ key: "plain", label_zh: "無條件單體（直接）", threshold: 0.9, value: 0.78, ok: false, tentative: false }] }),
        after: summary({ plain: "0.88～0.93", source_zh: "改後", lines: [{ key: "plain", label_zh: "無條件單體（直接）", threshold: 0.9, value: 0.93, ok: true, tentative: false }] }),
      },
    ],
    skipped: [{ skill_id: "skill_fire_bolt", name_zh: "火焰彈", reason_zh: "不適用" }],
    seeds: 50,
    groups: 6,
    before_cached: true,
    same_content: false,
    odd: [],
  };

  it("結果表：逐招六格改前改後、變了的格標出、參考線改前低於 → 改後達標；說明行列快取與跳過", () => {
    expect(cellChanged(RESULT.skills[0]!.before, RESULT.skills[0]!.after, "plain")).toBe(true);
    expect(cellChanged(RESULT.skills[0]!.before, RESULT.skills[0]!.after, "dual")).toBe(false);
    const out = html(createElement(RatioResultTable, { result: RESULT, skillName: (id: string) => id }));
    expect(out).toContain("火焰箭矢");
    expect(out).toMatch(/data-cell="plain"><td>直接<\/td><td class="tn-num">0\.74～0\.78<\/td><td class="tn-num tn-changed-cell">0\.88～0\.93<\/td>/);
    expect(out).toMatch(/data-line="plain"><td>參考線 無條件單體（直接） ≥ 0.90<\/td><td class="tn-v-weak">低於<\/td><td class="tn-v-ok">達標<\/td>/);
    const notes = ratioResultNotes(RESULT);
    expect(notes.some((n) => n.includes("快取"))).toBe(true);
    expect(notes.some((n) => n.includes("「火焰彈」沒量"))).toBe(true);
    expect(ratioResultNotes({ ...RESULT, same_content: true }).some((n) => n.includes("只跑一次"))).toBe(true);
  });

  it("模擬面板：「比值」分頁、受測招、規模按鈕、匯入基準、進度單位是「組」、結果表", () => {
    const job: TuningSimJob = { job_id: "j", state: "running", done: 3, total: 12, estimate_s: 2, elapsed_s: 1 };
    const base = { options: OPTIONS, blocked: null, error: null, skillName: (id: string) => id, onForm: () => undefined, onStart: () => undefined, onCancel: () => undefined, edited: ["skill_fire_arrow"], ratioPlan: PLAN, baselineNote: "已匯入：122 招" };
    const form = { boss: "", builds: [], seedsText: "3", scenario: "ratio" as const, ratio: DEFAULT_RATIO_FORM };
    const running = html(createElement(SimPanel, { ...base, form, job }));
    expect(running).toMatch(/aria-selected="true"[^>]*>比值</);
    expect(running).toContain("3/12 組");
    expect(running).toContain("匯入比值基準 JSON");
    expect(running).toContain("已匯入：122 招");
    expect(running).toContain("每組 50 種子（預設）");
    const done = html(createElement(SimPanel, { ...base, form, job: { ...job, state: "done", done: 12, ratio_result: RESULT } }));
    expect(done).toContain('data-testid="tuning-ratio-result"');
  });
});

describe("NW-2b 待決 5：分組預覽列結構違規；NW-2c：預覽加比值欄", () => {
  it("違規逐條紅字、判定欄加註、比值欄（內容已變另標）", () => {
    const preview: TuningGroupPreview = {
      rows: [
        {
          skill_id: "skill_rng_hamstring_shot",
          name_zh: "斷腱射擊",
          changes: [{ file: "skills/skill_rng_hamstring_shot.yaml", path: "effects[1].multiplier_permille", old: 400, new: 500 }],
          before_ratio_permille: 743,
          after_ratio_permille: 812,
          verdict: "ok",
          violations: [{ rule: "skeleton.secondary_share", message_zh: "骨架 displace：damage 占 53.8%，超過上限 50.0%" }],
          ratio: summary({ plain: "0.55", stale: true }),
        },
        { skill_id: "skill_fire_arrow", name_zh: "火焰箭矢", changes: [], before_ratio_permille: 788, after_ratio_permille: 788, verdict: "skipped", skipped_reason_zh: "沒有符合的傷害效果", violations: [], ratio: null },
      ],
      count: 2,
      max_skills: 100,
    };
    const out = html(createElement(GroupPreviewTable, { preview }));
    expect(out).toContain("<th>比值（直接，目前）</th>");
    expect(out).toContain("結構違規：骨架 displace：damage 占 53.8%，超過上限 50.0%（skeleton.secondary_share）");
    expect(out).toContain("＋結構違規");
    expect(out).toContain("0.55（內容已變）");
    expect(out.match(/data-testid="group-violation"/g)).toHaveLength(1);
  });
});

describe("PB-1n 待決 2：頭目部位欄位按部位分組", () => {
  const f = (path: string, group: string | null): TuningFieldView => ({ path, pattern: path, label_zh: path, kind: "int", value: 1, note_zh: "", group_zh: group });
  const FIELDS = [f("max_hp", null), f("parts[0].hp_permille", "部位 1「拂塵」"), f("parts[1].hp_permille", "部位 2「長劍」"), f("parts[0].armor_bonus", "部位 1「拂塵」"), f("parts[1].armor_bonus", "部位 2「長劍」"), f("speed", null)];

  it("fieldBlocks：部位集中成組（組內照原順序），其他欄位照原順序", () => {
    const blocks = fieldBlocks(FIELDS);
    expect(blocks.map((b) => [b.title, b.fields.map((x) => x.path)])).toEqual([
      [null, ["max_hp"]],
      ["部位 1「拂塵」", ["parts[0].hp_permille", "parts[0].armor_bonus"]],
      ["部位 2「長劍」", ["parts[1].hp_permille", "parts[1].armor_bonus"]],
      [null, ["speed"]],
    ]);
    expect(fieldBlocks([f("a", null), f("b", null)])).toEqual([{ title: null, fields: [f("a", null), f("b", null)] }]);
  });

  it("表單畫出部位標題，部位的欄位排在一起", () => {
    const detail: TuningObjectDetail = { kind: "unit", id: "sect_mist_lock_master", name_zh: "霧鎖真人", category: "boss", file: "units/sect_mist_lock_master.yaml", fields: FIELDS };
    const out = html(createElement(FieldForm, { detail, edits: {}, check: null, onEdit: () => undefined, onDrop: () => undefined }));
    expect(out).toContain('data-group="部位 1「拂塵」"');
    const order = ["max_hp", "parts[0].hp_permille", "parts[0].armor_bonus", "parts[1].hp_permille", "parts[1].armor_bonus", "speed"].map((p) => out.indexOf(`data-path="${p}"`));
    expect(order.every((at, i) => at > -1 && (i === 0 || at > order[i - 1]!))).toBe(true);
  });
});
