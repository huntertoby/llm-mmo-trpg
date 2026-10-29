// 畫面切換：開始畫面、戰鬥畫面、技能工坊、roguelite 一輪。啟動時先讀名詞對照表，再嘗試回到上次進行中的一輪。
import { useEffect, useState } from "react";
import { api, ApiError } from "./api/client";
import type { BattleResponse, RunResponse } from "./api/types";
import { setGlossary } from "./battle/glossary";
import { BattleScreen } from "./screens/BattleScreen";
import { StartScreen } from "./screens/StartScreen";
import { WorkshopScreen } from "./screens/WorkshopScreen";
import { isNotFoundStatus, readCurrentRun, resumeRun, writeCurrentRun } from "./run/flow";
import { isDevMode } from "./run/startFlow";
import { createDevRun, DEV_ENTER_EVENT, devScreenParam } from "./dev/devScreens";
import { RunNewScreen } from "./screens/RunNewScreen";
import { RunScreen } from "./screens/RunScreen";
import { ErrorBanner } from "./ui/ErrorBanner";

/** 重新整理後回到上次的一輪：先問伺服器（記憶體裡的一輪不丟步驟）；伺服器沒有（重啟過）才讀存檔。 */
function resume(runId: string): Promise<RunResponse> {
  return resumeRun(
    runId,
    (id) => api.run(id),
    (id) => api.loadRun(id),
    (e) => e instanceof ApiError && isNotFoundStatus(e.status),
  );
}

export function App() {
  const [battle, setBattle] = useState<BattleResponse | null>(null);
  // 戰鬥結束或離開後回到哪裡：從技能工坊進來的戰鬥回到工坊（草稿存在瀏覽器，不會遺失）。
  const [screen, setScreen] = useState<"start" | "workshop" | "run_new">("start");
  /** 進行中的一輪；`auto` ＝ 存檔在戰鬥中時直接進入該場戰鬥。 */
  const [run, setRun] = useState<{ data: RunResponse; auto: boolean } | null>(null);
  const [resuming, setResuming] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .glossary()
      .then((g) => {
        if (cancelled) return;
        setGlossary(g);
        const saved = readCurrentRun();
        if (saved === null) return undefined;
        return resume(saved).then(
          (data) => {
            if (!cancelled) setRun({ data, auto: true });
          },
          (e: unknown) => {
            // 讀不回來（存檔不見、內容檔已變更等）：忘掉這一輪，在首頁說明原因。
            writeCurrentRun(null);
            if (!cancelled) setNotice(e instanceof Error ? e.message : String(e));
          },
        );
      })
      .then(() => {
        if (cancelled) return;
        setReady(true);
        setResuming(false);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const enterRun = (data: RunResponse, auto: boolean) => {
    writeCurrentRun(data.run_id);
    setNotice(null);
    setRun({ data, auto });
  };

  // 開發用入口（3U-3）：`?dev=1&screen=…` 或排版掃描送來的事件，直接進戰後畫面；不帶 `?dev=1` 就不聽。
  useEffect(() => {
    if (!ready || !isDevMode(window.location.search)) return undefined;
    const onEnter = (e: Event) => {
      setBattle(null);
      enterRun((e as CustomEvent<RunResponse>).detail, false);
    };
    window.addEventListener(DEV_ENTER_EVENT, onEnter);
    const screenParam = devScreenParam(window.location.search);
    if (screenParam !== null) {
      createDevRun(screenParam).then(
        (data) => enterRun(data, false),
        (err: unknown) => setNotice(err instanceof Error ? err.message : String(err)),
      );
    }
    return () => window.removeEventListener(DEV_ENTER_EVENT, onEnter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready]);
  const leaveRun = (next: "start" | "run_new") => {
    writeCurrentRun(null);
    setRun(null);
    setScreen(next);
  };

  if (!ready || resuming) {
    return (
      <div className="loading">
        <ErrorBanner message={error} onClose={() => setError(null)} />
        {error === null ? "載入中……" : "無法載入名詞對照表，請確認 `trpg serve` 正在執行後重新整理。"}
      </div>
    );
  }
  if (run !== null) {
    return (
      <RunScreen
        key={run.data.run_id}
        initial={run.data}
        autoResume={run.auto}
        onHome={() => leaveRun("start")}
        onNewRun={() => leaveRun("run_new")}
      />
    );
  }
  if (battle === null) {
    if (screen === "run_new") {
      return <RunNewScreen onCreated={(data) => enterRun(data, false)} onHome={() => setScreen("start")} />;
    }
    if (screen === "workshop") {
      return <WorkshopScreen onHome={() => setScreen("start")} onStartBattle={setBattle} />;
    }
    return (
      <StartScreen
        onStart={setBattle}
        onWorkshop={() => setScreen("workshop")}
        onNewRun={() => setScreen("run_new")}
        onLoadRun={(data) => enterRun(data, true)}
        notice={notice}
        onCloseNotice={() => setNotice(null)}
      />
    );
  }
  return (
    <BattleScreen
      key={battle.battle_id}
      initial={battle}
      onExit={() => setBattle(null)}
      exitLabel={screen === "workshop" ? "回到技能工坊" : undefined}
    />
  );
}
