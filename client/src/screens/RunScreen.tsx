// 一輪的主畫面：依節點（戰鬥／升級／營火／結束）顯示進度、升級、營火或結束摘要；戰鬥沿用戰鬥畫面。
import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api/client";
import type { BattleResponse, RunChoice, RunResponse } from "../api/types";
import { OBJECTIVE_ICONS, objectiveBadge } from "../battle/objective";
import { battleName, runView, writeCurrentRun } from "../run/flow";
import { RunHeroPanel } from "../run/RunHeroPanel";
import { SkillPointsSection } from "../run/SkillPointsSection";
import { TestModeBadge } from "../ui/TestModeBadge";
import { ErrorBanner } from "../ui/ErrorBanner";
import { primeSkillCard } from "../ui/useSkillCards";
import { BattleScreen } from "./BattleScreen";
import { RunCampfire } from "./RunCampfire";
import { RunEnded } from "./RunEnded";
import { RunLevelUp } from "./RunLevelUp";

interface Props {
  initial: RunResponse;
  /** 讀檔或重新整理回來時，若存檔在戰鬥中就直接進入該場戰鬥。 */
  autoResume?: boolean;
  onHome(): void;
  onNewRun(): void;
}

function errorText(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

export function RunScreen({ initial, autoResume = false, onHome, onNewRun }: Props) {
  const [run, setRun] = useState(initial);
  const [battle, setBattle] = useState<BattleResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const resumedRef = useRef(false);
  const runId = run.run_id;

  // 主角裝備的技能（含升級得到的生成技能）先放進卡片快取，戰鬥畫面才認得出名稱。
  useEffect(() => {
    for (const card of run.hero.skills) primeSkillCard(card);
  }, [run.hero.skills]);

  // 結束的一輪不需要在重新整理後回來。
  useEffect(() => {
    if (run.node.kind === "ended") writeCurrentRun(null);
  }, [run.node.kind]);

  async function enterBattle() {
    setBusy(true);
    setError(null);
    try {
      const res = await api.runBattle(runId);
      setRun(res.run);
      setBattle(res.battle);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (autoResume && initial.battle_id !== null && !resumedRef.current) {
      resumedRef.current = true;
      void enterBattle();
    }
    // 只在掛載時判斷一次。
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** 戰鬥結束（或中途離開）→ 向後端結算並取得下一個節點。 */
  async function backToRun() {
    setError(null);
    try {
      setRun(await api.run(runId));
      setBattle(null);
    } catch (e) {
      setError(errorText(e));
    }
  }

  async function save(): Promise<string> {
    const out = await api.saveRun(runId);
    const text = out.in_battle ? `已存檔（戰鬥中：${out.file}）` : `已存檔（${out.file}）`;
    setNotice(text);
    return text;
  }

  async function saveFromMenu() {
    setError(null);
    try {
      await save();
    } catch (e) {
      setError(errorText(e));
    }
  }

  async function choose(choice: RunChoice): Promise<number | null> {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      setRun(await api.runChoice(runId, choice));
      return null;
    } catch (e) {
      setError(errorText(e));
      return e instanceof ApiError ? e.status : 0;
    } finally {
      setBusy(false);
    }
  }

  if (battle !== null) {
    return (
      <BattleScreen
        key={battle.battle_id}
        initial={battle}
        onExit={() => void backToRun()}
        exitLabel="回到一輪"
        runMode={{ onSave: save }}
      />
    );
  }

  let view;
  try {
    view = runView(run);
  } catch (e) {
    return (
      <div className="run-screen">
        <ErrorBanner message={errorText(e)} onClose={() => setError(null)} />
        <button type="button" onClick={onHome}>
          回首頁
        </button>
      </div>
    );
  }

  return (
    <div className="run-screen">
      <header className="run-header">
        <h1>
          一輪　<span className="muted small">種子 {run.seed}</span>
          {run.test_mode && <TestModeBadge />}
        </h1>
        <div className="run-header-buttons">
          {view.screen !== "ended" && (
            <button type="button" disabled={busy} onClick={() => void saveFromMenu()}>
              存檔
            </button>
          )}
          <button type="button" onClick={onHome}>
            回首頁
          </button>
        </div>
      </header>
      <ErrorBanner message={error} onClose={() => setError(null)} />
      {notice !== null && <div className="run-notice">{notice}</div>}
      {view.screen === "ended" ? (
        <RunEnded run={run} victory={view.victory} onNewRun={onNewRun} onHome={onHome} />
      ) : (
        <div className="run-layout">
          <RunHeroPanel hero={run.hero} />
          <div className="run-main">
            <RunPlanList run={run} />
            {view.screen === "progress" && (
              <div className="panel run-next">
                <h2>
                  下一場：{battleName(view.index, view.boss)}　{view.mapName}
                </h2>
                <div className={`run-next-goal ${view.goalKind}`}>
                  {/* goalLine 本身已是「名稱：說明」（3-41b），前面只放圖示，避免「全滅：全滅：」 */}
                  {OBJECTIVE_ICONS[view.goalKind]} {view.goalLine}
                </div>
                <div className="muted small">敵人：{view.enemies.join("、")}</div>
                <div className="muted small">隊友：標準隊友 2 名（滿狀態）；{run.resource_rule_zh}</div>
                <div className="run-actions">
                  <button type="button" className="primary" disabled={busy} onClick={() => void enterBattle()}>
                    {busy ? "載入中……" : view.buttonLabel}
                  </button>
                </div>
              </div>
            )}
            {view.screen === "progress" && (run.hero.skill_points ?? 0) > 0 && (
              <SkillPointsSection hero={run.hero} busy={busy} onChoose={choose} />
            )}
            {view.screen === "level_up" && (
              <RunLevelUp key={view.level} run={run} view={view} busy={busy} onChoose={choose} />
            )}
            {view.screen === "campfire" && (
              <RunCampfire
                key={`${view.afterBattle}`}
                run={run}
                view={view}
                busy={busy}
                onChoose={choose}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function RunPlanList({ run }: { run: RunResponse }) {
  return (
    <div className="panel run-plan">
      <div className="section-title">
        進度　<span className="muted small">{run.battles_done} / {run.plan.length} 場</span>
      </div>
      <ol className="run-plan-list">
        {run.plan.map((p) => {
          const rec = run.history.find((h) => h.index === p.index);
          const current = !p.done && p.index === run.battles_done + 1;
          return (
            <li key={p.index} className={`${p.done ? "done" : ""}${current ? " current" : ""}`}>
              <b>{battleName(p.index, p.boss)}</b>　{p.map_name_zh}
              <span className={`run-goal ${p.objective.kind}`}>{objectiveBadge(p.objective)}</span>
              <span className="muted small">
                {"　"}
                {rec !== undefined ? (rec.won ? `勝利・${rec.rounds} 輪` : "失敗") : p.done ? "完成" : ""}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
