// 數值工坊畫面（Phase NW-1b，規格 docs/phases/PhaseNW計畫.md 第 8 節 T-B1～T-B5）：純函式、畫面元件（renderToStaticMarkup）、
// 非同步流程用假的 API（不連網路）。
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ApiError } from "../api/client";
import type {
  TuningChangeIn,
  TuningCheckResult,
  TuningDiff,
  TuningObjectDetail,
  TuningSimJob,
  TuningSimOptions,
  TuningSimResult,
  TuningStatus,
} from "../api/types";
import { readFile, SRC_DIR, stripTsComments } from "../test/sourceScan";
import { ApplyDialog, ApplyPanel, AppliedNote, applyBlock, DiffView, DraftBar } from "./DraftPanel";
import { FieldForm, filterObjects } from "./FieldForm";
import { pollSim, probeEntry, saveAndDiff } from "./flow";
import {
  editKey,
  editsFromDraft,
  editsToChanges,
  entryFromError,
  estimateSeconds,
  estimateText,
  pageErrorsOf,
  parseIntText,
  rangeWarning,
  scaleProblem,
  setEdit,
  simCell,
  simRows,
  type Edits,
} from "./model";
import { SimResultTable } from "./SimPanel";
import { TuningEntryView } from "./TuningEntry";

const FILE = "units/ashen_heart.yaml";

/** 欄位清單故意放一個不存在於白名單的假欄位：表單必須照清單畫，不寫死。 */
const DETAIL: TuningObjectDetail = {
  kind: "unit",
  id: "ashen_heart",
  name_zh: "灰燼之心",
  category: "boss",
  file: FILE,
  notes_zh: ["實戰時另有遭遇護甲調整 +2（ashen_waste）"],
  fields: [
    { path: "max_hp", pattern: "max_hp", label_zh: "最大 HP", kind: "int", value: 160, hint_min: 1, hint_max: 999, note_zh: "單位檔的基礎值" },
    { path: "max_mana", pattern: "max_mana", label_zh: "法力基礎", kind: "int", value: null, default_zh: "沒寫＝依武器大類", note_zh: "沒寫時依武器大類" },
    { path: "phases[1].trigger.permille", pattern: "phases[*].trigger.permille", label_zh: "第 2 階段「呼吸」階段 HP 門檻", kind: "permille", value: 600, hint_min: 100, hint_max: 900, note_zh: "門檻" },
    { path: "zz_fake.value", pattern: "zz_fake.value", label_zh: "測試用假欄位", kind: "int", value: 7, note_zh: "只在測試裡" },
  ],
};

const STATUS: TuningStatus = {
  can_write: true,
  reason_zh: null,
  restart_needed: false,
  restart_note_zh: "這次開伺服器以來沒有寫回；遊戲用的是目前的數值。",
  draft_default: "current",
  drafts: [],
  sim_running: null,
};

const field = (path: string) => DETAIL.fields.find((f) => f.path === path)!;
const html = (el: Parameters<typeof renderToStaticMarkup>[0]) => renderToStaticMarkup(el);

/** `data-path` 那一列的 HTML（到下一列為止）。 */
function rowOf(markup: string, path: string): string {
  const at = markup.indexOf(`data-path="${path}"`);
  expect(at, path).toBeGreaterThan(-1);
  const next = markup.indexOf("data-path=", at + 10);
  return markup.slice(at, next === -1 ? undefined : next);
}

