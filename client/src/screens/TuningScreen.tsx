// 數值工坊（Phase NW-1b；NW-2b 開放技能；開發選單 `?dev=1` 進入，伺服器要設 `TRPG_TUNING=1`）：選敵人、頭目或技能 →
// 改數值（當場驗證、中文原因；技能另有即時預算比例）→ 小模擬改前改後並排（頭目戰／地圖戰）→ 看差異 →
// 寫回並自動 commit（要重開伺服器生效；超出預算或低於 #149 下限要勾「我確定」）→ 從寫回紀錄還原。
// NW-2c：技能表單的 1 階比值區、模擬面板的「比值」情境（改前改後並排）、匯入 t1_skill_ratio.py 的 JSON 當基準。
// 純函式在 `tuning/model.ts`、`tuning/skillModel.ts`，非同步流程在 `tuning/flow.ts`，畫面元件在 `tuning/*.tsx`。
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client";
import type {
  TuningApplyResult,
  TuningBudgetResult,
  TuningCheckResult,
  TuningDiff,
  TuningFieldView,
  TuningGroupPreset,
  TuningGroupPreview,
  TuningHistoryEntry,
  TuningObjectDetail,
  TuningObjectSummary,
  TuningRatioBaseline,
  TuningRatioPlan,
  TuningSimJob,
  TuningSimOptions,
  TuningSimRequest,
  TuningSkillRatio,
  TuningStatus,
} from "../api/types";
import { ErrorBanner } from "../ui/ErrorBanner";
import { ApplyDialog, ApplyPanel, CheckLine, DraftBar, ExceptionChecks, HistoryList } from "../tuning/DraftPanel";
import { FieldForm } from "../tuning/FieldForm";
import { errorText, pollSim, probeEntry, saveAndDiff, type TuningApi } from "../tuning/flow";
import { DEFAULT_GROUP_FORM, GroupPanel, groupRequest, type GroupForm } from "../tuning/GroupPanel";
import {
  CHECK_DELAY_MS,
  DEFAULT_DRAFT,
  dropEdit,
  editsFromDraft,
  editsToChanges,
  objectKind,
  pageErrorsOf,
  sameChanges,
  setEdit,
  setListEdit,
  type EntryState,
  type Edits,
} from "../tuning/model";
import { DEFAULT_RATIO_FORM, ratioSeedsProblem, ratioSkillsOf } from "../tuning/ratioModel";
import { DEFAULT_MAP_FORM, probesOf, seedsOf, SimPanel, type SimForm } from "../tuning/SimPanel";
import { SkillForm } from "../tuning/SkillForm";
import { ObjectPanel, type ObjectTab } from "../tuning/SkillList";
import { applyConfirm, confirmBlock, editedSkills, filterSkills, mergeGroupRows, type SkillFilter } from "../tuning/skillModel";

interface Props {
  onHome(): void;
  /** 測試可換掉 API。 */
  tapi?: TuningApi;
}

/** 技能預算：停止輸入多久才問後端（規格 T4：0.3 秒）。 */
export const BUDGET_DELAY_MS = 300;

/** 比值基準的狀態文字。 */
function baselineText(b: TuningRatioBaseline | null): string | null {
  if (b === null) return null;
  return `已匯入：${b.skills} 招、${b.rows} 組、每組 ${b.seeds} 種子。${b.note_zh}`;
}

function toggled(set: ReadonlySet<string>, id: string, on: boolean): ReadonlySet<string> {
  const next = new Set(set);
  if (on) next.add(id);
  else next.delete(id);
  return next;
}

