// 數值工坊（Phase NW-1b；開發選單 `?dev=1` 進入，伺服器要設 `TRPG_TUNING=1`）：選敵人或頭目 → 改數值（當場驗證、中文原因）→
// 小模擬改前改後並排 → 看差異 → 寫回並自動 commit（要重開伺服器生效）→ 從寫回紀錄還原。
// 純函式在 `tuning/model.ts`、非同步流程在 `tuning/flow.ts`，畫面元件在 `tuning/*.tsx`。
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client";
import type {
  TuningApplyResult,
  TuningCheckResult,
  TuningDiff,
  TuningFieldView,
  TuningHistoryEntry,
  TuningObjectDetail,
  TuningObjectSummary,
  TuningSimJob,
  TuningSimOptions,
  TuningStatus,
} from "../api/types";
import { ErrorBanner } from "../ui/ErrorBanner";
import { ApplyDialog, ApplyPanel, CheckLine, DraftBar, HistoryList } from "../tuning/DraftPanel";
import { FieldForm, ObjectList } from "../tuning/FieldForm";
import { errorText, pollSim, probeEntry, saveAndDiff, type TuningApi } from "../tuning/flow";
import {
  CHECK_DELAY_MS,
  DEFAULT_DRAFT,
  dropEdit,
  editsFromDraft,
  editsToChanges,
  pageErrorsOf,
  sameChanges,
  setEdit,
  type EntryState,
  type Edits,
} from "../tuning/model";
import { SimPanel, type SimForm } from "../tuning/SimPanel";

interface Props {
  onHome(): void;
  /** 測試可換掉 API。 */
  tapi?: TuningApi;
}