describe("T-B1 表單由欄位清單產生；改過標記與差異一致", () => {
  it("每個欄位一列（含假欄位）、中文名、現值；沒寫的顯示預設說明；‰ 欄位附百分比", () => {
    const m = html(createElement(FieldForm, { detail: DETAIL, edits: {}, check: null, onEdit: () => {}, onDrop: () => {} }));
    for (const f of DETAIL.fields) expect(rowOf(m, f.path)).toContain(f.label_zh);
    expect(rowOf(m, "zz_fake.value")).toContain("7");
    expect(rowOf(m, "max_mana")).toContain("沒寫＝依武器大類");
    expect(rowOf(m, "max_mana")).not.toContain("沒寫（沒寫");
    expect(rowOf(m, "phases[1].trigger.permille")).toContain("600‰（60%）");
    expect(m).toContain("實戰時另有遭遇護甲調整");
    expect(m).not.toContain("改過");
  });

  it("改值 → 該列「改過」＋單欄還原；改回原值或清空 → 不算改過", () => {
    let edits: Edits = {};
    edits = setEdit(edits, DETAIL, field("max_hp"), "150");
    edits = setEdit(edits, DETAIL, field("zz_fake.value"), "9");
    const m = html(createElement(FieldForm, { detail: DETAIL, edits, check: null, onEdit: () => {}, onDrop: () => {} }));
    expect(rowOf(m, "max_hp")).toContain("改過");
    expect(rowOf(m, "max_hp")).toContain("還原這欄");
    expect(rowOf(m, "zz_fake.value")).toContain("改過");
    expect(rowOf(m, "max_mana")).not.toContain("改過");
    expect(setEdit(edits, DETAIL, field("max_hp"), "160")[editKey(FILE, "max_hp")]).toBeUndefined();
    expect(setEdit(edits, DETAIL, field("max_hp"), " ")[editKey(FILE, "max_hp")]).toBeUndefined();
  });

  it("改過的欄位＝改動單＝草稿列的清單＝差異頁的列（存草稿後拿差異，假 API）", async () => {
    let edits: Edits = {};
    edits = setEdit(edits, DETAIL, field("phases[1].trigger.permille"), "550");
    edits = setEdit(edits, DETAIL, field("max_hp"), "150");
    edits = setEdit(edits, DETAIL, field("max_mana"), "12");
    const changes = editsToChanges(edits);
    expect(changes).toEqual([
      { file: FILE, path: "max_hp", old: 160, new: 150 },
      { file: FILE, path: "max_mana", old: null, new: 12 },
      { file: FILE, path: "phases[1].trigger.permille", old: 600, new: 550 },
    ]);
    const put: TuningChangeIn[][] = [];
    const fake = {
      tuningPutDraft: async (_n: string, c: TuningChangeIn[]) => {
        put.push(c);
        return { name: "current", changes: [] };
      },
      tuningDiff: async (): Promise<TuningDiff> => ({
        rows: put[0]!.map((c) => ({ object_id: "ashen_heart", object_name_zh: "灰燼之心", file: c.file, path: c.path, label_zh: field(c.path).label_zh, old: c.old, new: c.new as number })),
        text: "--- a/units/ashen_heart.yaml\n+++ b/units/ashen_heart.yaml\n-max_hp: 160\n+max_hp: 150\n",
      }),
    };
    const diff = await saveAndDiff(fake, "current", changes);
    expect(put).toEqual([changes]);
    const diffHtml = html(createElement(DiffView, { diff }));
    const form = html(createElement(FieldForm, { detail: DETAIL, edits, check: null, onEdit: () => {}, onDrop: () => {} }));
    const marked = DETAIL.fields.filter((f) => rowOf(form, f.path).includes("改過")).map((f) => f.path);
    expect(marked.sort()).toEqual(diff.rows.map((r) => r.path).sort());
    for (const r of diff.rows) expect(diffHtml).toContain(r.label_zh);
    expect(diffHtml).toContain("沒寫");
    const bar = html(createElement(DraftBar, { status: STATUS, name: "current", edits: Object.values(edits), unsaved: false, busy: false, onSave: () => {}, onSwitch: () => {}, onDiscard: () => {}, onOpen: () => {} }));
    for (const e of Object.values(edits)) expect(bar).toContain(e.label_zh);
    expect(bar).toContain("已存");
  });

  it("草稿 ↔ 改動：還原產生的「改回沒寫」(new = null) 來回不變", () => {
    const view = {
      name: "current",
      changes: [
        { file: FILE, path: "max_hp", old: 150, new: 160, object_id: "ashen_heart", label_zh: "最大 HP" },
        { file: FILE, path: "max_mana", old: 12, new: null, object_id: "ashen_heart", label_zh: "法力基礎" },
      ],
    };
    const edits = editsFromDraft(view);
    expect(editsToChanges(edits)).toEqual(view.changes.map(({ file, path, old, new: n }) => ({ file, path, old, new: n })));
  });

  it("本機轉型：全形數字收、文字與小數擋（中文原因）；建議範圍外只提醒", () => {
    expect(parseIntText("１５０")).toEqual({ ok: true, value: 150 });
    expect(parseIntText("－5")).toEqual({ ok: true, value: -5 });
    expect(parseIntText("1.5")).toMatchObject({ ok: false, error: expect.stringContaining("要填整數") });
    expect(parseIntText("abc")).toMatchObject({ ok: false });
    const edits = setEdit({}, DETAIL, field("max_hp"), "abc");
    const m = html(createElement(FieldForm, { detail: DETAIL, edits, check: null, onEdit: () => {}, onDrop: () => {} }));
    expect(rowOf(m, "max_hp")).toContain("要填整數");
    const big = setEdit({}, DETAIL, field("max_hp"), "1200")[editKey(FILE, "max_hp")];
    expect(rangeWarning(field("max_hp"), big)).toContain("超出建議範圍 1～999");
  });

  it("搜尋對象：中文名或 ID", () => {
    const list = [
      { kind: "unit", id: "ashen_heart", name_zh: "灰燼之心", category: "boss" as const, file: FILE },
      { kind: "unit", id: "std_enemy_t1", name_zh: "標準敵人一", category: "enemy" as const, file: "units/std_enemy_t1.yaml" },
    ];
    expect(filterObjects(list, "灰燼").map((o) => o.id)).toEqual(["ashen_heart"]);
    expect(filterObjects(list, "STD").map((o) => o.id)).toEqual(["std_enemy_t1"]);
    expect(filterObjects(list, "")).toHaveLength(2);
  });
});

