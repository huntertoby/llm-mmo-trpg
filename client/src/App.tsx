// 畫面切換：首頁（正式入口：繼續／建立新角色／roguelite 一輪／設定，UI-E1b）、開發選單（`?dev=1`：單場戰鬥、技能工坊、roguelite 一輪、數值工坊 NW-1b）、大世界（5A-5）。啟動時先讀名詞對照表，再嘗試回到上次進行中的一輪。
import { useEffect, useState } from "react";
import { api, ApiError } from "./api/client";
import type { BattleResponse, RunResponse } from "./api/types";
import { setGlossary } from "./battle/glossary";
import { BattleScreen } from "./screens/BattleScreen";
import { StartScreen } from "./screens/StartScreen";
import { HomeScreen } from "./screens/HomeScreen";
import { WorkshopScreen } from "./screens/WorkshopScreen";
import { TuningScreen } from "./screens/TuningScreen";
import { isNotFoundStatus, readCurrentRun, resumeRun, writeCurrentRun } from "./run/flow";
import { isDevMode } from "./run/startFlow";
import { RunNewScreen } from "./screens/RunNewScreen";
import { RunScreen } from "./screens/RunScreen";
import { LoginScreen } from "./screens/LoginScreen";
import { WorldEntry } from "./screens/WorldEntry";
import { AUTH_EXPIRED_EVENT } from "./auth/auth";
import { ErrorBanner } from "./ui/ErrorBanner";
import { writeWorldChar } from "./world/mapView";

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
  const [screen, setScreen] = useState<"start" | "workshop" | "run_new" | "world" | "tuning">("start");
  /** 進行中的一輪；`auto` ＝ 存檔在戰鬥中時直接進入該場戰鬥。 */
  const [run, setRun] = useState<{ data: RunResponse; auto: boolean } | null>(null);
  const [resuming, setResuming] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  /** 5D-R2：開發模式關時一輪、戰鬥、工坊、裝備測試要登入；收到 401 就先顯示登入畫面。 */
  const [needLogin, setNeedLogin] = useState(false);

  // 大世界入口自己處理登入（WorldEntry 也聽這個事件），其他畫面在這裡導到登入畫面。
  useEffect(() => {
    if (screen === "world") return undefined;
    const onExpired = () => setNeedLogin(true);
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired);
  }, [screen]);

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
            // 要登入（5D-R2）：先不忘掉這一輪，登入後重新整理還能接回來。
            if (e instanceof ApiError && e.status === 401) return;
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
    // I8：dev 程式動態載入（獨立 chunk，不進主 bundle）。
    if (!ready || !isDevMode(window.location.search)) return undefined;
    const onEnter = (e: Event) => {
      setBattle(null);
      enterRun((e as CustomEvent<RunResponse>).detail, false);
    };
    let cancelled = false;
    let detach = () => {};
    void import("./dev/devScreens").then(({ createDevRun, DEV_ENTER_EVENT, devScreenParam }) => {
      if (cancelled) return;
      window.addEventListener(DEV_ENTER_EVENT, onEnter);
      detach = () => window.removeEventListener(DEV_ENTER_EVENT, onEnter);
      const screenParam = devScreenParam(window.location.search);
      if (screenParam !== null) {
        createDevRun(screenParam).then(
          (data) => enterRun(data, false),
          (err: unknown) => setNotice(err instanceof Error ? err.message : String(err)),
        );
      }
    });
    return () => {
      cancelled = true;
      detach();
    };
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
  if (needLogin && screen !== "world") {
    return (
      <LoginScreen
        heading="登入"
        onLoggedIn={() => {
          setNeedLogin(false);
          window.location.reload(); // 重新讀取：上次的一輪與畫面照登入後的狀態接回來
        }}
        // 不給「返回首頁」：開發模式關時首頁（開戰表單）本身就要登入，回去會立刻再導回來
      />
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
    if (screen === "world") {
      return <WorldEntry onHome={() => setScreen("start")} />;
    }
    if (screen === "workshop") {
      return <WorkshopScreen onHome={() => setScreen("start")} onStartBattle={setBattle} />;
    }
    // 6F-1：開發選單（單場戰鬥、一輪、工坊、數值工坊）只在 `?dev=1`
    if (screen === "tuning" && isDevMode(window.location.search)) {
      return <TuningScreen onHome={() => setScreen("start")} />;
    }
    if (!isDevMode(window.location.search)) {
      // UI-E1b：首頁四顆鈕（繼續／建立新角色／roguelite 一輪／設定）；「繼續」記住角色後進大世界（WorldScreen 讀同一個記號）
      return (
        <HomeScreen
          onContinue={(id) => {
            writeWorldChar(id);
            setScreen("world");
          }}
          onCreate={() => {
            writeWorldChar(null);
            setScreen("world");
          }}
          onRun={() => setScreen("run_new")}
          notice={notice}
          onCloseNotice={() => setNotice(null)}
        />
      );
    }
    return (
      <StartScreen
        onStart={setBattle}
        onWorkshop={() => setScreen("workshop")}
        onTuning={() => setScreen("tuning")}
        onNewRun={() => setScreen("run_new")}
        onWorld={() => setScreen("world")}
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