export function TuningScreen({ onHome, tapi = api }: Props) {
  const [entry, setEntry] = useState<EntryState>({ kind: "checking" });
  const [status, setStatus] = useState<TuningStatus | null>(null);
  const [objects, setObjects] = useState<TuningObjectSummary[]>([]);
  const [skills, setSkills] = useState<TuningObjectSummary[]>([]);
  const [presets, setPresets] = useState<TuningGroupPreset[]>([]);
  const [ladder, setLadder] = useState<readonly string[] | null>(null);
  const [tab, setTab] = useState<ObjectTab>("unit");
  const [query, setQuery] = useState("");
  const [skillQuery, setSkillQuery] = useState("");
  const [skillFilter, setSkillFilter] = useState<SkillFilter>({});
  const [preset, setPreset] = useState("");
  const [checked, setChecked] = useState<string[]>([]);
  const [selectedUnit, setSelectedUnit] = useState<string | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null);
  const [mode, setMode] = useState<"one" | "group">("one");
  const [detail, setDetail] = useState<TuningObjectDetail | null>(null);
  const [draftName, setDraftName] = useState(DEFAULT_DRAFT);
  const [edits, setEdits] = useState<Edits>({});
  const [saved, setSaved] = useState<ReturnType<typeof editsToChanges>>([]);
  const [check, setCheck] = useState<TuningCheckResult | null>(null);
  const [checking, setChecking] = useState(false);
  const [budget, setBudget] = useState<TuningBudgetResult | null>(null);
  const [budgetLoading, setBudgetLoading] = useState(false);
  const [budgetOk, setBudgetOk] = useState<ReadonlySet<string>>(new Set());
  const [movesOk, setMovesOk] = useState<ReadonlySet<string>>(new Set());
  const [groupForm, setGroupForm] = useState<GroupForm>(DEFAULT_GROUP_FORM);
  const [groupPreview, setGroupPreview] = useState<TuningGroupPreview | null>(null);
  const [groupError, setGroupError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [diff, setDiff] = useState<TuningDiff | null>(null);
  const [confirm, setConfirm] = useState<TuningDiff | null>(null);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [applied, setApplied] = useState<TuningApplyResult | null>(null);
  const [history, setHistory] = useState<TuningHistoryEntry[]>([]);
  const [simOptions, setSimOptions] = useState<TuningSimOptions | null>(null);
  const [simForm, setSimForm] = useState<SimForm>({ boss: "", builds: [], seedsText: "3", scenario: "boss", map: DEFAULT_MAP_FORM, ratio: DEFAULT_RATIO_FORM });
  const [ratio, setRatio] = useState<TuningSkillRatio | null>(null);
  const [ratioLoading, setRatioLoading] = useState(false);
  const [ratioPlan, setRatioPlan] = useState<TuningRatioPlan | null>(null);
  const [baselineNote, setBaselineNote] = useState<string | null>(null);
  const [job, setJob] = useState<TuningSimJob | null>(null);
  const [simError, setSimError] = useState<string | null>(null);
  const [skillNames, setSkillNames] = useState<Readonly<Record<string, string>>>({});
  const leaving = useRef(false);

  const changes = useMemo(() => editsToChanges(edits), [edits]);
  const editList = useMemo(() => Object.values(edits).sort((a, b) => (a.object_id + a.path < b.object_id + b.path ? -1 : 1)), [edits]);
  const unsaved = !sameChanges(changes, saved);
  const edited = useMemo(() => editedSkills(edits), [edits]);
  const selected = tab === "unit" ? selectedUnit : selectedSkill;
  const filtered = useMemo(() => filterSkills(skills, "", skillFilter), [skills, skillFilter]);

  const refreshStatus = useCallback(() => {
    tapi.tuningStatus().then(setStatus, (e: unknown) => setError(errorText(e)));
    tapi.tuningHistory().then(setHistory, () => setHistory([]));
  }, [tapi]);

  const loadSkills = useCallback(() => {
    tapi.tuningObjects("skill").then(setSkills, (e: unknown) => setError(`讀不到技能清單：${errorText(e)}`));
  }, [tapi]);

  const loadDraft = useCallback(
    async (name: string) => {
      const view = await tapi.tuningDraft(name);
      const next = editsFromDraft(view);
      setDraftName(name);
      setEdits(next);
      setSaved(editsToChanges(next));
      setDiff(null);
    },
    [tapi],
  );

  // 進畫面：先問開關有沒有開；開了才讀對象、技能、草稿、模擬選項、紀錄。
  useEffect(() => {
    leaving.current = false;
    let cancelled = false;
    void probeEntry(tapi).then(async (state) => {
      if (cancelled) return;
      setEntry(state);
      if (state.kind !== "open") return;
      try {
        // PB-1n：AI 估值表（ai_profiles.yaml）和單位放在同一個分頁；讀不到就只列單位。
        const [st, units, ai] = await Promise.all([tapi.tuningStatus(), tapi.tuningObjects("unit"), tapi.tuningObjects("ai").catch(() => [])]);
        const objs = [...units, ...ai];
        if (cancelled) return;
        setStatus(st);
        setObjects(objs);
        setSelectedUnit((cur) => cur ?? objs.find((o) => o.category === "boss")?.id ?? objs[0]?.id ?? null);
        await loadDraft(st.draft_default);
        tapi.tuningHistory().then((h) => !cancelled && setHistory(h), () => undefined);
        tapi.tuningObjects("skill").then(
          (list) => {
            if (cancelled) return;
            setSkills(list);
            setSelectedSkill((cur) => cur ?? list[0]?.id ?? null);
          },
          (e: unknown) => !cancelled && setError(`讀不到技能清單：${errorText(e)}`),
        );
        tapi.tuningPresets().then((p) => !cancelled && setPresets(p), () => undefined);
        tapi.tuningLadders().then((l) => !cancelled && setLadder(l.dice), () => undefined);
        tapi.tuningRatioBaseline().then((b) => !cancelled && setBaselineNote(baselineText(b)), () => undefined);
        tapi.tuningSimOptions().then(
          (opts) => {
            if (cancelled) return;
            setSimOptions(opts);
            const firstMap = opts.maps?.[0]?.id;
            setSimForm({
              boss: opts.bosses[0]?.key ?? "",
              builds: opts.builds.map((b) => b.id),
              seedsText: String(opts.default_seeds),
              scenario: "boss",
              map: { ...DEFAULT_MAP_FORM, maps: firstMap === undefined ? [] : [firstMap], seedsText: String(opts.map_default_seeds) },
              ratio: { ...DEFAULT_RATIO_FORM, seedsText: String(opts.ratio_default_seeds ?? 50) },
            });
          },
          (e: unknown) => !cancelled && setSimError(`讀不到模擬選項：${errorText(e)}`),
        );
      } catch (e) {
        if (!cancelled) setError(errorText(e));
      }
    });
    return () => {
      cancelled = true;
      leaving.current = true;
    };
  }, [tapi, loadDraft]);

  // 選了對象 → 讀欄位；是模擬可選的頭目就順便把模擬的頭目換成它。
  useEffect(() => {
    if (selected === null || entry.kind !== "open") return undefined;
    let cancelled = false;
    setDetail((cur) => (cur !== null && cur.id === selected ? cur : null));
    tapi.tuningObject(objectKind(tab, objects, selected), selected).then(
      (d) => {
        if (cancelled) return;
        setDetail(d);
        const boss = simOptions?.bosses.find((b) => b.unit_id === d.id);
        if (boss !== undefined && job?.state !== "running") setSimForm((f) => ({ ...f, boss: boss.key }));
      },
      (e: unknown) => !cancelled && setError(errorText(e)),
    );
    return () => {
      cancelled = true;
    };
    // job 只用來判斷「跑中不換」，不需要因它重讀欄位
  }, [selected, tab, entry.kind, tapi, simOptions, objects]);

  // 改了數值 → 停止輸入 0.5 秒後驗證整張改動單（不必先存）；後端的 `superseded` 結果丟掉。
  useEffect(() => {
    if (entry.kind !== "open") return undefined;
    if (changes.length === 0) {
      setCheck(null);
      setChecking(false);
      return undefined;
    }
    let cancelled = false;
    setChecking(true);
    const timer = setTimeout(() => {
      tapi.tuningCheck(draftName, changes).then(
        (r) => {
          if (cancelled || r.superseded) return;
          setCheck(r);
          setChecking(false);
        },
        (e: unknown) => {
          if (cancelled) return;
          setError(errorText(e));
          setChecking(false);
        },
      );
    }, CHECK_DELAY_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [changes, draftName, entry.kind, tapi]);

  // 技能的預算比例：這招的改動變了 → 停止輸入 0.3 秒後問後端（只送這招檔案的改動）。
  const skillId = detail?.kind === "skill" ? detail.id : null;
  const skillFile = detail?.kind === "skill" ? detail.file : null;
  const ownKey = useMemo(() => JSON.stringify(changes.filter((c) => c.file === skillFile)), [changes, skillFile]);
  useEffect(() => {
    if (skillId === null || entry.kind !== "open") {
      setBudget(null);
      return undefined;
    }
    let cancelled = false;
    setBudgetLoading(true);
    const timer = setTimeout(() => {
      tapi.tuningBudget(skillId, JSON.parse(ownKey) as ReturnType<typeof editsToChanges>).then(
        (b) => {
          if (cancelled) return;
          setBudget(b);
          setBudgetLoading(false);
        },
        (e: unknown) => {
          if (cancelled) return;
          setError(`預算算不出來：${errorText(e)}`);
          setBudgetLoading(false);
        },
      );
    }, BUDGET_DELAY_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [skillId, ownKey, entry.kind, tapi]);

  // NW-2c：技能的 1 階比值（換招、比值工作跑完、匯入基準後重讀）。
  const ratioDone = job?.state === "done" && job.ratio_result != null ? job.job_id : null;
  const [ratioTick, setRatioTick] = useState(0);
  useEffect(() => {
    if (skillId === null || entry.kind !== "open") {
      setRatio(null);
      return undefined;
    }
    let cancelled = false;
    setRatioLoading(true);
    tapi.tuningSkillRatio(skillId).then(
      (r) => {
        if (cancelled) return;
        setRatio(r);
        setRatioLoading(false);
      },
      () => {
        if (cancelled) return;
        setRatio(null);
        setRatioLoading(false);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [skillId, entry.kind, tapi, ratioDone, ratioTick]);

  // NW-2c：比值情境的規模（組數、預估秒數）；停止輸入 0.3 秒後問後端。
  const simEdited = useMemo(() => (edited.length > 0 ? edited : skillId !== null ? [skillId] : []), [edited, skillId]);
  const ratioForm = simForm.ratio ?? DEFAULT_RATIO_FORM;
  const ratioKey = simForm.scenario === "ratio" && ratioSeedsProblem(ratioForm.seedsText) === null ? JSON.stringify([ratioSkillsOf(ratioForm, simEdited), Number(ratioForm.seedsText.trim())]) : null;
  useEffect(() => {
    setRatioPlan(null);
    if (ratioKey === null || entry.kind !== "open") return undefined;
    const [skills, seeds] = JSON.parse(ratioKey) as [string[], number];
    if (skills.length === 0) return undefined;
    let cancelled = false;
    const timer = setTimeout(() => {
      tapi.tuningRatioPlan({ skills, seeds }).then(
        (p) => !cancelled && setRatioPlan(p),
        (e: unknown) => !cancelled && setSimError(errorText(e)),
      );
    }, BUDGET_DELAY_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [ratioKey, entry.kind, tapi, ratioDone]);

  // 模擬結果的招式名稱（後端只給 ID）：技能清單有的直接用，沒有的（劇情技能、升階版）一招問一次技能卡。
  const listNames = useMemo(() => new Map(skills.map((s) => [s.id, s.name_zh] as const)), [skills]);
  useEffect(() => {
    const ids = new Set<string>();
    const result = job?.result;
    if (result != null) for (const side of [result.before, result.after]) for (const p of side.phases) for (const s of p.skills) ids.add(s.skill);
    const mapResult = job?.map_result;
    if (mapResult != null) for (const side of [mapResult.before, mapResult.after]) for (const s of side.skills) ids.add(s.skill);
    for (const id of ids) {
      if (skillNames[id] !== undefined || listNames.has(id)) continue;
      tapi.skill(id).then(
        (card) => setSkillNames((m) => ({ ...m, [id]: card.name_zh })),
        () => setSkillNames((m) => ({ ...m, [id]: id })),
      );
    }
  }, [job, skillNames, listNames, tapi]);

  async function run(task: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await task();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  const save = () =>
    run(async () => {
      await tapi.tuningPutDraft(draftName, changes);
      setSaved(changes);
      setInfo(`已存草稿「${draftName}」`);
      refreshStatus();
    });

  const switchDraft = (name: string) =>
    run(async () => {
      if (unsaved) await tapi.tuningPutDraft(draftName, changes);
      await loadDraft(name);
      setInfo(unsaved ? `已先存好「${draftName}」，換到「${name}」` : `換到草稿「${name}」`);
      refreshStatus();
    });

  const discard = () =>
    run(async () => {
      await tapi.tuningDeleteDraft(draftName);
      setEdits({});
      setSaved([]);
      setDiff(null);
      setInfo(`已丟掉草稿「${draftName}」`);
      refreshStatus();
    });

  const showDiff = () =>
    run(async () => {
      setDiff(await saveAndDiff(tapi, draftName, changes));
      setSaved(changes);
    });

  const askApply = () =>
    run(async () => {
      setApplyError(null);
      const d = await saveAndDiff(tapi, draftName, changes);
      setSaved(changes);
      setConfirm(d);
    });

  const doApply = () =>
    run(async () => {
      try {
        const result = await tapi.tuningApply(draftName, applyConfirm(check));
        setApplied(result);
        setInfo(null);
        setConfirm(null);
        setEdits({});
        setSaved([]);
        setDiff(null);
        setCheck(null);
        setBudgetOk(new Set());
        setMovesOk(new Set());
        refreshStatus();
        loadSkills();
        if (selected !== null) setDetail(await tapi.tuningObject(objectKind(tab, objects, selected), selected));
      } catch (e) {
        setApplyError(errorText(e)); // 409：前置檢查不過、或「我確定」和實際要勾的不符；檔案沒動
      }
    });

  const revert = (commit: string) =>
    run(async () => {
      if (unsaved) await tapi.tuningPutDraft(draftName, changes);
      const view = await tapi.tuningRevert(draftName, commit);
      const next = editsFromDraft(view);
      setEdits(next);
      setSaved(editsToChanges(next));
      setDiff(null);
      setInfo(`已把「${commit.slice(0, 8)}」的反向改動放進草稿「${draftName}」；確認差異後按「寫回遊戲」才會真的改回去`);
    });

  const simRequest = (): TuningSimRequest => {
    if (simForm.scenario === "ratio") {
      return { draft: draftName, scenario: "ratio", skills: ratioSkillsOf(ratioForm, simEdited), seeds: Number(ratioForm.seedsText.trim()) };
    }
    if (simForm.scenario === "map") {
      const map = simForm.map ?? DEFAULT_MAP_FORM;
      return {
        draft: draftName,
        scenario: "map",
        maps: [...map.maps],
        seeds: seedsOf(map.seedsText),
        allies: map.allies.length === 0 ? null : [...map.allies],
        probe: probesOf(map, edited),
        inject: [...map.inject],
      };
    }
    const builds = simOptions !== null && simForm.builds.length === simOptions.builds.length ? null : [...simForm.builds];
    return { draft: draftName, scenario: "boss", boss: simForm.boss, builds, seeds: Number(simForm.seedsText.trim()) };
  };

  const startSim = () =>
    run(async () => {
      setSimError(null);
      if (unsaved) {
        await tapi.tuningPutDraft(draftName, changes);
        setSaved(changes);
      }
      let first: TuningSimJob;
      try {
        first = await tapi.tuningStartSim(simRequest());
      } catch (e) {
        setSimError(errorText(e));
        return;
      }
      void pollSim(tapi, first, setJob, () => leaving.current);
    });

  const importBaseline = (text: string) =>
    run(async () => {
      let data: unknown;
      try {
        data = JSON.parse(text);
      } catch {
        setSimError("匯入失敗：檔案不是 JSON");
        return;
      }
      try {
        const info = await tapi.tuningImportRatioBaseline(data);
        setBaselineNote(baselineText(info));
        setSimError(null);
        setRatioTick((n) => n + 1);
      } catch (e) {
        setSimError(`匯入失敗：${errorText(e)}`);
      }
    });

  const cancelSim = () => {
    if (job === null) return;
    tapi.tuningCancelSim(job.job_id).then(setJob, (e: unknown) => setSimError(errorText(e)));
  };

  const previewGroup = () =>
    run(async () => {
      setGroupError(null);
      try {
        setGroupPreview(await tapi.tuningGroupPreview(groupRequest(groupForm, skillFilter, checked)));
      } catch (e) {
        setGroupPreview(null);
        setGroupError(errorText(e));
      }
    });

  // 「放進草稿」：逐招逐欄併進改動單 → 存草稿（後端回中文標籤）→ 差異頁逐招逐欄。
  const addGroup = () =>
    run(async () => {
      if (groupPreview === null) return;
      const merged = editsToChanges(mergeGroupRows(edits, groupPreview.rows));
      const view = await tapi.tuningPutDraft(draftName, merged);
      const next = editsFromDraft(view);
      setEdits(next);
      setSaved(editsToChanges(next));
      setDiff(null);
      const n = groupPreview.rows.filter((r) => r.verdict !== "skipped").length;
      setInfo(`已把分組改的 ${n} 招放進草稿「${draftName}」（逐招逐欄）；按「看差異」確認`);
      setGroupPreview(null);
    });

  const onEdit = (field: TuningFieldView, text: string) => {
    if (detail !== null) setEdits((cur) => setEdit(cur, detail, field, text));
  };

  const onList = (field: TuningFieldView, list: string[] | null) => {
    if (detail !== null) setEdits((cur) => setListEdit(cur, detail, field, list));
  };

  const openObject = (id: string) => {
    if (id.startsWith("skill_")) {
      setTab("skill");
      setMode("one");
      setSelectedSkill(id);
    } else {
      setTab("unit");
      setSelectedUnit(id);
    }
  };

  const header = (
    <header className="ws-header tn-header">
      <h1>數值工坊</h1>
      <span className="muted">改敵人、頭目與技能的數值、當場驗證、跑小模擬比較改前改後，確定後寫回遊戲。</span>
      <span className="ws-header-tools">
        <button type="button" onClick={onHome}>
          回首頁
        </button>
      </span>
    </header>
  );

  if (entry.kind !== "open") {
    return (
      <div className="tuning-screen">
        {header}
        <div className="panel tn-off" data-testid="tuning-off">
          {entry.kind === "checking" ? "讀取中……" : entry.reason}
        </div>
      </div>
    );
  }

  const blocked = changes.length > 0 && check !== null && !check.ok ? "草稿有錯，先修正再模擬" : checking ? "等驗證跑完再開始" : null;
  const pageErrors = pageErrorsOf(check, edits, detail?.file ?? null);
  const skillName = (id: string) => listNames.get(id) ?? skillNames[id] ?? id;
  const pending = confirmBlock(check, budgetOk, movesOk);
  const movesFlag = detail?.kind === "unit" ? (check?.needs_confirm_min_moves ?? []).find((f) => f.unit_id === detail.id) : undefined;
  const presetLabel = presets.find((p) => p.key === preset)?.label_zh ?? "目前的篩選";

  const middle =
    tab === "skill" && mode === "group" ? (
      <GroupPanel
        form={groupForm}
        filter={skillFilter}
        filterLabel={presetLabel}
        filterCount={filtered.length}
        manual={checked}
        preview={groupPreview}
        error={groupError}
        busy={busy}
        onForm={(f) => {
          setGroupForm(f);
          setGroupPreview(null);
        }}
        onPreview={() => void previewGroup()}
        onAdd={() => void addGroup()}
      />
    ) : detail === null || detail.kind !== objectKind(tab, objects, detail.id) ? (
      <div className="panel muted">讀取中……</div>
    ) : detail.kind === "skill" ? (
      <SkillForm
        detail={detail}
        edits={edits}
        check={check}
        budget={budget}
        budgetLoading={budgetLoading}
        ladder={ladder}
        confirmed={budgetOk.has(detail.id)}
        onConfirm={(on) => setBudgetOk((s) => toggled(s, detail.id, on))}
        onEdit={onEdit}
        onDrop={(k) => setEdits((cur) => dropEdit(cur, k))}
        ratio={ratio}
        ratioLoading={ratioLoading}
      />
    ) : (
      <FieldForm detail={detail} edits={edits} check={check} ladder={ladder} skills={skills} onList={onList} onEdit={onEdit} onDrop={(k) => setEdits((cur) => dropEdit(cur, k))} />
    );

  return (
    <div className="tuning-screen">
      {header}
      <ErrorBanner message={error} onClose={() => setError(null)} />
      {status?.restart_needed === true && (
        <div className="tn-restart-banner" role="status">
          {status.restart_note_zh}
        </div>
      )}
      {status !== null && !status.can_write && <div className="tn-readonly muted small">只能改與模擬，不能寫回：{status.reason_zh}</div>}
      {info !== null && (
        <div className="tn-info-line" role="status">
          {info}
          <button type="button" className="small-button" onClick={() => setInfo(null)}>
            知道了
          </button>
        </div>
      )}
      <div className="tn-layout">
        <ObjectPanel
          tab={tab}
          onTab={setTab}
          units={{ objects, selected: selectedUnit, query, edits, onQuery: setQuery, onSelect: setSelectedUnit }}
          skills={{
            skills,
            presets,
            selected: selectedSkill,
            query: skillQuery,
            filter: skillFilter,
            preset,
            checked,
            edits,
            onQuery: setSkillQuery,
            onFilter: (f, p) => {
              setSkillFilter(f);
              setPreset(p);
              setGroupPreview(null);
            },
            onSelect: (id) => {
              setSelectedSkill(id);
              setMode("one");
            },
            onCheck: (ids) => {
              setChecked(ids);
              setGroupPreview(null);
            },
          }}
        />
        <div className="tn-col">
          {tab === "skill" && (
            <div className="tn-tabs" role="tablist" aria-label="技能的改法">
              {(
                [
                  ["one", "這一招"],
                  ["group", "分組改"],
                ] as const
              ).map(([key, label]) => (
                <button key={key} type="button" role="tab" aria-selected={mode === key} className={mode === key ? "active" : ""} onClick={() => setMode(key)}>
                  {label}
                </button>
              ))}
            </div>
          )}
          {pageErrors.length > 0 && (
            <div className="panel tn-page-errors" role="alert" data-testid="tuning-page-errors">
              {pageErrors.map((m) => (
                <div key={m} className="tn-error">
                  {m}
                </div>
              ))}
            </div>
          )}
          <CheckLine check={check} checking={checking} count={changes.length} />
          {movesFlag !== undefined && (
            <div className="panel tn-moves-flag" role="alert" data-testid="min-moves-flag">
              <div className="tn-error">{movesFlag.message_zh}</div>
              <label className="tn-confirm-check">
                <input type="checkbox" checked={movesOk.has(movesFlag.unit_id)} onChange={(e) => setMovesOk((s) => toggled(s, movesFlag.unit_id, e.target.checked))} data-testid="confirm-min-moves" />
                我確定（寫回時 commit 內文會記「#149 例外」）
              </label>
            </div>
          )}
          {middle}
        </div>
        <div className="tn-col tn-side">
          {status !== null && (
            <DraftBar status={status} name={draftName} edits={editList} unsaved={unsaved} busy={busy} onSave={() => void save()} onSwitch={(n) => void switchDraft(n)} onDiscard={() => void discard()} onOpen={openObject} />
          )}
          {simOptions !== null ? (
            <SimPanel
              options={simOptions}
              form={simForm}
              job={job}
              blocked={blocked}
              error={simError}
              skillName={skillName}
              onForm={setSimForm}
              onStart={() => void startSim()}
              onCancel={cancelSim}
              edited={simEdited}
              skillChoices={skills}
              ratioPlan={ratioPlan}
              baselineNote={baselineNote}
              onImport={(t) => void importBaseline(t)}
            />
          ) : (
            simError !== null && <div className="panel tn-error">{simError}</div>
          )}
          {status !== null && (
            <ApplyPanel
              status={status}
              count={changes.length}
              check={check}
              checking={checking}
              busy={busy}
              diff={diff}
              applied={applied}
              simRunning={job?.state === "running"}
              confirm={pending}
              exceptions={
                <ExceptionChecks
                  check={check}
                  budgetOk={budgetOk}
                  movesOk={movesOk}
                  onBudget={(id, on) => setBudgetOk((s) => toggled(s, id, on))}
                  onMoves={(id, on) => setMovesOk((s) => toggled(s, id, on))}
                />
              }
              onDiff={() => void showDiff()}
              onApply={() => void askApply()}
            />
          )}
          <HistoryList history={history} busy={busy} onRevert={(c) => void revert(c)} />
        </div>
      </div>
      {confirm !== null && (
        <ApplyDialog
          diff={confirm}
          busy={busy}
          error={applyError}
          check={check}
          budgetOk={budgetOk}
          movesOk={movesOk}
          onBudget={(id, on) => setBudgetOk((s) => toggled(s, id, on))}
          onMoves={(id, on) => setMovesOk((s) => toggled(s, id, on))}
          onConfirm={() => void doApply()}
          onCancel={() => setConfirm(null)}
        />
      )}
    </div>
  );
}