describe("T-B2 後端的驗證錯誤：對得到欄位的在欄位下，對不到的在頁首", () => {
  const check: TuningCheckResult = {
    ok: false,
    superseded: false,
    seconds: 1.2,
    field_errors: [
      { file: FILE, path: "max_hp", message_zh: "最大 HP 不能小於 1" },
      { file: "units/other_boss.yaml", path: "speed", message_zh: "速度不能小於 0" },
    ],
    page_errors: ["第 3 階段的 HP 門檻必須比前一個階段低"],
  };

  it("欄位錯誤紅字在那一列；其他列沒有", () => {
    const edits = setEdit({}, DETAIL, field("max_hp"), "0");
    const m = html(createElement(FieldForm, { detail: DETAIL, edits, check, onEdit: () => {}, onDrop: () => {} }));
    expect(rowOf(m, "max_hp")).toContain("最大 HP 不能小於 1");
    expect(rowOf(m, "max_hp")).toContain('aria-invalid="true"');
    expect(rowOf(m, "max_mana")).not.toContain("不能小於");
  });

  it("頁首：page_errors＋別的檔的欄位錯誤（標對象與欄位名）", () => {
    const edits: Edits = {
      [editKey("units/other_boss.yaml", "speed")]: { file: "units/other_boss.yaml", path: "speed", old: 3, text: "-1", label_zh: "速度", object_id: "other_boss" },
    };
    const page = pageErrorsOf(check, edits, FILE);
    expect(page).toEqual(["第 3 階段的 HP 門檻必須比前一個階段低", "other_boss「速度」：速度不能小於 0"]);
    expect(pageErrorsOf(check, {}, null)).toContain("units/other_boss.yaml speed：速度不能小於 0");
    expect(pageErrorsOf(null, {}, FILE)).toEqual([]);
  });
});

const SIDE = (wins: number, n: number, extra: Partial<TuningSimResult["before"]> = {}): TuningSimResult["before"] => ({
  n,
  wins,
  rounds: n * 8,
  allies: n * 3,
  downed: 28,
  small: n < 30,
  phases: [
    { phase: 1, name_zh: "開場", reached: n, turns: 60, skills: [{ skill: "ash_breath", casts: 15, turns: 60, small: false }] },
    { phase: 2, name_zh: "呼吸", reached: 10, turns: 20, skills: [{ skill: "ember_rain", casts: 5, turns: 20, small: true }] },
  ],
  builds: [{ build: "build_a", n: 3, wins: 2 }],
  ...extra,
});

const RESULT: TuningSimResult = {
  boss: "ashen",
  battles: 24,
  before: SIDE(19, 24),
  after: SIDE(20, 24, { downed: 26, phases: [{ phase: 1, name_zh: "開場", reached: 24, turns: 62, skills: [{ skill: "ash_breath", casts: 14, turns: 62, small: false }] }] }),
  flips: { won_to_lost: 0, lost_to_won: 1 },
  before_cached: false,
};