export function TuningScreen({ onHome, tapi = api }: Props) {
  const [entry, setEntry] = useState<EntryState>({ kind: "checking" });
  const [status, setStatus] = useState<TuningStatus | null>(null);
  const [objects, setObjects] = useState<TuningObjectSummary[]>([]);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<TuningObjectDetail | null>(null);
  const [draftName, setDraftName] = useState(DEFAULT_DRAFT);
  const [edits, setEdits] = useState<Edits>({});
  const [saved, setSaved] = useState<ReturnType<typeof editsToChanges>>([]);
  const [check, setCheck] = useState<TuningCheckResult | null>(null);
  const [checking, setChecking] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [diff, setDiff] = useState<TuningDiff | null>(null);
  const [confirm, setConfirm] = useState<TuningDiff | null>(null);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [applied, setApplied] = useState<TuningApplyResult | null>(null);
  const [history, setHistory] = useState<TuningHistoryEntry[]>([]);
  const [simOptions, setSimOptions] = useState<TuningSimOptions | null>(null);
  const [simForm, setSimForm] = useState<SimForm>({ boss: "", builds: [], seedsText: "3" });
  const [job, setJob] = useState<TuningSimJob | null>(null);
  const [simError, setSimError] = useState<string | null>(null);
  const [skillNames, setSkillNames] = useState<Readonly<Record<string, string>>>({});
  const leaving = useRef(false);

  const changes = useMemo(() => editsToChanges(edits), [edits]);
  const editList = useMemo(() => Object.values(edits).sort((a, b) => (a.object_id + a.path < b.object_id + b.path ? -1 : 1)), [edits]);
  const unsaved = !sameChanges(changes, saved);

  const refreshStatus = useCallback(() => {
    tapi.tuningStatus().then(setStatus, (e: unknown) => setError(errorText(e)));
    tapi.tuningHistory().then(setHistory, () => setHistory([]));
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

  // 進畫面：先問開關有沒有開；開了才讀對象、草稿、模擬選項、紀錄。
  useEffect(() => {
    leaving.current = false;
    let cancelled = false;
    void probeEntry(tapi).then(async (state) => {
      if (cancelled) return;
      setEntry(state);
      if (state.kind !== "open") return;
      try {
        const [st, objs] = await Promise.all([tapi.tuningStatus(), tapi.tuningObjects()]);
        if (cancelled) return;
        setStatus(st);
        setObjects(objs);
        setSelected((cur) => cur ?? objs.find((o) => o.category === "boss")?.id ?? objs[0]?.id ?? null);
        await loadDraft(st.draft_default);
        tapi.tuningHistory().then((h) => !cancelled && setHistory(h), () => undefined);
        tapi.tuningSimOptions().then(
          (opts) => {
            if (cancelled) return;
            setSimOptions(opts);
            setSimForm({ boss: opts.bosses[0]?.key ?? "", builds: opts.builds.map((b) => b.id), seedsText: String(opts.default_seeds) });
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
    tapi.tuningObject("unit", selected).then(
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
  }, [selected, entry.kind, tapi, simOptions]);

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

  // 模擬結果的招式名稱（後端只給 ID）：一招問一次技能卡，問不到就顯示 ID。
  useEffect(() => {
    const result = job?.result;
    if (result == null) return;
    const ids = new Set<string>();
    for (const side of [result.before, result.after]) for (const p of side.phases) for (const s of p.skills) ids.add(s.skill);
    for (const id of ids) {
      if (skillNames[id] !== undefined) continue;
      tapi.skill(id).then(
        (card) => setSkillNames((m) => ({ ...m, [id]: card.name_zh })),
        () => setSkillNames((m) => ({ ...m, [id]: id })),
      );
    }
  }, [job, skillNames, tapi]);

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
        const result = await tapi.tuningApply(draftName);
        setApplied(result);
        setConfirm(null);
        setEdits({});
        setSaved([]);
        setDiff(null);
        setCheck(null);
        refreshStatus();
        if (selected !== null) setDetail(await tapi.tuningObject("unit", selected));
      } catch (e) {
        setApplyError(errorText(e)); // 409：前置檢查不過（例如開發 PM 正在合併），檔案沒動
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

  const startSim = () =>
    run(async () => {
      setSimError(null);
      if (unsaved) {
        await tapi.tuningPutDraft(draftName, changes);
        setSaved(changes);
      }
      const builds = simOptions !== null && simForm.builds.length === simOptions.builds.length ? null : [...simForm.builds];
      let first: TuningSimJob;
      try {
        first = await tapi.tuningStartSim({ draft: draftName, scenario: "boss", boss: simForm.boss, builds, seeds: Number(simForm.seedsText.trim()) });
      } catch (e) {
        setSimError(errorText(e));
        return;
      }
      void pollSim(tapi, first, setJob, () => leaving.current);
    });

  const cancelSim = () => {
    if (job === null) return;
    tapi.tuningCancelSim(job.job_id).then(setJob, (e: unknown) => setSimError(errorText(e)));
  };

  const onEdit = (field: TuningFieldView, text: string) => {
    if (detail !== null) setEdits((cur) => setEdit(cur, detail, field, text));
  };

  const header = (
    <header className="ws-header tn-header">
      <h1>數值工坊</h1>
      <span className="muted">改敵人與頭目的數值、當場驗證、跑小模擬比較改前改後，確定後寫回遊戲。</span>
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
  const skillName = (id: string) => skillNames[id] ?? id;

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
        <ObjectList objects={objects} selected={selected} query={query} edits={edits} onQuery={setQuery} onSelect={setSelected} />
        <div className="tn-col">
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
          {detail === null ? <div className="panel muted">讀取中……</div> : <FieldForm detail={detail} edits={edits} check={check} onEdit={onEdit} onDrop={(k) => setEdits((cur) => dropEdit(cur, k))} />}
        </div>
        <div className="tn-col tn-side">
          {status !== null && (
            <DraftBar status={status} name={draftName} edits={editList} unsaved={unsaved} busy={busy} onSave={() => void save()} onSwitch={(n) => void switchDraft(n)} onDiscard={() => void discard()} onOpen={setSelected} />
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
            />
          ) : (
            simError !== null && <div className="panel tn-error">{simError}</div>
          )}
          {status !== null && (
            <ApplyPanel status={status} count={changes.length} check={check} checking={checking} busy={busy} diff={diff} applied={applied} simRunning={job?.state === "running"} onDiff={() => void showDiff()} onApply={() => void askApply()} />
          )}
          <HistoryList history={history} busy={busy} onRevert={(c) => void revert(c)} />
        </div>
      </div>
      {confirm !== null && <ApplyDialog diff={confirm} busy={busy} error={applyError} onConfirm={() => void doApply()} onCancel={() => setConfirm(null)} />}
    </div>
  );
}