describe("T-B3 模擬結果表：改前／改後／差值、分子分母、樣本小、翻轉場數", () => {
  it("格子與差值", () => {
    expect(simCell(19, 24, "rate")).toMatchObject({ text: "79.2%", frac: "19/24", small: true });
    expect(simCell(0, 0, "rate")).toMatchObject({ text: "—", value: null });
    expect(simCell(15, 60, "rate").small).toBe(false);
    const rows = simRows(RESULT, (id) => (id === "ash_breath" ? "灰燼吐息" : id), (id) => `B:${id}`);
    const win = rows.find((r) => r.label === "我方勝率")!;
    expect(win.delta).toBe("+4.2 個百分點");
    expect(rows.find((r) => r.label === "平均輪數")!.delta).toBe("±0");
    // 階段 2 只在改前：改後是 0/24 到達、招式 0/0
    const reach2 = rows.find((r) => r.group.includes("呼吸") && r.label.startsWith("到達"))!;
    expect([reach2.before.frac, reach2.after.frac]).toEqual(["10/24", "0/24"]);
    const ember = rows.find((r) => r.label.includes("ember_rain"))!;
    expect(ember.after.text).toBe("—");
    expect(rows.find((r) => r.label.includes("灰燼吐息"))!.before.frac).toBe("15/60");
    expect(rows.find((r) => r.group === "各 build 勝率")!.label).toBe("B:build_a");
  });

  it("畫出來：三欄表頭、分子分母、樣本小、翻轉句", () => {
    const m = html(createElement(SimResultTable, { result: RESULT, skillName: (id: string) => id, buildName: (id: string) => id }));
    for (const h of ["改前", "改後", "差值"]) expect(m).toContain(`<th>${h}</th>`);
    expect(m).toContain("79.2%");
    expect(m).toContain("（19/24）");
    expect(m).toContain("樣本小");
    expect(m).toContain("改前贏→改後輸 0 場、改前輸→改後贏 1 場");
  });

  it("規模與估時：24 場、上限 160、程序數", () => {
    const opts: TuningSimOptions = { bosses: [], builds: [], default_seeds: 3, max_battles: 160, workers: 4, seconds_per_battle: 1.775 };
    expect(estimateSeconds(opts, 24, true)).toBe(11);
    expect(estimateSeconds(opts, 24, false)).toBe(21);
    expect(estimateText(opts, 24)).toContain("24 場");
    expect(estimateText(opts, 24)).toContain("11～21 秒");
    expect(scaleProblem(opts, 8, 3)).toBeNull();
    expect(scaleProblem(opts, 8, 21)).toContain("一次最多 160 場（現在 168 場）");
    expect(scaleProblem(opts, 0, 3)).toContain("至少勾一個");
    expect(scaleProblem(opts, 8, NaN)).toContain("種子數");
  });

  it("輪詢（假 API、假計時）：每秒問一次直到結束；離開畫面就停", async () => {
    const job = (state: TuningSimJob["state"], done: number): TuningSimJob => ({ job_id: "j1", state, done, total: 48, estimate_s: 20, elapsed_s: done, result: state === "done" ? RESULT : null });
    const answers = [job("running", 20), job("done", 48)];
    const seen: string[] = [];
    const waits: number[] = [];
    const last = await pollSim(
      { tuningSim: async () => answers.shift()! },
      job("running", 0),
      (j) => seen.push(`${j.state}:${j.done}`),
      () => false,
      async (ms) => void waits.push(ms),
    );
    expect(last.state).toBe("done");
    expect(seen).toEqual(["running:0", "running:20", "done:48"]);
    expect(waits).toEqual([1000, 1000]);
    let calls = 0;
    const stopped = await pollSim({ tuningSim: async () => (calls++, job("running", 1)) }, job("running", 0), () => {}, () => true, async () => {});
    expect(stopped.state).toBe("running");
    expect(calls).toBe(0);
    const failed = await pollSim({ tuningSim: async () => Promise.reject(new ApiError(404, "沒有這個模擬工作")) }, job("running", 0), () => {}, () => false, async () => {});
    expect(failed).toMatchObject({ state: "failed", error_zh: expect.stringContaining("沒有這個模擬工作") });
  });
});

describe("T-B4 寫回：不能寫回時停用並顯示原因；成功顯示 commit 與「重開伺服器」", () => {
  const ok: TuningCheckResult = { ok: true, superseded: false, seconds: 1.2, field_errors: [], page_errors: [] };

  it("停用原因", () => {
    const locked = { ...STATUS, can_write: false, reason_zh: "開發 PM 正在合併，稍後再寫回" };
    expect(applyBlock(locked, 1, ok, false)).toContain("開發 PM 正在合併");
    expect(applyBlock(STATUS, 0, ok, false)).toBe("草稿沒有改動");
    expect(applyBlock(STATUS, 1, null, true)).toBe("等驗證跑完");
    expect(applyBlock(STATUS, 1, { ...ok, ok: false }, false)).toContain("草稿有錯");
    expect(applyBlock(STATUS, 1, ok, false)).toBeNull();
    expect(applyBlock(STATUS, 1, ok, false, true)).toContain("模擬跑完");
    const m = html(createElement(ApplyPanel, { status: locked, count: 1, check: ok, checking: false, busy: false, diff: null, applied: null, onDiff: () => {}, onApply: () => {} }));
    expect(m).toMatch(/<button[^>]*disabled=""[^>]*data-testid="tuning-apply"/);
    expect(m).toContain("開發 PM 正在合併，稍後再寫回");
  });

  it("確認視窗：列改動、會 commit、要重開伺服器、一輪從頭開始；共用詢問視窗外框", () => {
    const diff: TuningDiff = { rows: [{ object_id: "ashen_heart", object_name_zh: "灰燼之心", file: FILE, path: "max_hp", label_zh: "最大 HP", old: 160, new: 150 }], text: "" };
    const m = html(createElement(ApplyDialog, { diff, busy: false, error: "開發 PM 正在合併，稍後再寫回", onConfirm: () => {}, onCancel: () => {} }));
    expect(m).toContain('role="dialog"');
    expect(m).toContain("decision-card");
    for (const s of ["灰燼之心", "最大 HP", "160", "150", "commit", "要重開伺服器", "從頭開始", "確定寫回", "開發 PM 正在合併"]) expect(m).toContain(s);
  });

  it("成功：commit、檔案、備份、重開伺服器的提示", () => {
    const m = html(
      createElement(AppliedNote, {
        applied: { commit: "0123456789abcdef", message: "tune: 灰燼之心 最大 HP 160→150\n\n- …", files: [FILE], backup: "saves/tuning/backups/x", restart_note_zh: "已寫回；重開伺服器後遊戲才會用新數值（模擬不用重開）。" },
      }),
    );
    expect(m).toContain("0123456789");
    expect(m).toContain("tune: 灰燼之心 最大 HP 160→150");
    expect(m).not.toContain("- …");
    expect(m).toContain("重開伺服器");
    expect(m).toContain(FILE);
  });
});

describe("T-B5 入口：只在 ?dev=1 的開發選單；開關沒開時顯示「未開啟」與怎麼開", () => {
  it("App：TuningScreen 只在開發模式；正式首頁沒有入口", () => {
    const app = stripTsComments(readFile(SRC_DIR, "App.tsx"), "App.tsx");
    expect(app).toMatch(/if \(screen === "tuning" && isDevMode\(window\.location\.search\)\)/);
    expect(app.match(/<TuningScreen\b/g)).toHaveLength(1);
    expect(app.match(/onTuning=/g)).toHaveLength(1);
    // onTuning 只傳給開發選單 StartScreen（在「不是開發模式就回傳首頁」之後）
    expect(app.indexOf("onTuning=")).toBeGreaterThan(app.indexOf("if (!isDevMode(window.location.search))"));
    expect(app.indexOf("onTuning=")).toBeGreaterThan(app.indexOf("<StartScreen"));
    const home = stripTsComments(readFile(SRC_DIR, "screens/HomeScreen.tsx"), "screens/HomeScreen.tsx");
    expect(home).not.toMatch(/Tuning|數值工坊/);
  });

  it("探測（假 API）：200 → 開；404 → 未開啟＋TRPG_TUNING=1；403 → Tunnel 原因；連不到", async () => {
    expect(await probeEntry({ tuningStatus: async () => STATUS })).toEqual({ kind: "open" });
    const off = await probeEntry({ tuningStatus: () => Promise.reject(new ApiError(404, "Not Found")) });
    expect(off.kind).toBe("off");
    expect(off.kind !== "open" && off.kind !== "checking" ? off.reason : "").toContain("TRPG_TUNING=1");
    expect(await probeEntry({ tuningStatus: () => Promise.reject(new ApiError(403, "數值工坊只能在本機瀏覽器直接開")) })).toEqual({ kind: "blocked", reason: "數值工坊只能在本機瀏覽器直接開" });
    expect((await probeEntry({ tuningStatus: () => Promise.reject(new ApiError(0, "無法連線")) })).kind).toBe("offline");
    expect(entryFromError(500, "壞了")).toMatchObject({ kind: "offline" });
  });

  it("入口按鈕：開 → 可按；未開啟 → 停用、寫「未開啟」與怎麼開", () => {
    const open = html(createElement(TuningEntryView, { state: { kind: "open" }, onOpen: () => {} }));
    expect(open).toContain("進入數值工坊");
    expect(open).not.toMatch(/disabled=""[^>]*data-testid="enter-tuning"/);
    const off = html(createElement(TuningEntryView, { state: entryFromError(404, "Not Found"), onOpen: () => {} }));
    expect(off).toContain("數值工坊（未開啟）");
    expect(off).toMatch(/disabled=""[^>]*data-testid="enter-tuning"/);
    expect(off).toContain("TRPG_TUNING=1");
  });
});
